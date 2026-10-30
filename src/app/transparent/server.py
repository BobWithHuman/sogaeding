"""Authenticated adapter API and real agentgateway HTTP extAuthz target."""
import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
from app.private_files import private_connect
import ssl
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from jsonschema import Draft202012Validator

from app.common import CONTRACT_DIR, canonical, digest, strict_json
from app.security_headers import apply_security_headers
from app.storage.auth_audit import AuthAudit
from app.transparent import security_audit
from app.transparent.engine import Engine, Rejected
from app.transparent.operator_access import OperatorAccess, valid_token
from app.transparent.runtime_lock import lease

RUNTIME = Path(os.environ.get("HOOKGW_RUNTIME", "/runtime"))


def local_request_ok(request):
    if len(request.headers.getlist('host')) != 1 or request.url.hostname not in {'127.0.0.1','localhost','::1','control'}:
        return False
    origins = request.headers.getlist('origin')
    return not origins or len(origins) == 1 and origins[0] == request.url.scheme + '://' + request.headers['host']
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


def bearer_token(request):
    """Use the same unambiguous ASCII credential syntax on both listeners."""
    values = request.headers.getlist("authorization")
    if len(values) != 1:
        return ""
    value = values[0]
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return ""
    scheme, separator, token = value.partition(" ")
    return token if scheme == "Bearer" and separator and token and not any(c.isspace() for c in token) else ""


