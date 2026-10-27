"""Codex CLI connector for the current product; start is always user initiated."""
import argparse
import base64
import importlib.util
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit


def sibling(name):
    path = Path(__file__).with_name(name + ".py")
    if path.is_symlink():
        raise ValueError("CONNECTOR_LINK_REJECTED")
    spec = importlib.util.spec_from_file_location("product_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


send = sibling("hookgw_hook").send
launcher = sibling("hookgw_launch")

POLICY = "engine-2026-10-24-gate6-1"
ROLE_FILES = ("ca.pem", "machine.id", "machine.token", "human.token")


def export_bundle(runtime):
    """Local pipe to the Windows ACL-controlled writer; never use as a log."""
    source = runtime / "host"
    if source.is_symlink() or any(not (source / name).is_file() or (source / name).is_symlink() for name in ROLE_FILES):
        raise ValueError("HOST_CREDENTIALS_UNAVAILABLE")
    values = {name: (source / name).read_bytes() for name in ROLE_FILES}
    if any(not 1 <= len(value) <= 8192 for value in values.values()):
        raise ValueError("HOST_CREDENTIALS_UNAVAILABLE")
    return {name: base64.b64encode(value).decode("ascii") for name, value in values.items()}


def export_host(runtime, destination, workspace, control_port, gateway_port):
    """Copy only this new runtime's client credentials, never Jev/storage keys."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("NEW_HOST_DIRECTORY_REQUIRED")
    if not 1024 <= control_port <= 65535 or not 1024 <= gateway_port <= 65535 or control_port == gateway_port:
        raise ValueError("INVALID_PORTS")
    source = runtime / "host"
    if source.is_symlink() or any(not (source / name).is_file() or (source / name).is_symlink() for name in ROLE_FILES):
        raise ValueError("HOST_CREDENTIALS_UNAVAILABLE")
    destination.mkdir(mode=0o700)
    for name in ROLE_FILES:
        shutil.copyfile(source / name, destination / name)
        os.chmod(destination / name, 0o644 if name.endswith(".pem") else 0o600)
    profile = {"format": "product-codex-1", "workspace": workspace, "engine_workspace": "/files",
               "mcp_only": True, "control_url": f"https://127.0.0.1:{control_port}",
               "gateway_url": f"https://127.0.0.1:{gateway_port}/mcp"}
    (destination / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    os.chmod(destination / "profile.json", 0o600)
    print(json.dumps({"state": "CLIENT_PREPARED", "model_requests": 0, "personal_settings_changed": False}))


def profile_for(host):
    path = host / "profile.json"
    if host.is_symlink() or path.is_symlink():
        raise ValueError("PROFILE_LINK_REJECTED")
    profile = json.loads(path.read_text(encoding="utf-8"))
    if (profile.get("format") != "product-codex-1" or profile.get("mcp_only") is not True
            or profile.get("engine_workspace") != "/files"):
        raise ValueError("PRODUCT_PROFILE_REQUIRED")
    for key, expected_path in (("control_url", ""), ("gateway_url", "/mcp")):
        url = urlsplit(profile[key])
        if (url.scheme != "https" or url.hostname != "127.0.0.1" or not url.port
                or url.path != expected_path or url.query or url.fragment or url.username or url.password):
            raise ValueError("LOCAL_TLS_REQUIRED")
    if profile["control_url"] == profile["gateway_url"].removesuffix("/mcp"):
        raise ValueError("INVALID_PORTS")
    return profile


def check(host):
    profile_for(host)
    deadline = time.monotonic() + 15
    while True:
        try:
            health = send(host, "/health", None, method="GET", timeout=2)
            break
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            # Retry only a read-only local health probe, never a model/tool call.
            if isinstance(getattr(error, "reason", None), ssl.SSLCertVerificationError) or time.monotonic() >= deadline:
                raise
            time.sleep(.25)
    if health.get("decision_policy") != POLICY or health.get("judge_mode") != "JEV_USER_LIVE":
        raise ValueError("CURRENT_LIVE_GATE6_REQUIRED")
    return {"state": "READY", "policy": POLICY, "mode": health["judge_mode"], "model_requests": 0,
            "provider_authentication": "NOT_TESTED", "scope": "REGISTERED_FILE_MCP"}


def history(host):
    profile_for(host)
    return send(host, "/history/summary", None, human=True, method="GET")


def start(project, host, executable):
    profile = profile_for(host)
    workspace = Path(profile["workspace"]).resolve()
    if Path.cwd().resolve() != workspace:
        raise ValueError("ENROLLED_WORKSPACE_REQUIRED")
    if not executable.is_file() or executable.resolve().is_relative_to(workspace):
        raise ValueError("INSTALLED_CODEX_EXECUTABLE_REQUIRED")
    launcher.check_conflicts(workspace, [], strict_product=True)
    check(host)
    connection = send(host, "/connect", {})["connection"]
    try:
        # Keep user's login, model, sandbox and approval settings. No prompt injected.
        print("With Human: gate-6 / registered file MCP. Review /hooks when prompted.", flush=True)
        print("Use with_human read_file/write_file; its files are in the product Docker workspace.", flush=True)
        result = subprocess.run([str(executable), *launcher.overrides(project, host, sys.executable)],
                                env={**os.environ, "WITH_HUMAN_CONNECTION": connection}, check=False)
        return result.returncode
    finally:
        try:
            send(host, "/connections/close", {"connection": connection})
        except Exception:
            print("Connection close unconfirmed; inspect history before retrying.", file=sys.stderr)


def cli_check(project, host, executable):
    """Parse the installed CLI configuration without a session or model call."""
    profile = profile_for(host)
    workspace = Path(profile["workspace"]).resolve()
    if Path.cwd().resolve() != workspace:
        raise ValueError("ENROLLED_WORKSPACE_REQUIRED")
    if not executable.is_file() or executable.resolve().is_relative_to(workspace):
        raise ValueError("INSTALLED_CODEX_EXECUTABLE_REQUIRED")
    launcher.check_conflicts(workspace, [], strict_product=True)
    result = subprocess.run([str(executable), *launcher.overrides(project, host, sys.executable), "features", "list"],
                            capture_output=True, text=True, timeout=30, check=False)
    if result.returncode or not re.search(r"(?m)^hooks\s+\S+\s+true\s*$", result.stdout):
        raise ValueError("CODEX_HOOK_CONFIGURATION_UNAVAILABLE")
    return {"state": "CLI_CONFIGURATION_ACCEPTED", "model_requests": 0, "interactive_session": "NOT_STARTED"}


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("mode", choices=("export-host", "export-bundle", "check", "history", "security", "start", "cli-check"))
    parser.add_argument("--host", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--workspace")
    parser.add_argument("--control-port", type=int, default=8130)
    parser.add_argument("--gateway-port", type=int, default=8140)
    parser.add_argument("--exe", type=Path)
    args = parser.parse_args()
    if args.mode == "export-bundle":
        if args.runtime is None:
            parser.error("export-bundle requires --runtime")
        print(json.dumps(export_bundle(args.runtime)))
        return
    if args.host is None:
        parser.error("--host required")
    if args.mode == "export-host":
        if args.runtime is None or not args.workspace:
            parser.error("export-host requires --runtime and --workspace")
        export_host(args.runtime, args.host, args.workspace, args.control_port, args.gateway_port)
    elif args.mode in ("start", "cli-check"):
        if args.exe is None:
            parser.error("start/cli-check requires installed --exe")
        project = Path(__file__).resolve().parents[1]
        if args.mode == "cli-check":
            print(json.dumps(cli_check(project, args.host, args.exe)))
        else:
            raise SystemExit(start(project, args.host, args.exe))
    else:
        value = send(args.host, '/security', None, human=True, method='GET') if args.mode == 'security' else check(args.host) if args.mode == 'check' else history(args.host)
        print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("PRODUCT_CONNECTION_UNAVAILABLE: inspect local setup; no automatic model retry.", file=sys.stderr)
        raise SystemExit(2) from None
