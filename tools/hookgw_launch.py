"""Launch user's normal interactive Codex with scoped overlays, no prompt input."""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

API_PROVIDER = "with_human_openai_api"
API_BASE = "https://api.openai.com/v1"
API_ENV_KEY = "OPENAI_API_KEY"


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        marker = "_specified_" + self.dest
        if getattr(namespace, marker, False):
            parser.error("Repeated launcher option is not permitted")
        setattr(namespace, marker, True)
        setattr(namespace, self.dest, values)


def trusted_helper(name):
    spec = importlib.util.spec_from_file_location("with_human_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trusted_send():
    spec = importlib.util.spec_from_file_location("with_human_trusted_hook", Path(__file__).with_name("hookgw_hook.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send


def check_conflicts(root, args, api=False, strict_product=False):
    # Refuse silently replacing an existing hook array; never print config values.
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    candidates = {home / "config.toml", *(p / ".codex/config.toml" for p in (root, *root.parents))}
    if api or strict_product:
        # Legacy managed defaults override CLI flags. Do not start under an
        # unreviewed managed layer or attempt to change its authentication rules.
        managed = {home / "managed_config.toml", Path.home() / ".codex/managed_config.toml"}
        if os.name != "nt":
            managed.add(Path("/etc/codex/managed_config.toml"))
            candidates.add(Path("/etc/codex/config.toml"))
        elif os.environ.get("ProgramData"):
            candidates.add(Path(os.environ["ProgramData"]) / "OpenAI/Codex/config.toml")
        if any(path.is_file() for path in managed):
            raise SystemExit("Managed defaults require reviewed API routing; no settings or login changed.")
    for path in candidates:
        if path.with_name("hooks.json").is_file():
            raise SystemExit("Existing hooks.json requires a reviewed merge; no definitions were overwritten.")
        if path.is_file():
            with path.open("rb") as stream:
                config = tomllib.load(stream)
            layers = [config, *config.get("profiles", {}).values()] if api or strict_product else [config]
            # CLI /hooks persists consent under hooks.state. It is not an
            # executable hook array and stays intact under per-event overlays.
            if any(hooks and (not isinstance(hooks, dict) or set(hooks) - {"state"}) for hooks in (layer.get("hooks") for layer in layers)):
                raise SystemExit("Existing hook config requires a reviewed merge; no arrays were overwritten.")
            if strict_product and any("with_human" in layer.get("mcp_servers", {}) for layer in layers):
                raise SystemExit("Existing with_human MCP config requires a reviewed merge; no definitions were overwritten.")
            if api and any(layer.get("forced_login_method") or layer.get("forced_chatgpt_workspace_id") for layer in layers):
                raise SystemExit("Managed login restriction requires review; no login state changed.")
            if api and any(API_PROVIDER in layer.get("model_providers", {}) for layer in layers):
                raise SystemExit("Reserved API provider already configured; no settings were overwritten.")
    if any(arg.startswith("--dangerously-bypass") or any(arg.startswith(x) and len(arg) > len(x) for x in ("-c", "-C", "-p", "-s", "-a")) for arg in args):
        raise SystemExit("Connection/security overrides require separate review.")
    forbidden = ("--config", "-c", "--cd", "-C", "--profile", "-p", "--sandbox", "-s", "--ask-for-approval", "-a", "--dangerously-bypass", "--yolo")
    if any(any(arg == x or arg.startswith(x + "=") for x in forbidden) for arg in args):
        raise SystemExit("Connection/security overrides require separate review; use normal interactive codex.")
    if api and args:
        raise SystemExit("API mode accepts direct interactive codex only; choose -Model at connection setup.")


def api_overrides(model):
    if not model or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}", model):
        raise SystemExit("Explicit API model ID required; access is not verified offline.")
    provider = '{name="With Human OpenAI API",base_url="' + API_BASE + '",env_key="' + API_ENV_KEY + '",wire_api="responses",requires_openai_auth=false,request_max_retries=0,stream_max_retries=0}'
    return ["-c", "model_provider=" + json.dumps(API_PROVIDER), "-c", "model=" + json.dumps(model),
            "-c", "model_providers." + API_PROVIDER + "=" + provider]


def overrides(root, host, python):
    command = f'"{python}" -I "{root / "tools/hookgw_hook.py"}" "{host}"'
    values = ["-c", "features.hooks=true"]
    for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
        handler = "{type=\"command\",command=" + json.dumps(command) + ",command_windows=" + json.dumps("& " + command) + ",timeout=120}"
        values += ["-c", "hooks." + event + "=[{hooks=[" + handler + "]}]"]
    values += ["-c", "mcp_servers.with_human.command=" + json.dumps(python),
               "-c", "mcp_servers.with_human.args=" + json.dumps(["-I", str(root / "tools/hookgw_mcp.py"), str(host)]),
               "-c", 'mcp_servers.with_human.env_vars=["WITH_HUMAN_CONNECTION"]']
    values += ['-c', 'mcp_servers.with_human.tool_timeout_sec=180']
    return values


def manual_review_overrides():
    # Only this child invocation; never saved in PS state/config/auth.
    # No sandbox change or automatic permissionDecision=allow.
    return ["-c", 'approvals_reviewer="user"', "-c", 'approval_policy="on-request"']


def check_manual_requirements():
    # Conservative local early refusal. CLI still enforces cloud/MDM/system
    # requirements; these checks never modify or reinterpret an allowed policy.
    paths = ([Path(os.environ["ProgramData"]) / "OpenAI/Codex/requirements.toml"]
             if os.name == "nt" and os.environ.get("ProgramData") else [Path("/etc/codex/requirements.toml")])
    for path in paths:
        if not path.is_file():
            continue
        try:
            with path.open("rb") as stream:
                requirements = tomllib.load(stream)
        except (OSError, ValueError):
            raise SystemExit("Managed requirements could not be verified; no constraints changed.") from None
        for name, required in (("allowed_approvals_reviewers", "user"), ("allowed_approval_policies", "on-request")):
            values = requirements.get(name)
            if values is not None and (not isinstance(values, list) or required not in values):
                raise SystemExit("Managed requirements reject manual review; no settings or constraints changed.")
        if requirements.get("allow_managed_hooks_only") is True:
            raise SystemExit("Managed requirements do not allow project hooks; no constraints changed.")


def main():
    import sys
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--root", type=Path, required=True, action=Once)
    p.add_argument("--exe", required=True, action=Once)
    p.add_argument("--check-config", action="store_true")
    p.add_argument("--api", action="store_true")
    p.add_argument("--model", action=Once)
    p.add_argument("--preflight", action="store_true")
    p.add_argument("--jev-rules", action="store_true")
    p.add_argument("--manual-review", action="count", default=0)
    opts, args = p.parse_known_args()
    if opts.manual_review > 1:
        p.error("Repeated --manual-review is not permitted")
    if opts.manual_review and not (opts.api and opts.jev_rules):
        p.error("--manual-review requires explicit --api --jev-rules")
    root = opts.root.resolve()
    if Path.cwd().resolve() != root:
        raise SystemExit("Enrolled workspace required")
    if opts.jev_rules and not opts.api:
        raise SystemExit("--jev-rules requires explicit --api mode; no personal login changed.")
    host = root / ("artifacts/runtime-hookgw/host-jev" if opts.jev_rules else "artifacts/runtime-hookgw/host")
    check_conflicts(root, args, api=opts.api)
    if opts.manual_review:
        check_manual_requirements()
    flags = overrides(root, host, sys.executable)
    if opts.api:
        flags += api_overrides(opts.model)
        if opts.manual_review:
            flags += manual_review_overrides()
    elif opts.model or opts.preflight:
        raise SystemExit("--model/--preflight require explicit --api mode.")
    if opts.check_config:
        raise SystemExit(subprocess.call([opts.exe, *flags, "features", "list"]))
    if opts.api:
        helper = trusted_helper("hookgw_preflight")
        if opts.manual_review:
            report = helper.run(root, host, opts.exe, flags, opts.model, jev=True, manual_review=True)
        else:
            report = helper.run(root, host, opts.exe, flags, opts.model, jev=True) if opts.jev_rules else helper.run(root, host, opts.exe, flags, opts.model)
        print(json.dumps(report, ensure_ascii=True), flush=True)
        if opts.preflight or not report["ready_to_open_cli"]:
            raise SystemExit(0 if report["ready_to_open_cli"] else 2)
    try:
        connection = trusted_send()(host, "/connect", {})["connection"]
    except (OSError, ValueError, KeyError):
        raise SystemExit("Connection bootstrap failed; no model started.") from None
    env = {**os.environ, "WITH_HUMAN_CONNECTION": connection}
    raise SystemExit(subprocess.call([opts.exe, *flags, *args], env=env))


if __name__ == "__main__":
    main()