def create_app(engine, keys, *, max_body_bytes=131072):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    machine = keys["machine_id"]
    if not valid_token(keys["machine"]):
        raise ValueError("MACHINE_CREDENTIAL_INVALID")
    event_schema = Draft202012Validator(json.loads((CONTRACT_DIR / "spec5.schema.json").read_text(encoding="utf-8")))
    app.state.auth_audit = AuthAudit(str(engine.path) + ".auth")
    operators = OperatorAccess(machine, keys["human"], keys.get("operators", ()))

    @app.middleware("http")
    async def no_store(request, call_next):
        if not local_request_ok(request):
            try:
                with engine.db() as db:
                    security_audit.record(engine, db, 'ACCESS_DENIED', 'untrusted-request', 'local-boundary', 'LOCAL_BOUNDARY_REJECTED')
                response = JSONResponse({'code':'LOCAL_BOUNDARY_REJECTED'}, status_code=403)
            except Exception:
                response = JSONResponse({'code':'ADAPTER_UNAVAILABLE'}, status_code=503)
        else:
            response = await call_next(request)
        apply_security_headers(response.headers, https=request.url.scheme == "https")
        return response

    def auth(request, role, permission=None):
        request.state.auth_surface = "HUMAN" if role == "human" else "SERVICE"
        token = bearer_token(request)
        principal = operators.authenticate(token) if role == "human" else None
        authenticated = bool(token) and (principal is not None if role == "human" else hmac.compare_digest(token.encode("ascii"), keys[role].encode("ascii")))
        # Session audit eviction must not reset the durable authentication limit.
        # Read failure still fails closed, but another actor cannot lock out valid credentials.
        path = Path(app.state.auth_audit.path)
        failures = 0
        if path.exists():
            with private_connect(path, read_only=True, timeout=1) as db:
                failures = db.execute("SELECT coalesce(sum(count),0) FROM auth_failures WHERE surface=? AND status IN (401,403) AND last_at>?",
                                      (request.state.auth_surface, time.time()-60)).fetchone()[0]
        if not authenticated:
            if failures >= 10:
                raise Rejected("AUTH_RATE_LIMIT")
            raise Rejected("AUTHENTICATION_FAILED")
        request.state.actor = 'operator:' + principal['subject'] if principal else 'machine:' + machine
        if principal is not None and permission not in principal["permissions"]:
            raise Rejected("OPERATOR_PERMISSION_REQUIRED")
        return principal

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
            security_audit.record(engine, db, 'AUTH_FAILURE' if exc.code in {'AUTHENTICATION_FAILED','AUTH_RATE_LIMIT'} else 'ACCESS_DENIED',
                                  getattr(_req.state, 'actor', 'unauthenticated'), getattr(_req.state, 'bound_call', ''), exc.code)
            engine.audit(db, "REJECT", exc.code, call)
            binding = getattr(_req.state, "rejection_binding", None)
            if binding and exc.code in REJECTION_CODES:
                db.execute("DELETE FROM gateway_rejections WHERE at<?", (time.time() - 60,))
                db.execute("INSERT OR IGNORE INTO gateway_rejections VALUES(?,?,?,?)",
                           (binding, time.time(), exc.code, digest(call) if call else None))
                db.execute("DELETE FROM gateway_rejections WHERE request NOT IN (SELECT request FROM gateway_rejections ORDER BY at DESC LIMIT 128)")
        return JSONResponse({"code": exc.code}, status_code=429 if exc.code == "AUTH_RATE_LIMIT" else 403)

    @app.exception_handler(Exception)
    async def unavailable(_req, _exc):
        response = JSONResponse({"code": "ADAPTER_UNAVAILABLE"}, status_code=503)
        apply_security_headers(response.headers, https=_req.url.scheme == "https")
        return response

    @app.get("/health")
    async def health(request: Request):
        if not request.headers.getlist("authorization"):
            return {"status": "ok"}
        auth(request, "machine")
        if engine.policy_router:
            return {"spec": "MVP-SPEC-5", 'decision_contract':'ASK_V1', 'ask_connector':'CODEX_MCP_FORM_CAPABILITY_REQUIRED', "judge_mode": "JEV_OFFLINE_FIXTURE" if getattr(engine.policy_router.client, "is_fixture", False) else "JEV_USER_LIVE" if engine.policy_router.client.settings.authorized() else "JEV_RULES_ONLY", "decision_policy": engine.policy,
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

    @app.post("/connections/close")
    async def close_connection(request: Request):
        auth(request, "machine")
        _, value = await body(request)
        if not isinstance(value, dict) or set(value) != {"connection"} or not isinstance(value["connection"], str) or not 1 <= len(value["connection"]) <= 512:
            raise Rejected("INVALID_EVENT")
        return engine.close_session_connection(machine, value["connection"])

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
            return {**result, **await engine.authorize(m, value["call"], ask_connection=value['connection'])}
        if kind == "ApprovalPoll":
            return {'decision':'DENY','state':'LEGACY_CONFIRM_READ_ONLY'}
        if kind == "PostToolUse":
            return engine.observe(m, value["call"], value["tool"], value["args"], value["output"], value.get("failed", False))
        raise Rejected("UNSUPPORTED_EVENT")

    @app.post('/ask/pending')
    async def ask_pending(request: Request):
        auth(request, 'machine')
        _, value = await body(request)
        if (not isinstance(value, dict) or set(value) != {'connection','tool','args'}
                or not isinstance(value['connection'], str) or not isinstance(value['tool'], str)
                or not isinstance(value['args'], dict)):
            raise Rejected('INVALID_EVENT')
        m, session = engine.connection(value['connection'])
        return engine.pending_ask(m, session, value['connection'], value['tool'], value['args'])

    @app.post('/ask/presented')
    @app.post('/ask/answer')
    async def ask_response(request: Request):
        auth(request, 'machine')
        _, value = await body(request)
        answering = request.url.path == '/ask/answer'
        expected = {'connection','ask_id','nonce'} | ({'answer'} if answering else set())
        if (not isinstance(value, dict) or set(value) != expected
                or any(not isinstance(x, str) or not 0 < len(x) <= 512 for x in value.values())):
            raise Rejected('INVALID_EVENT')
        m, _ = engine.connection(value['connection'])
        if answering:
            return await engine.answer_ask(m, value['connection'], value['ask_id'], value['nonce'], value['answer'])
        return engine.ask_presented(m, value['connection'], value['ask_id'], value['nonce'])

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
        principal = auth(request, "human", "history:read")
        from app.transparent.demo_approval import pending
        return pending(engine, principal["machine"])

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
        request.state.auth_surface = "AGENT"
        token = bearer_token(request)
        if not token:
            raise Rejected("AUTHENTICATION_FAILED")
        raw, value = await body(request)
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
        principal = auth(request, "human", "history:read")
        return {"calls": engine.history(machine=principal["machine"])}

    @app.get("/history/summary")
    async def history_summary(request: Request):
        principal = auth(request, "human", "history:read")
        calls = []
        def label(value, limit=40):
            return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1," + str(limit) + "}", value) else None
        for row in engine.history(machine=principal["machine"]):
            context = json.loads(row["reason"]) if row.get("reason") else {}
            reasons = [code for code in context.get("reasons", []) if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{1,80}", code)]
            calls.append({"id": label(row["id"], 128) or digest(row["id"]),
                          'initial_decision':row['initial_decision'], 'ask_history':row['ask_history'],
                          "decision": label(row["decision"]), "state": label(row["state"]),
                          "policy": label(context.get("policy"), 80),
                          "routing": label((context.get("policy_trace") or {}).get("routing")),
                          "reasons": reasons[:8], "reasons_truncated": len(reasons) > 8})
        return {"scope": "LATEST_100_CALLS", "counts": {decision: sum(row["decision"] == decision for row in calls)
                for decision in {row["decision"] for row in calls}}, "calls": calls}

    @app.get("/demo/history")
    async def demo_history(request: Request):
        if os.environ.get("HOOKGW_DEMO_VIEWER") != "1":
            return JSONResponse({"code": "DEMO_NOT_ENABLED"}, status_code=404)
        principal = auth(request, "human", "history:read")
        from app.transparent.demo_report import project
        return project(engine, machine=principal["machine"])

    @app.post("/approval")
    async def approval(request: Request):
        auth(request, "human", "approval:write")
        # Historical CONFIRM is retained for IR, never promoted to an ASK answer.
        return JSONResponse({'code':'LEGACY_CONFIRM_READ_ONLY'}, status_code=409)

    @app.post("/sessions/forget")
    async def forget(request: Request):
        principal = auth(request, "human", "session:purge")
        _, value = await body(request)
        if not isinstance(value, dict) or set(value) != {"session"} or not isinstance(value["session"], str) or not 1 <= len(value["session"]) <= 512:
            raise Rejected("INVALID_EVENT")
        engine.purge(value["session"], machine=principal["machine"], actor=request.state.actor)
        return {"state": "FORGOTTEN_LOGICALLY"}

    @app.get('/security')
    async def security_history(request: Request):
        auth(request, 'human', 'security:read')
        with engine.db() as db:
            return security_audit.read(engine, db)

    @app.post('/security/alerts/ack')
    async def acknowledge_alert(request: Request):
        auth(request, 'human', 'security:ack')
        _, value = await body(request)
        if not isinstance(value, dict) or set(value) != {'id'} or type(value['id']) is not int or value['id'] < 1:
            raise Rejected('INVALID_EVENT')
        with engine.db() as db:
            if not db.execute('SELECT 1 FROM security_alerts WHERE id=?', (value['id'],)).fetchone():
                raise Rejected('INVALID_EVENT')
            security_audit.record(engine, db, 'ALERT_ACK', request.state.actor, str(value['id']), 'ACKNOWLEDGED')
            db.execute('UPDATE security_alerts SET acknowledged=1 WHERE id=?', (value['id'],))
        return {'state':'ACKNOWLEDGED'}

    from app.transparent.dashboard import register
    register(app,engine,machine,auth,preview_forbidden=(keys['machine'],keys['human']))
    return app


def public_app(app):
    public = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @public.middleware("http")
    async def boundary(request, call_next):
        if not local_request_ok(request):
            # Let the mounted Control boundary record and reject this request.
            return await call_next(request)
        if request.url.path == "/authz":
            try:
                app.state.auth_audit.record("SERVICE", 403)
            except Exception:
                response = JSONResponse({"code": "ADAPTER_UNAVAILABLE"}, status_code=503)
            else:
                response = JSONResponse({"code": "PRIVATE_ENDPOINT"}, status_code=403)
            apply_security_headers(response.headers, https=request.url.scheme == "https")
            return response
        return await call_next(request)

    public.mount("/", app)
    return public


def serve_app(app, runtime=RUNTIME):
    with lease(app.state.engine.path):
        _serve_app(app, runtime)


def _serve_app(app, runtime=RUNTIME):
    """The same public/private TLS boundary is used by deployment and local tests."""
    public = public_app(app)
    async def serve():
        async def maintenance():
            while True:
                await asyncio.sleep(10)
                with app.state.engine.db() as db:
                    app.state.engine.cleanup(db)
        # Container interfaces serve Docker forwarding; compose publishes only 127.0.0.1.
        host = '0.0.0.0' if os.environ.get('WITH_HUMAN_CONTAINER_BOUNDARY') == 'loopback-published' else '127.0.0.1'  # nosec B104
        options = dict(host=host, ssl_certfile=str(runtime / "control.pem"), ssl_keyfile=str(runtime / "control.key"),
                       access_log=False, proxy_headers=False, log_level="critical")
        servers = asyncio.gather(uvicorn.Server(uvicorn.Config(public, port=8030, **options)).serve(),
                                 uvicorn.Server(uvicorn.Config(app, port=8050, ssl_ca_certs=str(runtime / "ca.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED, **options)).serve())
        worker = asyncio.create_task(maintenance())
        try:
            done, _ = await asyncio.wait((servers, worker), return_when=asyncio.FIRST_COMPLETED)
            for finished in done:
                finished.result()
        finally:
            worker.cancel()
            servers.cancel()
            await asyncio.gather(worker, servers, return_exceptions=True)
    asyncio.run(serve())


def main():
    grant = json.loads((RUNTIME / "grant.json").read_text(encoding="utf-8"))
    judge, router = None, None
    mode = os.environ.get("HOOKGW_PDP", "JEV")
    if mode == "JEV":
        from app.transparent.jev import JevClient
        from app.transparent.jev_config import DEFAULT_PROFILE, load_runtime_settings, make_policy
        settings = load_runtime_settings(Path(os.environ.get("JEV_POLICY_FILE", "/jev-config/policy.json")),
                                         allow_offline=os.environ.get("HOOKGW_REQUIRE_JEV", "1") == "0")
        profile = os.environ.get("HOOKGW_JEV_PROFILE", DEFAULT_PROFILE)
        client = JevClient(settings)
        if settings.authorized():
            client.preflight()
        router = make_policy(client, profile)
    elif mode != "GPT":
        raise RuntimeError("UNSUPPORTED_PDP_MODE")
    elif os.environ.get("HOOKGW_USER_LIVE") == "1":
        from app.transparent.judge import DevelopmentJudge
        judge = DevelopmentJudge(os.environ["JUDGE_BUDGET_DB_PATH"])
    path = Path(os.getenv('HOOKGW_DB','/data/control.sqlite3'))
    with lease(path):
        if (path.parent/'rotation.pending').exists():
            raise RuntimeError('OFFLINE_ROTATION_RECOVERY_REQUIRED')
        if (path.parent/'provider-reapproval.required').exists():
            raise RuntimeError('RESTORED_PROVIDER_REAPPROVAL_REQUIRED')
        authorization = path.parent/'provider.authorization'
        if authorization.exists():
            import hashlib
            policy_file = Path(os.environ.get('JEV_POLICY_FILE','/jev-config/policy.json'))
            if (authorization.is_symlink() or authorization.stat().st_size != 64
                    or authorization.read_text() != hashlib.sha256(policy_file.read_bytes()).hexdigest()):
                raise RuntimeError('RESTORED_PROVIDER_POLICY_BINDING')
        engine = Engine(path, secret("storage.key").encode(), grant, judge, policy_router=router,
                        preserve_history_on_policy_change=mode == "JEV")
        keys = {"machine": secret("machine.token"), "human": secret("human.token"), "machine_id": secret("machine.id"), "ticket": ticket}
        operator_file = RUNTIME / "operators.json"
        if operator_file.exists():
            if operator_file.is_symlink() or operator_file.stat().st_size > 16384:
                raise RuntimeError("OPERATOR_POLICY_INVALID")
            keys["operators"] = strict_json(operator_file.read_bytes())
        app = create_app(engine, keys)
        _serve_app(app)


if __name__ == "__main__":
    main()
