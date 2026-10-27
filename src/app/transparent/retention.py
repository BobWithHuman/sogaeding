"""Bounded local-MVP retention; configuration never extends stored deadlines."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionPolicy:
    session_seconds: int = 86400
    history_seconds: int = 604800
    evidence_seconds: int = 2592000

    @classmethod
    def from_env(cls):
        def seconds(name, default, lower, upper):
            text = os.environ.get(name, str(default))
            if not text.isascii() or not text.isdigit() or not lower <= int(text) <= upper:
                raise ValueError("RETENTION_POLICY_INVALID")
            return int(text)
        session = seconds("WITH_HUMAN_SESSION_TTL_SECONDS", 86400, 60, 86400)
        history = seconds("WITH_HUMAN_HISTORY_TTL_SECONDS", 604800, 60, 604800)
        evidence = seconds("WITH_HUMAN_DELETION_EVIDENCE_TTL_SECONDS", 2592000, 3600, 2592000)
        if history < session:
            raise ValueError("RETENTION_POLICY_INVALID")
        return cls(session, history, evidence)
