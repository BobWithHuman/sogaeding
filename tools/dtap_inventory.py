"""Static full DTAP inventory. No vendor imports, installs, setup or judges run."""

import argparse
import ast
import collections
import csv
import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath

import yaml


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def archive_files(path):
    result = {}
    total = 0
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            if member.isdir():
                continue
            parts = PurePosixPath(member.name).parts[1:]
            if (
                not member.isfile()
                or not parts
                or any(p in (".", "..") or ":" in p or "\\" in p for p in parts)
            ):
                raise ValueError("UNSAFE_SOURCE_ARCHIVE")
            total += member.size
            if total > 200 * 1024 * 1024 or len(result) >= 40000:
                raise ValueError("SOURCE_ARCHIVE_LIMIT")
            name = "/".join(parts)
            if name in result:
                raise ValueError("DUPLICATE_SOURCE_PATH")
            result[name] = archive.extractfile(member).read()
    return result


def tools_in_source(raw, name):
    """Signature inventory only; not a claim of validated MCP JSON schemas."""
    try:
        module = ast.parse(raw)
    except (SyntaxError, ValueError):
        return [], "AST_PARSE_UNKNOWN"
    rows = []
    for node in ast.walk(module):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = [
            d
            for d in node.decorator_list
            if isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "tool"
        ]
        if not decorators:
            continue
        tool = node.name
        for d in decorators:
            for k in d.keywords:
                if (
                    k.arg == "name"
                    and isinstance(k.value, ast.Constant)
                    and isinstance(k.value.value, str)
                ):
                    tool = k.value.value
        rows.append(
            {
                "tool": tool,
                "source": name,
                "line": node.lineno,
                "parameters": [
                    {
                        "name": a.arg,
                        "annotation": ast.unparse(a.annotation) if a.annotation else "UNKNOWN",
                    }
                    for a in node.args.args
                ],
                "varargs": bool(node.args.vararg or node.args.kwarg),
                "schema_status": "STATIC_SIGNATURE_NOT_RUNTIME_VALIDATED",
            }
        )
    return rows, "STATIC_ONLY"


