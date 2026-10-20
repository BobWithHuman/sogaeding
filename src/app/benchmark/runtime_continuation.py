"""Single, parent-bound USD7 continuation. Never rewrites the failed run."""

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

from app.benchmark.runtime_budget import (
    SETTLED_COST,
    RuntimeBudget,
    StopRun,
    charge,
    parent_baseline,
    verify_continuation_ledger,
)
from app.common import canonical, digest

PARENT_MANIFEST = "742efbc00e212f7e313bace19e4e296234de6a1b41630f16f92dbfa9d1368433"
SETTLED_PARENT_MANIFEST = "764b1bd63a92edccdb4b15f45bb06a0496525eb82e99ca6d2fc942329d7813fb"
CLAIM = "usd7-successor.json"
TABLES = ("binding", "stops", "jobs", "reservations", "owners", "resources", "resumes")


def ledger_fingerprint(db):
    # Hash opaque rows; no decryption or disclosure of task/model bodies.
    return digest(
        canonical(
            {
                table: db.execute("SELECT * FROM " + table + " ORDER BY 1,2").fetchall()
                for table in (*TABLES, "settlements", "budget_rejections", "lineage")
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            }
        )
    )


def read_parent(parent, expected=PARENT_MANIFEST):
    if expected not in (PARENT_MANIFEST, SETTLED_PARENT_MANIFEST):
        raise StopRun("UNREVIEWED_PARENT_MANIFEST")
    plan = json.loads((parent / "plan.json").read_text())
    if digest(canonical(plan["manifest"])) != expected:
        raise StopRun("PARENT_MANIFEST_CHANGED")
    if plan["manifest"]["limits"]["total"]["micro_usd"] != 7000000:
        raise StopRun("ORIGINAL_CUMULATIVE_USD7_REQUIRED")
    return plan


def seed_ledger(parent, child, manifest):
    """Snapshot a stopped ledger; preserve jobs/holds/stops, settle only known usage."""
    path = parent / "broker-data/provider.sqlite3"
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as original:
        original.execute("PRAGMA query_only=ON")
        original.execute("BEGIN")
        if (
            original.execute("SELECT 1 FROM owners").fetchone()
            or original.execute("SELECT 1 FROM reservations WHERE state='STARTED'").fetchone()
            or original.execute("SELECT 1 FROM jobs WHERE state='CLAIMED'").fetchone()
        ):
            raise StopRun("PARENT_ACTIVE_OR_UNRECONCILED")
        if not original.execute("SELECT 1 FROM stops").fetchone():
            raise StopRun("STOPPED_PARENT_REQUIRED")
        parent_hash = original.execute("SELECT hash FROM binding").fetchone()
        if not parent_hash or parent_hash[0] != manifest["continuation"]["parent_manifest_sha256"]:
            raise StopRun("PARENT_LEDGER_BINDING_CHANGED")
        if ledger_fingerprint(original) != manifest["continuation"]["parent_ledger_sha256"]:
            raise StopRun("PARENT_LEDGER_CHANGED")
        with sqlite3.connect(child / "broker-data/provider.sqlite3") as dest:
            original.backup(dest)
            dest.execute("UPDATE binding SET hash=?", (digest(canonical(manifest)),))
            dest.execute("CREATE TABLE IF NOT EXISTS lineage_history(parent_hash TEXT PRIMARY KEY,manifest_hash TEXT)")
            if dest.execute("SELECT 1 FROM sqlite_master WHERE name='lineage'").fetchone():
                dest.execute("INSERT OR IGNORE INTO lineage_history SELECT * FROM lineage")
                dest.execute("DELETE FROM lineage")
            dest.execute("CREATE TABLE IF NOT EXISTS lineage(parent_hash TEXT PRIMARY KEY,manifest_hash TEXT)")
            dest.execute(
                "INSERT INTO lineage VALUES(?,?)",
                (manifest["continuation"]["parent_ledger_sha256"], digest(canonical(manifest))),
            )
            # Explicit revision boundary only in the child. Old stops remain immutable.
            dest.execute("INSERT INTO resumes(before_stop,at) SELECT max(id),0 FROM stops")
    budget = RuntimeBudget(child / "broker-data/provider.sqlite3", manifest)
    with budget.db() as db:
        rows = db.execute(
            "SELECT id,provider,model,inputs,outputs,usage FROM reservations WHERE state='COMPLETED'"
        ).fetchall()
        for rid, provider, model, inputs, outputs, encoded in rows:
            value = json.loads(encoded) if encoded else {}
            usage = value.get("tokens")
            profile = manifest["providers"][provider]
            if (
                not isinstance(usage, dict)
                or value.get("resolved_model")
                not in profile.get("billing_model_aliases", {}).get(model, [])
                or any(
                    type(usage.get(key)) is not int or not 0 <= usage[key] <= maximum
                    for key, maximum in (("input_tokens", inputs), ("output_tokens", outputs))
                )
            ):
                continue  # Keep the entire original hold for unverifiable usage.
            db.execute(
                "INSERT OR IGNORE INTO settlements VALUES(?,?)",
                (
                    rid,
                    charge(profile["rates"][model], usage["input_tokens"], usage["output_tokens"]),
                ),
            )
    return budget


