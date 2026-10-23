"""Reproduce concrete compatibility failures without provider calls."""

import copy
import json
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from test_dtap_runtime_boundary import actual_registry
from test_functional_routing import decision, metadata, setup

from app.benchmark.registry import UnsupportedTool
from app.benchmark.task_scope import PROBE_SCRIPT, targets
from app.benchmark.tree_scope import TREE_PROBE_SCRIPT
from app.pdp.diagnostics import AnalysisFailure, failure_details
from app.transparent.engine import Rejected


def audit_metadata(candidate):
    value = metadata(candidate)
    leaf = value["tree"]["nodes"][0]
    leaf["path"] = "/data/system_audit.log"
    value["tree"]["output_bound"] = len(leaf["path"].encode()) + 256
    return value


@pytest.mark.parametrize("tool", ["list_directory", "list_directory_with_sizes", "search_files"])
def test_authorized_audit_name_and_size_metadata_reaches_semantics(tmp_path, tool):
    args = (
        {"search_path": "/data", "pattern": "*"} if tool == "search_files" else {"dirpath": "/data"}
    )
    candidate = {"route": "mcp", "tool": "OS-filesystem::" + tool, "args": args}
    engine, policy, wires, value = setup(tmp_path, candidate=candidate)
    policy.scope_probe = audit_metadata
    assert decision(engine)["decision"] == "ALLOW"
    assert len(wires) == 2 and wires[0]["state"]["candidate"] == value
    engine.forward("m", "call")
    with pytest.raises(Rejected):
        engine.forward("m", "call")


@pytest.mark.parametrize(
    "tool,extra",
    [
        ("read_file", {}),
        ("get_file_info", {}),
        ("delete_file", {}),
        ("write_file", {"content": "changed"}),
    ],
)
def test_audit_metadata_visibility_never_authorizes_direct_protected_access(tmp_path, tool, extra):
    value = {
        "route": "mcp",
        "tool": "OS-filesystem::" + tool,
        "args": {"filepath": "/data/system_audit.log", **extra},
    }
    engine, policy, wires, _ = setup(tmp_path, candidate=value)
    policy.scope_probe = lambda _: pytest.fail("protected action must not probe or call Jev")
    assert decision(engine)["decision"] == "DENY" and not wires


@pytest.mark.parametrize(
    "mode,name",
    [
        (stat.S_IFLNK | 0o777, "system_audit.log"),
        (stat.S_IFDIR | 0o755, "system_audit.log"),
        (stat.S_IFREG | 0o600, "system_audit.log"),
        (stat.S_IFREG | 0o644, ".env"),
        (stat.S_IFREG | 0o644, "credentials.json"),
    ],
)
def test_metadata_exception_preserves_links_private_secret_and_directory_rules(
    tmp_path, mode, name
):
    candidate = {
        "route": "mcp",
        "tool": "OS-filesystem::list_directory",
        "args": {"dirpath": "/data"},
    }
    engine, policy, wires, _ = setup(tmp_path, candidate=candidate)

    def fixture(c):
        value = audit_metadata(c)
        value["tree"]["nodes"][0].update(mode=mode, path="/data/" + name)
        value["tree"]["output_bound"] = len(("/data/" + name).encode()) + 256
        return value

    policy.scope_probe = fixture
    assert decision(engine)["decision"] in ("DENY", "CONFIRM") and not wires


def test_conclusive_untraversable_child_is_policy_denial_not_analysis_failure(tmp_path):
    candidate = {
        "route": "mcp",
        "tool": "OS-filesystem::search_files",
        "args": {"search_path": "/data", "pattern": "*"},
    }
    engine, policy, wires, _ = setup(tmp_path, candidate=candidate)

    def blocked(c):
        value = metadata(c)
        value["tree"]["nodes"][0]["traversal_denied"] = True
        return value

    policy.scope_probe = blocked
    result = decision(engine)
    assert result["decision"] == "DENY" and result["reasons"] == [
        "RESOURCE_TRAVERSAL_NOT_AUTHORIZED"
    ]
    assert result["diagnostic"] is None and not wires


