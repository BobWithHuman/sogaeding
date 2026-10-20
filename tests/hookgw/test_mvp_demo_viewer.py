"""Human-only demo projection and hostile text safety, no paid/model operations."""
import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest
from cryptography.fernet import Fernet

from app.common import canonical, digest
from app.transparent.demo_report import excerpt, project, safe_observations, source_excerpt
from app.transparent.engine import Engine
from app.transparent.server import create_app


def viewer():
    spec=importlib.util.spec_from_file_location("demo_viewer",Path(__file__).resolve().parents[2]/"tools/mvp_demo_viewer.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def engine(tmp_path):
    value=Engine(tmp_path/"control.sqlite3",Fernet.generate_key(),{"workspace":"C:\\synthetic", "tools":{"mcp":["read_file","write_file"]},"demo_scope":"SYNTHETIC_REGISTERED_MCP"})
    value.turn("machine","session","turn","배포 사실을 요약해줘. \x1b[31m<script>bad</script>","C:\\synthetic")
    value.register("machine","session","turn","call","write_file",{"path":"reports/normal.md","content":"<img src=x onerror=alert(1)>"},"mcp")
    with value.db() as db:
        db.execute("UPDATE calls SET state='DENIED',decision='DENY',reason=? WHERE id='call'",(canonical({"reasons":["ANALYSIS_UNAVAILABLE"],"source_hash":digest("[]"),"diagnostic":[{"code":"JEV_RESPONSE_INVALID","view":"A","PRIVATE":"SHOULD_NOT_APPEAR"}],"policy_trace":{"view_observations":{"A":[{"question":"task_relation","choice":"DIRECT","probabilities":{"DIRECT":1,"PRIVATE":0},"provider_confidence":1,"computed_confidence":1,"effective_confidence":1,"status":"ACCEPTED","PRIVATE":"SHOULD_NOT_APPEAR"}]}}}),))
    return value


def test_projection_masks_bounds_and_does_not_change_execution_state(engine):
    before=engine.history()
    report=project(engine)
    assert engine.history()==before
    raw=json.dumps(report)
    assert "SHOULD_NOT_APPEAR" not in raw and "PRIVATE" not in raw
    assert report["calls"][0]["decision"]=="DENY"
    assert report["calls"][0]["source_snapshot_verified"] is True
    assert "\x1b" not in report["calls"][0]["request_excerpt"]


def test_demo_endpoint_disabled_by_default_and_human_only(engine,monkeypatch):
    app=create_app(engine,{"machine":"fake-machine","human":"fake-human","machine_id":"machine","ticket":lambda *_:"fake-ticket"})
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="https://local") as client:
            monkeypatch.delenv("HOOKGW_DEMO_VIEWER",raising=False)
            assert (await client.get("/demo/history")).status_code==404
            monkeypatch.setenv("HOOKGW_DEMO_VIEWER","1")
            assert (await client.get("/demo/history",headers={"Authorization":"Bearer fake-machine"})).status_code==403
            response=await client.get("/demo/history",headers={"Authorization":"Bearer fake-human"})
            assert response.status_code==200 and len(response.json()["calls"])==1
    asyncio.run(run())


def test_non_demo_grant_never_projects_existing_history(engine):
    engine.grant.pop("demo_scope")
    assert project(engine)["calls"]==[]


def test_viewer_html_escapes_data_and_does_not_call_error_an_attack_block(engine,tmp_path):
    module=viewer()
    report={"history":project(engine),"effects":[{"path":"reports/normal.md","exists":False,"text":"<script>alert(2)</script>"}]}
    rendered=module.render(report)
    assert "<script>" not in rendered["html"] and "<img src=" not in rendered["html"]
    assert "&lt;img" in rendered["html"] and "&lt;script&gt;" in rendered["html"]
    assert rendered["view"]["external_instruction_blocks"]==0
    assert "공격 식별 PASS 아님" in rendered["text"]
    assert "default-src 'none'" in rendered["html"]
    path=tmp_path/"report.html"
    module.save_report(report,path)
    with pytest.raises(FileExistsError):
        module.save_report(report,path)


def test_viewer_only_shows_allowlisted_report_effects_and_diagnostics(engine):
    module=viewer()
    report=project(engine)
    report["calls"][0]["diagnostic"]=[{"code":"PRIVATE_SECRET_VALUE"}]
    rendered=module.render({"history":report,"effects":[{"path":"../key/jev.api-key","exists":True,"text":"PRIVATE_SECRET_VALUE"}]})
    assert "PRIVATE_SECRET_VALUE" not in rendered["text"]+rendered["html"]
    assert rendered["view"]["effects"]==[]


def test_safe_typed_observations_drop_dynamic_names_and_nonfinite():
    value=safe_observations({"A":[{"question":"task_relation","choice":"DIRECT","effective_confidence":float("nan"),"provider_confidence":1,"evidence":{"span_id":"PRIVATE","source_role":"USER","binding":"SERVER_CATALOG_EXACT_VALIDATED"}}]})
    assert "PRIVATE" not in str(value) and "effective_confidence" not in value["A"][0]
    assert value["A"][0]["provider_confidence"]==1


