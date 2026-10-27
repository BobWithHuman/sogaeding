"""Local operator capabilities, bound to this runtime's machine identity.

This is not a multi-user login service or an OIDC/MFA implementation.
"""
import hmac
import re
import time

from app.common import digest

PERMISSIONS = frozenset({"history:read", "approval:write", "session:purge", "security:read", "security:ack"})


def valid_token(token):
    return isinstance(token, str) and 1 <= len(token) <= 2048 and token.isascii() and not any(c.isspace() for c in token)


class OperatorAccess:
    def __init__(self, machine, token, entries=()):
        if not valid_token(token):
            raise ValueError("OPERATOR_POLICY_INVALID")
        self.machine = machine
        self.entries = [{"subject": "local-operator", "token_sha256": digest(token),
                         "permissions": PERMISSIONS, "expires_at": None}]
        if not isinstance(entries, (list, tuple)) or len(entries) > 16:
            raise ValueError("OPERATOR_POLICY_INVALID")
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) != {"subject", "token_sha256", "permissions", "expires_at"}
                    or not isinstance(entry["subject"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", entry["subject"])
                    or not isinstance(entry["token_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", entry["token_sha256"])
                    or entry["token_sha256"] == digest("")
                    or not isinstance(entry["permissions"], list) or not entry["permissions"]
                    or any(not isinstance(p, str) or p not in PERMISSIONS for p in entry["permissions"])
                    or type(entry["expires_at"]) is not int or not 0 < entry["expires_at"] <= 4102444800
                    or any(old["token_sha256"] == entry["token_sha256"] or old["subject"] == entry["subject"] for old in self.entries)):
                raise ValueError("OPERATOR_POLICY_INVALID")
            self.entries.append(dict(entry))

    def authenticate(self, token):
        if not valid_token(token):
            return None
        hashed = digest(token)
        for entry in self.entries:
            if hmac.compare_digest(hashed, entry["token_sha256"]) and (entry["expires_at"] is None or time.time() < entry["expires_at"]):
                return {"subject": entry["subject"], "machine": self.machine, "permissions": entry["permissions"]}
        return None
