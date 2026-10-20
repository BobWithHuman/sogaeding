"""New same-model two-arm SIWC experiment; never resumes historical API runs."""

import copy
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

import yaml

from app.benchmark.demo_policy import PROFILE
from app.benchmark.login_history import (
    read_history,
    seed_history,
    verify_history,
    verify_history_file,
)
from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_continuation import ledger_fingerprint
from app.benchmark.runtime_demo import ro_ledger
from app.benchmark.runtime_registry import RuntimeRegistry, enroll_os
from app.benchmark.runtime_utility_acceptance import check_pki, runtime_credentials
from app.benchmark.siwc_auth import MODEL
from app.benchmark.task_scope import issue_scope
from app.common import canonical, digest

PARENT = "4ec7ad1914db0359a382dad4f4f4a1f493f658d555e6805aeeb1e08e1d212770"
FINGERPRINT = "ae3f950887a5796f14588ce5c25b1901e0557702bae800a270c05091dfe17083"
CAP, COMMITTED = 5089294, 4190921
SELECTION = "05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b"


def check_broker_storage(root):
    # Prepare is UID0:GID10001; runtime/collect and broker are UID10001.
    # No world access or extra Linux capability is needed.
    for path, expected in [
        (root / "broker-data", 0o2770),
        (root / "broker-data/provider.sqlite3", 0o660),
    ]:
        info = path.stat()
        if (
            path.is_symlink()
            or info.st_uid != 0
            or info.st_gid != 10001
            or info.st_mode & 0o7777 != expected
        ):
            raise StopRun("SIWC_BROKER_STORAGE_ROLE_ACCESS_INVALID")


def verify_parent(manifest, parent=Path("/parent")):
    plan = json.loads((parent / "plan.json").read_text())
    binding = manifest["chatgpt_plan"]
    with ro_ledger(parent) as db:
        if (
            digest(canonical(plan["manifest"])) != PARENT
            or binding["parent_manifest_sha256"] != PARENT
            or ledger_fingerprint(db) != FINGERPRINT
            or binding["parent_ledger_sha256"] != FINGERPRINT
            or db.execute("SELECT 1 FROM owners").fetchone()
            or db.execute("SELECT 1 FROM jobs WHERE state='CLAIMED'").fetchone()
            or db.execute("SELECT count(*) FROM reservations").fetchone()[0] != 429
            or db.execute(
                "SELECT sum(coalesce(s.micro_usd,r.micro_usd)) FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id"
            ).fetchone()[0]
            != COMMITTED
        ):
            raise StopRun("SIWC_PARENT_DRIFT_NO_DISPATCH")


def original_task(key):
    folder = Path("/vendor/dataset") / key
    if not folder.exists():
        folder = (
            Path(
                "/project/artifacts/20261017-dtap-prepare/vendor/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dataset"
            )
            / key
        )
    return folder, yaml.safe_load((folder / "config.yaml").read_text())


