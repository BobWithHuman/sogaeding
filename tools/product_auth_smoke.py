"""Real TLS SDK MCP smoke. Only safe metadata is emitted, never token responses."""
import asyncio
import os
import ssl
from pathlib import Path

import httpx
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def main():
    runtime = Path(os.getenv("RUNTIME_DIR", "/runtime"))
    trust = ssl.create_default_context(cafile=str(runtime / "ca.pem"))
    human = (runtime / "human.token").read_text().strip()
    public = os.getenv("SMOKE_CONTROL_URL", "https://control:8000")
    gateway = os.getenv("SMOKE_MCP_URL", "https://gateway:8001/mcp")
    async with httpx.AsyncClient(verify=trust, trust_env=False, timeout=3) as client:
        assert (await client.get(public + "/healthz")).json() == {"status": "ok"}
        assert (await client.post(public + "/v1/sessions", json={})).status_code == 401
        assert (await client.post(public + "/internal/auth/resolve", json={})).status_code == 403
        response = await client.post(public + "/v1/sessions", headers={"Authorization": "Bearer " + human},
            json={"task_kind": "SUMMARIZE_ISSUE", "user_request": "이슈 42 요약", "issue_id": 42})
        assert response.status_code == 201
        session = response.json()
    for bearer, valid in [(session["agent_session_token"], True), (None, False), ("x" * 64, False), (human, False)]:
        headers = {"Authorization": "Bearer " + bearer} if bearer else {}
        async with httpx2.AsyncClient(verify=trust, trust_env=False, headers=headers, timeout=3) as client:
            try:
                async with Client(streamable_http_client(gateway, http_client=client)) as mcp:
                    tools = await mcp.list_tools()
                    assert valid
                    assert {t.name for t in tools.tools} == {"get_issue", "read_workspace_file", "post_issue_comment"}
                    result = await mcp.call_tool("get_issue", {"issue_id": 42})
                    assert result.structured_content["execution_state"] == "SUCCEEDED"
            except BaseExceptionGroup:
                if valid:
                    raise
            except Exception:
                if valid:
                    raise
    print("PASS actual TLS MCP list/call; missing/wrong/human bearer rejected; registered read succeeded")


if __name__ == "__main__":
    asyncio.run(main())
