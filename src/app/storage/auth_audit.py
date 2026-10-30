"""Bounded durable credential-free failure records, independent of sessions."""

from app.private_files import private_connect
import time


class AuthAudit:
    def __init__(self, path):
        self.path = str(path)

    def record(self, surface, status):
        # No bearer, token hash, URL, IP, raw headers, or error text is persisted.
        if surface not in ("HUMAN", "SERVICE", "AGENT") or status not in (401, 403, 429):
            raise ValueError("Fixed authentication audit values required")
        with private_connect(self.path, timeout=1) as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute(
                "CREATE TABLE IF NOT EXISTS auth_failures (bucket INTEGER, surface TEXT, status INTEGER, count INTEGER, first_at REAL, last_at REAL, PRIMARY KEY(bucket,surface,status))"
            )
            db.execute("BEGIN IMMEDIATE")
            now = time.time()
            db.execute("DELETE FROM auth_failures WHERE last_at<=?", (now - 86400,))
            db.execute(
                "INSERT INTO auth_failures VALUES (?,?,?,?,?,?) ON CONFLICT(bucket,surface,status) DO UPDATE SET count=count+1,last_at=excluded.last_at",
                (int(now // 10), surface, status, 1, now, now),
            )
