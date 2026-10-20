import hashlib

import pytest


def test_session_server_grant_token_hash_and_encryption(repo):
    request = {"task_kind": "POST_COMMENT", "user_request": "private user request",
               "issue_id": 42, "allowed_comment_body": "private comment"}
    result = repo.create_session(request)
    auth = repo.resolve(result["agent_session_token"])
    assert auth["session_id"] == result["session_id"]
    with repo.tx() as db:
        session = db.execute("SELECT * FROM sessions").fetchone()
        assert session["write_budget"] == 1 and session["call_budget"] == 8
        token = db.execute("SELECT * FROM session_tokens").fetchone()
        assert token["token_sha256"] == hashlib.sha256(result["agent_session_token"].encode()).hexdigest()
        assert b"private comment" not in session["comment_cipher"]
        assert b"private user request" not in session["request_cipher"]
    repo.close(result["session_id"])
    from app.common import SafeError
    with pytest.raises(SafeError):
        repo.resolve(result["agent_session_token"])


def test_auth_invalid_expired_audience_and_schema(repo):
    from app.common import SafeError, validate_tool
    session = repo.create_session({"task_kind": "SUMMARIZE_ISSUE", "user_request": "summary", "issue_id": 42})
    with pytest.raises(SafeError):
        repo.resolve("x" * 64)
    with repo.tx() as db:
        db.execute("UPDATE session_tokens SET audience='https://other.invalid'")
    with pytest.raises(SafeError):
        repo.resolve(session["agent_session_token"])
    for args in ({"issue_id": "42"}, {"issue_id": True}, {"issue_id": 42, "trusted": True}):
        with pytest.raises(SafeError):
            validate_tool("get_issue", args)
