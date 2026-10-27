"""Mentor findings: local MVP controls, never paid model/identity calls."""
import asyncio
import json
import sqlite3
from dataclasses import replace

import httpx
import pytest
from cryptography.fernet import Fernet
from starlette.requests import Request

from app.common import digest
from app.pdp.diagnostics import AnalysisFailure
from app.transparent.engine import Engine
from app.transparent.jev import JevClient, JevSettings, _sensitive_value
from app.transparent.server import create_app, public_app

KEYS = {"machine_id": "m", "machine": "synthetic-machine", "human": "synthetic-human",
        "ticket": lambda *_: "synthetic-not-a-ticket"}


def request(app, path="/health", token=None, method="GET", body=None):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="https://control") as client:
            return await client.request(method, path, json=body,
                                        headers={"Authorization": "Bearer " + token} if token else {})
    return asyncio.run(run())


def test_pr01_operator_history_cannot_cross_machine_owner(engine):
    engine.turn("other-machine", "other-session", "t", "Read release.", "/files")
    engine.register("other-machine", "other-session", "t", "other-call", "read_file", {"path": "docs/release.md"}, "mcp")
    response = request(public_app(create_app(engine, KEYS)), "/history", KEYS["human"])
    assert response.status_code == 200
    assert response.json()["calls"] == []


def test_pr02_personal_data_is_sensitive_before_provider_request():
    assert _sensitive_value({"state": {"source": "Contact alice@example.com, phone 010-1234-5678."}})


def test_pr03_security_headers_on_api_response(engine):
    response = request(public_app(create_app(engine, KEYS)))
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]
    assert response.headers["strict-transport-security"] == "max-age=31536000"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_loc01_public_health_does_not_disclose_policy_or_provider(engine):
    app = public_app(create_app(engine, KEYS))
    assert request(app).json() == {"status": "ok"}
    assert request(app, token=KEYS["machine"]).json()["decision_policy"] == engine.policy


def operator_keys(permission, *, expires=2000000000):
    return {**KEYS, "operators": [{"subject": "viewer", "token_sha256": digest("synthetic-scoped-token"),
                                   "permissions": [permission], "expires_at": expires}]}


def test_pr01_viewer_cannot_approve_or_purge_and_expired_credentials_fail(engine):
    app = public_app(create_app(engine, operator_keys("history:read")))
    token = "synthetic-scoped-token"
    assert request(app, "/history", token).status_code == 200
    for path, body in (("/approval", {"call": "c", "approve": True}), ("/sessions/forget", {"session": "s"})):
        response = request(app, path, token, "POST", body)
        assert response.status_code == 403 and response.json()["code"] == "OPERATOR_PERMISSION_REQUIRED"
    expired = public_app(create_app(engine, operator_keys("history:read", expires=1)))
    assert request(expired, "/history", token).status_code == 403


def test_pr01_operator_cannot_purge_other_owner_or_forge_owner_field(engine):
    engine.turn("other", "foreign", "t", "Read release.", "/files")
    app = public_app(create_app(engine, KEYS))
    response = request(app, "/sessions/forget", KEYS["human"], "POST", {"session": "foreign"})
    assert response.status_code == 403
    with engine.db() as db:
        assert db.execute("SELECT 1 FROM sessions WHERE id='foreign'").fetchone()
    assert request(app, "/sessions/forget", KEYS["human"], "POST", {"session": "foreign", "owner": "other"}).status_code == 403


@pytest.mark.parametrize("personal", ["alice@example.com", "010-1234-5678", "+82 10 1234 5678", "900101-1234567", "123-45-6789", "성명: 홍길동", "서울시 강남구 테헤란로 123"])
def test_pr02_personal_payload_is_never_sent_or_reserved(tmp_path, personal):
    key = tmp_path / "jev.api-key"
    key.write_text("synthetic-never-sent-api-key")
    budget = tmp_path / "typesafe-budget.sqlite3"
    settings = JevSettings(True, key_path=key, budget_path=budget, request_limit=4, input_token_limit=256000, policy_id="privacy-test", data_policy="nonpersonal_only")
    client = JevClient(settings, transport=httpx.MockTransport(lambda _: pytest.fail("PII must not leave process")))
    with pytest.raises(AnalysisFailure) as failure:
        asyncio.run(client.observe("A", {"user_request": personal},
                                  {"relation": {"type": "choice", "instructions": "Check task scope", "criteria": {"YES": "yes", "NO": "no"}}}, "pii-case"))
    assert failure.value.diagnostics[0]["code"] == "JEV_PII_INPUT"
    assert not budget.exists()
    assert not replace(settings, data_policy="allow_personal").authorized()


def test_pr02_hashes_and_bounded_nonpersonal_text_do_not_look_like_pii():
    from app.transparent.privacy import contains_pii
    assert not contains_pii({"hash": "abc9001011234567def", "note": "release 2026-10-26; revision 48217"})


