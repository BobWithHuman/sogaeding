"""Core fixed engine acceptance sequencing, no model/real key/actual CLI."""
import hashlib
import json
import shutil
import sqlite3
from types import SimpleNamespace

import pytest
from test_v5_demo_integration import PROJECT, followup
from test_v5_demo_integration import legacy_prepared as legacy_prepared


@pytest.fixture
def core(legacy_prepared, monkeypatch):
    b, root, _, _, _ = legacy_prepared
    f = followup()
    for name in ("tools/mvp_semantic_followup.py", "tools/mvp_confirm.py", "scripts/mvp_confirm.ps1", "tools/mvp_demo_probe.py", "compose.mvp-demo.core-auto-v5p1.yaml"):
        shutil.copyfile(PROJECT / name, root / name)
    compose = b.compose
    monkeypatch.setattr(f, "base", lambda _: b)
    parent = {"historical_requests": 25, "historical_input_reserved": 1600000, "historical_cli_starts": 4}
    monkeypatch.setattr(f, "core_parent", lambda *_: parent.copy())
    risk = {"source_path": "docs/review.md", "candidate": {"tool": "write_file", "route": "mcp", "args": {"path": "reports/review.md", "content": "false report"}}}
    monkeypatch.setattr(f, "core_risk_spec", lambda *_: risk.copy())
    monkeypatch.setattr(f, "behavior_compose", lambda project, base, args, image=None, timeout=60: compose(project, args, image, timeout))
    configured = f.behavior_base(root, True)
    monkeypatch.setattr(f, "behavior_base", lambda *args: configured)
    report = f.behavior_prepare(root, True)
    directory = b.runtime(root)
    assert report["status"] == "CORE_AUTO_PREPARED"
    sent = []
    usage = {"requests_attempted": 2, "input_reserved": 128000, "usage_complete": True}
    monkeypatch.setattr(b, "provider_summary", lambda _: usage.copy())
    def fixed(*args):
        sent.append(args)
        usage.update(requests_attempted=4, input_reserved=256000)
        return {"denied": True, "forbidden_effect": 0, "upstream_write_delta": 0}
    helper = b.helper
    monkeypatch.setattr(b, "helper", lambda project, name: SimpleNamespace(fixed_engine_block=fixed) if name == "mvp_demo_probe" else helper(project, name))
    monkeypatch.setattr(b, "read_local", lambda host, path, **kw: {"decision_policy": b.DECISION_POLICY, "judge_mode": "JEV_USER_LIVE"} if path == "/health" else {"calls": [], "truncated": True})
    monkeypatch.setattr(b, "upstream_summary", lambda _: {"attempts": 2, "observed": 2, "unknown": 0})
    b.write_new(directory / "episodes/episode-5.claim", {"manifest_sha256": report["manifest_sha256"]})
    events = directory / "episodes/events/episode-5"
    events.mkdir(parents=True)
    b.write_new(events / "finish.json", {"outcome": "EXITED", "exit_code": 0, "tree_cleanup": "VERIFIED", "connection_closed": "VERIFIED", "manifest_sha256": report["manifest_sha256"]})
    (directory / "workspace/reports/normal.md").write_text("Factual normal report")
    with sqlite3.connect(directory / "control-data/control.sqlite3") as db:
        db.execute("CREATE TABLE approvals (id TEXT)")
        db.execute("CREATE TABLE connections (id TEXT)")
        db.execute("CREATE TABLE turns (session TEXT,id TEXT,hash TEXT)")
        db.execute("INSERT INTO turns VALUES ('session','turn',?)", (hashlib.sha256(f.core_normal_spec()["user_request"].encode()).hexdigest(),))
        db.execute("CREATE TABLE calls (id TEXT,session TEXT,turn TEXT,hash TEXT,path TEXT,state TEXT,decision TEXT,reason TEXT,created REAL)")
        db.execute("CREATE TABLE demo_rpc_bindings (call TEXT,rpc_hash TEXT)")
    with sqlite3.connect(directory / "ledger/typesafe-budget.sqlite3") as db:
        db.execute("CREATE TABLE jev_attempts (analysis_id TEXT,view TEXT,status TEXT,input_reserved INTEGER)")
        db.executemany("INSERT INTO jev_attempts VALUES ('analysis',?,'COMPLETED',64000)", [("A",),("B",)])
    with sqlite3.connect(directory / "upstream-data/attempts.sqlite3") as db:
        db.execute("CREATE TABLE attempts (call TEXT,hash TEXT,state TEXT,at REAL)")
    (directory / "config/policy.json").write_text(b.canonical(b.policy(True)))
    approvals = dict(confirm_send=True, manifest_sha256=report["manifest_sha256"], requests=4, input_limit=256000,
        additional_starts=1, total_starts=5, cumulative_requests=29, cumulative_input=1856000, demo_requests=24, demo_input=1536000, wall_seconds=1800)
    result = f, b, root, directory, approvals, usage, sent
    normal_calls(result)
    return result


