"""Immutable prior login attempts; UNKNOWN jobs are never submitted again."""

import json
import sqlite3
from pathlib import Path

from app.benchmark.runtime_budget import StopRun
from app.common import canonical, digest

PARENT = "f7f7f3d136bd5d844fe800a4535bb355b806ee4b9e03d07edb7e460c7b29acf8"
SNAPSHOT = "d6b2d9b4705907b34dfc488d060f2403445e38d2fcff9788c42d105ce243d24f"
TABLE_KEYS = {
    "jobs": ("task", "arm"),
    "plan_requests": ("id",),
    "plan_account": ("binding",),
    "resources": ("identity",),
}
SCHEMA = {
    "plan_requests": "CREATE TABLE plan_requests(id TEXT PRIMARY KEY, task TEXT, arm TEXT, role TEXT, model TEXT, state TEXT, at REAL, usage TEXT, seconds INTEGER)",
    "plan_account": "CREATE TABLE plan_account(binding TEXT PRIMARY KEY)",
}


def read_history(project):
    path = project / "artifacts/20261020-siwc-runtime-ready/history.json"
    value = json.loads(path.read_text())
    if (
        digest(canonical(value)) != SNAPSHOT
        or value["parent_manifest_sha256"] != PARENT
        or set(value["tables"]) != set(TABLE_KEYS)
    ):
        raise StopRun("SIWC_HISTORY_PARENT_INVALID")
    jobs = value["tables"]["jobs"]["rows"]
    if (
        len(jobs) != 2
        or {r[1] for r in jobs} != {"engine-off", "engine-on"}
        or any(
            r[0] != "os-filesystem/malicious/indirect/consent-violations/1" or r[2] != "UNKNOWN"
            for r in jobs
        )
    ):
        raise StopRun("SIWC_HISTORY_UNKNOWN_REQUIRED")
    return value


def seed_history(db, value):
    baseline = {}
    for table, keys in TABLE_KEYS.items():
        if table in SCHEMA:
            db.execute(SCHEMA[table])
        entry = value["tables"][table]
        columns = [r[1] for r in db.execute("PRAGMA table_info(" + table + ")")]
        if columns != entry["columns"]:
            raise StopRun("SIWC_HISTORY_COLUMNS_CHANGED")
        rows = entry["rows"]
        db.executemany(
            "INSERT INTO " + table + " VALUES(" + ",".join("?" for _ in columns) + ")", rows
        )
        baseline[table] = [
            {
                "key": [row[columns.index(k)] for k in keys],
                "sha256": digest(
                    canonical(
                        db.execute(
                            "SELECT * FROM "
                            + table
                            + " WHERE "
                            + " AND ".join(k + "=?" for k in keys),
                            [row[columns.index(k)] for k in keys],
                        ).fetchone()
                    )
                ),
            }
            for row in rows
        ]
    return baseline


def verify_history(db, manifest):
    history = manifest.get("chatgpt_plan", {}).get("transport_history")
    if history is None:
        return
    try:
        if (
            history["parent_manifest_sha256"] != PARENT
            or history["snapshot_sha256"] != SNAPSHOT
            or set(history["rows"]) != set(TABLE_KEYS)
        ):
            raise StopRun("SIWC_HISTORY_BINDING_CHANGED")
        for table, keys in TABLE_KEYS.items():
            for entry in history["rows"][table]:
                row = db.execute(
                    "SELECT * FROM " + table + " WHERE " + " AND ".join(k + "=?" for k in keys),
                    entry["key"],
                ).fetchone()
                if row is None or digest(canonical(row)) != entry["sha256"]:
                    raise StopRun("SIWC_HISTORY_RECORD_CHANGED")
    except (sqlite3.Error, KeyError, TypeError) as error:
        raise StopRun("SIWC_HISTORY_RECORD_INVALID") from error


def verify_history_file(root, manifest):
    value = json.loads((Path(root) / "transport-history.json").read_text())
    if digest(canonical(value)) != manifest["chatgpt_plan"]["transport_history"]["snapshot_sha256"]:
        raise StopRun("SIWC_HISTORY_SNAPSHOT_CHANGED")
