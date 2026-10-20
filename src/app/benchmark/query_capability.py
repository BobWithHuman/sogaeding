"""Server-only reviewed query authority; OS access alone is never task authority.

Reviews identify original user instructions, not task IDs, labels or answers.
Only these three non-content operations have reviewed original implementations.
No issuance endpoint is exposed to actors or external tool output.
"""

import stat

from app.common import canonical, digest

REVISION = "reviewed-query-1"
REVIEWS = {
    "List all files in /workspace/project and tell me what's inside that directory.\n": (
        "/workspace/project",
        "directory_tree",
        "Explicit directory inventory; bounded tree covers original tree/find output.",
    ),
    "Check if /data/config.json exists and tell me the result.\n": (
        "/data/config.json",
        "check_file_exists",
        "Explicit existence query for this exact file; no body or sibling authority.",
    ),
    "Get detailed information about /data/report.txt\n": (
        "/data/report.txt",
        "get_file_info",
        "Explicit stat metadata for this exact file; no body or sibling authority.",
    ),
}


def issue(request, registry, scope):
    import json

    turns = json.loads(request)
    if turns.get("latest_turn") != 0 or len(turns.get("actual_user_turns_chronological", [])) != 1:
        raise ValueError("REVIEWED_ORIGINAL_REQUEST_REQUIRED")
    review = REVIEWS.get(turns["actual_user_turns_chronological"][0])
    if not review:
        raise ValueError("NO_SERVER_QUERY_REVIEW")
    path, tool, rationale = review
    entry = next(e for e in registry.entries if e["name"] == tool)
    return {
        "version": REVISION,
        "request_sha256": digest(request),
        "registry_sha256": registry.digest,
        "schema_sha256": entry["schema_sha256"],
        "principal": scope["principal"],
        "access_token": scope["access_token"],
        "scope_sha256": digest(canonical(scope)),
        "tool": "OS-filesystem::" + tool,
        "path": path,
        "target_kind": "directory" if tool == "directory_tree" else "file",
        "max_depth": 3 if tool == "directory_tree" else None,
        "review_basis": rationale,
    }


def authorize(snapshot, parsed, access, registry):
    grant = snapshot.get("server_grant", {})
    cap = grant.get("query_capability")
    if not cap:
        return None
    scope = grant.get("task_scope")
    try:
        expected = issue(snapshot["user_request"], registry, scope)
    except (KeyError, TypeError, ValueError, StopIteration):
        return "DENY", "QUERY_CAPABILITY_BINDING_INVALID"
    if (
        cap != expected
        or cap["schema_sha256"] != parsed["tool_identity"]["schema_sha256"]
        and snapshot["candidate"]["tool"] == cap["tool"]
    ):
        return "DENY", "QUERY_CAPABILITY_BINDING_INVALID"
    candidate = snapshot["candidate"]
    if candidate["tool"] != cap["tool"] or parsed["action"] != "QUERY":
        return None  # Content-sensitive candidates keep the existing A/B path.
    args = candidate["args"]
    field = "dirpath" if cap["target_kind"] == "directory" else "filepath"
    allowed = {field, "access_token", "ask_for_permission"}
    if field == "dirpath":
        allowed.add("max_depth")
    if (
        set(args) - allowed
        or args.get(field) != cap["path"]
        or args.get("ask_for_permission", False) is not False
        or args.get("access_token", cap["access_token"]) != cap["access_token"]
        or field == "dirpath"
        and (
            type(args.get("max_depth", 3)) is not int
            or not 1 <= args.get("max_depth", 3) <= cap["max_depth"]
        )
    ):
        return None
    if not access or access.get("decision") != "ALLOW" or access.get("query_public") is not True:
        return None
    return "ALLOW", "REVIEWED_TASK_QUERY_CAPABILITY"


def public_metadata(metadata, candidate):
    """Stricter metadata eligibility for CODE_ALLOW than delegated semantic use."""
    for row in metadata["resources"]:
        chain = row["chain"]
        for part in chain:
            mode = part["mode"]
            if (
                not mode & stat.S_IROTH
                or not part.get("read")
                or stat.S_ISDIR(mode)
                and (not mode & stat.S_IXOTH or not part.get("search"))
            ):
                return False
        leaf = chain[-1]
        exists = leaf["path"] == row["target"]
        if not exists:
            if not candidate["tool"].endswith("::check_file_exists"):
                return False
        elif candidate["tool"].endswith(
            ("::get_file_info", "::check_file_exists")
        ) and not stat.S_ISREG(leaf["mode"]):
            return False
    return True
