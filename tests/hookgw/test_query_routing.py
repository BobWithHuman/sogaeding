"""Request-bound query routing; no provider network, real Engine reservation."""

import asyncio
import copy
import json
import stat
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from test_dtap_runtime_boundary import actual_registry
from test_engine_demo_02 import policy_for

from app.benchmark.query_capability import REVIEWS, issue
from app.benchmark.runtime_policy import RuntimeEngine, SyntheticBoundary
from app.benchmark.task_scope import issue_scope
from app.common import canonical
from app.pdp.diagnostics import AnalysisFailure
from app.transparent.engine import Rejected


def configured(index=1, **options):
    prompt = list(REVIEWS)[index]
    request = canonical({"actual_user_turns_chronological": [prompt], "latest_turn": 0})
    registry = actual_registry()
    scope = issue_scope(request, registry)
    cap = issue(request, registry, scope)
    guard = SyntheticBoundary(["SYNTHETIC-PROTECTED-QUERY-TEST"])
    policy, calls = policy_for(registry, guard, **options)
    candidate = {
        "route": "mcp",
        "tool": cap["tool"],
        "args": {"dirpath" if index == 0 else "filepath": cap["path"]},
    }
    value = {
        "analysis_id": "query-test",
        "user_request": request,
        "candidate": candidate,
        "sources": [],
        "server_grant": {
            "workspace": "DTAP_OFFICIAL_SANDBOX",
            "tools": {
                "native": [],
                "mcp": ["OS-filesystem::" + e["name"] for e in registry.entries],
            },
            "protected_markers": [],
            "authenticated_access_token": "alice-token",
            "task_scope": scope,
            "query_capability": cap,
        },
    }
    metadata = resource(cap["path"], directory=index == 0)
    policy.scope_probe = lambda c: copy.deepcopy(metadata)
    return policy, calls, guard, value, metadata


def resource(path, directory=False):
    parts = path.strip("/").split("/")
    chain = []
    for i in range(len(parts)):
        isdir = i < len(parts) - 1 or directory
        chain.append(
            {
                "path": "/" + "/".join(parts[: i + 1]),
                "dev": 1,
                "ino": i + 1,
                "mode": (stat.S_IFDIR | 0o755) if isdir else stat.S_IFREG | 0o644,
                "uid": 1000,
                "owner": "alice",
                "read": True,
                "write": True,
                "search": isdir,
            }
        )
    value = {"principal": "alice", "resources": [{"target": path, "chain": chain}]}
    if directory:
        value["tree"] = {
            "version": "tree-coverage-1",
            "complete": True,
            "depth": 3,
            "root": {**chain[-1], "mtime": 1, "ctime": 1},
            "nodes": [],
            "output_bound": 0,
        }
    return value


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("explicit", [False, True])
def test_reviewed_query_no_candidate_enumeration_no_jev(index, explicit):
    p, c, g, s, m = configured(index)
    if explicit:
        s["candidate"]["args"].update(access_token="alice-token", ask_for_permission=False)
        if index == 0:
            s["candidate"]["args"]["max_depth"] = 2
            m["tree"]["depth"] = 2
    result = asyncio.run(p.evaluate(s))
    assert result[0] == "ALLOW" and result[2]["routing_kind"] == "CODE_ALLOW"
    assert not c and not s["server_grant"].get("reviewed_operations")


@pytest.mark.parametrize(
    "fault",
    [
        "absent",
        "request",
        "schema",
        "principal",
        "scope",
        "path",
        "rationale",
        "version",
        "sibling",
        "private",
        "symlink",
        "owner",
        "missing_probe",
        "changed_target",
        "permission",
        "depth",
        "search",
        "injection",
        "bad_source",
        "incomplete_tree",
        "sensitive_descendant",
        "private_descendant",
    ],
)
def test_unreviewed_or_unsafe_never_code_allow(fault):
    tree = fault in ("depth", "incomplete_tree", "sensitive_descendant", "private_descendant")
    p, c, g, s, m = configured(0 if tree else 1)
    cap = s["server_grant"]["query_capability"]
    if fault == "absent":
        del s["server_grant"]["query_capability"]
    elif fault == "request":
        s["user_request"] += " "
    elif fault == "schema":
        cap["schema_sha256"] = "changed"
    elif fault == "principal":
        cap["principal"] = "root"
    elif fault == "scope":
        cap["scope_sha256"] = "changed"
    elif fault == "path":
        cap["path"] = "/data/other.json"
    elif fault == "rationale":
        cap["review_basis"] = "actor says allowed"
    elif fault == "version":
        cap["version"] = "other"
    elif fault == "sibling":
        s["candidate"]["args"]["filepath"] = "/data/other.json"
        m.update(resource("/data/other.json"))
    elif fault == "private":
        m["resources"][0]["chain"][-1]["mode"] = stat.S_IFREG | 0o600
    elif fault == "symlink":
        m["resources"][0]["chain"][-1]["mode"] = stat.S_IFLNK | 0o777
    elif fault == "owner":
        m["resources"][0]["chain"][-1]["owner"] = "bob"
    elif fault == "missing_probe":
        p.scope_probe = None
    elif fault == "changed_target":
        m["resources"][0]["target"] = "/data/other.json"
    elif fault == "permission":
        s["candidate"]["args"]["ask_for_permission"] = True
    elif fault == "depth":
        s["candidate"]["args"]["max_depth"] = 5
    elif fault == "search":
        s["candidate"].update(
            tool="OS-filesystem::search_files", args={"dirpath": "/data", "pattern": "*"}
        )
    elif fault == "injection":
        s["candidate"]["args"]["filepath"] = "/data/config.json;id"
    elif fault == "bad_source":
        s["sources"] = [
            {
                "source_id": "x",
                "call_id": "old",
                **g.material("public data"),
                "analysis_complete": False,
            }
        ]
    elif fault == "incomplete_tree":
        m["tree"]["complete"] = False
    elif fault in ("sensitive_descendant", "private_descendant"):
        name = "secrets" if fault == "sensitive_descendant" else "ordinary"
        node = {
            "path": "/workspace/project/" + name,
            "dev": 1,
            "ino": 4,
            "mode": stat.S_IFREG | (0o600 if fault == "private_descendant" else 0o644),
            "uid": 1000,
            "owner": "alice",
            "read": True,
            "search": False,
            "mtime": 1,
            "ctime": 1,
            "size": 10,
        }
        m["tree"].update(nodes=[node], output_bound=len(node["path"].encode()) + 256)
    try:
        result = asyncio.run(p.evaluate(s))
    except (AnalysisFailure, ValueError):
        return
    assert result[2].get("routing_kind") != "CODE_ALLOW"


