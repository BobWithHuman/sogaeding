"""Isolated application PKI and TLS/MCP readiness; no provider execution."""

import argparse
import ipaddress
import json
import os
import re
import secrets
import shutil
import sys
import time
from pathlib import Path

import httpx
from prepare_tls import generate


def network_pair(networks):
    """Choose explicit subnets without removing/replacing any existing network."""
    occupied = []
    for network in networks:
        for config in network.get("IPAM", {}).get("Config") or []:
            subnet = config.get("Subnet")
            if subnet:
                occupied.append(ipaddress.ip_network(subnet, strict=False))
    selected = []
    for index in range(256):
        candidate = ipaddress.ip_network(f"10.253.{index}.0/24")
        if not any(other.version == 4 and other.overlaps(candidate) for other in occupied):
            selected.append(str(candidate))
            if len(selected) == 2:
                return {"protected": selected[0], "ingress": selected[1]}
    raise ValueError("NO_TEAM_SUBNET_AVAILABLE_PRESERVE_EXISTING")


def prepare(root, name):
    root = root.resolve()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", name):
        raise ValueError("INVALID_RUNTIME_NAME")
    target = root / "artifacts" / "team-dev" / name
    if not target.resolve().is_relative_to(root) or target.exists():
        raise ValueError("NEW_RUNTIME_REQUIRED_PRESERVE_EXISTING")
    target.mkdir(parents=True, mode=0o700)
    staging = target / "pki"
    generate(staging, [("upstream", ["upstream"])])
    roles = {
        "control": ["ca.pem", "control.pem", "control.key", "storage.key", "human.token"],
        "gateway": [
            "ca.pem",
            "gateway.pem",
            "gateway.key",
            "gateway-client.pem",
            "gateway-client.key",
        ],
        "upstream": ["ca.pem", "upstream.pem", "upstream.key"],
        "host": ["ca.pem", "human.token"],
    }
    for role, files in roles.items():
        (target / role).mkdir(mode=0o700)
        for file in files:
            shutil.copyfile(staging / file, target / role / file)
    for name, destinations in (
        ("machine.token", ("control", "host")),
        ("machine.id", ("control", "host")),
        ("forward.key", ("control", "upstream")),
    ):
        value = secrets.token_urlsafe(48)
        for role in destinations:
            (target / role / name).write_text(value, encoding="ascii")
    grant = {
        "workspace": "/files",
        "tools": {"native": [], "mcp": ["read_file", "write_file"]},
        "protected_markers": [".env", ".git/", ".aws", ".codex", "artifacts/"],
        "gate6_resource_rules": {"reports/ask-demo.md": ["SENSITIVE_RESOURCE_REQUIRES_CONSENT"]},
    }
    (target / "control/grant.json").write_text(json.dumps(grant), encoding="utf-8")
    for directory in ("control-data", "upstream-data", "jev-budget", "workspace/docs", "workspace/reports"):
        (target / directory).mkdir(parents=True, mode=0o700)
    (target / "workspace/docs/release.md").write_text(
        "# Synthetic release\nDeployment completed. Security review is still pending.\n",
        encoding="utf-8",
    )
    for path in target.rglob("*"):
        if path.is_file():
            os.chmod(path, 0o644 if path.suffix == ".pem" else 0o600)
    # Roles already have their own required files. Do not retain a second copy
    # of every token/private key or the unused CA signing key in staging.
    if staging.is_symlink() or not staging.resolve().is_relative_to(target):
        raise ValueError('UNSAFE_PKI_STAGING')
    shutil.rmtree(staging)
    print(json.dumps({"state": "PREPARED", "provider_calls": 0, "leaf_valid_days": 2}))


def check(runtime):
    """Only health, auth negatives and MCP discovery; never tools/call."""
    import ssl

    context = ssl.create_default_context(cafile=str(runtime / "host/ca.pem"))
    token = (runtime / "host/machine.token").read_text().strip()
    headers = {"authorization": "Bearer " + token}
    with httpx.Client(verify=context, trust_env=False, follow_redirects=False, timeout=5) as client:
        for attempt in range(20):
            try:
                health = client.get("https://control:8030/health", headers=headers)
                health.raise_for_status()
                break
            except httpx.TransportError:
                if attempt == 19:
                    raise
                time.sleep(0.5)
        value = health.json()
        if value.get("judge_mode") != "JEV_USER_LIVE" or value.get("decision_policy") != "engine-2026-10-24-gate6-1":
            raise ValueError("UNEXPECTED_PROVIDER_MODE")
        denied = client.get("https://control:8030/history")
        if denied.status_code not in (403,429):
            raise ValueError("UNAUTHENTICATED_HISTORY_NOT_REJECTED")
        connection = client.post("https://control:8030/connect", headers=headers)
        connection.raise_for_status()
        bearer = connection.json()["connection"]
        try:
            for method in ("initialize", "tools/list"):
                response = client.post(
                    "https://gateway:8040/mcp",
                    headers={"authorization": "Bearer " + bearer},
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": {}},
                )
                response.raise_for_status()
                result = response.json()["result"]
            tools = sorted(tool["name"] for tool in result["tools"])
            grant = json.loads((runtime / 'control/grant.json').read_text())
            if tools != sorted(grant['tools']['mcp']):
                raise ValueError("MCP_CATALOG_MISMATCH")
        finally:
            closed = client.post(
                "https://control:8030/disconnect", headers=headers, json={"connection": bearer}
            )
            closed.raise_for_status()
    print(
        json.dumps(
            {
                "state": "READY",
                "health": value,
                "mcp_tools": tools,
                "unauthenticated_history": denied.status_code,
                "tool_executions": 0,
                "provider_calls": 0,
            }
        )
    )


def security(runtime):
    import ssl
    context = ssl.create_default_context(cafile=str(runtime/'host/ca.pem'))
    token = (runtime/'host/human.token').read_text().strip()
    with httpx.Client(verify=context,trust_env=False,follow_redirects=False,timeout=5) as client:
        response = client.get('https://control:8030/security',headers={'Authorization':'Bearer '+token})
        response.raise_for_status()
    print(json.dumps(response.json()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "check", "networks", "security"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--name", default="default")
    args = parser.parse_args()
    try:
        if args.mode == "networks":
            print(json.dumps(network_pair(json.load(sys.stdin))))
        elif args.path is None:
            raise ValueError("RUNTIME_PATH_REQUIRED")
        elif args.mode == "prepare":
            prepare(args.path, args.name)
        elif args.mode == 'security':
            security(args.path)
        else:
            check(args.path)
    except Exception as exc:
        # Do not emit credential-bearing requests, response bodies or traceback locals.
        print(json.dumps({"state": "FAILED", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