def normal_calls(core, four=False, pre_success=False):
    f, _, _, directory, _, _, _ = core
    request = f.core_digest({"actual_user_turns_chronological": [f.core_normal_spec()["user_request"]], "latest_turn": 0})
    content = (directory / "workspace/reports/normal.md").read_text()
    sequence = [("read_file", {"path":"docs/release.md"}, "OBSERVED")]
    if four:
        sequence.append(("read_file", {"path":"reports/normal.md"}, "OBSERVED" if pre_success else "OBSERVED_ERROR"))
    sequence.append(("write_file", {"path":"reports/normal.md","content":content}, "OBSERVED"))
    if four:
        sequence.append(("read_file", {"path":"reports/normal.md"}, "OBSERVED"))
    with sqlite3.connect(directory / "control-data/control.sqlite3") as db, sqlite3.connect(directory / "upstream-data/attempts.sqlite3") as upstream:
        db.execute("DELETE FROM calls")
        db.execute("DELETE FROM demo_rpc_bindings")
        upstream.execute("DELETE FROM attempts")
        for index, (tool, args, state) in enumerate(sequence):
            call = str(index)
            action = f.core_digest({"route":"mcp","tool":tool,"args":args})
            context = {"policy":"hookgw-2026-10-17-jev-v5p1", "action_hash":action,"request_hash":request}
            if state == "OBSERVED_ERROR":
                context["execution_error"] = {"version":"file-error-1","code":"FILE_NOT_FOUND","operation":"READ","effect":"NO_WRITE"}
            db.execute("INSERT INTO calls VALUES (?,'session','turn',?,'mcp',?,'ALLOW',?,?)", (call, action, state, json.dumps(context), index*2))
            db.execute("INSERT INTO demo_rpc_bindings VALUES (?,?)", (call, f.core_digest("canonical-rpc-"+call)))
            upstream.execute("INSERT INTO attempts VALUES (?,?,?,?)", (call,f.core_digest("raw-http-"+call),state,index*2+1))


def test_core_reuses_launcher_separate_runtime_and_fixed_test_once(core):
    f, b, root, directory, approvals, usage, sent = core
    assert b.EPISODE_START == 5 and b.REVISION == "core-auto-v5p1"
    assert b.CONTROL_URL.endswith(":8037") and b.GATEWAY_URL.endswith(":8047/mcp")
    result = f.core_verify_block(root, **approvals)
    assert result["status"] == "FIXED_RISK_DENY_VERIFIED" and result["normal"]["pdp_approvals"] == 0
    assert len(sent) == 1 and usage["requests_attempted"] == 4
    with pytest.raises(ValueError, match="NO_RETRY"):
        f.core_verify_block(root, **approvals)
    assert len(sent) == 1 and (directory / "verify-block-result.json").exists()


@pytest.mark.parametrize("change", ["human", "confirm", "unknown", "usage", "missing_finish", "forbidden_file", "manifest", "limits"])
def test_normal_failure_or_unapproved_batch_never_sends_risk(core, change):
    f, _, root, directory, approvals, usage, sent = core
    if change in ("human", "confirm", "unknown"):
        with sqlite3.connect(directory / "control-data/control.sqlite3") as db:
            if change == "human":
                db.execute("INSERT INTO approvals VALUES ('human')")
            else:
                db.execute("UPDATE calls SET state=?,decision=?", ("UNKNOWN" if change == "unknown" else "OBSERVED", "CONFIRM"))
    elif change == "usage":
        usage["requests_attempted"] = 3
    elif change == "missing_finish":
        (directory / "episodes/events/episode-5/finish.json").unlink()
    elif change == "forbidden_file":
        (directory / "workspace/reports/review.md").write_text("unexpected")
    elif change == "manifest":
        approvals["manifest_sha256"] = "0" * 64
    else:
        approvals["cumulative_requests"] = 25
    with pytest.raises((ValueError, OSError)):
        f.core_verify_block(root, **approvals)
    assert not sent and not (directory / "verify-block.claim").exists()
