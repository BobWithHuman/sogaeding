"""Atomic provider holds; verified usage settlement is explicitly versioned."""

import copy
import json
import sqlite3
import time
from contextlib import contextmanager
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from uuid import uuid4

from app.common import canonical, digest

ARMS = ("engine-off", "engine-on")
PROVIDERS = ("actor", "jev", "environment", "judge")


class StopRun(RuntimeError):
    pass


class BudgetStop(StopRun):
    """A request was rejected before dispatch by an enrolled budget cap."""


SETTLED_COST = "verified-usage-plus-unresolved-holds-v1"
BASELINE_KEYS = {
    "reservations": ("id",),
    "jobs": ("task", "arm"),
    "stops": ("id",),
    "resources": ("identity",),
    "resumes": ("id",),
}
OPTIONAL_BASELINE_KEYS = {"settlements": ("reservation",)}


def parent_baseline(db):
    baseline = {}
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, keys in {**BASELINE_KEYS, **OPTIONAL_BASELINE_KEYS}.items():
        if table not in tables:
            continue
        columns = [row[1] for row in db.execute("PRAGMA table_info(" + table + ")")]
        baseline[table] = [
            {"key": [row[columns.index(key)] for key in keys], "sha256": digest(canonical(row))}
            for row in db.execute("SELECT * FROM " + table + " ORDER BY 1,2")
        ]
    return baseline


def verify_continuation_ledger(path, manifest):
    binding = manifest.get("continuation")
    if not binding:
        return
    try:
        with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            expected = (binding["parent_ledger_sha256"], digest(canonical(manifest)))
            if db.execute("SELECT parent_hash,manifest_hash FROM lineage").fetchall() != [expected]:
                raise StopRun("CONTINUATION_LEDGER_LINEAGE_CHANGED")
            if db.execute("SELECT hash FROM binding").fetchone() != (expected[1],):
                raise StopRun("CONTINUATION_LEDGER_BINDING_CHANGED")
            if (
                not set(BASELINE_KEYS)
                <= set(binding["parent_rows"])
                <= set(BASELINE_KEYS) | set(OPTIONAL_BASELINE_KEYS)
            ):
                raise StopRun("CONTINUATION_BASELINE_REQUIRED")
            for table in binding["parent_rows"]:
                keys = {**BASELINE_KEYS, **OPTIONAL_BASELINE_KEYS}[table]
                for entry in binding["parent_rows"][table]:
                    row = db.execute(
                        "SELECT * FROM "
                        + table
                        + " WHERE "
                        + " AND ".join(key + "=?" for key in keys),
                        entry["key"],
                    ).fetchone()
                    if row is None or digest(canonical(row)) != entry["sha256"]:
                        raise StopRun("CONTINUATION_PARENT_RECORD_CHANGED")
    except (sqlite3.Error, KeyError, TypeError) as error:
        raise StopRun("CONTINUATION_LEDGER_MISSING_OR_INVALID") from error


def is_budget_stop(code):
    return isinstance(code, str) and code.startswith("CAP_EXHAUSTED_")


def charge(rate, inputs, outputs):
    # Rates are USD per million tokens; result is integer micro-USD.
    return int(
        (
            Decimal(str(rate["input"])) * inputs + Decimal(str(rate["output"])) * outputs
        ).to_integral_value(rounding=ROUND_CEILING)
    )


