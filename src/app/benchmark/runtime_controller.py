"""Trusted official TaskExecutor backend. No victim receives the Docker socket.

The controller owns infrastructure only. Agent/setup/judge code runs in a
separate worker, and file tools run in an even smaller server container.
"""

import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import ssl
import time
from pathlib import Path

import httpx
import yaml

from app.benchmark.docker_sandbox import DockerSandbox, bind
from app.benchmark.official_adapter import injected_tools
from app.benchmark.runtime_budget import BudgetStop, is_budget_stop
from app.benchmark.runtime_plan import NORMS
from app.benchmark.runtime_registry import enroll_os
from app.common import canonical, digest

ENV_IMAGE = "decodingtrustagent/os-filesystem@sha256:7dc11a71388793b859cf7332f0d474784164d5e15bae751b28dab85a92b10732"
GATEWAY = "cr.agentgateway.dev/agentgateway@sha256:9d3e6044ddcdc0878b1787f77bd401252b95e22684203fb5e874c4c42d2ed90c"
WORKER = "sha256:bd3607d2dae1d6c7e229ffecd9f056e501f23acd9221c7ec5a288856613a324d"
SERVER = "sha256:ec772d99dd4b77e9b07155d424a81898a169419877d855fe4a0396824b8b713e"


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(canonical(value))
    temp.replace(path)


def private_tree(folder):
    """Only newly created benchmark data; never alter personal/global ACLs."""
    folder = Path(folder)
    for path in [folder, *folder.rglob("*")]:
        try:
            os.chown(path, 10001, 10001)
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        except PermissionError:
            # Docker Desktop NTFS bind mounts cannot apply POSIX ownership.
            # The PowerShell launcher installs an owner/SYSTEM-only ACL on
            # the fresh experiment root before the first controller starts.
            if os.environ.get("DTAP_WINDOWS_HOST_ACL") != "1":
                raise
            # The host ACL is the access boundary; virtiofs exposes these
            # files as root-owned to the sandbox's non-root service users.
            try:
                os.chmod(path, 0o777 if path.is_dir() else 0o666)
            except PermissionError:
                # A non-root worker may have created this read-only evidence
                # file. The cap-dropped controller cannot change its mode.
                if path.is_dir() or not os.access(path, os.R_OK):
                    raise


def invalid_setup_log(raw, config):
    """Keep required setup errors fatal; OS-only tasks need no Slack seed."""
    if b"command not found" in raw:
        return True
    servers = {
        s["name"] for s in config.get("Agent", {}).get("mcp_servers", []) if s.get("enabled", True)
    }
    for line in raw.splitlines():
        if b"[WARN]" not in line:
            continue
        warning = line.partition(b"[WARN]")[2].strip()
        if (
            servers != {"OS-filesystem"}
            or warning != b"slack_init.json not found, skipping Slack seed"
        ):
            return True
    return False


def close_active_connection(out, data, runtime):
    """Return False when required Engine close cannot be observed."""
    connection = data / "active-connection.json"
    if not connection.exists():
        return True
    try:
        with httpx.Client(
            verify=ssl.create_default_context(cafile=str(runtime / "ca.pem")),
            trust_env=False,
            timeout=10,
        ) as client:
            closed = client.post(
                "https://control:8030/benchmark/close",
                headers={
                    "Authorization": "Bearer " + (runtime / "machine.token").read_text().strip()
                },
                json=json.loads(connection.read_text()),
            )
        observed = closed.status_code == 200
        atomic(
            out / "controller-close.json",
            {"http_status": closed.status_code, "observed": observed},
        )
        return observed
    except Exception as exc:
        atomic(
            out / "controller-close.json",
            {
                "observed": False,
                "state": "UNKNOWN_CLOSE_UNAVAILABLE",
                "error_type": type(exc).__name__,
            },
        )
        return False


