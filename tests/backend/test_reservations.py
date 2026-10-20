from concurrent.futures import ThreadPoolExecutor

import pytest
from test_policy import candidate


def post_session(repo):
    return repo.create_session({"task_kind": "POST_COMMENT", "user_request": "comment", "issue_id": 42,
                                "allowed_comment_body": "done"})


def test_reserve_write_race_unknown_no_refund(repo):
    from app.common import SafeError
    session = post_session(repo)
    calls = [repo.check(candidate(session, "post_issue_comment", {"issue_id": 42, "body": "done"})) for _ in range(2)]
    payload = {"tool_name": "post_issue_comment", "backend_id": "demo.v1", "args": {"issue_id": 42, "body": "done"}}
    def reserve(call):
        try:
            return repo.reserve(call["call_id"], payload)
        except SafeError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(reserve, calls))
    assert sum(x is not None for x in replies) == 1
    reserved = next(x for x in replies if x)
    repo.report(reserved["call_id"], {"reservation_id": reserved["reservation_id"], "state": "UNKNOWN"})
    with pytest.raises(SafeError, match="EXECUTION_OUTCOME_UNKNOWN"):
        repo.reserve(reserved["call_id"], payload)
    with repo.tx() as db:
        assert repo.session(db, session["session_id"])["write_budget"] == 0


def test_confirm_pending_and_binding_stale(repo):
    from app.common import SafeError
    session = post_session(repo)
    call = repo.check(candidate(session, "post_issue_comment", {"issue_id": 42, "body": "changed"}))
    payload = {"tool_name": "post_issue_comment", "backend_id": "demo.v1", "args": {"issue_id": 42, "body": "changed"}}
    with pytest.raises(SafeError, match="APPROVAL_PENDING"):
        repo.reserve(call["call_id"], payload)
    payload["args"]["body"] = "done"
    with pytest.raises(SafeError, match="ACTION_BINDING_MISMATCH"):
        repo.reserve(call["call_id"], payload)
