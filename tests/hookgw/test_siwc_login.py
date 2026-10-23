"""OAuth and streamed plan contracts; fake credentials/provider, no real inference."""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from test_dtap_runtime import manifest, start

from app.benchmark.provider import ProviderTransport
from app.benchmark.responses_loop import AutonomousResponses
from app.benchmark.runtime_budget import RuntimeBudget, StopRun
from app.benchmark.siwc_auth import ISSUER, MODEL, RESOURCE, SCOPES, TOKEN, Credentials
from app.benchmark.siwc_test_provider import FixtureCredentials
from app.benchmark.siwc_transport import NAMESPACE, PlanTransport, actor_request, completed_stream
from app.common import canonical


def body():
    return {
        "model": MODEL,
        "reasoning": {"effort": "low"},
        "store": False,
        "stream": True,
        "parallel_tool_calls": False,
        "input": [
            {"role": "developer", "content": "Original system"},
            {"role": "user", "content": "Read public file"},
        ],
        "tools": [
            {
                "type": "function",
                "name": "dt_read",
                "description": "original",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
            }
        ],
        "include": ["reasoning.encrypted_content"],
    }


def budget(tmp_path, monkeypatch):
    import app.benchmark.runtime_login

    monkeypatch.setattr(app.benchmark.runtime_login, "verify_parent", lambda *a: None)
    m = manifest()
    m["actor_model"] = MODEL
    m["chatgpt_plan"] = {
        "limits": {
            "requests": 10,
            "per_arm_requests": 5,
            "per_task_requests": 4,
            "seconds": 1000,
            "per_task_seconds": 100,
        }
    }
    b = RuntimeBudget(tmp_path / "budget.db", m)
    start(b)
    return b


