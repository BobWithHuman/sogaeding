"""One official paired acceptance after the real SIWC tool-response probe."""

import copy
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_demo import ro_ledger
from app.benchmark.runtime_utility_acceptance import runtime_credentials
from app.common import canonical, digest

PARENT = "a02391481b552d1419fec2ecb16704cf8928903196958284c9569c92b93ea71e"
PROBE = "8fc7c6afd12a6888d0094d35fbdcfffb8a7a6b96e51d72481b86865b2f4ba91b"
KEY = "os-filesystem/malicious/indirect/consent-violations/3"
TABLES = {
    "pair_parent_jobs": ("task", "arm"),
    "pair_parent_stops": ("id",),
    "plan_requests": ("id",),
    "plan_account": ("binding",),
    "resources": ("identity",),
    "reservations": ("id",),
    "settlements": ("reservation",),
}


def baseline(db):
    result = {}
    for table, keys in TABLES.items():
        columns = [r[1] for r in db.execute("PRAGMA table_info(" + table + ")")]
        result[table] = [
            {"key": [row[columns.index(k)] for k in keys], "sha256": digest(canonical(row))}
            for row in db.execute("SELECT * FROM " + table + " ORDER BY 1")
        ]
    return result


def verify_rows(db, manifest):
    pair = manifest.get("chatgpt_plan", {}).get("paired_acceptance")
    if pair is None:
        return
    if (
        pair["parent_manifest_sha256"] != PARENT
        or pair["probe_manifest_sha256"] != PROBE
        or set(pair["parent_rows"]) != set(TABLES)
    ):
        raise StopRun("SIWC_PAIR_HISTORY_BINDING_CHANGED")
    for table, keys in TABLES.items():
        for entry in pair["parent_rows"][table]:
            row = db.execute(
                "SELECT * FROM " + table + " WHERE " + " AND ".join(k + "=?" for k in keys),
                entry["key"],
            ).fetchone()
            if row is None or digest(canonical(row)) != entry["sha256"]:
                raise StopRun("SIWC_PAIR_HISTORY_RECORD_CHANGED")


def verify_pair(root, manifest):
    from app.benchmark.runtime_login import SELECTION

    m = manifest
    pair = m["chatgpt_plan"]["paired_acceptance"]
    if (
        m["task_keys"] != [KEY]
        or m["target_total"] != 1
        or m["runtime_ready"] != 1
        or m["selection_profile"] != "SIWC_OFFICIAL_ONE_PAIR_ACCEPTANCE"
        or m["task_limits"]["responses"] != 8
        or m["task_limits"]["tool_calls"] != 8
        or m["wall_seconds_per_arm"] != 1200
        or m["chatgpt_plan"]["limits"]["requests"] != 140
        or m["chatgpt_plan"]["limits"]["per_arm_requests"] != 68
        or pair["parent_manifest_sha256"] != PARENT
        or pair["probe_manifest_sha256"] != PROBE
    ):
        raise StopRun("SIWC_PAIR_SCOPE_CHANGED")
    selection = (root / "selection.json").read_bytes()
    source = json.loads(selection)
    if (
        m["selection_sha256"] != SELECTION
        or hashlib.sha256(selection).hexdigest() != SELECTION
        or len(source["task_keys"]) != 100
        or KEY not in source["task_keys"]
    ):
        raise StopRun("SIWC_PAIR_ORIGINAL_SELECTION_REQUIRED")
    path = root / "snapshots" / digest(KEY) / "snapshot.json"
    if hashlib.sha256(path.read_bytes()).hexdigest() != pair["initial_snapshot_sha256"]:
        raise StopRun("SIWC_PAIR_INITIAL_SNAPSHOT_CHANGED")
    proof = root / "tool-probe-result.json"
    if hashlib.sha256(proof.read_bytes()).hexdigest() != pair["probe_result_sha256"]:
        raise StopRun("SIWC_PAIR_TOOL_PROOF_CHANGED")


