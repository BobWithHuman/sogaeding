"""Completed normal effects and unused risk allowance: no actor/provider."""
import concurrent.futures
import json
import sqlite3

import pytest
from test_core_auto_runner import core as core
from test_core_auto_runner import normal_calls
from test_v5_demo_integration import legacy_prepared as legacy_prepared


@pytest.mark.parametrize("four,pre_success", [(False,False),(True,False),(True,True)])
def test_complete_normal_transcript_accepts_known_reads_even_if_ui_truncated(core, four, pre_success):
    f, b, root, _, _, usage, sent = core
    normal_calls(core, four, pre_success)
    result = f.core_normal_gate(root,b)
    assert result["calls"] == (4 if four else 2)
    assert result["observed_errors"] == int(four and not pre_success)
    assert usage["requests_attempted"] == 2 and not sent


@pytest.mark.parametrize("change", ["extra_write","wrong_target","unknown","error_code","error_effect","error_after_write",
    "error_on_write","error_on_source","turn","request_hash","action_hash","approval","policy","rpc","upstream_id",
    "upstream_order","upstream_result","extra_upstream","extra_rpc","usage_status","usage_analysis","finish","normal_content","source_after_write"])
def test_full_call_and_upstream_mismatches_never_send(core, change):
    f,b,root,directory,approvals,_,sent = core
    normal_calls(core, True)
    with sqlite3.connect(directory / "control-data/control.sqlite3") as db, sqlite3.connect(directory / "upstream-data/attempts.sqlite3") as upstream:
        if change == "extra_write":
            db.execute("INSERT INTO calls SELECT 'extra',session,turn,hash,path,state,decision,reason,created+0.5 FROM calls WHERE id='2'")
        elif change in ("wrong_target","normal_content"):
            if change == "normal_content":
                (directory / "workspace/reports/normal.md").write_text("changed")
            else:
                db.execute("UPDATE calls SET hash=? WHERE id='2'", (f.core_digest({"route":"mcp","tool":"write_file","args":{"path":"reports/review.md","content":"bad"}}),))
        elif change == "unknown":
            db.execute("UPDATE calls SET state='UNKNOWN' WHERE id='3'")
        elif change.startswith("error_"):
            ident = {"error_after_write":"3","error_on_write":"2","error_on_source":"0"}.get(change,"1")
            context = json.loads(db.execute("SELECT reason FROM calls WHERE id=?",(ident,)).fetchone()[0])
            context["execution_error"] = {"version":"file-error-1","code":"FILE_NOT_FOUND","operation":"READ","effect":"NO_WRITE"}
            if change == "error_code":
                context["execution_error"]["code"] = "OTHER"
            if change == "error_effect":
                context["execution_error"]["effect"] = "UNKNOWN"
            db.execute("UPDATE calls SET state='OBSERVED_ERROR',reason=? WHERE id=?",(json.dumps(context),ident))
        elif change == "turn":
            db.execute("UPDATE calls SET turn='other' WHERE id='2'")
        elif change in ("request_hash","action_hash","policy"):
            context = json.loads(db.execute("SELECT reason FROM calls WHERE id='2'").fetchone()[0])
            context[change] = "changed"
            db.execute("UPDATE calls SET reason=? WHERE id='2'",(json.dumps(context),))
        elif change == "approval":
            db.execute("INSERT INTO approvals VALUES ('human')")
        elif change == "rpc":
            db.execute("UPDATE demo_rpc_bindings SET rpc_hash='changed' WHERE call='2'")
        elif change == "upstream_id":
            upstream.execute("UPDATE attempts SET call='other' WHERE call='2'")
        elif change == "upstream_order":
            upstream.execute("UPDATE attempts SET at=100 WHERE call='0'")
        elif change == "upstream_result":
            upstream.execute("UPDATE attempts SET state='OBSERVED' WHERE call='1'")
        elif change == "extra_upstream":
            upstream.execute("INSERT INTO attempts VALUES ('extra','rpc','OBSERVED',99)")
        elif change == "extra_rpc":
            db.execute("INSERT INTO demo_rpc_bindings VALUES ('extra','rpc')")
        elif change == "source_after_write":
            db.execute("UPDATE calls SET created=100 WHERE id='0'")
    if change.startswith("usage_"):
        with sqlite3.connect(directory / "ledger/typesafe-budget.sqlite3") as db:
            if change == "usage_status":
                db.execute("UPDATE jev_attempts SET status='UNKNOWN' WHERE view='B'")
            else:
                db.execute("UPDATE jev_attempts SET analysis_id='other' WHERE view='B'")
    if change == "finish":
        path = directory / "episodes/events/episode-5/finish.json"
        event = json.loads(path.read_text())
        event["tree_cleanup"] = "UNVERIFIED"
        path.write_text(json.dumps(event))
    with pytest.raises((ValueError,OSError)):
        f.core_verify_block(root, **approvals)
    assert not sent and not (directory / "verify-block.claim").exists()


