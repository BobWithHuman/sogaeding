import pytest

from app.common import validate


@pytest.mark.asyncio
async def test_manual_diagnostics_and_connection_are_user_only_without_effects(product):
    request = {"task_kind": "POST_COMMENT", "comment_mode": "ISSUE_SUMMARY", "issue_id": 42,
               "user_request": "이슈42를 읽고 요약 댓글을 한 번 작성해줘"}
    created = await product.request("/v1/sessions", request)
    assert created.status_code == 201
    session = created.json()
    other = (await product.request("/v1/sessions", request)).json()
    sid = session["session_id"]
    for path in (f"/v1/sessions/{sid}/diagnostics", "/v1/judge-usage"):
        for token in ("", product.service, session["agent_session_token"]):
            reply = await product.request(path, role="none", token=token)
            assert reply.status_code == 401
        reply = await product.request(path)
        assert reply.status_code == 200
        validate("AnalysisDiagnostics" if path.endswith("diagnostics") else "JudgeUsage", reply.json())
        assert session["agent_session_token"] not in reply.text and product.human not in reply.text
    route = f"/v1/sessions/{sid}/cli-binding"
    for token in ("", product.service, session["agent_session_token"]):
        reply = await product.request(route, {"agent_session_token": session["agent_session_token"]}, token=token)
        assert reply.status_code == 401
    wrong = await product.request(route, {"agent_session_token": other["agent_session_token"]})
    assert wrong.status_code == 403
    good = await product.request(route, {"agent_session_token": session["agent_session_token"]})
    assert good.status_code == 200 and good.json()["session_id"] == sid
    validate("AnalysisDiagnostics", good.json())
    assert product.counts(sid) == (0, 0)
    assert (await product.request("/v1/judge-usage")).json()["requests_attempted"] == 0
    product.record("manual-user-read-role-binding-zero-effects", session)
