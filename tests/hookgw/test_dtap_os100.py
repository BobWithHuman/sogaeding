"""OS cohort reporting and Windows-hosted sandbox boundary checks."""

import json
import os
from types import SimpleNamespace

import pytest

from app.benchmark.runtime_controller import Controller, close_active_connection, private_tree
from app.benchmark.runtime_report import summarize


def test_partial_os_cohort_cannot_claim_final_defense_win():
    plan = {
        "manifest": {
            "arms": ["engine-off", "engine-on"],
            "mode": "LIVE",
            "source_commit": "pinned",
            "target_total": 100,
            "runtime_ready": 100,
        },
        "coverage": [{"task_key": f"case/{i}", "threat_model": "indirect"} for i in range(100)],
    }
    jobs = [
        {
            "task_key": "case/0",
            "arm": "engine-off",
            "state": "COMPLETED",
            "result": {
                "initial_snapshot": {"image": "same"},
                "judge": {"attack_success": True, "task_success": True},
                "events": [],
            },
        },
        {
            "task_key": "case/0",
            "arm": "engine-on",
            "state": "COMPLETED",
            "result": {
                "initial_snapshot": {"image": "same"},
                "judge": {"attack_success": False, "task_success": True},
                "events": [{"stage": "PRE", "decision": "DENY"}],
            },
        },
        {"task_key": "case/1", "arm": "engine-off", "state": "UNKNOWN", "result": None},
    ]
    report = summarize(plan, jobs, {"stop": None})
    assert report["comparison"]["valid_completed_pairs"] == 1
    assert report["comparison"]["paired_reduction_count"] == 1
    assert report["comparison"]["final_asr_reportable"] is False
    assert report["comparison"]["normal_false_positive_rate"] == "NOT_EVALUATED_NO_BENIGN_TASKS"
    on = next(
        g for g in report["groups"] if g["arm"] == "engine-on" and g["threat_model"] == "indirect"
    )
    assert on["states"] == {"COMPLETED": 1, "NOT_STARTED": 99}
    assert on["observed_semantic_deny_tasks"] == 1
    assert on["completed_attack_success"] == 0


def test_windows_acl_fallback_requires_explicit_launcher_marker(tmp_path, monkeypatch):
    leaf = tmp_path / "worker-owned.txt"
    leaf.write_text("public evidence")

    def denied(*_args):
        raise PermissionError("Docker Desktop NTFS ownership")

    monkeypatch.setattr(os, "chown", denied)
    monkeypatch.delenv("DTAP_WINDOWS_HOST_ACL", raising=False)
    with pytest.raises(PermissionError):
        private_tree(tmp_path)
    monkeypatch.setenv("DTAP_WINDOWS_HOST_ACL", "1")
    private_tree(tmp_path)
    assert leaf.read_text() == "public evidence"


def test_failed_container_cleanup_is_recorded_and_not_silent(tmp_path):
    controller = Controller.__new__(Controller)
    controller.created = ["failed-container", "removed-container"]
    controller.sandbox = SimpleNamespace(
        logs=lambda _cid: b"safe log",
        remove=lambda cid: (
            (_ for _ in ()).throw(OSError("simulated removal failure"))
            if cid == "failed-container"
            else None
        ),
    )
    with pytest.raises(RuntimeError, match="CONTAINER_CLEANUP_FAILED"):
        controller.cleanup_created(tmp_path, "environment")
    evidence = json.loads((tmp_path / "cleanup-failures.json").read_text())
    assert evidence == [{"container_id": "failed-container", "error": "OSError"}]
    assert controller.created == ["failed-container"]


def test_second_arm_waits_for_slow_but_successful_shared_seed(tmp_path, monkeypatch):
    from app.common import digest

    controller = Controller.__new__(Controller)
    controller.root = tmp_path
    key = "os-filesystem/malicious/indirect/consent-violations/1"
    folder = tmp_path / "snapshots" / digest(key)
    folder.mkdir(parents=True)
    (folder / "seed.lock").write_text("winner owns setup")
    calls = 0

    def advance(_seconds):
        nonlocal calls
        calls += 1
        if calls == 181:
            (folder / "snapshot.json").write_text('{"image":"paired-image"}')

    monkeypatch.setattr("app.benchmark.runtime_controller.time.sleep", advance)
    assert controller.initial_snapshot(key) == {"image": "paired-image"}
    assert calls == 181


@pytest.mark.parametrize("status,expected", [(200, True), (503, False)])
def test_required_engine_close_records_observed_status(tmp_path, monkeypatch, status, expected):
    out, data, runtime = (tmp_path / name for name in ("out", "data", "runtime"))
    for path in (out, data, runtime):
        path.mkdir()
    (data / "active-connection.json").write_text('{"session_id":"test"}')
    (runtime / "machine.token").write_text("test")
    monkeypatch.setattr(
        "app.benchmark.runtime_controller.ssl.create_default_context", lambda **_kw: None
    )

    class Client:
        def __init__(self, **_kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def post(self, *_args, **_kw):
            return SimpleNamespace(status_code=status)

    monkeypatch.setattr("app.benchmark.runtime_controller.httpx.Client", Client)
    assert close_active_connection(out, data, runtime) is expected
    assert json.loads((out / "controller-close.json").read_text()) == {
        "http_status": status,
        "observed": expected,
    }
