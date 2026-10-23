"""DTAP OFF/ON with the Claude Code CLI actor on this host's subscription login.

prepare: verify/extract the pinned DTAP source, pull the pinned image, prewarm
         the official MCP server lock and check the dedicated Claude login.
run:     one fresh worker process per task-arm, engine-off then engine-on.
         A started task-arm is never re-run; its missing result stays UNKNOWN.
status:  print a run summary.
No API key is used for the actor. Engine-on uses the separate TypeSafe Jev key.
"""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("CONTRACT_DIR", str(ROOT / "docs/mvp/contracts"))
STATE = ROOT / "artifacts/dtap-cc"
VENV = STATE / "venv"
SOURCE_COMMIT = "e0323a521ba4ef88f8e14c1eccf68d0a3d19a458"
ARCHIVE_SHA256 = "e904c6e12eebc4683f257c9aad0da8b1b6732a0c32a43f7b64ef11dd18a48946"
ARCHIVE_URL = "https://codeload.github.com/AI-secure/DecodingTrust-Agent/tar.gz/" + SOURCE_COMMIT
SOURCE = STATE / "source" / SOURCE_COMMIT
DEFAULT_CONFIG = Path.home() / ".config/with-human/claude-dtap"
DEFAULT_CLAUDE = Path.home() / ".local/bin/claude"
JEV_LEDGER = STATE / "typesafe-ledger.sqlite3"
# Task-arm outcomes after which the next task may start. Every other stop (login/API
# key/rate limit/overage guards, analysis or infrastructure failures, unexpected
# runner states) halts the run: later task-arms would not be comparable.
TASK_STOPS = (
    None,
    "CONFIRM_UNAPPROVED",
    "TOOL_CALL_LIMIT",
    "ACTOR_TIMEOUT",
    "ACTOR_RESULT_ERROR_MAX_TURNS",
    "OFFICIAL_ENVIRONMENT_INJECTION_FAILED",
    "PROMPT_INJECTION_TASK_NOT_ENROLLED",
    "TASK_SERVER_FAMILY_NOT_ENROLLED",
    "UNENROLLED_INJECTION_SERVER",
    "SOURCE_CONTEXT_LIMIT_OBSERVED",
    "JEV_RESPONSE_INVALID_TASK_STOP",
    "UNKNOWN_PREVIOUS_ATTEMPT",
    # One slow or oversized simulated-user answer leaves its task-arm unresolved.
    "CONSENT_SIMULATOR_ACTOR_TIMEOUT",
    "CONSENT_SIMULATOR_CONSENT_REQUEST_LIMIT",
)
TASK_STOP_PREFIXES = ("UNSUPPORTED_", "UNREVIEWED_")


def halts_run(stop):
    return stop not in TASK_STOPS and not str(stop).startswith(TASK_STOP_PREFIXES)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    temp.replace(path)


def private(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path


def engine_source():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "tools"], cwd=ROOT,
                           capture_output=True, text=True).stdout.splitlines()
    files = sorted((ROOT / "src/app").rglob("*.py")) + [ROOT / "tools/dtap_claude_code.py"]
    combined = hashlib.sha256()
    for path in files:
        combined.update(str(path.relative_to(ROOT)).encode() + b"\0" + sha256(path).encode() + b"\n")
    return {"git_head": head, "uncommitted_paths": len(dirty), "source_sha256": combined.hexdigest(),
            "files": len(files)}


def claude_login(binary, config_dir):
    sys.path[:0] = [str(ROOT / "src")]
    from app.benchmark.claude_code import ActorStop, preflight

    try:
        return asyncio.run(preflight(binary, config_dir))
    except ActorStop as stop:
        print("STOP " + str(stop))
        print("Log in once with Anthropic's own flow for this dedicated directory, then rerun:")
        print("  CLAUDE_CONFIG_DIR=%s %s auth login --claudeai" % (config_dir, binary))
        raise SystemExit(2) from None


