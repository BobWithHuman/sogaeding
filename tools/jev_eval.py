"""Explicit user-only synthetic Jev smoke; prep/preflight never submit inference.

All keys remain in an ignored owner-protected folder. No actor, real file tool,
existing DB, OpenAI ledger, provider aliases, retries or automatic fallback.
"""

import argparse
import asyncio
import copy
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELATIVE = "artifacts/runtime-jev-eval"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
REQUEST_LIMIT, TOKEN_LIMIT = 4, 256000
FOLLOWUP_RUN_ID = "followup-response-v2"
FOLLOWUP_VERSION = "jev-followup-execution-1"
V4_RUN_ID = "followup-auto-v4"
V4_VERSION = "jev-v4-evaluation-1"
V4_INPUT = "artifacts/20261017-auto-decision"
V5_RUN_ID = "followup-behavior-v5"
V5_VERSION = "jev-v5-evaluation-1"
V5_INPUT = "artifacts/20261017-decision-attribution"
V5_ORIGINAL_PLAN = "artifacts/runtime-jev-followups/followup-auto-v4/plan/requests.json"
V5_ORIGINAL_SHA = "0d36e068c29ca7b0ccfa08af981ac3c38e3bca85a193884d89548cc9060ad735"
V5_CANDIDATE_SHA = "f9f5a2f36645aee62f58511d7246bcae8cb835a722aadab705a8ffaa07e9ec64"
V5_SNAPSHOTS = {
    "normal": "595559b9e0e0ad3f8803d6602fcb3823a01feac61a749cea6c5ae298074408e3",
    "attack": "3deb230d8a94a73ee295e2acbca321045b5d74e49f0a1f30e231d5c05231f83b",
}
FIXED_RUNS = (V4_RUN_ID, V5_RUN_ID)
V4_FIXED_HASHES = {
    "future-eval-proposal.json": "23bcf22ed8106ed4660bfb964e4f8c7073cbd1b2e186247caa0905c1c24dd7d0",
    "candidate-manifest.json": "293f35548af85be5ed6fd72c27fdf93f94e922e5874b4d973a02914ae3138959",
    "proposal-normal-A.json": "562898ff848289639282d9220c737c32be63400d4a15479e97f68433b35746ba",
    "proposal-normal-B.json": "f77d8dbc19151806d839cafb0c0a8f4bab9382d3e8164d5a38186756d3080ea8",
    "proposal-attack-A.json": "3664ce473f0cc77ae43d098ff8ee964676451af106332610c5d9d93a4a546b56",
    "proposal-attack-B.json": "0ffbf3a9d1f673f3bd8344a5d6bc4d7759e59e4d4778decb5da408f235587a02",
}
PRICE = {"checked_utc_date": "2026-10-16", "input_usd_per_million": 0.042,
         "output_usd": 0, "proposed_reservation_usd_before_tax": 0.010752,
         "status": "PROPOSAL_NOT_USAGE_OR_ACCOUNT_BILLING_GUARANTEE",
         "source": "https://docs.typesafe.ai/models"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def location(root):
    root = root.resolve()
    path = root / RELATIVE
    if path.is_symlink() or not path.resolve().is_relative_to(root / "artifacts"):
        raise ValueError("EVAL_PATH_REJECTED")
    return path


def protect(path, directory=False):
    if path.is_symlink():
        raise ValueError("EVAL_PATH_REJECTED")
    if os.name == "nt":
        system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
        found = subprocess.run([str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True)
        sid = next(csv.reader(io.StringIO(found.stdout)))[1]
        if not re.fullmatch(r"S-1-5-[0-9-]+", sid):
            raise ValueError("ACL_IDENTITY_UNAVAILABLE")
        suffix = "(OI)(CI)F" if directory else "F"
        result = subprocess.run([str(system / "icacls.exe"), str(path), "/inheritance:r", "/grant:r", f"*{sid}:{suffix}", f"*S-1-5-18:{suffix}"], capture_output=True, check=False)
        if result.returncode:
            raise ValueError("OWNER_ACL_UNAVAILABLE")
    else:
        path.chmod(0o700 if directory else 0o600)


def private_ready(root, run_path=None):
    path = run_path or location(root)
    target = path / "key/jev.api-key"
    if run_path is not None:
        target = location(root) / "key/jev.api-key"
    git = shutil.which("git")
    if not git or Path(git).resolve().is_relative_to(root.resolve()):
        raise ValueError("IGNORED_KEY_PATH_UNVERIFIED")
    ignored = subprocess.run([git, "-C", str(root), "check-ignore", "--quiet", "--", str(target.relative_to(root))], capture_output=True, check=False)
    if ignored.returncode:
        raise ValueError("IGNORED_KEY_PATH_UNVERIFIED")
    candidates = [path, path / "config", path / "ledger", path / "results", path / "plan"]
    candidates.append(target.parent)
    if target.exists():
        candidates.append(target)
    for item in candidates:
        if item.is_symlink():
            raise ValueError("EVAL_PATH_REJECTED")
        if os.name != "nt":
            if stat.S_IMODE(item.stat().st_mode) != (0o700 if item.is_dir() else 0o600):
                raise ValueError("OWNER_ACL_UNVERIFIED")
        else:
            # ACL identities only. No secret file is opened by this check.
            script = "$a=Get-Acl -LiteralPath $env:JEV_EVAL_ACL_PATH; $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User; $ok=$a.AreAccessRulesProtected; foreach($r in $a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) { if($r.AccessControlType -eq 'Allow' -and $r.IdentityReference.Value -notin @($sid.Value,'S-1-5-18')) {$ok=$false} }; if($ok){exit 0}else{exit 1}"
            executable = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
            environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "PATH") if key in os.environ}
            environment["JEV_EVAL_ACL_PATH"] = str(item)
            outcome = subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-Command", script], env=environment, capture_output=True, timeout=15, check=False)
            if outcome.returncode:
                raise ValueError("OWNER_ACL_UNVERIFIED")
    return True


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical(value) + "\n")
    protect(path)


def trusted_docker(root):
    exe = shutil.which("docker")
    if not exe or Path(exe).resolve().is_relative_to(root.resolve()):
        raise ValueError("TRUSTED_DOCKER_REQUIRED")
    return str(Path(exe).resolve())


def image_id(root):
    result = subprocess.run([trusted_docker(root), "image", "inspect", "with-human-dev:local", "--format", "{{.Id}}"], capture_output=True, text=True, timeout=15, check=False)
    value = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError("EXISTING_PINNED_IMAGE_REQUIRED_NO_PULL")
    return value


def source_hashes(root):
    root = root.resolve()
    paths = [*sorted((root / "src").rglob("*.py")), *sorted((root / "docs/mvp/contracts").glob("*.json")),
             root / "fixtures/jev/smoke.json", root / "tools/jev_eval.py"]
    if (root / "scripts/jev_eval.ps1").is_file():
        paths.append(root / "scripts/jev_eval.ps1")
    for path in paths:
        if not path.resolve().is_relative_to(root):
            raise ValueError("SOURCE_PATH_REJECTED")
        for item in (path, *path.parents):
            if item == root:
                break
            if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
                raise ValueError("SOURCE_PATH_REJECTED")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("SOURCE_PATH_REJECTED")
    return {path.relative_to(root).as_posix(): sha(path) for path in paths}


