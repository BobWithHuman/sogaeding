import json
import sqlite3
import time
from uuid import uuid4

import httpx
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


@pytest.mark.asyncio
async def test_at03_at04_at11_tool_inputs_and_bypass(product):
    session = await product.session()
    invalid = [
        ("get_issue", {"issue_id": 42, "session_id": str(uuid4())}),
        ("get_issue", {"issue_id": "42"}), ("get_issue", {"issue_id": True}),
        ("get_issue", {"issue_id": -1}), ("get_issue", {}),
        ("read_workspace_file", {"file_id": "SECRET_ENV", "readOnly": True}),
        ("read_workspace_file", {"file_id": "../../.env"}),
        ("post_issue_comment", {"issue_id": 42, "body": "x" * 4097}),
        ("post_issue_comment", {"issue_id": 42, "body": "x", "decision": "ALLOW"}),
        ("execute", {}),
    ]
    for name, args in invalid:
        result = await product.tool(session, name, args)
        assert result.is_error
    assert product.counts(session["session_id"]) == (0, 0)
    for path in ("/execute", "/executor", "/internal/execute"):
        response = await product.request(path, {}, role="human")
        assert response.status_code in (401, 403, 404)
    product.record("AT-03", session)
    product.record("AT-04", session)
    product.record("AT-11-tool", session)


@pytest.mark.asyncio
async def test_at08_at10_at13_roles_and_masked_storage(product):
    session = await product.session("POST_COMMENT")
    other = await product.session()
    for _role, credential in [("none", ""), ("service", product.service),
                              ("agent", session["agent_session_token"])]:
        response = await product.request("/v1/sessions", {}, token=credential)
        assert response.status_code == 401
        response = await product.request(f"/v1/sessions/{session['session_id']}/timeline", token=credential)
        assert response.status_code == 401
    read = await product.tool(session, "get_issue", {"issue_id": 42})
    forbidden = await product.tool(session, "post_issue_comment", {"issue_id": 42,
                    "body": "<script>alert(1)</script> DEMO_SECRET_DO_NOT_SEND " + session["agent_session_token"]})
    assert forbidden.is_error and forbidden.structured_content["decision"] == "DENY"
    response = await product.request(f"/v1/sessions/{session['session_id']}/timeline")
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    for marker in ("DEMO_SECRET_DO_NOT_SEND", product.human, product.service, session["agent_session_token"]):
        assert marker not in serialized and marker not in str(read)
        assert marker.encode() not in product.control_db.read_bytes()
    assert response.json()["sources"][1]["kind"] == "EXTERNAL"
    response_other = await product.request(f"/v1/sessions/{other['session_id']}/timeline")
    assert len(response_other.json()["checks"]) == 0
    forge_source = await product.request("/internal/sources", {"kind": "USER_REQUEST"}, role="service")
    assert forge_source.status_code == 422
    product.record("AT-08", session, forbidden, "post_issue_comment")
    product.record("AT-10-storage-api", session, forbidden, "post_issue_comment")
    product.record("AT-13", session)


@pytest.mark.asyncio
async def test_at11_rest_duplicate_depth_size_and_protocol(product):
    async with httpx.AsyncClient(verify=product.trust, trust_env=False,
                    headers={"Authorization": "Bearer " + product.human}, timeout=2) as client:
        url = "https://127.0.0.1:8000/v1/sessions"
        for raw, expected in [(b'{"task_kind":"SUMMARIZE_ISSUE","task_kind":"POST_COMMENT"}', 422),
                              (b'[' * 20 + b'0' + b']' * 20, 422),
                              (b'{"x":NaN}', 422), (b'"' + b'x' * 33000 + b'"', 413)]:
            response = await client.post(url, content=raw, headers={"Content-Type": "application/json"})
            assert response.status_code == expected
            assert "Traceback" not in response.text
        response = await client.post(url, content=b'{}', headers=[("Authorization", "Bearer " + product.human),
                                             ("Authorization", "Bearer " + product.service)])
        assert response.status_code == 422
        response = await client.post(url + "?token=omitted", json={})
        assert response.status_code == 422
        response = await client.post(url, json={}, headers={"Origin": "https://attacker.invalid"})
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_at13_actual_mcp_expired_audience_scope(product):
    session = await product.session()
    for field, bad in [("audience", "https://wrong.invalid/mcp"), ("expires_at", time.time() - 1)]:
        with sqlite3.connect(product.control_db) as db:
            previous = db.execute(f"SELECT {field} FROM session_tokens WHERE session_id=?", (session["session_id"],)).fetchone()[0]
            db.execute(f"UPDATE session_tokens SET {field}=? WHERE session_id=?", (bad, session["session_id"]))
        try:
            async with httpx2.AsyncClient(verify=product.trust, trust_env=False, timeout=2,
                    headers={"Authorization": "Bearer " + session["agent_session_token"]}) as http:
                with pytest.raises((ExceptionGroup, httpx2.HTTPError)):
                    async with Client(streamable_http_client("https://127.0.0.1:8001/mcp", http_client=http)) as client:
                        await client.list_tools()
        finally:
            with sqlite3.connect(product.control_db) as db:
                db.execute(f"UPDATE session_tokens SET {field}=? WHERE session_id=?", (previous, session["session_id"]))
    assert product.counts(session["session_id"]) == (0, 0)
    product.record("AT-13-mcp-expired-audience", session)


@pytest.mark.asyncio
async def test_pl_sec_transport_product_all_three_paths(product):
    session = await product.session()
    # Verified host -> Control / MCP and actual Gateway -> mTLS Control are used on every tool call.
    result = await product.tool(session, "get_issue", {"issue_id": 42})
    assert not result.is_error
    for url in ("https://127.0.0.1:8000/healthz", "https://127.0.0.1:8001/mcp"):
        async with httpx.AsyncClient(trust_env=False, timeout=1) as client:
            with pytest.raises(httpx.HTTPError):
                await client.get(url)
        async with httpx.AsyncClient(verify=product.trust, trust_env=False, timeout=1) as client:
            with pytest.raises(httpx.HTTPError):
                await client.get(url.replace("127.0.0.1", "127.0.0.2"))
    async with httpx.AsyncClient(verify=product.trust, trust_env=False, timeout=1) as client:
        with pytest.raises(httpx.HTTPError):
            await client.post("https://127.0.0.1:8443/internal/auth/resolve", json={})
        # Plaintext is tested without a credential, never sending one over HTTP.
        with pytest.raises(httpx.HTTPError):
            await client.get("http://127.0.0.1:8000/healthz")
    product.record("PL-SEC-TRANSPORT-product", session, result, "get_issue")


@pytest.mark.asyncio
async def test_at09_internal_tls_validation_failure_zero_execution(product):
    session = await product.session("POST_COMMENT")
    ca = product.pki / "ca.pem"
    original = ca.read_bytes()
    # Existing process's own server cert remains valid; only its new client trust is broken.
    ca.write_bytes((product.pki / "wrong-host.pem").read_bytes())
    try:
        with pytest.raises((ExceptionGroup, httpx2.HTTPError)):
            await product.tool(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
        assert product.counts(session["session_id"], "post_issue_comment") == (0, 0)
    finally:
        ca.write_bytes(original)
    product.record("AT-09-internal-TLS", session, tool="post_issue_comment")
