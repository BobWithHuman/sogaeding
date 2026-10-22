"""Fail-closed provider opt-in. Never reads the OpenAI key or ledger."""
from app.common import strict_json
from app.transparent.jev import JevSettings

DEFAULT_PROFILE = "current_candidate_1"


def make_policy(client, profile=DEFAULT_PROFILE):
    """Current .50 policy is the default; historical policies require selection."""
    from app.transparent.jev_core_v5p1 import JevPolicyCurrent, JevPolicyV5P1
    from app.transparent.jev_decision_v5 import JevPolicyV5
    from app.transparent.jev_policy import JevPolicy
    from app.transparent.jev_semantic_v3 import JevPolicyV3

    policies = {
        DEFAULT_PROFILE: JevPolicyCurrent,
        "behavior_v5p1": JevPolicyV5P1,
        "behavior_v5": JevPolicyV5,
        "semantic_confirm_v3": JevPolicyV3,
        "legacy_v2": JevPolicy,
    }
    if profile not in policies:
        raise RuntimeError("UNSUPPORTED_JEV_PROFILE")
    return policies[profile](client)


def load_settings(path):
    if not path.is_file():
        return JevSettings()
    if path.is_symlink() or path.stat().st_size > 4096:
        raise ValueError("JEV_SETTINGS_INVALID")
    value = strict_json(path.read_bytes())
    required = {"enabled", "model", "request_limit", "input_token_limit", "policy_id"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("JEV_SETTINGS_INVALID")
    settings = JevSettings(**value, key_path="/jev-key/jev.api-key", budget_path="/jev-budget/typesafe-budget.sqlite3")
    if value["enabled"] is not False and not settings.authorized():
        raise ValueError("JEV_SETTINGS_INVALID")
    return settings