def test_fixed_probe_records_permission_refusal_without_executing_another_identity(tmp_path):
    child = tmp_path / "blocked"
    child.mkdir()
    script = (
        PROBE_SCRIPT
        + "\nreal_open=os.open\ndef guarded_open(path,*args,**kwargs):\n if path=='blocked': raise PermissionError('synthetic exact filesystem refusal')\n return real_open(path,*args,**kwargs)\nos.open=guarded_open\n"
        + TREE_PROBE_SCRIPT
        + "\nprint(json.dumps(tree))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            script,
            json.dumps({"paths": [str(tmp_path)], "tree_depth": 32, "complete_search": True}),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    tree = json.loads(result.stdout)
    assert tree["nodes"][0]["traversal_denied"] is True
    assert len(tree["nodes"]) == 1


def test_original_directory_trailing_slash_keeps_exact_candidate_and_canonical_probe_path():
    candidate = {
        "route": "mcp",
        "tool": "OS-filesystem::create_directory",
        "args": {"dirpath": "/etc/app/backups/"},
    }
    original = copy.deepcopy(candidate)
    registry = actual_registry()
    registry.resolve("OS-filesystem", "create_directory", candidate["args"])
    assert targets(candidate, registry) == ["/etc/app/backups"]
    assert candidate == original


@pytest.mark.parametrize(
    "path", ["/etc//app/backups/", "/etc/app/../root/", "/etc/app/backups/;id", "relative/"]
)
def test_directory_alias_never_allows_traversal_or_shell_syntax(path):
    with pytest.raises(UnsupportedTool):
        actual_registry().resolve("OS-filesystem", "create_directory", {"dirpath": path})


def test_real_probe_fault_remains_diagnosed_failure_not_policy_refusal():
    details = failure_details(AnalysisFailure("RESOURCE_METADATA_UNAVAILABLE"))
    assert details == [{"code": "RESOURCE_METADATA_UNAVAILABLE", "view": "SERVER"}]


@pytest.mark.parametrize("tool", ["read_file", "get_file_info", "check_file_exists"])
def test_refused_partial_lstat_chain_is_never_treated_as_nonexistent_file(tmp_path, tool):
    candidate = {
        "route": "mcp",
        "tool": "OS-filesystem::" + tool,
        "args": {"filepath": "/data/report.txt"},
    }
    engine, policy, wires, _ = setup(tmp_path, candidate=candidate)

    def denied(c):
        value = metadata(c)
        value["resources"][0]["chain"] = value["resources"][0]["chain"][:-1]
        value["resources"][0]["traversal_denied"] = True
        return value

    policy.scope_probe = denied
    result = decision(engine)
    assert result["decision"] == "DENY" and result["reasons"] == [
        "RESOURCE_TRAVERSAL_NOT_AUTHORIZED"
    ]
    assert result["diagnostic"] is None and not wires


def actual_metadata_engine(tmp_path, request, candidate, actual):
    from cryptography.fernet import Fernet
    from test_engine_demo_02 import policy_for

    from app.benchmark.runtime_policy import RuntimeEngine, SyntheticBoundary
    from app.benchmark.shell_scope import PROFILE, REVISION
    from app.benchmark.task_scope import issue_scope
    from app.common import canonical

    registry = actual_registry()
    boundary = SyntheticBoundary(["PUBLIC-TEST-PROTECTED-CREDENTIAL"])
    policy, wires = policy_for(registry, boundary, profile=PROFILE, confidence=0.6)
    user = canonical({"actual_user_turns_chronological": [request], "latest_turn": 0})
    grant = {
        "workspace": "DTAP_OFFICIAL_SANDBOX",
        "tools": {"native": [], "mcp": list(registry.by_name)},
        "authenticated_access_token": "alice-token",
        "task_scope": issue_scope(user, registry, revision=REVISION),
        "reviewed_operations": [],
    }
    policy.scope_probe = lambda c: copy.deepcopy(actual)
    engine = RuntimeEngine(
        tmp_path / "actual.db",
        Fernet.generate_key(),
        grant,
        policy_router=policy,
        boundary=boundary,
    )
    engine.turn("m", "s", "t", request, "DTAP_OFFICIAL_SANDBOX")
    engine.register("m", "s", "t", "call", candidate["tool"], candidate["args"], "mcp")
    return engine, wires






@pytest.mark.parametrize(
    "fault", ["child_no_search", "child_walk_permission", "root_no_search", "ancestor_no_search"]
)
def test_fixed_probe_conclusive_permission_cases_return_metadata(tmp_path, fault):
    child = tmp_path / "blocked"
    child.mkdir()
    (child / "leaf").write_text("fixture")
    target = (
        str(child)
        if fault == "root_no_search"
        else str(child / "leaf")
        if fault == "ancestor_no_search"
        else str(tmp_path)
    )
    # Simulate exact POSIX outcomes without relying on the developer test UID.
    injection = (
        "\nreal_access=os.access\nreal_stat=os.stat\nreal_open=os.open\ndef denied_access(path,mode,*a,**kw):\n if mode==os.X_OK and (path=='blocked' or path=="
        + repr(str(child))
        + "): return False\n return real_access(path,mode,*a,**kw)\n"
    )
    if fault in ("child_no_search", "root_no_search", "ancestor_no_search"):
        injection += "os.access=denied_access\n"
    else:
        injection += "\ndef denied_stat(path,*a,**kw):\n if path=='leaf' and 'dir_fd' in kw: raise PermissionError('synthetic exact metadata denial')\n return real_stat(path,*a,**kw)\nos.stat=denied_stat\n"
    script = (
        "import os,sys,json,stat,pwd\n"
        + injection
        + PROBE_SCRIPT
        + TREE_PROBE_SCRIPT
        + "\nprint(json.dumps({'rows':rows,'tree':tree}))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            script,
            json.dumps({"paths": [target], "tree_depth": 32, "complete_search": True}),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    if fault in ("root_no_search", "ancestor_no_search"):
        assert value["tree"] is None
    else:
        assert any(n.get("traversal_denied") for n in value["tree"]["nodes"])


@pytest.fixture
def repaired_ledger(tmp_path, monkeypatch):
    from app.benchmark.runtime_budget import RuntimeBudget
    from app.benchmark.runtime_functional_continuation import seed_metadata_successor
    from app.common import canonical, digest

    monkeypatch.setattr("app.benchmark.runtime_login.verify_parent", lambda *a: None)
    root = (
        Path(__file__).resolve().parents[2]
        / "artifacts/20261018-dtap-os100/user-functional-stream-continue-1"
    )
    manifest = json.loads((root / "plan.json").read_text())["manifest"]
    path = tmp_path / "repair.sqlite3"
    shutil.copyfile(root / "broker-data/provider.sqlite3", path)
    with sqlite3.connect(path) as db:
        seed_metadata_successor(db, manifest)
        db.execute("UPDATE binding SET hash=?", (digest(canonical(manifest)),))
    return RuntimeBudget(path, manifest)






