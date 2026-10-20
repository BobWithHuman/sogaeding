"""Scope2 fixed-three preparation and stop-before-next-task contracts."""

import asyncio
import json
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from app.benchmark.runtime_budget import BudgetStop, RuntimeBudget, StopRun
from app.benchmark.runtime_controller import Controller
from app.benchmark.runtime_demo import ro_ledger, runtime_grant
from app.benchmark.runtime_registry import RuntimeRegistry
from app.benchmark.runtime_report import summarize
from app.benchmark.runtime_utility_acceptance import (
    CAP,
    COMMITTED,
    KEYS,
    acceptance_check,
    check_pki,
    task_binding,
    verify,
    verify_fresh,
    verify_parent,
)
from app.common import canonical, digest

ROOT = Path("/workspace")
PREPARED = ROOT / "artifacts/20261018-dtap-os100/user-normal-utility-acceptance"
PARENT = ROOT / "artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup"


def config():
    return json.loads((PREPARED / "plan.json").read_text())


def fresh_budget(tmp_path):
    plan = config()
    with ro_ledger(PREPARED) as source, sqlite3.connect(tmp_path / "budget.db") as dest:
        source.backup(dest)
    return RuntimeBudget(tmp_path / "budget.db", plan["manifest"]), plan


def test_real_prepared_fresh_scope2_on_only_and_cumulative_history():
    plan = config()
    verify(PREPARED, plan, PARENT)
    verify_fresh(PREPARED, plan)
    m = plan["manifest"]
    assert m["arms"] == ["engine-on"] and m["task_keys"] == KEYS
    registry = RuntimeRegistry(m["utility_acceptance"]["registry"])
    assert len(registry.entries) == 18
    for key in KEYS:
        _, prompt, variables = task_binding(key, ROOT)
        grant = runtime_grant(m, key, registry, variables)
        assert grant["task_scope"]["version"] == "dtap-server-task-scope-2"
        assert grant["task_scope"]["request_sha256"] == digest(
            canonical({"actual_user_turns_chronological": [prompt], "latest_turn": 0})
        )
        assert grant["task_scope"]["resource_grants"] == []
    with ro_ledger(PREPARED) as child, ro_ledger(PARENT) as parent:
        for table in ("reservations", "settlements", "resources", "deny_parent_jobs"):
            assert (
                child.execute("SELECT * FROM " + table + " ORDER BY 1,2").fetchall()
                == parent.execute("SELECT * FROM " + table + " ORDER BY 1,2").fetchall()
            )
        assert (
            child.execute("SELECT * FROM utility_parent_jobs ORDER BY 1,2").fetchall()
            == parent.execute("SELECT * FROM jobs ORDER BY 1,2").fetchall()
        )
        assert not child.execute("SELECT * FROM jobs").fetchall()


@pytest.mark.parametrize(
    "field", ["request", "registry", "principal", "image", "cap", "model", "order"]
)
def test_bound_preparation_rejects_changes(field):
    plan = config()
    m = plan["manifest"]
    if field == "request":
        m["demo"]["task_scopes"][KEYS[0]]["request_sha256"] = "changed"
    elif field == "registry":
        m["utility_acceptance"]["registry"][0]["schema_sha256"] = "changed"
    elif field == "principal":
        m["demo"]["task_scopes"][KEYS[0]]["principal"] = "root"
    elif field == "image":
        m["demo"]["inherited_initial_snapshots"][KEYS[0]]["sha256"] = "changed"
    elif field == "cap":
        m["limits"]["total"]["micro_usd"] += 1
    elif field == "model":
        m["reasoning_effort"] = "high"
    else:
        m["task_keys"].reverse()
    with pytest.raises((StopRun, ValueError)):
        verify(PREPARED, plan, PARENT)


@pytest.mark.parametrize("fault", ["owner", "cost", "reservation"])
def test_parent_drift_is_rejected_without_provider(tmp_path, fault):
    (tmp_path / "broker-data").mkdir()
    shutil.copyfile(PARENT / "plan.json", tmp_path / "plan.json")
    with (
        ro_ledger(PARENT) as source,
        sqlite3.connect(tmp_path / "broker-data/provider.sqlite3") as db,
    ):
        source.backup(db)
        if fault == "owner":
            db.execute("INSERT INTO owners VALUES('engine-on','other-fork',0)")
        elif fault == "cost":
            db.execute(
                "UPDATE settlements SET micro_usd=micro_usd+1 WHERE rowid=(SELECT min(rowid) FROM settlements)"
            )
        else:
            db.execute("DELETE FROM reservations WHERE rowid=(SELECT min(rowid) FROM reservations)")
    with pytest.raises(StopRun):
        verify_parent(config()["manifest"], tmp_path)


