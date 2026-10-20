"""Real failed-run copies only; never touch its ledger or contact providers."""

import copy
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_functional import verify_rows as verify_functional
from app.benchmark.runtime_functional_continuation import (
    diagnostic_receipt,
    seed,
    validate_parent,
    verify_rows,
)
from app.benchmark.siwc_transport import PlanMeter
from app.common import canonical, digest

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "artifacts/20261018-dtap-os100/user-functional-os100-1"
PROBE_ROOT = PROJECT / "artifacts/20261020-functional-stream-failure"


@pytest.fixture
def predecessor(tmp_path, monkeypatch):
    monkeypatch.setattr("app.benchmark.runtime_login.verify_parent", lambda *a: None)
    manifest = json.loads((ROOT / "plan.json").read_text())["manifest"]
    dbfile = tmp_path / "provider.sqlite3"
    shutil.copyfile(ROOT / "broker-data/provider.sqlite3", dbfile)
    return dbfile, manifest


@pytest.fixture
def successor(predecessor):
    dbfile, manifest = predecessor
    with sqlite3.connect(dbfile) as db:
        account = db.execute("SELECT binding FROM plan_account").fetchone()[0]
        raw, receipt = diagnostic_receipt(PROBE_ROOT, account)
        seed(db, manifest, raw, receipt)
        db.execute("UPDATE binding SET hash=?", (digest(canonical(manifest)),))
    return RuntimeBudget(dbfile, manifest)


def test_copy_preserves_terminal_jobs_unknowns_cost_and_counts_diagnostic(successor):
    b = successor
    with b.db() as db:
        verify_functional(db, b.manifest)
        assert db.execute("SELECT count(*) FROM jobs").fetchone() == (7,)
        assert db.execute("SELECT count(*) FROM jobs WHERE state='UNKNOWN'").fetchone() == (6,)
        assert db.execute("SELECT code FROM stream_parent_stops").fetchone() == (
            "SIWC_STREAM_NOT_COMPLETED_UNKNOWN",
        )
        assert db.execute("SELECT 1 FROM stops").fetchone() is None
    status = b.status()
    assert status["not_started_arm_tasks"] == 193
    assert status["chatgpt_plan_usage"]["requests"] == 131
    assert status["chatgpt_plan_usage"]["standalone_diagnostic_requests"] == 1
    assert status["chatgpt_plan_usage"]["unresolved_plan_requests"] == 5
    assert status["committed_micro_usd"] == 4190921
    assert status["remaining_micro_usd"] == 898373


def test_terminal_jobs_never_claimed_again_and_unstarted_can_run(successor):
    b = successor
    owner = b.acquire("engine-off")
    with b.db() as db:
        task = db.execute("SELECT task FROM jobs WHERE arm='engine-off' LIMIT 1").fetchone()[0]
    assert b.claim(task, "engine-off", owner) == "UNKNOWN"
    fresh = next(k for k in b.manifest["task_keys"] if k != task and k.endswith("/12"))
    assert b.claim(fresh, "engine-off", owner) == "NEW"


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM jobs WHERE state='UNKNOWN'",
        "UPDATE jobs SET state='INCOMPLETE' WHERE state='CONFIRM_UNAPPROVED'",
        "DELETE FROM stream_parent_stops",
        "DELETE FROM plan_requests WHERE role='diagnostic'",
        "UPDATE plan_requests SET usage='{}' WHERE role='diagnostic'",
        "DELETE FROM plan_stream_observations",
        "DELETE FROM settlements",
    ],
)
def test_missing_or_changed_prior_rows_prevent_new_provider_or_task(successor, sql):
    b = successor
    with b.db() as db:
        db.execute(sql)
    with pytest.raises(StopRun):
        b.acquire("engine-on")


def test_original_parent_active_or_changed_stop_rejected_before_copy(predecessor):
    dbfile, manifest = predecessor
    with sqlite3.connect(dbfile) as db:
        validate_parent(db, manifest)
        db.execute("UPDATE stops SET code='changed'")
        with pytest.raises(StopRun, match="PARENT_STATE_CHANGED"):
            validate_parent(db, manifest)


def test_external_diagnostic_counts_against_global_plan_cap(successor):
    b = successor
    b.manifest["chatgpt_plan"]["limits"]["requests"] = 131
    b.binding = digest(canonical(b.manifest))
    owner = b.acquire("engine-on")
    task = next(k for k in b.manifest["task_keys"] if k.endswith("/12"))
    b.claim(task, "engine-on", owner)
    with pytest.raises(StopRun, match="CAP_EXHAUSTED_CHATGPT_PLAN"):
        PlanMeter(b).reserve({"task": task, "arm": "engine-on", "provider": "actor"}, 120)


def test_new_stream_failure_still_stops_every_arm(successor):
    successor.stop("SIWC_STREAM_NOT_COMPLETED_UNKNOWN")
    with pytest.raises(StopRun, match="SIWC_STREAM_NOT_COMPLETED_UNKNOWN"):
        successor.acquire("engine-off")
    with pytest.raises(StopRun, match="SIWC_STREAM_NOT_COMPLETED_UNKNOWN"):
        successor.acquire("engine-on")


def test_partial_parent_table_or_rebound_diagnostic_cannot_change_history(successor):
    m = copy.deepcopy(successor.manifest)
    m["stream_continuation"]["parent_rows"].pop("jobs")
    with successor.db() as db:
        with pytest.raises(StopRun):
            verify_rows(db, m)


def test_receipt_requires_completed_no_effect_same_account(tmp_path, predecessor):
    dbfile, _ = predecessor
    with sqlite3.connect(dbfile) as db:
        account = db.execute("SELECT binding FROM plan_account").fetchone()[0]
    shutil.copytree(PROBE_ROOT / "bundle", tmp_path / "bundle")
    shutil.copytree(
        PROBE_ROOT / "user-one-permission-request", tmp_path / "user-one-permission-request"
    )
    path = tmp_path / "user-one-permission-request/result.json"
    result = json.loads(path.read_text())
    result["decision_applied"] = True
    path.write_text(canonical(result))
    with pytest.raises(StopRun, match="DIAGNOSTIC_RECEIPT_INVALID"):
        diagnostic_receipt(tmp_path, account)
    assert hashlib.sha256(
        (PROBE_ROOT / "user-one-permission-request/result.json").read_bytes()
    ).hexdigest()


def test_public_receipt_must_match_exact_trusted_original_bytes(tmp_path, predecessor):
    dbfile, _ = predecessor
    with sqlite3.connect(dbfile) as db:
        account = db.execute("SELECT binding FROM plan_account").fetchone()[0]
    original = (PROBE_ROOT / "user-one-permission-request/result.json").read_bytes()
    replacement = tmp_path / "receipt.json"
    # Same valid JSON/usage/flags; even invisible byte changes are untrusted.
    replacement.write_bytes(original + b"\n")
    with pytest.raises(StopRun, match="DIAGNOSTIC_RECEIPT_INVALID"):
        diagnostic_receipt(PROBE_ROOT, account, public_receipt=replacement)