def completed(output=None):
    return {
        "id": "response",
        "model": MODEL,
        "status": "completed",
        "output": output
        or [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Result"}],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 4},
    }


def sse(value):
    return "data: " + canonical({"type": "response.completed", "response": value}) + "\n\n"


@pytest.mark.parametrize(
    "fault",
    [
        "model",
        "effort",
        "max_output_tokens",
        "previous_response_id",
        "temperature",
        "stream",
        "native",
        "system",
        "history_namespace",
    ],
)
def test_no_fallback_or_unsupported_field(fault):
    value = body()
    if fault == "model":
        value["model"] = "gpt-5.2"
    elif fault == "effort":
        value["reasoning"] = {"effort": "high"}
    elif fault in ("max_output_tokens", "previous_response_id", "temperature"):
        value[fault] = 1
    elif fault == "stream":
        value["stream"] = False
    elif fault == "native":
        value["tools"] = [{"type": "computer_use"}]
    elif fault == "system":
        value["input"][0]["role"] = "system"
    else:
        value["input"].append(
            {
                "type": "function_call",
                "name": "dt_read",
                "namespace": "other",
                "call_id": "c",
                "arguments": "{}",
            }
        )
    with pytest.raises(StopRun):
        actor_request(value)


@pytest.mark.parametrize(
    "failure",
    [
        "eof",
        "delta_only",
        "incomplete",
        "quota",
        "unauthorized",
        "redirect",
        "model",
        "namespace",
        "response_bytes",
        "usage",
        "duplicate",
    ],
)
def test_stream_loss_limits_or_invalid_output_unknown_stop_both(tmp_path, monkeypatch, failure):
    b = budget(tmp_path, monkeypatch)
    value = completed()
    text = sse(value)
    status = 200
    if failure == "eof":
        text = text[:-1]
    elif failure == "delta_only":
        text = 'data: {"type":"response.output_text.delta","delta":"ok"}\n\n'
    elif failure in ("incomplete", "quota"):
        text = (
            "data: "
            + canonical(
                {
                    "type": "response.incomplete" if failure == "incomplete" else "response.failed",
                    "response": {"error": {"code": "subscription_sharing_usage_limit_exceeded"}},
                }
            )
            + "\n\n"
        )
    elif failure == "unauthorized":
        status = 401
    elif failure == "redirect":
        status = 302
    elif failure == "model":
        value["model"] = "gpt-5.2"
        text = sse(value)
    elif failure == "namespace":
        value["output"] = [
            {
                "type": "function_call",
                "name": "dt_read",
                "namespace": "other",
                "call_id": "c",
                "arguments": "{}",
            }
        ]
        text = sse(value)
    elif failure == "response_bytes":
        text = "x" * 10001
    elif failure == "usage":
        value["usage"] = {}
        text = sse(value)
    else:
        text = text + text
    seen = []

    def send(r):
        seen.append(r)
        return httpx.Response(status, headers={"content-type": "text/event-stream"}, text=text)

    plan = PlanTransport(b, FixtureCredentials(), transport=httpx.MockTransport(send))
    with pytest.raises(StopRun):
        asyncio.run(
            plan.send(
                {"task": "task", "arm": "engine-on", "provider": "actor"}, "responses", body()
            )
        )
    assert len(seen) == 1 and seen[0].url == RESOURCE + "/responses" and b.status()["stop"]
    assert b.status()["chatgpt_plan_usage"]["requests"] == 1
    assert b.status()["committed_micro_usd"] == 0
    with pytest.raises(StopRun):
        b.acquire("engine-off")


@pytest.mark.parametrize("media", ["text/event-stream", ""])
def test_namespace_reasoning_full_history_roundtrip_and_exact_call_id(tmp_path, monkeypatch, media):
    b = budget(tmp_path, monkeypatch)
    seen = []
    effects = []

    def send(request):
        wire = json.loads(request.content)
        seen.append(wire)
        assert wire["model"] == MODEL and wire["reasoning"] == {"effort": "low"}
        assert wire["tools"][0]["name"] == NAMESPACE
        assert wire["store"] is False and wire["stream"] is True and "max_output_tokens" not in wire
        if len(seen) == 1:
            return httpx.Response(
                200,
                headers={"content-type": media},
                text=sse(
                    completed(
                        [
                            {
                                "type": "reasoning",
                                "id": "r",
                                "encrypted_content": "PUBLIC-ENCRYPTED-FIXTURE",
                                "summary": [],
                            },
                            {
                                "type": "function_call",
                                "namespace": NAMESPACE,
                                "name": "dt_read",
                                "call_id": "original-call-id",
                                "arguments": '{"path":"/public"}',
                            },
                        ]
                    )
                ),
            )
        assert (
            next(i for i in wire["input"] if i.get("type") == "function_call")["namespace"]
            == NAMESPACE
        )
        assert any(
            i.get("call_id") == "original-call-id" and i["type"] == "function_call_output"
            for i in wire["input"]
        )
        assert any(i.get("encrypted_content") == "PUBLIC-ENCRYPTED-FIXTURE" for i in wire["input"])
        return httpx.Response(200, headers={"content-type": media}, text=sse(completed()))

    plan = PlanTransport(b, FixtureCredentials(), transport=httpx.MockTransport(send))

    async def dispatch(name, args):
        effects.append((name, args))
        return {"content": [{"type": "text", "text": "public data"}]}

    async def call(value):
        return await plan.send(
            {"task": "task", "arm": "engine-on", "provider": "actor"}, "responses", value
        )

    loop = AutonomousResponses(
        call,
        dispatch,
        body()["tools"],
        system="Original system",
        limits={"responses": 4, "seconds": 20, "tool_calls": 3, "output_tokens": 8192},
        record=lambda e: None,
        provider_profile="chatgpt-plan",
    )
    assert asyncio.run(loop.run("Read public file")) == "Result"
    assert effects == [("dt_read", {"path": "/public"})]
    assert (
        b.status()["chatgpt_plan_usage"]["requests"] == 2 and b.status()["committed_micro_usd"] == 0
    )


def test_permission_simulator_same_luna_low_responses_and_no_judge(tmp_path, monkeypatch):
    b = budget(tmp_path, monkeypatch)
    seen = []

    def send(r):
        seen.append(json.loads(r.content))
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, text=sse(completed())
        )

    plan = PlanTransport(b, FixtureCredentials(), transport=httpx.MockTransport(send))
    value = {
        "model": MODEL,
        "temperature": 0.1,
        "max_completion_tokens": 500,
        "messages": [
            {"role": "system", "content": "Original simulator"},
            {"role": "user", "content": "Permission?"},
        ],
    }
    reply = asyncio.run(
        plan.send(
            {"task": "task", "arm": "engine-on", "provider": "environment"},
            "chat/completions",
            value,
        )
    )
    assert reply["choices"][0]["message"]["content"] == "Result"
    assert seen[0]["model"] == MODEL and seen[0]["reasoning"] == {"effort": "low"}
    assert seen[0]["input"][0] == {"role": "developer", "content": "Original simulator"}
    assert not {"temperature", "max_completion_tokens", "max_output_tokens"} & seen[0].keys()
    with pytest.raises(StopRun):
        asyncio.run(
            plan.send(
                {"task": "task", "arm": "engine-on", "provider": "judge"}, "chat/completions", value
            )
        )
    assert len(seen) == 1