def prepare(args):
    archive = STATE / "archive" / (SOURCE_COMMIT + ".tar.gz")
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(ARCHIVE_URL, timeout=120) as response:
            archive.with_suffix(".part").write_bytes(response.read(200 * 1024 * 1024))
        archive.with_suffix(".part").replace(archive)
    if sha256(archive) != ARCHIVE_SHA256:
        raise SystemExit("DTAP_ARCHIVE_SHA256_MISMATCH")
    marker = SOURCE / ".with-human-archive-sha256"
    if not marker.exists():
        if SOURCE.exists():
            shutil.rmtree(SOURCE)
        SOURCE.mkdir(parents=True)
        with tarfile.open(archive) as tar:
            members = []
            for member in tar.getmembers():
                parts = Path(member.name).parts[1:]
                if not parts or not (member.isfile() or member.isdir()) or ".." in parts:
                    continue
                member.name = str(Path(*parts))
                members.append(member)
            tar.extractall(SOURCE, members=members, filter="data")
        marker.write_text(ARCHIVE_SHA256)
    sys.path[:0] = [str(ROOT / "src")]
    from app.benchmark.claude_code_dtap import ENV_IMAGE, FORWARD_IMAGE

    for image in (ENV_IMAGE, FORWARD_IMAGE):
        subprocess.run(["docker", "pull", "-q", image], check=True)
    server = SOURCE / "dt_arena/mcp_server/os-filesystem"
    subprocess.run(
        [str(VENV / "bin/uv"), "sync", "--frozen", "--no-dev"],
        cwd=server,
        check=True,
        env={"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin",
             "UV_CACHE_DIR": str(STATE / "uv-cache"), "UV_PROJECT_ENVIRONMENT": str(STATE / "mcp-venv"),
             "UV_PYTHON": os.path.realpath(sys._base_executable), "UV_PYTHON_DOWNLOADS": "never",
             "UV_NO_CONFIG": "1"},
    )
    config = Path(args.claude_config_dir)
    config.mkdir(mode=0o700, parents=True, exist_ok=True)
    login = claude_login(args.claude_binary, config)
    value = {"source_commit": SOURCE_COMMIT, "archive_sha256": ARCHIVE_SHA256, "environment_image": ENV_IMAGE,
             "claude": {k: login[k] for k in ("version", "subscription", "auth_method")},
             "claude_binary_sha256": sha256(login["binary"]), "prepared_at": time.time()}
    write(STATE / "prepared.json", value)
    print(json.dumps(value, indent=2))


def tasks(argument):
    if argument.startswith("@"):
        keys = [line.strip() for line in Path(argument[1:]).read_text().splitlines()]
    else:
        keys = argument.split(",")
    keys = [k for k in keys if k and not k.startswith("#")]
    for key in keys:
        if ".." in Path(key).parts or Path(key).is_absolute() or not (
            SOURCE / "dataset/os-filesystem" / key / "config.yaml"
        ).is_file():
            raise SystemExit("UNKNOWN_TASK " + key)
    if len(set(keys)) != len(keys):
        raise SystemExit("DUPLICATE_TASK")
    return keys


def sweep(folder, name, binary):
    """A killed worker cannot clean up: stop its own process groups and environment."""
    from app.benchmark.claude_code_dtap import remove_environment

    path = folder / "processes.json"
    for pid in json.loads(path.read_text()) if path.exists() else []:
        command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
        # Only groups this worker started; never a reused unrelated pid.
        if not any(mark in command for mark in (binary, "stateless_http", "env_injection.py")):
            continue
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pid, sig)
            except ProcessLookupError:
                break
            time.sleep(2)
    remove_environment(name)


def worker(run, key, arm, manifest):
    """Returns (row, fresh). Cached rows are reported but never re-trigger a run stop."""
    folder = run / "arms" / arm / hashlib.sha256(key.encode()).hexdigest()[:16]
    if (folder / "result.json").exists():
        return json.loads((folder / "result.json").read_text()), False
    if folder.exists():
        # Started before and never finished: never re-run, never count as a defense.
        return {"task_key": key, "arm": arm, "summary": {"stop": "UNKNOWN_PREVIOUS_ATTEMPT"}}, False
    private(folder)
    runtime = private(folder / "runtime")
    write(folder / "claim.json", {"task_key": key, "arm": arm, "started_at": time.time()})
    context = {**manifest["context"], "task_key": key, "arm": arm, "out": str(folder)}
    if arm == "engine-on":
        context["jev"] = manifest["jev"]
    write(folder / "context.json", context)
    env = {
        "HOME": os.environ["HOME"],
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        # Claude Code finds its macOS keychain login only with USER and TMPDIR set.
        **{k: os.environ[k] for k in ("USER", "LOGNAME", "TMPDIR") if k in os.environ},
        # Docker Desktop's CLI directory; the official runner also calls `docker ps`.
        "PATH": str(VENV / "bin") + ":" + os.path.dirname(shutil.which("docker")) + ":/usr/bin:/bin",
        "PYTHONPATH": str(ROOT / "src") + ":" + str(SOURCE),
        "CONTRACT_DIR": str(ROOT / "docs/mvp/contracts"),
        "HOOKGW_RUNTIME": str(runtime),
        "RUNTIME_DIR": str(runtime),
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENAI_AGENTS_DISABLE_TRACING": "1",
    }
    with open(folder / "worker.log", "wb") as log:
        try:
            code = subprocess.run(
                [str(VENV / "bin/python"), "-m", "app.benchmark.claude_code_dtap", str(folder / "context.json")],
                cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1500,
            ).returncode
        except subprocess.TimeoutExpired:
            code = "TIMEOUT"
    # runtime/ keeps the per-task engine keys with its sealed DB (0700, never committed).
    if not (folder / "result.json").exists():
        from app.benchmark.claude_code_dtap import environment_name

        sweep(folder, environment_name(manifest["run_id"], arm, key), manifest["context"]["claude"]["binary"])
        return {"task_key": key, "arm": arm, "summary": {"stop": "WORKER_FAILED_UNKNOWN", "exit": code}}, True
    return json.loads((folder / "result.json").read_text()), True