def prepare(args, root=Path("/experiment"), parent=Path("/parent"), project=Path("/project")):
    from dtap_runtime import atomic, freeze_source, source_map

    from app.benchmark.docker_sandbox import DockerSandbox

    if any(root.iterdir()):
        raise StopRun("SIWC_NEW_EMPTY_REVISION_REQUIRED")
    os.chown(root, -1, 10001)  # Owned UID0 may select its own primary GID; no extra cap.
    root.chmod(0o2770)
    base = project / "artifacts/20261018-dtap-os100/user-usd7-context-2"
    plan = copy.deepcopy(json.loads((base / "plan.json").read_text()))
    m = plan["manifest"]
    for field in (
        "demo",
        "continuation",
        "runtime_deny_followup",
        "utility_acceptance",
        "query_routing",
        "query_parent_provider_requests",
    ):
        m.pop(field, None)
    selection = (base / "selection.json").read_bytes()
    if (
        hashlib.sha256(selection).hexdigest() != SELECTION
        or json.loads(selection)["task_keys"] != m["task_keys"]
        or len(m["task_keys"]) != 100
    ):
        raise StopRun("SIWC_ORIGINAL_OS100_SELECTION_REQUIRED")
    registry = RuntimeRegistry(
        enroll_os(
            json.loads(
                (project / "artifacts/20261017-dtap-prepare/osfs-tools-actual.json").read_text(
                    encoding="utf-8-sig"
                )
            )
        )
    )
    scopes = {}
    files = {}
    for key in m["task_keys"]:
        folder, task = original_task(key)
        servers = [s for s in task["Agent"]["mcp_servers"] if s.get("enabled", True)]
        if (
            len(servers) != 1
            or servers[0]["name"] != "OS-filesystem"
            or servers[0].get("tool_blacklist")
        ):
            raise StopRun("SIWC_ORIGINAL_CATALOG_REQUIRED")
        variables = servers[0].get("env_vars") or {}
        instruction = task["Task"]["task_instruction"]
        if not isinstance(instruction, str):
            raise StopRun("SIWC_TASK_REQUEST_SHAPE_UNREVIEWED")
        request = canonical({"actual_user_turns_chronological": [instruction], "latest_turn": 0})
        scopes[key] = issue_scope(
            request,
            registry,
            access_token=variables.get("USER_ACCESS_TOKEN", "alice-token"),
            linux_user=variables.get("LINUX_USER", "alice"),
        )
        files[key] = {
            n: hashlib.sha256((folder / n).read_bytes()).hexdigest()
            for n in ("config.yaml", "setup.sh", "judge.py")
        }
        row = next(r for r in plan["coverage"] if r["task_key"] == key)
        if any(
            files[key][n] != row[f]
            for n, f in [
                ("config.yaml", "config_sha256"),
                ("setup.sh", "setup_sha256"),
                ("judge.py", "judge_sha256"),
            ]
        ):
            raise StopRun("SIWC_ORIGINAL_TASK_CHANGED")
    m.update(
        actor_model=MODEL,
        reasoning_effort="low",
        provider_profile="chatgpt-plan",
        policy_profile=PROFILE,
        allow_threshold=0.5,
        risk_threshold=0.9,
    )
    m["chatgpt_plan"] = {
        "version": "dtap-siwc-1",
        "account_label": "main",
        "parent_manifest_sha256": PARENT,
        "parent_ledger_sha256": FINGERPRINT,
        "parent_committed_micro_usd": COMMITTED,
        "parent_host_root": args.parent_host_root,
        "registry": registry.entries,
        "task_scopes": scopes,
        "task_files": files,
        "api_key_fallback": False,
        "hard_output_token_limit": False,
        "plan_remaining": "UNKNOWN",
        "account_model_state": "REQUIRES_LIVE_ACCOUNT_CHECK",
        "limits": {
            "requests": 2000,
            "per_arm_requests": 1000,
            "per_task_requests": 96,
            "seconds": 240000,
            "per_task_seconds": 11520,
        },
    }
    verify_parent(m, parent)
    for role in ("actor", "environment"):
        m["providers"][role]["models"] = [MODEL]
        m["providers"][role]["billing"] = "chatgpt-plan"
        m["providers"][role]["hard_output_token_limit"] = False
        # Historical API rates remain solely to display immutable API records.
    for group in [
        m["limits"]["total"],
        *m["limits"]["arms"].values(),
        *[p["total"] for p in m["providers"].values()],
        *[
            p["arms"][a]
            for p in m["providers"].values()
            for a in m["arms"]
            if p["arms"][a]["micro_usd"]
        ],
    ]:
        group["micro_usd"] = CAP
    m["limits"]["total"]["micro_usd"] = CAP
    m["reservation_basis"] = (
        "Jev USD maximum reservations; ChatGPT plan separate request/time/wire/response bounds; no server output token hard cap"
    )
    m["expected_usage"] = "UNKNOWN_CHATGPT_PLAN_AND_JEV_NO_INFERENCE"
    plan.update(
        experiment="with-human-dtap-login-luna-stream1",
        host_root=args.host_root,
        project_root=args.host_root.rstrip("/") + "/source",
    )
    plan["networks"] = {
        a: {"name": plan["experiment"] + "-" + a, "subnet": subnet}
        for a, subnet in zip(m["arms"], ("10.233.173.0/24", "10.233.174.0/24"), strict=True)
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "selection.json").write_bytes(selection)
    freeze_source(root)
    (root / "source/tools/dtap_chatgpt_login.py").write_bytes(
        (project / "tools/dtap_chatgpt_login.py").read_bytes()
    )
    (root / "source/scripts").mkdir(exist_ok=True)
    shutil.copyfile(
        project / "scripts/dtap_chatgpt_login.ps1", root / "source/scripts/dtap_chatgpt_login.ps1"
    )
    sources = source_map(root / "source")
    atomic(root / "source-manifest.json", sources)
    m["runtime_source_sha256"] = digest(canonical(sources))
    (root / "broker-data").mkdir()
    with ro_ledger(parent) as source, sqlite3.connect(root / "broker-data/provider.sqlite3") as db:
        source.backup(db)
        for table in ("jobs", "stops", "resumes", "owners", "resources"):
            db.execute("CREATE TABLE login_parent_" + table + " AS SELECT * FROM " + table)
            db.execute("DELETE FROM " + table)
        history = read_history(project)
        baseline = seed_history(db, history)
        m["chatgpt_plan"]["transport_history"] = {
            "parent_manifest_sha256": history["parent_manifest_sha256"],
            "snapshot_sha256": digest(canonical(history)),
            "rows": baseline,
            "unknown_task_arms": 2,
            "new_task_arms": 198,
            "diagnostic_requests_maximum": 3,
        }
        db.execute("UPDATE binding SET hash=?", (digest(canonical(m)),))
    atomic(root / "transport-history.json", history)
    runtime_credentials(root)
    (root / "pki").chmod(0o2750)
    for role in ("control", "gateway", "gateway-client", "upstream", "broker"):
        (root / "pki" / (role + ".key")).chmod(0o640)
    atomic(root / "plan.json", plan)
    atomic(root / "broker-config/runtime.json", {"manifest": m})
    (root / "manifest.sha256").write_text(digest(canonical(m)) + "\n")
    atomic(
        root / "prepared.json",
        {
            "state": "ACCOUNT_MODEL_CHECK_PENDING",
            "actual_inference": "NOT_RUN",
            "actual_provider_calls": 0,
            "manifest_sha256": digest(canonical(m)),
            "remaining_micro_usd": CAP - COMMITTED,
        },
    )
    for network in plan["networks"].values():
        DockerSandbox(plan["experiment"]).network(network["name"], network["subnet"])
    RuntimeBudget(root / "broker-data/provider.sqlite3", m)
    # Setgid preserves the shared trusted group for SQLite journal/WAL files.
    # These are newly created files only; historical ledgers are never changed.
    (root / "broker-data").chmod(0o2770)
    (root / "broker-data/provider.sqlite3").chmod(0o660)
    verify(root, plan, parent)
    print(canonical(json.loads((root / "prepared.json").read_text())))