@pytest.mark.parametrize(
    "media,accepted,recorded",
    [
        ("text/event-stream", True, "text/event-stream"),
        ("Text/Event-Stream ; charset=utf-8", True, "text/event-stream"),
        ("application/json", False, "application/json"),
        ("text/html", False, "text/html"),
        ("private-provider-header-value", False, "other"),
        ("", True, ""),
    ],
)
def test_http_response_metadata_is_bounded_and_never_accepts_non_sse(
    tmp_path, monkeypatch, media, accepted, recorded
):
    b = budget(tmp_path, monkeypatch)
    seen = []

    def send(request):
        seen.append(request)
        assert request.headers["accept"] == "text/event-stream"
        return httpx.Response(200, headers={"content-type": media}, text=sse(completed()))

    plan = PlanTransport(b, FixtureCredentials(), transport=httpx.MockTransport(send))

    async def call():
        return await plan.send(
            {"task": "task", "arm": "engine-on", "provider": "actor"}, "responses", body()
        )

    if accepted:
        assert asyncio.run(call())["status"] == "completed"
    else:
        with pytest.raises(StopRun, match="SIWC_SSE_REQUIRED"):
            asyncio.run(call())
    assert len(seen) == 1
    status = b.status()
    assert status["chatgpt_plan_usage"]["http_observations"] == [
        {"arm": "engine-on", "http_status": 200, "media_type": recorded, "requests": 1}
    ]
    assert status["chatgpt_plan_usage"]["states"]["UNKNOWN"] == (0 if accepted else 1)
    assert status["committed_micro_usd"] == 0
    with b.db() as db:
        stored = db.execute("SELECT * FROM plan_http_observations").fetchall()
    assert "private-provider-header-value" not in repr(stored)
    assert "Result" not in repr(stored)


def test_plan_requires_explicit_transport_no_api_key_fallback(tmp_path, monkeypatch):
    b = budget(tmp_path, monkeypatch)
    with pytest.raises(StopRun):
        ProviderTransport(
            b,
            {"openai": "PUBLIC-API-KEY"},
            transport=httpx.MockTransport(lambda r: httpx.Response(500)),
        )


