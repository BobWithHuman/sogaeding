"""Check real prepared lineage through temporary ledger copies only."""

import copy
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_functional import verify, verify_parent_ledger, verify_rows
from app.benchmark.runtime_login import check_start

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "artifacts/20261018-dtap-os100/user-functional-os100-1"
PARENT = PROJECT / "artifacts/20261018-dtap-os100/user-chatgpt-login-luna-pair1"


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    monkeypatch.setattr("app.benchmark.runtime_login.verify_parent", lambda *a: None)
    plan = json.loads((ROOT / "plan.json").read_text())
    (tmp_path / "broker-data").mkdir()
    path = tmp_path / "broker-data/provider.sqlite3"
    shutil.copyfile(ROOT / "broker-data/provider.sqlite3", path)
    return tmp_path, plan, RuntimeBudget(path, plan["manifest"])


def test_original100_same_models_caps_and_preserved_unknown(candidate):
    _, plan, b = candidate
    verify(ROOT, plan["manifest"])
    assert len(plan["manifest"]["task_keys"]) == 100
    status = b.status()
    assert status["committed_micro_usd"] == 4190921
    assert status["remaining_micro_usd"] == 898373
    assert status["chatgpt_plan_usage"]["requests"] == 122
    with b.db() as db:
        assert db.execute("SELECT count(*) FROM jobs WHERE state='UNKNOWN'").fetchone() == (4,)
        assert db.execute("SELECT 1 FROM stops").fetchone() is None
        assert db.execute("SELECT 1 FROM resumes").fetchone() is None
        assert db.execute("SELECT 1 FROM budget_rejections").fetchone() is None


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM jobs WHERE state='UNKNOWN'",
        "UPDATE jobs SET state='INCOMPLETE' WHERE state='UNKNOWN'",
        "DELETE FROM settlements",
        "DELETE FROM reservations",
        "DELETE FROM pair_parent_stops",
    ],
)
def test_history_tampering_never_becomes_a_new_baseline(candidate, sql):
    _, _, b = candidate
    with b.db() as db:
        db.execute(sql)
    with pytest.raises(StopRun):
        b.acquire("engine-off")


@pytest.mark.parametrize(
    "sql,match",
    [
        ("UPDATE binding SET hash='changed'", "FUNCTIONAL_PARENT_LEDGER_BINDING_CHANGED"),
        (
            "UPDATE pair_parent_jobs SET state='INCOMPLETE' WHERE state='UNKNOWN'",
            "SIWC_PAIR_HISTORY_RECORD_CHANGED",
        ),
        ("DELETE FROM settlements", "SIWC_PAIR_HISTORY_RECORD_CHANGED"),
    ],
)
def test_parent_drift_rejected_before_backup(tmp_path, sql, match):
    path = tmp_path / "parent.sqlite3"
    shutil.copyfile(PARENT / "broker-data/provider.sqlite3", path)
    manifest = json.loads((PARENT / "plan.json").read_text())["manifest"]
    with sqlite3.connect(path) as db:
        verify_parent_ledger(db, manifest)
        db.execute(sql)
        with pytest.raises(StopRun, match=match):
            verify_parent_ledger(db, manifest)


def test_unstarted_helper_accepts_exact_inherited_unknown_and_rejects_new_job(
    candidate, monkeypatch
):
    root, plan, b = candidate
    monkeypatch.setattr("app.benchmark.runtime_login.verify", lambda *a: None)
    check_start(root, plan)
    with b.db() as db:
        db.execute("INSERT INTO jobs(task,arm,state) VALUES('changed','engine-off','COMPLETED')")
    with pytest.raises(StopRun, match="SIWC_NO_OLD_JOB_REEXECUTION"):
        check_start(root, plan)


def test_new_denial_of_service_cannot_hide_old_unknown(candidate):
    _, plan, b = candidate
    m = copy.deepcopy(plan["manifest"])
    m["functional_routing"]["parent_rows"].pop("pair_parent_jobs")
    with b.db() as db:
        with pytest.raises(StopRun):
            verify_rows(db, m)
