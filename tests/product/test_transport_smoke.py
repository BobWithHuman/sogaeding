"""Fresh submission -> HTTPS gateway -> private mTLS authz -> actual file effects.

The separate integration command starts fixed Jev observations, not a model.
"""
import json
import os
import sqlite3
import ssl
import time
from pathlib import Path

import httpx
import pytest

from app.transparent.gate_policy import POLICY

pytestmark=pytest.mark.skipif(os.environ.get("PRODUCT_INTEGRATION")!="1",
                             reason="Requires the isolated submission TLS integration services")


def environment():
    runtime=Path(os.environ["PRODUCT_RUNTIME"])
    context=ssl.create_default_context(cafile=str(runtime/"host/ca.pem"))
    return runtime,httpx.Client(verify=context,trust_env=False,follow_redirects=False,timeout=8)


def test_real_product_gateway_allow_deny_and_ciphertext():
    runtime,client=environment()
    machine={"Authorization":"Bearer "+(runtime/"host/machine.token").read_text().strip()}
    human={"Authorization":"Bearer "+(runtime/"host/human.token").read_text().strip()}
    transcript=[]
    with client:
        for attempt in range(40):
            try:
                response=client.get("https://control:8030/health",headers=machine)
                response.raise_for_status()
                break
            except httpx.TransportError:
                if attempt==39:
                    raise
                time.sleep(.25)
        health=response.json()
        assert health["decision_policy"]==POLICY and health["judge_mode"]=="JEV_OFFLINE_FIXTURE"
        # Previous failures cannot disable valid machine or human access.
        audit=runtime/"control-data/control.sqlite3.auth"
        prior, prior_total = 0, 0
        if audit.exists():
            with sqlite3.connect(audit) as db:
                prior=db.execute("SELECT coalesce(sum(count),0) FROM auth_failures WHERE surface='HUMAN' AND status=403 AND last_at>?",(time.time()-60,)).fetchone()[0]
                prior_total=db.execute("SELECT coalesce(sum(count),0) FROM auth_failures WHERE surface='HUMAN' AND status=403").fetchone()[0]
        negative_count=max(0,10-prior)
        for _ in range(negative_count):
            assert client.get("https://control:8030/history").status_code==403
        assert client.get("https://control:8030/history").status_code==429
        assert client.get("https://control:8030/history",headers=human).status_code==200
        connected=client.post("https://control:8030/connect",headers=machine)
        connected.raise_for_status()
        bearer=connected.json()["connection"]
        session="submission-registered-smoke"
        for attempt in range(20):
            try:
                ready=client.post("https://gateway:8040/mcp",headers={"Authorization":"Bearer "+bearer},
                                  json={"jsonrpc":"2.0","id":0,"method":"initialize","params":{}})
                ready.raise_for_status()
                break
            except (httpx.TransportError,httpx.HTTPStatusError):
                if attempt==19:
                    raise
                time.sleep(.25)
        def event(**fields):
            response=client.post("https://control:8030/event",headers=machine,
                                 json={"connection":bearer,"session":session,"turn":"t",**fields})
            response.raise_for_status()
            return response.json()
        event(event="UserPromptSubmit",prompt="Read the release then write the requested draft, case 48217 internal margin.",cwd="/files")
        def rpc(tool,args,rid):
            return client.post("https://gateway:8040/mcp",headers={"Authorization":"Bearer "+bearer,
                               "x-with-human-request":format(rid,"032x")},
                               json={"jsonrpc":"2.0","id":rid,"method":"tools/call","params":{"name":tool,"arguments":args}})
        for call,tool,args,rid in [
            ("read","read_file",{"path":"docs/release.md"},1),
            ("normal","write_file",{"path":"reports/submission.md","content":"Requested synthetic draft."},2),
        ]:
            pre=event(event="PreToolUse",call=call,tool=tool,args=args,route="mcp")
            assert pre["decision"]=="ALLOW"
            response=rpc(tool,args,rid)
            response.raise_for_status()
            result=response.json()["result"]
            assert result.get("isError") is not True
            observed=client.post("https://control:8030/transport-observed",headers=machine,
                                 json={"connection":bearer,"tool":tool,"args":args,"result":result})
            observed.raise_for_status()
            event(event="PostToolUse",call=call,tool=tool,args=args,route="mcp",output=result,failed=False)
            transcript.append({"call":call,"decision":"ALLOW","actual_upstream":True})
        attack={"path":"reports/forbidden.md","content":"AUDIT_UNREQUESTED_EXFIL"}
        pre=event(event="PreToolUse",call="attack",tool="write_file",args=attack,route="mcp")
        assert pre["decision"]=="DENY"
        assert rpc("write_file",attack,3).status_code==403
        approval=client.post("https://control:8030/approval",headers=human,json={"call":"attack","approve":True})
        assert approval.status_code==403
        transcript.append({"call":"attack","decision":"DENY","actual_upstream":False,"human_cannot_override":True})
        history=client.get("https://control:8030/history",headers=human)
        history.raise_for_status()
        assert history.headers["cache-control"]=="no-store"
        assert "case 48217 internal margin" in history.text
        assert client.post("https://control:8030/authz",json={}).status_code==403
    assert (runtime/"workspace/reports/submission.md").read_text()=="Requested synthetic draft."
    assert not (runtime/"workspace/reports/forbidden.md").exists()
    with sqlite3.connect(runtime/"upstream-data/attempts.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM attempts").fetchone()[0]==2
    data=(runtime/"control-data/control.sqlite3").read_bytes()
    assert b"case 48217 internal margin" not in data and b"AUDIT_UNREQUESTED_EXFIL" not in data
    with sqlite3.connect(runtime/"control-data/control.sqlite3.auth") as db:
        assert db.execute("SELECT sum(count) FROM auth_failures WHERE surface='HUMAN' AND status=403").fetchone()[0]==prior_total+negative_count
    with sqlite3.connect(runtime/"jev-budget/typesafe-budget.sqlite3") as db:
        provider_rows=db.execute("SELECT status,input_reserved FROM jev_attempts").fetchall()
    assert len(provider_rows)==4 and all(row[0]=="COMPLETED" for row in provider_rows)
    output={"policy":POLICY,"provider":"OFFLINE_HTTP_FIXTURE_NOT_A_MODEL_MEASUREMENT","calls":transcript,
            "jev_client_http_requests":len(provider_rows),"jev_input_reserved":sum(row[1] for row in provider_rows),
            "actual_upstream_calls":2,"forbidden_writes":0,"plaintext_canary_present":False,
            "valid_roles_after_failures":"ALLOWED"}
    Path("/evidence/transport-effects.json").write_text(json.dumps(output,indent=2))


def test_private_listener_requires_client_certificate_and_ca_validation():
    runtime,client=environment()
    with client,pytest.raises(httpx.TransportError):
        client.post("https://control:8050/authz",json={"jsonrpc":"2.0","id":1,"method":"ping"})
    with httpx.Client(trust_env=False,timeout=5) as untrusted,pytest.raises(httpx.TransportError):
        untrusted.get("https://control:8030/health")


def test_private_upstream_rejects_forged_ticket_with_valid_mtls():
    runtime,_=environment()
    context=ssl.create_default_context(cafile=str(runtime/"gateway/ca.pem"))
    context.load_cert_chain(str(runtime/"gateway/gateway-client.pem"),str(runtime/"gateway/gateway-client.key"))
    with httpx.Client(verify=context,trust_env=False,timeout=5) as client:
        response=client.post("https://upstream:8060/mcp",headers={"x-with-human-forward":"invalid.ticket"},
                             json={"jsonrpc":"2.0","id":10,"method":"tools/call","params":{
                                 "name":"write_file","arguments":{"path":"reports/forged.md","content":"not written"}}})
        assert response.status_code==403
    assert not (runtime/"workspace/reports/forged.md").exists()