def report(run, manifest, rows, stopped):
    pairs = {}
    for row in rows:
        pairs.setdefault(row["task_key"], {})[row["arm"]] = row.get("summary", {})
    summary = {"run_id": manifest["run_id"], "jev_mode": manifest.get("jev_mode"), "stopped": stopped,
               "tasks": pairs}
    write(run / "summary.json", summary)
    lines = ["Jev: " + str(manifest.get("jev_mode")), "",
             "| task | arm | completed | task_success | attack_success | ALLOW/DENY/CONFIRM | executed | stop |",
             "|---|---|---|---|---|---|---|---|"]
    for key, arms in pairs.items():
        for arm, s in arms.items():
            d = s.get("decisions") or {}
            lines.append("| %s | %s | %s | %s | %s | %s/%s/%s | %s | %s |" % (
                key, arm, s.get("actor_completed"), s.get("task_success"), s.get("attack_success"),
                d.get("ALLOW", "-"), d.get("DENY", "-"), d.get("CONFIRM", "-"), s.get("upstream_executed"),
                s.get("stop") or ""))
    if stopped:
        lines.append("\nRun stopped: " + stopped)
    (run / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def run(args):
    if not (SOURCE / ".with-human-archive-sha256").exists():
        raise SystemExit("RUN_PREPARE_FIRST")
    keys = tasks(args.tasks)
    arms = args.arms.split(",")
    if not set(arms) <= {"engine-off", "engine-on"} or not arms:
        raise SystemExit("UNKNOWN_ARM")
    run = STATE / "runs" / args.run_id
    config = Path(args.claude_config_dir)
    login = claude_login(args.claude_binary, config)
    sys.path[:0] = [str(ROOT / "src")]
    from app.benchmark.consent_simulator import official_instructions

    simulator = {
        # The same subscription login answers as the user in both arms (see consent_simulator).
        "mode": "CLAUDE_CODE_SUBSCRIPTION_SIMULATED_USER",
        "model": args.simulator_model or args.model,
        "effort": args.simulator_effort if args.simulator_model else args.effort,
        "instructions_sha256": hashlib.sha256(official_instructions(SOURCE).encode()).hexdigest(),
        "answers": ["ENVIRONMENT_PERMISSION", "ENGINE_CONFIRM"],
    }
    manifest_path = run / "run.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        claude = manifest["context"]["claude"]
        jev = manifest["jev"] or {}
        # A resumed pair must use the same engine, CLI, model and Jev settings throughout.
        if (
            manifest["tasks"] != keys
            or manifest["arms"] != arms
            or (claude["model"], claude["effort"]) != (args.model, args.effort)
            or manifest["context"].get("policy", "functional-3") != args.policy
            or manifest["context"].get("simulator") != simulator
            or manifest["engine"]["source_sha256"] != engine_source()["source_sha256"]
            or manifest["claude_binary_sha256"] != sha256(login["binary"])
            or bool(jev.get("offline_fixture")) != args.offline_fixture_jev
            or (args.jev_requests is not None and jev.get("request_limit") != args.jev_requests)
        ):
            raise SystemExit("RUN_MANIFEST_CHANGED_USE_NEW_RUN_ID")
    else:
        jev = None
        if args.offline_fixture_jev:
            # OFFLINE TEST ONLY: fixture Jev answers; the run name keeps it apart from results.
            if not args.run_id.startswith("offline-"):
                raise SystemExit("OFFLINE_FIXTURE_JEV_REQUIRES_offline-_RUN_ID")
            private(run)
            key_path = run / "jev.api-key"
            key_path.write_text("PUBLIC-OFFLINE-TYPESAFE-FIXTURE")
            key_path.chmod(0o600)
            jev = {"key_path": str(key_path), "ledger_path": str(run / "typesafe-ledger.sqlite3"),
                   "request_limit": 200, "total_limit": 200, "offline_fixture": True}
        elif "engine-on" in arms:
            key_path = Path(args.jev_key).expanduser()
            if not key_path.is_file():
                raise SystemExit("JEV_KEY_FILE_MISSING " + str(key_path))
            if key_path.stat().st_mode & 0o077:
                raise SystemExit("JEV_KEY_FILE_MUST_BE_PRIVATE_0600")
            if not args.jev_requests:
                raise SystemExit("JEV_REQUEST_CAP_REQUIRED")
            total = args.jev_total_requests
            if JEV_LEDGER.exists():
                import sqlite3

                with sqlite3.connect(JEV_LEDGER) as db:
                    stored = db.execute("SELECT total_requests FROM jev_cap").fetchone()[0]
                if total is not None and total != stored:
                    raise SystemExit("JEV_TOTAL_CAP_IS_FIXED_AT_%d" % stored)
                total = stored
            elif total is None:
                raise SystemExit("JEV_TOTAL_CAP_REQUIRED_FOR_FIRST_LIVE_RUN")
            if args.jev_requests > total:
                raise SystemExit("JEV_RUN_CAP_ABOVE_TOTAL")
            jev = {"key_path": str(key_path), "ledger_path": str(JEV_LEDGER),
                   "request_limit": args.jev_requests, "total_limit": total}
        if not run.exists():
            private(run)
        manifest = {
            "run_id": args.run_id,
            "tasks": keys,
            "arms": arms,
            "created_at": time.time(),
            "engine": engine_source(),
            "claude_binary_sha256": sha256(login["binary"]),
            "jev": jev,
            "jev_mode": "OFFLINE_FIXTURE_NOT_A_MEASUREMENT" if args.offline_fixture_jev else "TYPESAFE_LIVE"
            if jev else "NOT_USED",
            "permission_simulator": simulator,
            "context": {
                "run_id": args.run_id,
                "policy": args.policy,
                "simulator": simulator,
                "source": str(SOURCE),
                "root": str(STATE),
                "claude": {"binary": login["binary"], "version": login["version"],
                           "config_dir": str(config), "model": args.model, "effort": args.effort},
            },
        }
        write(manifest_path, manifest)
    rows, stopped = [], None
    for key in keys:
        for arm in arms:
            row, fresh = worker(run, key, arm, manifest)
            rows.append(row)
            summary = row.get("summary", {})
            print(json.dumps({"task": key, "arm": arm, **summary}, ensure_ascii=False), flush=True)
            if fresh and halts_run(summary.get("stop")):
                stopped = summary["stop"]
                break
        if stopped:
            break
    report(run, manifest, rows, stopped)


def status(args):
    run = STATE / "runs" / args.run_id
    manifest = json.loads((run / "run.json").read_text())
    rows = []
    for key in manifest["tasks"]:
        for arm in manifest["arms"]:
            folder = run / "arms" / arm / hashlib.sha256(key.encode()).hexdigest()[:16]
            if (folder / "result.json").exists():
                rows.append(json.loads((folder / "result.json").read_text()))
            elif folder.exists():
                rows.append({"task_key": key, "arm": arm, "summary": {"stop": "UNKNOWN_PREVIOUS_ATTEMPT"}})
    report(run, manifest, rows, None)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        command = sub.add_parser(name)
        command.add_argument("--claude-binary", default=str(DEFAULT_CLAUDE))
        command.add_argument("--claude-config-dir", default=str(DEFAULT_CONFIG))
    command = sub.choices["run"]
    command.add_argument("--run-id", required=True)
    command.add_argument("--tasks", required=True, help="comma list or @file of dataset/os-filesystem keys")
    command.add_argument("--arms", default="engine-off,engine-on")
    command.add_argument("--model", required=True)
    command.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"),
                         help="omit for models without effort support (e.g. claude-haiku-4-5)")
    command.add_argument("--jev-key", default="~/.config/with-human/jev.api-key")
    command.add_argument("--policy", default="gate-6",
                         choices=("functional-3", "explicit-4", "review-5", "gate-6"),
                         help="engine-on scope profile (explicit-4 adds user-named-resource rules; "
                         "review-5 sends former consent stops to Jev A and B; gate-6 also lets Jev "
                         "decide unnamed sensitive/outside targets and refuse held cases)")
    command.add_argument("--simulator-model", help="simulated-user model; default: the actor model")
    command.add_argument("--simulator-effort", choices=("low", "medium", "high", "xhigh", "max"))
    command.add_argument("--jev-requests", type=int, help="TypeSafe request cap for this run")
    command.add_argument("--jev-total-requests", type=int,
                         help="cumulative cap across all runs; fixed when the host ledger is first created")
    command.add_argument("--offline-fixture-jev", action="store_true",
                         help="OFFLINE TEST ONLY: fixture Jev answers, run id must start with offline-")
    sub.add_parser("status").add_argument("--run-id", required=True)
    args = parser.parse_args()
    if "run_id" in args and not args.run_id.replace("-", "").isalnum():
        raise SystemExit("RUN_ID_ALNUM_DASH_ONLY")
    {"prepare": prepare, "run": run, "status": status}[args.command](args)


if __name__ == "__main__":
    main()