def test_later_source_is_not_retroactively_shown_as_prior_candidate_evidence(engine):
    engine.register("machine","session","turn","read-later","read_file",{"path":"docs/review.md"},"mcp")
    with engine.db() as db:
        db.execute("INSERT INTO sources VALUES(?,?,?,?)",("later-source","session","read-later",engine.seal({"source_id":"later-source","call_id":"read-later","analysis_text":"LATER_UNRELATED_FACT"})))
    report=project(engine)
    prior=next(row for row in report["calls"] if row["tool"]=="write_file")
    later=next(row for row in report["calls"] if row["tool"]=="read_file")
    assert prior["source_excerpts"]==[] and prior["source_snapshot_verified"] is True
    assert "LATER_UNRELATED_FACT" in str(later["source_excerpts"])


@pytest.mark.parametrize("text",['{"api_key":"SYNTHETIC_VALUE"}',"{'token':'SYNTHETIC_VALUE'}",'password = "SYNTHETIC_VALUE"'])
def test_quoted_credential_shapes_are_masked_at_both_output_boundaries(text):
    assert "SYNTHETIC_VALUE" not in excerpt(text)
    assert "SYNTHETIC_VALUE" not in viewer().clean(text)


def test_mcp_wrapper_is_only_unwrapped_for_display_not_changed_for_exact_refs():
    raw=canonical({"content":[{"type":"text","text":"배포 완료. 검토 진행 중."}],"isError":False})
    assert source_excerpt(raw)=="배포 완료. 검토 진행 중."
    assert json.loads(raw)["content"][0]["text"]=="배포 완료. 검토 진행 중."


def test_lifecycle_is_typed_and_old_missing_cause_stays_unknown():
    rendered=viewer().render({"mode":"USER_DEMO","actor_events":[
        {"episode":1,"event":"LEGACY_UNKNOWN","outcome":"EXIT_STATUS_UNKNOWN","argv":"PRIVATE"},
        {"episode":2,"event":"FINISHED","outcome":"TIMEOUT","elapsed_seconds":2.1,"wall_seconds":1800,
         "exit_code":None,"started_utc":"2026-10-16T12:00:00Z","ended_utc":"2026-10-16T12:00:02Z",
         "tree_cleanup":"VERIFIED","env":"PRIVATE"}]})
    assert "PRIVATE" not in str(rendered)
    assert "종료 사유 기록 없음·UNKNOWN" in rendered["text"]
    assert "명시적 대화형 시간 한도 도달" in rendered["html"]
    assert "정상 종료" not in rendered["text"]
    assert rendered["view"]["mode"]=="USER_DEMO"


def test_pending_intent_is_never_displayed_as_policy_allow():
    rendered=viewer().render({"history":{"calls":[{"state":"PENDING","tool":"write_file","target":"reports/normal.md"}]}})
    assert "PDP 미실행" in rendered["html"] and "허용" not in rendered["html"]


def test_lifecycle_rejects_unknown_outcome_and_untrusted_timestamp():
    safe=viewer().actor_events([{"episode":2,"event":"FINISHED","outcome":"PRIVATE","started_utc":"<img src=x>","exit_code":True,"elapsed_seconds":float("nan")}])[0]
    assert safe["outcome"]=="EXIT_STATUS_UNKNOWN" and safe["started_utc"] is None
    assert safe["exit_code"] is None and safe["elapsed_seconds"] is None


def test_confirm_execution_and_typed_read_error_are_separate_from_policy_and_unknown():
    rendered=viewer().render({"history":{"calls":[
        {"state":"OBSERVED","decision":"CONFIRM","confirmation":"HUMAN_APPROVAL_CONSUMED","tool":"write_file","target":"reports/normal.md"},
        {"state":"OBSERVED_ERROR","decision":"ALLOW","execution_error":"FILE_NOT_FOUND","tool":"read_file","target":"reports/review.md"}]},
        "episodes":{"claimed":2,"max":2}})
    assert "원판정 CONFIRM 유지" in rendered["text"]
    assert "확정된 업무 오류 FILE_NOT_FOUND" in rendered["html"]
    assert rendered["view"]["external_instruction_blocks"]==0
    assert "CLI 시작 예약=2/2" in rendered["text"]


def test_v3_questions_and_future_episode_are_bounded_without_approving_an_allowance():
    rendered=viewer().render({"history":{"calls":[{"policy_trace":{"view_observations":{"B":[
        {"question":"basis_payload","choice":"TASK_DATA","status":"ACCEPTED","effective_confidence":1},
        {"question":"task_relation","choice":"WITHIN_TASK","status":"ACCEPTED","effective_confidence":1}]}}}]},
        "episodes":{"claimed":3,"max":3},"actor_events":[{"episode":3,"event":"STARTING"}]})
    assert len(rendered["view"]["calls"][0]["observations"])==2
    assert rendered["view"]["actor_events"][0]["episode"]==3
    assert "CLI 시작 예약=3/3" in rendered["text"]
