"""A new attempt for unstarted arm/tasks; retain every prior terminal row."""

import copy
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_demo import ro_ledger
from app.common import canonical, digest

PREDECESSOR = "e4383d95e8503b1b2233edb8520a892503b18948a5fcf8c69cca1bf4e713a1ca"
PROBE = "23379262c954d05f8815b1340f21417168adb4773e6a38a4146d82f151d297ad"
RECEIPT_SHA256 = "d8badca23bfc73904d2f825a19ff8d3ab3bfdc99bc42a9b49651c6f9773e6d44"
VERSION = "unstarted-only-stream-continuation-1"
METADATA_PARENT = "dde77e5e1843d7999c7448cc71a53ce800ea6bab46f75d38182be9ccd85b312e"
TABLES = {
    "jobs": ("task", "arm"),
    "stream_parent_stops": ("id",),
    "stream_parent_resumes": ("id",),
    "stream_parent_budget_rejections": ("task", "arm", "provider", "code", "at"),
    "plan_requests": ("id",),
    "plan_account": ("binding",),
    "plan_http_observations": ("request_id",),
    "plan_stream_observations": ("request_id",),
    "resources": ("identity",),
    "reservations": ("id",),
    "settlements": ("reservation",),
}


def baseline(db):
    result = {}
    for table, keys in TABLES.items():
        columns = [r[1] for r in db.execute("PRAGMA table_info(" + table + ")")]
        result[table] = [
            {"key": [r[columns.index(k)] for k in keys], "sha256": digest(canonical(r))}
            for r in db.execute("SELECT * FROM " + table + " ORDER BY 1")
        ]
    return result


def verify_rows(db, manifest):
    config = manifest["stream_continuation"]
    if (
        config["version"] != VERSION
        or config["parent_manifest_sha256"] != PREDECESSOR
        or config["diagnostic_manifest_sha256"] != PROBE
        or config["diagnostic_result_sha256"] != RECEIPT_SHA256
        or config["diagnostic_request_id"] != "external-permission-diagnostic-" + RECEIPT_SHA256
        or config["terminal_job_count"] != 7
        or set(config["parent_rows"]) != set(TABLES)
        or len(config["parent_rows"]["jobs"]) != 7
        or len(config["parent_rows"]["plan_requests"]) != 131
    ):
        raise StopRun("STREAM_CONTINUATION_BINDING_CHANGED")
    for table, keys in TABLES.items():
        for item in config["parent_rows"][table]:
            row = db.execute(
                "SELECT * FROM " + table + " WHERE " + " AND ".join(k + "=?" for k in keys),
                item["key"],
            ).fetchone()
            if row is None or digest(canonical(row)) != item["sha256"]:
                raise StopRun("STREAM_CONTINUATION_PRIOR_ROW_CHANGED")
    successor = config.get("metadata_successor")
    if successor:
        tables = metadata_tables()
        if (
            successor["parent_manifest_sha256"] != METADATA_PARENT
            or successor["version"] != "metadata-boundary-fix-1"
            or successor["terminal_job_count"] != 12
            or set(successor["parent_rows"]) != set(tables)
            or len(successor["parent_rows"]["jobs"]) != 12
            or len(successor["parent_rows"]["plan_requests"]) != 153
        ):
            raise StopRun("METADATA_SUCCESSOR_BINDING_CHANGED")
        for table, keys in tables.items():
            for item in successor["parent_rows"][table]:
                row = db.execute(
                    "SELECT * FROM " + table + " WHERE " + " AND ".join(k + "=?" for k in keys),
                    item["key"],
                ).fetchone()
                if row is None or digest(canonical(row)) != item["sha256"]:
                    raise StopRun("METADATA_SUCCESSOR_PRIOR_ROW_CHANGED")


def metadata_tables():
    return {
        **TABLES,
        "metadata_parent_stops": ("id",),
        "metadata_parent_resumes": ("id",),
        "metadata_parent_budget_rejections": ("task", "arm", "provider", "code", "at"),
    }


