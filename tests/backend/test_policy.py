from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest


def candidate(session, tool, args, key=None, resume=None):
    value = {"session_id": session["session_id"], "client_request_id": key or str(uuid4()),
             "tool_name": tool, "backend_id": "demo.v1", "args": args}
    if resume:
        value["resume_call_id"] = resume
    return value


def test_policy_exact_scope_secret_and_binding(repo):
    from app.common import SafeError
    session = repo.create_session({"task_kind": "SUMMARIZE_ISSUE", "user_request": "summary", "issue_id": 42})
    assert repo.check(candidate(session, "get_issue", {"issue_id": 42}))["decision"] == "ALLOW"
    assert repo.check(candidate(session, "post_issue_comment", {"issue_id": 42, "body": "done"}))["decision"] == "DENY"
    assert repo.check(candidate(session, "read_workspace_file", {"file_id": "SECRET_ENV"}))["reason_codes"] == ["SENSITIVE_RESOURCE"]
    session = repo.create_session({"task_kind": "POST_COMMENT", "user_request": "comment", "issue_id": 42,
                                   "allowed_comment_body": "검토 완료"})
    value = candidate(session, "post_issue_comment", {"issue_id": 42, "body": "검토 완료"})
    result = repo.check(value)
    assert result["decision"] == "ALLOW"
    assert repo.check(value) == result
    value["args"]["body"] += " "
    with pytest.raises(SafeError, match="REQUEST_KEY_CONFLICT"):
        repo.check(value)
    assert repo.check(candidate(session, "post_issue_comment", {"issue_id": 42, "body": "changed"}))["decision"] == "CONFIRM"
    denied = repo.check(candidate(session, "post_issue_comment", {"issue_id": 42, "body": "DEMO_SECRET_DO_NOT_SEND"}))
    with repo.tx() as db:
        row = repo.call(db, denied["call_id"])
        assert row["canonical_cipher"] is None
        assert "DEMO_SECRET_DO_NOT_SEND" not in row["masked_args_json"]


def test_atomic_call_budget_and_canonical_unicode(repo):
    from app.common import SafeError, action, digest
    session = repo.create_session({"task_kind": "SUMMARIZE_ISSUE", "user_request": "summary", "issue_id": 42})
    def check(_):
        try:
            return repo.check(candidate(session, "get_issue", {"issue_id": 42}))
        except SafeError:
            return None
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(check, range(12)))
    assert sum(x is not None for x in outcomes) == 8
    assert digest(action("post_issue_comment", {"body": "가", "issue_id": 42})) != digest(
        action("post_issue_comment", {"body": "가 ", "issue_id": 42}))
