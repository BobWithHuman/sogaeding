"""Opt-in runtime demo routing. Grants are server configuration, never source claims."""

from app.common import canonical, digest
from app.transparent.candidate_policy import ALLOW_THRESHOLD as ALLOW_THRESHOLD
from app.transparent.candidate_policy import RISK_THRESHOLD as RISK_THRESHOLD
from app.transparent.candidate_policy import positive_semantics as positive_semantics

PROFILE = "dtap-demo-allow50-scope-v2"


def authority(snapshot, parsed):
    """Exact operation grants, bound to request, registry, schema and all slots.

    PUBLIC means reviewed non-sensitive data, not a path/name heuristic. A grant
    authorizes the candidate only; the Engine must still reserve before execution.
    """
    expected = {
        "request_sha256": digest(snapshot["user_request"]),
        "registry_sha256": parsed["tool_identity"]["registry_sha256"],
        "schema_sha256": parsed["tool_identity"]["schema_sha256"],
        "candidate_sha256": digest(canonical(snapshot["candidate"])),
    }
    grants = snapshot.get("server_grant", {}).get("reviewed_operations", [])
    return next((g for g in grants if all(g.get(k) == v for k, v in expected.items())), None)


def route(snapshot, parsed, access=None):
    if access and access["decision"] != "ALLOW":
        return access["decision"], access["reason"]
    if access and access.get("semantic_consent"):
        return None  # scope-5 held case: only A and B review (compose) may allow it
    grant = authority(snapshot, parsed)
    if grant and grant.get("prohibited") is True:
        return "DENY", "REVIEWED_OPERATION_PROHIBITED"
    if access and access.get("code_allow") is True and access.get("authorized") is True:
        # scope-4 only: verified metadata of a user-named location, or the fixed session log.
        return "ALLOW", (
            "EXPLICIT_USER_SCOPE_METADATA"
            if access["reason"] == "SERVER_TASK_SCOPE_ACCESS_VERIFIED"
            else access["reason"]
        )
    args = snapshot["candidate"]["args"]
    # An actor cannot switch authenticated identity via a synthetic API option.
    # Official permission requests remain semantic candidates, never auto-grants.
    identity = snapshot.get("server_grant", {}).get("authenticated_access_token")
    if args.get("access_token") is not None and args["access_token"] != identity:
        return "DENY", "UNAUTHORIZED_IDENTITY_OVERRIDE"
    if (
        grant
        and grant.get("authorized") is True
        and parsed["action"] == "QUERY"
        and grant.get("data_class") == "PUBLIC"
        and grant.get("side_effect_free") is True
        and not args.get("ask_for_permission")
    ):
        return "ALLOW", "REVIEWED_PUBLIC_QUERY"
    return None


def explicit_semantics(observations):
    """scope-4: the user named the resource, so B alone owns the .50 positive rule."""
    b = [row for row in observations["B"]
         if row["question"] in ("behavior", "current_behavior", "benchmark_behavior")]
    if len(b) != 1:
        raise ValueError("CURRENT_SEMANTIC_OBSERVATION_REQUIRED")
    return b[0]["choice"] == "LEGITIMATE" and b[0]["effective_confidence"] >= ALLOW_THRESHOLD


def consent_semantics(observations):
    """scope-5: both views affirm at the .50 bar; A's raw label alone is not enough."""
    a = [row for row in observations["A"] if row["question"] == "task_relation"]
    b = [row for row in observations["B"]
         if row["question"] in ("behavior", "current_behavior", "benchmark_behavior")]
    if len(a) != 1 or len(b) != 1:
        raise ValueError("CURRENT_SEMANTIC_OBSERVATION_REQUIRED")
    return (
        a[0]["choice"] == "WITHIN_TASK"
        and a[0]["effective_confidence"] >= ALLOW_THRESHOLD
        and b[0]["choice"] == "LEGITIMATE"
        and b[0]["effective_confidence"] >= ALLOW_THRESHOLD
    )


def semantic_rejection(observations):
    """scope-6: either view's explicit negative label at the .50 bar."""
    a = [row for row in observations["A"] if row["question"] == "task_relation"]
    b = [row for row in observations["B"]
         if row["question"] in ("behavior", "current_behavior", "benchmark_behavior")]
    if len(a) != 1 or len(b) != 1:
        raise ValueError("CURRENT_SEMANTIC_OBSERVATION_REQUIRED")
    return (
        a[0]["choice"] == "OUTSIDE_TASK" and a[0]["effective_confidence"] >= ALLOW_THRESHOLD
        or b[0]["choice"] in ("EXTERNAL_ADOPTION", "OUTSIDE_TASK")
        and b[0]["effective_confidence"] >= ALLOW_THRESHOLD
    )


def compose(old, observations, grant):
    # Risk and A/B conflicts always take priority, using the unchanged .90 rule.
    if old[0] == "DENY":
        return old
    if grant and grant.get("semantic_consent"):
        affirmed = (
            grant.get("authorized") is True
            and grant.get("prohibited") is not True
            and consent_semantics(observations)
        )
        if grant.get("jev_gate") is True:
            from app.benchmark.task_scope import RISK_HOLDS

            # scope-6: Jev decides the held case. A rejection by either view refuses it;
            # a former code refusal also needs both views to affirm before the user is asked.
            if semantic_rejection(observations):
                return "DENY", ["JEV_REJECTED_HELD_CASE"]
            if set(grant["semantic_consent"]) & set(RISK_HOLDS):
                return ("CONFIRM", list(grant["semantic_consent"])) if affirmed else (
                    "DENY", ["JEV_NOT_AFFIRMED_RISK_CASE"])
        # A case that used to stop for consent: only both views together replace the
        # user's answer. Anything less still asks the user.
        if affirmed:
            return "ALLOW", ["CONSENT_CASE_A_AND_B_AFFIRMED"]
        return "CONFIRM", list(grant["semantic_consent"])
    if (
        positive_semantics(old, observations)
        and grant
        and grant.get("authorized") is True
        and (grant.get("data_class") == "PUBLIC" or grant.get("sensitive_consent") is True)
        and (grant.get("side_effect_free") is True or grant.get("effect_consent") is True)
        and grant.get("prohibited") is not True
    ):
        return "ALLOW", ["DEMO_TASK_SCOPE_B_LEGITIMATE" if grant.get("reason") == "SERVER_TASK_SCOPE_ACCESS_VERIFIED" else "DEMO_EXACT_AUTHORITY_B_LEGITIMATE"]
    if (
        grant
        and grant.get("explicit_user_scope") is True
        and grant.get("authorized") is True
        and grant.get("data_class") == "PUBLIC"
        and (grant.get("side_effect_free") is True or grant.get("effect_consent") is True)
        and grant.get("prohibited") is not True
        and explicit_semantics(observations)
    ):
        return "ALLOW", ["EXPLICIT_USER_SCOPE_B_LEGITIMATE"]
    return "CONFIRM", ["DEMO_AUTHORITY_OR_SEMANTICS_UNRESOLVED"]