def seed_metadata_successor(db, manifest):
    from app.benchmark.runtime_functional import verify_rows as verify_functional

    verify_functional(db, manifest)
    if (
        db.execute("SELECT hash FROM binding").fetchone() != (METADATA_PARENT,)
        or db.execute("SELECT 1 FROM owners").fetchone()
        or db.execute("SELECT 1 FROM jobs WHERE state='CLAIMED'").fetchone()
        or db.execute("SELECT 1 FROM plan_requests WHERE state='STARTED'").fetchone()
        or db.execute("SELECT state,count(*) FROM jobs GROUP BY state ORDER BY state").fetchall()
        != [("COMPLETED", 2), ("CONFIRM_UNAPPROVED", 1), ("INCOMPLETE", 1), ("UNKNOWN", 8)]
        or db.execute("SELECT count(*) FROM plan_requests").fetchone() != (153,)
        or db.execute("SELECT count(*) FROM plan_requests WHERE state='UNKNOWN'").fetchone() != (5,)
        or db.execute("SELECT count(*) FROM reservations").fetchone() != (431,)
        or db.execute("SELECT code FROM stops ORDER BY id").fetchall()
        != [("INFRASTRUCTURE_STOP_ALL",)]
        or db.execute(
            "SELECT coalesce(sum(coalesce(s.micro_usd,r.micro_usd)),0) FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id"
        ).fetchone()
        != (4191420,)
    ):
        raise StopRun("METADATA_SUCCESSOR_PARENT_STATE_CHANGED")
    for table in ("stops", "resumes", "budget_rejections"):
        db.execute("CREATE TABLE metadata_parent_" + table + " AS SELECT * FROM " + table)
        db.execute("DELETE FROM " + table)
    rows = {}
    for table, keys in metadata_tables().items():
        columns = [r[1] for r in db.execute("PRAGMA table_info(" + table + ")")]
        rows[table] = [
            {"key": [r[columns.index(k)] for k in keys], "sha256": digest(canonical(r))}
            for r in db.execute("SELECT * FROM " + table + " ORDER BY 1")
        ]
    manifest["stream_continuation"]["metadata_successor"] = {
        "parent_manifest_sha256": METADATA_PARENT,
        "version": "metadata-boundary-fix-1",
        "terminal_job_count": 12,
        "unstarted_arm_tasks_at_preparation": 188,
        "parent_rows": rows,
        "new_diagnostic_requests": 0,
        "failure_policy": "UNCHANGED_GLOBAL_STOP_NO_RETRY",
    }


def validate_parent(db, manifest):
    from app.benchmark.runtime_functional import verify_rows as verify_functional

    verify_functional(db, manifest)
    if db.execute("SELECT hash FROM binding").fetchone() != (PREDECESSOR,):
        raise StopRun("STREAM_CONTINUATION_EXACT_PARENT_REQUIRED")
    if (
        db.execute("SELECT 1 FROM owners").fetchone()
        or db.execute("SELECT 1 FROM jobs WHERE state='CLAIMED'").fetchone()
        or db.execute("SELECT 1 FROM plan_requests WHERE state='STARTED'").fetchone()
    ):
        raise StopRun("STREAM_CONTINUATION_PARENT_ACTIVE")
    if (
        db.execute("SELECT state,count(*) FROM jobs GROUP BY state ORDER BY state").fetchall()
        != [("CONFIRM_UNAPPROVED", 1), ("UNKNOWN", 6)]
        or db.execute("SELECT count(*) FROM plan_requests").fetchone() != (130,)
        or db.execute("SELECT count(*) FROM plan_requests WHERE state='UNKNOWN'").fetchone() != (5,)
        or db.execute("SELECT count(*) FROM reservations").fetchone() != (429,)
        or db.execute("SELECT code FROM stops ORDER BY id").fetchall()
        != [("SIWC_STREAM_NOT_COMPLETED_UNKNOWN",)]
        or db.execute(
            "SELECT coalesce(sum(coalesce(s.micro_usd,r.micro_usd)),0) "
            "FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id"
        ).fetchone()
        != (4190921,)
    ):
        raise StopRun("STREAM_CONTINUATION_PARENT_STATE_CHANGED")


