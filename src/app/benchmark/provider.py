"""Budgeted real provider transport, shared by production and offline tests."""

import asyncio
import base64
import hashlib
import hmac
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.benchmark.runtime_budget import StopRun, is_budget_stop
from app.common import canonical, strict_json

OPENAI = "https://api.openai.com/v1/"
TYPESAFE = "https://api.typesafe.ai/v1/systemone"


def token(secret, task, arm, provider, expires):
    body = base64.urlsafe_b64encode(
        canonical({"task": task, "arm": arm, "provider": provider, "expires": expires}).encode()
    ).decode()
    return body + "." + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def claims(secret, authorization):
    try:
        bearer = authorization.removeprefix("Bearer ")
        body, sig = bearer.split(".", 1)
        if not authorization.startswith("Bearer ") or not hmac.compare_digest(
            sig, hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        ):
            raise ValueError()
        value = strict_json(base64.urlsafe_b64decode(body))
        if value["expires"] < time.time():
            raise ValueError()
        return value
    except Exception as error:
        raise StopRun("PROVIDER_ROLE_AUTH_FAILED") from error


class ProviderTransport:
    def __init__(self, budget, keys, *, live=False, transport=None, plan=None):
        if live and transport is not None:
            raise StopRun("MOCK_FORBIDDEN_IN_USER_RUN")
        if not live and not isinstance(transport, httpx.MockTransport):
            raise StopRun("OFFLINE_EXPLICIT_FAKE_REQUIRED")
        if live and budget.manifest.get("live_opt_in") != "EXPLICIT_USER_COMMAND":
            raise StopRun("LIVE_OPT_IN_REQUIRED")
        self.budget, self.keys, self.live, self.transport = budget, keys, live, transport
        self.plan = plan
        if bool(budget.manifest.get('chatgpt_plan')) != bool(plan):
            raise StopRun('EXPLICIT_CHATGPT_PLAN_TRANSPORT_REQUIRED')

    async def send(self, job, path, body):
        role = job["provider"]
        if self.plan and role != 'jev':
            return await self.plan.send(job,path,body)
        profile = self.budget.manifest["providers"][role]
        if path not in profile["paths"] or not isinstance(body, dict):
            raise StopRun("PROVIDER_PATH_OR_BODY")
        model = body.get("model")
        if model not in profile["models"]:
            raise StopRun("PROVIDER_MODEL_CHANGED")
        if role != "jev" and model != "gpt-5.2":
            raise StopRun("OPENAI_GPT52_ONLY")
        if role == "environment":
            # The pinned OS tool permits a model override but always sends
            # temperature=0.1. GPT-5.2 low rejects temperature, so normalize
            # only this exact original permission shape at the trusted broker.
            if (
                path != "chat/completions"
                or body.get("temperature") != 0.1
                or body.get("max_completion_tokens") != 500
                or body.get("reasoning_effort") is not None
            ):
                raise StopRun("OS_PERMISSION_SHAPE_CHANGED")
            body = {k: v for k, v in body.items() if k != "temperature"}
            body["reasoning_effort"] = "low"
        if role == "actor":
            if (
                path != "responses"
                or model != "gpt-5.2"
                or body.get("reasoning") != {"effort": "low"}
                or body.get("store") is not False
                or body.get("parallel_tool_calls") is not False
            ):
                raise StopRun("ACTOR_GPT52_LOW_CONTRACT")
            if any(tool.get("type") != "function" for tool in body.get("tools", [])):
                raise StopRun("NO_NATIVE_UNGUARDED_PROVIDER_TOOLS")
        raw = canonical(body).encode()
        if len(raw) > profile["per_request"]["wire_bytes"]:
            raise StopRun("PROVIDER_CONTEXT_CAP_INCOMPLETE")
        if any(part in raw for part in (b'"input_image"', b'"image_url"', b'"input_audio"')):
            raise StopRun("MULTIMODAL_RESERVATION_NOT_ENROLLED")
        if role == "jev":
            outputs = 0
            inputs = profile["per_request"]["input_tokens"]
        else:
            outputs = (
                body.get("max_output_tokens")
                if path == "responses"
                else body.get("max_completion_tokens", body.get("max_tokens"))
            )
            if type(outputs) is not int or outputs < 1:
                raise StopRun("EXPLICIT_OUTPUT_BOUND_REQUIRED")
            # Reserve the enrolled provider's entire input context, including
            # replayed encrypted reasoning. UTF-8 wire bytes are a separate
            # transport bound, never an exact tokenizer estimate.
            inputs = profile["per_request"]["input_tokens"]
        try:
            rid = self.budget.reserve(
                job["task"],
                job["arm"],
                role,
                model,
                inputs,
                outputs,
                profile["per_request"]["seconds"],
            )
        except StopRun as error:
            if str(error).startswith("CAP_EXHAUSTED_"):
                self.budget.note_budget_rejection(job["task"], job["arm"], role, str(error))
                self.budget.stop(str(error))
            raise
        recorded = False
        try:
            target = TYPESAFE if role == "jev" else OPENAI + path
            key = self.keys["typesafe" if role == "jev" else "openai"]
            if not isinstance(key, str) or not key.strip():
                raise StopRun("PROVIDER_KEY_UNAVAILABLE")
            # Prevent literal actual credentials reaching any model input. This
            # is separate from public schema labels/synthetic benchmark values.
            if any(value.encode() in raw for value in self.keys.values() if value):
                raise StopRun("ACTUAL_PROVIDER_SECRET_IN_INPUT")
            async with (
                asyncio.timeout(profile["per_request"]["seconds"]),
                httpx.AsyncClient(
                    transport=self.transport,
                    timeout=profile["per_request"]["seconds"],
                    trust_env=False,
                    follow_redirects=False,
                ) as client,
            ):
                async with client.stream(
                    "POST",
                    target,
                    content=raw,
                    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    data = bytearray()
                    async for block in response.aiter_bytes():
                        data.extend(block)
                        if len(data) > profile["per_request"]["response_bytes"]:
                            raise StopRun("PROVIDER_RESPONSE_CAP")
            value = strict_json(bytes(data))
            usage = value.get("usage")
            if path == "chat/completions" and isinstance(usage, dict):
                usage = {
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                }
            if role == "jev" and isinstance(usage, dict):
                # Jev does not generate billable output tokens. Preserve its
                # provider field separately; reservation charge is input-only.
                usage = {"input_tokens": usage.get("input_tokens"), "output_tokens": 0}
            valid = self.budget.record(rid, usage, resolved_model=value.get("model"))
            recorded = True
            if not valid:
                raise StopRun("PROVIDER_USAGE_OR_MODEL_UNKNOWN")
            return value
        except BaseException as error:
            if not recorded:
                self.budget.record(rid, None)
            code = "PROVIDER_REQUEST_UNKNOWN_NO_RETRY"
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code in (
                401,
                403,
            ):
                code = "PROVIDER_AUTH_FAILURE_STOP_ALL"
            self.budget.stop(code)
            raise StopRun(code) from error


def broker_app(budget, transport, secret, admin_token=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/admin/{operation}")
    async def administration(operation: str, request: Request):
        if not admin_token or not hmac.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + admin_token
        ):
            return JSONResponse({"code": "ADMIN_ROLE_REQUIRED"}, status_code=403)
        try:
            raw = await request.body()
            if len(raw) > 1048576:
                raise StopRun("ADMIN_BODY_LIMIT")
            value = strict_json(raw)
            if operation == "status":
                return budget.status()
            if operation == "acquire":
                return {"owner": budget.acquire(value["arm"])}
            if operation == "claim":
                return {"state": budget.claim(value["task"], value["arm"], value["owner"])}
            if operation == "heartbeat":
                budget.heartbeat(value["arm"], value["owner"])
            elif operation == "release":
                budget.release(value["arm"], value["owner"])
            elif operation == "finish":
                budget.finish(
                    value["task"], value["arm"], value["owner"], value["state"], value["result"]
                )
            elif operation == "stop":
                code = value.get("code", "OPERATOR_STOP")
                if code not in ("OPERATOR_STOP", "INFRASTRUCTURE_STOP_ALL"):
                    raise StopRun("STOP_CODE_NOT_ALLOWED")
                budget.stop(code)
            elif operation == "recover":
                budget.reconcile_interrupted(value["arm"])
            elif operation == "storage":
                budget.reserve_storage(
                    value["identity"], value["bytes"], cleanup=value.get("cleanup")
                )
            elif operation == "tokens":
                with budget.db() as db:
                    if not db.execute(
                        "SELECT 1 FROM jobs WHERE task=? AND arm=? AND owner=? AND state='CLAIMED'",
                        (value["task"], value["arm"], value["owner"]),
                    ).fetchone():
                        raise StopRun("ACTIVE_OWNED_TASK_REQUIRED")
                expires = time.time() + budget.manifest["task_limits"]["seconds"] + 120
                return {
                    role: token(secret, value["task"], value["arm"], role, expires)
                    for role in ("actor", "jev", "environment", "judge")
                }
            else:
                raise StopRun("UNKNOWN_ADMIN_OPERATION")
            return {"state": "RECORDED"}
        except StopRun as error:
            code = str(error)
            return JSONResponse(
                {
                    "code": code
                    if is_budget_stop(code)
                    else "EXPERIMENT_STOP_OR_INVALID_OPERATION",
                    "budget_stopped": is_budget_stop(code),
                },
                status_code=409,
            )
        except (ValueError, KeyError, TypeError):
            return JSONResponse({"code": "EXPERIMENT_STOP_OR_INVALID_OPERATION"}, status_code=409)

    @app.post("/{path:path}")
    async def forward(path: str, request: Request):
        job = None
        try:
            job = claims(secret, request.headers.get("authorization", ""))
            chunks = bytearray()
            async for chunk in request.stream():
                chunks.extend(chunk)
                if len(chunks) > 1048576:
                    raise StopRun("BROKER_BODY_LIMIT")
            bearer = request.headers["authorization"].removeprefix("Bearer ")
            if bearer.encode() in chunks:
                raise StopRun("ACTUAL_ROLE_CREDENTIAL_IN_INPUT")
            value = await transport.send(job, path.removeprefix("v1/"), strict_json(bytes(chunks)))
            return JSONResponse(value)
        except (StopRun, ValueError, KeyError):
            if job and not budget.status()["stop"]:
                budget.stop("PROVIDER_CONTRACT_REJECTED_STOP_ALL")
            stop = budget.status()["stop"]
            return JSONResponse(
                {
                    "error": {
                        "type": "benchmark_stop",
                        "code": stop if is_budget_stop(stop) else "REQUEST_REJECTED_OR_UNKNOWN",
                    }
                },
                status_code=503,
            )

    return app
