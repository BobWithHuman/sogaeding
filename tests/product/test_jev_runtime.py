"""Production Jev wire/client and gate-6 together; HTTP is explicitly mocked."""
import asyncio
import importlib.util
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from conftest import Observer
from cryptography.fernet import Fernet

from app.pdp.diagnostics import AnalysisFailure
from app.transparent import server
from app.transparent.engine import Engine, Rejected
from app.transparent.jev import ENDPOINT, MODEL, JevClient, JevSettings, validate_response
from app.transparent.jev_config import load_runtime_settings, make_policy

ROOT = Path(__file__).resolve().parents[2]


def test_unlimited_requires_explicit_mode_and_keeps_auditable_attempts(tmp_path,engine_factory):
    from app.transparent.dashboard import Projection
    settings=JevSettings(enabled=True,key_path=tmp_path/'jev.api-key',
                         budget_path=tmp_path/'typesafe-budget.sqlite3',policy_id='explicit-unlimited',unlimited=True)
    assert settings.authorized()
    assert not replace(settings,unlimited=False).authorized()
    assert not replace(settings,unlimited='yes').authorized()
    assert not replace(settings,request_limit=100).authorized()
    client=JevClient(settings)
    engine=engine_factory()
    engine.policy_router.client=client
    empty=Projection(engine,'m').ledger()
    assert empty['unlimited'] is True and empty['requests'] is None and empty['status']=='UNAVAILABLE'
    for i in range(105):
        client._claim(str(i),'A')
    with sqlite3.connect(settings.budget_path) as db:
        assert db.execute('SELECT count(*),sum(input_reserved) FROM jev_attempts').fetchone()==(105,0)
        binding=json.loads(db.execute('SELECT binding FROM jev_policy').fetchone()[0])
        assert binding['unlimited'] is True and binding['input_token_limit'] is None
    ledger=Projection(engine,'m').ledger()
    assert ledger['status']=='AVAILABLE' and ledger['requests']==105 and ledger['unlimited'] is True
    assert ledger['request_limit'] is None and ledger['input_reservation_remaining'] is None
    assert ledger['input_tokens_actual'] is None  # unknown usage is not zero


def test_provider_usage_above_old_token_threshold_is_observed_without_quota():
    questions={'q':{'type':'noul','instructions':'Is this directly requested?'}}
    _,usage=validate_response({'model':MODEL,'answers':{'q':{'type':'noul','noul':.8}},
                               'usage':{'input_tokens':64001,'output_tokens':1000001}},questions)
    assert usage=={'input_tokens':64001,'output_tokens':1000001}


def test_product_start_requires_jev_instead_of_silent_rules_only(tmp_path,monkeypatch):
    (tmp_path/"grant.json").write_text(json.dumps({"workspace":"/files"}))
    monkeypatch.setattr(server,"RUNTIME",tmp_path)
    monkeypatch.setenv("HOOKGW_PDP","JEV")
    monkeypatch.delenv("HOOKGW_REQUIRE_JEV",raising=False)
    monkeypatch.setenv("JEV_POLICY_FILE",str(tmp_path/"missing.json"))
    monkeypatch.setattr(server,"serve_app",lambda *_:pytest.fail("Missing configuration must not serve"))
    with pytest.raises(RuntimeError,match="JEV_CONFIGURATION_REQUIRED"):
        server.main()
    assert not list(tmp_path.glob("*.sqlite3"))


def test_explicit_offline_mode_and_invalid_disabled_policy(tmp_path):
    assert not load_runtime_settings(tmp_path/"missing.json",allow_offline=True).authorized()
    policy=tmp_path/"policy.json"
    value=json.loads((Path(__file__).with_name("jev-policy.json")).read_text())
    assert value["enabled"] is True and value["model"]==MODEL
    policy.write_text(json.dumps(value))
    assert load_runtime_settings(policy).authorized()
    value["enabled"]=False
    policy.write_text(json.dumps(value))
    with pytest.raises(RuntimeError,match="JEV_CONFIGURATION_REQUIRED"):
        load_runtime_settings(policy)


@pytest.mark.parametrize("key_value",[None,"","too-short","two words in a key","\u00ff"*20])
def test_configured_product_rejects_missing_or_invalid_key_before_serving(tmp_path,monkeypatch,key_value):
    (tmp_path/"grant.json").write_text(json.dumps({"workspace":"/files"}))
    policy=tmp_path/"policy.json"
    policy.write_bytes((Path(__file__).with_name("jev-policy.json")).read_bytes())
    key=tmp_path/"jev.api-key"
    if key_value is not None:
        key.write_text(key_value,encoding="utf-8")
    settings=replace(load_runtime_settings(policy),key_path=key,budget_path=tmp_path/"typesafe-budget.sqlite3")
    monkeypatch.setattr(server,"RUNTIME",tmp_path)
    monkeypatch.setenv("HOOKGW_PDP","JEV")
    monkeypatch.setattr("app.transparent.jev_config.load_runtime_settings",lambda *args,**kwargs:settings)
    monkeypatch.setattr(server,"serve_app",lambda *_:pytest.fail("Invalid key must not serve"))
    with pytest.raises(AnalysisFailure) as failure:
        server.main()
    assert failure.value.diagnostics[0]["code"]=="MISSING_API_KEY"
    assert not settings.budget_path.exists()


