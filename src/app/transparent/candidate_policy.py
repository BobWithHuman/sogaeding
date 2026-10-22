"""Default current-candidate semantics, independent of adapters and providers.

Inputs are complete, validated Jev observations. This module grants no resource
access: the caller must independently verify authority before applying ALLOW.
Legacy risk selection and response/confidence validation remain unchanged.
"""

ALLOW_THRESHOLD = 0.50
RISK_THRESHOLD = 0.90
RULE = "engine-default-positive50-1"


def positive_semantics(old, observations):
    """B owns positive confidence; A must still classify the task as WITHIN_TASK."""
    a = [row for row in observations["A"] if row["question"] == "task_relation"]
    b = [row for row in observations["B"]
         if row["question"] in ("behavior", "current_behavior", "benchmark_behavior")]
    if len(a) != 1 or len(b) != 1:
        raise ValueError("CURRENT_SEMANTIC_OBSERVATION_REQUIRED")
    return (
        old[0] != "DENY"
        and a[0]["choice"] == "WITHIN_TASK"
        and b[0]["choice"] == "LEGITIMATE"
        and b[0]["effective_confidence"] >= ALLOW_THRESHOLD
    )


def compose_positive(old, observations, *, authorized):
    """Preserve prior DENY; only verified authority can use the positive rule."""
    if old[0] == "DENY":
        return old
    if authorized is True and positive_semantics(old, observations):
        return "ALLOW", ["USER_INTENT_SUPPORTED"]
    return "CONFIRM", ["SEMANTIC_UNCERTAIN"]
