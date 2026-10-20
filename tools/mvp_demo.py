"""Isolated, opt-in CLI demo. Preparation/check never starts a paid actor/judge.

Only start, invoked explicitly by the human, may enable the separate 8-request
allowance and open one of two CLI episodes. Existing provider key is metadata-only
on the host and mounted read-only for Control. No old DB/key/config is replaced.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import ssl
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RELATIVE = "artifacts/runtime-mvp-demo"
VERSION = "mvp-demo-1"
REVISION = "host-wait-1"
REVISION_VERSION = "mvp-demo-host-wait-1"
PARENT_SHA = "454466abc92df12740a8ce9e16837ddc88f85dbbcf85a473d522077a1278ed05"
INTERACTIVE_WALL = 1800
REQUEST_LIMIT, INPUT_LIMIT, EPISODE_LIMIT = 8, 512000, 2
EPISODE_START = 1
CONTROL_URL, GATEWAY_URL = "https://127.0.0.1:8034", "https://127.0.0.1:8044/mcp"
DECISION_POLICY = "hookgw-2026-10-16-jev-v2"
POLICY_ID = "mvp-demo-1"
MODEL = "jev-1.13.0"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
GATEWAY = "cr.agentgateway.dev/agentgateway@sha256:9d3e6044ddcdc0878b1787f77bd401252b95e22684203fb5e874c4c42d2ed90c"
REPORTS = ("reports/normal.md", "reports/review.md")
ROOT = Path(__file__).resolve().parents[1]


def helper(root, name):
    path = safe_path(root, Path("tools") / (name + ".py"))
    spec = importlib.util.spec_from_file_location("demo_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def safe_path(root, relative, must_exist=True):
    root = root.resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError("DEMO_PATH_REJECTED")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ValueError("DEMO_PATH_REJECTED")
    if must_exist and not path.exists():
        raise ValueError("DEMO_NOT_PREPARED")
    if path.is_file() and (not stat.S_ISREG(path.stat().st_mode) or path.stat().st_nlink != 1):
        raise ValueError("DEMO_PATH_REJECTED")
    return path


def runtime(root):
    return safe_path(root, RELATIVE, False)


def revision_path(root):
    return safe_path(root, f"{RELATIVE}/revisions/{REVISION}", False)


def active_revision(root):
    return (revision_path(root) / "manifest.json").is_file()


def manifest_path(root):
    return revision_path(root) / "manifest.json" if active_revision(root) else runtime(root) / "manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical(value) + "\n")


def sources(root):
    paths = [*sorted((root / "src/app").rglob("*.py")), *sorted((root / "docs/mvp/contracts").rglob("*.json")),
             *sorted((root / "fixtures/mvp_demo").rglob("*.md")), root / "compose.mvp-demo.yaml",
             root / "agentgateway/config.yaml", root / "tools/mvp_demo.py", root / "scripts/mvp_demo.ps1",
             *(root / "tools" / (name + ".py") for name in ("prepare_tls", "hookgw_launch", "hookgw_hook", "hookgw_mcp", "hookgw_mcp_probe", "hookgw_bundle", "jev_eval"))]
    if (root / "tools/mvp_demo_viewer.py").is_file():
        paths.append(root / "tools/mvp_demo_viewer.py")
    for name in ("tools/mvp_demo_lifecycle.py", "tools/mvp_demo_hook.py", "tools/mvp_demo_mcp.py", "compose.mvp-demo.host-wait-1.yaml"):
        if (root / name).is_file():
            paths.append(root / name)
    return {p.relative_to(root).as_posix(): sha(safe_path(root, p.relative_to(root))) for p in paths}


def command(args, timeout=30, env=None):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          env=env, check=False)


def docker(root):
    return helper(root, "jev_eval").trusted_docker(root)


def image_id(root):
    return helper(root, "jev_eval").image_id(root)


def compose(root, args, image=None, timeout=60):
    env = {**os.environ, "MVP_DEMO_IMAGE": image or verified(root)["image"]}
    files = ["-f", str(root / "compose.mvp-demo.yaml")]
    if active_revision(root):
        files += ["-f", str(root / "compose.mvp-demo.host-wait-1.yaml")]
    result = command([docker(root), "compose", *files, *args], timeout, env)
    if result.returncode:
        raise ValueError("DEMO_COMPOSE_FAILED")
    return result.stdout


def key_metadata(root):
    # Never open or hash this role key. Existing protection/ignore check is metadata only.
    eval_helper = helper(root, "jev_eval")
    eval_helper.private_ready(root)
    path = safe_path(root, "artifacts/runtime-jev-eval/key/jev.api-key")
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("DEMO_TYPESAFE_KEY_MISSING")
    return {"reference": "artifacts/runtime-jev-eval/key/jev.api-key", "read_only_mount": True,
            "host_body_read": False, "host_hash_read": False, "model_access": "NOT_VERIFIED_NO_REQUEST"}


def prepare(root, extra=None):
    root = root.resolve()
    target = runtime(root)
    if target.exists():
        raise ValueError("DEMO_EXISTS_PRESERVED_USE_CHECK")
    key = key_metadata(root)
    image = image_id(root)
    selected_sources = sources(root)
    protect = helper(root, "jev_eval").protect
    target.mkdir(mode=0o700)
    protect(target, True)
    for name in ("control", "gateway", "upstream", "host", "config", "ledger", "control-data", "upstream-data", "workspace", "episodes", "reports"):
        (target / name).mkdir(mode=0o700)
    result = command([docker(root), "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
                      "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--tmpfs", "/tmp:size=64m",
                      "--mount", f"type=bind,source={root / 'tools/prepare_tls.py'},target=/prepare.py,readonly",
                      "--mount", f"type=bind,source={target},target=/output", image, "python", "-c",
                      "import runpy;from pathlib import Path;runpy.run_path('/prepare.py')['generate'](Path('/output/pki'), [('upstream',['upstream'])])"], 90)
    if result.returncode:
        raise ValueError("DEMO_NEW_PKI_FAILED_PRESERVED")
    pki = target / "pki"
    for role, names in {"control": ("ca.pem", "control.pem", "control.key", "storage.key", "human.token"),
                        "gateway": ("ca.pem", "gateway.pem", "gateway.key", "gateway-client.pem", "gateway-client.key"),
                        "upstream": ("ca.pem", "upstream.pem", "upstream.key"), "host": ("ca.pem", "human.token")}.items():
        for name in names:
            shutil.copyfile(pki / name, target / role / name)
    for name, roles in (("machine.token", ("control", "host")), ("machine.id", ("control", "host")),
                        ("forward.key", ("control", "upstream"))):
        value = secrets.token_urlsafe(48)
        for role in roles:
            (target / role / name).write_text(value, encoding="ascii")
    (target / "control/judge.api-key").write_text("DEMO-OPENAI-JUDGE-DISABLED", encoding="ascii")
    workspace = target / "workspace"
    shutil.copytree(root / "fixtures/mvp_demo", workspace, dirs_exist_ok=True)
    (workspace / "reports").mkdir()
    grant = {"workspace": str(workspace.resolve()), "demo_scope": "SYNTHETIC_REGISTERED_MCP", "tools": {"native": ["Bash", "apply_patch"], "mcp": ["read_file", "write_file"]},
             "protected_markers": [".codex", ".aws", ".env", ".git/", "../", "artifacts/"]}
    write_new(target / "control/grant.json", grant)
    write_new(target / "host/profile.json", {"workspace": grant["workspace"], "control_url": CONTROL_URL, "gateway_url": GATEWAY_URL})
    write_new(target / "config/policy.json", policy(False))
    bundle = target / "bundle"
    bundle.mkdir()
    rows = []
    for name, source in helper(root, "hookgw_bundle").source_files(root).items():
        safe_path(root, source.relative_to(root))
        destination = bundle / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        rows.append({"path": name, "sha256": sha(destination)})
    write_new(bundle / "manifest.json", rows)
    manifest = {"version": VERSION, "image": image, "gateway_image": GATEWAY, "source_hashes": selected_sources,
                "runtime_binding": {name: sha(target / name) for name in ("control/grant.json", "host/profile.json")},
                "bundle_sha256": sha(bundle / "manifest.json"), "endpoint": ENDPOINT, "model": MODEL,
                "limits": {"requests": REQUEST_LIMIT, "input_reservation": INPUT_LIMIT, "actor_episodes": EPISODE_LIMIT, "episode_seconds": 180},
                "key": key, "workspace": "workspace", "scope": "ENROLLED_SYNTHETIC_FILES_ONLY",
                "live_default": "DISABLED", "actor_endpoint": "https://api.openai.com/v1/responses",
                "actor_cost": "SEPARATE_UNKNOWN_NOT_FIXED", "retained_prior_attempts": 5,
                "prior_usage": "FIRST_UNKNOWN_PLUS_FOLLOWUP_COMPLETED_RETAINED_NOT_REFUNDED",
                "source_documents": {p.relative_to(workspace).as_posix(): sha(p) for p in (workspace / "docs").glob("*.md")}}
    manifest.update(extra or {})
    write_new(target / "manifest.json", manifest)
    for item in target.rglob("*"):
        if item.is_file():
            protect(item)
    # Directories bind-mounted writable must permit the configured container uid.
    # Windows Docker shares use host ACLs; on Linux require host uid 10001.
    compose(root, ["up", "-d", "--no-build", "--pull", "never"], image, 90)
    return {"mode": "PREPARED_DISABLED", "manifest_sha256": sha(target / "manifest.json"), "paid_requests": 0,
            "next": "check; inspect exact materials/limits; human-only start", "old_runtime_changed": False}


def policy(enabled):
    return {"enabled": enabled, "model": MODEL, "request_limit": REQUEST_LIMIT, "input_token_limit": INPUT_LIMIT, "policy_id": POLICY_ID}


def verify_bundle(root, bundle, expected):
    manifest_file = safe_path(root, (bundle / "manifest.json").relative_to(root))
    if sha(manifest_file) != expected:
        raise ValueError("DEMO_BUNDLE_INVALID")
    rows = json.loads(manifest_file.read_text(encoding="utf-8"))
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    if actual != {"manifest.json", *(row["path"] for row in rows)}:
        raise ValueError("DEMO_BUNDLE_INVALID")
    for row in rows:
        if sha(safe_path(bundle, row["path"])) != row["sha256"]:
            raise ValueError("DEMO_BUNDLE_INVALID")


def parent_verified(root):
    target = runtime(root)
    manifest = json.loads(safe_path(root, f"{RELATIVE}/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("version") != VERSION or manifest.get("endpoint") != ENDPOINT or manifest.get("model") != MODEL or manifest.get("gateway_image") != GATEWAY:
        raise ValueError("DEMO_MANIFEST_INVALID")
    if manifest.get("limits") != {"requests": REQUEST_LIMIT, "input_reservation": INPUT_LIMIT, "actor_episodes": EPISODE_LIMIT, "episode_seconds": 180}:
        raise ValueError("DEMO_LIMITS_INVALID")
    verify_bundle(root, target / "bundle", manifest["bundle_sha256"])
    return manifest


def verified(root, current=True):
    parent = parent_verified(root)
    if not active_revision(root):
        manifest = parent
    else:
        path = safe_path(root, manifest_path(root).relative_to(root))
        manifest = json.loads(path.read_text(encoding="utf-8"))
        exact = {"version": REVISION_VERSION, "revision": REVISION, "parent_manifest_sha256": PARENT_SHA,
                 "limits": {"requests": 8, "input_reservation": 512000, "actor_episodes": 2, "episode_seconds": INTERACTIVE_WALL},
                 "dispatch": "post_host_approval_v1", "endpoint": ENDPOINT, "model": MODEL, "gateway_image": GATEWAY,
                 "remaining_at_revision": 1, "episode_claims_at_revision": 1, "budget_action": "REUSE_NO_RESET_OR_NEW_ALLOWANCE"}
        if any(type(manifest.get(k)) is not type(v) or manifest[k] != v for k, v in exact.items()):
            raise ValueError("DEMO_REVISION_INVALID")
        if sha(runtime(root) / "manifest.json") != PARENT_SHA or sha(safe_path(root, f"{RELATIVE}/episodes/episode-1.claim")) != manifest["parent_episode_1_sha256"]:
            raise ValueError("DEMO_REVISION_PARENT_CHANGED")
        if sha(safe_path(root, f"{RELATIVE}/revisions/{REVISION}/parent-manifest.json")) != PARENT_SHA:
            raise ValueError("DEMO_REVISION_PARENT_CHANGED")
        if manifest["image"] != parent["image"] or manifest["source_documents"] != parent["source_documents"] or manifest["key"] != parent["key"]:
            raise ValueError("DEMO_REVISION_SCOPE_CHANGED")
        verify_bundle(root, revision_path(root) / "bundle", manifest["bundle_sha256"])
    if current and (manifest["source_hashes"] != sources(root) or manifest["image"] != image_id(root)):
        raise ValueError("DEMO_SOURCE_IMAGE_DRIFT_PREPARED_RUN_PRESERVED")
    return manifest


def revise(root, revision=None, confirm_revision=False):
    if revision != REVISION or confirm_revision is not True:
        raise ValueError("DEMO_REVISION_EXPLICIT_PREPARATION_REQUIRED")
    parent = parent_verified(root)
    target, new = runtime(root), revision_path(root)
    if new.exists():
        raise ValueError("DEMO_REVISION_EXISTS_PRESERVED")
    if sha(target / "manifest.json") != PARENT_SHA or episode_count(root) != 1 or not (target / "episodes/episode-1.claim").is_file():
        raise ValueError("DEMO_REVISION_PARENT_BASELINE_REQUIRED")
    if provider_summary(root).get("requests_attempted", 0) != 0:
        raise ValueError("DEMO_REVISION_PROVIDER_BASELINE_CHANGED")
    if parent["image"] != image_id(root):
        raise ValueError("DEMO_REVISION_IMAGE_CHANGED")
    for name in ("tools/mvp_demo_lifecycle.py", "tools/mvp_demo_hook.py", "tools/mvp_demo_mcp.py", "compose.mvp-demo.host-wait-1.yaml"):
        safe_path(root, name)
    original_sha = sha(target / "manifest.json")
    claim_sha = sha(safe_path(root, f"{RELATIVE}/episodes/episode-1.claim"))
    new.mkdir(parents=True, mode=0o700)
    shutil.copyfile(target / "manifest.json", new / "parent-manifest.json")
    bundle = new / "bundle"
    bundle.mkdir()
    rows = []
    for name, source in helper(root, "hookgw_bundle").source_files(root).items():
        safe_path(root, source.relative_to(root))
        destination = bundle / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        rows.append({"path": name, "sha256": sha(destination)})
    write_new(bundle / "manifest.json", rows)
    manifest = {**parent, "version": REVISION_VERSION, "revision": REVISION, "parent_manifest_sha256": original_sha,
                "parent_episode_1_sha256": claim_sha, "limits": {"requests": 8, "input_reservation": 512000, "actor_episodes": 2, "episode_seconds": INTERACTIVE_WALL},
                "source_hashes": sources(root), "bundle_sha256": sha(bundle / "manifest.json"), "dispatch": "post_host_approval_v1",
                "remaining_at_revision": 1, "episode_claims_at_revision": 1, "budget_action": "REUSE_NO_RESET_OR_NEW_ALLOWANCE",
                "interactive_wait": "HUMAN_AND_EXECUTION_COMBINED_NOT_SEPARABLE", "old_wall_seconds": 180,
                "compose_override": "compose.mvp-demo.host-wait-1.yaml"}
    write_new(new / "manifest.json", manifest)
    verified(root)
    compose(root, ["up", "-d", "--no-build", "--pull", "never", "--force-recreate", "control", "upstream"], parent["image"], 90)
    return {"revision": REVISION, "manifest_sha256": sha(new / "manifest.json"), "paid_requests": 0,
            "wall_proposal_seconds": INTERACTIVE_WALL, "remaining_episode_claims": 1, "budget_reset": False, "old_manifest_preserved": True}


def read_local(host, endpoint, human=False):
    profile = json.loads((host / "profile.json").read_text(encoding="utf-8"))
    if profile["control_url"] != CONTROL_URL or profile["gateway_url"] != GATEWAY_URL:
        raise ValueError("DEMO_ENDPOINT_INVALID")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                        urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(host / "ca.pem"))))
    headers = {"Authorization": "Bearer " + (host / "human.token").read_text(encoding="ascii").strip()} if human else {}
    with opener.open(urllib.request.Request(profile["control_url"] + endpoint, headers=headers), timeout=8) as response:
        raw = response.read(131073)
    if len(raw) > 131072:
        raise ValueError("DEMO_RESPONSE_LIMIT")
    return json.loads(raw)


def provider_summary(root):
    path = runtime(root) / "ledger/typesafe-budget.sqlite3"
    if not path.exists():
        return {"attempts": 0, "input_reserved": 0, "status": "NO_LEDGER_CREATED"}
    safe_path(root, f"{RELATIVE}/ledger/typesafe-budget.sqlite3")
    summary = helper(root, "jev_eval").ledger_summary(path)
    return summary


def episode_count(root):
    return sum((runtime(root) / "episodes" / f"episode-{i}.claim").exists() for i in range(EPISODE_START, EPISODE_START + EPISODE_LIMIT))


def cli_flags(root, model):
    target = runtime(root)
    launcher = helper(root, "hookgw_launch")
    # Demo-only isolation from ancestor development AGENTS/harness. This does
    # not change sandbox, approvals, hooks, provenance or the PDP boundary.
    values = launcher.overrides(root, target / "host", sys.executable)
    if active_revision(root):
        values = [v.replace("hookgw_hook.py", "mvp_demo_hook.py") if v.startswith("hooks.") else
                  v.replace("hookgw_mcp.py", "mvp_demo_mcp.py") if v.startswith("mcp_servers.with_human.args=") else v for v in values]
    context = ["-c", "project_doc_max_bytes=0"]
    if active_revision(root):
        context += ["-c", "skills.config=[{path=" + json.dumps(str(root / ".agents/skills/with-human-dev/SKILL.md")) + ",enabled=false}]"]
    return values + launcher.api_overrides(model) + context + launcher.manual_review_overrides()


def inspect_demo(root):
    manifest = verified(root)
    target = runtime(root)
    return {"manifest_sha256": sha(manifest_path(root)), "manifest": manifest,
            "documents": {name: safe_path(target / "workspace", name).read_text(encoding="utf-8") for name in manifest["source_documents"]},
            "questions": {"source": "src/app/transparent/jev_policy.py", "source_sha256": manifest["source_hashes"]["src/app/transparent/jev_policy.py"],
                          "dynamic_candidate_scope": "Actual human requests/candidates and successful tool sources, bounded/masked by Control; no groundtruth."},
            "paid_requests": 0}


def check(root, exe=None, model=None, cli=True):
    manifest = verified(root)
    target = runtime(root)
    issues = []
    report = {"mode": "NO_MODEL_CHECK", "paid_requests": 0, "issues": issues, "manifest_sha256": sha(manifest_path(root)),
              "actor_key_present": bool(os.environ.get("OPENAI_API_KEY", "").strip()), "model_access": "NOT_VERIFIED_NO_REQUEST",
              "provider_key": key_metadata(root), "provider": provider_summary(root), "episodes": {"claimed": episode_count(root), "limit": EPISODE_LIMIT},
              "hook_death_boundary": "NATIVE_CLI_FAIL_OPEN_LIMITATION_RETAINED", "native_general_development": "NOT_ESTABLISHED"}
    try:
        health = read_local(target / "host", "/health")
        report["health"] = health
        if health.get("judge_mode") not in ("JEV_RULES_ONLY", "JEV_USER_LIVE") or health.get("spec") != "MVP-SPEC-5" or health.get("decision_policy") != DECISION_POLICY:
            issues.append("DEMO_HEALTH_INVALID")
        if active_revision(root) and health.get("demo_dispatch") != "post_host_approval_v1":
            issues.append("DEMO_POST_HOST_APPROVAL_DISPATCH_UNVERIFIED")
        current_policy = json.loads((target / "config/policy.json").read_text(encoding="utf-8"))
        if current_policy not in (policy(False), policy(True)):
            issues.append("DEMO_POLICY_INVALID")
        expected = "JEV_USER_LIVE" if current_policy.get("enabled") else "JEV_RULES_ONLY"
        if health.get("judge_mode") != expected:
            issues.append("DEMO_POLICY_CONTAINER_MISMATCH")
        # Hash only public product code, not key/runtime contents.
        expression = "import hashlib,json;from pathlib import Path;r=Path('/product');m=json.loads((r/'manifest.json').read_text());print(json.dumps({'manifest':hashlib.sha256((r/'manifest.json').read_bytes()).hexdigest(),'files_match':all(hashlib.sha256((r/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in m)}))"
        for service in ("control", "upstream"):
            value = json.loads(compose(root, ["exec", "-T", service, "python", "-c", expression], manifest["image"]))
            if value != {"manifest": manifest["bundle_sha256"], "files_match": True}:
                issues.append("DEMO_CONTAINER_BUNDLE_MISMATCH")
        for service in ("control", "upstream", "agentgateway"):
            container_id = compose(root, ["ps", "-q", service], manifest["image"]).strip()
            if not re.fullmatch(r"[0-9a-f]{12,64}", container_id):
                issues.append("DEMO_CONTAINER_IMAGE_UNVERIFIED")
                continue
            result = command([docker(root), "inspect", container_id, "--format", "{{.Image}}"])
            expected_image = manifest["gateway_image"].split("@", 1)[1] if service == "agentgateway" else manifest["image"]
            if result.returncode or result.stdout.strip() != expected_image:
                issues.append("DEMO_CONTAINER_IMAGE_UNVERIFIED")
        report["container_bundle_current"] = "DEMO_CONTAINER_BUNDLE_MISMATCH" not in issues
        report["mcp_startup"] = helper(root, "hookgw_mcp_probe").probe(root, target / "host")
        if not report["mcp_startup"].get("ready"):
            issues.append("DEMO_MCP_STARTUP_FAILED")
    except (OSError, ValueError, subprocess.SubprocessError):
        issues.append("DEMO_SERVICE_UNAVAILABLE")
    if cli:
        launcher = helper(root, "hookgw_launch")
        try:
            if not exe or not model:
                raise ValueError("CLI_AND_MODEL_REQUIRED")
            launcher.check_conflicts(target / "workspace", [], api=True)
            launcher.check_manual_requirements()
            flags = cli_flags(root, model)
            outcome = command([exe, *flags, "features", "list"])
            if outcome.returncode or outcome.stderr.strip() or not any(len(x.split()) == 3 and x.split()[0] == "hooks" and x.split()[2] == "true" for x in outcome.stdout.splitlines()):
                issues.append("DEMO_CLI_CONFIG_WARNING_OR_REJECTED")
        except (OSError, ValueError, SystemExit, subprocess.SubprocessError):
            issues.append("DEMO_CLI_CONFIG_UNVERIFIED")
        if not report["actor_key_present"]:
            issues.append("ACTOR_OPENAI_ENV_KEY_MISSING")
    report["ready"] = not issues
    report["warnings"] = ["BOB_AGENTGATEWAY_4400_SEPARATE_PERSONAL_MCP_WARNING_NOT_CHANGED"]
    return report


def claim_episode(root, manifest_sha256, model):
    target = runtime(root)
    for index in range(EPISODE_START, EPISODE_START + EPISODE_LIMIT):
        try:
            write_new(target / "episodes" / f"episode-{index}.claim", {"episode": index, "manifest_sha256": manifest_sha256, "actor_model": model,
                                                                      "status": "CLAIMED_NO_AUTOMATIC_RETRY"})
            return index
        except FileExistsError:
            continue
    raise ValueError("DEMO_EPISODES_EXHAUSTED_NO_RESET")


def wait_health(root, expected):
    for _ in range(20):
        try:
            if read_local(runtime(root) / "host", "/health").get("judge_mode") == expected:
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    raise ValueError("DEMO_RESTART_NOT_READY_CLAIM_RETAINED")


def actor_sink(root, episode, revision, manifest_sha256):
    directory = safe_path(root, f"{RELATIVE}/episodes/events/episode-{episode}", False)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    def append(value):
        name = "start.json" if value["event"] == "STARTING" else "finish.json"
        write_new(directory / name, {**value, "episode": episode, "revision": revision or "legacy-180", "manifest_sha256": manifest_sha256})
    return append


def actor_events(root):
    rows = []
    allowed = {"event", "episode", "revision", "manifest_sha256", "started_utc", "ended_utc", "elapsed_seconds", "wall_seconds",
               "wait_accounting", "outcome", "exit_code", "started", "tree_cleanup", "connection_closed"}
    for episode in range(EPISODE_START, EPISODE_START + EPISODE_LIMIT):
        if not (runtime(root) / "episodes" / f"episode-{episode}.claim").exists():
            continue
        found = []
        for name in ("start.json", "finish.json"):
            path = safe_path(root, f"{RELATIVE}/episodes/events/episode-{episode}/{name}", False)
            if path.is_file():
                if path.stat().st_size > 4096:
                    raise ValueError("DEMO_ACTOR_EVENT_LIMIT")
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict) or set(value) - allowed or value.get("episode") != episode:
                    raise ValueError("DEMO_ACTOR_EVENT_INVALID")
                found.append(value)
        rows.extend(found)
        if not found or found[-1].get("event") != "FINISHED":
            rows.append({"event": "LEGACY_UNKNOWN", "episode": episode, "outcome": "EXIT_STATUS_UNKNOWN",
                         "exit_code": None, "tree_cleanup": "UNVERIFIED", "connection_closed": "UNVERIFIED"})
    return rows[-4:]


def start(root, exe, model, confirm_send=False, manifest_sha256=None, requests=None, input_reservation=None, actor_episodes=None,
          revision=None, interactive_wall_seconds=None):
    manifest = verified(root)
    target = runtime(root)
    if not confirm_send or not isinstance(manifest_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) or sha(manifest_path(root)) != manifest_sha256:
        raise ValueError("DEMO_EXACT_MANIFEST_AND_CONFIRM_SEND_REQUIRED")
    if any(type(v) is not int for v in (requests, input_reservation, actor_episodes)) or (requests, input_reservation, actor_episodes) != (REQUEST_LIMIT, INPUT_LIMIT, EPISODE_LIMIT):
        raise ValueError("DEMO_EXPLICIT_LIMITS_8_512000_2_REQUIRED")
    if active_revision(root):
        if revision != REVISION or type(interactive_wall_seconds) is not int or interactive_wall_seconds != INTERACTIVE_WALL:
            raise ValueError("DEMO_REVISION_AND_EXPLICIT_WALL_1800_REQUIRED")
    elif revision is not None or interactive_wall_seconds not in (None, 180):
        raise ValueError("DEMO_LEGACY_WALL_180_NOT_SILENTLY_EXPANDED")
    wall = INTERACTIVE_WALL if active_revision(root) else 180
    report = check(root, exe, model)
    if not report["ready"]:
        return {"started": False, "preflight": report}
    for name, digest in manifest["source_documents"].items():
        if sha(safe_path(target / "workspace", name)) != digest:
            raise ValueError("DEMO_SOURCE_DOCUMENT_CHANGED")
    verified(root)
    if sha(manifest_path(root)) != manifest_sha256:
        raise ValueError("DEMO_APPROVAL_BINDING_CHANGED")
    episode = claim_episode(root, manifest_sha256, model)
    sink = actor_sink(root, episode, revision, manifest_sha256)
    lifecycle = helper(root, "mvp_demo_lifecycle")
    connection = None
    tick, started_utc = time.monotonic(), lifecycle.utc()
    try:
        config = safe_path(root, f"{RELATIVE}/config/policy.json")
        previous = json.loads(config.read_text(encoding="utf-8"))
        if previous == policy(False):
            pending = config.with_suffix(".pending")
            write_new(pending, policy(True))
            os.replace(pending, config)
            compose(root, ["up", "-d", "--no-build", "--pull", "never", "--force-recreate", "control"], manifest["image"])
            wait_health(root, "JEV_USER_LIVE")
        elif previous != policy(True):
            raise ValueError("DEMO_POLICY_INVALID")
        report = check(root, exe, model)
        if not report["ready"]:
            raise ValueError("DEMO_SECOND_PREFLIGHT_FAILED")
        connection = helper(root, "hookgw_hook").send(target / "host", "/connect", {})["connection"]
        flags = cli_flags(root, model)
        print(f"Opening Codex: explicit wall {wall}s includes human waiting and execution. Host approvals remain yours; sandbox/settings unchanged.", flush=True)
        print("bob-agentgateway:4400 is a separate personal MCP warning; no global configuration was changed.", flush=True)
        def revoke():
            value = helper(root, "hookgw_hook").send(target / "host", "/demo/close", {"connection": connection}, timeout=5)
            return value.get("state") == "CLOSED"
        result = lifecycle.run([exe, *flags], cwd=target / "workspace", env={**os.environ, "WITH_HUMAN_CONNECTION": connection},
                               wall_seconds=wall, event_sink=sink, before_stop=revoke if revision else None)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        closed = "NOT_APPLICABLE"
        if connection and revision:
            with lifecycle.cleanup_shield():
                closed = lifecycle.stop_control(lambda: helper(root, "hookgw_hook").send(target / "host", "/demo/close", {"connection": connection}, timeout=5).get("state") == "CLOSED")
        result = {"event": "FINISHED", "outcome": "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "LAUNCH_FAILED", "started": False,
                  "exit_code": None, "tree_cleanup": "NOT_CREATED", "connection_closed": "UNVERIFIED" if closed == "INTERRUPTED" else closed,
                  "started_utc": started_utc, "ended_utc": lifecycle.utc(), "elapsed_seconds": round(time.monotonic()-tick, 3), "wall_seconds": wall}
        directory = target / "episodes/events" / f"episode-{episode}"
        if not (directory / "start.json").exists():
            sink({"event": "STARTING", "started_utc": started_utc, "wall_seconds": wall})
        if not (directory / "finish.json").exists():
            sink(result)
    return {"started": result["started"], "episode": episode, "actor_result": result, "automatic_retry": False,
            "semantic_result": "SEE_HISTORY_NOT_INFERRED_FROM_CLI_EXIT"}


def effects(root):
    target = runtime(root)
    rows = []
    for name in REPORTS:
        path = safe_path(target / "workspace", name, False)
        if path.exists():
            size = path.stat().st_size
            if size > 16384:
                raise ValueError("DEMO_EFFECT_LIMIT")
            text = path.read_text(encoding="utf-8")
            rows.append({"path": name, "exists": True, "bytes": size, "sha256": sha(path), "text": text[:2048]})
        else:
            rows.append({"path": name, "exists": False, "bytes": 0, "sha256": None, "text": ""})
    return rows


def upstream_summary(root):
    # Upstream attempts prove observed transport/file attempts, never an atomic receipt.
    expression = "import json,sqlite3;from pathlib import Path;p=Path('/data/attempts.sqlite3');d=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);r=d.execute('SELECT state,count(*) FROM attempts GROUP BY state').fetchall();print(json.dumps({'attempts':sum(n for _,n in r),'observed':sum(n for s,n in r if s=='OBSERVED'),'unknown':sum(n for s,n in r if s=='UNKNOWN'),'receipt':'NOT_ATOMIC_FILE_RECEIPT'}));d.close()"
    value = json.loads(compose(root, ["exec", "-T", "upstream", "python", "-c", expression]))
    if set(value) != {"attempts", "observed", "unknown", "receipt"} or any(type(value[k]) is not int or not 0 <= value[k] <= 10000 for k in ("attempts", "observed", "unknown")) or value["receipt"] != "NOT_ATOMIC_FILE_RECEIPT":
        raise ValueError("DEMO_UPSTREAM_SUMMARY_INVALID")
    return value


def history(root):
    verified(root, current=False)
    return {"version": "mvp-demo-history-1", "mode": "USER_DEMO", "actor_events": actor_events(root), "history": read_local(runtime(root) / "host", "/demo/history", human=True),
            "effects": effects(root), "provider": provider_summary(root), "upstream": upstream_summary(root), "episodes": {"claimed": episode_count(root), "max": EPISODE_LIMIT},
            "scope": "ENROLLED_SYNTHETIC_MCP_FILES", "actual_model_accuracy": "USER_RUN_ONLY_NOT_ESTABLISHED",
            "attack_status": "DERIVE_ONLY_FROM_ACTUAL_CANDIDATE_AND_DECISION_NO_ATTEMPT_IS_NOT_PASS"}


def show_history(root):
    value = history(root)
    viewer = helper(root, "mvp_demo_viewer")
    rendered = viewer.render(value)
    output = runtime(root) / "reports" / ("history-" + secrets.token_hex(8) + ".html")
    viewer.save_report(value, output)
    print(rendered["text"])
    print("Local report: " + str(output))
    return output


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("mode", choices=("prepare", "revise", "inspect", "check", "start", "verify-block", "history"))
    parser.add_argument("--exe")
    parser.add_argument("--model")
    parser.add_argument("--confirm-send", action="store_true")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--resume-manifest-sha256")
    parser.add_argument("--risk-attempt")
    parser.add_argument("--attempt-manifest-sha256")
    parser.add_argument("--select-hands-on-limits", action="store_true")
    parser.add_argument("--approve-request-limit", type=int)
    parser.add_argument("--approve-input-reservation-limit", type=int)
    parser.add_argument("--approve-actor-episodes", type=int)
    parser.add_argument("--revision", choices=(REVISION, "behavior-v5-1", "core-auto-v5p1", "hands-on-1", "frozen-demo-1"))
    parser.add_argument("--confirm-revision", action="store_true")
    parser.add_argument("--approve-interactive-wall-seconds", type=int)
    for name in ("total-actor-starts", "cumulative-requests", "cumulative-input-reservation", "demo-cumulative-requests", "demo-cumulative-input-reservation"):
        parser.add_argument("--approve-" + name, type=int)
    args = parser.parse_args()
    try:
        if args.revision in ("hands-on-1","frozen-demo-1"):
            f = helper(ROOT,"mvp_semantic_followup")
            prefix="frozen" if args.revision=="frozen-demo-1" else "hands"
            check_demo,start_demo,history_demo,base_demo=(getattr(f,prefix+"_"+name) for name in ("check","start","history","base"))
            forbidden = (args.resume_manifest_sha256,args.risk_attempt,args.attempt_manifest_sha256,args.approve_request_limit,
                         args.approve_input_reservation_limit,args.approve_actor_episodes,args.approve_total_actor_starts,
                         args.approve_cumulative_requests,args.approve_cumulative_input_reservation,args.approve_demo_cumulative_requests,
                         args.approve_demo_cumulative_input_reservation,args.approve_interactive_wall_seconds,args.confirm_revision)
            if any(value is not None and value is not False for value in forbidden):
                raise ValueError("HANDS_USE_FROZEN_SELECTION_ONLY")
            if args.mode != "start" and any((args.confirm_send,args.manifest_sha256,args.select_hands_on_limits)):
                raise ValueError("HANDS_APPROVAL_START_ONLY")
            if args.mode == "check":
                value = check_demo(ROOT,args.exe,args.model)
            elif args.mode == "inspect":
                value = base_demo(ROOT).inspect_demo(ROOT)
            elif args.mode == "history":
                history_demo(ROOT,True)
                return
            elif args.mode == "start":
                value = start_demo(ROOT,args.exe,args.model,args.confirm_send,args.manifest_sha256,args.select_hands_on_limits)
                try:
                    history_demo(ROOT,True)
                except (OSError,ValueError,KeyError,subprocess.SubprocessError):
                    print(f"Demo history unavailable; use -Revision {args.revision} -Mode history; no retry.")
            else:
                raise ValueError("HANDS_MODE_REJECTED")
            print(json.dumps(value,ensure_ascii=True))
            if args.mode == "check" and not value["ready"]:
                raise SystemExit(2)
            if args.mode == "start" and any(value.get("actor_result",{}).get(k)!=v for k,v in {"outcome":"EXITED","exit_code":0,"tree_cleanup":"VERIFIED","connection_closed":"VERIFIED"}.items()):
                raise SystemExit(2)
            return
        if args.select_hands_on_limits:
            raise ValueError("HANDS_REVISION_REQUIRED")
        if (args.risk_attempt is not None or args.attempt_manifest_sha256 is not None) and (args.mode != "verify-block" or args.revision != "core-auto-v5p1" or args.risk_attempt != "post-complete-1" or args.resume_manifest_sha256 is not None):
            raise ValueError("CORE_POST_EXACT_ATTEMPT_REQUIRED")
        if args.resume_manifest_sha256 is not None and (args.mode != "verify-block" or args.revision != "core-auto-v5p1"):
            raise ValueError("CORE_RESUME_VERIFY_BLOCK_ONLY")
        extra_approvals = (args.approve_total_actor_starts, args.approve_cumulative_requests, args.approve_cumulative_input_reservation,
                           args.approve_demo_cumulative_requests, args.approve_demo_cumulative_input_reservation)
        if any(n is not None for n in extra_approvals) and (args.mode not in ("start", "verify-block") or args.revision not in ("behavior-v5-1", "core-auto-v5p1")):
            raise ValueError("BEHAVIOR_APPROVALS_START_ONLY")
        if args.mode not in ("start", "verify-block") and any((args.confirm_send, args.manifest_sha256, args.approve_request_limit is not None, args.approve_input_reservation_limit is not None, args.approve_actor_episodes is not None, args.approve_interactive_wall_seconds is not None)):
            raise ValueError("DEMO_APPROVAL_ARGUMENTS_START_ONLY")
        if args.confirm_revision and args.mode != "revise":
            raise ValueError("DEMO_CONFIRM_REVISION_PREPARE_ONLY")
        if args.revision in ("behavior-v5-1", "core-auto-v5p1"):
            core = args.revision == "core-auto-v5p1"
            followup = helper(ROOT, "mvp_semantic_followup")
            if args.mode == "revise" and args.confirm_revision:
                value = followup.behavior_prepare(ROOT, core)
            elif args.mode == "inspect":
                value = followup.behavior_inspect(ROOT, core)
            elif args.mode == "check":
                value = followup.behavior_check(ROOT, args.exe, args.model, core)
            elif args.mode == "history":
                followup.behavior_show_history(ROOT, core)
                return
            elif args.mode in ("start", "verify-block"):
                operation = followup.behavior_start if args.mode == "start" else followup.core_verify_block
                if args.mode == "verify-block" and not core:
                    raise ValueError("CORE_REVISION_REQUIRED")
                positional = (ROOT, args.exe, args.model) if args.mode == "start" else (ROOT,)
                extras = {"core": core} if args.mode == "start" else {"resume_manifest_sha256": args.resume_manifest_sha256,
                        "risk_attempt":args.risk_attempt,"attempt_manifest_sha256":args.attempt_manifest_sha256}
                value = operation(*positional, **extras, confirm_send=args.confirm_send, manifest_sha256=args.manifest_sha256,
                         requests=args.approve_request_limit, input_limit=args.approve_input_reservation_limit,
                         additional_starts=args.approve_actor_episodes, total_starts=args.approve_total_actor_starts,
                         cumulative_requests=args.approve_cumulative_requests, cumulative_input=args.approve_cumulative_input_reservation,
                         demo_requests=args.approve_demo_cumulative_requests, demo_input=args.approve_demo_cumulative_input_reservation,
                         wall_seconds=args.approve_interactive_wall_seconds)
                try:
                    followup.behavior_show_history(ROOT, core)
                except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                    print(f"History unavailable; use -Revision {args.revision} -Mode history; no retry.")
                if args.mode == "verify-block":
                    print(json.dumps(value, ensure_ascii=True))
                    if value.get("status") != "FIXED_RISK_DENY_VERIFIED":
                        raise SystemExit(2)
                    return
                result = value.get("actor_result", {})
                if result.get("outcome") != "EXITED" or result.get("exit_code") != 0 or result.get("tree_cleanup") != "VERIFIED" or result.get("connection_closed") != "VERIFIED":
                    raise SystemExit(2)
            else:
                raise ValueError("BEHAVIOR_REVISION_MODE_REJECTED")
            print(json.dumps(value, ensure_ascii=True))
            if args.mode == "check" and not value["ready"]:
                raise SystemExit(2)
            return
        if args.mode == "prepare":
            value = prepare(ROOT)
        elif args.mode == "revise":
            value = revise(ROOT, args.revision, args.confirm_revision)
        elif args.mode == "inspect":
            value = inspect_demo(ROOT)
        elif args.mode == "check":
            value = check(ROOT, args.exe, args.model)
        elif args.mode == "start":
            value = start(ROOT, args.exe, args.model, args.confirm_send, args.manifest_sha256,
                          args.approve_request_limit, args.approve_input_reservation_limit, args.approve_actor_episodes,
                          args.revision, args.approve_interactive_wall_seconds)
            result = value.get("actor_result", {})
            print("CLI lifecycle: " + result.get("outcome", "NOT_STARTED_PREFLIGHT_FAILED") + "; exit=" + str(result.get("exit_code")) + "; cleanup=" + result.get("tree_cleanup", "UNKNOWN"))
            try:
                show_history(ROOT)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                print("MVP_DEMO_HISTORY_UNAVAILABLE; run scripts/mvp_demo.ps1 -Mode history; no automatic retry.")
            if result.get("outcome") != "EXITED" or result.get("exit_code") != 0 or result.get("tree_cleanup") != "VERIFIED" or result.get("connection_closed") == "UNVERIFIED":
                raise SystemExit(124 if result.get("outcome") == "TIMEOUT" else 130 if result.get("outcome") == "INTERRUPTED" else 2)
            return
        else:
            show_history(ROOT)
            return
        if args.mode == "inspect":
            print(json.dumps(value, ensure_ascii=True))
        elif args.mode in ("prepare", "revise"):
            print("Public revision prepared: paid requests 0; original config/budget/claims preserved." if args.mode == "revise" else "Demo prepared: LIVE disabled; paid requests 0; existing history preserved.")
            print("Manifest SHA256: " + value["manifest_sha256"])
            print("Next: check, inspect, then explicit human start.")
        else:
            print("Model-free demo check: " + ("READY" if value["ready"] else "NOT READY"))
            print("Issues: " + (", ".join(value["issues"]) or "none"))
            print("Provider access unverified; model requests 0. Host hooks require /hooks trust review.")
            print("Manifest SHA256: " + value["manifest_sha256"])
            if not value["ready"]:
                raise SystemExit(2)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        codes = {"CORE_NORMAL_CLI_NOT_VERIFIED", "CORE_NORMAL_USAGE_OR_REMAINDER_INVALID", "CORE_NORMAL_EFFECT_INVALID",
                 "HANDS_USE_FROZEN_SELECTION_ONLY","HANDS_APPROVAL_START_ONLY","HANDS_MODE_REJECTED","HANDS_REVISION_REQUIRED",
                 "HANDS_EXPLICIT_SELECTION_REQUIRED","HANDS_ALREADY_USED_NO_RETRY","HANDS_SOURCE_IMAGE_PARENT_CHANGED",
                 "CORE_POST_EXACT_ATTEMPT_REQUIRED","CORE_POST_FAILURE_EVIDENCE_CHANGED","CORE_POST_FAILED_RECORD_CHANGED",
                 "CORE_POST_ALREADY_CLAIMED_NO_RETRY","CORE_POST_NORMAL_OR_USAGE_CHANGED","CORE_POST_EXACT_MANIFEST_REQUIRED","CORE_POST_STALE_BINDING",
                 "CORE_NORMAL_RECORD_BUSY", "CORE_NORMAL_RECORD_CHANGED", "CORE_NORMAL_HUMAN_APPROVAL_NOT_AUTOMATIC",
                 "CORE_NORMAL_CONNECTION_NOT_CLOSED", "CORE_NORMAL_USER_TURN_INVALID", "CORE_NORMAL_CALLS_NOT_AUTOMATIC",
                 "CORE_NORMAL_READ_ERROR_INVALID", "CORE_NORMAL_EXACT_FILES_REQUIRED", "CORE_NORMAL_UPSTREAM_INVALID",
                 "CORE_RESUME_VERIFY_BLOCK_ONLY", "CORE_RESUME_EXACT_MANIFEST_REQUIRED", "CORE_RESUME_STALE_BINDING",
                 "CORE_RESUME_UNAUTHORIZED_DRIFT", "CORE_RESUME_ORIGINAL_MANIFEST_INVALID", "CORE_RESUME_CONTAINER_BINDING_INVALID", "CORE_RESUME_NORMAL_EVIDENCE_CHANGED",
                 "CORE_BLOCK_ALREADY_CLAIMED_NO_RETRY", "CORE_LIVE_POLICY_REQUIRED", "CORE_LIVE_PROFILE_UNVERIFIED",
                 "CORE_EXACT_MANIFEST_REQUIRED", "CORE_EXACT_BATCH_APPROVALS_REQUIRED"}
        code = str(error) if isinstance(error, ValueError) and str(error) in codes else "LOCAL_BINDING_UNAVAILABLE"
        print(json.dumps({"error": "MVP_DEMO_UNAVAILABLE_OR_BINDING_REJECTED", "stage": "CORE_RISK_PREFLIGHT" if args.mode == "verify-block" else "LOCAL_PRECONDITION",
                          "code": code, "paid_execution": "NOT_INFERRED_NO_RETRY_CHECK_HISTORY"}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
