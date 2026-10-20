"""Isolated real processes, TLS/mTLS and DBs. No auth/reserve mocks."""
import importlib.util
import json
import os
import sqlite3
import ssl
import subprocess
import time
from pathlib import Path

import httpx
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


class Product:
    def __init__(self, root, environment=None):
        self.root = root
        self.pki = root / "pki"
        spec = importlib.util.spec_from_file_location("prepare_tls", "/workspace/tools/prepare_tls.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate(self.pki)
        self.trust = ssl.create_default_context(cafile=str(self.pki / "ca.pem"))
        self.service_trust = ssl.create_default_context(cafile=str(self.pki / "ca.pem"))
        self.service_trust.load_cert_chain(self.pki / "gateway-client.pem", self.pki / "gateway-client.key")
        self.human = (self.pki / "human.token").read_text().strip()
        self.service = (self.pki / "service.token").read_text().strip()
        self.control_db, self.effects_db = root / "control.sqlite3", root / "effects.sqlite3"
        self.env = {**os.environ, "RUNTIME_DIR": str(self.pki), "CONTROL_DB_PATH": str(self.control_db),
                    "EFFECTS_DB_PATH": str(self.effects_db), "CONTROL_BASE_URL": "https://127.0.0.1:8443"}
        self.env.update(environment or {})
        self.processes = []
        self.records = []
        self.start()

    def start(self):
        for module in ("app.control.serve", "app.gateway.main"):
            self.processes.append(subprocess.Popen(["python", "-m", module], env=self.env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for _ in range(80):
            if any(p.poll() is not None for p in self.processes):
                raise RuntimeError("Product subprocess failed; no credential output captured")
            try:
                with httpx.Client(verify=self.trust, trust_env=False, timeout=0.2) as client:
                    if client.get("https://127.0.0.1:8000/healthz").status_code == 200:
                        client.get("https://127.0.0.1:8001/mcp")
                        return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        raise RuntimeError("Product readiness timeout")

    def stop(self):
        for process in self.processes:
            process.terminate()
        for process in self.processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self.processes = []

    async def request(self, path, value=None, role="human", token=None):
        internal = path.startswith("/internal/")
        credential = token if token is not None else {"human": self.human, "service": self.service, "none": ""}[role]
        headers = {"Authorization": "Bearer " + credential} if credential else {}
        async with httpx.AsyncClient(verify=self.service_trust if internal else self.trust,
                                     trust_env=False, timeout=2, headers=headers) as client:
            url = (f"https://127.0.0.1:{self.env.get('INTERNAL_PORT', '8443')}" if internal else "https://127.0.0.1:8000") + path
            return await (client.get(url) if value is None else client.post(url, json=value))

    async def session(self, task="SUMMARIZE_ISSUE", body="검토 완료", issue=42):
        request = {"task_kind": task, "user_request": "이슈 작업 요청", "issue_id": issue}
        if task == "POST_COMMENT":
            request["allowed_comment_body"] = body
        response = await self.request("/v1/sessions", request)
        assert response.status_code == 201
        return response.json()

    async def tool(self, session, name, args):
        async with httpx2.AsyncClient(verify=self.trust, trust_env=False, timeout=40,
                 headers={"Authorization": "Bearer " + session["agent_session_token"]}) as http:
            async with Client(streamable_http_client("https://127.0.0.1:8001/mcp", http_client=http)) as client:
                return await client.call_tool(name, args)

    def counts(self, sid, tool=None):
        if not self.effects_db.exists():
            return (0, 0)
        with sqlite3.connect(self.effects_db) as db:
            invocations = db.execute("SELECT count(*) FROM invocations WHERE session_id=?" +
                (" AND tool_name=?" if tool else ""), (sid, tool) if tool else (sid,)).fetchone()[0]
            effects = db.execute("SELECT count(*) FROM comments WHERE session_id=?", (sid,)).fetchone()[0]
        return invocations, effects

    def record(self, case, session, result=None, tool=None):
        value = result.structured_content if result is not None else {}
        counts = self.counts(session["session_id"], tool)
        self.records.append({"case_id": case, "mode": "REPLAY", "session_id": session["session_id"],
             "call_id": value.get("call_id"), "decision": value.get("decision"),
             "execution_state": value.get("execution_state"), "executor_invocations": counts[0],
             "actual_effects": counts[1], "tool": tool, "result": "PASS"})
        if value.get("call_id"):
            with sqlite3.connect(self.control_db) as db:
                db.row_factory = sqlite3.Row
                row = db.execute("SELECT c.args_sha256,c.policy_version,d.id AS decision_id,e.reservation_id,a.id AS approval_id FROM calls c JOIN decisions d ON d.call_id=c.id LEFT JOIN executions e ON e.call_id=c.id LEFT JOIN approvals a ON a.call_id=c.id WHERE c.id=?", (value["call_id"],)).fetchone()
                if row:
                    self.records[-1].update(dict(row))


@pytest.fixture(scope="session")
def product(tmp_path_factory):
    value = Product(tmp_path_factory.mktemp("product"))
    try:
        yield value
    finally:
        value.stop()
        target = os.getenv("EVIDENCE_DIR")
        if target:
            Path(target).mkdir(parents=True, exist_ok=True)
            # Tokens/raw user responses/DB copies are intentionally absent.
            (Path(target) / "product-traces.json").write_text(json.dumps(value.records, indent=2), encoding="utf-8")
