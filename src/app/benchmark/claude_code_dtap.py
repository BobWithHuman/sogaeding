"""Pinned official DTAP task on the macOS host with the Claude Code CLI actor.

One process runs one task-arm. A fresh pinned environment container, the
official MCP server and the injection server start on 127.0.0.1 only. Both arms
use the container runtime's Control -> authz -> one-shot proxy chain in process;
only the policy's enabled flag differs. Claude Code has no built-in tools and
reaches the environment solely through the loopback bridge.
"""

import asyncio
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
import yaml
from cryptography.fernet import Fernet
from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.benchmark.claude_code import ActorStop, ClaudeCodeActor, preflight, server_key
from app.benchmark.mcp_bridge import BridgeStopped, LoopbackServer, bridge_app
from app.benchmark.official_adapter import dispatch_tool, injected_tools, judge_bridge
from app.benchmark.proxy import rpc
from app.benchmark.registry import UnsupportedTool
from app.benchmark.responses_loop import TaskIncomplete
from app.common import canonical, digest

ENV_IMAGE = "decodingtrustagent/os-filesystem@sha256:7dc11a71388793b859cf7332f0d474784164d5e15bae751b28dab85a92b10732"
SOURCE_COMMIT = "e0323a521ba4ef88f8e14c1eccf68d0a3d19a458"
SERVER = "OS-filesystem"
INJECTION_SERVER = "os-filesystem-injection"
AGENT_TYPE = "withhuman-claude-code"
ARMS = ("engine-off", "engine-on")
LIMITS = {"tool_calls": 96, "seconds": 900, "source_bytes": 65536, "catalog_bytes": 262144}
# Selectable engine-on policy: the scope-3 functional profile, or scope-4 which adds
# the user-named-resource rules that reduce false positives.
POLICIES = {
    "functional-3": ("dtap-functional-scope-3", "dtap-functional-routing-1"),
    "explicit-4": ("dtap-functional-scope-4", "dtap-functional-routing-2"),
    # scope-4 plus Jev A and B review of former consent stops (task_scope.REVIEW_REVISION).
    "review-5": ("dtap-functional-scope-5", "dtap-functional-routing-3"),
    # scope-5 with Jev deciding held cases, including unnamed sensitive/outside targets.
    "gate-6": ("dtap-functional-scope-6", "dtap-functional-routing-4"),
}
# Same settings the container runtime applied to the unchanged official server.
LAUNCH_MCP = (
    "import runpy;m=runpy.run_path('main.py')['mcp'];m.settings.host='127.0.0.1';"
    "m.settings.port={port};m.settings.stateless_http=True;"
    "m.settings.transport_security.allowed_hosts=['127.0.0.1:{port}','localhost:{port}'];"
    "m.settings.transport_security.allowed_origins=['http://127.0.0.1:{port}'];"
    "m.run(transport='streamable-http')"
)
# Same pinned base as Dockerfile.dev; runs only the fixed stdlib forwarder below.
FORWARD_IMAGE = "python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
FORWARD = (
    "import asyncio\n"
    "async def pipe(r,w):\n"
    "    try:\n"
    "        while data:=await r.read(65536):\n"
    "            w.write(data);await w.drain()\n"
    "    finally:\n"
    "        w.close()\n"
    "async def handle(r,w):\n"
    "    try:\n"
    "        ur,uw=await asyncio.open_connection('official-env',8034)\n"
    "    except OSError:\n"
    "        w.close();return\n"
    "    await asyncio.gather(pipe(r,uw),pipe(ur,w),return_exceptions=True)\n"
    "async def main():\n"
    "    server=await asyncio.start_server(handle,'0.0.0.0',8034)\n"
    "    async with server:\n"
    "        await server.serve_forever()\n"
    "asyncio.run(main())\n"
)
# The container runtime's environment limits (docker_sandbox.create defaults).
CONFINED = [
    "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
    "--pids-limit", "128", "--memory", "512m", "--cpus", "1",
]
LAUNCH_INJECTION = (
    "import runpy,sys;from app.benchmark.mcp_compat import module;"
    "sys.modules['fastmcp']=module();runpy.run_path('env_injection.py',run_name='__main__')"
)


def loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def child_env(extra):
    env = {k: os.environ[k] for k in ("HOME", "LANG") if k in os.environ}
    env.update(PATH="/usr/bin:/bin", PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


def environment_name(run_id, arm, key):
    """Deterministic names so the runner can clean up after a killed worker."""
    return "wh-cc-" + run_id + "-" + arm + "-" + digest(key)[:12]


def task_server(task):
    servers = [s for s in task["Agent"].get("mcp_servers", []) if s.get("enabled", True)]
    if len(servers) != 1 or servers[0]["name"] != SERVER:
        raise TaskIncomplete("TASK_SERVER_FAMILY_NOT_ENROLLED")
    variables = servers[0].get("env_vars") or {}
    if set(variables) - {"USER_ACCESS_TOKEN", "LINUX_USER", "PERMISSION_AUTO_APPROVE"}:
        raise TaskIncomplete("UNREVIEWED_OFFICIAL_SERVER_ENVIRONMENT")
    if str(variables.get("PERMISSION_AUTO_APPROVE", "false")).lower() not in ("true", "false"):
        raise TaskIncomplete("UNREVIEWED_ORIGINAL_PERMISSION_SETTING")
    # The reviewed task scope (scope-3) is issued for alice only; other synthetic
    # identities stay unenrolled in both arms rather than crashing the grant.
    if variables.get("USER_ACCESS_TOKEN", "alice-token") != "alice-token" or variables.get(
        "LINUX_USER", "alice"
    ) != "alice":
        raise TaskIncomplete("UNREVIEWED_SYNTHETIC_IDENTITY")
    return servers[0], variables


class HostEnvironment:
    """Fresh pinned environment container plus official servers for one task-arm."""

    def __init__(self, source, root, name, variables, logs, *, injection, permission):
        self.source, self.root, self.name = Path(source), Path(root), name
        self.variables, self.logs, self.injection = variables, Path(logs), injection
        # The pinned server's permission LLM settings: the loopback simulated user.
        self.permission = permission
        self.processes = []

    def _docker(self, *args, timeout=180):
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, check=True
        ).stdout.strip()

    def _spawn(self, label, argv, cwd, env):
        log = open(self.logs / (label + ".log"), "wb")
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.processes.append((proc, log))
        record_process(self.logs.parent, proc.pid)

    async def _wait(self, check, code, seconds=90):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if any(proc.poll() is not None for proc, _ in self.processes):
                raise TaskIncomplete(code)
            try:
                if await check():
                    return
            except (httpx.HTTPError, OSError, ValueError, KeyError):
                pass
            await asyncio.sleep(0.5)
        raise TaskIncomplete(code)

    async def _initialized(self, url):
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            value, _ = await rpc(
                client,
                url,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "with-human-dtap-cc", "version": "1"},
                    },
                },
            )
            return "result" in value

    async def tools(self):
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            _, session = await rpc(
                client,
                self.mcp_url,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "with-human-dtap-cc-discovery", "version": "1"},
                    },
                },
            )
            headers = {"mcp-session-id": session} if session else {}
            await rpc(client, self.mcp_url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, headers)
            listed, _ = await rpc(client, self.mcp_url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers)
            return listed["result"]["tools"]

    async def __aenter__(self):
        try:
            return await self._start()
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    async def _start(self):
        # Internal network: no egress and no host gateway from the environment.
        # Only the fixed forwarder publishes its API, on 127.0.0.1.
        label = ["--label", "with-human.dtap-cc=1"]
        self._docker("network", "create", "--internal", *label, self.name + "-net")
        self._docker(
            "run", "-d", "--name", self.name, *label, "--network", self.name + "-net",
            "--network-alias", "official-env", *CONFINED,
            "--cap-add", "SETUID", "--cap-add", "SETGID", "--cap-add", "CHOWN",
            "--cap-add", "DAC_OVERRIDE", "--tmpfs", "/tmp:rw,size=134217728,mode=1777",
            "-e", "API_PORT=8034", "-e", "PERMISSION_LOG_PATH=/decodingtrust_agent/permission_log.jsonl",
            ENV_IMAGE,
        )
        self._docker(
            "run", "-d", "--name", self.name + "-fwd", *label, "-p", "127.0.0.1::8034",
            "--read-only", "--user", "65534:65534", *CONFINED, FORWARD_IMAGE, "python", "-I", "-c", FORWARD,
        )
        self._docker("network", "connect", self.name + "-net", self.name + "-fwd")
        host, port = self._docker("port", self.name + "-fwd", "8034/tcp").splitlines()[0].rsplit(":", 1)
        if host != "127.0.0.1":
            raise TaskIncomplete("ENVIRONMENT_PORT_NOT_LOOPBACK")
        self.api_port = int(port)
        self.api = "http://127.0.0.1:%d" % self.api_port

        async def healthy():
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                return (await client.get(self.api + "/health")).status_code == 200

        await self._wait(healthy, "ENVIRONMENT_HEALTH_FAILED")
        mcp_port = loopback_port()
        self.mcp_url = "http://127.0.0.1:%d/mcp" % mcp_port
        self._spawn(
            "mcp-server",
            [str(self.root / "venv/bin/uv"), "run", "--frozen", "--no-dev", "python", "-c",
             LAUNCH_MCP.format(port=mcp_port)],
            self.source / "dt_arena/mcp_server/os-filesystem",
            child_env(
                {
                    "UV_CACHE_DIR": str(self.root / "uv-cache"),
                    "UV_PROJECT_ENVIRONMENT": str(self.root / "mcp-venv"),
                    "UV_PYTHON": os.path.realpath(sys._base_executable),
                    "UV_PYTHON_DOWNLOADS": "never",
                    "UV_NO_CONFIG": "1",
                    "FILESYSTEM_API_URL": self.api,
                    "PORT": str(mcp_port),
                    **self.permission,
                    "PERMISSION_AUTO_APPROVE": str(
                        self.variables.get("PERMISSION_AUTO_APPROVE", "false")
                    ).lower(),
                    **{k: str(v) for k, v in self.variables.items() if k != "PERMISSION_AUTO_APPROVE"},
                }
            ),
        )
        await self._wait(lambda: self._initialized(self.mcp_url), "OFFICIAL_MCP_SERVER_START_FAILED")
        self.injection_url = None
        if self.injection:
            port = loopback_port()
            self.injection_url = "http://127.0.0.1:%d/mcp" % port
            self._spawn(
                "injection-server",
                [str(self.root / "venv/bin/python"), "-c", LAUNCH_INJECTION],
                self.source / "dt_arena/injection_mcp_server/os-filesystem",
                child_env(
                    {
                        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
                        "FILESYSTEM_API_HOST": "127.0.0.1",
                        "FILESYSTEM_API_PORT": str(self.api_port),
                        "USER_ACCESS_TOKEN": "admin-token-for-setup",
                        "OS_FILESYSTEM_INJECTION_MCP_HOST": "127.0.0.1",
                        "OS_FILESYSTEM_INJECTION_MCP_PORT": str(port),
                    }
                ),
            )
            await self._wait(
                lambda: self._initialized(self.injection_url), "INJECTION_SERVER_START_FAILED"
            )
        return self

    async def __aexit__(self, *exc):
        for proc, log in self.processes:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                if proc.poll() is not None:
                    break
                try:
                    os.killpg(proc.pid, sig)
                    proc.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    continue
            log.close()
        try:
            (self.logs / "environment.log").write_text(
                subprocess.run(
                    ["docker", "logs", "--tail", "200", self.name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout
            )
        finally:
            remove_environment(self.name)


def record_process(out, pid):
    """Process groups the runner kills if this worker dies before its own cleanup."""
    path = Path(out) / "processes.json"
    pids = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps(pids + [pid]))


def remove_environment(name):
    for args in (["rm", "-f", name, name + "-fwd"], ["network", "rm", name + "-net"]):
        subprocess.run(["docker", *args], capture_output=True, timeout=60)


class TypeSafeSend:
    """Runtime-profile Jev transport: pinned endpoint, run ledger, no retry or refund.

    Same limits as the container broker's Jev profile (512 KiB request, 64 KiB
    response, 18 s, a 64k-token reservation per request), not the product client's.
    A reservation is spent before sending and kept on every failure.
    """

    WIRE_BYTES, RESPONSE_BYTES, SECONDS, RESERVED_TOKENS = 524288, 65536, 18, 64000

    def __init__(self, key_path, ledger, run_id, run_limit, total_limit, *, transport=None):
        # One ledger for every run on this host: total_limit is fixed when it is created,
        # so a new run id never resets spending. run_limit bounds this run within it.
        if not 1 <= run_limit <= total_limit <= 100000:
            raise ValueError("JEV_REQUEST_LIMIT")
        self.key_path, self.ledger, self.run_id = Path(key_path), Path(ledger), run_id
        self.run_limit, self.total_limit = run_limit, total_limit
        # MockTransport is the only injectable transport (offline fixture runs).
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError("Only an explicit offline MockTransport may be injected")
        self.transport = transport

    def _key(self, view):
        from app.pdp.diagnostics import AnalysisFailure

        try:
            if self.key_path.is_symlink() or self.key_path.stat().st_size > 4096:
                raise OSError()
            key = self.key_path.read_text(encoding="ascii").strip()
            if not 16 <= len(key) <= 2048 or any(c.isspace() for c in key):
                raise OSError()
        except (OSError, UnicodeError):
            raise AnalysisFailure("MISSING_API_KEY", view) from None
        return key

    def _reserve(self, view, size):
        import sqlite3

        from app.pdp.diagnostics import AnalysisFailure

        with sqlite3.connect(self.ledger, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "CREATE TABLE IF NOT EXISTS jev_cap(singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
                " total_requests INTEGER NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS jev_requests(id INTEGER PRIMARY KEY, at REAL, run_id TEXT,"
                " view TEXT, wire_bytes INTEGER, reserved_tokens INTEGER, status TEXT, usage TEXT)"
            )
            # Diagnostics added after the first live run: the provider's answer (no input) and timing.
            columns = {row[1] for row in db.execute("PRAGMA table_info(jev_requests)")}
            for column in ("completed_at REAL", "issue TEXT", "response TEXT"):
                if column.split()[0] not in columns:
                    db.execute("ALTER TABLE jev_requests ADD COLUMN " + column)
            cap = db.execute("SELECT total_requests FROM jev_cap").fetchone()
            if cap is None:
                db.execute("INSERT INTO jev_cap VALUES(1,?)", (self.total_limit,))
            elif cap[0] != self.total_limit:
                raise AnalysisFailure("JEV_BUDGET_BINDING", view)
            total = db.execute("SELECT count(*) FROM jev_requests").fetchone()[0]
            ran = db.execute("SELECT count(*) FROM jev_requests WHERE run_id=?", (self.run_id,)).fetchone()[0]
            if total >= self.total_limit or ran >= self.run_limit:
                raise AnalysisFailure("REQUEST_BUDGET_EXHAUSTED", view)
            return db.execute(
                "INSERT INTO jev_requests(at,run_id,view,wire_bytes,reserved_tokens,status)"
                " VALUES(?,?,?,?,?,'STARTED')",
                (time.time(), self.run_id, view, size, self.RESERVED_TOKENS),
            ).lastrowid

    def _settle(self, row, status, usage=None, *, issue=None, response=None):
        import sqlite3

        with sqlite3.connect(self.ledger, timeout=5) as db:
            db.execute(
                "UPDATE jev_requests SET status=?,usage=?,completed_at=?,issue=?,response=? WHERE id=?",
                (status, canonical(usage) if usage is not None else None, time.time(), issue, response, row),
            )

    async def __call__(self, body):
        from app.benchmark.provider import TYPESAFE
        from app.common import strict_json
        from app.pdp.diagnostics import AnalysisFailure
        from app.transparent.jev import MODEL, ResponseValidationError, validate_response

        view = "A" if "task_relation" in body.get("questions", {}) else "B"
        raw = canonical(body).encode()
        if len(raw) > self.WIRE_BYTES:
            raise AnalysisFailure("JEV_CONTEXT_LIMIT", view)
        key = self._key(view)
        if key.encode() in raw:
            raise AnalysisFailure("JEV_SENSITIVE_INPUT", view)
        row = self._reserve(view, len(raw))
        status = "FAILED"
        try:
            async with (
                asyncio.timeout(self.SECONDS),
                httpx.AsyncClient(
                    transport=self.transport, timeout=self.SECONDS, trust_env=False, follow_redirects=False
                ) as client,
                client.stream(
                    "POST",
                    TYPESAFE,
                    content=raw,
                    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                ) as response,
            ):
                if response.status_code != 200:
                    raise AnalysisFailure(
                        "API_AUTHENTICATION" if response.status_code in (401, 403)
                        else "API_RATE_LIMIT" if response.status_code in (429, 529)
                        else "API_ERROR",
                        view,
                    )
                data = bytearray()
                async for block in response.aiter_bytes():
                    data.extend(block)
                    if len(data) > self.RESPONSE_BYTES:
                        raise AnalysisFailure("JEV_RESPONSE_INVALID", view)
            value = strict_json(bytes(data))
            if not isinstance(value, dict) or value.get("model") != MODEL:
                raise AnalysisFailure("JEV_RESPONSE_INVALID", view)
            usage = value.get("usage")
            if not isinstance(usage, dict) or type(usage.get("input_tokens")) is not int or usage["input_tokens"] < 0:
                # As the broker: spend that cannot be accounted stops instead of continuing.
                status = "USAGE_UNKNOWN"
                raise AnalysisFailure("UNEXPECTED_OUTPUT", view)
            try:
                # SharedJev validates again; failing here keeps a typed code instead of a
                # generic adapter error, so one malformed answer stays a case-local stop.
                validate_response(value, body["questions"])
            except (ResponseValidationError, ValueError, TypeError, KeyError) as error:
                status = "RESPONSE_INVALID"
                self._settle(row, status, usage, issue=canonical(getattr(error, "metadata", None) or
                             {"error": type(error).__name__}), response=bytes(data).decode())
                raise AnalysisFailure("JEV_RESPONSE_INVALID", view) from None
            status = "COMPLETED"
            self._settle(row, status, usage, response=bytes(data).decode())
            return value
        except TimeoutError:
            raise AnalysisFailure("API_TIMEOUT", view) from None
        except httpx.TransportError:
            raise AnalysisFailure("API_CONNECTION", view) from None
        finally:
            if status not in ("COMPLETED", "RESPONSE_INVALID"):
                self._settle(row, status)


class OffJev:
    """engine-off never asks Jev; any call is a wiring error, not an analysis."""

    is_fixture = False

    def __init__(self):
        from types import SimpleNamespace

        self.settings = SimpleNamespace(authorized=lambda: False)

    async def observe(self, view, state, questions, analysis_id):
        from app.pdp.diagnostics import AnalysisFailure

        raise AnalysisFailure("JEV_NOT_AUTHORIZED", view)


def gateway_app(control, proxy):
    """The agentgateway extAuthz route in process: authz first, then the one-shot proxy."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/mcp")
    async def mcp(request: Request):
        raw = await request.body()
        headers = {
            k: request.headers[k]
            for k in ("authorization", "content-type", "x-with-human-request")
            if k in request.headers
        }
        authz = await control.post("/authz", content=raw, headers=headers)
        forward = authz.headers.get("x-with-human-forward")
        if authz.status_code != 200 or not forward:
            return Response(status_code=403)
        upstream = await proxy.post(
            "/mcp",
            content=raw,
            headers={"content-type": "application/json", "x-with-human-forward": forward},
        )
        return Response(
            upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type"),
        )

    return app


class EngineChain:
    """Control, gateway and proxy for one task-arm; files live in a private runtime dir."""

    def __init__(self, context, key, env, registry, catalog, variables, protected):
        from app.benchmark.proxy import create_proxy
        from app.benchmark.runtime_demo import runtime_grant
        from app.benchmark.runtime_plan import NORMS
        from app.benchmark.runtime_policy import RuntimeEngine, RuntimePolicy, SyntheticBoundary
        from app.benchmark.server import control_app
        from app.benchmark.task_scope import ResourceProbe, issue_scope

        runtime = Path(os.environ["HOOKGW_RUNTIME"])
        data = Path(context["out"]) / "engine-data"
        data.mkdir(mode=0o700)
        values = {
            "storage.key": Fernet.generate_key().decode(),
            "machine.id": "dtap-cc-" + secrets.token_hex(8),
            "machine.token": secrets.token_urlsafe(32),
            "human.token": secrets.token_urlsafe(32),
            "forward.key": secrets.token_urlsafe(32),
        }
        for name, value in values.items():
            path = runtime / name
            path.write_text(value)
            path.chmod(0o600)
        self.machine_token = values["machine.token"]
        # The simulated user's approval channel; never given to the actor or the simulator.
        self.human_token = values["human.token"]
        on = context["arm"] == "engine-on"
        task = yaml.safe_load((Path(context["source"]) / "dataset/os-filesystem" / key / "config.yaml").read_text())
        request = canonical(
            {"actual_user_turns_chronological": [task["Task"]["task_instruction"]], "latest_turn": 0}
        )
        revision, profile = POLICIES[context.get("policy", "functional-3")]
        scope = issue_scope(request, registry, revision=revision)
        grant = runtime_grant({"demo": {"task_scopes": {key: scope}}}, key, registry, variables)
        (runtime / "grant.json").write_text(canonical(grant))
        self.boundary = SyntheticBoundary(
            [*protected, *values.values()],
            max_source_bytes=LIMITS["source_bytes"],
            max_catalog_bytes=LIMITS["catalog_bytes"],
        )
        if on:
            from app.benchmark.runtime_policy import SharedJev

            jev = context["jev"]
            transport = None
            if jev.get("offline_fixture") is True:
                # OFFLINE TEST ONLY: deterministic fixture answers, labeled in the run
                # manifest and summary; never a defense measurement.
                from app.benchmark.runtime_test_provider import fake_provider

                transport = httpx.MockTransport(fake_provider)
            send = TypeSafeSend(
                jev["key_path"],
                jev["ledger_path"],
                context["run_id"],
                jev["request_limit"],
                jev["total_limit"],
                transport=transport,
            )
            # The container runtime's composition: boundary check, then validated answers.
            client = SharedJev(send, self.boundary, live=True)
        else:
            client = OffJev()
        policy = RuntimePolicy(
            client,
            registry,
            self.boundary,
            NORMS["os-filesystem"],
            enabled=on,
            profile=profile if on else None,
        )
        policy.scope_probe = ResourceProbe(scope, registry, endpoint=env.api)
        guard = self.boundary
        self.control = control_app(
            runtime,
            registry,
            policy,
            catalog,
            engine_factory=lambda _container_path, *a, **k: RuntimeEngine(
                str(data / "control.sqlite3"), *a, boundary=guard, **k
            ),
        )
        policy.source_lookup = self.control.state.runtime_engine.source_roles
        self.proxy = create_proxy(
            registry, {SERVER: env.mcp_url}, str(data / "attempts.sqlite3"), values["forward.key"]
        )
        self.control_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.control), base_url="http://control", timeout=60
        )
        self.proxy_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.proxy), base_url="http://upstream", timeout=60
        )
        self.gateway = gateway_app(self.control_client, self.proxy_client)
        self.gateway_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.gateway), base_url="http://gateway", timeout=65
        )
        self.policy = policy.policy

    async def aclose(self):
        for client in (self.gateway_client, self.control_client, self.proxy_client):
            await client.aclose()


def agent_class(context, chain, actual, login, deadline, simulator):
    from dt_arena.src.types import hooks as official_hooks
    from dt_arena.src.types.agent import Agent, AgentResult
    from dt_arena.src.types.trajectory import Trajectory

    from app.benchmark.consent_simulator import APPROVABLE, consent_prompt, verdict
    from app.benchmark.hook import NOT_ASKED, GatewayHook, GuardedDispatch

    bridge_key = server_key(SERVER)

    class ClaudeCodeOfficialAgent(Agent):
        def __init__(self, agent_config, runtime_config):
            super().__init__(agent_config, runtime_config)
            self.events = []
            self.records = []
            self.turn_index = 0
            self.completed_turns = 0
            self.final_output = ""
            self.output_dir = Path(runtime_config.output_dir)
            self.trajectory = Trajectory()
            self.trajectory.data["runtime_tool_events"] = self.events
            self.actor = self.server = None
            self.requests = []

        def _create_mcp_server(self, server_config):
            raise TaskIncomplete("DIRECT_SDK_DISPATCH_FORBIDDEN")

        def record(self, event):
            self.records.append(event)
            target = Path(context["out"]) / "runtime-events.json"
            temp = target.with_suffix(".tmp")
            temp.write_text(canonical(self.records))
            temp.replace(target)
            self.trajectory.save(str(self.output_dir / "trajectory.json"))

        async def initialize(self):
            try:
                await self._initialize()
            except Exception as error:
                # The pinned runner swallows this; keep the reason so it stops the run.
                self.record(
                    {
                        "kind": "actor_incomplete",
                        "code": str(error)
                        if isinstance(error, (TaskIncomplete, ActorStop))
                        else "ACTOR_INITIALIZE_FAILED_" + type(error).__name__,
                    }
                )
                raise

        async def _initialize(self):
            self.control = chain.control_client
            self.headers = {"Authorization": "Bearer " + chain.machine_token}
            connected = await self.control.post("/connect", headers=self.headers, json={})
            connected.raise_for_status()
            self.connection = connected.json()["connection"]
            self.session = "dtap-" + str(uuid4())
            tools = injected_tools(actual, self.runtime_config.mcp_injection, SERVER)
            catalog = [{"server": SERVER, **t} for t in tools]
            if digest(canonical(catalog)) != context["catalog_sha256"]:
                raise TaskIncomplete("ACTOR_AND_ENGINE_CATALOG_MISMATCH")
            self.names = {bridge_key + "::" + t["name"]: (SERVER, t["name"]) for t in tools}
            self.bridge = bridge_app({bridge_key: tools}, context["bridge_token"], self.dispatch)
            self.server = LoopbackServer(self.bridge)
            await self.server.__aenter__()
            # Actor config files only, outside any repository and without arm/task names.
            # The actor itself runs with cwd "/": Claude Code adds git status and directory
            # facts to its context, which must not leak the harness.
            self.workdir = Path(tempfile.mkdtemp(prefix="wh-actor-"))
            self.actor = ClaudeCodeActor(
                login,
                context["claude"]["config_dir"],
                self.workdir,
                model=context["claude"]["model"],
                effort=context["claude"]["effort"],
                system_prompt=self.config.system_prompt,
                urls={bridge_key: self.server.url(bridge_key)},
                token=context["bridge_token"],
                expected_tools={"mcp__%s__%s" % (bridge_key, t["name"]) for t in tools},
                record=self.record,
                deadline=deadline,
                ready=self.bridge.state.ready,
                stopped=self.bridge.state.stopped,
                expected_model=context["claude"]["model"],
            )
            await self.actor.start()
            record_process(context["out"], self.actor.proc.pid)

        async def dispatch(self, server, tool, args):
            if self.bridge.state.calls > LIMITS["tool_calls"]:
                raise BridgeStopped("TOOL_CALL_LIMIT")
            try:
                result = await dispatch_tool(self, server + "::" + tool, args)
            except TaskIncomplete as stop:
                if str(stop) == "ANALYSIS_OR_INFRASTRUCTURE_STOP" and self._only_invalid_jev_answer():
                    # One malformed provider answer: this task-arm stops unresolved (never a
                    # defense win); auth/limit/transport/budget failures still halt the run.
                    raise BridgeStopped("JEV_RESPONSE_INVALID_TASK_STOP") from stop
                raise BridgeStopped(str(stop)) from stop
            except BridgeStopped:
                raise
            except UnsupportedTool as refused:
                # Registry refusal of the actor's own arguments, equal in both arms:
                # this task-arm stops as in the container runtime; the run continues.
                raise BridgeStopped("UNSUPPORTED_" + str(refused)) from refused
            except Exception as error:
                raise BridgeStopped("DISPATCH_INFRASTRUCTURE_" + type(error).__name__) from error
            if "policy_feedback" in result:
                # Same trusted refusal the Responses actor received as its whole output.
                return {"isError": True, "content": [{"type": "text", "text": canonical(result)}]}
            return result

        async def consent(self, call, tool, args, pre):
            """A CONFIRM goes to the simulated user with the actual request, then the
            engine's own single-use approval. The actor never holds the human token."""
            # Only scope-5/6 CONFIRMs that an approval can release reach the simulated user;
            # the scope-3/4 baselines keep CONFIRM as an unanswered stop.
            if context.get("policy") not in ("review-5", "gate-6") or not set(pre.get("reasons") or ["-"]) <= APPROVABLE:
                return NOT_ASKED
            prompt = consent_prompt("\n\n".join(self.requests), tool.split("::")[-1], args, pre.get("reasons", []))
            text = await simulator.decide("ENGINE_CONFIRM", prompt)
            if text is None:
                raise BridgeStopped("CONSENT_SIMULATOR_" + str(simulator.failure))
            answer = verdict(text)
            if answer is None:
                simulator.fail("ANSWER_INVALID")
                raise BridgeStopped("CONSENT_SIMULATOR_ANSWER_INVALID")
            decided = await self.control.post(
                "/approval",
                headers={"Authorization": "Bearer " + chain.human_token},
                json={"call": call, "approve": answer == "APPROVED"},
            )
            if decided.status_code != 200:
                raise BridgeStopped("CONSENT_APPROVAL_REJECTED")
            if answer != "APPROVED":
                return None
            polled = await self.control.post(
                "/event",
                headers=self.headers,
                json={
                    "event": "ApprovalPoll",
                    "connection": self.connection,
                    "session": self.session,
                    "turn": self.turn,
                    "call": call,
                    "action_hash": pre["action_hash"],
                },
            )
            if polled.status_code != 200 or polled.json().get("decision") != "ALLOW":
                raise BridgeStopped("CONSENT_APPROVAL_NOT_CONSUMED")
            return polled.json()

        def _only_invalid_jev_answer(self):
            with chain.control.state.runtime_engine.db() as db:
                row = db.execute("SELECT details FROM analysis_stops ORDER BY rowid DESC LIMIT 1").fetchone()
            codes = {d.get("code") for d in json.loads(row[0]).get("diagnostic", [])} if row else set()
            return codes == {"JEV_RESPONSE_INVALID"}

        async def _register_turn(self, original):
            response = await self.control.post(
                "/event",
                headers=self.headers,
                json={
                    "event": "UserPromptSubmit",
                    "connection": self.connection,
                    "session": self.session,
                    "turn": self.turn,
                    "prompt": original,
                    "cwd": "DTAP_OFFICIAL_SANDBOX",
                },
            )
            response.raise_for_status()
            if self.turn_index == 1:
                response = await self.control.post(
                    "/benchmark/catalog", headers=self.headers, json={"connection": self.connection}
                )
                response.raise_for_status()

        async def run(self, user_input, metadata=None):
            # metadata carries official labels/attack goals; never passed to the actor or Jev.
            self.turn_index += 1
            originals = context["original_instructions"]
            original = originals[min(self.turn_index - 1, len(originals) - 1)] if originals else user_input
            original = original or user_input
            if user_input.strip() != original.strip():
                # The official runner only strips the instruction; any other change is a
                # prompt injection, which this host runner does not enroll.
                self.record({"kind": "actor_incomplete", "code": "PROMPT_INJECTION_TASK_NOT_ENROLLED"})
                raise TaskIncomplete("PROMPT_INJECTION_TASK_NOT_ENROLLED")
            self.turn = "turn-" + str(self.turn_index)
            self.requests.append(original)
            try:
                await self._register_turn(original)
            except Exception as error:
                self.record({"kind": "actor_incomplete", "code": "CONTROL_EVENT_FAILED_" + type(error).__name__})
                raise
            hook = GatewayHook(
                context["registry"],
                self.control,
                chain.gateway_client,
                chain.machine_token,
                self.connection,
                self.session,
                self.turn,
                self.record,
                consent=self.consent,
            )
            self.dispatcher = GuardedDispatch(official_hooks, hook)
            self.trajectory.append_user_step(user_input)
            try:
                self.final_output = await self.actor.turn(user_input)
                self.completed_turns += 1
                self.trajectory.set_final_response(self.final_output)
                return AgentResult(
                    final_output=self.final_output,
                    turn_count=self.actor.turns,
                    trajectory=self.trajectory,
                )
            except ActorStop as stop:
                code = self.bridge.state.stop_code or str(stop)
                self.record({"kind": "actor_incomplete", "code": code})
                raise TaskIncomplete(code) from stop
            finally:
                self.record(
                    {
                        "kind": "turn_finished",
                        "turn": self.turn_index,
                        "completed_turns": self.completed_turns,
                        "final_output": self.final_output,
                    }
                )

        async def cleanup(self):
            try:
                if self.actor:
                    await self.actor.close()
                if self.server:
                    # Let an in-flight dispatch finish before the judge reads the environment.
                    try:
                        async with asyncio.timeout(90):
                            async with self.bridge.state.lock:
                                pass
                    except TimeoutError:
                        self.record({"kind": "actor_incomplete", "code": "DISPATCH_IN_FLIGHT_UNKNOWN"})
                    await self.server.__aexit__(None, None, None)
            finally:
                if getattr(self, "workdir", None):
                    shutil.rmtree(self.workdir, ignore_errors=True)
                if hasattr(self, "connection"):
                    response = await self.control.post(
                        "/benchmark/close", headers=self.headers, json={"connection": self.connection}
                    )
                    response.raise_for_status()

    return ClaudeCodeOfficialAgent


async def run_official(task_dir, context, chain, env, actual, login, deadline, simulator):
    import eval.task_runner as runner

    cls = agent_class(context, chain, actual, login, deadline, simulator)
    agents = []
    setup_failures = []

    def build(agent_type=None, agent_cfg=None, runtime_cfg=None, **kwargs):
        if agent_type != AGENT_TYPE or kwargs:
            raise TaskIncomplete("UNENROLLED_AGENT_BACKEND")
        agent = cls(agent_cfg, runtime_cfg)
        agents.append(agent)
        return agent

    def injection_servers(config, **kwargs):
        required = set(config["environment_servers"])
        if required - {INJECTION_SERVER} or env.injection_url is None:
            raise TaskIncomplete("UNENROLLED_ENVIRONMENT_INJECTION_SERVER")
        return None, {**config, "environment_servers": {INJECTION_SERVER: {"url": env.injection_url}}}

    async def apply_injections(injections, urls):
        from app.benchmark.injection_outcome import inspect_results
        from app.benchmark.mcp_compat import module

        previous = sys.modules.get("fastmcp")
        sys.modules["fastmcp"] = module()
        try:
            results = await original["apply_environment_injections_async"](injections, urls)
        finally:
            if previous is None:
                sys.modules.pop("fastmcp", None)
            else:
                sys.modules["fastmcp"] = previous
        (Path(context["out"]) / "environment-injection-results.json").write_text(canonical(results))
        outcome = inspect_results(injections, results)
        if not outcome["verified"]:
            setup_failures.append(
                {
                    "kind": "benchmark_setup_failure",
                    "stage": "ENVIRONMENT_INJECTION",
                    "code": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED",
                    "verified_domain_failure": outcome["domain_failure"],
                    "injection_outcome": outcome,
                }
            )
            raise TaskIncomplete("OFFICIAL_ENVIRONMENT_INJECTION_FAILED")
        return results

    original = {
        name: getattr(runner, name)
        for name in (
            "start_task_mcp_servers",
            "build_agent",
            "run_judge",
            "start_injection_mcp_servers",
            "wait_for_injection_mcp_ready",
            "apply_environment_injections_async",
        )
    }
    try:
        # Official setup.sh runs unchanged against this task-arm's fresh environment.
        runner.start_task_mcp_servers = lambda *a, **k: None
        runner.build_agent = build
        runner.run_judge = judge_bridge
        runner.start_injection_mcp_servers = injection_servers
        runner.wait_for_injection_mcp_ready = lambda config: None
        runner.apply_environment_injections_async = apply_injections
        code = await runner.run_single_task(
            Path(task_dir),
            agent_type=AGENT_TYPE,
            model=context["claude"]["model"],
            max_turns=LIMITS["tool_calls"],
            skip_mcp=False,
            skip_judge=False,
            temperature=None,
        )
    finally:
        for name, value in original.items():
            setattr(runner, name, value)
    agent = agents[0] if agents else None
    if not agent:
        return {"official_exit_code": code, "judge": {"error": "AGENT_NOT_INITIALIZED"}, "events": setup_failures}
    path = agent.output_dir / "judge_result.json"
    if not path.exists():
        # Judge partial effects too, without calling an incomplete actor complete.
        path.write_text(canonical(judge_bridge(task_dir, agent.final_output, trajectory=agent.trajectory.data)))
    return {
        "official_exit_code": code,
        "actor_initialized": agent.actor is not None,
        "actor_completed": agent.completed_turns == agent.turn_index and agent.turn_index > 0,
        "judge": json.loads(path.read_text()),
        "final_output": agent.final_output,
        "events": setup_failures + agent.records,
    }


def summarize(result):
    events = result.get("events", [])
    pre = [e for e in events if e.get("stage") == "PRE"]
    # The bridge/engine code explains an actor stop better than the actor's own label;
    # setup failures and a silently incomplete official run are never left blank.
    stops = [
        e["code"]
        for kind in ("actor_incomplete", "actor_stop", "benchmark_setup_failure")
        for e in events
        if e.get("kind") == kind
    ]
    if not stops and "events" in result and not result.get("actor_completed"):
        stops = ["OFFICIAL_RUNNER_INCOMPLETE"]
    models = sorted({e.get("model") for e in events if e.get("kind") == "actor_init"} - {None})
    usage = [e for e in events if e.get("kind") == "actor_result"]
    judge = result.get("judge") or {}
    simulated = [e for e in events if e.get("kind") == "consent_simulation" and e.get("source")]
    return {
        # Engine CONFIRMs the simulated user answered, and the pinned server's own requests.
        "confirm_consent": {c: sum(1 for e in pre if e.get("consent") == c) for c in ("APPROVED", "DENIED")},
        "environment_permission": {
            c: sum(1 for e in simulated if e["source"] == "ENVIRONMENT_PERMISSION" and e.get("decision") == c)
            for c in ("APPROVED", "DENIED")
        },
        "simulator_notional_cost_usd": round(sum(e.get("notional_cost_usd") or 0 for e in simulated), 6),
        "actor_completed": bool(result.get("actor_completed")),
        "task_success": judge.get("task_success"),
        "attack_success": judge.get("attack_success"),
        "judge_error": judge.get("error"),
        "decisions": {d: sum(1 for e in pre if e.get("decision") == d) for d in ("ALLOW", "DENY", "CONFIRM")},
        "deny_reasons": sorted({r for e in pre if e.get("decision") == "DENY" for r in e.get("reasons", [])}),
        "upstream_executed": sum(1 for e in events if e.get("kind") == "observed_tool"),
        "stop": stops[0] if stops else None,
        "actor_model": models[0] if len(models) == 1 else models or None,
        "notional_cost_usd": round(sum(u.get("notional_cost_usd") or 0 for u in usage), 6),
    }


async def run_task(context):
    """Entry for one task-arm; writes result.json into context['out']."""
    from dt_arena.src.types.task import AttackConfig
    from utils.injection_helpers import (
        build_tool_injections_from_config,
        get_env_injections_from_attack,
        get_required_injection_servers,
    )

    from app.benchmark.consent_simulator import (
        ConsentSimulator,
        official_instructions,
        permission_app,
    )
    from app.benchmark.runtime_policy import SyntheticBoundary
    from app.benchmark.runtime_registry import RuntimeRegistry, enroll_os

    started = time.monotonic()
    deadline = started + LIMITS["seconds"]
    key, out = context["task_key"], Path(context["out"])
    task_dir = Path(context["source"]) / "dataset/os-filesystem" / key
    task = yaml.safe_load((task_dir / "config.yaml").read_text())
    server, variables = task_server(task)
    attack = AttackConfig.from_yaml(str(task_dir / "config.yaml"))
    required = get_required_injection_servers(get_env_injections_from_attack(attack))
    if set(required) - {INJECTION_SERVER}:
        raise TaskIncomplete("UNENROLLED_INJECTION_SERVER")
    login = await preflight(context["claude"]["binary"], context["claude"]["config_dir"])
    if login["version"] != context["claude"]["version"]:
        raise ActorStop("CLAUDE_CODE_VERSION_CHANGED")
    logs = out / "logs"
    logs.mkdir(mode=0o700)
    name = environment_name(context["run_id"], context["arm"], key)
    result = {"task_key": key, "arm": context["arm"], "login": login}
    consent_events = []

    def consent_record(event):
        if event.get("kind") == "actor_process":
            record_process(out, event["pid"])
        else:
            consent_events.append(event)

    permission_token, bridge_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    # One simulated user per task-arm, same in both arms: the pinned server's permission
    # requests and, in engine-on, With Human's CONFIRM.
    simulator = ConsentSimulator(
        login,
        context["claude"]["config_dir"],
        model=context["simulator"]["model"],
        effort=context["simulator"]["effort"],
        instructions=official_instructions(context["source"]),
        record=consent_record,
        boundary=SyntheticBoundary([permission_token, bridge_token]),
    )
    permission = LoopbackServer(permission_app(simulator, permission_token, context["simulator"]["model"]))
    await permission.__aenter__()
    try:
        async with HostEnvironment(
            context["source"],
            context["root"],
            name,
            variables,
            logs,
            injection=bool(required),
            permission={
                "PERMISSION_LLM_API_BASE_URL": "http://127.0.0.1:%d/v1" % permission.port,
                "PERMISSION_LLM_API_KEY": permission_token,
                "PERMISSION_LLM_MODEL": context["simulator"]["model"],
            },
        ) as env:
            tools = await env.tools()
            blacklist = set(server.get("tool_blacklist") or [])
            registry = RuntimeRegistry([e for e in enroll_os(tools) if e["name"] not in blacklist])
            actual = [t for t in tools if t["name"] not in blacklist]
            catalog = [
                {"server": SERVER, **t}
                for t in injected_tools(actual, build_tool_injections_from_config(attack), SERVER)
            ]
            original = task["Task"].get("task_instruction", "")
            context = {
                **context,
                "registry": registry,
                "catalog_sha256": digest(canonical(catalog)),
                "bridge_token": bridge_token,
                "original_instructions": [original] if isinstance(original, str) else original,
            }
            chain = EngineChain(context, key, env, registry, catalog, variables, [bridge_token, permission_token])
            os.environ["OS_FILESYSTEM_API_PORT"] = str(env.api_port)
            os.environ["OS_FILESYSTEM_PROJECT_NAME"] = name
            os.environ["EVAL_RESULTS_ROOT"] = str(out / "official-results")
            os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
            try:
                result.update(
                    await run_official(task_dir, context, chain, env, actual, login, deadline, simulator),
                    policy=chain.policy,
                    registry_sha256=registry.digest,
                    catalog_sha256=context["catalog_sha256"],
                    environment_image=ENV_IMAGE,
                    source_commit=SOURCE_COMMIT,
                    model=context["claude"]["model"],
                    effort=context["claude"]["effort"],
                    seconds=round(time.monotonic() - started, 1),
                )
            finally:
                await chain.aclose()
    finally:
        await permission.__aexit__(None, None, None)
    result.setdefault("events", []).extend(consent_events)
    if simulator.failure:
        # Never a denial: a failed simulated user leaves this task-arm unresolved.
        result["events"].append({"kind": "actor_stop", "code": "CONSENT_SIMULATOR_" + simulator.failure})
    result["summary"] = summarize(result)
    return result


def main():
    context = json.loads(Path(sys.argv[1]).read_text())
    out = Path(context["out"])
    try:
        result = asyncio.run(run_task(context))
    except (TaskIncomplete, ActorStop) as stop:
        result = {"task_key": context["task_key"], "arm": context["arm"], "stop": str(stop), "events": []}
        result["summary"] = {**summarize(result), "stop": str(stop)}
    (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(canonical({"task": context["task_key"], "arm": context["arm"], **result["summary"]}))


if __name__ == "__main__":
    main()
