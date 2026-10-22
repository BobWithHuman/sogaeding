"""Authenticated adapter API and real agentgateway HTTP extAuthz target."""
import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import ssl
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from jsonschema import Draft202012Validator

from app.common import CONTRACT_DIR, canonical, digest, strict_json
from app.storage.auth_audit import AuthAudit
from app.transparent.engine import Engine, Rejected

RUNTIME = Path(os.environ.get("HOOKGW_RUNTIME", "/runtime"))
REJECTION_CODES = {
    "AUTHENTICATION_FAILED", "AUTH_RATE_LIMIT", "CONNECTION_BINDING", "CONNECTION_OR_SESSION_EXPIRED",
    "FORWARD_SNAPSHOT_STALE", "SESSION_OR_TURN_MISMATCH", "PRIOR_RESULT_UNOBSERVED",
    "NO_UNIQUE_HOOK_BINDING", "FORWARD_REPLAY", "NO_USER_TURN", "UNSUPPORTED_RPC",
    "INVALID_RPC", "INVALID_RPC_METADATA",
    "DEMO_POLICY_DENIED", "DEMO_CONFIRM_NOT_DISPATCHED",
    "DEMO_RESUME_RPC_BINDING", "DEMO_APPROVAL_REJECTED", "DEMO_APPROVAL_EXPIRED", "DEMO_APPROVAL_STALE", "DEMO_APPROVAL_CONSUMED",
}
REQUEST_ID = re.compile(r"[a-f0-9]{32}\Z")


def rejection_binding(connection, request_id, tool, args):
    if not isinstance(connection, str) or not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id) or not isinstance(tool, str) or not isinstance(args, dict):
        return None
    return digest(canonical({"connection_hash": digest(connection), "request_id": request_id,
                             "tool": tool, "args": args}))


def secret(name):
    return (RUNTIME / name).read_text(encoding="ascii").strip()