@pytest.fixture
def resumed(core, monkeypatch):
    f,b,root,directory,approvals,_,_ = core
    normal_calls(core,True)
    manifest = json.loads((directory / "manifest.json").read_text())
    monkeypatch.setattr(f,"CORE_ORIGINAL_SHA",b.sha(directory / "manifest.json"))
    monkeypatch.setattr(f,"CORE_RUNNER_BEFORE",{name:manifest["source_hashes"][name] for name in f.CORE_RUNNER_BEFORE})
    normal = f.core_normal_gate(root,b)
    evidence = root/f.CORE_NORMAL_EVIDENCE
    evidence.parent.mkdir(parents=True,exist_ok=True)
    evidence.write_text(json.dumps({"original_manifest_sha256":f.CORE_ORIGINAL_SHA,
        "normal_file":{"bytes":normal["normal_bytes"],"sha256":normal["normal_sha256"]},"provider_usage":normal["usage"],
        "finish":json.loads((directory/"episodes/events/episode-5/finish.json").read_text())}))
    monkeypatch.setattr(f,"CORE_NORMAL_EVIDENCE_SHA",b.sha(evidence))
    for name in f.CORE_RUNNER_BEFORE:
        with (root / name).open("a") as stream:
            stream.write("\n")
    prepared = f.core_resume_prepare(root)
    approvals["resume_manifest_sha256"] = prepared["resume_manifest_sha256"]
    return core,prepared


def test_resume_preserves_original_manifest_and_uses_original_unused_pair(resumed):
    (f,b,root,directory,approvals,usage,sent),prepared = resumed
    original = (directory / "manifest.json").read_bytes()
    result = f.core_verify_block(root,**approvals)
    assert result["status"] == "FIXED_RISK_DENY_VERIFIED" and len(sent)==1
    assert usage["requests_attempted"] == 4
    assert (directory / "manifest.json").read_bytes() == original
    claim = json.loads((directory / "verify-block.claim").read_text())
    assert claim["resume_manifest_sha256"] == prepared["resume_manifest_sha256"]
    # Helpers used after claim retain the original + runner binding.
    assert b.verified(root)["policy"] == b.DECISION_POLICY
    with pytest.raises(ValueError,match="NO_RETRY"):
        f.core_verify_block(root,**approvals)


@pytest.mark.parametrize("change", ["runner","other_source","bundle","document","policy","normal","finish","usage","manifest","resume",
                                   "resume_hash","claim","result","parent","container","evidence"])
def test_resume_drift_rejected_before_claim(resumed, monkeypatch, change):
    (f,b,root,directory,approvals,usage,sent),_ = resumed
    paths = {"runner":root/"tools/mvp_demo.py", "other_source":root/"src/app/fake.py", "bundle":directory/"bundle/manifest.json",
             "document":directory/"workspace/docs/release.md", "policy":directory/"config/policy.json", "normal":directory/"workspace/reports/normal.md",
             "finish":directory/"episodes/events/episode-5/finish.json", "manifest":directory/"manifest.json", "resume":directory/f.CORE_RESUME_FILE}
    if change in paths:
        with paths[change].open("a") as stream:
            stream.write(" ")
    elif change == "evidence":
        with (root/f.CORE_NORMAL_EVIDENCE).open("a") as stream:
            stream.write(" ")
    elif change == "usage":
        usage["requests_attempted"] = 3
    elif change == "resume_hash":
        approvals["resume_manifest_sha256"] = "0"*64
    elif change in ("claim","result"):
        (directory / ("verify-block.claim" if change=="claim" else "verify-block-result.json")).write_text("{}")
    elif change == "parent":
        monkeypatch.setattr(f,"core_parent",lambda *_:{"changed":True})
    else:
        monkeypatch.setattr(f,"core_live_binding",lambda *_: (_ for _ in ()).throw(ValueError("CORE_RESUME_CONTAINER_BINDING_INVALID")))
    with pytest.raises((ValueError,OSError)):
        f.core_verify_block(root,**approvals)
    assert not sent
    assert (directory / "verify-block.claim").exists() == (change=="claim")


def test_resume_concurrency_has_at_most_one_transmission(resumed):
    (f,_,root,directory,approvals,_,sent),_ = resumed
    def invoke():
        try:
            return f.core_verify_block(root,**approvals)
        except (ValueError,OSError):
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _:invoke(),range(2)))
    assert len(sent)==1 and (directory / "verify-block.claim").exists()


def test_probe_error_claim_is_retained_and_never_retried(resumed,monkeypatch):
    (f,b,root,directory,approvals,_,sent),_ = resumed
    helper=b.helper
    def crash(*_):
        sent.append("attempt")
        raise ValueError("PRIVATE-SENTINEL-MUST-NOT-OUTPUT")
    from types import SimpleNamespace
    monkeypatch.setattr(b,"helper",lambda project,name:SimpleNamespace(fixed_engine_block=crash) if name=="mvp_demo_probe" else helper(project,name))
    result=f.core_verify_block(root,**approvals)
    assert result["status"]=="NOT_VERIFIED_OR_UNKNOWN_STOP" and "SENTINEL" not in json.dumps(result)
    with pytest.raises(ValueError,match="NO_RETRY"):
        f.core_verify_block(root,**approvals)
    assert len(sent)==1


@pytest.mark.parametrize("mode",["start","history","inspect"])
def test_resume_argument_rejected_outside_risk_mode_without_raw_error(core,monkeypatch,capsys,mode):
    _,b,_,_,_,_,sent=core
    import sys
    monkeypatch.setattr(sys,"argv",["mvp_demo.py",mode,"--revision","core-auto-v5p1","--resume-manifest-sha256","a"*64])
    with pytest.raises(SystemExit) as error:
        b.main()
    assert error.value.code==2
    value=json.loads(capsys.readouterr().out)
    assert value["code"]=="CORE_RESUME_VERIFY_BLOCK_ONLY" and not sent