def test_pr04_configurable_deadline_deletes_context_and_records_safe_evidence(engine_factory, monkeypatch):
    now = [1000000.]
    monkeypatch.setattr("time.time", lambda: now[0])
    monkeypatch.setenv("WITH_HUMAN_SESSION_TTL_SECONDS", "60")
    monkeypatch.setenv("WITH_HUMAN_HISTORY_TTL_SECONDS", "120")
    engine = engine_factory()
    engine.turn("m", "s", "t", "Private task context canary.", "/files")
    engine.register("m", "s", "t", "c", "read_file", {"path": "docs/release.md"}, "mcp")
    now[0] += 121
    assert engine.history(machine="m") == []
    with engine.db() as db:
        assert db.execute("SELECT count(*) FROM turns").fetchone()[0] == 0
        row = db.execute("SELECT session_hash,counts FROM deletion_evidence").fetchone()
        assert row["session_hash"] == digest("s") and json.loads(row["counts"])["calls"] == 1
    with sqlite3.connect(engine.path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.parametrize("value", ["0", "-1", "nan", "604801"])
def test_pr04_invalid_or_excessive_retention_fails_startup(engine_factory, monkeypatch, value):
    monkeypatch.setenv("WITH_HUMAN_HISTORY_TTL_SECONDS", value)
    with pytest.raises(ValueError, match="RETENTION_POLICY_INVALID"):
        engine_factory()


def test_pr04_restart_cannot_extend_existing_retention_deadline(tmp_path, monkeypatch):
    now = [1000000.]
    monkeypatch.setattr("time.time", lambda: now[0])
    monkeypatch.setenv("WITH_HUMAN_SESSION_TTL_SECONDS", "60")
    monkeypatch.setenv("WITH_HUMAN_HISTORY_TTL_SECONDS", "120")
    key = Fernet.generate_key()
    grant = {"workspace": "/files", "tools": {"mcp": ["read_file"], "native": []}}
    path = tmp_path / "control.sqlite3"
    original = Engine(path, key, grant)
    original.turn("m", "s", "t", "Read the release", "/files")
    monkeypatch.setenv("WITH_HUMAN_HISTORY_TTL_SECONDS", "240")
    later = Engine(path, key, grant)
    with later.db() as db:
        assert db.execute("SELECT deadline FROM retention_deadlines WHERE session='s'").fetchone()[0] == 1000120
    now[0] += 121
    later.history()
    with later.db() as db:
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_pr03_legacy_control_authentication_error_also_has_security_headers(monkeypatch):
    main = pytest.importorskip("app.control.main")
    monkeypatch.setattr(main, "secret_file", lambda _: "synthetic-credential")
    monkeypatch.setattr(main.AuthAudit, "record", lambda *_: None)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="https://control:8000") as client:
            return await client.get("/v1/sessions")
    response = asyncio.run(run())
    assert response.status_code == 401
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_pr03_legacy_control_generic_error_also_has_security_headers():
    main = pytest.importorskip("app.control.main")
    response = asyncio.run(main.unknown_error(Request({"type": "http", "scheme": "https", "method": "GET",
                                                     "server": ("control", 8000), "query_string": b"",
                                                     "path": "/healthz", "headers": []}), RuntimeError()))
    assert response.status_code == 503
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["strict-transport-security"] == "max-age=31536000"


@pytest.mark.parametrize("mutation", ["duplicate", "unknown_permission", "unhashable_permission"])
def test_pr01_malformed_operator_policy_fails_startup(engine, mutation):
    keys = operator_keys("history:read")
    if mutation == "duplicate":
        keys["operators"].append(dict(keys["operators"][0]))
    else:
        keys["operators"][0]["permissions"] = ["root:all"] if mutation == "unknown_permission" else [[]]
    with pytest.raises(ValueError, match="OPERATOR_POLICY_INVALID"):
        create_app(engine, keys)


@pytest.mark.parametrize("token", ["", " ", "a b", "\u00ff", None])
def test_pr01_invalid_bearer_cannot_match_an_operator(token):
    from app.transparent.operator_access import OperatorAccess
    access = OperatorAccess("m", "synthetic-bootstrap")
    assert access.authenticate(token) is None


def test_pr01_empty_token_hash_and_empty_bootstrap_are_rejected(engine):
    keys = operator_keys("history:read")
    keys["operators"][0]["token_sha256"] = digest("")
    with pytest.raises(ValueError, match="OPERATOR_POLICY_INVALID"):
        create_app(engine, keys)
    with pytest.raises(ValueError):
        create_app(engine, {**KEYS, "human": ""})
    with pytest.raises(ValueError):
        create_app(engine, {**KEYS, "machine": ""})


def test_pr03_public_private_boundary_and_fail_closed_errors_have_headers(engine, monkeypatch):
    private = create_app(engine, KEYS)
    public = public_app(private)
    denied = request(public, "/authz", method="POST", body={})
    assert denied.status_code == 403 and denied.headers["referrer-policy"] == "no-referrer"
    monkeypatch.setattr(private.state.auth_audit, "record", lambda *_: (_ for _ in ()).throw(OSError()))
    failed = request(public, "/authz", method="POST", body={})
    assert failed.status_code == 503 and failed.headers["strict-transport-security"] == "max-age=31536000"
    monkeypatch.setattr(engine, "history", lambda **_: (_ for _ in ()).throw(RuntimeError()))
    failed = request(public, "/history", KEYS["human"])
    assert failed.status_code == 503 and failed.headers["x-content-type-options"] == "nosniff"