def ticket(call, body):
    data = canonical({"call": call, "hash": hashlib.sha256(body).hexdigest(), "expires": int(time.time()) + 30})
    import base64
    encoded = base64.urlsafe_b64encode(data.encode()).decode()
    sig = hmac.new(secret("forward.key").encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + "." + sig


def create_app(engine, keys, *, max_body_bytes=131072):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    machine = keys["machine_id"]
    event_schema = Draft202012Validator(json.loads((CONTRACT_DIR / "spec5.schema.json").read_text(encoding="utf-8")))
    app.state.auth_audit = AuthAudit(str(engine.path) + ".auth")

    def auth(request, role):
        request.state.auth_surface = "HUMAN" if role == "human" else "SERVICE"
        # Session audit eviction must not reset the durable authentication limit.
        path = Path(app.state.auth_audit.path)
        if path.exists():
            with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1) as db:
                failures = db.execute("SELECT coalesce(sum(count),0) FROM auth_failures WHERE last_at>?", (time.time()-60,)).fetchone()[0]
            if failures >= 10:
                raise Rejected("AUTH_RATE_LIMIT")
        value = request.headers.get("authorization", "")
        if not hmac.compare_digest(value, "Bearer " + keys[role]):
            with engine.db() as db:
                engine.audit(db, "AUTH", "AUTHENTICATION_FAILED")
            raise Rejected("AUTHENTICATION_FAILED")

    async def body(request):
        raw = bytearray()
        async for part in request.stream():
            raw.extend(part)
            if len(raw) > max_body_bytes:
                raise Rejected("BODY_LIMIT")
        return bytes(raw), strict_json(bytes(raw))

    @app.exception_handler(Rejected)
    async def rejection(_req, exc):
        if exc.code in {"AUTHENTICATION_FAILED", "AUTH_RATE_LIMIT", "CONNECTION_BINDING", "CONNECTION_OR_SESSION_EXPIRED"}:
            try:
                app.state.auth_audit.record(getattr(_req.state, "auth_surface", "AGENT"), 429 if exc.code == "AUTH_RATE_LIMIT" else 403)
            except Exception:
                return JSONResponse({"code": "ADAPTER_UNAVAILABLE"}, status_code=503)
        call = getattr(_req.state, "bound_call", "")
        with engine.db() as db:
            engine.audit(db, "REJECT", exc.code, call)
            binding = getattr(_req.state, "rejection_binding", None)
            if binding and exc.code in REJECTION_CODES:
                db.execute("DELETE FROM gateway_rejections WHERE at<?", (time.time() - 60,))
                db.execute("INSERT OR IGNORE INTO gateway_rejections VALUES(?,?,?,?)",
                           (binding, time.time(), exc.code, digest(call) if call else None))
                db.execute("DELETE FROM gateway_rejections WHERE request NOT IN (SELECT request FROM gateway_rejections ORDER BY at DESC LIMIT 128)")
        return JSONResponse({"code": exc.code}, status_code=403)

    @app.exception_handler(Exception)
    async def unavailable(_req, _exc):
        return JSONResponse({"code": "ADAPTER_UNAVAILABLE"}, status_code=503)

    @app.get("/health")
    async def health():
        if engine.policy_router:
            return {"spec": "MVP-SPEC-5", "judge_mode": "JEV_OFFLINE_FIXTURE" if getattr(engine.policy_router.client, "is_fixture", False) else "JEV_USER_LIVE" if engine.policy_router.client.settings.authorized() else "JEV_RULES_ONLY", "decision_policy": engine.policy,
                    "jev_live": "NOT_AUTHORIZED" if not engine.policy_router.client.settings.authorized() else "USER_CONFIGURED_NOT_EVALUATED",
                    **({"demo_dispatch": "post_host_approval_v1"} if os.environ.get("HOOKGW_DEMO_DISPATCH") == "1" else {})}
        mode = "OFFLINE_FIXTURE" if getattr(engine.judge, "is_fixture", False) else "LIVE_USER" if engine.judge is not None else "UNAVAILABLE"
        return {"spec": "MVP-SPEC-5", "judge_mode": mode}

    @app.post("/connect")
    async def connect(request: Request):
        auth(request, "machine")
        token = secrets.token_urlsafe(48)
        engine.connect(machine, token)
        return {"connection": token}

    @app.post("/disconnect")
    async def disconnect(request: Request):
        auth(request, "machine")
        _, value = await body(request)
        if not isinstance(value, dict) or set(value) != {"connection"} or not isinstance(value["connection"], str):
            raise Rejected("INVALID_EVENT")
        return engine.disconnect_metadata(machine, value["connection"])

    @app.post("/event")
    async def event(request: Request):
        auth(request, "machine")
        _raw, value = await body(request)
        # Source labels, user_request, decisions and trust claims never come from tool args.
        allowed = {"event", "connection", "session", "turn", "prompt", "cwd", "call", "tool", "args", "output", "failed", "route", "action_hash"}
        if not isinstance(value, dict) or set(value) - allowed or not event_schema.is_valid(value):
            raise Rejected("INVALID_EVENT")
        m, session = engine.connection(value["connection"], value["session"])
        kind = value["event"]
        if kind == "UserPromptSubmit":
            return engine.turn(m, session, value["turn"], value["prompt"], value["cwd"])
        if kind == "PreToolUse":
            result = engine.register(m, session, value["turn"], value["call"], value["tool"], value["args"], value["route"])
            return {**result, **await engine.authorize(m, value["call"])}
        if kind == "ApprovalPoll":
            with engine.db() as db:
                row = db.execute("SELECT state FROM calls WHERE id=? AND session=? AND turn=?", (value["call"], session, value["turn"])).fetchone()
            if not row:
                raise Rejected("UNKNOWN_CALL")
            if row["state"] == "APPROVED":
                return engine.consume_approval(m, value["call"], value["action_hash"])
            return {"state": row["state"], "decision": "CONFIRM" if row["state"] == "CONFIRM" else "DENY"}
        if kind == "PostToolUse":
            return engine.observe(m, value["call"], value["tool"], value["args"], value["output"], value.get("failed", False))
        raise Rejected("UNSUPPORTED_EVENT")

    @app.post("/transport-failure")
    async def failure(request: Request):
        auth(request, "machine")
        _, value = await body(request)
        if set(value) != {"connection", "tool", "args"}:
            raise Rejected("INVALID_EVENT")
        m, session = engine.connection(value["connection"])
        engine.transport_failure(m, session, value["tool"], value["args"])
        return {"state": "UNKNOWN_IF_FORWARDED"}

    @app.post("/demo/intent")
    async def demo_intent(request: Request):
        if os.environ.get("HOOKGW_DEMO_DISPATCH") != "1":
            return JSONResponse({"code": "DEMO_NOT_ENABLED"}, status_code=404)
        auth(request, "machine")
        _, value = await body(request)
        fields = {"event", "connection", "session", "turn", "call", "tool", "args", "route"}
        if (not isinstance(value, dict) or set(value) != fields or not event_schema.is_valid(value)
                or value["event"] != "PreToolUse" or value["route"] != "mcp"):
            raise Rejected("INVALID_EVENT")
        m, session = engine.connection(value["connection"], value["session"])
        return engine.register_demo_intent(m, session, value["turn"], value["call"], value["tool"], value["args"], value["connection"])

    @app.post("/demo/close")
    async def demo_close(request: Request):
        if os.environ.get("HOOKGW_DEMO_DISPATCH") != "1":
            return JSONResponse({"code": "DEMO_NOT_ENABLED"}, status_code=404)
        auth(request, "machine")
        _, value = await body(request)
        if (not isinstance(value, dict) or set(value) != {"connection"}
                or not isinstance(value["connection"], str) or not 1 <= len(value["connection"]) <= 512):
            raise Rejected("INVALID_EVENT")
        return engine.close_demo_connection(machine, value["connection"])

    @app.post("/demo/wait")
    async def demo_wait(request: Request):
        if os.environ.get("HOOKGW_DEMO_DISPATCH") != "1":
            return JSONResponse({"code": "DEMO_NOT_ENABLED"}, status_code=404)
        auth(request, "machine")
        _, value = await body(request)
        if (not isinstance(value, dict) or set(value) != {"connection", "tool", "args"}
                or not isinstance(value["connection"], str) or not 1 <= len(value["connection"]) <= 512
                or not isinstance(value["tool"], str) or not isinstance(value["args"], dict)):
            raise Rejected("INVALID_EVENT")
        m, session = engine.connection(value["connection"])
        if m != machine:
            raise Rejected("CONNECTION_BINDING")
        from app.transparent.demo_approval import wait
        return wait(engine, m, session, value["tool"], value["args"], value["connection"])

    @app.get("/demo/pending")
    async def demo_pending(request: Request):
        if os.environ.get("HOOKGW_DEMO_DISPATCH") != "1":
            return JSONResponse({"code": "DEMO_NOT_ENABLED"}, status_code=404)
        auth(request, "human")
        from app.transparent.demo_approval import pending
        return pending(engine, machine)

    @app.post("/transport-observed")
    async def transport(request: Request):
        auth(request, "machine")
        _, value = await body(request)
        if set(value) != {"connection", "tool", "args", "result"}:
            raise Rejected("INVALID_EVENT")
        m, session = engine.connection(value["connection"])
        outcome = engine.transport_observed(m, session, value["tool"], value["args"], value["result"])
        if outcome:
            return outcome
        return {"state": "RESPONSE_OBSERVED_NOT_RECEIPT"}

    @app.post("/transport-rejection")
    async def transport_rejection(request: Request):
        # Separate authenticated Control channel: never trust gateway/upstream error bodies.
        auth(request, "machine")
        _, value = await body(request)
        if not isinstance(value, dict) or set(value) != {"connection", "request_id", "tool", "args"}:
            raise Rejected("INVALID_EVENT")
        binding = rejection_binding(value["connection"], value["request_id"], value["tool"], value["args"])
        with engine.db() as db:
            row = db.execute("SELECT code,call_hash FROM gateway_rejections WHERE request=? AND at>=?",
                             (binding, time.time() - 60)).fetchone() if binding else None
        if not row or row["code"] not in REJECTION_CODES:
            return {"origin": "UNCONFIRMED", "code": "HTTP_REJECTION_UNCLASSIFIED"}
        return {"origin": "CONTROL", "reason": row["code"], "call_ref": row["call_hash"]}

    @app.post("/authz")
    async def authz(request: Request):
        # This endpoint is only mounted on the private mTLS listener in deployment.
        raw, value = await body(request)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if isinstance(value, dict) and value.get("method") == "tools/call" and isinstance(value.get("params"), dict):
            params = value["params"]
            request.state.rejection_binding = rejection_binding(token, request.headers.get("x-with-human-request"), params.get("name"), params.get("arguments"))
        m, session = engine.connection(token)
        if not isinstance(value, dict) or value.get("jsonrpc") != "2.0" or set(value) - {"jsonrpc", "id", "method", "params"}:
            raise Rejected("INVALID_RPC")
        method = value.get("method")
        if method in ("initialize", "notifications/initialized", "ping", "tools/list"):
            return Response(status_code=200)
        if not session:
            raise Rejected("NO_USER_TURN")
        if method != "tools/call" or "id" not in value:
            raise Rejected("UNSUPPORTED_RPC")
        params = value.get("params", {})
        if set(params) - {"name", "arguments", "_meta"} or not isinstance(params.get("arguments"), dict):
            raise Rejected("INVALID_RPC")
        if "_meta" in params and (not isinstance(params["_meta"], dict) or len(canonical(params["_meta"]).encode()) > 4096):
            raise Rejected("INVALID_RPC_METADATA")
        if os.environ.get("HOOKGW_DEMO_DISPATCH") == "1":
            from app.transparent.demo_approval import resume
            rpc_hash = digest(canonical(value))
            call = resume(engine, m, session, params["name"], params["arguments"], token, rpc_hash)
            if call is not None:
                request.state.bound_call = call
                return Response(status_code=200, headers={"x-with-human-forward": keys["ticket"](call, raw)})
            call = engine.claim_demo_intent(m, session, params["name"], params["arguments"], token, rpc_hash=rpc_hash)
            request.state.bound_call = call
            outcome = await engine.authorize(m, call, demo_connection=token)
            if outcome["decision"] != "ALLOW":
                raise Rejected("DEMO_CONFIRM_NOT_DISPATCHED" if outcome["decision"] == "CONFIRM" else "DEMO_POLICY_DENIED")
        else:
            call = engine.pending_mcp(m, session, params["name"], params["arguments"])
        request.state.bound_call = call
        engine.forward(m, call, connection_token=token)
        # Header is overwritten from the authz response, never trusted from the client.
        return Response(status_code=200, headers={"x-with-human-forward": keys["ticket"](call, raw)})

    @app.get("/history")
    async def history(request: Request):
        auth(request, "human")
        return {"calls": engine.history()}

    @app.get("/demo/history")
    async def demo_history(request: Request):
        if os.environ.get("HOOKGW_DEMO_VIEWER") != "1":
            return JSONResponse({"code": "DEMO_NOT_ENABLED"}, status_code=404)
        auth(request, "human")
        from app.transparent.demo_report import project
        return project(engine)

    @app.post("/approval")
    async def approval(request: Request):
        auth(request, "human")
        _, value = await body(request)
        if (not isinstance(value, dict) or set(value) not in ({"call", "approve"}, {"call", "approve", "approval_binding"})
                or type(value["approve"]) is not bool or not isinstance(value["call"], str)):
            raise Rejected("INVALID_EVENT")
        return engine.approval(machine, value["call"], value["approve"], value.get("approval_binding"))

    @app.post("/sessions/forget")
    async def forget(request: Request):
        auth(request, "human")
        _, value = await body(request)
        if set(value) != {"session"}:
            raise Rejected("INVALID_EVENT")
        engine.purge(value["session"])
        return {"state": "FORGOTTEN_LOGICALLY"}

    return app