class RuntimeBudget:
    def __init__(self, path, manifest):
        self.path = str(path)
        self.manifest = copy.deepcopy(manifest)
        self.binding = digest(canonical(manifest))
        verify_continuation_ledger(path, manifest)
        if manifest["arms"] != (
            ["engine-on"] if manifest.get("utility_acceptance") else list(ARMS)
        ):
            raise ValueError("EXACT_TWO_ARMS_REQUIRED")
        with self.db() as db:
            schema = """CREATE TABLE IF NOT EXISTS binding(id INTEGER PRIMARY KEY CHECK(id=1),hash TEXT);
                CREATE TABLE IF NOT EXISTS stops(id INTEGER PRIMARY KEY,code TEXT,at REAL);
                CREATE TABLE IF NOT EXISTS jobs(task TEXT,arm TEXT,state TEXT,owner TEXT,started REAL,finished REAL,result TEXT,PRIMARY KEY(task,arm));
                CREATE TABLE IF NOT EXISTS reservations(id TEXT PRIMARY KEY,task TEXT,arm TEXT,provider TEXT,model TEXT,state TEXT,inputs INTEGER,outputs INTEGER,seconds INTEGER,micro_usd INTEGER,usage TEXT,at REAL);
                CREATE TABLE IF NOT EXISTS owners(arm TEXT PRIMARY KEY,owner TEXT,heartbeat REAL);
                CREATE TABLE IF NOT EXISTS resources(identity TEXT PRIMARY KEY,bytes INTEGER);
                CREATE TABLE IF NOT EXISTS settlements(reservation TEXT PRIMARY KEY REFERENCES reservations(id),micro_usd INTEGER NOT NULL CHECK(micro_usd>=0));
                CREATE TABLE IF NOT EXISTS budget_rejections(task TEXT,arm TEXT,provider TEXT,code TEXT,at REAL);
                CREATE TABLE IF NOT EXISTS resumes(id INTEGER PRIMARY KEY,before_stop INTEGER,at REAL);"""
            for statement in schema.split(";"):
                if statement.strip():
                    db.execute(statement)
            old = db.execute("SELECT hash FROM binding").fetchone()
            if old and old[0] != self.binding:
                raise StopRun("EXPERIMENT_MANIFEST_CHANGED")
            if not old:
                db.execute("INSERT INTO binding VALUES(1,?)", (self.binding,))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _active(self, db):
        if self.manifest.get("chatgpt_plan"):
            from app.benchmark.login_history import verify_history
            from app.benchmark.runtime_login import verify_parent

            verify_parent(self.manifest)
            verify_history(db, self.manifest)
            if self.manifest["chatgpt_plan"].get("paired_acceptance"):
                from app.benchmark.runtime_login_pair import verify_rows

                verify_rows(db, self.manifest)
            if self.manifest.get("functional_routing"):
                from app.benchmark.runtime_functional import verify_rows

                verify_rows(db, self.manifest)
        if self.manifest.get("demo"):
            from app.benchmark.runtime_demo import verify_parent_ledger

            verify_parent_ledger(self.manifest)
        if digest(canonical(self.manifest)) != self.binding:
            raise StopRun("RUNTIME_LIMITS_MUTATED")
        stopped = db.execute(
            "SELECT code FROM stops WHERE id>coalesce((SELECT max(before_stop) FROM resumes),0) ORDER BY id LIMIT 1"
        ).fetchone()
        if stopped:
            raise (BudgetStop if is_budget_stop(stopped[0]) else StopRun)(stopped[0])

    def stop(self, code):
        if not isinstance(code, str) or len(code) > 100:
            raise ValueError("STOP_CODE")
        with self.db() as db:
            db.execute("INSERT INTO stops(code,at) VALUES(?,?)", (code, time.time()))

    def resume_operator_stop(self):
        if self.manifest.get("chatgpt_plan"):
            raise StopRun("CHATGPT_PLAN_ONE_SHOT_NO_RESUME")
        if self.manifest.get("utility_acceptance"):
            raise StopRun("UTILITY_ONE_SHOT_NO_RESUME")
        with self.db() as db:
            stops = db.execute(
                "SELECT id,code FROM stops WHERE id>coalesce((SELECT max(before_stop) FROM resumes),0)"
            ).fetchall()
            if not stops:
                return
            if (
                any(code != "OPERATOR_STOP" for _, code in stops)
                or db.execute("SELECT 1 FROM owners").fetchone()
            ):
                raise StopRun("NONRESUMABLE_STOP_OR_ACTIVE_OWNER")
            db.execute(
                "INSERT INTO resumes(before_stop,at) VALUES(?,?)",
                (max(i for i, _ in stops), time.time()),
            )

    def acquire(self, arm):
        if self.manifest.get("demo") and arm != "engine-on":
            raise StopRun("DEMO_FRESH_ON_ONLY")
        if arm not in self.manifest["arms"]:
            raise StopRun("ARM_NOT_ALLOWED")
        owner = str(uuid4())
        with self.db() as db:
            self._active(db)
            if db.execute("SELECT 1 FROM owners WHERE arm=?", (arm,)).fetchone():
                raise StopRun("ARM_ALREADY_CLAIMED_EXPLICIT_RECONCILIATION_REQUIRED")
            db.execute("INSERT INTO owners VALUES(?,?,?)", (arm, owner, time.time()))
        return owner

    def heartbeat(self, arm, owner):
        with self.db() as db:
            self._active(db)
            if (
                db.execute(
                    "UPDATE owners SET heartbeat=? WHERE arm=? AND owner=?",
                    (time.time(), arm, owner),
                ).rowcount
                != 1
            ):
                raise StopRun("ARM_OWNER_CHANGED")

    def release(self, arm, owner):
        with self.db() as db:
            db.execute("DELETE FROM owners WHERE arm=? AND owner=?", (arm, owner))

    def claim(self, task, arm, owner):
        if task not in self.manifest["task_keys"] or arm not in self.manifest["arms"]:
            raise StopRun("TASK_OR_ARM_NOT_ENROLLED")
        with self.db() as db:
            self._active(db)
            if not db.execute(
                "SELECT 1 FROM owners WHERE arm=? AND owner=?", (arm, owner)
            ).fetchone():
                raise StopRun("OWNER_REQUIRED")
            old = db.execute(
                "SELECT state FROM jobs WHERE task=? AND arm=?", (task, arm)
            ).fetchone()
            if old:
                return old[0]  # terminal/UNKNOWN never dispatch again
            db.execute(
                "INSERT INTO jobs VALUES(?,?,?,?,?,NULL,NULL)",
                (task, arm, "CLAIMED", owner, time.time()),
            )
        return "NEW"

    def finish(self, task, arm, owner, state, result):
        if state not in (
            "COMPLETED",
            "INCOMPLETE",
            "UNKNOWN",
            "UNSUPPORTED",
            "ERROR",
            "CONFIRM_UNAPPROVED",
            "BUDGET_STOPPED",
            "CONTEXT_LIMIT",
            "SETUP_FAILED",
        ):
            raise ValueError("INVALID_FINAL_STATE")
        with self.db() as db:
            if (
                db.execute(
                    "UPDATE jobs SET state=?,finished=?,result=? WHERE task=? AND arm=? AND owner=? AND state='CLAIMED'",
                    (state, time.time(), canonical(result), task, arm, owner),
                ).rowcount
                != 1
            ):
                raise StopRun("TASK_FINAL_OR_OWNER_CHANGED")

    def reserve(self, task, arm, provider, model, inputs, outputs, seconds):
        if (
            arm not in self.manifest["arms"]
            or provider not in PROVIDERS
            or task not in self.manifest["task_keys"]
        ):
            raise StopRun("UNBOUND_PROVIDER_REQUEST")
        if any(type(n) is not int or n < 0 for n in (inputs, outputs, seconds)):
            raise StopRun("INVALID_RESERVATION")
        profile = self.manifest["providers"][provider]
        if model not in profile["models"]:
            raise StopRun("MODEL_NOT_ENROLLED")
        if (
            inputs > profile["per_request"]["input_tokens"]
            or outputs > profile["per_request"]["output_tokens"]
            or seconds > profile["per_request"]["seconds"]
        ):
            raise StopRun("PER_REQUEST_CAP")
        price = charge(profile["rates"][model], inputs, outputs)
        rid = str(uuid4())
        with self.db() as db:
            self._active(db)
            if not db.execute(
                "SELECT 1 FROM jobs WHERE task=? AND arm=? AND state='CLAIMED'", (task, arm)
            ).fetchone():
                raise StopRun("ACTIVE_TASK_REQUIRED")
            for scope, where, args, limit in [
                ("total", "1=1", (), self.manifest["limits"]["total"]),
                ("arm", "arm=?", (arm,), self.manifest["limits"]["arms"][arm]),
                ("provider", "provider=?", (provider,), profile["total"]),
                ("provider_arm", "provider=? AND arm=?", (provider, arm), profile["arms"][arm]),
                (
                    "task_provider",
                    "provider=? AND arm=? AND task=?",
                    (provider, arm, task),
                    profile["per_task"],
                ),
            ]:
                cost = (
                    "coalesce(s.micro_usd,r.micro_usd)"
                    if self.manifest.get("cost_accounting") == SETTLED_COST
                    else "r.micro_usd"
                )
                counts = db.execute(
                    "SELECT count(*),coalesce(sum(inputs),0),coalesce(sum(outputs),0),"
                    "coalesce(sum(seconds),0),coalesce(sum(" + cost + "),0) "
                    "FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id WHERE "
                    + where,
                    args,
                ).fetchone()
                added = (1, inputs, outputs, seconds, price)
                if any(
                    current + new > limit[field]
                    for current, new, field in zip(
                        counts,
                        added,
                        ("requests", "input_tokens", "output_tokens", "seconds", "micro_usd"),
                        strict=True,
                    )
                ):
                    raise BudgetStop("CAP_EXHAUSTED_" + scope.upper())
            db.execute(
                "INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?,NULL,?)",
                (
                    rid,
                    task,
                    arm,
                    provider,
                    model,
                    "STARTED",
                    inputs,
                    outputs,
                    seconds,
                    price,
                    time.time(),
                ),
            )
        return rid

    def record(self, rid, usage, *, resolved_model=None):
        with self.db() as db:
            row = db.execute(
                "SELECT state,inputs,outputs,model,provider FROM reservations WHERE id=?", (rid,)
            ).fetchone()
            if not row or row[0] != "STARTED":
                raise StopRun("REQUEST_FINAL_NO_REPLAY")
            valid = isinstance(usage, dict) and all(
                type(usage.get(k)) is int and 0 <= usage[k] <= cap
                for k, cap in [("input_tokens", row[1]), ("output_tokens", row[2])]
            )
            if resolved_model is not None and (
                not isinstance(resolved_model, str)
                or resolved_model != row[3]
                and not resolved_model.startswith(row[3] + "-")
            ):
                valid = False
            if self.manifest.get("cost_accounting") == SETTLED_COST and resolved_model not in (
                self.manifest["providers"][row[4]].get("billing_model_aliases", {}).get(row[3], [])
            ):
                valid = False
            body = {"tokens": usage, "resolved_model": resolved_model} if valid else None
            db.execute(
                "UPDATE reservations SET state=?,usage=? WHERE id=?",
                ("COMPLETED" if valid else "UNKNOWN", canonical(body) if body else None, rid),
            )
            if valid and self.manifest.get("cost_accounting") == SETTLED_COST:
                db.execute(
                    "INSERT INTO settlements VALUES(?,?)",
                    (
                        rid,
                        charge(
                            self.manifest["providers"][row[4]]["rates"][row[3]],
                            usage["input_tokens"],
                            usage["output_tokens"],
                        ),
                    ),
                )
        return valid

    def note_budget_rejection(self, task, arm, provider, code):
        if not is_budget_stop(code):
            raise ValueError("BUDGET_CODE_REQUIRED")
        with self.db() as db:
            db.execute(
                "INSERT INTO budget_rejections VALUES(?,?,?,?,?)",
                (task, arm, provider, code, time.time()),
            )

    def reconcile_interrupted(self, arm):
        # Explicit operator operation, before a new owner starts. Never refunds
        # or requeues ambiguous effects/charges, regardless of elapsed time.
        with self.db() as db:
            db.execute(
                "UPDATE jobs SET state='UNKNOWN',finished=? WHERE arm=? AND state='CLAIMED'",
                (time.time(), arm),
            )
            db.execute(
                "UPDATE reservations SET state='UNKNOWN' WHERE arm=? AND state='STARTED'", (arm,)
            )
            db.execute("DELETE FROM owners WHERE arm=?", (arm,))

    def reserve_storage(self, identity, size, *, cleanup=None):
        if (
            type(size) is not int
            or size < 0
            or size > self.manifest.get("snapshot_per_image_bytes", 1073741824)
        ):
            raise StopRun("SNAPSHOT_IMAGE_CAP")
        with self.db() as db:
            if cleanup is None:
                self._active(db)
            elif not db.execute(
                "SELECT 1 FROM jobs WHERE task=? AND arm=? AND owner=? AND state='CLAIMED'",
                (cleanup["task"], cleanup["arm"], cleanup["owner"]),
            ).fetchone():
                raise StopRun("ACTIVE_OWNED_TASK_REQUIRED")
            if db.execute("SELECT 1 FROM resources WHERE identity=?", (identity,)).fetchone():
                return
            used = db.execute("SELECT coalesce(sum(bytes),0) FROM resources").fetchone()[0]
            if used + size > self.manifest.get("snapshot_total_bytes", 8589934592):
                raise StopRun("SNAPSHOT_TOTAL_CAP")
            db.execute("INSERT INTO resources VALUES(?,?)", (identity, size))

    def status(self):
        with self.db() as db:
            utility_jobs = (
                db.execute("SELECT state,result FROM jobs").fetchall()
                if self.manifest.get("utility_acceptance")
                else []
            )
            jobs = [
                {"arm": a, "state": s, "count": n}
                for a, s, n in db.execute("SELECT arm,state,count(*) FROM jobs GROUP BY arm,state")
            ]
            usage = [
                {
                    "arm": a,
                    "provider": p,
                    "state": s,
                    "requests": n,
                    "input_reserved": i,
                    "output_reserved": o,
                    "seconds_reserved": t,
                    "micro_usd_reserved": c,
                }
                for a, p, s, n, i, o, t, c in db.execute(
                    "SELECT arm,provider,state,count(*),sum(inputs),sum(outputs),sum(seconds),sum(micro_usd) FROM reservations GROUP BY arm,provider,state"
                )
            ]
            actual = db.execute(
                "SELECT arm,provider,model,usage FROM reservations WHERE usage IS NOT NULL"
            ).fetchall()
            stopped = db.execute(
                "SELECT code FROM stops WHERE id>coalesce((SELECT max(before_stop) FROM resumes),0) ORDER BY id LIMIT 1"
            ).fetchone()
            resources = db.execute(
                "SELECT count(*),coalesce(sum(bytes),0) FROM resources"
            ).fetchone()
            settled, held = db.execute(
                "SELECT coalesce(sum(s.micro_usd),0),"
                "coalesce(sum(CASE WHEN s.reservation IS NULL THEN r.micro_usd ELSE 0 END),0) "
                "FROM reservations r LEFT JOIN settlements s ON s.reservation=r.id"
            ).fetchone()
            unresolved = [
                {"task_key": task, "arm": arm, "state": state, "requests": count}
                for task, arm, state, count in db.execute(
                    "SELECT task,arm,state,count(*) FROM reservations WHERE state!='COMPLETED' GROUP BY task,arm,state"
                )
            ]
            rejections = [
                {"task_key": task, "arm": arm, "provider": provider, "code": code}
                for task, arm, provider, code in db.execute(
                    "SELECT DISTINCT task,arm,provider,code FROM budget_rejections"
                )
            ]

        plan_usage = {}
        if self.manifest.get("chatgpt_plan"):
            with self.db() as db:
                exists = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='plan_requests'"
                ).fetchone()
                rows = (
                    db.execute(
                        "SELECT arm,role,model,state,usage,seconds FROM plan_requests"
                    ).fetchall()
                    if exists
                    else []
                )
                account_exists = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='plan_account'"
                ).fetchone()
                account = (
                    db.execute("SELECT binding FROM plan_account").fetchone()
                    if account_exists
                    else None
                )
                http_exists = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='plan_http_observations'"
                ).fetchone()
                http_rows = (
                    db.execute(
                        "SELECT r.arm,h.status,h.media,count(*) FROM plan_http_observations h JOIN plan_requests r ON r.id=h.request_id GROUP BY r.arm,h.status,h.media"
                    ).fetchall()
                    if http_exists
                    else []
                )
            plan_usage = {
                "chatgpt_plan_usage": {
                    "billing": "chatgpt-plan",
                    "api_dollar_charge": "NOT_APPLICABLE",
                    "remaining_plan_quota": "UNKNOWN",
                    "requests": len(rows),
                    "standalone_diagnostic_requests": sum(r[1] == "diagnostic" for r in rows),
                    "account_binding_sha256": account[0] if account else None,
                    "unresolved_plan_requests": sum(r[3] in ("STARTED", "UNKNOWN") for r in rows),
                    "states": {
                        state: sum(r[3] == state for r in rows)
                        for state in ("STARTED", "COMPLETED", "UNKNOWN")
                    },
                    "by_arm": {a: sum(r[0] == a for r in rows) for a in self.manifest["arms"]},
                    "input_tokens": sum(
                        json.loads(r[4]).get("input_tokens", 0) for r in rows if r[4]
                    ),
                    "output_tokens": sum(
                        json.loads(r[4]).get("output_tokens", 0) for r in rows if r[4]
                    ),
                    "http_observations": [
                        {"arm": arm, "http_status": status, "media_type": media, "requests": count}
                        for arm, status, media, count in http_rows
                    ],
                    "reserved_seconds": sum(r[5] for r in rows),
                    "observed_elapsed_ms": sum(
                        json.loads(r[4]).get("elapsed_ms", 0) for r in rows if r[4]
                    ),
                    "model": self.manifest["actor_model"],
                    "reasoning_effort": "low",
                    "hard_output_token_limit": False,
                }
            }
        totals = {}
        for arm, provider, model, encoded in actual:
            entry = json.loads(encoded)
            key = arm + ":" + provider + ":" + str(entry["resolved_model"])
            row = totals.setdefault(
                key,
                {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "nominal_usage_micro_usd": 0,
                },
            )
            row["requests"] += 1
            for name in ("input_tokens", "output_tokens"):
                row[name] += entry["tokens"][name]
            row["nominal_usage_micro_usd"] += charge(
                self.manifest["providers"][provider]["rates"][model],
                entry["tokens"]["input_tokens"],
                entry["tokens"]["output_tokens"],
            )
        done = sum(j["count"] for j in jobs if j["state"] == "COMPLETED")
        finalized = sum(j["count"] for j in jobs if j["state"] != "CLAIMED")
        reserved = sum(row["micro_usd_reserved"] for row in usage)
        utility_progress = {}
        if self.manifest.get("utility_acceptance"):
            results = [json.loads(r or "{}") for _, r in utility_jobs]
            utility_progress = {
                "utility_progress": {
                    "attempted": len(utility_jobs),
                    "completed": done,
                    "task_success": sum(
                        s == "COMPLETED" and r.get("judge", {}).get("task_success") is True
                        for (s, _), r in zip(utility_jobs, results, strict=True)
                    ),
                    "accepted": sum(
                        r.get("utility_acceptance_check", {}).get("succeeded") is True
                        for r in results
                    ),
                    "confirm": sum(s == "CONFIRM_UNAPPROVED" for s, _ in utility_jobs),
                    "unknown": sum(s == "UNKNOWN" for s, _ in utility_jobs),
                    "not_started": len(self.manifest["task_keys"]) - len(utility_jobs),
                    "stage_actual_micro_usd": settled
                    - self.manifest["demo"]["parent_committed_micro_usd"],
                    "stage_committed_micro_usd": settled
                    + held
                    - self.manifest["demo"]["parent_committed_micro_usd"],
                    "stage_hold_micro_usd": held,
                    "cumulative_micro_usd": settled + held,
                }
            }
        demo_progress = {}
        if self.manifest.get("demo"):
            on_attempted = sum(j["count"] for j in jobs if j["arm"] == "engine-on")
            on_completed = sum(
                j["count"] for j in jobs if j["arm"] == "engine-on" and j["state"] == "COMPLETED"
            )
            target = len(self.manifest["task_keys"])
            demo_progress = {
                "demo_progress": {
                    "reused_off_completed": sum(
                        j["count"]
                        for j in jobs
                        if j["arm"] == "engine-off" and j["state"] == "COMPLETED"
                    ),
                    "new_on_target": target,
                    "new_on_attempted": on_attempted,
                    "new_on_completed": on_completed,
                    "new_on_not_started": target - on_attempted,
                    "new_on_completion_percent": 100 * on_completed / target,
                    "legacy_completion_percent_basis": "BOTH_ARMS_INCLUDING_REUSED_OFF",
                    "excluded_parent_unknown": self.manifest.get("runtime_deny_followup", {}).get(
                        "excluded_unknown_task"
                    ),
                }
            }
        return {
            **utility_progress,
            **plan_usage,
            **demo_progress,
            "manifest_sha256": self.binding,
            "total_arm_tasks": len(self.manifest["task_keys"]) * len(self.manifest["arms"]),
            "jobs": jobs,
            "provider_reservations": usage,
            "actual_usage": totals,
            "unresolved_provider_requests": unresolved,
            "budget_rejections": rejections,
            "stop": stopped[0] if stopped else None,
            "unknown_never_refunded": True,
            "completed_arm_tasks": done,
            "completion_percent": 100
            * done
            / (len(self.manifest["task_keys"]) * len(self.manifest["arms"])),
            "finalized_arm_tasks": finalized,
            "not_started_arm_tasks": len(self.manifest["task_keys"]) * len(self.manifest["arms"])
            - sum(j["count"] for j in jobs),
            "cost_accounting": self.manifest.get(
                "cost_accounting", "permanent-maximum-reservations"
            ),
            "settled_micro_usd": settled,
            "unresolved_hold_micro_usd": held,
            "committed_micro_usd": settled + held
            if self.manifest.get("cost_accounting") == SETTLED_COST
            else reserved,
            "remaining_micro_usd": self.manifest["limits"]["total"]["micro_usd"]
            - (
                settled + held if self.manifest.get("cost_accounting") == SETTLED_COST else reserved
            ),
            "snapshots_reserved": {"images": resources[0], "bytes": resources[1]},
        }