def diagnostic_receipt(folder, account, *, public_receipt=None):
    manifest_raw = (folder / "bundle/manifest.json").read_bytes()
    probe = json.loads(manifest_raw)
    # The real probe result remains owner-only (UID10001). The root preparer
    # receives an exact, public-field-only receipt; never widen original ACLs.
    raw = (public_receipt or folder / "user-one-permission-request/result.json").read_bytes()
    result = json.loads(raw)
    if (
        hashlib.sha256(raw).hexdigest() != RECEIPT_SHA256
        or digest(canonical(probe)) != PROBE
        or probe["account_binding_sha256"] != account
        or probe["parent_dtap_manifest"] != PREDECESSOR
        or not (folder / "user-one-permission-request/one-request.claim").is_file()
        or result["state"] != "COMPLETED"
        or result["model"] != "gpt-5.6-luna"
        or result["reasoning_effort"] != "low"
        or result["billing"] != "chatgpt-plan"
        or result["api_key_fallback"] is not False
        or result["permission_response_validated"] is not True
        or result["decision_applied"] is not False
        or result["tool_executions"] != 0
        or result["error_kind"] is not None
        or result["usage"] != {"input_tokens": 315, "output_tokens": 47}
        or result["stream_detail"]["terminal_status"] != "completed"
        or result["stream_detail"]["model_matches"] is not True
    ):
        raise StopRun("STREAM_CONTINUATION_DIAGNOSTIC_RECEIPT_INVALID")
    return raw, result


def seed(db, manifest, receipt_raw, receipt):
    validate_parent(db, manifest)
    for table in ("stops", "resumes", "budget_rejections"):
        db.execute("CREATE TABLE stream_parent_" + table + " AS SELECT * FROM " + table)
        db.execute("DELETE FROM " + table)
    rid = "external-permission-diagnostic-" + hashlib.sha256(receipt_raw).hexdigest()
    db.execute(
        "CREATE TABLE IF NOT EXISTS plan_stream_observations(request_id TEXT PRIMARY KEY, detail TEXT NOT NULL)"
    )
    db.execute(
        "INSERT INTO plan_requests VALUES(?,?,?,?,?,?,?,?,?)",
        (
            rid,
            "STANDALONE_PERMISSION_DIAGNOSTIC",
            "standalone-diagnostic",
            "diagnostic",
            "gpt-5.6-luna",
            "COMPLETED",
            0,
            canonical(receipt["usage"]),
            60,
        ),
    )
    db.execute("INSERT INTO plan_http_observations VALUES(?,?,?)", (rid, 200, ""))
    db.execute(
        "INSERT INTO plan_stream_observations VALUES(?,?)",
        (rid, canonical(receipt["stream_detail"])),
    )
    manifest["stream_continuation"] = {
        "version": VERSION,
        "parent_manifest_sha256": PREDECESSOR,
        "diagnostic_manifest_sha256": PROBE,
        "diagnostic_result_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "diagnostic_request_id": rid,
        "terminal_job_count": 7,
        "unstarted_arm_tasks_at_preparation": 193,
        "parent_rows": baseline(db),
        "old_failure_cause": "NOT_ESTABLISHED",
        "failure_policy": "UNCHANGED_GLOBAL_STOP_NO_RETRY",
    }