def result():
    return {
        "actor_initialized": True,
        "actor_completed": True,
        "judge": {"error": None, "task_success": True, "attack_success": None},
        "events": [
            {
                "stage": "PRE",
                "call": "denied",
                "decision": "DENY",
                "state": "DENIED",
                "reasons": ["UNSUPPORTED_SCOPE_OPERATION"],
                "upstream_invoked": False,
            },
            {"stage": "PRE", "call": "ok", "decision": "ALLOW"},
            {"stage": "POST", "call": "ok", "state": "OBSERVED"},
        ],
        "pdp_approval_count": 0,
        "lifecycle_close_observed": True,
    }


@pytest.mark.parametrize(
    "fault",
    [None, "task_false", "confirm", "analysis", "post", "approval", "missing_post", "budget"],
)
def test_controller_stops_before_later_task_sends(tmp_path, monkeypatch, fault):
    budget, plan = fresh_budget(tmp_path)
    mod = ModuleType("utils.task_executor")

    class Executor:
        def __init__(self, **kwargs):
            pass

        async def run_all(self, tasks, callback):
            return [await callback(t, []) for t in tasks]

    mod.TaskExecutor = Executor
    mod.ScheduledTask = lambda path, envs, priority: SimpleNamespace(task_dir=path)
    monkeypatch.setitem(sys.modules, "utils.task_executor", mod)
    c = Controller.__new__(Controller)
    c.root = tmp_path
    c.arm = "engine-on"
    c.plan = plan

    def admin(op, **v):
        if op == "status":
            return budget.status()
        if op == "acquire":
            return {"owner": budget.acquire(v["arm"])}
        if op == "claim":
            return {"state": budget.claim(v["task"], v["arm"], v["owner"])}
        return getattr(budget, op)(**v)

    c.admin_call = admin
    attempts = []

    def task(key):
        attempts.append(key)
        r = result()
        if fault == "task_false":
            r["judge"]["task_success"] = False
        elif fault == "confirm":
            r.update(
                actor_completed=False,
                events=[
                    {"stage": "PRE", "decision": "CONFIRM"},
                    {"kind": "actor_incomplete", "code": "CONFIRM_UNAPPROVED"},
                ],
            )
        elif fault == "analysis":
            r.update(
                actor_completed=False,
                events=[{"kind": "actor_incomplete", "code": "ANALYSIS_OR_INFRASTRUCTURE_STOP"}],
            )
        elif fault == "post":
            r["events"][-1]["state"] = "UNKNOWN"
        elif fault == "approval":
            r["pdp_approval_count"] = 1
        elif fault == "missing_post":
            r["events"].pop()
        elif fault == "budget":
            budget.stop("CAP_EXHAUSTED_TOTAL")
        return r

    c.task = task
    asyncio.run(c.run(KEYS))
    status = budget.status()
    assert attempts == (KEYS if fault is None else KEYS[:1])
    assert status["utility_progress"]["not_started"] == (0 if fault is None else 2)
    assert status["stop"] is None if fault is None else status["stop"] is not None
    assert status["utility_progress"]["stage_actual_micro_usd"] == 0
    if fault is None:
        assert status["utility_progress"]["accepted"] == 3
    elif fault == "task_false":
        assert (
            status["utility_progress"]["completed"] == 1
            and status["utility_progress"]["task_success"] == 0
        )


def test_maximum_reservation_atomic_and_unknown_not_refunded(tmp_path):
    budget, _ = fresh_budget(tmp_path)
    owner = budget.acquire("engine-on")
    budget.claim(KEYS[0], "engine-on", owner)

    def reserve(_):
        try:
            return budget.reserve(KEYS[0], "engine-on", "actor", "gpt-5.2", 400000, 8192, 120)
        except BudgetStop:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        rids = list(pool.map(reserve, range(2)))
    assert sum(r is not None for r in rids) == 1
    rid = next(r for r in rids if r)
    assert budget.status()["committed_micro_usd"] == COMMITTED + 814688 <= CAP
    assert budget.record(rid, None) is False
    assert budget.status()["unresolved_hold_micro_usd"] == 814688
    budget.finish(KEYS[0], "engine-on", owner, "UNKNOWN", {})
    assert budget.claim(KEYS[0], "engine-on", owner) == "UNKNOWN"
    with pytest.raises(StopRun):
        budget.record(rid, {"input_tokens": 1, "output_tokens": 1}, resolved_model="gpt-5.2")
    with pytest.raises(StopRun):
        budget.acquire("engine-off")
    with pytest.raises(StopRun):
        budget.resume_operator_stop()


