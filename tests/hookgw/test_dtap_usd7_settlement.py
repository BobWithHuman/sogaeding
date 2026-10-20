"""Real reservation transactions; no network, secrets, or paid provider calls."""

import asyncio
import copy
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import httpx
import pytest

from app.benchmark.provider import ProviderTransport, broker_app
from app.benchmark.runtime_budget import (
    SETTLED_COST,
    BudgetStop,
    RuntimeBudget,
    StopRun,
    parent_baseline,
)
from app.benchmark.runtime_continuation import claim_successor, ledger_fingerprint, seed_ledger
from app.benchmark.runtime_controller import Controller


def manifest():
    plan = json.loads(
        Path("/workspace/artifacts/20261018-dtap-os100/user-usd7/plan.json").read_text()
    )
    m = copy.deepcopy(plan["manifest"])
    m["cost_accounting"] = SETTLED_COST
    for profile in m["providers"].values():
        profile["billing_model_aliases"] = {
            model: [model, "gpt-5.2-2025-12-11"] for model in profile["models"]
        }
    return m


def start(budget, arm="engine-off"):
    owner = budget.acquire(arm)
    key = budget.manifest["task_keys"][0]
    assert budget.claim(key, arm, owner) == "NEW"
    return key, owner


def reserve(budget, task, arm="engine-off"):
    return budget.reserve(task, arm, "actor", "gpt-5.2", 400000, 8192, 120)


def test_original_permanent_reservation_reproduces_four_request_stop(tmp_path):
    m = manifest()
    del m["cost_accounting"]
    budget = RuntimeBudget(tmp_path / "old.db", m)
    task, _ = start(budget)
    for _ in range(4):
        rid = reserve(budget, task)
        assert budget.record(
            rid, {"input_tokens": 5000, "output_tokens": 100}, resolved_model="gpt-5.2"
        )
    with pytest.raises(BudgetStop, match="CAP_EXHAUSTED_ARM"):
        reserve(budget, task)


def test_verified_completed_usage_settles_without_rewriting_original_reservation(tmp_path):
    budget = RuntimeBudget(tmp_path / "new.db", manifest())
    task, _ = start(budget)
    for _ in range(30):
        rid = reserve(budget, task)
        assert budget.record(
            rid, {"input_tokens": 5000, "output_tokens": 100}, resolved_model="gpt-5.2-2025-12-11"
        )
    status = budget.status()
    assert status["settled_micro_usd"] == 30 * 10150
    assert status["unresolved_hold_micro_usd"] == 0
    assert status["remaining_micro_usd"] == 7000000 - 304500
    assert status["provider_reservations"][0]["micro_usd_reserved"] == 30 * 814688


@pytest.mark.parametrize(
    "usage,model",
    [
        (None, "gpt-5.2"),
        ({"input_tokens": True, "output_tokens": 1}, "gpt-5.2"),
        ({"input_tokens": 400001, "output_tokens": 1}, "gpt-5.2"),
        ({"input_tokens": 1, "output_tokens": 8193}, "gpt-5.2"),
        ({"input_tokens": 1, "output_tokens": 1}, None),
        ({"input_tokens": 1, "output_tokens": 1}, "gpt-5.2-pro"),
    ],
)
def test_missing_invalid_or_unenrolled_billing_model_keeps_entire_hold(tmp_path, usage, model):
    budget = RuntimeBudget(tmp_path / "new.db", manifest())
    task, _ = start(budget)
    rid = reserve(budget, task)
    assert not budget.record(rid, usage, resolved_model=model)
    assert budget.status()["unresolved_hold_micro_usd"] == 814688
    assert budget.status()["settled_micro_usd"] == 0
    with pytest.raises(StopRun, match="NO_REPLAY"):
        budget.record(rid, {"input_tokens": 1, "output_tokens": 1}, resolved_model="gpt-5.2")


def test_pending_unknown_and_concurrent_settlements_never_overcommit(tmp_path):
    m = manifest()
    budget = RuntimeBudget(tmp_path / "new.db", m)
    task, _ = start(budget)
    start(budget, "engine-on")

    def request(i):
        arm = m["arms"][i % 2]
        try:
            rid = reserve(budget, task, arm)
        except BudgetStop:
            return False
        if i % 3 == 0:
            budget.record(
                rid, {"input_tokens": 5000, "output_tokens": 100}, resolved_model="gpt-5.2"
            )
        elif i % 3 == 1:
            budget.record(rid, None)
        with budget.db() as db:
            for arm_limit in [None, *m["arms"]]:
                where = "" if arm_limit is None else " WHERE r.arm=?"
                args = () if arm_limit is None else (arm_limit,)
                amount = (
                    db.execute(
                        "SELECT sum(coalesce(s.micro_usd,r.micro_usd)) FROM reservations r "
                        "LEFT JOIN settlements s ON r.id=s.reservation" + where,
                        args,
                    ).fetchone()[0]
                    or 0
                )
                assert amount <= (7000000 if arm_limit is None else 3500000)
        return True

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(request, range(80))) >= 8
    assert budget.status()["committed_micro_usd"] <= 7000000
    assert budget.status()["unresolved_hold_micro_usd"] > 0


