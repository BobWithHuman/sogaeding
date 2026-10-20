"""Isolated runtime service entry points; user run never selects fake models."""

import argparse
import json
import ssl
from pathlib import Path

import httpx
import uvicorn
from fastapi import Request

from app.benchmark.provider import ProviderTransport, broker_app
from app.benchmark.proxy import create_proxy
from app.benchmark.runtime_budget import RuntimeBudget
from app.benchmark.runtime_policy import RuntimeEngine, RuntimePolicy, SharedJev, SyntheticBoundary
from app.benchmark.runtime_registry import RuntimeRegistry
from app.benchmark.server import control_app, serve_control, serve_proxy
from app.common import digest
from app.transparent.engine import Rejected


def read_config(path="/config/runtime.json"):
    return json.loads(Path(path).read_text())


def boundary(config):
    return SyntheticBoundary(
        [
            *config["protected_credentials"],
            Path("/runtime/machine.token").read_text().strip(),
            Path("/runtime/forward.key").read_text().strip(),
        ],
        max_source_bytes=config["limits"]["source_bytes"],
        max_catalog_bytes=config["limits"]["catalog_bytes"],
    )


def control(config):
    registry = RuntimeRegistry(config["registry"])
    guard = boundary(config)

    async def jev(body):
        ca = ssl.create_default_context(cafile="/runtime/ca.pem")
        async with httpx.AsyncClient(
            base_url=config["provider_url"], verify=ca, trust_env=False, timeout=18
        ) as client:
            response = await client.post(
                "/v1/systemone",
                json=body,
                headers={"Authorization": "Bearer " + config["jev_token"]},
            )
            response.raise_for_status()
            return response.json()

    policy = RuntimePolicy(
        SharedJev(jev, guard, live=config["provider_mode"] == "LIVE"),
        registry,
        guard,
        config["norms"],
        enabled=config["arm"] == "engine-on",
        profile=config.get("policy_profile"),
    )
    scope = json.loads(Path("/runtime/grant.json").read_text()).get("task_scope")
    if scope:
        from app.benchmark.task_scope import ResourceProbe

        policy.scope_probe = ResourceProbe(scope, registry)
    app = control_app(
        "/runtime",
        registry,
        policy,
        config["catalog"],
        engine_factory=lambda *a, **k: RuntimeEngine(*a, boundary=guard, **k),
    )
    policy.source_lookup = app.state.runtime_engine.source_roles

    # A trusted prompt injection is source material, never a new USER grant.
    # It is bound to the exact current connection/turn and immutable full text.
    @app.post("/runtime/prompt-source")
    async def prompt_source(request: Request):
        import hmac
        from uuid import uuid4

        engine = app.state.runtime_engine
        if not hmac.compare_digest(
            request.headers.get("authorization", ""),
            "Bearer " + Path("/runtime/machine.token").read_text().strip(),
        ):
            raise Rejected("ROLE_AUTHENTICATION_FAILED")
        value = await request.json()
        if set(value) != {"connection", "text", "turn"}:
            raise Rejected("INVALID_EVENT")
        machine, session = engine.connection(value["connection"])
        source = {
            "source_id": str(uuid4()),
            "call_id": "prompt-" + digest(value["turn"]),
            "origin": "mcp",
            "same_issue": False,
            **guard.material(value["text"]),
        }
        if not source["analysis_complete"]:
            raise Rejected("SOURCE_CONTEXT_INCOMPLETE")
        with engine.db() as db:
            engine._current(db, machine, session, value["turn"])
            if db.execute(
                "SELECT 1 FROM sources WHERE session=? AND call=?", (session, source["call_id"])
            ).fetchone():
                raise Rejected("CALL_REPLAY")
            db.execute(
                "INSERT INTO sources VALUES(?,?,?,?)",
                (source["source_id"], session, source["call_id"], engine.seal(source)),
            )
            engine.audit(db, "PROMPT_SOURCE", "OBSERVED")
        return {"state": "OBSERVED_UNTRUSTED_PROMPT_SOURCE"}

    serve_control(app, "/runtime")


