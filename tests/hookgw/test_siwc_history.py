"""Transport continuation uses existing UNKNOWN rows, not a retry queue."""

import copy
import json
from pathlib import Path

import pytest
from test_dtap_runtime import manifest

from app.benchmark.login_history import PARENT, SNAPSHOT, read_history, seed_history, verify_history
from app.benchmark.runtime_budget import BudgetStop, RuntimeBudget, StopRun
from app.benchmark.siwc_transport import PlanMeter
from app.common import canonical, digest


@pytest.fixture
def history():
    return read_history(Path(__file__).resolve().parents[2])


@pytest.fixture
def prepared(tmp_path, monkeypatch, history):
    monkeypatch.setattr("app.benchmark.runtime_login.verify_parent", lambda *args: None)
    m = manifest()
    m["actor_model"] = "gpt-5.6-luna"
    unknown = history["tables"]["jobs"]["rows"][0][0]
    m["task_keys"] = [unknown, "task"]
    m["chatgpt_plan"] = {
        "limits": {
            "requests": 6,
            "per_arm_requests": 5,
            "per_task_requests": 4,
            "seconds": 2000,
            "per_task_seconds": 100,
        }
    }
    b = RuntimeBudget(tmp_path / "provider.sqlite3", m)
    with b.db() as db:
        baseline = seed_history(db, history)
        m["chatgpt_plan"]["transport_history"] = {
            "parent_manifest_sha256": PARENT,
            "snapshot_sha256": SNAPSHOT,
            "rows": baseline,
        }
        db.execute("UPDATE binding SET hash=?", (digest(canonical(m)),))
    return RuntimeBudget(tmp_path / "provider.sqlite3", m), unknown


def test_history_contains_live_success_and_unresolved_usage(history):
    rows = history["tables"]["plan_requests"]["rows"]
    assert len(rows) == 5
    assert sum(r[5] == "UNKNOWN" for r in rows) == 4
    assert [json.loads(r[7]) for r in rows if r[7]] == [{"input_tokens": 12, "output_tokens": 5}]
    assert history["diagnostics"][0]["actual_send"] == "UNKNOWN_0_OR_1"


@pytest.mark.parametrize("arm", ["engine-off", "engine-on"])
def test_inherited_unknown_is_skipped_and_next_task_can_start(prepared, arm):
    b, unknown = prepared
    owner = b.acquire(arm)
    assert b.claim(unknown, arm, owner) == "UNKNOWN"
    assert b.claim("task", arm, owner) == "NEW"
    with b.db() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM jobs WHERE task=? AND arm=?", (unknown, arm)
            ).fetchone()[0]
            == 1
        )
    status = b.status()["chatgpt_plan_usage"]
    assert status["requests"] == 5 and status["unresolved_plan_requests"] == 4


def test_probe_and_unknown_requests_consume_shared_plan_cap(prepared):
    b, _ = prepared
    owner = b.acquire("engine-on")
    b.claim("task", "engine-on", owner)
    meter = PlanMeter(b)
    job = {"task": "task", "arm": "engine-on", "provider": "actor"}
    rid = meter.reserve(job, 10)
    meter.record(rid)
    with pytest.raises(BudgetStop, match="CAP_EXHAUSTED_CHATGPT_PLAN"):
        meter.reserve(job, 10)
    assert b.status()["committed_micro_usd"] == 0


@pytest.mark.parametrize("table", ["jobs", "plan_requests", "plan_account", "resources"])
def test_inherited_row_tampering_prevents_any_new_claim(prepared, table):
    b, _ = prepared
    with b.db() as db:
        db.execute("DELETE FROM " + table)
    with pytest.raises(StopRun, match="SIWC_HISTORY_RECORD_CHANGED"):
        b.acquire("engine-on")


def test_history_manifest_cannot_rebind_parent(prepared):
    b, _ = prepared
    changed = copy.deepcopy(b.manifest)
    changed["chatgpt_plan"]["transport_history"]["parent_manifest_sha256"] = "0" * 64
    with b.db() as db, pytest.raises(StopRun, match="SIWC_HISTORY_BINDING_CHANGED"):
        verify_history(db, changed)
