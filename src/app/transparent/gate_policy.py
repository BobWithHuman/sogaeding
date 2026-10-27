"""Shared gate-6 decision rules, independent of evaluation runners and providers.

Callers supply validated observations and server-verified resource authority.
This module never executes tools or treats external consent claims as authority.
"""
from app.transparent.candidate_policy import ALLOW_THRESHOLD, positive_semantics
from app.transparent.candidate_policy import RISK_THRESHOLD as RISK_THRESHOLD

RULE = "engine-gate6-1"
POLICY = "engine-2026-10-24-gate6-1"
RISK_HOLDS = (
    "OUTSIDE_TASK_CAPABILITY_REQUIRES_CONSENT",
    "SENSITIVE_RESOURCE_REQUIRES_CONSENT",
)


def semantic_rows(observations):
    a = [r for r in observations["A"] if r["question"] == "task_relation"]
    b = [r for r in observations["B"]
         if r["question"] in ("behavior", "current_behavior", "benchmark_behavior")]
    if len(a) != 1 or len(b) != 1:
        raise ValueError("CURRENT_SEMANTIC_OBSERVATION_REQUIRED")
    return a[0], b[0]


def explicit_semantics(observations):
    b = [r for r in observations["B"]
         if r["question"] in ("behavior", "current_behavior", "benchmark_behavior")]
    if len(b) != 1:
        raise ValueError("CURRENT_SEMANTIC_OBSERVATION_REQUIRED")
    b = b[0]
    return b["choice"] == "LEGITIMATE" and b["effective_confidence"] >= ALLOW_THRESHOLD


def consent_semantics(observations):
    a, b = semantic_rows(observations)
    return (a["choice"] == "WITHIN_TASK" and a["effective_confidence"] >= ALLOW_THRESHOLD
            and b["choice"] == "LEGITIMATE" and b["effective_confidence"] >= ALLOW_THRESHOLD)


def semantic_rejection(observations):
    a, b = semantic_rows(observations)
    return (a["choice"] == "OUTSIDE_TASK" and a["effective_confidence"] >= ALLOW_THRESHOLD
            or b["choice"] in ("EXTERNAL_ADOPTION", "OUTSIDE_TASK")
            and b["effective_confidence"] >= ALLOW_THRESHOLD)


def compose(old, observations, grant):
    """Preserve hard/risk DENY; held risk requires A+B affirmation and human consent."""
    if old[0] == "DENY":
        return old
    if grant and grant.get("semantic_consent"):
        affirmed = (grant.get("authorized") is True and grant.get("prohibited") is not True
                    and consent_semantics(observations))
        if grant.get("jev_gate") is True:
            if semantic_rejection(observations):
                return "DENY", ["JEV_REJECTED_HELD_CASE"]
            if set(grant["semantic_consent"]) & set(RISK_HOLDS):
                return (("CONFIRM", list(grant["semantic_consent"])) if affirmed else
                        ("DENY", ["JEV_NOT_AFFIRMED_RISK_CASE"]))
        if affirmed:
            return "ALLOW", ["CONSENT_CASE_A_AND_B_AFFIRMED"]
        return "CONFIRM", list(grant["semantic_consent"])
    if (positive_semantics(old, observations) and grant and grant.get("authorized") is True
            and (grant.get("data_class") == "PUBLIC" or grant.get("sensitive_consent") is True)
            and (grant.get("side_effect_free") is True or grant.get("effect_consent") is True)
            and grant.get("prohibited") is not True):
        return "ALLOW", ["DEMO_TASK_SCOPE_B_LEGITIMATE" if grant.get("reason") == "SERVER_TASK_SCOPE_ACCESS_VERIFIED"
                         else "DEMO_EXACT_AUTHORITY_B_LEGITIMATE"]
    if (grant and grant.get("explicit_user_scope") is True and grant.get("authorized") is True
            and grant.get("data_class") == "PUBLIC"
            and (grant.get("side_effect_free") is True or grant.get("effect_consent") is True)
            and grant.get("prohibited") is not True and explicit_semantics(observations)):
        return "ALLOW", ["EXPLICIT_USER_SCOPE_B_LEGITIMATE"]
    return "CONFIRM", ["DEMO_AUTHORITY_OR_SEMANTICS_UNRESOLVED"]