def inventory(archive, tree, source_commit, dataset_revision, trajectory_revision, output):
    output = Path(output)
    if output.exists():
        raise ValueError("INVENTORY_OUTPUT_EXISTS_PRESERVED")
    files = archive_files(archive)
    expected = {r["path"]: r["sha"] for r in tree["tree"] if r["type"] == "blob"}
    actual = {
        # SHA-1 is required for Git object identity only; security binding also
        # pins the full archive and every extracted file with SHA-256.
        name: hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
        for name, raw in files.items()
    }
    if tree.get("truncated") or expected != actual:
        raise ValueError("SOURCE_TREE_HASH_MISMATCH")
    mcp = yaml.safe_load(files["dt_arena/config/mcp.yaml"])
    definitions = {s["name"]: s for s in mcp["servers"]}
    env_config = yaml.safe_load(files["dt_arena/config/env.yaml"])["environments"]
    environments = {}
    for env_name, definition in env_config.items():
        compose_path = definition["docker_compose"]
        raw = files.get(compose_path)
        spec = yaml.safe_load(raw) if raw else {}
        environments[env_name] = {
            "compose_path": compose_path,
            "compose_sha256": sha(raw) if raw else None,
            "services": {
                name: {
                    "image": service.get("image"),
                    "build": service.get("build"),
                    "image_digest_status": "NOT_PINNED_RUNTIME_REVIEW_REQUIRED",
                }
                for name, service in (spec.get("services", {}) or {}).items()
            },
            "reset_endpoints": definition.get("reset_endpoints", {}),
            "additional_llm_calls": "TRANSITIVE_RUNTIME_REVIEW_REQUIRED",
        }
    tools = {}
    for server, config in definitions.items():
        folder = "dt_arena/mcp_server/" + str(PurePosixPath(config["path"]).parent) + "/"
        rows = []
        for name, raw in files.items():
            if name.startswith(folder) and name.endswith(".py"):
                found, _ = tools_in_source(raw, name)
                rows += found
        tools[server] = {
            "path": config["path"],
            "environment": config.get("environment"),
            "tools": rows,
            "status": "SCHEMA_RUNTIME_AND_SLOT_ENROLLMENT_REQUIRED",
        }
    records = []
    seen = collections.Counter()
    duplicates = []
    lists = {}
    configs = {}
    for name, raw in files.items():
        if not name.startswith("benchmark/") or not name.endswith(".jsonl"):
            continue
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        lists[name] = {"sha256": sha(raw), "rows": len(rows)}
        for row in rows:
            threat = "benign" if row["type"] == "benign" else row["threat_model"]
            if threat not in ("benign", "direct", "indirect"):
                raise ValueError("UNKNOWN_THREAT_MODEL")
            pieces = ["dataset", row["domain"], row["type"]]
            if row["type"] == "malicious":
                pieces += [threat, row["risk_category"]]
            elif row.get("risk_category"):
                pieces += [row["risk_category"]]
            pieces += [str(row["task_id"])]
            if any(
                not isinstance(piece, str)
                or piece in ("", ".", "..")
                or "/" in piece
                or "\\" in piece
                or ":" in piece
                for piece in pieces
            ):
                raise ValueError("UNSAFE_TASK_PATH_COMPONENT")
            base = "/".join(pieces)
            key = base.removeprefix("dataset/")
            source_key = key
            seen[key] += 1
            duplicate = seen[key] > 1
            if duplicate:
                duplicates.append({"source_task_key": key, "list": name, "occurrence": seen[key]})
                key += "#occurrence-" + str(seen[source_key])
            config = files.get(base + "/config.yaml")
            judge = files.get(base + "/judge.py")
            parsed = yaml.safe_load(config) if config else {}
            if not isinstance(parsed, dict):
                raise ValueError("TASK_CONFIG_INVALID")
            agent = parsed.get("Agent", {}) or {}
            servers = agent.get("mcp_servers", []) or []
            names = [
                s["name"] if isinstance(s, dict) else s
                for s in servers
                if not isinstance(s, dict) or s.get("enabled", True)
            ]
            native = agent.get("tools", []) or []
            reason = []
            if duplicate:
                reason.append("DUPLICATE_OFFICIAL_RECORD_PRESERVED_AS_SEPARATE_OCCURRENCE")
            if not config:
                reason.append("MISSING_CONFIG")
            if not judge:
                reason.append("MISSING_OFFICIAL_JUDGE")
            if native:
                reason.append("NATIVE_TOOL_PARITY_REVIEW_REQUIRED")
            for server in names:
                reason.append(
                    server
                    + ":"
                    + (
                        "RUNTIME_SCHEMA_SLOT_MAPPING_AND_ENVIRONMENT_REQUIRED"
                        if server in definitions
                        else "SERVER_DEFINITION_UNKNOWN"
                    )
                )
            if not names:
                reason.append("NO_MCP_SERVERS_REQUIRES_REVIEW")
            text = judge.decode(errors="replace") if judge else ""
            llm = any(
                s in text
                for s in (
                    "OpenAI",
                    "openai",
                    "anthropic",
                    "completions",
                    "llm_judge",
                    "judge_with_llm",
                    "llm_check",
                    "call_llm",
                )
            )
            record = {
                "task_key": key,
                "source_task_key": source_key,
                "list_path": name,
                "domain": row["domain"],
                "threat_model": threat,
                "task_id": str(row["task_id"]),
                "config_path": base + "/config.yaml",
                "config_sha256": sha(config) if config else None,
                "judge_path": base + "/judge.py",
                "judge_sha256": sha(judge) if judge else None,
                "setup_sha256": sha(files[base + "/setup.sh"])
                if base + "/setup.sh" in files
                else None,
                "servers": names,
                "native_tools": native,
                "environments": sorted(
                    {
                        e
                        for s in names
                        if s in definitions
                        for e in (
                            [definitions[s].get("environment")]
                            if isinstance(definitions[s].get("environment"), str)
                            else definitions[s].get("environment") or []
                        )
                    }
                ),
                "transitive_judge_calls": "UNKNOWN_UNTIL_HELPER_AND_RUNTIME_BOUND",
                "environment_llm_calls": "UNKNOWN_UNTIL_DOMAIN_BOUND; PERMISSION_TOOLS_MAY_CALL_LLM",
                "judge_calls": "POSSIBLE_LLM_REQUIRES_BOUND"
                if llm
                else "STATIC_SCAN_NO_LLM_MARKER_NOT_RUNTIME_PROOF",
                "coverage": "NOT_EXECUTION_READY",
                "reasons": reason,
            }
            records.append(record)
            # Evaluation-only object; actor/PDP material is built separately from
            # an explicit allowlist. Task labels/judges never become model state.
            configs[key] = {
                "task_instruction": (parsed.get("Task", {}) or {}).get("task_instruction"),
                "agent": agent,
            }
    records.sort(key=lambda r: r["task_key"])
    counts = collections.Counter(r["threat_model"] for r in records)
    output.mkdir(parents=True)
    summary = {
        "version": "dtap-inventory-1",
        "source_commit": source_commit,
        "dataset_revision": dataset_revision,
        "trajectory_revision": trajectory_revision,
        "task_source": "PINNED_OFFICIAL_REPOSITORY_DATASET; HF_REVISION_REFERENCED_NOT_ASSUMED_BYTE_IDENTICAL",
        "repo_license_sha256": sha(files["LICENSE"]),
        "archive_sha256": sha(Path(archive).read_bytes()),
        "task_lists": lists,
        "counts": dict(counts),
        "total": len(records),
        "domains": sorted({r["domain"] for r in records}),
        "unique_source_tasks": len(seen),
        "duplicate_records": duplicates,
        "runtime_ready": 0,
        "status": "INVENTORY_COMPLETE_EXECUTION_COVERAGE_INCOMPLETE",
        "paid_calls": 0,
    }
    for name, value in [
        ("inventory.json", records),
        ("summary.json", summary),
        ("tools.json", tools),
        ("environments.json", environments),
        ("task-inputs-evaluation-only.json", configs),
    ]:
        (output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=[
            "task_key",
            "domain",
            "threat_model",
            "task_id",
            "coverage",
            "servers",
            "judge_calls",
            "reasons",
        ],
    )
    writer.writeheader()
    for row in records:
        writer.writerow(
            {k: ";".join(row[k]) if isinstance(row[k], list) else row[k] for k in writer.fieldnames}
        )
    (output / "COVERAGE.csv").write_text(stream.getvalue(), encoding="utf-8-sig", newline="")
    tool_rows = []
    for server, definition in tools.items():
        for row in definition["tools"] or [
            {
                "tool": "UNKNOWN_DYNAMIC_CATALOG",
                "source": definition["path"],
                "line": None,
                "schema_status": "DYNAMIC_CATALOG_NOT_ENUMERATED",
            }
        ]:
            tool_rows.append(
                {
                    "server": server,
                    "tool": row["tool"],
                    "source": row["source"],
                    "line": row["line"],
                    "environment": definition["environment"],
                    "coverage": "NOT_EXECUTION_READY",
                    "reason": "RUNTIME_SCHEMA_RESOURCE_SLOTS_PARITY_AND_EFFECT_TEST_REQUIRED",
                    "schema_status": row["schema_status"],
                }
            )
    with (output / "TOOL_COVERAGE.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(tool_rows[0]))
        writer.writeheader()
        writer.writerows(tool_rows)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache = args.cache
    result = inventory(
        cache / "source.tar.gz",
        json.loads((cache / "repo-tree.json").read_text()),
        json.loads((cache / "repo-head.json").read_text())["sha"],
        json.loads((cache / "dataset-metadata.json").read_text())["sha"],
        json.loads((cache / "trajectories-metadata.json").read_text())["sha"],
        args.output,
    )
    print(canonical({k: result[k] for k in ("counts", "total", "domains", "status", "paid_calls")}))


if __name__ == "__main__":
    main()
