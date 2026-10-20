"""One reviewed successor: unstarted scope-v2 tasks, no extra budget or replay."""

import copy
import json
import secrets
import shutil
import sqlite3
from pathlib import Path

from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.runtime_continuation import ledger_fingerprint
from app.common import canonical, digest

PARENT = "338e9f53a7060ab7682c38ab5ccedbcb30a90b7aa84e0d4d6f99ca9c51ccdbd8"
EXCLUDED = "os-filesystem/malicious/indirect/consent-violations/11"
CAP = 5089294
COMMITTED = 3332794


def successor_keys(parent, original):
    from app.benchmark.runtime_demo import ro_ledger

    with ro_ledger(parent) as db:
        if db.execute("SELECT 1 FROM owners").fetchone():
            raise StopRun("DENY_PARENT_CONTROLLER_ACTIVE")
        if not db.execute(
            "SELECT 1 FROM stops WHERE id>coalesce((SELECT max(before_stop) FROM resumes),0)"
        ).fetchone():
            raise StopRun("DENY_PARENT_MUST_REMAIN_STOPPED")
        on = db.execute(
            "SELECT task,state FROM jobs WHERE arm='engine-on' ORDER BY task"
        ).fetchall()
        if on != [(EXCLUDED, "UNKNOWN")]:
            raise StopRun("DENY_PARENT_ATTEMPTS_CHANGED")
        committed = db.execute(
            "SELECT coalesce(sum(coalesce(s.micro_usd,r.micro_usd)),0) FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id"
        ).fetchone()[0]
        if committed != COMMITTED:
            raise StopRun("DENY_PARENT_COST_OR_HOLD_CHANGED")
    keys = [key for key in original if key != EXCLUDED]
    if len(original) != 15 or len(keys) != 14 or EXCLUDED not in original:
        raise StopRun("DENY_PARENT_COHORT_CHANGED")
    return keys


def verify_selection(manifest, parent):
    old = json.loads((parent / "plan.json").read_text())["manifest"]
    keys = successor_keys(parent, old["task_keys"])
    if manifest["task_keys"] != keys or manifest["limits"]["total"]["micro_usd"] != CAP:
        raise StopRun("DENY_SUCCESSOR_SCOPE_OR_CAP_CHANGED")
    if manifest["demo"]["parent_committed_micro_usd"] != COMMITTED:
        raise StopRun("DENY_SUCCESSOR_COST_CHANGED")
    for field in ("actor_model", "reasoning_effort", "providers"):
        if manifest.get(field) != old.get(field):
            raise StopRun("DENY_SUCCESSOR_PROVIDER_CONFIGURATION_CHANGED")
    for field in ("task_scopes", "reviewed_operations"):
        if manifest["demo"][field] != {k: v for k, v in old["demo"][field].items() if k in keys}:
            raise StopRun("DENY_SUCCESSOR_GRANT_CHANGED")


