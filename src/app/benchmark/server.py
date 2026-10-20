"""Benchmark service factory reusing product authentication, Engine and TLS."""

import asyncio
import json
import ssl
from pathlib import Path

import uvicorn
from fastapi import Request

from app.transparent.engine import Engine, Rejected
from app.transparent.server import create_app, public_app, secret, ticket


def control_app(path, registry, policy, catalog=None, *, engine_factory=Engine):
    runtime = Path(path)
    grant = json.loads((runtime / "grant.json").read_text())
    if grant["tools"] != {
        "native": [],
        "mcp": [registry.name(e["server"], e["name"]) for e in registry.entries],
    }:
        raise ValueError("BENCHMARK_GRANT_REGISTRY_MISMATCH")
    engine = engine_factory(
        "/data/control.sqlite3",
        (runtime / "storage.key").read_text().strip().encode(),
        grant,
        policy_router=policy,
    )
    machine = (runtime / "machine.id").read_text().strip()
    machine_token = (runtime / "machine.token").read_text().strip()
    app = create_app(
        engine,
        {
            "machine": machine_token,
            "human": secret("human.token"),
            "machine_id": machine,
            "ticket": ticket,
        },
        max_body_bytes=1114112,
    )
    app.state.runtime_engine = engine

    @app.post("/benchmark/catalog")
    async def collect_catalog(request: Request):
        import hmac
        from uuid import uuid4

        from app.common import canonical, digest

        if not hmac.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + machine_token
        ):
            raise Rejected("ROLE_AUTHENTICATION_FAILED")
        value = await request.json()
        if set(value) != {"connection"} or catalog is None:
            raise Rejected("INVALID_EVENT")
        m, session = engine.connection(value["connection"])
        sid = "catalog-" + digest(canonical(catalog))
        source = {
            "source_id": str(uuid4()),
            "call_id": sid,
            "origin": "mcp",
            "same_issue": False,
            "collection_kind": "MCP_CATALOG_UNTRUSTED_DATA",
            **engine.source_material(canonical(catalog)),
        }
        if not source["analysis_complete"]:
            raise Rejected("SOURCE_CONTEXT_INCOMPLETE")
        with engine.db() as db:
            engine._current(db, m, session)
            if db.execute(
                "SELECT 1 FROM sources WHERE session=? AND call=?", (session, sid)
            ).fetchone():
                raise Rejected("CATALOG_REPLAY")
            db.execute(
                "INSERT INTO sources VALUES(?,?,?,?)",
                (source["source_id"], session, sid, engine.seal(source)),
            )
            engine.audit(db, "MCP_CATALOG", "OBSERVED")
        return {"state": "CATALOG_OBSERVED", "untrusted_data_only": True}

    @app.post("/benchmark/close")
    async def close(request: Request):
        import hmac

        if not hmac.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + machine_token
        ):
            raise Rejected("ROLE_AUTHENTICATION_FAILED")
        value = await request.json()
        if set(value) != {"connection"}:
            raise Rejected("INVALID_EVENT")
        return engine.close_demo_connection(machine, value["connection"])

    return app


def serve_control(app, path):
    runtime = Path(path)

    async def serve():
        opts = dict(
            host="0.0.0.0",
            ssl_certfile=str(runtime / "control.pem"),
            ssl_keyfile=str(runtime / "control.key"),
            access_log=False,
            proxy_headers=False,
            log_level="critical",
        )
        await asyncio.gather(
            uvicorn.Server(uvicorn.Config(public_app(app), port=8030, **opts)).serve(),
            uvicorn.Server(
                uvicorn.Config(
                    app,
                    port=8050,
                    ssl_ca_certs=str(runtime / "ca.pem"),
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    **opts,
                )
            ).serve(),
        )

    asyncio.run(serve())


def serve_proxy(app, path):
    runtime = Path(path)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8060,
        ssl_certfile=str(runtime / "upstream.pem"),
        ssl_keyfile=str(runtime / "upstream.key"),
        ssl_ca_certs=str(runtime / "ca.pem"),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        access_log=False,
        proxy_headers=False,
        log_level="critical",
    )