def prepare(args, root=Path("/experiment"), parent=Path("/parent"), project=Path("/project")):
    from dtap_runtime import atomic, freeze_source, source_map

    from app.benchmark.docker_sandbox import DockerSandbox
    from app.benchmark.runtime_login import verify

    if any(root.iterdir()):
        raise StopRun("SIWC_PAIR_NEW_EMPTY_ROOT_REQUIRED")
    failed = project / "artifacts/20261018-dtap-os100/user-chatgpt-login-luna-stream1"
    plan = copy.deepcopy(json.loads((failed / "plan.json").read_text()))
    if digest(canonical(plan["manifest"])) != PARENT:
        raise StopRun("SIWC_PAIR_PARENT_CHANGED")
    probe_root = project / "artifacts/20261020-siwc-tool-probe"
    if hashlib.sha256((probe_root / "bundle/manifest.json").read_bytes()).hexdigest() != PROBE:
        raise StopRun("SIWC_PAIR_PROBE_MANIFEST_CHANGED")
    # Public proof copies avoid granting the UID0 preparer DAC override access
    # to UID10001's private result/snapshot directories. Original files stay RO.
    public = project / "artifacts/20261020-siwc-pair-acceptance"
    probe_raw = (public / "tool-proof.json").read_bytes()
    if hashlib.sha256(probe_raw).hexdigest() != "73883793941af42c7d3c3323d7dfa39b3345c3f37b7fc3554a9158f8680ff621":
        raise StopRun("SIWC_PAIR_TOOL_PROOF_COPY_CHANGED")
    proof = json.loads(probe_raw)
    if (
        proof.get("state") != "COMPLETED"
        or proof.get("tool_response_validated") is not True
        or proof.get("tool_calls") != 1
        or proof.get("tool_executions") != 0
        or proof.get("model") != "gpt-5.6-luna"
        or proof.get("reasoning_effort") != "low"
        or proof.get("api_key_fallback") is not False
        or proof.get("usage") != {"input_tokens": 167, "output_tokens": 21}
    ):
        raise StopRun("SIWC_PAIR_REAL_TOOL_PROOF_REQUIRED")
    os.chown(root, -1, 10001)
    root.chmod(0o2770)
    m = plan["manifest"]
    m.update(
        task_keys=[KEY],
        target_total=1,
        runtime_ready=1,
        selection_profile="SIWC_OFFICIAL_ONE_PAIR_ACCEPTANCE",
        selection_task_keys_sha256=digest(canonical([KEY])),
        wall_seconds_per_arm=1200,
    )
    plan["coverage"] = [r for r in plan["coverage"] if r["task_key"] == KEY]
    m["coverage_sha256"] = digest(canonical(plan["coverage"]))
    m["task_limits"].update(responses=8, tool_calls=8, seconds=900)
    login = m["chatgpt_plan"]
    login.pop("transport_history")
    login["task_scopes"] = {KEY: login["task_scopes"][KEY]}
    login["task_files"] = {KEY: login["task_files"][KEY]}
    login["limits"].update(requests=140, per_arm_requests=68)
    snapshot_raw = (public / "initial-snapshot.json").read_bytes()
    snapshot = json.loads(snapshot_raw)
    if snapshot.get("task_key") != KEY:
        raise StopRun("SIWC_PAIR_INITIAL_TASK_CHANGED")
    login["inherited_initial_snapshots"] = {
        KEY: {"image": snapshot["image"], "sha256": hashlib.sha256(snapshot_raw).hexdigest()}
    }
    plan.update(
        experiment="with-human-luna-pair-1",
        host_root=args.host_root,
        project_root=args.host_root.rstrip("/") + "/source",
    )
    plan["networks"] = {
        arm: {"name": plan["experiment"] + "-" + arm, "subnet": subnet}
        for arm, subnet in zip(m["arms"], ("10.233.177.0/24", "10.233.178.0/24"), strict=True)
    }
    (root / "selection.json").write_bytes((failed / "selection.json").read_bytes())
    (root / "tool-probe-result.json").write_bytes(probe_raw)
    snap = root / "snapshots" / digest(KEY)
    snap.mkdir(parents=True)
    (snap / "snapshot.json").write_bytes(snapshot_raw)
    (snap / "seed.lock").write_text("Original initial image only; no setup or UNKNOWN replay.")
    freeze_source(root)
    shutil.copyfile(
        project / "tools/dtap_chatgpt_login.py", root / "source/tools/dtap_chatgpt_login.py"
    )
    (root / "source/scripts").mkdir(exist_ok=True)
    shutil.copyfile(
        project / "scripts/dtap_login_pair.ps1", root / "source/scripts/dtap_login_pair.ps1"
    )
    sources = source_map(root / "source")
    atomic(root / "source-manifest.json", sources)
    m["runtime_source_sha256"] = digest(canonical(sources))
    (root / "broker-data").mkdir()
    with ro_ledger(failed) as source, sqlite3.connect(root / "broker-data/provider.sqlite3") as db:
        if (
            source.execute("SELECT 1 FROM owners").fetchone()
            or source.execute("SELECT 1 FROM jobs WHERE state='CLAIMED'").fetchone()
            or source.execute("SELECT 1 FROM plan_requests WHERE state='STARTED'").fetchone()
            or source.execute("SELECT hash FROM binding").fetchone() != (PARENT,)
            or source.execute("SELECT count(*) FROM plan_requests").fetchone()[0] != 115
        ):
            raise StopRun("SIWC_PAIR_PARENT_ACTIVE_OR_CHANGED")
        states = source.execute("SELECT arm,state FROM jobs WHERE task=?", (KEY,)).fetchall()
        if sorted(states) != [("engine-off", "INCOMPLETE"), ("engine-on", "INCOMPLETE")]:
            raise StopRun("SIWC_PAIR_PRIOR_UNKNOWN_NOT_RETRYABLE")
        for (encoded,) in source.execute("SELECT result FROM jobs WHERE task=?", (KEY,)):
            previous = json.loads(encoded)
            events = previous.get("events", [])
            if (
                previous.get("actor_completed") is not False
                or not any(e.get("code") == "NO_FINAL_MESSAGE" for e in events)
                or any(
                    e.get("kind") == "tool_result" or e.get("stage") in ("PRE", "POST")
                    for e in events
                )
            ):
                raise StopRun("SIWC_PAIR_PRIOR_EFFECT_NOT_CLEAR")
        if (
            source.execute("SELECT count(*) FROM reservations").fetchone()[0] != 429
            or source.execute(
                "SELECT sum(coalesce(s.micro_usd,r.micro_usd)) FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id"
            ).fetchone()[0]
            != 4190921
        ):
            raise StopRun("SIWC_PAIR_API_ACCOUNTING_CHANGED")
        source.backup(db)
        for table in ("jobs", "stops"):
            db.execute("CREATE TABLE pair_parent_" + table + " AS SELECT * FROM " + table)
            db.execute("DELETE FROM " + table)
        db.execute(
            "INSERT INTO plan_requests VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "diagnostic:tool-probe-8fc7c6af",
                "tool-response-probe",
                "diagnostic",
                "protocol-probe",
                "gpt-5.6-luna",
                "COMPLETED",
                0,
                canonical(proof["usage"]),
                60,
            ),
        )
        login["paired_acceptance"] = {
            "parent_manifest_sha256": PARENT,
            "probe_manifest_sha256": PROBE,
            "probe_result_sha256": hashlib.sha256(probe_raw).hexdigest(),
            "initial_snapshot_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
            "parent_rows": baseline(db),
            "purpose": "FUNCTIONAL_ACCEPTANCE_NOT_FULL_ASR",
        }
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
    atomic(
        root / "prepared.json",
        {
            "state": "PAIRED_ACCEPTANCE_READY",
            "manifest_sha256": digest(canonical(m)),
            "actual_evaluation": "NOT_RUN",
            "new_provider_calls": 0,
            "remaining_micro_usd": 898373,
        },
    )
    sandbox = DockerSandbox(plan["experiment"])
    if (
        sandbox.request("GET", "/images/" + snapshot["image"] + "/json").get("Id")
        != snapshot["image"]
    ):
        raise StopRun("SIWC_PAIR_INITIAL_IMAGE_UNAVAILABLE")
    for network in plan["networks"].values():
        sandbox.network(network["name"], network["subnet"])
    RuntimeBudget(root / "broker-data/provider.sqlite3", m)
    verify(root, plan, parent)
    print(canonical(json.loads((root / "prepared.json").read_text())))