def test_valid_key_preflight_does_not_send_http_or_create_budget(tmp_path):
    policy=tmp_path/"policy.json"
    policy.write_bytes((Path(__file__).with_name("jev-policy.json")).read_bytes())
    key=tmp_path/"jev.api-key"
    key.write_text("synthetic-preflight-key-do-not-transmit")
    settings=replace(load_runtime_settings(policy),key_path=key,budget_path=tmp_path/"typesafe-budget.sqlite3")
    client=JevClient(settings,transport=httpx.MockTransport(lambda _:pytest.fail("Preflight must not send HTTP")))
    client.preflight()
    assert not settings.budget_path.exists()


@pytest.mark.parametrize("behavior,http_status,decision",[("LEGITIMATE",200,"ALLOW"),("EXTERNAL_ADOPTION",200,"DENY"),("LEGITIMATE",503,"DENY")])
def test_real_jev_client_wire_to_common_gate6_and_budget(tmp_path,behavior,http_status,decision):
    policy=tmp_path/"policy.json"
    policy.write_bytes((Path(__file__).with_name("jev-policy.json")).read_bytes())
    key=tmp_path/"jev.api-key"
    key.write_text("synthetic-jev-key-for-mocked-http-only")
    settings=replace(load_runtime_settings(policy),key_path=key,budget_path=tmp_path/"typesafe-budget.sqlite3")
    calls=[]
    observer=Observer(b=behavior,b_confidence=1.)
    async def wire(request):
        assert str(request.url)==ENDPOINT and request.method=="POST"
        assert request.headers["authorization"]=="Bearer "+key.read_text()
        body=json.loads(request.content)
        assert body["model"]==MODEL
        calls.append(body)
        if http_status!=200:
            return httpx.Response(http_status,text="SYNTHETIC_PRIVATE_ERROR_BODY")
        view="B" if any(name in body["questions"] for name in ("behavior","current_behavior","benchmark_behavior")) else "A"
        answers=await observer.observe(view,body["state"],body["questions"],"mocked-wire")
        return httpx.Response(200,json={"model":MODEL,"answers":dict(answers),"usage":{"input_tokens":10,"output_tokens":5}})
    client=JevClient(settings,transport=httpx.MockTransport(wire))
    engine=Engine(tmp_path/"control.sqlite3",Fernet.generate_key(),
                  {"workspace":"/files","tools":{"mcp":["read_file","write_file"]}},policy_router=make_policy(client))
    engine.turn("m","s","t","Write case 48217 internal margin to the draft.","/files")
    engine.register("m","s","t","w","write_file",{"path":"reports/draft.md","content":"Requested draft."},"mcp")
    result=asyncio.run(engine.authorize("m","w"))
    assert result["decision"]==decision and len(calls)==2
    with sqlite3.connect(settings.budget_path) as db:
        rows=db.execute("SELECT status,input_reserved FROM jev_attempts").fetchall()
    assert len(rows)==2 and sum(row[1] for row in rows)==(0 if settings.unlimited else 128000)
    assert {row[0] for row in rows}==({"COMPLETED"} if http_status==200 else {"FAILED"})
    if decision=="DENY":
        with pytest.raises(Rejected):
            engine.forward("m","w")
    assert not (tmp_path/"reports/draft.md").exists()
    assert b"SYNTHETIC_PRIVATE_ERROR_BODY" not in Path(engine.path).read_bytes()
    assert key.read_bytes() not in Path(engine.path).read_bytes()


def test_deployment_mounts_key_config_and_private_budget_for_control_only():
    import yaml
    config=yaml.safe_load((ROOT/"compose.yaml").read_text())
    control=config["services"]["control"]
    assert control["environment"]["HOOKGW_REQUIRE_JEV"]=="1"
    mounts={row["target"]:row for row in control["volumes"] if isinstance(row,dict)}
    for target in ("/jev-key/jev.api-key","/jev-config/policy.json"):
        assert mounts[target]["read_only"] and mounts[target]["bind"]["create_host_path"] is False
    assert mounts["/jev-budget"]["volume"]["subpath"].endswith("/jev-budget")
    for role in ("gateway","upstream","check"):
        assert "/jev-key" not in str(config["services"][role])
    assert "ingress" in control["networks"] and not config["networks"]["ingress"].get("internal",False)


def test_readiness_check_accepts_configured_jev_without_sending_inference(tmp_path,monkeypatch):
    # Exercise the shipped checker with mocked TLS HTTP; only discovery is allowed.
    spec=importlib.util.spec_from_file_location("product_team_runtime",ROOT/"tools/team_runtime.py")
    runtime=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    host=tmp_path/"host"
    host.mkdir()
    (host/"machine.token").write_text("synthetic-machine")
    calls=[]
    def wire(request):
        calls.append(str(request.url))
        if request.url.path=="/health":
            return httpx.Response(200,json={"judge_mode":"JEV_USER_LIVE","decision_policy":"engine-2026-10-24-gate6-1"})
        if request.url.path=="/history":
            return httpx.Response(403)
        if request.url.path=="/connect":
            return httpx.Response(200,json={"connection":"synthetic-connection"})
        if request.url.path=="/disconnect":
            return httpx.Response(200,json={"state":"CLOSED"})
        body=json.loads(request.content)
        assert body["method"] in ("initialize","tools/list")
        return httpx.Response(200,json={"result":{"tools":[{"name":"read_file"},{"name":"write_file"}]}})
    original=httpx.Client
    monkeypatch.setattr(runtime.httpx,"Client",lambda **kwargs:original(transport=httpx.MockTransport(wire)))
    import ssl
    monkeypatch.setattr(ssl,"create_default_context",lambda **kwargs:None)
    runtime.check(tmp_path)
    assert len(calls)==6 and not any("typesafe" in url for url in calls)
