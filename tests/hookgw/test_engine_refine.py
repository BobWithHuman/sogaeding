"""Bounded inspections and current candidate roles; no actor/Jev requests."""

import asyncio
import copy
import json
import subprocess
import sys

import pytest
from test_functional_routing import decision, metadata, setup

from app.benchmark.denial import policy_denial, policy_feedback
from app.benchmark.hook import Stopped
from app.benchmark.task_scope import PROBE_SCRIPT
from app.benchmark.tree_scope import TREE_PROBE_SCRIPT
from app.transparent.engine import Rejected


@pytest.mark.parametrize("kind", ["nodes", "depth", "output"])
def test_fixed_probe_limits_return_no_partial_coverage(tmp_path, kind):
    if kind == "nodes":
        for index in range(65):
            (tmp_path / str(index)).touch()
        depth = 32
        expected = "TREE_NODE_LIMIT"
    elif kind == "depth":
        (tmp_path / "child").mkdir()
        (tmp_path / "child/leaf").touch()
        depth = 1
        expected = "SEARCH_DEPTH_LIMIT_INCOMPLETE"
    else:
        # At most 64 entries, but full names exceed the existing output bound.
        for index in range(64):
            (tmp_path / (str(index) + "a" * 245)).touch()
        depth = 32
        expected = "TREE_OUTPUT_LIMIT"
    result = subprocess.run(
        [sys.executable, "-I", "-c", PROBE_SCRIPT + TREE_PROBE_SCRIPT
         + "\nprint(json.dumps(tree))",
         json.dumps({"paths": [str(tmp_path)], "tree_depth": depth, "complete_search": True})],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "version": "tree-coverage-1", "complete": False, "inspection_limit": expected,
    }


def search():
    return {"route": "mcp", "tool": "OS-filesystem::search_files",
            "args": {"search_path": "/data", "pattern": "app.conf"}}


@pytest.mark.parametrize("limit", ["TREE_NODE_LIMIT", "TREE_OUTPUT_LIMIT", "SEARCH_DEPTH_LIMIT_INCOMPLETE"])
def test_limit_denies_exact_call_then_safe_alternative_completes(tmp_path, limit):
    engine, policy, wires, _ = setup(tmp_path, candidate=search())

    def probe(candidate):
        value = metadata(candidate)
        if candidate["tool"].endswith("::search_files"):
            value["tree"] = {"version": "tree-coverage-1", "complete": False, "inspection_limit": limit}
        return value

    policy.scope_probe = probe
    refused = decision(engine)
    assert refused["decision"] == "DENY" and refused["reasons"] == ["RESOURCE_INSPECTION_LIMIT"]
    assert refused["diagnostic"] is None and not wires
    with pytest.raises(Rejected):
        engine.forward("m", "call")
    assert policy_denial({"stage": "PRE", "decision": "DENY", "state": "DENIED",
                          "upstream_invoked": False, "reasons": refused["reasons"]},
                         Stopped("DTAP_PRE_STOPPED"))
    feedback = policy_feedback(refused["reasons"], [("OS-filesystem", "get_file_info")])
    assert "narrower" in feedback["inspection_guidance"]
    with engine.db() as db:
        assert db.execute("SELECT 1 FROM analysis_stops").fetchone() is None
    engine.register("m", "s", "t", "safe", "OS-filesystem::get_file_info",
                    {"filepath": "/data/report.txt"}, "mcp")
    assert asyncio.run(engine.authorize("m", "safe"))["decision"] == "ALLOW"
    engine.forward("m", "safe")
    engine.transport_observed("m", "s", "OS-filesystem::get_file_info",
                              {"filepath": "/data/report.txt"},
                              {"isError": False, "content": [{"type": "text", "text": "File size: 8"}]})
    observed = engine.observe("m", "safe", "OS-filesystem::get_file_info",
                             {"filepath": "/data/report.txt"},
                             {"isError": False, "content": [{"type": "text", "text": "File size: 8"}]})
    assert observed["state"] == "OBSERVED"
    with pytest.raises(Rejected):
        engine.forward("m", "safe")


@pytest.mark.parametrize("tamper", ["unknown", "partial", "complete"])
def test_malformed_limit_remains_analysis_failure(tmp_path, tamper):
    engine, policy, wires, _ = setup(tmp_path, candidate=search())
    value = metadata(search())
    value["tree"] = {"version": "tree-coverage-1", "complete": False,
                     "inspection_limit": "TREE_NODE_LIMIT"}
    if tamper == "unknown":
        value["tree"]["inspection_limit"] = "TREE_CHANGED"
    elif tamper == "partial":
        value["tree"]["nodes"] = []
    else:
        value["tree"]["complete"] = True
    policy.scope_probe = lambda _: copy.deepcopy(value)
    result = decision(engine)
    assert result["decision"] == "DENY" and result["diagnostic"] is not None and not wires
    with pytest.raises(Rejected):
        engine.forward("m", "call")


def test_runtime_current_context_and_new_question_version(tmp_path):
    engine, policy, wires, _ = setup(tmp_path, candidate=search())
    assert decision(engine)["decision"] == "ALLOW"
    assert policy.contract == "dtap-demo-behavior-4"
    assert policy.prompt_version == "dtap-demo-questions-4"
    assert wires[0]["state"]["current_actual_user_request"] == "List files in /data and inspect their metadata."
    assert wires[0]["state"]["previous_actual_user_turns"] == []
    assert wires[1]["state"]["current_candidate"] == search()
    assert "withheld in A" in wires[0]["questions"]["task_relation"]["instructions"]
    assert "false completion" in wires[1]["questions"]["behavior"]["instructions"]


