"""Manifest-bound no-refund provider reservations and immutable task claims."""

import copy
import sqlite3
import time
from contextlib import contextmanager

from app.common import canonical, digest


class Exhausted(ValueError):
    pass


class Ledger:
    def __init__(self, path, manifest_hash, limits):
        self.path, self.manifest_hash, self.limits = str(path), manifest_hash, copy.deepcopy(limits)
        binding = canonical({"manifest": manifest_hash, "limits": limits})
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS binding(id INTEGER PRIMARY KEY,binding TEXT)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,provider TEXT,arm TEXT,state TEXT,input_reserved INTEGER,output_reserved INTEGER,usage TEXT,at REAL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks(task TEXT,arm TEXT,state TEXT,PRIMARY KEY(task,arm))"
            )
            old = db.execute("SELECT binding FROM binding WHERE id=1").fetchone()
            if old and old[0] != binding:
                raise ValueError("LEDGER_MANIFEST_BINDING_CHANGED")
            if not old:
                db.execute("INSERT INTO binding VALUES(1,?)", (binding,))

    @contextmanager
    def db(self):
        with sqlite3.connect(self.path, timeout=3) as db:
            db.execute("BEGIN IMMEDIATE")
            yield db

    def reserve(self, request_id, provider, arm, input_tokens, output_tokens):
        if arm not in ("engine-off", "engine-on") or provider not in self.limits:
            raise Exhausted("PROVIDER_OR_ARM_NOT_ENROLLED")
        if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
            raise ValueError("INVALID_RESERVATION")
        limit = self.limits[provider]
        with self.db() as db:
            if db.execute("SELECT binding FROM binding WHERE id=1").fetchone()[0] != canonical(
                {"manifest": self.manifest_hash, "limits": self.limits}
            ):
                raise Exhausted("LEDGER_LIMITS_CHANGED")
            arm_limit = limit.get("per_arm", {}).get(arm)
            if limit.get("per_arm") and arm_limit is None:
                raise Exhausted("ARM_BUDGET_NOT_ENROLLED")
            if arm_limit:
                ac, ai, ao = db.execute(
                    "SELECT count(*),coalesce(sum(input_reserved),0),coalesce(sum(output_reserved),0) FROM attempts WHERE provider=? AND arm=?",
                    (provider, arm),
                ).fetchone()
                if (
                    ac >= arm_limit["requests"]
                    or ai + input_tokens > arm_limit["input_tokens"]
                    or ao + output_tokens > arm_limit["output_tokens"]
                ):
                    raise Exhausted("ARM_BUDGET_EXHAUSTED")
            count, inputs, outputs = db.execute(
                "SELECT count(*),coalesce(sum(input_reserved),0),coalesce(sum(output_reserved),0) FROM attempts WHERE provider=?",
                (provider,),
            ).fetchone()
            if (
                count >= limit["requests"]
                or inputs + input_tokens > limit["input_tokens"]
                or outputs + output_tokens > limit["output_tokens"]
            ):
                raise Exhausted("PROVIDER_BUDGET_EXHAUSTED")
            try:
                db.execute(
                    "INSERT INTO attempts VALUES(?,?,?,?,?,?,NULL,?)",
                    (
                        request_id,
                        provider,
                        arm,
                        "STARTED",
                        input_tokens,
                        output_tokens,
                        time.time(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise Exhausted("REQUEST_ALREADY_RESERVED_NO_RETRY") from error

    def record(self, request_id, usage=None):
        complete = isinstance(usage, dict) and all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
        )
        with self.db() as db:
            row = db.execute(
                "SELECT state,input_reserved,output_reserved FROM attempts WHERE id=?",
                (request_id,),
            ).fetchone()
            if not row or row[0] != "STARTED":
                raise ValueError("RESERVATION_STATE_CHANGED")
            if complete and (usage["input_tokens"] > row[1] or usage["output_tokens"] > row[2]):
                complete = False
            db.execute(
                "UPDATE attempts SET state=?,usage=? WHERE id=?",
                (
                    "COMPLETED" if complete else "UNKNOWN",
                    canonical(usage) if complete else None,
                    request_id,
                ),
            )
        return complete

    def claim_task(self, task, arm):
        if arm not in ("engine-off", "engine-on"):
            raise ValueError("TWO_ARMS_ONLY")
        with self.db() as db:
            try:
                db.execute(
                    "INSERT INTO tasks VALUES(?,?,?)",
                    (digest(task), arm, "CLAIMED_NO_AUTOMATIC_RETRY"),
                )
            except sqlite3.IntegrityError as error:
                raise Exhausted("TASK_CLAIMED_RECONCILE_NOT_REPLAY") from error

    def recover(self):
        with self.db() as db:
            db.execute("UPDATE attempts SET state='UNKNOWN' WHERE state='STARTED'")
            db.execute(
                "UPDATE tasks SET state='UNKNOWN_RECONCILIATION_REQUIRED' WHERE state='CLAIMED_NO_AUTOMATIC_RETRY'"
            )

    def finish_task(self, task, arm, *, completed):
        if type(completed) is not bool or arm not in ("engine-off", "engine-on"):
            raise ValueError("INVALID_TASK_COMPLETION")
        with self.db() as db:
            changed = db.execute(
                "UPDATE tasks SET state=? WHERE task=? AND arm=? AND state='CLAIMED_NO_AUTOMATIC_RETRY'",
                (
                    "COMPLETED" if completed else "UNKNOWN_RECONCILIATION_REQUIRED",
                    digest(task),
                    arm,
                ),
            ).rowcount
            if changed != 1:
                raise Exhausted("TASK_FINAL_OR_UNCLAIMED_NO_REPLAY")
