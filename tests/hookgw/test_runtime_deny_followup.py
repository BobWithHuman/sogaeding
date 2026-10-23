"""Trusted policy stop vs infrastructure; no actor/provider/model requests."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dtap_runtime import manifest

from app.benchmark.denial import POLICY_DENIAL_REASONS, policy_denial
from app.benchmark.hook import Stopped
from app.benchmark.runtime_budget import RuntimeBudget

ROOT = Path("/workspace")
PARENT = ROOT / "artifacts/20261018-dtap-os100/user-engine-demo-02-scope-v2"


def actor(dispatcher, records):
    return SimpleNamespace(
        dispatcher=dispatcher,
        records=records,
        events=[],
        names={
            "shell": ("OS-filesystem", "execute_command"),
            "read": ("OS-filesystem", "check_file_exists"),
        },
        trajectory=SimpleNamespace(
            append_agent_step=lambda *a, **k: None, append_tool_return=lambda *a, **k: None
        ),
        record=records.append,
    )




@pytest.mark.parametrize("reason", sorted(POLICY_DENIAL_REASONS))
def test_reviewed_exact_reasons_only(reason):
    pre = {
        "stage": "PRE",
        "decision": "DENY",
        "state": "DENIED",
        "upstream_invoked": False,
        "reasons": [reason],
    }
    assert policy_denial(pre, Stopped("DTAP_PRE_STOPPED"))
    assert not policy_denial(pre, Stopped("EXACT_ONE_SHOT_BINDING"))


@pytest.mark.parametrize(
    "change",
    [
        {"reasons": ["TASK_SCOPE_BINDING_INVALID"]},
        {"reasons": ["ANALYSIS_FAILURE"]},
        {"reasons": ["OUTSIDE_TASK_SCOPE", "ReadTimeout"]},
        {"reasons": []},
        {"reasons": "OUTSIDE_TASK_SCOPE"},
        {"state": "UNKNOWN"},
        {"upstream_invoked": None},
        {"stage": "POST"},
        {"decision": "ALLOW"},
    ],
)
def test_fault_unknown_and_malformed_are_not_policy_denials(change):
    pre = {
        "stage": "PRE",
        "decision": "DENY",
        "state": "DENIED",
        "upstream_invoked": False,
        "reasons": ["OUTSIDE_TASK_SCOPE"],
    }
    pre.update(change)
    assert not policy_denial(pre, Stopped("DTAP_PRE_STOPPED"))




def test_parent_status_progress_separates_off_and_fresh_on(tmp_path):
    m = manifest()
    m["task_keys"] = [str(i) for i in range(15)]
    m["demo"] = {}
    b = RuntimeBudget(tmp_path / "status.db", m)
    with b.db() as db:
        for i in range(12):
            db.execute(
                "INSERT INTO jobs(task,arm,state) VALUES(?,'engine-off','COMPLETED')", (str(i),)
            )
        db.execute("INSERT INTO jobs(task,arm,state) VALUES('0','engine-on','UNKNOWN')")
    m["demo"] = {"status_only": True}
    b.manifest = m
    p = b.status()["demo_progress"]
    assert p["reused_off_completed"] == 12 and p["new_on_completed"] == 0
    assert p["new_on_attempted"] == 1 and p["new_on_not_started"] == 14
    assert p["new_on_completion_percent"] == 0 and b.status()["completion_percent"] == 40




