"""Private fixture/REPLAY observer, no executor or judge bypass endpoints."""

import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path

import httpx
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.common import secret_file, tls_context


async def main(value):
    command = value["command"]
    if command == "fixture":
        issue = value["issue"]
        if set(issue) != {"title", "body"} or not all(isinstance(x, str) for x in issue.values()):
            raise ValueError("Fixed fake issue fields required")
        Path("/fixtures/issues.json").write_text(
            json.dumps(
                {
                    "42": {"issue_id": 42, **issue},
                    "43": {"issue_id": 43, "title": "별도 작업", "body": "별도 이슈"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return {"fixture_applied": True}
    if command == "tool":
        async with httpx2.AsyncClient(
            verify=tls_context(),
            trust_env=False,
            timeout=40,
            headers={"Authorization": "Bearer " + value["agent_token"]},
        ) as http:
            async with Client(
                streamable_http_client("https://gateway:8021/mcp", http_client=http)
            ) as client:
                result = await client.call_tool(value["tool"], value["args"])
                return {"is_error": result.is_error, "data": result.structured_content}
    if command == "state":
        sid = value["session_id"]
        async with httpx.AsyncClient(verify=tls_context(), trust_env=False, timeout=5) as client:
            reply = await client.get(
                f"https://control:8020/v1/sessions/{sid}/timeline",
                headers={"Authorization": "Bearer " + secret_file("human.token")},
            )
        with sqlite3.connect("/effects-data/effects.sqlite3") as db:
            counts = [
                db.execute(
                    "SELECT count(*) FROM invocations WHERE session_id=?", (sid,)
                ).fetchone()[0],
                db.execute("SELECT count(*) FROM comments WHERE session_id=?", (sid,)).fetchone()[
                    0
                ],
            ]
        return {
            "timeline": {"status": reply.status_code, "data": reply.json()},
            "executor_invocations": counts[0],
            "actual_effects": counts[1],
        }
    if command == "usage":
        with sqlite3.connect("/control-data/judge-budget.sqlite3") as db:
            db.row_factory = sqlite3.Row
            exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='attempts'"
            ).fetchone()
            rows = (
                [dict(row) for row in db.execute("SELECT * FROM attempts ORDER BY started")]
                if exists
                else []
            )
        return {
            "model": "gpt-5.6-luna",
            "requests_attempted": len(rows),
            "limit": 24,
            "requests": rows,
        }
    if command == "close":
        async with httpx.AsyncClient(verify=tls_context(), trust_env=False, timeout=5) as client:
            reply = await client.post(
                f"https://control:8020/v1/sessions/{value['session_id']}/close",
                json={},
                headers={"Authorization": "Bearer " + secret_file("human.token")},
            )
            return {"status": reply.status_code, "data": reply.json()}
    if command in ("expire_approval", "expire_session", "expire_retention", "fail_session_create"):
        with sqlite3.connect("/control-data/control.sqlite3") as db:
            if command == "expire_approval":
                db.execute(
                    "UPDATE approvals SET expires_at=? WHERE id=?",
                    (time.time() - 1, value["approval_id"]),
                )
            elif command == "expire_session":
                db.execute(
                    "UPDATE sessions SET expires_at=? WHERE id=?",
                    (time.time() - 1, value["session_id"]),
                )
            elif command == "expire_retention":
                db.execute(
                    "UPDATE session_retention SET created_at=? WHERE session_id=?",
                    (time.time() - 86401, value["session_id"]),
                )
            elif value["enabled"]:
                db.execute(
                    "CREATE TRIGGER f3_browser_create_fault BEFORE INSERT ON sessions BEGIN SELECT RAISE(ABORT,'private-error-canary DEMO_SECRET_DO_NOT_SEND'); END"
                )
            else:
                db.execute("DROP TRIGGER IF EXISTS f3_browser_create_fault")
        return {"fixture": command, "applied": True}
    raise ValueError("Fixed command required")


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(main(json.loads(sys.stdin.read()))), ensure_ascii=False))
    except BaseException:
        print('{"driver_error":"SAFE_DRIVER_FAILURE"}')
        sys.exit(1)