def prepare(args, root=Path("/experiment"), parent=Path("/parent"), project=Path("/project")):
    from dtap_runtime import atomic, freeze_source, source_map, verify_frozen

    from app.benchmark.docker_sandbox import DockerSandbox
    from app.benchmark.runtime_login import verify, verify_parent
    from app.benchmark.runtime_utility_acceptance import runtime_credentials

    if any(root.iterdir()):
        raise StopRun("STREAM_CONTINUATION_EMPTY_ROOT_REQUIRED")
    predecessor = project / "artifacts/20261018-dtap-os100/user-functional-os100-1"
    plan = copy.deepcopy(json.loads((predecessor / "plan.json").read_text()))
    m = plan["manifest"]
    if digest(canonical(m)) != PREDECESSOR:
        raise StopRun("STREAM_CONTINUATION_EXACT_PARENT_REQUIRED")
    verify_frozen(predecessor, plan)
    with ro_ledger(predecessor) as src:
        validate_parent(src, m)
        account = src.execute("SELECT binding FROM plan_account").fetchone()[0]
        raw, receipt = diagnostic_receipt(
            project / "artifacts/20261020-functional-stream-failure",
            account,
            public_receipt=project
            / "artifacts/20261020-functional-stream-continuation/diagnostic-receipt.json",
        )
        verify_parent(m, parent)
        plan.update(
            experiment="with-human-functional-stream-continue-1",
            host_root=args.host_root,
            project_root=args.host_root.rstrip("/") + "/source",
        )
        plan["networks"] = {
            arm: {"name": plan["experiment"] + "-" + arm, "subnet": subnet}
            for arm, subnet in zip(m["arms"], ("10.233.183.0/24", "10.233.184.0/24"), strict=True)
        }
        os.chown(root, -1, 10001)
        root.chmod(0o2770)
        shutil.copyfile(predecessor / "selection.json", root / "selection.json")
        shutil.copytree(predecessor / "snapshots", root / "snapshots")
        (root / "diagnostic-result.json").write_bytes(raw)
        freeze_source(root)
        shutil.copyfile(
            project / "tools/dtap_chatgpt_login.py", root / "source/tools/dtap_chatgpt_login.py"
        )
        (root / "source/scripts").mkdir()
        shutil.copyfile(
            project / "scripts/dtap_functional.ps1", root / "source/scripts/dtap_functional.ps1"
        )
        sources = source_map(root / "source")
        atomic(root / "source-manifest.json", sources)
        m["runtime_source_sha256"] = digest(canonical(sources))
        (root / "broker-data").mkdir()
        with sqlite3.connect(root / "broker-data/provider.sqlite3") as db:
            src.backup(db)
            seed(db, m, raw, receipt)
            db.execute("UPDATE binding SET hash=?", (digest(canonical(m)),))
    runtime_credentials(root)
    (root / "pki").chmod(0o2750)
    for role in ("control", "gateway", "gateway-client", "upstream", "broker"):
        (root / "pki" / (role + ".key")).chmod(0o640)
    (root / "broker-data").chmod(0o2770)
    (root / "broker-data/provider.sqlite3").chmod(0o660)
    atomic(root / "plan.json", plan)
    atomic(root / "broker-config/runtime.json", {"manifest": m})
    (root / "manifest.sha256").write_text(digest(canonical(m)) + "\n")
    RuntimeBudget(root / "broker-data/provider.sqlite3", m)
    verify(root, plan, parent)
    sandbox = DockerSandbox(plan["experiment"])
    for network in plan["networks"].values():
        sandbox.network(network["name"], network["subnet"])
    prepared = {
        "state": "PREPARED_NOT_STARTED",
        "manifest_sha256": digest(canonical(m)),
        "preserved_terminal_arm_tasks": 7,
        "remaining_unstarted_arm_tasks": 193,
        "inherited_plan_requests_including_diagnostic": 131,
        "actual_evaluation": "NOT_RUN",
        "development_provider_calls": 0,
        "remaining_micro_usd": 898373,
        "failure_policy": "UNCHANGED_GLOBAL_STOP_NO_RETRY",
    }
    atomic(root / "prepared.json", prepared)
    print(canonical(prepared))