def prepare(args, root=Path("/experiment"), parent=Path("/parent")):
    from dtap_runtime import atomic, freeze_source, private_tree, verify_frozen
    from prepare_tls import generate

    from app.benchmark.docker_sandbox import DockerSandbox
    from app.benchmark.runtime_demo import ro_ledger

    if any(root.iterdir()):
        raise StopRun("NEW_EMPTY_DENY_SUCCESSOR_REQUIRED")
    old = json.loads((parent / "plan.json").read_text())
    if digest(canonical(old["manifest"])) != PARENT or old["host_root"] != args.parent_host_root:
        raise StopRun("DENY_EXACT_PARENT_REQUIRED")
    verify_frozen(parent, old)
    keys = successor_keys(parent, old["manifest"]["task_keys"])
    plan = copy.deepcopy(old)
    m = plan["manifest"]
    m["runtime_deny_followup"] = {"excluded_unknown_task": EXCLUDED, "new_paid_calls": 0}
    m["task_keys"] = keys
    m["target_total"] = m["runtime_ready"] = 14
    plan["coverage"] = [r for r in old["coverage"] if r["task_key"] in keys]
    m["coverage_sha256"] = digest(canonical(plan["coverage"]))
    inventory = json.loads(
        Path("/project/artifacts/20261017-dtap-prepare/inventory-final/inventory.json").read_text()
    )
    indexed = {r["task_key"]: r for r in inventory}
    m["task_manifest_sha256"] = digest(canonical([indexed[k] for k in keys]))
    demo = m["demo"]
    demo.update(
        parent_host_root=args.parent_host_root,
        parent_manifest_sha256=PARENT,
        parent_committed_micro_usd=COMMITTED,
        additional_cap_micro_usd=CAP - COMMITTED,
    )
    for field in ("task_scopes", "reviewed_operations"):
        demo[field] = {k: v for k, v in demo[field].items() if k in keys}
    demo["presentation"] = [r for r in demo["presentation"] if r["task_key"] in keys]
    for key in demo["inherited_initial_snapshots"]:
        target = root / "snapshots" / digest(key)
        shutil.copytree(parent / "snapshots" / digest(key), target)
    m["runtime_source_sha256"] = freeze_source(root)
    plan.update(
        experiment="with-human-engine-demo-02-deny-followup",
        host_root=args.host_root,
        project_root=args.host_root.rstrip("/") + "/source",
    )
    plan["networks"] = {
        arm: {"name": plan["experiment"] + suffix, "subnet": subnet}
        for arm, suffix, subnet in [
            ("engine-off", "-off", args.subnet_off),
            ("engine-on", "-on", args.subnet_on),
        ]
    }
    (root / "broker-data").mkdir()
    with ro_ledger(parent) as source, sqlite3.connect(root / "broker-data/provider.sqlite3") as db:
        demo["parent_ledger_sha256"] = ledger_fingerprint(source)
        source.backup(db)
        for table in ("jobs", "stops", "resumes", "owners"):
            db.execute("CREATE TABLE deny_parent_" + table + " AS SELECT * FROM " + table)
            db.execute("DELETE FROM " + table)
        for key in keys:
            db.execute(
                "INSERT INTO jobs SELECT * FROM deny_parent_jobs WHERE task=? AND arm='engine-off' AND state='COMPLETED'",
                (key,),
            )
        db.execute("UPDATE binding SET hash=?", (digest(canonical(m)),))
    verify_selection(m, parent)
    budget = RuntimeBudget(root / "broker-data/provider.sqlite3", m)
    if budget.status()["committed_micro_usd"] != COMMITTED:
        raise StopRun("DENY_INHERITED_COST_LOST")
    pki = root / "pki"
    generate(pki, [("upstream", ["upstream"]), ("broker", ["broker", "localhost", "127.0.0.1"])])
    for folder, names in [
        ("task-runtime", [p.name for p in pki.iterdir()]),
        ("broker-runtime", ["ca.pem", "broker.pem", "broker.key"]),
    ]:
        target = root / folder
        target.mkdir()
        for name in names:
            shutil.copyfile(pki / name, target / name)
    for folder, names in [
        ("task-runtime", ("machine.id", "machine.token", "forward.key")),
        ("broker-runtime", ("admin.token", "broker.secret")),
    ]:
        for name in names:
            (root / folder / name).write_text(secrets.token_urlsafe(48))
    atomic(root / "plan.json", plan)
    atomic(root / "broker-config/runtime.json", {"manifest": m})
    atomic(root / "selection.json", {"unstarted": keys, "excluded_unknown": EXCLUDED})
    sandbox = DockerSandbox(plan["experiment"])
    for network in plan["networks"].values():
        sandbox.network(network["name"], network["subnet"])
    (root / "manifest.sha256").write_text(digest(canonical(m)) + "\n")
    private_tree(root)
    prepared = {
        "state": "PREPARED_NOT_STARTED",
        "provider_calls": 0,
        "target_total": 14,
        "parent_committed_micro_usd": COMMITTED,
        "new_maximum_micro_usd": CAP,
        "remaining_micro_usd": CAP - COMMITTED,
        "manifest_sha256": digest(canonical(m)),
    }
    atomic(root / "prepared.json", prepared)
    print(canonical(prepared))
