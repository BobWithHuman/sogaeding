"""Scope2 fixed-three preparation and stop-before-next-task contracts."""

import json
import sqlite3
from pathlib import Path

from app.benchmark.runtime_budget import RuntimeBudget
from app.benchmark.runtime_demo import ro_ledger
from app.benchmark.runtime_utility_acceptance import (
    acceptance_check,
)

ROOT = Path("/workspace")
PREPARED = ROOT / "artifacts/20261018-dtap-os100/user-normal-utility-acceptance"
PARENT = ROOT / "artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup"


def config():
    return json.loads((PREPARED / "plan.json").read_text())


def fresh_budget(tmp_path):
    plan = config()
    with ro_ledger(PREPARED) as source, sqlite3.connect(tmp_path / "budget.db") as dest:
        source.backup(dest)
    return RuntimeBudget(tmp_path / "budget.db", plan["manifest"]), plan








def result():
    return {
        "actor_initialized": True,
        "actor_completed": True,
        "judge": {"error": None, "task_success": True, "attack_success": None},
        "events": [
            {
                "stage": "PRE",
                "call": "denied",
                "decision": "DENY",
                "state": "DENIED",
                "reasons": ["UNSUPPORTED_SCOPE_OPERATION"],
                "upstream_invoked": False,
            },
            {"stage": "PRE", "call": "ok", "decision": "ALLOW"},
            {"stage": "POST", "call": "ok", "state": "OBSERVED"},
        ],
        "pdp_approval_count": 0,
        "lifecycle_close_observed": True,
    }








def test_success_gate_requires_judge_post_and_zero_approval():
    r = result()
    assert acceptance_check(r, "COMPLETED")["succeeded"]
    r["pdp_approval_count"] = None
    assert not acceptance_check(r, "COMPLETED")["succeeded"]