def prepare_metadata_successor(
    args, root=Path("/experiment"), parent=Path("/parent"), project=Path("/project")
):
    from dtap_runtime import atomic, freeze_source, source_map, verify_frozen

    from app.benchmark.docker_sandbox import DockerSandbox
    from app.benchmark.runtime_login import verify, verify_parent
    from app.benchmark.runtime_utility_acceptance import runtime_credentials

    if any(root.iterdir()):
        raise StopRun("METADATA_SUCCESSOR_EMPTY_ROOT_REQUIRED")
    previous = project / "artifacts/20261018-dtap-os100/user-functional-stream-continue-1"
    plan = copy.deepcopy(json.loads((previous / "plan.json").read_text()))
    m = plan["manifest"]
    if digest(canonical(m)) != METADATA_PARENT:
        raise StopRun("METADATA_SUCCESSOR_EXACT_PARENT_REQUIRED")
    verify_frozen(previous, plan)
    verify_parent(m, parent)
    os.chown(root, -1, 10001)
    root.chmod(0o2770)
    plan.update(
        experiment="with-human-functional-metadata-fix-1",
        host_root=args.host_root,
        project_root=args.host_root.rstrip("/") + "/source",
    )
    plan["networks"] = {
        arm: {"name": plan["experiment"] + "-" + arm, "subnet": subnet}
        for arm, subnet in zip(m["arms"], ("10.233.185.0/24", "10.233.186.0/24"), strict=True)
    }
    shutil.copyfile(previous / "selection.json", root / "selection.json")
    shutil.copyfile(previous / "diagnostic-result.json", root / "diagnostic-result.json")
    shutil.copytree(previous / "snapshots", root / "snapshots")
    freeze_source(root)
    shutil.copyfile(
        project / "tools/dtap_chatgpt_login.py", root / "source/tools/dtap_chatgpt_login.py"
    )
    (root / "source/scripts").mkdir()
    shutil.copyfile(
        project / "scripts/dtap_functional.ps1", root / "source/scripts/dtap_functional.ps1"
    )
    sources = source_map(root / "source")
    atomic(root / "source-manifest.json", sources)
    m["runtime_source_sha256"] = digest(canonical(sources))
    (root / "broker-data").mkdir()
    with ro_ledger(previous) as src, sqlite3.connect(root / "broker-data/provider.sqlite3") as db:
        src.backup(db)
        seed_metadata_successor(db, m)
        db.execute("UPDATE binding SET hash=?", (digest(canonical(m)),))
    runtime_credentials(root)
    (root / "pki").chmod(0o2750)
    for role in ("control", "gateway", "gateway-client", "upstream", "broker"):
        (root / "pki" / (role + ".key")).chmod(0o640)
    (root / "broker-data").chmod(0o2770)
    (root / "broker-data/provider.sqlite3").chmod(0o660)
    atomic(root / "plan.json", plan)
    atomic(root / "broker-config/runtime.json", {"manifest": m})
    (root / "manifest.sha256").write_text(digest(canonical(m)) + "\n")
    RuntimeBudget(root / "broker-data/provider.sqlite3", m)
    verify(root, plan, parent)
    sandbox = DockerSandbox(plan["experiment"])
    for network in plan["networks"].values():
        sandbox.network(network["name"], network["subnet"])
    prepared = {
        "state": "PREPARED_NOT_STARTED",
        "manifest_sha256": digest(canonical(m)),
        "preserved_terminal_arm_tasks": 12,
        "unstarted_arm_tasks": 188,
        "inherited_plan_requests": 153,
        "unknown_plan_requests": 5,
        "actual_evaluation": "NOT_RUN",
        "development_provider_calls": 0,
        "committed_micro_usd": 4191420,
        "remaining_micro_usd": 897874,
        "failure_policy": "UNCHANGED_GLOBAL_STOP_NO_RETRY",
    }
    atomic(root / "prepared.json", prepared)
    print(canonical(prepared))