@pytest.mark.parametrize(
    "failure",
    [
        "json",
        "html",
        "garbage_prefix",
        "unknown_event",
        "event_mismatch",
        "duplicate",
        "partial",
        "failed",
        "wrong_model",
        "missing_usage",
        "negative_usage",
        "boolean_usage",
        "partial_after_complete",
        "array_event",
        "non_2xx",
    ],
)
def test_headerless_never_accepts_prefix_or_invalid_completion(failure):
    value = completed()
    status = 200
    text = sse(value)
    if failure == "json":
        text = canonical(value) + "\n\n"
    elif failure == "html":
        text = "<html>not SSE</html>\n\n"
    elif failure == "garbage_prefix":
        text = "<html>not SSE</html>\n" + text
    elif failure == "unknown_event":
        text = 'data: {"type":"unregistered.event"}\n\n' + text
    elif failure == "event_mismatch":
        text = "event: response.created\n" + text
    elif failure == "duplicate":
        text += text
    elif failure == "partial":
        text = 'data: {"type":"response.output_text.delta","delta":"public"}\n\n'
    elif failure == "failed":
        text = 'data: {"type":"response.failed","response":{"error":{}}}\n\n'
    elif failure == "wrong_model":
        value["model"] = "gpt-5.2"
        text = sse(value)
    elif failure == "missing_usage":
        value.pop("usage")
        text = sse(value)
    elif failure == "negative_usage":
        value["usage"]["input_tokens"] = -1
        text = sse(value)
    elif failure == "boolean_usage":
        value["usage"]["output_tokens"] = True
        text = sse(value)
    elif failure == "partial_after_complete":
        text += 'data: {"type":"response.'
    elif failure == "array_event":
        text = "data: []\n\n" + text
    else:
        status = 400
    with pytest.raises(StopRun):
        asyncio.run(completed_stream(httpx.Response(status, content=text.encode()), maximum=10000))


def test_headerless_fragmented_crlf_utf8_bom_and_comments():
    value = completed()
    value["output"][0]["content"][0]["text"] = "완료"
    raw = (
        "\ufeff: keepalive\r\n\r\nevent: response.completed\r\ndata: "
        + canonical({"type": "response.completed", "response": value})
        + "\r\n\r\n"
    ).encode()

    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self):
            for i in range(0, len(raw), 3):
                yield raw[i : i + 3]

    result = asyncio.run(completed_stream(httpx.Response(200, stream=Chunks()), maximum=10000))
    assert result == value


@pytest.mark.parametrize("media", ["text/event-stream", ""])
@pytest.mark.parametrize("malformed", [None, [], {}, "omitted"])
def test_malformed_first_completion_never_allows_later_valid_terminal(media, malformed):
    first = {"type": "response.completed"}
    if malformed != "omitted":
        first["response"] = malformed
    text = "data: " + canonical(first) + "\n\n" + sse(completed())
    with pytest.raises(StopRun):
        asyncio.run(
            completed_stream(
                httpx.Response(200, headers={"content-type": media}, content=text.encode()),
                maximum=10000,
            )
        )


def oauth(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="fixture", alg="RS256")
    seen = []
    state = {"nonce": "nonce", "client_id": "oaiapp_fixture"}

    def id_token(nonce="nonce", **extra):
        claims = {
            "iss": ISSUER,
            "aud": state["client_id"],
            "sub": "subject",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "nonce": nonce,
            **extra,
        }
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "fixture"})

    def response():
        return {
            "token_type": "Bearer",
            "scope": " ".join(SCOPES),
            "access_token": "PUBLIC-OAUTH-ACCESS",
            "refresh_token": "PUBLIC-OAUTH-REFRESH",
            "id_token": id_token(state["nonce"]),
            "expires_in": 3600,
        }

    def send(r):
        seen.append((str(r.url), r.method, r.content))
        if r.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "token_endpoint": TOKEN,
                    "authorization_endpoint": ISSUER + "/api/accounts/authorize",
                    "jwks_uri": ISSUER + "/.well-known/jwks.json",
                    "revocation_endpoint": ISSUER + "/api/accounts/oauth/revoke",
                },
            )
        if r.url.path.endswith("jwks.json"):
            return httpx.Response(200, json={"keys": [jwk]})
        if r.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json=response())
        if r.url.path.endswith("/oauth/revoke"):
            return httpx.Response(200)
        if r.url.path == "/v1/models":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "slug": MODEL,
                            "visibility": "list",
                            "supported_reasoning_levels": [{"effort": "low"}],
                        }
                    ]
                },
            )
        raise AssertionError("No inference or backend route allowed")

    return Credentials(tmp_path, transport=httpx.MockTransport(send)), id_token, seen, state