def test_record_and_reserve_are_atomic_at_exact_cap(tmp_path):
    m = manifest()
    m["limits"]["total"]["micro_usd"] = 814688
    budget = RuntimeBudget(tmp_path / "new.db", m)
    task, _ = start(budget)
    rid = reserve(budget, task)
    with pytest.raises(BudgetStop):
        reserve(budget, task)
    budget.record(rid, {"input_tokens": 0, "output_tokens": 0}, resolved_model="gpt-5.2")
    assert reserve(budget, task)
    assert budget.status()["remaining_micro_usd"] == 0


def test_history_copy_keeps_unknown_and_jobs_and_includes_parent_usage(tmp_path):
    parent, child = tmp_path / "parent", tmp_path / "child"
    for folder in (parent, child):
        (folder / "broker-data").mkdir(parents=True)
    old = manifest()
    del old["cost_accounting"]
    budget = RuntimeBudget(parent / "broker-data/provider.sqlite3", old)
    task, owner = start(budget)
    known = reserve(budget, task)
    budget.record(known, {"input_tokens": 5000, "output_tokens": 100}, resolved_model="gpt-5.2")
    unknown = reserve(budget, task)
    budget.record(unknown, None)
    budget.finish(task, "engine-off", owner, "UNKNOWN", {"reexecution": "FORBIDDEN"})
    budget.release("engine-off", owner)
    budget.stop("CAP_EXHAUSTED_ARM")
    with budget.db() as db:
        before = ledger_fingerprint(db)
        baseline = parent_baseline(db)
    new = copy.deepcopy(old)
    new["cost_accounting"] = SETTLED_COST
    new["continuation"] = {
        "parent_ledger_sha256": before,
        "parent_manifest_sha256": budget.binding,
        "parent_rows": baseline,
    }
    child_budget = seed_ledger(parent, child, new)
    assert child_budget.status()["settled_micro_usd"] == 10150
    assert child_budget.status()["unresolved_hold_micro_usd"] == 814688
    assert child_budget.status()["remaining_micro_usd"] == 7000000 - 10150 - 814688
    with budget.db() as db:
        assert ledger_fingerprint(db) == before
    owner = child_budget.acquire("engine-off")
    assert child_budget.claim(task, "engine-off", owner) == "UNKNOWN"
    assert child_budget.status()["stop"] is None
    with pytest.raises(StopRun, match="MISSING_OR_INVALID"):
        RuntimeBudget(tmp_path / "missing.db", new)
    assert not (tmp_path / "missing.db").exists()
    with child_budget.db() as db:
        db.execute("DELETE FROM reservations WHERE id=?", (known,))
    with pytest.raises(StopRun, match="PARENT_RECORD_CHANGED"):
        RuntimeBudget(child_budget.path, new)


def test_budget_stop_reason_survives_secondary_stop_and_cleanup_can_persist(tmp_path):
    budget = RuntimeBudget(tmp_path / "new.db", manifest())
    task, owner = start(budget)
    budget.stop("CAP_EXHAUSTED_ARM")
    budget.stop("INFRASTRUCTURE_STOP_ALL")
    assert budget.status()["stop"] == "CAP_EXHAUSTED_ARM"
    with pytest.raises(BudgetStop):
        budget.heartbeat("engine-off", owner)
    budget.reserve_storage(
        "final", 100, cleanup={"task": task, "arm": "engine-off", "owner": owner}
    )
    with pytest.raises(StopRun):
        budget.reserve_storage(
            "other", 100, cleanup={"task": task, "arm": "engine-off", "owner": "wrong"}
        )
    with pytest.raises(BudgetStop):
        budget.reserve_storage("new-start", 100)


