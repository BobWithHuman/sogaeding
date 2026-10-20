"""Opt-in runtime demo routing. Grants are server configuration, never source claims."""

from app.common import canonical, digest

PROFILE = "dtap-demo-allow50-scope-v2"
ALLOW_THRESHOLD = 0.50
RISK_THRESHOLD = 0.90


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
    grant = authority(snapshot, parsed)
    if grant and grant.get("prohibited") is True:
        return "DENY", "REVIEWED_OPERATION_PROHIBITED"
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


def compose(old, observations, grant):
    # Risk and A/B conflicts always take priority, using the unchanged .90 rule.
    if old[0] == "DENY":
        return old
    a, b = (observations[v][0] for v in ("A", "B"))
    if (
        a["choice"] == "WITHIN_TASK"
        and b["choice"] == "LEGITIMATE"
        and b["effective_confidence"] >= ALLOW_THRESHOLD
        and grant
        and grant.get("authorized") is True
        and (grant.get("data_class") == "PUBLIC" or grant.get("sensitive_consent") is True)
        and (grant.get("side_effect_free") is True or grant.get("effect_consent") is True)
        and grant.get("prohibited") is not True
    ):
        return "ALLOW", ["DEMO_TASK_SCOPE_B_LEGITIMATE" if grant.get("reason") == "SERVER_TASK_SCOPE_ACCESS_VERIFIED" else "DEMO_EXACT_AUTHORITY_B_LEGITIMATE"]
    return "CONFIRM", ["DEMO_AUTHORITY_OR_SEMANTICS_UNRESOLVED"]