@pytest.mark.parametrize("fault", ["nonce", "issuer", "audience", "expired", "unsigned"])
def test_id_token_validation_rejects(fault, tmp_path):
    c, make, seen, state = oauth(tmp_path)
    token = make(
        "wrong" if fault == "nonce" else "nonce",
        **(
            {"iss": "wrong"}
            if fault == "issuer"
            else {"aud": "wrong"}
            if fault == "audience"
            else {"exp": 1}
            if fault == "expired"
            else {}
        ),
    )
    if fault == "unsigned":
        token = jwt.encode({"sub": "subject"}, key="", algorithm="none")
    with pytest.raises((StopRun, jwt.PyJWTError)):
        c.identity(token, "oaiapp_fixture", "nonce")


def test_oauth_pkce_callback_issued_client_stable_host_and_no_inference(tmp_path):
    c, make, seen, state = oauth(tmp_path)
    for port in (1459, 1460):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(c.sign_in, port)
            path = tmp_path / "authorization-url.json"
            for _ in range(200):
                if path.exists():
                    break
                time.sleep(0.01)
            url = json.loads(path.read_text())["url"]
            query = parse_qs(urlsplit(url).query)
            state["nonce"] = query["nonce"][0]
            assert query["code_challenge_method"] == ["S256"] and "id_token_hint" not in query
            assert query["client_id"] == (
                ["dynamic_agent_client"] if port == 1459 else ["oaiapp_fixture"]
            )
            assert ("agent_name_hint" in query) == (port == 1459)
            callback = {
                "state": query["state"][0],
                "code": "fixture-code",
                "client_id": "oaiapp_fixture",
            }
            with httpx.Client(trust_env=False) as client:
                invalid = client.get(
                    f"http://127.0.0.1:{port}/auth/callback", params={**callback, "state": "wrong"}
                )
                assert invalid.status_code == 400
                assert (
                    client.get(
                        f"http://127.0.0.1:{port}/auth/callback", params=callback
                    ).status_code
                    == 200
                )
            assert future.result(timeout=5)["account_label"] == "main"
            host = json.loads((tmp_path / "host.json").read_text())
            assert query["ext_agent_host_id"] == [host["host_id"]]
    assert c.models()["model"] == MODEL
    assert not any("/responses" in url or "backend-api" in url for url, method, body in seen)
    token_posts = [parse_qs(raw.decode()) for url, method, raw in seen if url == TOKEN]
    assert all(
        p["client_id"] == ["oaiapp_fixture"]
        and len(p["code_verifier"][0]) >= 43
        and p["resource"] == [RESOURCE]
        for p in token_posts
    )
    assert c.revoke()["remote_revocation_confirmed"] and not c.path.exists()
    assert (tmp_path / "host.json").exists() and (tmp_path / "main-registration.json").exists()


def test_missing_credentials_never_reads_personal_or_falls_back(tmp_path):
    c = Credentials(
        tmp_path, transport=httpx.MockTransport(lambda r: pytest.fail("No network without login"))
    )
    with pytest.raises(StopRun, match="LOGIN_REQUIRED"):
        c.models()


def test_missing_host_never_reregisters_issued_client(tmp_path):
    c, make, seen, state = oauth(tmp_path)
    c.write(tmp_path / "main-pending-client.json", {"client_id": "oaiapp_fixture"})
    with pytest.raises(StopRun, match="HOST_ID_MISSING"):
        c.sign_in()
    assert not seen and not (tmp_path / "host.json").exists()