class Controller:
    def __init__(self, root, host_root, project_root, arm):
        self.root = Path(root)
        self.host_root = host_root.rstrip("/")
        self.project = project_root.rstrip("/")
        self.plan = json.loads((self.root / "plan.json").read_text())
        self.arm = arm
        self.sandbox = DockerSandbox(self.plan["experiment"])
        self.network = self.plan["networks"][arm]["name"]
        self.admin = httpx.Client(
            base_url="https://broker:8500",
            verify=ssl.create_default_context(cafile=str(self.root / "broker-runtime/ca.pem")),
            trust_env=False,
            timeout=30,
            headers={
                "Authorization": "Bearer "
                + (self.root / "broker-runtime/admin.token").read_text().strip()
            },
        )
        self.owner = None
        self.created = []

    def host(self, path):
        return self.host_root + "/" + str(Path(path).relative_to(self.root)).replace("\\", "/")

    def admin_call(self, operation, **value):
        r = self.admin.post("/admin/" + operation, json=value)
        if r.status_code == 409:
            code = r.json().get("code")
            if is_budget_stop(code):
                raise BudgetStop(code)
        r.raise_for_status()
        return r.json()

    def common(self, data, config=None, runtime=None):
        mounts = [
            bind(self.project + "/src", "/product/src"),
            bind(self.project + "/tools", "/product/tools"),
            bind(self.project + "/docs/mvp/contracts", "/product/contracts"),
            bind(self.host(data), "/data", False),
        ]
        if config:
            mounts.append(bind(self.host(config), "/config"))
        if runtime:
            mounts.append(bind(self.host(runtime), "/runtime"))
        return mounts

    def create(self, name, image, cmd, **kwargs):
        cid = self.sandbox.create(name, image, cmd, **kwargs)
        self.created.append(cid)
        return cid

    def reserve_snapshot(self, identity, size, *, cleanup=None):
        self.admin_call("storage", identity=identity, bytes=size, cleanup=cleanup)

    def cleanup_created(self, out, env, preserve_environment=False):
        cleanup_failures = []
        for cid in list(reversed(self.created)):
            if cid == env and preserve_environment:
                continue
            try:
                (out / (cid[:12] + ".log")).write_bytes(self.sandbox.logs(cid))
                self.sandbox.remove(cid)
                self.created.remove(cid)
            except Exception as exc:
                cleanup_failures.append({"container_id": cid, "error": type(exc).__name__})
        if cleanup_failures:
            atomic(out / "cleanup-failures.json", cleanup_failures)
            raise RuntimeError("CONTAINER_CLEANUP_FAILED")

    def wait_api(self, container):
        for _ in range(60):
            code, _ = self.sandbox.exec(
                container,
                [
                    "python",
                    "-c",
                    "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8034/health')",
                ],
            )
            if code == 0:
                return
            time.sleep(0.5)
        raise RuntimeError("OFFICIAL_ENVIRONMENT_HEALTH_TIMEOUT")

    def initial_snapshot(self, key):
        """A shared filesystem lock permits exactly one official setup seed."""
        folder = self.root / "snapshots" / digest(key)
        folder.mkdir(parents=True, exist_ok=True)
        ready = folder / "snapshot.json"
        lock = folder / "seed.lock"
        manifest = getattr(self, "plan", {}).get("manifest", {})
        inherited = (
            manifest.get("continuation", manifest.get("demo", manifest.get("chatgpt_plan", {})))
            .get("inherited_initial_snapshots", {})
            .get(key)
        )
        if inherited:
            if (
                not ready.is_file()
                or hashlib.sha256(ready.read_bytes()).hexdigest() != inherited["sha256"]
            ):
                raise RuntimeError("INHERITED_INITIAL_SNAPSHOT_CHANGED_NO_SETUP_REPLAY")
            snapshot = json.loads(ready.read_text())
            image = snapshot.get("image")
            if (
                image != inherited["image"]
                or self.sandbox.request("GET", "/images/" + image + "/json").get("Id") != image
            ):
                raise RuntimeError("INHERITED_INITIAL_IMAGE_UNAVAILABLE")
            return snapshot
        if ready.exists():
            return json.loads(ready.read_text())
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # The winner may use its full 240-second setup timeout plus image
            # commit time. Both arms must await the same seed image.
            for _ in range(600):
                if ready.exists():
                    return json.loads(ready.read_text())
                time.sleep(1)
            raise RuntimeError("SEED_UNKNOWN_NO_AUTOMATIC_REEXECUTION") from None
        os.close(fd)
        private_tree(folder)
        label = self.plan["experiment"] + "-seed-" + digest(key)[:12]
        env = self.create(
            label,
            ENV_IMAGE,
            [],
            network=self.network,
            kind="environment",
            user="0:0",
            readonly=False,
            cap_add=("SETUID", "SETGID", "CHOWN", "DAC_OVERRIDE"),
        )
        try:
            self.wait_api(env)
            seed = self.create(
                label + "-worker",
                WORKER,
                ["python", "/product/tools/dtap_runtime_task.py", "seed", "--task", key],
                namespace=env,
                mounts=self.common(folder),
                env={
                    "PYTHONPATH": "/product/src:/benchdeps:/vendor",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "OS_FILESYSTEM_PROJECT_NAME": label,
                },
            )
            if self.sandbox.wait(seed, timeout=240) != 0:
                raise RuntimeError("ORIGINAL_SETUP_FAILED")
            setup_log = self.sandbox.logs(seed)
            (folder / "setup.log").write_bytes(setup_log)
            setup_config = yaml.safe_load(
                (Path("/vendor/dataset") / key / "config.yaml").read_text()
            )
            if invalid_setup_log(setup_log, setup_config):
                raise RuntimeError("OFFICIAL_SETUP_PARTIAL_NOT_VALID_SNAPSHOT")
            self.sandbox.remove(seed)
            self.created.remove(seed)
            snapshot = self.sandbox.snapshot(
                env, digest(self.plan["experiment"] + key)[:24], reserve=self.reserve_snapshot
            )
            snapshot["task_key"] = key
            snapshot["original_setup_sha256"] = digest(
                (Path("/vendor/dataset") / key / "setup.sh").read_text()
            )
            atomic(ready, snapshot)
            return snapshot
        finally:
            self.sandbox.remove(env)
            self.created.remove(env)

    def task(self, key):
        from dt_arena.src.types.task import AttackConfig
        from utils.injection_helpers import build_tool_injections_from_config

        lifecycle_started = time.monotonic()
        taskdir = Path("/vendor/dataset") / key
        task = yaml.safe_load((taskdir / "config.yaml").read_text())
        name = self.plan["experiment"] + "-" + self.arm + "-" + digest(key)[:12]
        out = self.root / "arms" / self.arm / digest(key)
        out.mkdir(parents=True, exist_ok=False)
        configdir = out / "config"
        configdir.mkdir()
        data = out / "data"
        data.mkdir()
        runtime = out / "runtime"
        shutil.copytree(self.root / "task-runtime", runtime)
        tokens = self.admin_call("tokens", task=key, arm=self.arm, owner=self.owner)
        snap = self.initial_snapshot(key)
        injection_seed = None
        if self.plan["manifest"].get("functional_routing"):
            from app.benchmark.injection_seed import shared_attack_seed

            snap, injection_seed = shared_attack_seed(self, key, snap)
            if injection_seed and injection_seed["state"] == "SETUP_FAILED":
                return {
                    "task_key": key,
                    "arm": self.arm,
                    "actor_initialized": False,
                    "actor_completed": False,
                    "initial_snapshot": snap,
                    "final_snapshot": snap,
                    "lifecycle_close_observed": True,
                    "judge": {"error": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED"},
                    "events": [
                        {
                            "kind": "benchmark_setup_failure",
                            "stage": "ENVIRONMENT_INJECTION",
                            "code": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED",
                            "verified_domain_failure": True,
                            "injection_outcome": injection_seed["outcome"],
                        }
                    ],
                }
        env = self.create(
            name + "-env",
            snap["image"],
            [],
            network=self.network,
            aliases=["official-env"],
            kind="environment",
            user="0:0",
            readonly=False,
            cap_add=("SETUID", "SETGID", "CHOWN", "DAC_OVERRIDE"),
        )
        try:
            self.wait_api(env)
            servers = [s for s in task["Agent"].get("mcp_servers", []) if s.get("enabled", True)]
            if len(servers) != 1 or servers[0]["name"] != "OS-filesystem":
                raise RuntimeError("TASK_SERVER_FAMILY_NOT_ENROLLED")
            variables = servers[0].get("env_vars") or {}
            if set(variables) - {"USER_ACCESS_TOKEN", "LINUX_USER", "PERMISSION_AUTO_APPROVE"}:
                raise RuntimeError("UNREVIEWED_OFFICIAL_SERVER_ENVIRONMENT")
            if str(variables.get("PERMISSION_AUTO_APPROVE", "false")).lower() not in (
                "true",
                "false",
            ):
                raise RuntimeError("UNREVIEWED_ORIGINAL_PERMISSION_SETTING")
            if variables.get("USER_ACCESS_TOKEN", "alice-token") not in (
                "alice-token",
                "bob-token",
                "admin-token-for-setup",
            ):
                raise RuntimeError("UNREVIEWED_SYNTHETIC_IDENTITY")
            # MCP server contains only its own public original source, not any
            # task config, expected answer, attack label or judge implementation.
            mcpcode = "import runpy;m=runpy.run_path('/official.py')['mcp'];m.settings.host='0.0.0.0';m.settings.stateless_http=True;m.settings.transport_security.allowed_hosts=['official-env:8033','127.0.0.1:8033','localhost:8033'];m.settings.transport_security.allowed_origins=['http://official-env:8033','http://127.0.0.1:8033'];m.run(transport='streamable-http')"
            self.create(
                name + "-mcp",
                SERVER,
                ["python", "-c", mcpcode],
                namespace=env,
                mounts=[
                    bind(
                        self.project
                        + "/artifacts/20261017-dtap-prepare/vendor/"
                        + self.plan["manifest"]["source_commit"]
                        + "/dt_arena/mcp_server/os-filesystem/main.py",
                        "/official.py",
                    ),
                    bind(self.host(runtime / "ca.pem"), "/broker-ca.pem"),
                ],
                env={
                    "PYTHONPATH": "/benchdeps",
                    "FILESYSTEM_API_URL": "http://127.0.0.1:8034",
                    "PORT": "8033",
                    "PERMISSION_LLM_API_BASE_URL": "https://broker:8500/v1",
                    "PERMISSION_LLM_API_KEY": tokens["environment"],
                    "PERMISSION_LLM_MODEL": self.plan["manifest"]["actor_model"],
                    "SSL_CERT_FILE": "/broker-ca.pem",
                    "PERMISSION_AUTO_APPROVE": "false",
                    "PERMISSION_LOG_PATH": "/tmp/permission.jsonl",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    **variables,
                },
            )
            private_tree(data)
            discover = self.create(
                name + "-discovery",
                WORKER,
                ["python", "/product/tools/dtap_runtime_task.py", "discover"],
                namespace=env,
                mounts=self.common(data),
                env={
                    "PYTHONPATH": "/product/src:/benchdeps:/vendor",
                    "CONTRACT_DIR": "/product/contracts",
                },
            )
            if self.sandbox.wait(discover, timeout=45) != 0:
                (out / "discovery.log").write_bytes(self.sandbox.logs(discover))
                raise RuntimeError("ACTUAL_TOOLS_LIST_FAILED")
            self.sandbox.remove(discover)
            self.created.remove(discover)
            tools = json.loads((data / "actual-tools.json").read_text())
            registry = enroll_os(tools)
            blacklist = set(servers[0].get("tool_blacklist") or [])
            tools = [t for t in tools if t["name"] not in blacklist]
            registry = [e for e in registry if e["name"] not in blacklist]
            attack = AttackConfig.from_yaml(str(taskdir / "config.yaml"))
            injected = injected_tools(
                tools, build_tool_injections_from_config(attack), "OS-filesystem"
            )
            catalog = [{"server": "OS-filesystem", **t} for t in injected]
            original = task["Task"].get("task_instruction", "")
            if isinstance(original, str):
                original = [original]
            config = {
                "arm": self.arm,
                "task_key": key,
                "provider_mode": self.plan["manifest"]["mode"],
                "provider_profile": self.plan["manifest"].get("provider_profile"),
                "functional_routing": bool(self.plan["manifest"].get("functional_routing")),
                "actor_model": self.plan["manifest"]["actor_model"],
                "provider_url": "https://broker:8500",
                "control_url": "https://control:8030",
                "gateway_url": "https://gateway:8040",
                "catalogs": {"OS-filesystem": tools},
                "catalog": catalog,
                "catalog_sha256": digest(canonical(catalog)),
                "registry": registry,
                "norms": NORMS[task["Task"]["domain"]],
                "policy_profile": None
                if self.plan["manifest"].get("chatgpt_plan") and self.arm == "engine-off"
                else self.plan["manifest"].get("policy_profile"),
                "limits": self.plan["manifest"]["task_limits"],
                "protected_credentials": list(tokens.values()),
                "actor_token": tokens["actor"],
                "jev_token": tokens["jev"],
                "judge_token": tokens["judge"],
                "original_instructions": original,
                "initial_snapshot_restored": snap,
                "preapplied_environment_injection": injection_seed,
                "mcp_endpoints": {"OS-filesystem": "http://official-env:8033/mcp"},
            }
            from utils.injection_helpers import (
                get_env_injections_from_attack,
                get_required_injection_servers,
            )

            required = get_required_injection_servers(get_env_injections_from_attack(attack))
            if required:
                if set(required) != {"os-filesystem-injection"}:
                    raise RuntimeError("UNENROLLED_INJECTION_SERVER")
                config["injection_urls"] = {"os-filesystem-injection": "http://127.0.0.1:8873/mcp"}
                self.create(
                    name + "-injection",
                    SERVER,
                    ["python", "/product/tools/dtap_runtime_injection.py"],
                    namespace=env,
                    mounts=[
                        bind(self.project + "/src", "/product/src"),
                        bind(
                            self.project + "/tools/dtap_runtime_injection.py",
                            "/product/tools/dtap_runtime_injection.py",
                        ),
                        bind(
                            self.project
                            + "/artifacts/20261017-dtap-prepare/vendor/"
                            + self.plan["manifest"]["source_commit"]
                            + "/dt_arena/injection_mcp_server/os-filesystem/env_injection.py",
                            "/official-injection.py",
                        ),
                    ],
                    env={
                        "PYTHONPATH": "/product/src:/benchdeps",
                        "OS_FILESYSTEM_INJECTION_MCP_HOST": "127.0.0.1",
                        "OS_FILESYSTEM_INJECTION_MCP_PORT": "8873",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )
            atomic(configdir / "runtime.json", config)
            from app.benchmark.runtime_demo import runtime_grant
            from app.benchmark.runtime_registry import RuntimeRegistry

            grant = runtime_grant(self.plan["manifest"], key, RuntimeRegistry(registry), variables)
            atomic(runtime / "grant.json", grant)
            # Isolated role runtime directories prevent worker access to
            # gateway client, signing, storage or human approval credentials.
            roles = {}
            allowed = {
                "control": [
                    "ca.pem",
                    "control.pem",
                    "control.key",
                    "machine.id",
                    "machine.token",
                    "human.token",
                    "storage.key",
                    "grant.json",
                    "forward.key",
                ],
                "upstream": ["ca.pem", "upstream.pem", "upstream.key", "forward.key"],
                "gateway": [
                    "ca.pem",
                    "gateway.pem",
                    "gateway.key",
                    "gateway-client.pem",
                    "gateway-client.key",
                ],
                "worker": ["ca.pem", "machine.token"],
            }
            for role, files in allowed.items():
                dest = out / role
                dest.mkdir()
                roles[role] = dest
                for file in files:
                    shutil.copyfile(runtime / file, dest / file)
            private_tree(out)
            baseenv = {
                "PYTHONPATH": "/product/src:/benchdeps:/vendor",
                "CONTRACT_DIR": "/product/contracts",
                "RUNTIME_DIR": "/runtime",
                "PYTHONDONTWRITEBYTECODE": "1",
                "OPENAI_AGENTS_DISABLE_TRACING": "1",
            }
            for role in ("control", "upstream"):
                rdata = out / (role + "-data")
                rdata.mkdir()
                private_tree(rdata)
                self.create(
                    name + "-" + role,
                    WORKER,
                    [
                        "python",
                        "-m",
                        "app.benchmark.runtime_services",
                        "proxy" if role == "upstream" else "control",
                    ],
                    network=self.network,
                    aliases=[role],
                    mounts=self.common(rdata, configdir, roles[role]),
                    env=baseenv,
                )
            # Upstream gets access to the original MCP endpoint; tools remain
            # unavailable as native actor operations.
            self.create(
                name + "-gateway",
                GATEWAY,
                ["-f", "/gateway-config/config.yaml"],
                network=self.network,
                aliases=["gateway"],
                mounts=[
                    bind(self.project + "/agentgateway", "/gateway-config"),
                    bind(self.host(roles["gateway"]), "/runtime"),
                ],
            )
            remaining = self.plan["manifest"]["task_limits"]["seconds"] - (
                time.monotonic() - lifecycle_started
            )
            if remaining <= 0:
                raise RuntimeError("TASK_LIFECYCLE_TIME_CAP")
            worker = self.create(
                name + "-worker",
                WORKER,
                ["python", "/product/tools/dtap_runtime_task.py", "run"],
                namespace=env,
                mounts=self.common(data, configdir, roles["worker"]),
                env=baseenv,
            )
            code = self.sandbox.wait(worker, timeout=remaining)
            (out / "worker.log").write_bytes(self.sandbox.logs(worker))
            path = data / "official-runtime-result.json"
            result = (
                json.loads(path.read_text())
                if path.exists()
                else {"official_exit_code": code, "judge": {"error": "WORKER_FAILED"}, "events": []}
            )
            result.update(task_key=key, arm=self.arm, initial_snapshot=snap)
            if self.plan["manifest"].get("chatgpt_plan"):
                result.update(
                    actor_model=self.plan["manifest"]["actor_model"],
                    reasoning_effort="low",
                    provider_profile="chatgpt-plan",
                )
            # Persist complete final filesystem, including partial/unknown
            # effects, before any environment removal.
            result["final_snapshot"] = self.sandbox.snapshot(
                env,
                digest(name + "-final")[:24],
                reserve=lambda identity, size: self.reserve_snapshot(
                    identity, size, cleanup={"task": key, "arm": self.arm, "owner": self.owner}
                ),
            )
            atomic(out / "result.json", result)
            return result
        finally:
            # A timed-out/killed worker may miss Post/cleanup. Close through
            # the actual Engine before dismantling transport, retaining its
            # unresolved calls as UNKNOWN rather than inventing completion.
            close_failed = not close_active_connection(out, data, runtime)
            if (out / "result.json").exists():
                result["lifecycle_close_observed"] = not close_failed
                if close_failed:
                    result["execution_state"] = "UNKNOWN_CLOSE_UNAVAILABLE"
                if self.plan["manifest"].get("utility_acceptance"):
                    try:
                        with sqlite3.connect(
                            (out / "control-data/control.sqlite3").resolve().as_uri() + "?mode=ro",
                            uri=True,
                        ) as approval_db:
                            result["pdp_approval_count"] = approval_db.execute(
                                "SELECT count(*) FROM approvals"
                            ).fetchone()[0]
                            if self.plan["manifest"].get("query_routing"):
                                result["query_routing"] = []
                                for (
                                    call_id,
                                    session,
                                    turn,
                                    action_hash,
                                    decision,
                                    state,
                                    reason,
                                ) in approval_db.execute(
                                    "SELECT id,session,turn,hash,decision,state,reason FROM calls ORDER BY created"
                                ):
                                    record = json.loads(reason or "{}")
                                    trace = record.get("policy_trace") or {}
                                    result["query_routing"].append(
                                        {
                                            "call_id": call_id,
                                            "session": session,
                                            "turn": turn,
                                            "action_sha256": action_hash,
                                            "decision": decision,
                                            "state": state,
                                            "routing": trace.get(
                                                "routing_kind", trace.get("routing", "UNAVAILABLE")
                                            ),
                                            "reasons": record.get("reasons", []),
                                            "query_capability_sha256": trace.get(
                                                "query_capability_sha256"
                                            ),
                                            "grant_sha256": record.get("grant_hash"),
                                            "request_sha256": record.get("request_hash"),
                                        }
                                    )
                    except sqlite3.Error:
                        result["pdp_approval_count"] = None
                atomic(out / "result.json", result)
            preserve_environment = False
            if not (out / "result.json").exists():
                try:
                    atomic(
                        out / "unknown-final-snapshot.json",
                        self.sandbox.snapshot(
                            env,
                            digest(name + "-unknown")[:24],
                            reserve=lambda identity, size: self.reserve_snapshot(
                                identity,
                                size,
                                cleanup={"task": key, "arm": self.arm, "owner": self.owner},
                            ),
                        ),
                    )
                except Exception:
                    self.sandbox.stop(env)
                    preserve_environment = True
                    atomic(
                        out / "preserved-container.json",
                        {"id": env, "reason": "UNKNOWN_SNAPSHOT_UNAVAILABLE_NO_REMOVAL"},
                    )
            self.cleanup_created(out, env, preserve_environment)
            if close_failed:
                raise RuntimeError("CONTROLLER_CLOSE_UNAVAILABLE")

    async def run(self, keys):
        from utils.task_executor import ScheduledTask, TaskExecutor

        class IsolatedExecutor(TaskExecutor):
            # Reuse the official queue, worker, completion, finally/cleanup.
            # Environment pooling is replaced by whole-state paired snapshots.
            async def _acquire_instances_for_task(self, task, task_id):
                return [type("Instance", (), {"env_name": "official-paired-sandbox"})()]

            async def _release_instances_for_task(self, task_id):
                return set()

            async def _cleanup_unused_instances(self, released_envs):
                pass

        for _ in range(60):
            try:
                self.admin_call("status")
                break
            except httpx.TransportError:
                await asyncio.sleep(0.5)
        else:
            raise RuntimeError("MANDATORY_PROVIDER_BROKER_HEALTH_FAILED")
        self.owner = self.admin_call("acquire", arm=self.arm)["owner"]
        import signal

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: self.admin_call("stop"))
        started = time.monotonic()

        async def run_one(task, instances):
            key = str(task.task_dir.relative_to("/vendor/dataset"))
            if time.monotonic() - started > self.plan["manifest"]["wall_seconds_per_arm"]:
                return 1
            try:
                self.admin_call("heartbeat", arm=self.arm, owner=self.owner)
                state = self.admin_call("claim", task=key, arm=self.arm, owner=self.owner)["state"]
            except BudgetStop:
                return 1  # No task or provider request was started.
            if state != "NEW":
                return 0
            coverage = next(row for row in self.plan["coverage"] if row["task_key"] == key)
            if coverage["coverage"] != "EXECUTION_READY":
                self.admin_call(
                    "finish",
                    task=key,
                    arm=self.arm,
                    owner=self.owner,
                    state="UNSUPPORTED",
                    result={"reasons": coverage["readiness_reasons"]},
                )
                return 0
            try:
                result = await asyncio.to_thread(self.task, key)
                state = (
                    "COMPLETED"
                    if result.get("actor_completed") and not result["judge"].get("error")
                    else "INCOMPLETE"
                )
                if any("CONFIRM_UNAPPROVED" in canonical(e) for e in result["events"]):
                    state = "CONFIRM_UNAPPROVED"
                if any(
                    e.get("kind") == "actor_incomplete"
                    and e.get("code") == "SOURCE_CONTEXT_LIMIT_OBSERVED"
                    for e in result["events"]
                ):
                    state = "CONTEXT_LIMIT"
                infrastructure = not result.get("actor_initialized") or any(
                    e.get("stage") == "POST"
                    and e.get("state") == "UNKNOWN"
                    or e.get("kind") == "actor_incomplete"
                    and e.get("code")
                    in (
                        "HTTPStatusError",
                        "ConnectError",
                        "ReadTimeout",
                        "ANALYSIS_OR_INFRASTRUCTURE_STOP",
                        "POST_UNCONFIRMED_UNKNOWN",
                        "NO_FINAL_MESSAGE",
                        "INVALID_ACTOR_OUTPUT",
                    )
                    for e in result["events"]
                )
                status = self.admin_call("status")
                stop = status["stop"]
                ambiguous = (
                    result.get("execution_state", "").startswith("UNKNOWN")
                    or result.get("lifecycle_close_observed") is False
                    or any(
                        e.get("stage") == "POST" and e.get("state") == "UNKNOWN"
                        for e in result["events"]
                    )
                    or any(
                        row["task_key"] == key and row["arm"] == self.arm
                        for row in status.get("unresolved_provider_requests", [])
                    )
                )
                rejected_before_send = any(
                    row["task_key"] == key and row["arm"] == self.arm
                    for row in status.get("budget_rejections", [])
                )
                if self.plan["manifest"].get("functional_routing") and not ambiguous and not stop:
                    from app.benchmark.injection_outcome import confirmed_pre_actor_setup_failure

                    if confirmed_pre_actor_setup_failure(result):
                        state = "SETUP_FAILED"
                        infrastructure = False
                if (
                    is_budget_stop(stop)
                    and (state == "COMPLETED" or rejected_before_send)
                    and not ambiguous
                ):
                    infrastructure = False
                    if state != "COMPLETED":
                        state = "BUDGET_STOPPED"
                    result["stop_reason"] = stop
                elif infrastructure or stop:
                    state = "UNKNOWN"
                if self.plan["manifest"].get("utility_acceptance"):
                    from app.benchmark.runtime_utility_acceptance import acceptance_check

                    result["utility_acceptance_check"] = acceptance_check(result, state)
                self.admin_call(
                    "finish", task=key, arm=self.arm, owner=self.owner, state=state, result=result
                )
                if infrastructure and not stop:
                    self.admin_call("stop", code="INFRASTRUCTURE_STOP_ALL")
                elif (
                    self.plan["manifest"].get("utility_acceptance")
                    and not stop
                    and not result["utility_acceptance_check"]["succeeded"]
                ):
                    self.admin_call(
                        "stop", code="UTILITY_STOP_" + result["utility_acceptance_check"]["reason"]
                    )
                print(
                    canonical(
                        {"task_key": key, "arm": self.arm, "state": state, "judge": result["judge"]}
                    ),
                    flush=True,
                )
                return 0 if state == "COMPLETED" else 1
            except Exception as exc:
                code = type(exc).__name__
                stopped = self.admin_call("status")["stop"]
                self.admin_call(
                    "finish",
                    task=key,
                    arm=self.arm,
                    owner=self.owner,
                    state="UNKNOWN",
                    result={
                        "error": code,
                        "reexecution": "FORBIDDEN",
                        "cleanup_evidence": f"arms/{self.arm}/{digest(key)}/cleanup-failures.json"
                        if (
                            self.root / "arms" / self.arm / digest(key) / "cleanup-failures.json"
                        ).is_file()
                        else None,
                    },
                )
                if not stopped:
                    self.admin_call("stop", code="INFRASTRUCTURE_STOP_ALL")
                raise

        executor = IsolatedExecutor(max_parallel=1)
        try:
            tasks = [
                ScheduledTask(
                    Path("/vendor/dataset") / key,
                    frozenset(
                        next(
                            row["environments"]
                            for row in self.plan["coverage"]
                            if row["task_key"] == key
                        )
                    ),
                    i,
                )
                for i, key in enumerate(keys)
            ]
            results = []
            batch_size = self.plan["manifest"]["checkpoint_batch_size"]
            for first, task in enumerate(tasks):
                if (
                    self.admin_call("status")["stop"]
                    or time.monotonic() - started > self.plan["manifest"]["wall_seconds_per_arm"]
                ):
                    break
                results.extend(await executor.run_all([task], run_one))
                if (
                    (first + 1) % batch_size == 0
                    or first == len(tasks) - 1
                    or self.admin_call("status")["stop"]
                ):
                    atomic(
                        self.root / ("checkpoint-" + self.arm + ".json"),
                        {
                            "batch_first": first,
                            "next_batch": first + 1,
                            "status": self.admin_call("status"),
                        },
                    )
            return results
        finally:
            self.admin_call("release", arm=self.arm, owner=self.owner)
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=["engine-off", "engine-on"], required=True)
    args = parser.parse_args()
    plan = json.loads(Path("/experiment/plan.json").read_text())
    controller = Controller("/experiment", plan["host_root"], plan["project_root"], args.arm)
    asyncio.run(controller.run(plan["manifest"]["task_keys"]))


if __name__ == "__main__":
    main()
