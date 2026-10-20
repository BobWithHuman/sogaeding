"""Prepare NEW role-separated app PKI only. Never touch global trust or old runtime."""
import argparse
import importlib.util
import json
import os
import secrets
import shutil
from pathlib import Path

_tls_spec = importlib.util.spec_from_file_location("reviewed_prepare_tls", Path(__file__).with_name("prepare_tls.py"))
_tls_module = importlib.util.module_from_spec(_tls_spec)
_tls_spec.loader.exec_module(_tls_module)
generate = _tls_module.generate


def prepare(root):
    root = root.resolve()
    runtime = root / "artifacts/runtime-hookgw"
    if runtime.exists():
        raise SystemExit("Runtime already exists; preserving keys/DB. Use status/check instead.")
    runtime.mkdir(parents=True, mode=0o700)
    staging = runtime / "pki"
    generate(staging, [("upstream", ["upstream"])])
    files = {
        "control": ["ca.pem", "control.pem", "control.key", "storage.key", "human.token"],
        "gateway": ["ca.pem", "gateway.pem", "gateway.key", "gateway-client.pem", "gateway-client.key"],
        "upstream": ["ca.pem", "upstream.pem", "upstream.key"],
        "host": ["ca.pem", "human.token"],
    }
    for role, names in files.items():
        target = runtime / role
        target.mkdir(mode=0o700)
        for name in names:
            shutil.copyfile(staging / name, target / name)
    # New generated credentials, never copied from a legacy runtime or personal auth.
    for name, roles in [("machine.token", ["control", "host"]), ("machine.id", ["control", "host"]),
                        ("forward.key", ["control", "upstream"])]:
        value = secrets.token_urlsafe(48)
        for role in roles:
            (runtime / role / name).write_text(value, encoding="ascii")
    grant = {"workspace": str(root), "tools": {"native": ["Bash", "apply_patch"], "mcp": ["read_file", "write_file"]},
             "protected_markers": ["artifacts/", "references/", ".codex", ".aws", ".env", ".git/", "docs/plans/", "AGENTS.md", "docs/handoffs/", "src/app/", "agentgateway/", "tools/hookgw", "scripts/hookgw", "compose.hookgw"]}
    (runtime / "control/grant.json").write_text(json.dumps(grant, indent=2), encoding="utf-8")
    # No private CA key is retained by generate(). Staging is never mounted in services.
    for item in runtime.rglob("*"):
        if item.is_file():
            os.chmod(item, 0o644 if item.suffix == ".pem" else 0o600)
    print("New hookgw application runtime prepared. No global CA/config/auth modified.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    prepare(p.parse_args().root)