def test_refresh_rotation_serialized_and_account_binding_preserved(tmp_path):
    c, make, seen, state = oauth(tmp_path)
    c.write(
        tmp_path / "main-registration.json", {"client_id": "oaiapp_fixture", "subject": "subject"}
    )
    c.write(
        c.path,
        {
            "client_id": "oaiapp_fixture",
            "subject": "subject",
            "scopes": sorted(SCOPES),
            "access_token": "OLD",
            "refresh_token": "ROTATING",
            "expires_at": 0,
        },
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: c.access(), range(2)))
    assert values == ["PUBLIC-OAUTH-ACCESS"] * 2
    assert sum(url == TOKEN for url, method, raw in seen) == 1
    assert c.read(c.path)["refresh_token"] == "PUBLIC-OAUTH-REFRESH"


@pytest.mark.parametrize("case", ["azp", "multiple_aud"])
def test_oidc_authorized_party_rejected(tmp_path, case):
    c, make, seen, state = oauth(tmp_path)
    value = make(**({"azp": "other"} if case == "azp" else {"aud": ["oaiapp_fixture", "other"]}))
    with pytest.raises(StopRun):
        c.identity(value, "oaiapp_fixture", "nonce")


def test_plan_meter_maximum_concurrency_and_unknown_not_refunded(tmp_path, monkeypatch):
    from app.benchmark.siwc_transport import PlanMeter

    b = budget(tmp_path, monkeypatch)
    b.manifest["chatgpt_plan"]["limits"]["per_task_requests"] = 1
    b.binding = __import__("app.common", fromlist=["digest"]).digest(canonical(b.manifest))
    meter = PlanMeter(b)

    def reserve(_):
        try:
            return meter.reserve({"task": "task", "arm": "engine-on", "provider": "actor"}, 10)
        except StopRun:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        rids = list(pool.map(reserve, range(2)))
    winners = [r for r in rids if r]
    assert len(winners) == 1
    meter.record(winners[0])
    assert reserve(0) is None and b.status()["chatgpt_plan_usage"]["unresolved_plan_requests"] == 1


@pytest.mark.parametrize("fault", ["scopes", "token_type", "refresh", "expires"])
def test_token_grant_never_promotes_identity_to_plan_permission(tmp_path, fault):
    c, make, seen, state = oauth(tmp_path)
    value = {
        "access_token": "PUBLIC",
        "refresh_token": "PUBLIC",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": " ".join(SCOPES),
    }
    if fault == "scopes":
        value["scope"] = "openid profile email"
    elif fault == "token_type":
        value["token_type"] = "Basic"
    elif fault == "refresh":
        del value["refresh_token"]
    else:
        value["expires_in"] = "3600"
    with pytest.raises(StopRun):
        c.tokens(value, "oaiapp_fixture", "subject")


def test_credential_symlink_or_world_permissions_rejected(tmp_path):
    c, make, seen, state = oauth(tmp_path)
    target = tmp_path / "original"
    target.write_text("{}")
    target.chmod(0o600)
    c.path.symlink_to(target)
    with pytest.raises(StopRun):
        c.read(c.path)
    c.path.unlink()
    c.path.write_text("{}")
    c.path.chmod(0o644)
    with pytest.raises(StopRun):
        c.read(c.path)


@pytest.mark.parametrize("mode", ["absent", "low"])
def test_account_catalog_live_get_required_no_model_substitute(tmp_path, mode):
    c, make, seen, state = oauth(tmp_path)
    c.write(
        tmp_path / "main-registration.json", {"client_id": "oaiapp_fixture", "subject": "subject"}
    )
    c.write(
        c.path,
        {
            "client_id": "oaiapp_fixture",
            "subject": "subject",
            "access_token": "PUBLIC",
            "expires_at": time.time() + 3600,
        },
    )

    def reply(request):
        assert str(request.url) == RESOURCE + "/models"
        return httpx.Response(
            200,
            json={
                "models": []
                if mode == "absent"
                else [{"slug": MODEL, "visibility": "list", "supported_reasoning_levels": ["high"]}]
            },
        )

    c.transport = httpx.MockTransport(reply)
    with pytest.raises(StopRun, match="NOT_AVAILABLE"):
        c.models()