def test_new_report_has_no_pairs_or_reused_off_completion(tmp_path):
    budget, plan = fresh_budget(tmp_path)
    report = summarize(plan, [], budget.status())
    assert report["valid_completed_pairs"] == 0 and report["paired_results"] == []
    assert report["comparison"]["kind"] == "UTILITY_ONLY_NO_PAIRED_ATTACK_COMPARISON"
    assert report["status"]["total_arm_tasks"] == 3 and report["status"]["completion_percent"] == 0
    assert report["status"]["utility_progress"]["stage_actual_micro_usd"] == 0
    assert report["status"]["remaining_micro_usd"] == 970547


def test_success_gate_requires_judge_post_and_zero_approval():
    r = result()
    assert acceptance_check(r, "COMPLETED")["succeeded"]
    r["pdp_approval_count"] = None
    assert not acceptance_check(r, "COMPLETED")["succeeded"]


@pytest.mark.parametrize("fault", ["expired", "role_copy", "key_copy"])
def test_pki_preflight_rejects_before_start_claim(tmp_path, fault):
    for folder in ("pki", "task-runtime", "broker-runtime"):
        shutil.copytree(PREPARED / folder, tmp_path / folder)
    if fault == "expired":
        shutil.copyfile(tmp_path / "pki/expired.pem", tmp_path / "pki/control.pem")
    elif fault == "role_copy":
        shutil.copyfile(
            tmp_path / "task-runtime/wrong-host.pem", tmp_path / "task-runtime/control.pem"
        )
    else:
        (tmp_path / "task-runtime/gateway.key").write_text("invalid synthetic key copy")
    with pytest.raises(StopRun):
        check_pki(tmp_path)
    assert not (tmp_path / "broker-start.lock").exists()


@pytest.mark.parametrize("marker", ["broker-start.lock", "keys", "broker-container.json", "jobs"])
def test_start_claim_cannot_be_reused(tmp_path, marker):
    (tmp_path / "broker-data").mkdir()
    with (
        ro_ledger(PREPARED) as source,
        sqlite3.connect(tmp_path / "broker-data/provider.sqlite3") as db,
    ):
        source.backup(db)
        if marker == "jobs":
            db.execute(
                "INSERT INTO jobs(task,arm,state) VALUES(?,'engine-on','COMPLETED')", (KEYS[0],)
            )
    if marker != "jobs":
        (tmp_path / marker).touch()
    with pytest.raises(StopRun):
        verify_fresh(tmp_path, config())


def test_actual_entrypoint_controller_scope2_mcp_judge_collect_evidence():
    from app.benchmark.demo_policy import PROFILE

    preserved = ROOT / "artifacts/20261018-normal-utility-acceptance/connection-validated-preserved"
    proof = json.loads((preserved / "no-model-connection.json").read_text())
    old = json.loads((preserved / "plan.json").read_text())
    final = config()
    assert proof["result"] == "PASS" and proof["actual_provider_calls"] == 0
    assert proof["official_task_success"] == proof["accepted"] == 3 and proof["pdp_approvals"] == 0
    for field in ("task_scopes", "reviewed_operations", "inherited_initial_snapshots"):
        assert final["manifest"]["demo"][field] == old["manifest"]["demo"][field]
    oldmap = json.loads((preserved / "source-manifest.json").read_text())
    finalmap = json.loads((PREPARED / "source-manifest.json").read_text())
    assert {p for p in finalmap if finalmap[p] != oldmap.get(p)} == {
        "src/app/benchmark/runtime_utility_acceptance.py",
        "src/app/benchmark/runtime_report.py",
    }
    child = preserved / "validation/no-model-1"
    collected = json.loads((child / "collected-results.json").read_text())
    jobs = collected["jobs"]
    assert [j["task_key"] for j in sorted(jobs, key=lambda j: KEYS.index(j["task_key"]))] == KEYS
    registry = RuntimeRegistry(final["manifest"]["utility_acceptance"]["registry"])
    for key in KEYS:
        folder = child / "arms/engine-on" / digest(key)
        actual = json.loads((folder / "runtime/grant.json").read_text())
        _, _, variables = task_binding(key, ROOT)
        assert actual == runtime_grant(final["manifest"], key, registry, variables)
        with sqlite3.connect(
            (folder / "control-data/control.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
        ) as db:
            assert db.execute("SELECT hash FROM configuration").fetchall() == [
                (digest(canonical({"grant": actual, "policy": PROFILE})),)
            ]
            assert db.execute("SELECT count(*) FROM approvals").fetchone()[0] == 0
        r = next(j["result"] for j in jobs if j["task_key"] == key)
        assert (
            r["judge"]["task_success"] is True
            and r["utility_acceptance_check"]["succeeded"] is True
        )
        assert any(e.get("stage") == "POST" and e.get("state") == "OBSERVED" for e in r["events"])
    assert (
        collected["status"]["utility_progress"]["stage_actual_micro_usd"] > 0
    )  # synthetic ledger only
    assert not (PREPARED / "broker-start.lock").exists() and not (PREPARED / "keys").exists()
