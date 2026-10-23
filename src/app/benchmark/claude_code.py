"""Claude Code CLI actor on the user's own subscription login, never an API key.

The unmodified `claude` binary runs headless with no built-in tools and only the
loopback MCP bridge. Its OAuth credential stays in Claude Code's own login under
a dedicated config directory; this module never reads, copies or forwards it.
"""

import asyncio
import json
import os
import re
import signal
import time
from pathlib import Path

from app.common import canonical, mask

# Parent variables are dropped so an API key or third-party provider cannot leak in.
PASSED_ENV = ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR")
FIXED_ENV = {
    "PATH": "/usr/bin:/bin",
    "DISABLE_AUTOUPDATER": "1",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ENABLE_TOOL_SEARCH": "false",
}
SUBSCRIPTIONS = ("pro", "max", "team", "enterprise")
# Shipped inside the pinned 2.1.308 binary (path "builtin"); no tool of theirs is in the
# actor's toolset. Any user/third-party plugin or a new built-in one stops for review.
BUILTIN_PLUGINS = {("cc-plugin-agents-md", "builtin"), ("cc-plugin-plugin-authoring", "builtin")}
MAX_LINE_BYTES = 16 * 1024 * 1024
STDERR_TAIL_BYTES = 4096


class ActorStop(RuntimeError):
    pass


def server_key(name):
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not key:
        raise ValueError("INVALID_MCP_SERVER_NAME")
    return key


def same_model(reported, requested):
    """The requested id, or that id's dated snapshot (claude-haiku-4-5 -> claude-haiku-4-5-20251001)."""
    return isinstance(reported, str) and (
        reported == requested or re.fullmatch(re.escape(requested) + r"-\d{8}", reported) is not None
    )


def actor_env(config_dir, parent=None):
    parent = os.environ if parent is None else parent
    env = {k: parent[k] for k in PASSED_ENV if k in parent}
    env.update(FIXED_ENV)
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return env