def docker_args(root, image, mode, live=False, run_id=None):
    path = followup_location(root, run_id) if run_id is not None else location(root)
    uid = "10001:10001" if os.name == "nt" else f"{os.getuid()}:{os.getgid()}"
    args = [trusted_docker(root), "run", "--rm", "--pull", "never", "--read-only", "--user", uid,
            "--network", "bridge" if live else "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--tmpfs", "/tmp:size=64m,mode=1777", "--pids-limit", "64", "--memory", "512m",
            "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "CONTRACT_DIR=/product/contracts",
            "--mount", f"type=bind,source={root / 'src'},target=/product/src,readonly",
            "--mount", f"type=bind,source={root / 'docs/mvp/contracts'},target=/product/contracts,readonly",
            "--mount", f"type=bind,source={root / 'fixtures/jev/smoke.json'},target=/smoke.json,readonly",
            "--mount", f"type=bind,source={root / 'tools/jev_eval.py'},target=/runner.py,readonly"]
    if mode != "_plan":
        for folder, target, readonly in (("plan", "/plan", True), ("key", "/jev-key", True),
                                         ("config", "/jev-config", True), ("ledger", "/jev-budget", False),
                                         ("results", "/evidence", False)):
            source = location(root) / "key" if run_id is not None and folder == "key" else path / folder
            args += ["--mount", f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")]
    if run_id is not None:
        args += ["-e", "JEV_EVAL_RUN_ID=" + run_id]
    if run_id == V4_RUN_ID:
        args += ["--mount", f"type=bind,source={root / V4_INPUT},target=/v4-input,readonly",
                 "--mount", f"type=bind,source={root / 'fixtures/mvp_demo'},target=/v4-fixtures,readonly"]
    if run_id == V5_RUN_ID:
        args += ["--mount", f"type=bind,source={root / V5_ORIGINAL_PLAN},target=/v5-original-requests.json,readonly"]
    return [*args, image, "python", "-I", "/runner.py", mode]


def build_plan(fixture_path):
    from app.common import canonical as wire
    from app.pdp.semantic import material
    from app.transparent.jev_policy import CONTRACT, POLICY, QUESTION_VERSION, THRESHOLD, build
    from app.transparent.tool_schema import parse
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("version") != "jev-ko-smoke-1" or len(fixture.get("cases", [])) != 2:
        raise ValueError("SMOKE_FIXTURE_INVALID")
    cases = []
    for case in fixture["cases"]:
        snap = {"analysis_id": "jev-ko-smoke-1-" + case["id"],
                "user_request": wire({"actual_user_turns_chronological": [case["request"]], "latest_turn": 0}),
                "server_grant": {"workspace": "C:\\synthetic-jev-smoke", "comment_mode": "DEVELOPMENT"},
                "candidate": case["candidate"],
                "sources": [{"source_id": "smoke-source", "same_issue": False, **material(case["source"])}]}
        requests, _, _, _ = build(snap, parse(snap["candidate"], snap["server_grant"]["workspace"]))
        cases.append({"case_id": case["id"], "snapshot": snap,
                      "wire": {view: {"model": MODEL, "state": state, "questions": questions}
                               for view, (state, questions) in requests.items()},
                      "expected_local_only": case["expected_local_only"]})
    return {"version": "jev-smoke-plan-1", "endpoint": ENDPOINT, "model": MODEL,
            "policy": POLICY, "contract": CONTRACT, "question_version": QUESTION_VERSION,
            "threshold": THRESHOLD, "threshold_status": "PLACEHOLDER_NOT_CALIBRATED",
            "request_limit": REQUEST_LIMIT, "input_token_reservation_limit": TOKEN_LIMIT,
            "price_proposal": PRICE, "cases": cases}


def prepare(root):
    path = location(root)
    if path.exists():
        raise ValueError("EVAL_ALREADY_PREPARED_NO_OVERWRITE_OR_NEW_ALLOWANCE")
    image = image_id(root)
    outcome = subprocess.run(docker_args(root, image, "_plan"), capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if outcome.returncode:
        raise ValueError("OFFLINE_PLAN_UNAVAILABLE")
    plan = json.loads(outcome.stdout)
    path.mkdir(parents=True)
    protect(path, True)
    for name in ("plan", "key", "config", "ledger", "results"):
        folder = path / name
        folder.mkdir()
        protect(folder, True)
    write_new(path / "plan/requests.json", plan)
    manifest = {"version": "jev-smoke-manifest-1", "image_id": image, "source_hashes": source_hashes(root),
                "requests_sha256": sha(path / "plan/requests.json"), "endpoint": ENDPOINT, "model": MODEL,
                "request_limit": REQUEST_LIMIT, "input_token_limit": TOKEN_LIMIT}
    write_new(path / "plan/manifest.json", manifest)
    write_new(path / "config/policy.json", {"enabled": False, "model": MODEL, "request_limit": None,
                                         "input_token_limit": None, "policy_id": None})
    private_ready(root)
    return {"prepared": True, "enabled": False, "paid_requests": 0, "key_present": False,
            "manifest_sha256": sha(path / "plan/manifest.json"), "provider_access": "NOT_VERIFIED_NO_REQUEST"}


def store_key(root, value):
    path = location(root)
    if not (path / "plan/manifest.json").is_file():
        raise ValueError("PREPARE_FIRST")
    private_ready(root)  # Must pass before consuming/writing the user's hidden input.
    key = value.strip()
    if not 16 <= len(key) <= 2048 or not key.isascii() or any(c.isspace() for c in key):
        raise ValueError("KEY_FORMAT_REJECTED")
    target = path / "key/jev.api-key"
    if target.exists() or target.is_symlink():
        raise ValueError("EXISTING_KEY_NOT_REPLACED")
    with target.open("xb") as stream:
        stream.write(key.encode("ascii"))
    protect(target)
    return {"key_stored": True, "key_value_recorded": False, "paid_requests": 0, "enabled": False}


def verified(root, require_current=True):
    path = location(root)
    for name in ("plan", "key", "config", "ledger", "results"):
        if (path / name).is_symlink():
            raise ValueError("EVAL_PATH_REJECTED")
    for name in ("plan/manifest.json", "plan/requests.json", "config/policy.json", "config/authorized-run.json", "results/result.json"):
        if (path / name).is_symlink():
            raise ValueError("EVAL_PATH_REJECTED")
    manifest = json.loads((path / "plan/manifest.json").read_text(encoding="utf-8"))
    if (require_current and manifest.get("source_hashes") != source_hashes(root)) or manifest.get("requests_sha256") != sha(path / "plan/requests.json"):
        raise ValueError("EVAL_PLAN_STALE_OR_TAMPERED")
    if manifest.get("endpoint") != ENDPOINT or manifest.get("model") != MODEL or manifest.get("request_limit") != REQUEST_LIMIT or manifest.get("input_token_limit") != TOKEN_LIMIT:
        raise ValueError("EVAL_LIMIT_OR_ENDPOINT_CHANGED")
    return path, manifest


def preflight(root):
    path, manifest = verified(root)
    private_ready(root)
    outcome = subprocess.run(docker_args(root, manifest["image_id"], "_preflight"), capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if outcome.returncode:
        raise ValueError("EVAL_PREFLIGHT_UNAVAILABLE")
    report = json.loads(outcome.stdout)
    report.update(manifest_sha256=sha(path / "plan/manifest.json"), provider_access="NOT_VERIFIED_NO_REQUEST",
                  live_authorized=False, request_limit_proposed=4, input_reservation_limit_proposed=256000, price_proposal=PRICE)
    return report


def evaluate(root, confirm_send=False, manifest_sha256=None, approve_request_limit=None, approve_input_reservation_limit=None):
    path, manifest = verified(root)
    expected = sha(path / "plan/manifest.json")
    if confirm_send is not True or manifest_sha256 != expected or type(approve_request_limit) is not int or approve_request_limit != REQUEST_LIMIT or type(approve_input_reservation_limit) is not int or approve_input_reservation_limit != TOKEN_LIMIT:
        raise ValueError("USER_SEND_APPROVAL_AND_EXACT_MANIFEST_REQUIRED")
    if (path / "ledger/typesafe-budget.sqlite3").exists() or (path / "results/result.json").exists():
        raise ValueError("EVALUATION_ALREADY_ATTEMPTED_NO_RETRY_OR_RESET")
    report = preflight(root)
    if not report.get("ready_for_user_opt_in"):
        raise ValueError("EVAL_PREFLIGHT_FAILED")
    write_new(path / "config/authorized-run.json", {"enabled": True, "model": MODEL, "request_limit": 4,
              "input_token_limit": 256000, "policy_id": "jev-smoke-" + expected[:32]})
    outcome = subprocess.run(docker_args(root, manifest["image_id"], "_evaluate", live=True), capture_output=True, text=True, encoding="utf-8", timeout=100, check=False)
    # No provider error body/exception text is ever copied from Docker stderr.
    collected = collect(root)
    return {"execution_exit": outcome.returncode, "provider_calls": "SEE_SEPARATE_PROVIDER_LEDGER",
            "execution_exit_is_semantic_success": False, "semantic_summary": collected["semantic_summary"],
            "result": collected, "paid_actor_requests": 0}


def ledger_summary(path):
    if not path.is_file():
        return {"requests_attempted": 0, "input_reserved": 0, "actual_input_tokens": 0, "actual_output_tokens": 0,
                "usage_complete": True, "actual_usage_status": "NO_ATTEMPTS"}
    if path.is_symlink():
        raise ValueError("EVAL_PATH_REJECTED")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        rows = db.execute("SELECT status,input_reserved,usage FROM jev_attempts").fetchall()
    result = {"requests_attempted": len(rows), "input_reserved": sum(row[1] for row in rows), "actual_input_tokens": 0, "actual_output_tokens": 0}
    counters = []
    for _, _, usage in rows:
        try:
            value = json.loads(usage) if usage else None
        except (ValueError, TypeError):
            value = None
        known = {}
        if isinstance(value, dict) and not set(value) - {"input_tokens", "output_tokens"}:
            for key, maximum in (("input_tokens", 64000), ("output_tokens", 1000000)):
                count = value.get(key)
                if type(count) is int and 0 <= count <= maximum:
                    known[key] = count
                    result["actual_" + key] += count
        counters.append(known)
    result["usage_complete"] = all(set(value) == {"input_tokens", "output_tokens"} for value in counters)
    result["input_usage_complete"] = all("input_tokens" in value for value in counters)
    result["output_usage_complete"] = all("output_tokens" in value for value in counters)
    result["recorded_input_charge_usd_before_tax"] = result["actual_input_tokens"] * 0.042 / 1000000
    result["estimated_total_charge_usd_before_tax"] = result["recorded_input_charge_usd_before_tax"] if result["usage_complete"] else None
    result["actual_usage_status"] = "COMPLETE_RECORDED_USAGE" if result["usage_complete"] else "INCOMPLETE_UNKNOWN_BILLABLE_USAGE"
    return result


def semantic_summary(record, planned):
    rows = record.get("results", []) if isinstance(record, dict) else []
    by_id = {row.get("case_id"): row for row in rows if isinstance(row, dict)}
    cases, scored, not_scored, not_attempted, mismatches = [], 0, 0, 0, 0
    for case in planned:
        case_id = case["case_id"]
        row = by_id.get(case_id)
        if row is None:
            not_attempted += 1
            cases.append({"case_id": case_id, "status": "NOT_ATTEMPTED", "comparison": "NOT_SCORED"})
            continue
        comparison = row.get("local_expected_comparison", "NOT_SCORED")
        if comparison in ("MATCH", "MISMATCH") and row.get("decision") in ("ALLOW", "DENY", "CONFIRM"):
            scored += 1
            mismatches += int(comparison == "MISMATCH")
            cases.append({"case_id": case_id, "status": "SCORED_SMOKE_OBSERVATION", "decision": row["decision"], "comparison": comparison})
        else:
            not_scored += 1
            diagnostic = row.get("diagnostics", [])
            enriched = any(isinstance(item, dict) and set(item) - {"code", "view"} for item in diagnostic)
            cases.append({"case_id": case_id, "status": "ANALYSIS_UNAVAILABLE", "comparison": "NOT_SCORED",
                          "diagnostic_detail": "AVAILABLE_ALLOWLIST_METADATA" if enriched else "UNKNOWN_NOT_RECORDED"})
    outcome = ("ANALYSIS_FAILED_PARTIAL" if not_scored else "NOT_RUN" if not_attempted == len(planned) else
               "PARTIAL_OBSERVATIONS" if not_attempted else "COMPLETE_OBSERVATIONS_WITH_MISMATCH" if mismatches else
               "COMPLETE_OBSERVATIONS_MATCH_SMOKE_ONLY")
    return {"outcome": outcome, "planned_candidates": len(planned), "scored_candidates": scored,
            "not_scored_candidates": not_scored, "not_attempted_candidates": not_attempted,
            "cases": cases, "attack_identification": "NOT_ESTABLISHED", "execution_exit_is_semantic_success": False}


def collect(root):
    path, manifest = verified(root, require_current=False)
    summary = ledger_summary(path / "ledger/typesafe-budget.sqlite3")
    result_path = path / "results/result.json"
    record = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else "NOT_RUN_OR_RESULT_UNAVAILABLE"
    plan = json.loads((path / "plan/requests.json").read_text(encoding="utf-8"))
    return {"usage": summary, "result": record, "semantic_summary": semantic_summary(record, plan["cases"]),
            "current_source_matches_frozen_run": manifest["source_hashes"] == source_hashes(root),
            "model_accuracy": "NOT_ESTABLISHED_CONNECTION_SMOKE_ONLY", "real_file_effects": "NOT_RUN"}


def followup_location(root, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r"followup-[a-z0-9][a-z0-9-]{0,39}", run_id):
        raise ValueError("FOLLOWUP_RUN_ID_REJECTED")
    root = root.resolve()
    artifacts = root / "artifacts"
    base = artifacts / "runtime-jev-followups"
    def linked(path):
        return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())
    if linked(artifacts) or linked(base) or not artifacts.resolve().is_relative_to(root):
        raise ValueError("EVAL_PATH_REJECTED")
    target = base / run_id
    if linked(target) or not target.resolve().is_relative_to(artifacts.resolve()):
        raise ValueError("EVAL_PATH_REJECTED")
    return target


def followup_plan(root, run_id, confirm_new_plan=False):
    # A disabled proposal only. This function never mounts/reads/copies the old
    # key and cannot create provider allowance, ledger or authorization config.
    if confirm_new_plan is not True:
        raise ValueError("EXPLICIT_NEW_PLAN_CONFIRMATION_REQUIRED")
    target = followup_location(root, run_id)
    if target.exists():
        raise ValueError("FOLLOWUP_ALREADY_EXISTS_NO_OVERWRITE")
    prior, prior_manifest = verified(root, require_current=False)
    prior_usage = ledger_summary(prior / "ledger/typesafe-budget.sqlite3")
    attempted, reserved = prior_usage["requests_attempted"], prior_usage["input_reserved"]
    if not 0 <= attempted <= REQUEST_LIMIT or reserved != attempted * 64000:
        raise ValueError("PRIOR_BUDGET_INVALID")
    image = image_id(root)
    generated = subprocess.run(docker_args(root, image, "_plan"), capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if generated.returncode:
        raise ValueError("OFFLINE_PLAN_UNAVAILABLE")
    plan = json.loads(generated.stdout)
    remaining_requests, remaining_reserved = REQUEST_LIMIT - attempted, TOKEN_LIMIT - reserved
    proposal = {"status": "DISABLED_PROPOSAL_NOT_EXECUTABLE", "budget_snapshot_utc": datetime.now(UTC).isoformat(),
                "prior_request_limit": REQUEST_LIMIT, "prior_input_limit": TOKEN_LIMIT,
                "prior_requests_attempted": attempted, "prior_input_reserved": reserved,
                "remaining_requests": remaining_requests, "remaining_input_reserved": remaining_reserved,
                "full_smoke_requests": 4, "full_smoke_input_reservation": 256000,
                "proposed_total_requests_including_prior": attempted + 4,
                "proposed_total_input_reservation_including_prior": reserved + 256000,
                "prior_failure_reservation_refunded": False,
                "additional_requests_needed": max(0, 4 - remaining_requests),
                "additional_input_reservation_needed": max(0, 256000 - remaining_reserved),
                "full_smoke_fits_existing_remainder": remaining_requests >= 4 and remaining_reserved >= 256000,
                "prior_usage_status": prior_usage["actual_usage_status"], "prior_actual_charge": prior_usage.get("estimated_total_charge_usd_before_tax"),
                "budget_snapshot_is_not_reservation": True, "budget_may_change_with_concurrent_activity": True,
                "new_allowance_created": False, "evaluation_supported": False,
                "next_step": "SEPARATE_USER_DECISION_ON_EXACT_DATA_AND_TOTAL_ADDITIONAL_BUDGET_REQUIRED"}
    target = followup_location(root, run_id)  # Recheck after the external plan builder.
    target.parent.mkdir(exist_ok=True)
    target = followup_location(root, run_id)  # Recheck after subprocess/writer race.
    target.mkdir()  # Atomic no-clobber claim: concurrent same run ID has one winner.
    protect(target, True)
    (target / "plan").mkdir()
    (target / "config").mkdir()
    protect(target / "plan", True)
    protect(target / "config", True)
    write_new(target / "plan/requests.json", plan)
    write_new(target / "plan/manifest.json", {"version": "jev-followup-proposal-1", "run_id": run_id,
              "image_id": image, "source_hashes": source_hashes(root), "requests_sha256": sha(target / "plan/requests.json"),
              "parent_manifest_sha256": sha(prior / "plan/manifest.json"), "parent_image_id": prior_manifest["image_id"],
              "provider_key_reference": {"path": RELATIVE + "/key/jev.api-key", "mount_readonly": True, "contents_read_or_copied": False},
              "prior_ledger_reference": {"path": RELATIVE + "/ledger/typesafe-budget.sqlite3", "mode": "READ_ONLY_ACCOUNTING_REFERENCE"},
              "endpoint": ENDPOINT, "model": MODEL, "budget_proposal": proposal})
    write_new(target / "config/policy.json", {"enabled": False, "model": MODEL, "request_limit": None, "input_token_limit": None, "policy_id": None})
    return {"run_id": run_id, "created": "DISABLED_PROPOSAL_ONLY", "paid_requests": 0,
            "manifest_sha256": sha(target / "plan/manifest.json"), "budget_proposal": proposal,
            "provider_key_read_or_copied": False, "new_provider_ledger_created": False}


def parent_binding(root):
    prior, manifest = verified(root, require_current=False)
    ledger = prior / "ledger/typesafe-budget.sqlite3"
    if ledger.is_symlink() or not ledger.is_file() or any(Path(str(ledger) + ending).exists() for ending in ("-wal", "-journal")):
        raise ValueError("PRIOR_LEDGER_UNAVAILABLE_OR_BUSY")
    before = sha(ledger)
    usage = ledger_summary(ledger)
    if sha(ledger) != before or usage["requests_attempted"] != 1 or usage["input_reserved"] != 64000:
        raise ValueError("PRIOR_LEDGER_CHANGED_OR_UNEXPECTED")
    return {"manifest_sha256": sha(prior / "plan/manifest.json"), "ledger_sha256": before,
            "ledger_reference": RELATIVE + "/ledger/typesafe-budget.sqlite3", "usage": usage,
            "parent_image_id": manifest["image_id"]}


def followup_prepare(root, run_id, confirm_new_plan=False):
    if run_id in FIXED_RUNS:
        return v4_prepare(root, confirm_new_plan, run_id)
    if run_id != FOLLOWUP_RUN_ID or confirm_new_plan is not True:
        raise ValueError("SINGLE_FOLLOWUP_PREPARATION_CONFIRMATION_REQUIRED")
    target = followup_location(root, run_id)
    if target.exists():
        raise ValueError("FOLLOWUP_ALREADY_EXISTS_NO_PROMOTION_OR_OVERWRITE")
    if not (root / "scripts/jev_eval.ps1").is_file():
        raise ValueError("FOLLOWUP_WRAPPER_REQUIRED")
    binding = parent_binding(root)
    private_ready(root)  # Existing key ACL/metadata only, never contents/hash.
    image = image_id(root)
    generated = subprocess.run(docker_args(root, image, "_plan"), capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if generated.returncode:
        raise ValueError("OFFLINE_PLAN_UNAVAILABLE")
    plan = json.loads(generated.stdout)
    if parent_binding(root) != binding:
        raise ValueError("PRIOR_LEDGER_CHANGED_OR_UNEXPECTED")
    target = followup_location(root, run_id)
    target.parent.mkdir(exist_ok=True)
    target = followup_location(root, run_id)
    target.mkdir()  # One canonical slot; no arbitrary allowance factory.
    protect(target, True)
    for name in ("plan", "config", "ledger", "results"):
        (target / name).mkdir()
        protect(target / name, True)
    write_new(target / "plan/requests.json", plan)
    write_new(target / "config/policy.json", {"enabled": False, "model": MODEL, "request_limit": None, "input_token_limit": None, "policy_id": None})
    manifest = {"version": FOLLOWUP_VERSION, "run_id": run_id, "image_id": image,
                "source_hashes": source_hashes(root), "requests_sha256": sha(target / "plan/requests.json"),
                "endpoint": ENDPOINT, "model": MODEL, "parent_binding": binding,
                "provider_key_reference": RELATIVE + "/key/jev.api-key", "key_mount": "READ_ONLY_REFERENCE_NO_COPY",
                "request_limit": 4, "input_token_limit": 256000, "cumulative_request_limit": 5,
                "cumulative_input_reservation_limit": 320000, "additional_request_limit": 1,
                "additional_input_reservation_limit": 64000,
                "prior_consumed_requests": 1, "prior_consumed_input_reserved": 64000,
                "prior_remaining_requests": 3, "prior_remaining_input_reserved": 192000}
    write_new(target / "plan/manifest.json", manifest)
    return {"run_id": run_id, "prepared": True, "enabled": False, "paid_requests": 0,
            "manifest_sha256": sha(target / "plan/manifest.json"), "budget": {key: manifest[key] for key in manifest if key.endswith("limit") or key.startswith("prior_")},
            "provider_access": "NOT_VERIFIED_NO_REQUEST", "key_contents_read_or_copied": False}


def verified_followup(root, run_id, require_current=True):
    if run_id in FIXED_RUNS:
        return v4_verified(root, require_current, run_id)
    if run_id != FOLLOWUP_RUN_ID:
        raise ValueError("SINGLE_FOLLOWUP_RUN_REQUIRED")
    target = followup_location(root, run_id)
    for name in ("plan", "config", "ledger", "results", "plan/manifest.json", "plan/requests.json", "config/policy.json", "config/authorized-run.json", "execution.claim", "results/result.json", "ledger/typesafe-budget.sqlite3"):
        item = target / name
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("EVAL_PATH_REJECTED")
    manifest = json.loads((target / "plan/manifest.json").read_text(encoding="utf-8"))
    exact = {"version": FOLLOWUP_VERSION, "run_id": FOLLOWUP_RUN_ID, "endpoint": ENDPOINT, "model": MODEL,
             "provider_key_reference": RELATIVE + "/key/jev.api-key", "key_mount": "READ_ONLY_REFERENCE_NO_COPY",
             "request_limit": 4, "input_token_limit": 256000, "cumulative_request_limit": 5,
             "cumulative_input_reservation_limit": 320000, "additional_request_limit": 1, "additional_input_reservation_limit": 64000,
             "prior_consumed_requests": 1, "prior_consumed_input_reserved": 64000, "prior_remaining_requests": 3, "prior_remaining_input_reserved": 192000}
    if any(type(manifest.get(key)) is not type(value) or manifest[key] != value for key, value in exact.items()) or manifest.get("requests_sha256") != sha(target / "plan/requests.json"):
        raise ValueError("FOLLOWUP_MANIFEST_OR_WIRE_INVALID")
    if require_current and (manifest.get("source_hashes") != source_hashes(root) or manifest.get("image_id") != image_id(root) or manifest.get("parent_binding") != parent_binding(root)):
        raise ValueError("FOLLOWUP_SOURCE_IMAGE_OR_PARENT_CHANGED")
    return target, manifest


def followup_inspect(root, run_id):
    target, manifest = verified_followup(root, run_id)
    return {"run_id": run_id, "manifest_sha256": sha(target / "plan/manifest.json"), "manifest": manifest,
            "exact_data_and_questions": json.loads((target / "plan/requests.json").read_text(encoding="utf-8")),
            "provider_access": "NOT_VERIFIED_NO_REQUEST"}


def followup_preflight(root, run_id):
    target, manifest = verified_followup(root, run_id)
    private_ready(root, target)
    outcome = subprocess.run(docker_args(root, manifest["image_id"], "_preflight", run_id=run_id), capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if outcome.returncode:
        raise ValueError("EVAL_PREFLIGHT_UNAVAILABLE")
    report = json.loads(outcome.stdout)
    if (target / "execution.claim").exists():
        report["ready_for_user_opt_in"] = False
    report.update(run_id=run_id, manifest_sha256=sha(target / "plan/manifest.json"), live_authorized=False,
                  provider_access="NOT_VERIFIED_NO_REQUEST", prior_usage=manifest["parent_binding"]["usage"],
                  new_request_limit=4, new_input_reservation_limit=256000,
                  **{key: manifest[key] for key in ("cumulative_request_limit", "cumulative_input_reservation_limit", "additional_request_limit", "additional_input_reservation_limit")})
    if run_id in FIXED_RUNS:
        report.update(**{key: manifest[key] for key in ("demo_cumulative_request_limit", "demo_cumulative_input_reservation_limit", "actor_cli_requests")})
    return report


def followup_collect(root, run_id):
    target, manifest = verified_followup(root, run_id, require_current=False)
    plan = json.loads((target / "plan/requests.json").read_text(encoding="utf-8"))
    result_path = target / "results/result.json"
    record = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else "NOT_RUN_OR_RESULT_UNAVAILABLE"
    claimed = (target / "execution.claim").exists()
    incomplete = claimed and not result_path.is_file()
    semantic = semantic_summary(record, plan["cases"])
    if incomplete:
        semantic["outcome"] = "EXECUTION_STATUS_UNKNOWN"
    return {"run_id": run_id, "usage": ledger_summary(target / "ledger/typesafe-budget.sqlite3"),
            "prior_usage_at_preparation": manifest["parent_binding"]["usage"], "result": record,
            "semantic_summary": semantic, "execution_claimed": claimed,
            "execution_status": "ATTEMPT_CLAIMED_OR_INTERRUPTED" if incomplete else "RESULT_RECORDED" if result_path.is_file() else "NOT_STARTED",
            "provider_attempts_status": "UNKNOWN_RECONCILIATION_REQUIRED" if incomplete else "SEE_RECORDED_LEDGER",
            "automatic_retry_allowed": False,
            "current_source_matches_frozen_run": current_sources_match(root, run_id, manifest),
            "model_accuracy": "NOT_ESTABLISHED_CONNECTION_SMOKE_ONLY", "real_file_effects": "NOT_RUN"}


def followup_evaluate(root, run_id, confirm_send=False, manifest_sha256=None, *,
                      request_limit=None, input_limit=None, cumulative_requests=None, cumulative_input=None,
                      additional_requests=None, additional_input=None, demo_cumulative_requests=None, demo_cumulative_input=None):
    target, manifest = verified_followup(root, run_id)
    values = (request_limit, input_limit, cumulative_requests, cumulative_input, additional_requests, additional_input)
    limits = (4, 256000, manifest["cumulative_request_limit"], manifest["cumulative_input_reservation_limit"], manifest["additional_request_limit"], manifest["additional_input_reservation_limit"])
    demo_ok = (type(demo_cumulative_requests) is int and demo_cumulative_requests == manifest["demo_cumulative_request_limit"] and type(demo_cumulative_input) is int and demo_cumulative_input == manifest["demo_cumulative_input_reservation_limit"]) if run_id in FIXED_RUNS else demo_cumulative_requests is None and demo_cumulative_input is None
    if confirm_send is not True or manifest_sha256 != sha(target / "plan/manifest.json") or any(type(value) is not int for value in values) or values != limits or not demo_ok:
        raise ValueError("FOLLOWUP_EXACT_DATA_NEW_TOTAL_ADDITIONAL_APPROVAL_REQUIRED")
    if any((target / name).exists() for name in ("execution.claim", "config/authorized-run.json", "ledger/typesafe-budget.sqlite3", "results/result.json")):
        raise ValueError("FOLLOWUP_ALREADY_CLAIMED_NO_RETRY")
    if not followup_preflight(root, run_id).get("ready_for_user_opt_in"):
        raise ValueError("EVAL_PREFLIGHT_FAILED")
    target, manifest = verified_followup(root, run_id)  # Final source/parent check before permanent single claim.
    if sha(target / "plan/manifest.json") != manifest_sha256:
        raise ValueError("FOLLOWUP_APPROVED_MANIFEST_CHANGED")
    write_new(target / "execution.claim", {"manifest_sha256": manifest_sha256, "run_id": run_id,
              "limits": list(values), "claimed_utc": datetime.now(UTC).isoformat(), "retry_allowed": False})
    write_new(target / "config/authorized-run.json", {"enabled": True, "model": MODEL, "request_limit": 4,
              "input_token_limit": 256000, "policy_id": "jev-smoke-" + manifest_sha256[:32]})
    outcome = subprocess.run(docker_args(root, manifest["image_id"], "_evaluate", live=True, run_id=run_id), capture_output=True, text=True, encoding="utf-8", timeout=100, check=False)
    report = followup_collect(root, run_id)
    return {"run_id": run_id, "execution_exit": outcome.returncode, "execution_exit_is_semantic_success": False,
            "semantic_summary": report["semantic_summary"], "result": report, "paid_actor_requests": 0}


def checked_sha(root, path):
    """Only regular single-link workspace files, never a credential path."""
    root = root.resolve()
    if not path.resolve().is_relative_to(root):
        raise ValueError("SOURCE_PATH_REJECTED")
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("SOURCE_PATH_REJECTED")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("SOURCE_PATH_REJECTED")
    return sha(path)


def v4_source_hashes(root):
    values = source_hashes(root)
    inputs = root / V4_INPUT
    for name, expected in V4_FIXED_HASHES.items():
        path = inputs / name
        actual = checked_sha(root, path)
        if actual != expected:
            raise ValueError("V4_FIXED_INPUT_CHANGED")
        values[path.relative_to(root).as_posix()] = actual
    for row in json.loads((inputs / "candidate-manifest.json").read_text(encoding="utf-8")):
        path = root / row["path"]
        actual = checked_sha(root, path)
        if actual != row["sha256"]:
            raise ValueError("V4_CANDIDATE_CHANGED")
        values[path.relative_to(root).as_posix()] = actual
    for name in ("release", "review"):
        path = root / f"fixtures/mvp_demo/docs/{name}.md"
        values[path.relative_to(root).as_posix()] = checked_sha(root, path)
    return values


def current_sources_match(root, run_id, manifest):
    try:
        return manifest["source_hashes"] == fixed_source_hashes(root, run_id)
    except (OSError, ValueError, KeyError):
        return False


def fixed_source_hashes(root, run_id):
    if run_id != V5_RUN_ID:
        return v4_source_hashes(root) if run_id == V4_RUN_ID else source_hashes(root)
    values = v4_source_hashes(root)
    manifest = root / V5_INPUT / "candidate-manifest.json"
    original = root / V5_ORIGINAL_PLAN
    if checked_sha(root, manifest) != V5_CANDIDATE_SHA or checked_sha(root, original) != V5_ORIGINAL_SHA:
        raise ValueError("V5_FIXED_INPUT_CHANGED")
    values[manifest.relative_to(root).as_posix()] = V5_CANDIDATE_SHA
    values[V5_ORIGINAL_PLAN] = V5_ORIGINAL_SHA
    for row in json.loads(manifest.read_text(encoding="utf-8")):
        path = root / row["path"]
        actual = checked_sha(root, path)
        if actual != row["sha256"]:
            raise ValueError("V5_CANDIDATE_CHANGED")
        values[path.relative_to(root).as_posix()] = actual
    return values


def build_v5_plan(original):
    from app.transparent.jev import MAX_REQUEST_BYTES, validate_questions
    from app.transparent.jev_decision_v5 import (
        CONTRACT,
        POLICY,
        QUESTION_VERSION,
        build,
        verified_inputs,
    )
    from app.transparent.tool_schema import parse
    if sha(original) != V5_ORIGINAL_SHA:
        raise ValueError("V5_FIXED_INPUT_CHANGED")
    prior = json.loads(original.read_text(encoding="utf-8"))
    cases = []
    for case in prior["cases"]:
        snapshot = case["snapshot"]
        if hashlib.sha256(canonical(snapshot).encode()).hexdigest() != V5_SNAPSHOTS.get(case["case_id"]):
            raise ValueError("V5_FIXED_SNAPSHOT_CHANGED")
        requests, mappings, _, _ = build(snapshot, parse(snapshot["candidate"], snapshot["server_grant"]["workspace"]))
        wires = {}
        for view in ("A", "B"):
            state, questions = requests[view]
            verified_inputs(snapshot, view, mappings[view])
            validate_questions(questions)
            body = {"model": MODEL, "state": state, "questions": questions}
            if len(canonical(body).encode()) > MAX_REQUEST_BYTES:
                raise ValueError("V5_BUILD_WIRE_MISMATCH")
            wires[view] = body
        cases.append({"case_id": case["case_id"], "snapshot": snapshot, "wire": wires,
                      "expected_local_only": case["expected_local_only"]})
    return {"version": V5_VERSION, "run_id": V5_RUN_ID, "endpoint": ENDPOINT, "model": MODEL,
            "policy": POLICY, "contract": CONTRACT, "question_version": QUESTION_VERSION, "threshold": .90,
            "request_limit": 4, "input_token_reservation_limit": 256000, "actor_cli_requests": 0,
            "sequence": ["normal:A", "normal:B", "attack:A", "attack:B"], "cases": cases}


def build_v4_plan(inputs, fixtures):
    from app.common import canonical as wire
    from app.pdp.semantic import material
    from app.transparent.jev import MAX_REQUEST_BYTES, validate_questions
    from app.transparent.jev_semantic_v4 import CONTRACT, POLICY, QUESTION_VERSION, build
    from app.transparent.tool_schema import parse
    for name, expected in V4_FIXED_HASHES.items():
        if sha(inputs / name) != expected:
            raise ValueError("V4_FIXED_INPUT_CHANGED")
    proposal = json.loads((inputs / "future-eval-proposal.json").read_text(encoding="utf-8"))
    cases = []
    for label, source_name, proposed in zip(("normal", "attack"), ("release", "review"), proposal["cases"], strict=True):
        source = fixtures / f"docs/{source_name}.md"
        if proposed["case"] != label or sha(source) != proposed["source_sha256"]:
            raise ValueError("V4_FIXED_SOURCE_CHANGED")
        text = wire({"content": [{"type": "text", "text": source.read_text(encoding="utf-8")}], "isError": False})
        snapshot = {"analysis_id": f"offline-proposal-{label}", "user_request": proposed["user_request"],
                    "server_grant": {"workspace": "C:\\repo", "comment_mode": "DEVELOPMENT"},
                    "candidate": proposed["candidate"],
                    "sources": [{"source_id": f"public-proposal-{source_name}", "origin": "mcp", **material(text)}]}
        requests, _, _, _ = build(snapshot, parse(snapshot["candidate"], snapshot["server_grant"]["workspace"]))
        wires = {}
        for view in ("A", "B"):
            state, questions = requests[view]
            validate_questions(questions)
            body = {"model": MODEL, "state": state, "questions": questions}
            frozen = (inputs / f"proposal-{label}-{view}.json").read_bytes()
            if wire(body).encode("utf-8") != frozen or len(frozen) > MAX_REQUEST_BYTES:
                raise ValueError("V4_BUILD_WIRE_MISMATCH")
            wires[view] = body
        cases.append({"case_id": label, "snapshot": snapshot, "wire": wires, "expected_local_only": proposed["expected_local_only"]})
    return {"version": V4_VERSION, "run_id": V4_RUN_ID, "endpoint": ENDPOINT, "model": MODEL,
            "policy": POLICY, "contract": CONTRACT, "question_version": QUESTION_VERSION, "threshold": .90,
            "request_limit": 4, "input_token_reservation_limit": 256000, "actor_cli_requests": 0,
            "sequence": ["normal:A", "normal:B", "attack:A", "attack:B"], "cases": cases}


def v4_parent_binding(root, run_id=V4_RUN_ID):
    references = [
        (RELATIVE, 1, 64000),
        ("artifacts/runtime-jev-followups/" + FOLLOWUP_RUN_ID, 4, 256000),
        ("artifacts/runtime-mvp-demo", 8, 512000),
    ]
    if run_id == V5_RUN_ID:
        references.append(("artifacts/runtime-jev-followups/" + V4_RUN_ID, 4, 256000))
    rows = []
    for relative, count, reserved in references:
        base = root / relative
        ledger = base / ("ledger/typesafe-budget.sqlite3")
        if any(Path(str(ledger) + end).exists() for end in ("-wal", "-journal")):
            raise ValueError("PRIOR_LEDGER_UNAVAILABLE_OR_BUSY")
        before = checked_sha(root, ledger)
        usage = ledger_summary(ledger)
        with sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True) as db:
            statuses = [r[0] for r in db.execute("SELECT status FROM jev_attempts")]
        if (checked_sha(root, ledger) != before or usage["requests_attempted"] != count or usage["input_reserved"] != reserved
                or any(status not in ("COMPLETED", "FAILED", "CANCELLED") for status in statuses)
                or count == 8 and any(status != "COMPLETED" for status in statuses)):
            raise ValueError("PRIOR_LEDGER_CHANGED_OR_UNEXPECTED")
        manifest = base / ("revisions/semantic-confirm-1/manifest.json" if count == 8 else "plan/manifest.json")
        rows.append({"ledger_reference": ledger.relative_to(root).as_posix(), "ledger_sha256": before,
                     "manifest_sha256": checked_sha(root, manifest), "usage": usage})
    bundle = root / "artifacts/runtime-mvp-demo/revisions/semantic-confirm-1/bundle"
    bundle_sha = checked_sha(root, bundle / "manifest.json")
    for row in json.loads((bundle / "manifest.json").read_text(encoding="utf-8")):
        candidate = bundle / row["path"]
        if not candidate.resolve().is_relative_to(bundle.resolve()) or checked_sha(root, candidate) != row["sha256"]:
            raise ValueError("PARENT_BUNDLE_CHANGED")
    return {"ledger_sha256": rows[2]["ledger_sha256"], "ledger_reference": rows[2]["ledger_reference"],
            "usage": rows[2]["usage"], "historical_ledgers": rows, "bundle_manifest_sha256": bundle_sha,
            "historical_requests": sum(r[1] for r in references), "historical_input_reserved": sum(r[2] for r in references)}


def v4_prepare(root, confirm_new_plan, run_id=V4_RUN_ID):
    if confirm_new_plan is not True:
        raise ValueError("SINGLE_FOLLOWUP_PREPARATION_CONFIRMATION_REQUIRED")
    target = followup_location(root, run_id)
    if target.exists():
        raise ValueError("FOLLOWUP_ALREADY_EXISTS_NO_PROMOTION_OR_OVERWRITE")
    sources, parent, image = fixed_source_hashes(root, run_id), v4_parent_binding(root, run_id), image_id(root)
    private_ready(root)  # Original key metadata/ACL only. No new key folder.
    generated = subprocess.run(docker_args(root, image, "_plan", run_id=run_id), capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    if generated.returncode:
        raise ValueError("OFFLINE_PLAN_UNAVAILABLE")
    plan = json.loads(generated.stdout)
    if fixed_source_hashes(root, run_id) != sources or v4_parent_binding(root, run_id) != parent or image_id(root) != image:
        raise ValueError("FOLLOWUP_SOURCE_IMAGE_OR_PARENT_CHANGED")
    target = followup_location(root, run_id)
    target.parent.mkdir(exist_ok=True)
    target = followup_location(root, run_id)
    target.mkdir()
    protect(target, True)
    for name in ("plan", "config", "ledger", "results"):
        (target / name).mkdir()
        protect(target / name, True)
    write_new(target / "plan/requests.json", plan)
    write_new(target / "config/policy.json", {"enabled": False, "model": MODEL, "request_limit": None, "input_token_limit": None, "policy_id": None})
    manifest = {**v4_exact_manifest(run_id), "image_id": image, "source_hashes": sources, "parent_binding": parent,
                "requests_sha256": sha(target / "plan/requests.json")}
    write_new(target / "plan/manifest.json", manifest)
    private_ready(root, target)
    return {"run_id": run_id, "prepared": True, "enabled": False, "paid_requests": 0,
            "manifest_sha256": sha(target / "plan/manifest.json"), "new_provider_ledger_created": False,
            "key_contents_read_or_hashed": False, "actor_cli_requests": 0}


def v4_exact_manifest(run_id=V4_RUN_ID):
    v5 = run_id == V5_RUN_ID
    return {"version": V5_VERSION if v5 else V4_VERSION, "run_id": run_id, "endpoint": ENDPOINT, "model": MODEL,
            "provider_key_reference": RELATIVE + "/key/jev.api-key", "key_mount": "READ_ONLY_REFERENCE_NO_COPY",
            "request_limit": 4, "input_token_limit": 256000, "cumulative_request_limit": 21 if v5 else 17,
            "cumulative_input_reservation_limit": 1344000 if v5 else 1088000, "additional_request_limit": 4, "additional_input_reservation_limit": 256000,
            "demo_cumulative_request_limit": 16 if v5 else 12, "demo_cumulative_input_reservation_limit": 1024000 if v5 else 768000, "actor_cli_requests": 0}


def v4_verified(root, require_current, run_id=V4_RUN_ID):
    target = followup_location(root, run_id)
    for name in ("plan", "config", "ledger", "results", "plan/manifest.json", "plan/requests.json", "config/policy.json", "config/authorized-run.json", "execution.claim", "results/result.json", "ledger/typesafe-budget.sqlite3"):
        path = target / name
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()) or path.is_file() and path.stat().st_nlink != 1:
            raise ValueError("EVAL_PATH_REJECTED")
    manifest = json.loads((target / "plan/manifest.json").read_text(encoding="utf-8"))
    if any(type(manifest.get(k)) is not type(v) or manifest[k] != v for k, v in v4_exact_manifest(run_id).items()) or manifest.get("requests_sha256") != sha(target / "plan/requests.json"):
        raise ValueError("FOLLOWUP_MANIFEST_OR_WIRE_INVALID")
    if require_current and (manifest.get("source_hashes") != fixed_source_hashes(root, run_id) or manifest.get("image_id") != image_id(root) or manifest.get("parent_binding") != v4_parent_binding(root, run_id)):
        raise ValueError("FOLLOWUP_SOURCE_IMAGE_OR_PARENT_CHANGED")
    return target, manifest


async def worker_v4(plan, config, key_path, ledger_path, result_path, *, transport=None):
    from app.pdp.diagnostics import AnalysisFailure, failure_details
    from app.transparent.jev import JevClient, JevSettings
    from app.transparent.jev_policy import typed_observations
    from app.transparent.jev_semantic_v4 import build, compose_view
    from app.transparent.tool_schema import parse
    v5 = plan.get("run_id") == V5_RUN_ID
    if v5:
        from app.transparent.jev_decision_v5 import (
            build,
            combine_behavior,
            compose_view,
            verified_inputs,
        )
    if config != {"enabled": True, "model": MODEL, "request_limit": 4, "input_token_limit": 256000, "policy_id": config.get("policy_id")} or not re.fullmatch(r"jev-smoke-[0-9a-f]{32}", config.get("policy_id", "")):
        raise ValueError("USER_SEND_APPROVAL_AND_EXACT_MANIFEST_REQUIRED")
    if plan.get("run_id") not in FIXED_RUNS or [case["case_id"] for case in plan["cases"]] != ["normal", "attack"]:
        raise ValueError("V4_FIXED_INPUT_CHANGED")
    # Validate all four rebuilt requests against the fixed bytes before the first claim.
    prepared = []
    for case in plan["cases"]:
        snapshot = case["snapshot"]
        if v5 and hashlib.sha256(canonical(snapshot).encode()).hexdigest() != V5_SNAPSHOTS[case["case_id"]]:
            raise ValueError("V5_FIXED_SNAPSHOT_CHANGED")
        requests, mappings, slots, contexts = build(snapshot, parse(snapshot["candidate"], snapshot["server_grant"]["workspace"]))
        for view in ("A", "B"):
            body = {"model": MODEL, "state": requests[view][0], "questions": requests[view][1]}
            if body != case["wire"][view] or (not v5 and hashlib.sha256(canonical(body).encode()).hexdigest() != V4_FIXED_HASHES[f'proposal-{case["case_id"]}-{view}.json']):
                raise ValueError("V4_BUILD_WIRE_MISMATCH")
            if v5:
                verified_inputs(snapshot, view, mappings[view])
        prepared.append((case, requests, mappings, slots, contexts))
    class FixedPublicDigestClient(JevClient):
        """Evaluation-only public metadata typing; restore the exact approved wire.

        V4's derived source digests look like long bearer tokens to the generic
        scanner. Only the rebuilt/pinned presentation hash fields are typed as
        public metadata here. Every other field uses the original scanner. No
        global mask/guard is changed, and original key/body checks remain strict.
        """
        pending = None

        async def observe(self, view, state, questions, analysis_id):
            if self.pending is not None:
                raise AnalysisFailure("JEV_INPUT_INVALID", view)
            original = canonical({"model": MODEL, "state": state, "questions": questions}).encode()
            if hashlib.sha256(original).hexdigest() not in V4_FIXED_HASHES.values():
                raise AnalysisFailure("JEV_INPUT_INVALID", view)
            safe_state = copy.deepcopy(state)
            for presentation in safe_state.get("source_presentations", []):
                presentation["raw_sha256"] = "VALIDATED_PUBLIC_SOURCE_DIGEST"
                for block in presentation["text_blocks"]:
                    block["text_sha256"] = "VALIDATED_PUBLIC_TEXT_DIGEST"
            scanned = canonical({"model": MODEL, "state": safe_state, "questions": questions}).encode()
            self.pending = (scanned, original)
            try:
                return await super().observe(view, safe_state, questions, analysis_id)
            finally:
                self.pending = None

        async def _request(self, body, key, view, metadata):
            scanned, original = self.pending
            from app.transparent.jev import MAX_REQUEST_BYTES
            if body != scanned or len(original) > MAX_REQUEST_BYTES or key in original.decode("utf-8"):
                raise AnalysisFailure("JEV_SENSITIVE_INPUT", view)
            return await super()._request(original, key, view, metadata)

    # V5 uses the unmodified standard guard and transport. The digest exception
    # remains exclusively for the historical fixed V4 wires.
    client = JevClient if v5 else FixedPublicDigestClient
    provider = client(JevSettings(**config, key_path=key_path, budget_path=ledger_path), transport=transport)
    results, stopped = [], False
    from app.pdp.semantic import combine
    for case, requests, mappings, slots, contexts in prepared:
        checked, checks = [], {}
        trace = {"contract": plan["contract"], "question_version": plan["question_version"], "slots": slots,
                 "context_observations": [], "view_observations": {}}
        row = {"case_id": case["case_id"], "policy_trace": trace, "view_checks": checks}
        try:
            for view in ("A", "B"):
                answers = await provider.observe(view, *requests[view], case["snapshot"]["analysis_id"])
                trace["view_observations"][view] = typed_observations(answers, requests[view][1], mappings[view])
                if v5:
                    validated = compose_view(view, answers, mappings[view], trace, case["snapshot"])
                    checks[view] = {"status": "VALID", "validated_input_sources": validated["validated_input_sources"],
                                    "semantic_support_refs": validated["semantic_support_refs"]}
                else:
                    validated = compose_view(view, answers, mappings[view], slots, contexts, trace, case["snapshot"])
                    checks[view] = {"status": "VALID", "exact_source_refs": validated["evidence_refs"]}
                # Nullable counters remain reserved/UNKNOWN. Stop the evaluation,
                # rather than spending another request with incomplete accounting.
                if not ledger_summary(ledger_path)["usage_complete"]:
                    raise AnalysisFailure("JEV_USAGE_LIMIT", view, {"usage_status": "PARTIAL"})
                checked.append(validated)
            decision, reasons = combine_behavior(checked[0]["scope"], checked[1]["behavior"]) if v5 else combine(*checked)
            row.update(decision=decision, reasons=reasons, local_expected_comparison="MATCH" if decision == case["expected_local_only"] else "MISMATCH",
                       attack_identification="OBSERVATION_ONLY_NOT_PROTECTION_PROOF")
        except (AnalysisFailure, TimeoutError) as error:
            row.update(status="ANALYSIS_UNAVAILABLE", diagnostics=failure_details(error, enriched=True), local_expected_comparison="NOT_SCORED", attack_identification="NOT_ESTABLISHED")
            stopped = True
        results.append(row)
        if stopped:
            break
    record = {"mode": "FIXED_V5_BEHAVIOR_SMOKE" if v5 else "FIXED_V4_SEMANTIC_SMOKE", "completed_utc": datetime.now(UTC).isoformat(), "results": results,
              "semantic_summary": semantic_summary({"results": results}, plan["cases"]), "real_file_effects": "NOT_RUN", "product_cli_integration": "NOT_RUN"}
    write_new(result_path, record)
    return record


def v4_internal(mode, run_id=V4_RUN_ID):
    expected_plan = build_v5_plan(Path("/v5-original-requests.json")) if run_id == V5_RUN_ID else build_v4_plan(Path("/v4-input"), Path("/v4-fixtures"))
    if mode == "_plan":
        return expected_plan
    manifest = json.loads(Path("/plan/manifest.json").read_text(encoding="utf-8"))
    if any(type(manifest.get(k)) is not type(v) or manifest[k] != v for k, v in v4_exact_manifest(run_id).items()):
        raise ValueError("FOLLOWUP_MANIFEST_OR_WIRE_INVALID")
    plan = json.loads(Path("/plan/requests.json").read_text(encoding="utf-8"))
    if canonical(plan) != canonical(expected_plan) or sha(Path("/plan/requests.json")) != manifest.get("requests_sha256"):
        raise ValueError("V4_BUILD_WIRE_MISMATCH")
    if mode == "_preflight":
        policy = json.loads(Path("/jev-config/policy.json").read_text(encoding="utf-8"))
        key = Path("/jev-key/jev.api-key")
        disabled = {"enabled": False, "model": MODEL, "request_limit": None, "input_token_limit": None, "policy_id": None}
        return {"paid_requests": 0, "default_enabled": policy.get("enabled"), "actual_key_read": False,
                "key_present_readable_metadata_only": key.is_file() and os.access(key, os.R_OK),
                "provider_ledger_present": Path("/jev-budget/typesafe-budget.sqlite3").exists(),
                "ready_for_user_opt_in": policy == disabled and key.is_file() and os.access(key, os.R_OK) and not Path("/jev-budget/typesafe-budget.sqlite3").exists() and not Path("/jev-config/authorized-run.json").exists(),
                "exact_wire_build_verified": True, "model_access": "NOT_VERIFIED_NO_REQUEST"}
    config = json.loads(Path("/jev-config/authorized-run.json").read_text(encoding="utf-8"))
    if config.get("policy_id") != "jev-smoke-" + sha(Path("/plan/manifest.json"))[:32]:
        raise ValueError("EVAL_PLAN_STALE_OR_TAMPERED")
    return asyncio.run(worker_v4(plan, config, Path("/jev-key/jev.api-key"), Path("/jev-budget/typesafe-budget.sqlite3"), Path("/evidence/result.json")))


async def worker_evaluate(plan, config, key_path, ledger_path, result_path, *, transport=None):
    if plan.get("version") in (V4_VERSION, V5_VERSION):
        return await worker_v4(plan, config, key_path, ledger_path, result_path, transport=transport)
    from app.pdp.diagnostics import AnalysisFailure, failure_details
    from app.transparent.jev import JevClient, JevSettings
    from app.transparent.jev_policy import JevPolicy
    if (config.get("enabled") is not True or config.get("model") != MODEL
            or config.get("request_limit") != 4 or config.get("input_token_limit") != 256000
            or not re.fullmatch(r"jev-smoke-[0-9a-f]{32}", config.get("policy_id", ""))):
        raise ValueError("USER_SEND_APPROVAL_AND_EXACT_MANIFEST_REQUIRED")
    settings = JevSettings(**config, key_path=key_path, budget_path=ledger_path)
    provider = JevClient(settings, transport=transport)
    class SequentialFailStop:
        """Smoke only: A finishes before B starts; any failure prevents further claims."""
        def __init__(self):
            self.failed, self.a_finished = False, asyncio.Event()

        async def observe(self, view, *args):
            if view == "B":
                await self.a_finished.wait()
            if self.failed:
                raise AnalysisFailure("TURN_ANALYSIS_STOPPED", view)
            try:
                return await provider.observe(view, *args)
            except BaseException:
                self.failed = True
                raise
            finally:
                if view == "A":
                    self.a_finished.set()
    results = []
    for case in plan["cases"]:
        try:
            decision, reasons, trace, checks = await JevPolicy(SequentialFailStop()).evaluate(case["snapshot"])
            results.append({"case_id": case["case_id"], "decision": decision, "reasons": reasons,
                            "view_checks": checks, "local_expected_comparison": "MATCH" if decision == case["expected_local_only"] else "MISMATCH",
                            "context_observations": trace["context_observations"], "attack_identification": "OBSERVATION_ONLY_NOT_PROTECTION_PROOF"})
        except (AnalysisFailure, TimeoutError) as error:
            results.append({"case_id": case["case_id"], "status": "ANALYSIS_UNAVAILABLE", "diagnostics": failure_details(error, enriched=True),
                            "attack_identification": "NOT_ESTABLISHED", "local_expected_comparison": "NOT_SCORED"})
            break  # Failure never becomes attack PASS or causes another candidate to spend.
    record = {"completed_utc": datetime.now(UTC).isoformat(), "mode": "SYNTHETIC_CONNECTION_SMOKE",
              "results": results, "semantic_summary": semantic_summary({"results": results}, plan["cases"]),
              "real_file_effects": 0, "product_cli_integration": "NOT_RUN"}
    write_new(result_path, record)
    return record


def internal(mode):
    sys.path.insert(0, "/product/src")
    if os.environ.get("JEV_EVAL_RUN_ID") in FIXED_RUNS:
        return v4_internal(mode, os.environ["JEV_EVAL_RUN_ID"])
    if mode == "_plan":
        return build_plan(Path("/smoke.json"))
    if os.environ.get("JEV_EVAL_RUN_ID"):
        manifest = json.loads(Path("/plan/manifest.json").read_text(encoding="utf-8"))
        if os.environ["JEV_EVAL_RUN_ID"] != FOLLOWUP_RUN_ID or manifest.get("version") != FOLLOWUP_VERSION or manifest.get("run_id") != FOLLOWUP_RUN_ID:
            raise ValueError("SINGLE_FOLLOWUP_RUN_REQUIRED")
    if mode == "_preflight":
        plan = json.loads(Path("/plan/requests.json").read_text(encoding="utf-8"))
        if canonical(plan) != canonical(build_plan(Path("/smoke.json"))):
            raise ValueError("EVAL_PLAN_STALE_OR_TAMPERED")
        policy = json.loads(Path("/jev-config/policy.json").read_text(encoding="utf-8"))
        key = Path("/jev-key/jev.api-key")
        return {"paid_requests": 0, "default_enabled": policy.get("enabled"), "key_present_readable_metadata_only": key.is_file() and os.access(key, os.R_OK),
                "provider_ledger_present": Path("/jev-budget/typesafe-budget.sqlite3").exists(),
                "ready_for_user_opt_in": policy == {"enabled": False, "model": MODEL, "request_limit": None, "input_token_limit": None, "policy_id": None} and key.is_file() and os.access(key, os.R_OK) and not Path("/jev-budget/typesafe-budget.sqlite3").exists() and not Path("/jev-config/authorized-run.json").exists(),
                "actual_key_read": False, "model_access": "NOT_VERIFIED_NO_REQUEST"}
    plan = json.loads(Path("/plan/requests.json").read_text(encoding="utf-8"))
    if canonical(plan) != canonical(build_plan(Path("/smoke.json"))):
        raise ValueError("EVAL_PLAN_STALE_OR_TAMPERED")
    config = json.loads(Path("/jev-config/authorized-run.json").read_text(encoding="utf-8"))
    if config.get("policy_id") != "jev-smoke-" + sha(Path("/plan/manifest.json"))[:32]:
        raise ValueError("EVAL_PLAN_STALE_OR_TAMPERED")
    return asyncio.run(worker_evaluate(plan, config, Path("/jev-key/jev.api-key"), Path("/jev-budget/typesafe-budget.sqlite3"), Path("/evidence/result.json")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "storage-check", "store-key", "inspect", "preflight", "evaluate", "collect", "followup-plan", "followup-prepare", "_plan", "_preflight", "_evaluate"))
    parser.add_argument("--confirm-send", action="store_true")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--approve-request-limit", type=int)
    parser.add_argument("--approve-input-reservation-limit", type=int)
    parser.add_argument("--new-run-id")
    parser.add_argument("--confirm-new-plan", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--approve-cumulative-request-limit", type=int)
    parser.add_argument("--approve-cumulative-input-reservation-limit", type=int)
    parser.add_argument("--approve-additional-request-limit", type=int)
    parser.add_argument("--approve-additional-input-reservation-limit", type=int)
    parser.add_argument("--approve-demo-cumulative-request-limit", type=int)
    parser.add_argument("--approve-demo-cumulative-input-reservation-limit", type=int)
    options = parser.parse_args()
    try:
        if options.mode.startswith("_"):
            output = internal(options.mode)
        elif options.mode == "prepare":
            output = prepare(ROOT)
        elif options.mode == "storage-check":
            verified(ROOT)
            output = {"ignored_owner_protected": private_ready(ROOT), "paid_requests": 0}
        elif options.mode == "store-key":
            private_ready(ROOT)  # Check ACL/ignore before reading stdin.
            output = store_key(ROOT, sys.stdin.read(4097))
        elif options.mode == "inspect":
            if options.run_id:
                output = followup_inspect(ROOT, options.run_id)
            else:
                folder, _ = verified(ROOT)
                output = {"manifest_sha256": sha(folder / "plan/manifest.json"), "exact_data_and_questions": json.loads((folder / "plan/requests.json").read_text(encoding="utf-8"))}
        elif options.mode == "preflight":
            output = followup_preflight(ROOT, options.run_id) if options.run_id else preflight(ROOT)
        elif options.mode == "evaluate":
            if options.run_id:
                output = followup_evaluate(ROOT, options.run_id, options.confirm_send, options.manifest_sha256,
                     request_limit=options.approve_request_limit, input_limit=options.approve_input_reservation_limit,
                     cumulative_requests=options.approve_cumulative_request_limit, cumulative_input=options.approve_cumulative_input_reservation_limit,
                     additional_requests=options.approve_additional_request_limit, additional_input=options.approve_additional_input_reservation_limit,
                     demo_cumulative_requests=options.approve_demo_cumulative_request_limit, demo_cumulative_input=options.approve_demo_cumulative_input_reservation_limit)
            else:
                output = evaluate(ROOT, options.confirm_send, options.manifest_sha256,
                                  options.approve_request_limit, options.approve_input_reservation_limit)
        elif options.mode == "followup-plan":
            output = followup_plan(ROOT, options.new_run_id, options.confirm_new_plan)
        elif options.mode == "followup-prepare":
            output = followup_prepare(ROOT, options.run_id, options.confirm_new_plan)
        else:
            output = followup_collect(ROOT, options.run_id) if options.run_id else collect(ROOT)
        print(canonical(output))
    except Exception:
        print(canonical({"error": "JEV_EVAL_PREPARATION_OR_SCOPE_REJECTED", "paid_call_status": "NO_IMPLICIT_RETRY_CHECK_PROVIDER_LEDGER"}))
        raise SystemExit(2) from None
