import sqlite3

from app.storage.auth_audit import AuthAudit


def test_durable_bounded_credential_free_failure_audit(tmp_path, monkeypatch):
    path = tmp_path / "auth.sqlite3"
    clock = [1000000.0]
    monkeypatch.setattr("app.storage.auth_audit.time.time", lambda: clock[0])
    for _ in range(30):
        AuthAudit(path).record("HUMAN", 401)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count,sum(count) FROM auth_failures").fetchone() == (30, 30)
        assert len(db.execute("PRAGMA table_info(auth_failures)").fetchall()) == 6
    clock[0] += 86401
    AuthAudit(path).record("SERVICE", 429)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT surface,count FROM auth_failures").fetchall() == [("SERVICE", 1)]
