"""Read-only audit of every pinned OS indirect task before live enrollment."""

import ast
import contextlib
import io
import json
import subprocess
from collections import Counter
from pathlib import Path

import yaml
from dt_arena.src.types.task import AttackConfig
from dtap_runtime import selected_os100
from utils.injection_helpers import (
    build_tool_injections_from_config,
    get_env_injections_from_attack,
    get_required_injection_servers,
)


def main():
    project = Path("/project")
    inventory = json.loads(
        (project / "artifacts/20261017-dtap-prepare/inventory-final/inventory.json").read_text()
    )
    details = json.loads(
        (project / "artifacts/20261017-dtap-runtime/audit-fast/tasks.json").read_text()
    )
    rows = selected_os100(inventory, details)
    categories = Counter()
    injections = Counter()
    permissions = Counter()
    judge_llm = Counter()
    failures = []
    for row in rows:
        key = row["task_key"]
        path = Path("/vendor/dataset") / key
        try:
            task = yaml.safe_load((path / "config.yaml").read_text())
            attack = AttackConfig.from_yaml(str(path / "config.yaml"))
            with contextlib.redirect_stdout(io.StringIO()):
                tool_attacks = build_tool_injections_from_config(attack)
            required = set(get_required_injection_servers(get_env_injections_from_attack(attack)))
            if required - {"os-filesystem-injection"}:
                raise ValueError("UNKNOWN_INJECTION_SERVER")
            servers = [s for s in task["Agent"].get("mcp_servers", []) if s.get("enabled", True)]
            if len(servers) != 1 or servers[0]["name"] != "OS-filesystem":
                raise ValueError("UNKNOWN_OFFICIAL_SERVER")
            variables = servers[0].get("env_vars") or {}
            if set(variables) - {"USER_ACCESS_TOKEN", "LINUX_USER", "PERMISSION_AUTO_APPROVE"}:
                raise ValueError("UNKNOWN_SERVER_VARIABLE")
            if variables.get("USER_ACCESS_TOKEN", "alice-token") not in (
                "alice-token",
                "bob-token",
                "admin-token-for-setup",
            ):
                raise ValueError("UNKNOWN_SYNTHETIC_CREDENTIAL")
            if str(variables.get("PERMISSION_AUTO_APPROVE", "false")).lower() not in (
                "true",
                "false",
            ):
                raise ValueError("UNKNOWN_PERMISSION_SETTING")
            judge = (path / "judge.py").read_text()
            ast.parse(judge, filename=str(path / "judge.py"))
            syntax = subprocess.run(
                ["bash", "-n", str(path / "setup.sh")], capture_output=True, check=False, timeout=5
            )
            if syntax.returncode:
                raise ValueError("OFFICIAL_SETUP_BASH_SYNTAX")
            categories[key.split("/")[3]] += 1
            kinds = tuple(next(d for d in details if d["task_key"] == key)["injection_types"])
            injections["+".join(kinds)] += 1
            if bool(tool_attacks) != ("tool" in kinds) or bool(required) != (
                "environment" in kinds
            ):
                raise ValueError("OFFICIAL_INJECTION_SHAPE_MISMATCH")
            permissions[str(variables.get("PERMISSION_AUTO_APPROVE", "false")).lower()] += 1
            judge_llm[
                "llm_marker_present"
                if "llm_check" in judge or "openai" in judge.lower()
                else "no_direct_marker"
            ] += 1
        except Exception as exc:
            failures.append(
                {"task_key": key, "error": type(exc).__name__, "reason": str(exc)[:160]}
            )
    evidence = {
        "target": 100,
        "checked": len(rows),
        "failures": failures,
        "categories": categories,
        "injections": injections,
        "official_permissions": permissions,
        "judge_direct_llm_markers": judge_llm,
        "review_limit": "STATIC_AND_OFFICIAL_PARSER_ONLY; live model outcomes not established",
    }
    Path("/output/os100-audit.json").write_text(json.dumps(evidence, sort_keys=True, indent=2))
    print(
        json.dumps(
            {
                "checked": len(rows),
                "failure_count": len(failures),
                "injections": injections,
                "permissions": permissions,
            }
        )
    )
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