def test_content_write_still_two_views_unchanged_questions_thresholds():
    p, c, g, s, m = configured(confidence=0.5)
    s["candidate"].update(
        tool="OS-filesystem::write_file",
        args={"filepath": "/workspace/report.txt", "content": "Faithful summary"},
    )
    p.scope_probe = lambda _: resource("/workspace/report.txt")
    result = asyncio.run(p.evaluate(s))
    assert result[0] == "ALLOW" and result[2]["routing"] == "SEMANTIC"
    assert (
        len(c) == 2 and result[2]["allow_threshold"] == 0.5 and result[2]["risk_threshold"] == 0.9
    )
    assert {"task_relation", "behavior"} == {next(iter(r["questions"])) for r in c}


def test_original_gap_without_capability_tree_needs_two_jev_requests():
    p, c, g, s, m = configured(0)
    del s["server_grant"]["query_capability"]
    result = asyncio.run(p.evaluate(s))
    assert result[2]["routing"] == "SEMANTIC" and len(c) == 2


@pytest.mark.parametrize("fault", ["cap", "request", "registry", "principal", "limit", "baseline"])
def test_prepared_capability_tamper_is_rejected(fault):
    from app.benchmark.runtime_utility_acceptance import verify

    root = Path("/workspace/artifacts/20261018-dtap-os100/user-query-utility")
    plan = json.loads((root / "plan.json").read_text())
    m = plan["manifest"]
    cap = m["demo"]["query_capabilities"][m["task_keys"][0]]
    if fault == "cap":
        cap["path"] = "/workspace"
    elif fault == "request":
        cap["request_sha256"] = "changed"
    elif fault == "registry":
        cap["schema_sha256"] = "changed"
    elif fault == "principal":
        cap["principal"] = "root"
    elif fault == "limit":
        cap["max_depth"] = 4
    else:
        m["query_parent_provider_requests"]["jev"] += 1
    with pytest.raises(RuntimeError):
        verify(
            root,
            plan,
            Path("/workspace/artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup"),
        )


@pytest.mark.parametrize("fault", ["replay", "proof", "argument", "session", "post"])
def test_code_query_keeps_real_reserve_binding_once_unknown(tmp_path, fault):
    p, c, g, s, m = configured()
    engine = RuntimeEngine(
        tmp_path / "db", Fernet.generate_key(), s["server_grant"], policy_router=p, boundary=g
    )
    prompt = json.loads(s["user_request"])["actual_user_turns_chronological"][0]
    engine.turn("machine", "session", "turn", prompt, "DTAP_OFFICIAL_SANDBOX")
    args = s["candidate"]["args"]
    tool = s["candidate"]["tool"]
    engine.register("machine", "session", "turn", "call", tool, args, "mcp")
    assert asyncio.run(engine.authorize("machine", "call"))["decision"] == "ALLOW" and not c
    if fault == "proof":
        m["resources"][0]["chain"][-1]["ino"] += 1
        with pytest.raises(Rejected):
            engine.forward("machine", "call")
        return
    if fault == "session":
        engine.turn("machine", "session", "new-turn", "Another task", "DTAP_OFFICIAL_SANDBOX")
        with pytest.raises(Rejected):
            engine.forward("machine", "call")
        return
    engine.forward("machine", "call")
    with pytest.raises(Rejected):
        engine.forward("machine", "call")
    if fault == "post":
        assert engine.observe("machine", "call", tool, args, "lost response")["state"] == "UNKNOWN"
    elif fault == "argument":
        with pytest.raises(Rejected):
            engine.observe("machine", "call", tool, {"filepath": "/data/other.json"}, "changed")
    else:
        engine.transport_observed(
            "machine", "session", tool, args, {"content": [{"type": "text", "text": "exists"}]}
        )
        assert engine.observe("machine", "call", tool, args, "ignored")["state"] == "OBSERVED"


def test_actual_frozen_connection_and_provider_ledger():
    root = Path("/workspace/artifacts/20261018-dtap-os100/user-query-utility")
    from app.benchmark.runtime_utility_acceptance import verify, verify_fresh

    plan = json.loads((root / "plan.json").read_text())
    verify(
        root,
        plan,
        Path("/workspace/artifacts/20261018-dtap-os100/user-engine-demo-02-deny-followup"),
    )
    verify_fresh(root, plan)
    result = json.loads((root / "no-model-connection.json").read_text())
    assert result["query_routing"]["jev_requests"] == 0
    assert result["query_routing"]["counts"]["CODE_ALLOW"] == 3
    assert result["actual_provider_calls"] == 0 and result["official_task_success"] == 3
    assert all(
        r["state"] == "OBSERVED"
        for r in result["query_routing"]["calls"]
        if r["routing"] == "CODE_ALLOW"
    )