def proxy(config):
    registry = RuntimeRegistry(config["registry"])
    app = create_proxy(
        registry,
        config["mcp_endpoints"],
        "/data/attempts.sqlite3",
        Path("/runtime/forward.key").read_text().strip(),
    )
    serve_proxy(app, "/runtime")


def plan_transport(budget, *, offline):
    from app.benchmark.siwc_auth import Credentials
    from app.benchmark.siwc_transport import PlanTransport

    if offline:
        from app.benchmark.siwc_test_provider import FixtureCredentials, fake_provider

        return PlanTransport(
            budget,
            FixtureCredentials(),
            transport=httpx.MockTransport(
                lambda request: fake_provider(
                    request, functional=bool(budget.manifest.get("functional_routing"))
                )
            ),
        )
    credentials = Credentials(account=budget.manifest["chatgpt_plan"]["account_label"])
    checked = credentials.models()  # Account catalog only, no inference.
    with budget.db() as db:
        db.execute("CREATE TABLE IF NOT EXISTS plan_account(binding TEXT PRIMARY KEY)")
        old = db.execute("SELECT binding FROM plan_account").fetchall()
        if old and old != [(checked["account_binding_sha256"],)]:
            raise ValueError("SIWC_ACCOUNT_CHANGED_STOP_BOTH")
        if not old:
            db.execute("INSERT INTO plan_account VALUES(?)", (checked["account_binding_sha256"],))
    return PlanTransport(budget, credentials, live=True)


def broker(config, *, offline):
    budget = RuntimeBudget("/data/provider.sqlite3", config["manifest"])
    if offline != (config["manifest"]["mode"] == "OFFLINE"):
        raise ValueError("MOCK_FORBIDDEN_IN_USER_RUN")
    if offline:
        if config["manifest"].get("chatgpt_plan"):
            from app.benchmark.siwc_test_provider import fake_provider
        elif config["manifest"].get("utility_acceptance"):
            from app.benchmark.runtime_utility_test_provider import fake_provider
        else:
            from app.benchmark.runtime_test_provider import fake_provider

        provider = ProviderTransport(
            budget,
            {"openai": "PUBLIC-OFFLINE-OPENAI", "typesafe": "PUBLIC-OFFLINE-TYPESAFE"},
            transport=httpx.MockTransport(fake_provider),
            plan=plan_transport(budget, offline=True)
            if config["manifest"].get("chatgpt_plan")
            else None,
        )
    else:
        authorization = json.loads(Path("/data/paid-opt-in.json").read_text())
        if (
            authorization.get("manifest_sha256") != budget.binding
            or authorization.get("max_total_micro_usd")
            != config["manifest"]["limits"]["total"]["micro_usd"]
        ):
            raise ValueError("EXPLICIT_MATCHING_PAID_OPT_IN_REQUIRED")
        # Existing keys are referenced RO only here, outside all victim/tool
        # containers. Their values/hashes never go to an artifact or prompt.
        keys = {"typesafe": Path("/keys/jev.api-key").read_text().strip()}
        if not config["manifest"].get("chatgpt_plan"):
            keys["openai"] = Path("/keys/openai.api-key").read_text().strip()
        elif Path("/keys/openai.api-key").exists():
            raise ValueError("SIWC_API_KEY_FORBIDDEN_NO_FALLBACK")
        provider = ProviderTransport(
            budget,
            keys,
            live=True,
            plan=plan_transport(budget, offline=False)
            if config["manifest"].get("chatgpt_plan")
            else None,
        )
    app = broker_app(
        budget,
        provider,
        Path("/runtime/broker.secret").read_text().strip(),
        Path("/runtime/admin.token").read_text().strip(),
    )
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8500,
        ssl_certfile="/runtime/broker.pem",
        ssl_keyfile="/runtime/broker.key",
        access_log=False,
        proxy_headers=False,
        log_level="critical",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["control", "proxy", "broker"])
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    config = read_config()
    if args.role == "broker":
        broker(config, offline=args.offline)
    elif args.offline:
        raise ValueError("OFFLINE_FLAG_ONLY_PROVIDER_ROLE")
    elif args.role == "control":
        control(config)
    else:
        proxy(config)


if __name__ == "__main__":
    main()