def test_broker_to_controller_preserves_typed_pre_send_budget_stop(tmp_path):
    async def check():
        m = manifest()
        m["limits"]["total"]["micro_usd"] = 0
        budget = RuntimeBudget(tmp_path / "new.db", m)
        task, owner = start(budget)
        hits = []
        provider = ProviderTransport(
            budget,
            {"openai": "public-fake-key"},
            transport=httpx.MockTransport(lambda r: hits.append(r)),
        )
        app = broker_app(budget, provider, "secret", "admin")
        from app.benchmark.provider import token

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="https://test"
        ) as client:
            res = await client.post(
                "/v1/responses",
                headers={
                    "Authorization": "Bearer "
                    + token("secret", task, "engine-off", "actor", 9999999999)
                },
                json={
                    "model": "gpt-5.2",
                    "reasoning": {"effort": "low"},
                    "store": False,
                    "parallel_tool_calls": False,
                    "max_output_tokens": 8192,
                    "input": [],
                },
            )
            assert res.json()["error"]["code"] == "CAP_EXHAUSTED_TOTAL"
            res = await client.post(
                "/admin/heartbeat",
                headers={"Authorization": "Bearer admin"},
                json={"arm": "engine-off", "owner": owner},
            )
            assert res.status_code == 409
            controller = Controller.__new__(Controller)
            controller.admin = SimpleNamespace(post=lambda *a, **kw: res)
            with pytest.raises(BudgetStop, match="CAP_EXHAUSTED_TOTAL"):
                controller.admin_call("heartbeat")
        assert hits == [] and budget.status()["provider_reservations"] == []

    asyncio.run(check())


def test_parent_has_only_one_authoritative_successor(tmp_path):
    claim_successor(tmp_path, "C:/one", manifest())
    with pytest.raises(FileExistsError):
        claim_successor(tmp_path, "C:/two", manifest())


@pytest.mark.parametrize(
    "ambiguous,expected",
    [
        (False, "BUDGET_STOPPED"),
        (True, "UNKNOWN"),
        ("provider", "UNKNOWN"),
        ("other_arm_cap", "UNKNOWN"),
        ("context", "CONTEXT_LIMIT"),
    ],
)
def test_controller_budget_end_stops_queue_and_does_not_hide_unknown(
    tmp_path, monkeypatch, ambiguous, expected
):
    module = ModuleType("utils.task_executor")

    class Executor:
        def __init__(self, **_kwargs):
            pass

        async def run_all(self, tasks, callback):
            return [await callback(task, []) for task in tasks]

    module.TaskExecutor = Executor
    module.ScheduledTask = lambda path, envs, priority: SimpleNamespace(task_dir=path)
    monkeypatch.setitem(sys.modules, "utils.task_executor", module)
    budget = RuntimeBudget(tmp_path / "budget.db", manifest())
    controller = Controller.__new__(Controller)
    controller.root, controller.arm = tmp_path, "engine-off"
    controller.plan = {
        "manifest": {**manifest(), "wall_seconds_per_arm": 100, "checkpoint_batch_size": 16},
        "coverage": [
            {"task_key": key, "environments": [], "coverage": "EXECUTION_READY"}
            for key in manifest()["task_keys"]
        ],
    }
    calls = []

    def admin(operation, **value):
        calls.append(operation)
        if operation == "status":
            return budget.status()
        if operation == "acquire":
            return {"owner": budget.acquire(value["arm"])}
        if operation == "claim":
            return {"state": budget.claim(value["task"], value["arm"], value["owner"])}
        return getattr(budget, operation)(**value)

    controller.admin_call = admin

    def task(_key):
        if ambiguous == "context":
            return {"actor_completed": False, "actor_initialized": True, "judge": {"error": None},
                    "lifecycle_close_observed": True,
                    "events": [{"stage": "POST", "state": "OBSERVED", "analysis_complete": False},
                               {"kind": "actor_incomplete", "code": "SOURCE_CONTEXT_LIMIT_OBSERVED"}]}
        if ambiguous != "other_arm_cap":
            budget.note_budget_rejection(_key, "engine-off", "actor", "CAP_EXHAUSTED_ARM")
        if ambiguous == "provider":
            rid = reserve(budget, _key)
            budget.record(rid, None)
        budget.stop("CAP_EXHAUSTED_ARM")
        return {
            "actor_completed": False,
            "actor_initialized": True,
            "judge": {"error": "INCOMPLETE"},
            "lifecycle_close_observed": True,
            "events": [{"kind": "actor_incomplete", "code": "HTTPStatusError"}]
            + ([{"stage": "POST", "state": "UNKNOWN"}] if ambiguous is True else []),
        }

    controller.task = task
    asyncio.run(controller.run(manifest()["task_keys"][:2]))
    count = 2 if ambiguous == "context" else 1
    assert budget.status()["jobs"] == [{"arm": "engine-off", "state": expected, "count": count}]
    assert calls.count("heartbeat") == count
    assert calls.count("claim") == count
    assert "stop" not in calls
    assert budget.status()["stop"] == (None if ambiguous == "context" else "CAP_EXHAUSTED_ARM")
