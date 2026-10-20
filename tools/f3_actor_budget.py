"""Record an actor episode before launch; two episodes total, no refund."""

import json
import sqlite3
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/runtime-f3-01/actor-budget.sqlite3"
with sqlite3.connect(target, timeout=1) as db:
    db.execute("CREATE TABLE IF NOT EXISTS episodes (id TEXT PRIMARY KEY, started REAL NOT NULL)")
    db.execute("BEGIN IMMEDIATE")
    if db.execute("SELECT count(*) FROM episodes").fetchone()[0] >= 2:
        raise SystemExit("Actor budget exhausted; no automatic retry.")
    db.execute("INSERT INTO episodes VALUES (?,?)", (sys.argv[1], time.time()))
print(json.dumps({"episode_id": sys.argv[1], "attempt_recorded": True, "episode_limit": 2}))