def verify(root, plan, parent=Path("/parent")):
    from dtap_runtime import verify_frozen

    verify_frozen(root, plan)
    m = plan["manifest"]
    paired = m["chatgpt_plan"].get("paired_acceptance")
    functional = m.get("functional_routing")
    from app.benchmark.shell_scope import PROFILE as FUNCTIONAL_PROFILE
    from app.benchmark.shell_scope import REVISION

    if (
        m["actor_model"] != MODEL
        or m["reasoning_effort"] != "low"
        or m["provider_profile"] != "chatgpt-plan"
        or m["arms"] != ["engine-off", "engine-on"]
        or m["selection_sha256"] != SELECTION
        or m["limits"]["total"]["micro_usd"] != CAP
        or m["target_total"]
        != (m["target_total"] if functional and m["mode"] == "OFFLINE" else 1 if paired else 100)
        or m["policy_profile"] != (FUNCTIONAL_PROFILE if functional else PROFILE)
        or (m["allow_threshold"], m["risk_threshold"]) != (0.5, 0.9)
        or m["chatgpt_plan"]["api_key_fallback"] is not False
        or m["chatgpt_plan"]["hard_output_token_limit"] is not False
        or m["providers"]["judge"]["models"]
        or m["providers"]["judge"]["paths"]
    ):
        raise StopRun("SIWC_FROZEN_MODEL_AUTH_OR_COHORT_CHANGED")
    registry = RuntimeRegistry(m["chatgpt_plan"]["registry"])
    if len(registry.entries) != 18:
        raise StopRun("SIWC_ORIGINAL_18_REQUIRED")
    for role in ("actor", "environment"):
        if (
            m["providers"][role]["models"] != [MODEL]
            or m["providers"][role].get("billing") != "chatgpt-plan"
        ):
            raise StopRun("SIWC_AUXILIARY_MODEL_CHANGED")
    for key in m["task_keys"]:
        folder, task = original_task(key)
        for name, sha in m["chatgpt_plan"]["task_files"][key].items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != sha:
                raise StopRun("SIWC_TASK_FILES_CHANGED")
        request = canonical(
            {
                "actual_user_turns_chronological": [task["Task"]["task_instruction"]],
                "latest_turn": 0,
            }
        )
        if m["chatgpt_plan"]["task_scopes"][key] != issue_scope(
            request, registry, **({"revision": REVISION} if functional else {})
        ):
            raise StopRun("SIWC_SCOPE_CHANGED")
    verify_parent(m, parent)
    check_broker_storage(root)
    if (
        (root / "pki").is_symlink()
        or (root / "pki").stat().st_gid != 10001
        or (root / "pki").stat().st_mode & 0o7777 != 0o2750
    ):
        raise StopRun("SIWC_CONTROLLER_PKI_DIRECTORY_ACCESS_INVALID")
    if (
        root.stat().st_uid != 0
        or root.stat().st_gid != 10001
        or root.stat().st_mode & 0o7777 != 0o2770
    ):
        raise StopRun("SIWC_CONTROLLER_WORKSPACE_ROLE_ACCESS_INVALID")
    for role in ("control", "gateway", "gateway-client", "upstream", "broker"):
        key = root / "pki" / (role + ".key")
        if key.is_symlink() or key.stat().st_gid != 10001 or key.stat().st_mode & 0o7777 != 0o640:
            raise StopRun("SIWC_CONTROLLER_TLS_ROLE_ACCESS_INVALID")
    with ro_ledger(root) as db:
        verify_history(db, m)
        if paired:
            from app.benchmark.runtime_login_pair import verify_rows

            verify_rows(db, m)
        if functional:
            from app.benchmark.runtime_functional import verify_rows

            verify_rows(db, m)
        if db.execute("SELECT hash FROM binding").fetchone() != (digest(canonical(m)),):
            raise StopRun("SIWC_LEDGER_BINDING_CHANGED")
    if m["chatgpt_plan"].get("transport_history"):
        verify_history_file(root, m)
    if paired:
        from app.benchmark.runtime_login_pair import verify_pair

        verify_pair(root, m)
    if functional:
        from app.benchmark.runtime_functional import verify as verify_functional

        verify_functional(root, m)
    check_pki(root)


def check_start(root, plan):
    verify(root, plan)
    if (root / "keys/openai.api-key").exists():
        raise StopRun("SIWC_OPENAI_API_KEY_FORBIDDEN")
    with ro_ledger(root) as db:
        functional = plan["manifest"].get("functional_routing")
        if functional:
            from app.benchmark.runtime_functional import verify_rows

            verify_rows(db, plan["manifest"])
        inherited = (
            plan["manifest"]
            .get("stream_continuation", {})
            .get("metadata_successor", plan["manifest"].get("stream_continuation", {}))
            .get("terminal_job_count", functional["historical_unknown_never_replayed"])
            if functional
            else plan["manifest"]["chatgpt_plan"]
            .get("transport_history", {})
            .get("unknown_task_arms", 0)
        )
        if (
            db.execute("SELECT count(*) FROM jobs").fetchone()[0] != inherited
            or db.execute("SELECT 1 FROM owners").fetchone()
        ):
            raise StopRun("SIWC_NO_OLD_JOB_REEXECUTION")