def claim_successor(parent, host_root, manifest):
    with (parent / CLAIM).open("x", encoding="utf-8") as file:
        file.write(
            canonical(
                {"child_host_root": host_root, "child_manifest_sha256": digest(canonical(manifest))}
            )
        )


def inherited_snapshots(parent, plan):
    snapshots = {}
    with sqlite3.connect((parent / "broker-data/provider.sqlite3").resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        jobs = db.execute("SELECT task,arm,result FROM jobs").fetchall()
    attempted = {(key, arm) for key, arm, _ in jobs}
    required = {}
    for key, arm, encoded in jobs:
        other = "engine-on" if arm == "engine-off" else "engine-off"
        if (key, other) not in attempted:
            image = (json.loads(encoded or "{}").get("initial_snapshot") or {}).get("image")
            if not image:
                raise StopRun("PARENT_INITIAL_STATE_UNVERIFIED_NO_SETUP_REPLAY")
            required[key] = image
    for folder in (parent / "snapshots").glob("*"):
        ready = folder / "snapshot.json"
        if not ready.is_file():
            raise StopRun("PARENT_SEED_UNKNOWN_PRESERVED")
        value = json.loads(ready.read_text())
        key = value.get("task_key")
        if key not in plan["manifest"]["task_keys"] or folder.name != digest(key):
            raise StopRun("PARENT_SNAPSHOT_TASK_BINDING_CHANGED")
        row = next(row for row in plan["coverage"] if row["task_key"] == key)
        if value.get("original_setup_sha256") != row["setup_sha256"]:
            raise StopRun("PARENT_SNAPSHOT_SETUP_CHANGED")
        if key in required and value.get("image") != required[key]:
            raise StopRun("PARENT_PAIRED_IMAGE_CHANGED")
        snapshots[key] = {"image": value["image"], "sha256": hashlib.sha256(ready.read_bytes()).hexdigest()}
    if not set(required) <= set(snapshots):
        raise StopRun("PARENT_INITIAL_SNAPSHOT_MISSING_NO_SETUP_REPLAY")
    return snapshots


def verify_parent(root, plan, parent):
    binding = plan["manifest"].get("continuation")
    if not binding:
        raise StopRun("USD7_PARENT_BOUND_CONTINUATION_REQUIRED")
    parent_plan = read_parent(parent, binding["parent_manifest_sha256"])
    claim = json.loads((parent / CLAIM).read_text())
    expected = {
        "child_host_root": plan["host_root"],
        "child_manifest_sha256": digest(canonical(plan["manifest"])),
    }
    if claim != expected or binding["parent_host_root"] != parent_plan["host_root"]:
        raise StopRun("USD7_SINGLE_SUCCESSOR_BINDING_CHANGED")
    with sqlite3.connect(
        (parent / "broker-data/provider.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
    ) as db:
        db.execute("PRAGMA query_only=ON")
        if ledger_fingerprint(db) != binding["parent_ledger_sha256"]:
            raise StopRun("PARENT_LEDGER_CHANGED")
    if json.loads((root / "plan.json").read_text()) != plan:
        raise StopRun("CONTINUATION_PLAN_CHANGED")
    verify_continuation_ledger(root / "broker-data/provider.sqlite3", plan["manifest"])
    for key, record in binding.get("inherited_initial_snapshots", {}).items():
        for folder in (root, parent):
            if hashlib.sha256((folder / "snapshots" / digest(key) / "snapshot.json").read_bytes()).hexdigest() != record["sha256"]:
                raise StopRun("INHERITED_INITIAL_SNAPSHOT_CHANGED")


def prepare(args, root=Path("/experiment"), parent=Path("/parent")):
    from dtap_runtime import atomic, freeze_source, private_tree, verify_frozen
    from prepare_tls import generate

    if any(root.iterdir()):
        raise StopRun("NEW_EMPTY_CONTINUATION_DIRECTORY_REQUIRED")
    expected_parent = args.continue_parent_sha256 or PARENT_MANIFEST
    parent_plan = read_parent(parent, expected_parent)
    if args.parent_host_root != parent_plan["host_root"]:
        raise StopRun("PARENT_HOST_PATH_CHANGED")
    verify_frozen(parent, parent_plan)
    with sqlite3.connect(
        (parent / "broker-data/provider.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
    ) as db:
        db.execute("PRAGMA query_only=ON")
        fingerprint = ledger_fingerprint(db)
        baseline = parent_baseline(db)
    plan = copy.deepcopy(parent_plan)
    manifest = plan["manifest"]
    manifest["cost_accounting"] = SETTLED_COST
    manifest["reservation_basis"] = (
        "Full-context pending/UNKNOWN holds; verified COMPLETED usage at enrolled uncached rates; original USD7 cumulative cap."
    )
    for profile in manifest["providers"].values():
        profile["billing_model_aliases"] = {
            model: [model, "gpt-5.2-2025-12-11"] if model == "gpt-5.2" else [model]
            for model in profile["models"]
        }
    manifest["continuation"] = {
        "parent_host_root": args.parent_host_root,
        "parent_manifest_sha256": expected_parent,
        "parent_ledger_sha256": fingerprint,
        "parent_rows": baseline,
        "inherited_initial_snapshots": inherited_snapshots(parent, parent_plan),
        "scope": "UNSTARTED_TASK_ARMS_ONLY; original jobs/UNKNOWN/CONFIRM immutable",
    }
    manifest["runtime_source_sha256"] = freeze_source(root)
    # Keep all original product/benchmark files identical except the reviewed repair.
    before = json.loads((parent / "source-manifest.json").read_text())
    after = json.loads((root / "source-manifest.json").read_text())
    allowed = {
        "src/app/benchmark/" + name + ".py"
        for name in ("runtime_budget", "runtime_continuation", "runtime_controller", "provider", "runtime_policy",
                     "server", "proxy", "hook", "official_adapter")
    }
    allowed.add("tools/dtap_runtime.py")
    allowed.update(("src/app/transparent/engine.py", "src/app/transparent/server.py"))
    if {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)} - allowed:
        raise StopRun("UNRELATED_PRODUCT_SOURCE_CHANGED")
    plan["experiment"] = parent_plan["experiment"] + "-settled1"
    plan["host_root"] = args.host_root
    plan["project_root"] = args.host_root.rstrip("/") + "/source"
    plan["networks"] = {
        arm: {"name": plan["experiment"] + suffix, "subnet": subnet}
        for arm, suffix, subnet in (
            ("engine-off", "-off", args.subnet_off),
            ("engine-on", "-on", args.subnet_on),
        )
    }
    # Single authoritative child, allocated once even if preparation is interrupted.
    claim_successor(parent, args.host_root, manifest)
    for name in ("selection.json", "COVERAGE.csv"):
        (root / name).write_bytes((parent / name).read_bytes())
    for key in manifest["continuation"]["inherited_initial_snapshots"]:
        folder = root / "snapshots" / digest(key)
        folder.mkdir(parents=True)
        (folder / "snapshot.json").write_bytes((parent / "snapshots" / digest(key) / "snapshot.json").read_bytes())
        (folder / "seed.lock").write_text("Inherited immutable initial image; no setup replay.")
    (root / "broker-data").mkdir()
    budget = seed_ledger(parent, root, manifest)
    pki = root / "pki"
    generate(pki, [("upstream", ["upstream"]), ("broker", ["broker", "localhost", "127.0.0.1"])])
    import secrets
    import shutil

    for folder, names in (
        ("task-runtime", [p.name for p in pki.iterdir()]),
        ("broker-runtime", ["ca.pem", "broker.pem", "broker.key"]),
    ):
        target = root / folder
        target.mkdir()
        for name in names:
            shutil.copyfile(pki / name, target / name)
    for folder, names in (
        ("task-runtime", ("machine.id", "machine.token", "forward.key")),
        ("broker-runtime", ("admin.token", "broker.secret")),
    ):
        for name in names:
            (root / folder / name).write_text(secrets.token_urlsafe(48))
    atomic(root / "broker-config/runtime.json", {"manifest": manifest})
    atomic(root / "plan.json", plan)
    (root / "manifest.sha256").write_text(digest(canonical(manifest)) + "\n")
    private_tree(root)
    print(
        canonical(
            {
                "manifest_sha256": digest(canonical(manifest)),
                "state": "PREPARED_NOT_STARTED",
                "budget": budget.status(),
            }
        )
    )
