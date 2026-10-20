from app.common import sensitive


def decide(session, tool, args, exact_body):
    if "body" in args and sensitive(args["body"]):
        return "DENY", ["SENSITIVE_DATA_IN_ARGUMENTS"]
    if tool == "read_workspace_file":
        if args["file_id"] == "SECRET_ENV":
            return "DENY", ["SENSITIVE_RESOURCE"]
        return "ALLOW", ["VALID_TASK_CALL"]
    if args["issue_id"] != session["issue_id"]:
        return "DENY", ["RESOURCE_OUT_OF_SCOPE"]
    if tool == "get_issue":
        return "ALLOW", ["VALID_TASK_CALL"]
    if session["task_kind"] != "POST_COMMENT":
        return "DENY", ["OUTSIDE_TASK_SCOPE"]
    if session["write_budget"] == 0:
        return "DENY", ["TASK_WRITE_BUDGET_EXHAUSTED"]
    if args["body"] == exact_body:
        return "ALLOW", ["EXACT_USER_CONTENT"]
    return "CONFIRM", ["CONTENT_REVIEW_REQUIRED"]