async def _output(argv, env, seconds=30):
    proc = await asyncio.create_subprocess_exec(
        *argv,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await asyncio.wait_for(proc.communicate(), seconds)
    return proc.returncode, out


async def preflight(binary, config_dir):
    """No inference. Claude Code's own status for the dedicated subscription login."""
    binary = str(Path(binary).resolve(strict=True))
    env = actor_env(config_dir)
    code, out = await _output([binary, "--version"], env)
    version = out.decode("utf-8", "replace").strip().split(" ")[0]
    if code != 0 or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ActorStop("CLAUDE_CODE_VERSION_UNKNOWN")
    code, out = await _output([binary, "auth", "status", "--json"], env)
    try:
        value = json.loads(out)
    except ValueError:
        value = {}
    if (
        code != 0
        or value.get("loggedIn") is not True
        or value.get("authMethod") != "claude.ai"
        or value.get("apiProvider") != "firstParty"
        or value.get("subscriptionType") not in SUBSCRIPTIONS
    ):
        raise ActorStop("CLAUDE_SUBSCRIPTION_LOGIN_REQUIRED")
    # Account identity (email/org) is deliberately not retained.
    return {
        "binary": binary,
        "version": version,
        "auth_method": value["authMethod"],
        "subscription": value["subscriptionType"],
    }


def command(binary, *, model, effort, system_prompt, mcp_config_file, servers):
    return [
        binary,
        "-p",
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        # Some models (e.g. Haiku 4.5) take no effort setting; None leaves it unset.
        *(["--effort", effort] if effort else []),
        "--tools",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        str(mcp_config_file),
        # No servers (the consent simulator): no tool is allowed at all.
        *(["--allowedTools", ",".join("mcp__" + s for s in sorted(servers))] if servers else []),
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--no-session-persistence",
        "--system-prompt",
        system_prompt,
    ]


class ClaudeCodeActor:
    def __init__(
        self,
        login,
        config_dir,
        workdir,
        *,
        model,
        effort,
        system_prompt,
        urls,
        token,
        expected_tools,
        record,
        deadline,
        ready,
        stopped,
        expected_model=None,
        cwd="/",
    ):
        # urls: {server_key: loopback bridge URL}; expected_tools: exact mcp__ names.
        # ready/stopped are the bridge's events: dispatch opens only after the
        # verified startup report, and either side stopping halts all dispatch.
        self.login, self.config_dir, self.workdir = login, Path(config_dir), Path(workdir)
        self.model, self.effort, self.system_prompt = model, effort, system_prompt
        self.urls, self.token = dict(urls), token
        self.expected_tools = set(expected_tools)
        self.record, self.deadline = record, deadline
        self.ready, self.stopped = ready, stopped
        self.expected_model = expected_model
        # Claude Code tells the model its working directory; a private host temp path
        # would be explored as if it existed in the benchmark environment.
        self.cwd = cwd
        self.proc = None
        self.pending = None
        self.failure = None
        self.closing = False
        self.initialized = False
        self.tool_uses = 0
        self.turns = 0
        self.stderr_tail = b""
        self.usage = []

    async def start(self):
        config = self.workdir / ".mcp-bridge.json"
        config.write_text(
            canonical(
                {
                    "mcpServers": {
                        server: {
                            "type": "http",
                            "url": url,
                            "headers": {"Authorization": "Bearer " + self.token},
                        }
                        for server, url in self.urls.items()
                    }
                }
            )
        )
        config.chmod(0o600)
        argv = command(
            self.login["binary"],
            model=self.model,
            effort=self.effort,
            system_prompt=self.system_prompt,
            mcp_config_file=config,
            servers=self.urls,
        )
        self.proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=self.cwd,
            env=actor_env(self.config_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=MAX_LINE_BYTES,
            start_new_session=True,
        )
        self.record({"kind": "actor_process", "pid": self.proc.pid})
        self.reader = asyncio.create_task(self._read())
        self.errors = asyncio.create_task(self._stderr())

    def _fail(self, code):
        if self.failure is None:
            self.failure = code
            self.record({"kind": "actor_stop", "code": code})
        self.stopped.set()
        if self.pending and not self.pending.done():
            self.pending.set_exception(ActorStop(code))

    def _check_init(self, msg):
        servers = {s.get("name"): s.get("status") for s in msg.get("mcp_servers", [])}
        observed = {
            "kind": "actor_init",
            "claude_code_version": msg.get("claude_code_version"),
            "model": msg.get("model"),
            "api_key_source": msg.get("apiKeySource"),
            "permission_mode": msg.get("permissionMode"),
            "tools": sorted(msg.get("tools", [])),
            "mcp_servers": servers,
            "plugins": sorted(
                (pl.get("name"), pl.get("path")) for pl in msg.get("plugins", []) if isinstance(pl, dict)
            ),
            "skills": sorted(msg.get("skills") or []),
            "slash_commands": len(msg.get("slash_commands") or []),
        }
        self.record(observed)
        if msg.get("apiKeySource") != "none":
            # Any API key in use means usage would not come from the subscription.
            return self._fail("CLAUDE_API_KEY_IN_USE_FORBIDDEN")
        if msg.get("claude_code_version") != self.login["version"]:
            return self._fail("CLAUDE_CODE_VERSION_CHANGED")
        if self.expected_model is not None and not same_model(msg.get("model"), self.expected_model):
            return self._fail("ACTOR_MODEL_MISMATCH")
        if set(servers) != set(self.urls) or any(v != "connected" for v in servers.values()):
            return self._fail("ACTOR_MCP_NOT_CONNECTED")
        if set(observed["tools"]) != self.expected_tools:
            return self._fail("ACTOR_TOOLSET_MISMATCH")
        if not {tuple(p) for p in observed["plugins"]} <= BUILTIN_PLUGINS:
            return self._fail("ACTOR_CONFIG_NOT_ISOLATED")
        self.initialized = True
        if not self.failure:
            self.ready.set()

    def _handle(self, msg):
        kind = msg.get("type")
        if kind == "system" and msg.get("subtype") == "init":
            self._check_init(msg)
        elif kind == "rate_limit_event":
            info = msg.get("rate_limit_info") or {}
            self.record(
                {
                    "kind": "actor_rate_limit",
                    "status": info.get("status"),
                    "resets_at": info.get("resetsAt"),
                    "utilization": info.get("utilization"),
                    "error_code": info.get("errorCode"),
                    "using_overage": info.get("isUsingOverage"),
                    "overage_status": info.get("overageStatus"),
                }
            )
            if info.get("status") not in ("allowed", "allowed_warning"):
                self._fail("SUBSCRIPTION_RATE_LIMITED")
            elif info.get("isUsingOverage") is True:
                # Extra usage is billed beyond the plan; this runner never spends it.
                self._fail("SUBSCRIPTION_OVERAGE_IN_USE")
        elif kind == "assistant":
            for block in (msg.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    self.tool_uses += 1
                    self.record(
                        {"kind": "actor_tool_use", "id": block.get("id"), "name": block.get("name")}
                    )
        elif kind == "result":
            usage = {
                "kind": "actor_result",
                "subtype": msg.get("subtype"),
                "is_error": msg.get("is_error"),
                "api_error_status": msg.get("api_error_status"),
                "num_turns": msg.get("num_turns"),
                "duration_ms": msg.get("duration_ms"),
                "usage": msg.get("usage"),
                "notional_cost_usd": msg.get("total_cost_usd"),
                "permission_denials": len(msg.get("permission_denials") or []),
            }
            self.usage.append(usage)
            self.record(usage)
            if not self.initialized:
                self._fail(self.failure or "ACTOR_INIT_MISSING")
            elif msg.get("api_error_status") == 429:
                self._fail("SUBSCRIPTION_RATE_LIMITED")
            elif msg.get("subtype") != "success" or msg.get("is_error"):
                self._fail("ACTOR_RESULT_" + str(msg.get("subtype")).upper())
            elif usage["permission_denials"]:
                # Only the bridge may refuse; a CLI-side denial means a wrong toolset.
                self._fail("ACTOR_CLI_PERMISSION_DENIAL")
            elif self.pending and not self.pending.done():
                self.pending.set_result(msg.get("result") or "")

    async def _read(self):
        try:
            while line := await self.proc.stdout.readline():
                try:
                    msg = json.loads(line)
                except ValueError:
                    self._fail("ACTOR_STREAM_INVALID")
                    continue
                if isinstance(msg, dict):
                    try:
                        self._handle(msg)
                    except (AttributeError, TypeError, ValueError):
                        # An unexpected shape must not silently disable the guards.
                        self._fail("ACTOR_STREAM_INVALID")
        except (ValueError, asyncio.LimitOverrunError):
            self._fail("ACTOR_STREAM_LIMIT")
        if not self.closing:
            self._fail(self.failure or "ACTOR_PROCESS_EXITED")

    async def _stderr(self):
        while block := await self.proc.stderr.read(4096):
            self.stderr_tail = (self.stderr_tail + block)[-STDERR_TAIL_BYTES:]

    async def turn(self, prompt):
        """Send one user turn; returns the final text or raises ActorStop."""
        if self.failure or self.stopped.is_set():
            raise ActorStop(self.failure or "BRIDGE_STOPPED")
        if time.monotonic() >= self.deadline:
            self._fail("ACTOR_TIMEOUT")
            raise ActorStop(self.failure)
        self.turns += 1
        self.pending = asyncio.get_running_loop().create_future()
        message = {"type": "user", "message": {"role": "user", "content": prompt}}
        self.proc.stdin.write((canonical(message) + "\n").encode())
        await self.proc.stdin.drain()
        stop = asyncio.create_task(self.stopped.wait())
        try:
            remaining = self.deadline - time.monotonic()
            done, _ = await asyncio.wait(
                {self.pending, stop},
                timeout=max(remaining, 0),
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            stop.cancel()
        if self.pending in done:
            return self.pending.result()
        self._fail("BRIDGE_STOPPED" if stop in done else "ACTOR_TIMEOUT")
        await self.close()
        raise ActorStop(self.failure)

    async def close(self):
        if not self.proc:
            return
        self.closing = True
        if self.proc.returncode is None:
            try:
                self.proc.stdin.close()
                await asyncio.wait_for(self.proc.wait(), 10 if not self.failure else 0.1)
            except (asyncio.TimeoutError, BrokenPipeError, ConnectionResetError):
                pass
        if self.proc.returncode is None:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(self.proc.pid, sig)
                    await asyncio.wait_for(self.proc.wait(), 5)
                    break
                except (ProcessLookupError, asyncio.TimeoutError):
                    continue
        for task in (self.reader, self.errors):
            task.cancel()
        if self.stderr_tail:
            self.record(
                {
                    "kind": "actor_stderr_tail",
                    "text": mask(self.stderr_tail.decode("utf-8", "replace")),
                }
            )
