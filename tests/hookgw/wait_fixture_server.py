"""Isolated integration fixture; never a product entry point or deployed route.

Advances only the Engine module's clock. The real ticket/upstream clocks stay
untouched, so a successful delayed reservation still needs a fresh short ticket.
"""
import asyncio
import json
import ssl
import time
from pathlib import Path
from types import SimpleNamespace

import uvicorn
from fastapi import Request

import app.transparent.engine as engine_module
from app.common import canonical, digest
from app.transparent.engine import Engine, Rejected
from app.transparent.jev import JevClient
from app.transparent.jev_policy import JevPolicy
from app.transparent.server import create_app, public_app, secret, ticket


def main():
    clock = {"offset": 0.0}
    engine_module.time = SimpleNamespace(time=lambda: time.time() + clock["offset"])
    engine = Engine("/data/control.sqlite3", secret("storage.key").encode(),
                    json.loads(Path("/runtime/grant.json").read_text()),
                    policy_router=JevPolicy(JevClient()))
    original_grant = json.loads(canonical(engine.grant))
    original_hash, original_policy = engine.grant_hash, engine.policy
    app = create_app(engine, {"machine": secret("machine.token"), "human": secret("human.token"),
                              "machine_id": secret("machine.id"), "ticket": ticket})

    @app.post("/fixture-control")
    async def control(request: Request):
        # Fixture-only machine-authenticated route on a new isolated DB/network.
        if request.headers.get("authorization") != "Bearer " + secret("machine.token"):
            raise Rejected("AUTHENTICATION_FAILED")
        value = await request.json()
        action = value["action"]
        if action == "advance":
            clock["offset"] += float(value["seconds"])
        elif action == "reset":
            clock["offset"] = 0.0
            engine.grant = json.loads(canonical(original_grant))
            engine.grant_hash, engine.policy = original_hash, original_policy
        elif action == "grant":
            engine.grant_hash = "fixture-changed-grant"
        elif action == "policy":
            engine.policy = "fixture-changed-policy"
        elif action == "protected":
            engine.grant["protected_markers"].append("notes.txt")
        elif action in ("unknown", "gap", "semantic", "source", "request", "session_expiry", "connection_expiry", "analysis_stop"):
            with engine.db() as db:
                row = db.execute("SELECT * FROM calls WHERE id=?", (value["call"],)).fetchone()
                if action == "unknown":
                    db.execute("UPDATE calls SET state='UNKNOWN' WHERE id=?", (row["id"],))
                elif action == "gap":
                    db.execute("INSERT INTO calls SELECT id||':gap',session,turn,hash,path,'UNKNOWN',decision,reason,body,created FROM calls WHERE id=?", (row["id"],))
                elif action == "semantic":
                    reason = json.loads(row["reason"])
                    reason["policy_trace"]["routing"] = "SEMANTIC"
                    reason["reasons"] = ["USER_INTENT_SUPPORTED"]
                    db.execute("UPDATE calls SET reason=? WHERE id=?", (canonical(reason), row["id"]))
                elif action == "request":
                    db.execute("UPDATE turns SET body=? WHERE session=? AND id=?", (engine.seal({"prompt": "Changed user context."}), row["session"], row["turn"]))
                elif action == "session_expiry":
                    db.execute("UPDATE expiry SET deadline=0 WHERE kind='session' AND id=?", (row["session"],))
                elif action == "connection_expiry":
                    db.execute("UPDATE expiry SET deadline=0 WHERE kind='connection' AND id IN (SELECT hash FROM connections WHERE session=?)", (row["session"],))
                elif action == "analysis_stop":
                    db.execute("INSERT INTO analysis_stops VALUES(?,?,?)", (digest(row["session"]), digest(row["turn"]), canonical({"fixture": True})))
                else:
                    db.execute("INSERT INTO sources VALUES(?,?,?,?)", (row["id"]+":source", row["session"], row["id"]+":sourcecall", engine.seal({"source_id": "fixture", "analysis_complete": False})))
        else:
            raise Rejected("INVALID_EVENT")
        return {"fixture": True, "clock_offset": clock["offset"]}

    async def serve():
        options = dict(host="0.0.0.0", ssl_certfile="/runtime/control.pem", ssl_keyfile="/runtime/control.key",
                       access_log=False, proxy_headers=False, log_level="critical")
        await asyncio.gather(uvicorn.Server(uvicorn.Config(public_app(app), port=8030, **options)).serve(),
                             uvicorn.Server(uvicorn.Config(app, port=8050, ssl_ca_certs="/runtime/ca.pem", ssl_cert_reqs=ssl.CERT_REQUIRED, **options)).serve())
    asyncio.run(serve())


if __name__ == "__main__":
    main()
