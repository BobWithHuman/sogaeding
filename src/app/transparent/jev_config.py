"""Fail-closed provider opt-in. Never reads the OpenAI key or ledger."""
from app.common import strict_json
from app.transparent.jev import JevSettings


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