def public_app(app):
    public = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @public.middleware("http")
    async def boundary(request, call_next):
        if request.url.path == "/authz":
            try:
                app.state.auth_audit.record("SERVICE", 403)
            except Exception:
                return JSONResponse({"code": "ADAPTER_UNAVAILABLE"}, status_code=503)
            return JSONResponse({"code": "PRIVATE_ENDPOINT"}, status_code=403)
        return await call_next(request)

    public.mount("/", app)
    return public


def main():
    grant = json.loads((RUNTIME / "grant.json").read_text(encoding="utf-8"))
    judge, router = None, None
    mode = os.environ.get("HOOKGW_PDP", "GPT")
    if mode == "JEV":
        from app.transparent.jev import JevClient
        from app.transparent.jev_config import DEFAULT_PROFILE, load_settings, make_policy
        settings = load_settings(Path(os.environ.get("JEV_POLICY_FILE", "/jev-config/policy.json")))
        profile = os.environ.get("HOOKGW_JEV_PROFILE", DEFAULT_PROFILE)
        router = make_policy(JevClient(settings), profile)
    elif mode != "GPT":
        raise RuntimeError("UNSUPPORTED_PDP_MODE")
    elif os.environ.get("HOOKGW_USER_LIVE") == "1":
        from app.transparent.judge import DevelopmentJudge
        judge = DevelopmentJudge(os.environ["JUDGE_BUDGET_DB_PATH"])
    engine = Engine(os.getenv("HOOKGW_DB", "/data/control.sqlite3"), secret("storage.key").encode(), grant, judge, policy_router=router,
                    preserve_history_on_policy_change=mode == "JEV")
    keys = {"machine": secret("machine.token"), "human": secret("human.token"), "machine_id": secret("machine.id"), "ticket": ticket}
    app = create_app(engine, keys)
    # Reject authz on the public listener even with a valid connection bearer.
    public = public_app(app)
    async def serve():
        options = dict(host="0.0.0.0", ssl_certfile=str(RUNTIME / "control.pem"), ssl_keyfile=str(RUNTIME / "control.key"),
                       access_log=False, proxy_headers=False, log_level="critical")
        await asyncio.gather(uvicorn.Server(uvicorn.Config(public, port=8030, **options)).serve(),
                             uvicorn.Server(uvicorn.Config(app, port=8050, ssl_ca_certs=str(RUNTIME / "ca.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED, **options)).serve())
    asyncio.run(serve())


if __name__ == "__main__":
    main()
