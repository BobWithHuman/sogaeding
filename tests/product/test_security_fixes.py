import asyncio
import json
import sqlite3

import httpx
import pytest
from cryptography.fernet import Fernet

from app.common import canonical
from app.transparent.engine import Engine, Rejected
from app.transparent.jev_config import make_policy
from app.transparent.server import create_app, public_app

KEYS={"machine_id":"m","human":"synthetic-human-credential","machine":"synthetic-machine-credential",
      "ticket":lambda *_:"not-a-forward-ticket"}


def request(app,path="/history",*,token=None,headers=None,method="GET",body=None):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url="https://control") as client:
            return await client.request(method,path,headers=headers if headers is not None else
                {"Authorization":"Bearer "+(token or KEYS["human"])},json=body)
    return asyncio.run(run())


def test_sec01_invalid_attempts_do_not_lock_valid_roles_or_extend_failures(engine,monkeypatch):
    clock=[100000.]
    monkeypatch.setattr("time.time",lambda:clock[0])
    app=public_app(create_app(engine,KEYS))
    assert request(app).status_code==200
    for _ in range(10):
        assert request(app,token="invalid").status_code==403
    assert request(app,token="invalid").status_code==429
    assert request(app).status_code==200
    assert request(app,"/connect",method="POST",token=KEYS["machine"]).status_code==200
    # Other roles have their own failure window.
    assert request(app,"/connect",method="POST",token="invalid").status_code==403
    for second in range(2,132,2):
        clock[0]=100000.+second
        assert request(app).status_code==200
    assert request(app,token="invalid").status_code==403
    with sqlite3.connect(str(engine.path)+".auth") as db:
        assert db.execute("SELECT sum(count) FROM auth_failures WHERE surface='HUMAN' AND status=429").fetchone()[0]==1


def test_sec03_non_ascii_and_duplicate_bearers_are_audited_auth_failures(engine):
    app=public_app(create_app(engine,KEYS))
    for headers in [[(b"authorization",b"Bearer \xff\xfe")],
                    [(b"authorization",b"Bearer "+KEYS["human"].encode()),(b"authorization",b"Bearer invalid")]]:
        response=request(app,headers=headers)
        assert response.status_code==403 and response.json()["code"]=="AUTHENTICATION_FAILED"
    with sqlite3.connect(str(engine.path)+".auth") as db:
        assert db.execute("SELECT sum(count) FROM auth_failures WHERE surface='HUMAN'").fetchone()[0]==2
    assert request(app).status_code==200


def test_auth_audit_storage_failure_is_not_allowed(engine):
    app=public_app(create_app(engine,KEYS))
    from pathlib import Path
    Path(str(engine.path)+".auth").write_bytes(b"not a database")
    assert request(app).status_code==503
    assert request(app,"/connect",method="POST",token=KEYS["machine"]).status_code==503
    with engine.db() as db:
        assert db.execute("SELECT count(*) FROM connections").fetchone()[0]==0


@pytest.mark.parametrize("malformed",["duplicate_valid_first","duplicate_valid_last","missing_scheme","non_ascii"])
def test_private_authz_uses_the_same_single_ascii_bearer_syntax(engine,malformed):
    app=create_app(engine,KEYS)  # private app; deployment additionally requires mTLS
    token="synthetic-agent-connection"
    engine.connect("m",token)
    rpc={"jsonrpc":"2.0","id":1,"method":"tools/list"}
    assert request(app,"/authz",method="POST",token=token,body=rpc).status_code==200
    good=(b"authorization",b"Bearer "+token.encode())
    bad=(b"authorization",b"Bearer invalid")
    headers={"duplicate_valid_first":[good,bad],"duplicate_valid_last":[bad,good],
             "missing_scheme":[(b"authorization",token.encode())],
             "non_ascii":[(b"authorization",b"Bearer \xff\xfe")]}[malformed]
    response=request(app,"/authz",method="POST",headers=headers,body=rpc)
    assert response.status_code==403 and response.json()["code"]=="AUTHENTICATION_FAILED"
    with sqlite3.connect(str(engine.path)+".auth") as db:
        assert db.execute("SELECT sum(count) FROM auth_failures WHERE surface='AGENT'").fetchone()[0]==1
    from pathlib import Path
    assert token.encode() not in Path(str(engine.path)+".auth").read_bytes()
    assert request(app,"/authz",method="POST",token=token,body=rpc).status_code==200


def authorize(engine,*,content="Requested draft."):
    engine.turn("m","s","t","Write case 48217 internal margin to the draft.","/files")
    result=engine.register("m","s","t","write","write_file",{"path":"reports/draft.md","content":content},"mcp")
    return result,asyncio.run(engine.authorize("m","write"))


def test_metadata_history_is_human_only_bounded_and_excludes_large_context(engine):
    authorize(engine)
    with engine.db() as db:
        row=db.execute("SELECT reason FROM calls WHERE id='write'").fetchone()
        context=engine.read_reason(row["reason"])
        context["large_private_quote"]="PRIVATE_CANARY"*20000
        context["reasons"]=["REASON_"+str(i) for i in range(100)]
        db.execute("UPDATE calls SET reason=? WHERE id='write'",(engine.write_reason(context),))
    app=public_app(create_app(engine,KEYS))
    assert request(app,"/history/summary",token=KEYS["machine"]).status_code==403
    reply=request(app,"/history/summary")
    assert reply.status_code==200 and reply.headers["cache-control"]=="no-store"
    assert len(reply.content)<2000 and "PRIVATE_CANARY" not in reply.text
    value=reply.json()
    assert value["counts"]=={"ALLOW":1} and value["scope"]=="LATEST_100_CALLS"
    assert len(value["calls"][0]["reasons"])==8 and value["calls"][0]["reasons_truncated"] is True


@pytest.mark.parametrize("decision",["ALLOW","DENY","ASK"])
def test_sec02_full_context_and_payload_are_encrypted_but_authorized_history_works(engine,observer,decision):
    if decision=="DENY":
        observer.a="OUTSIDE_TASK"
    elif decision=="ASK":
        observer.b="UNCERTAIN"
    payload="Private audit payload 97312 projected margin."
    _,result=authorize(engine,content=payload)
    assert result["decision"]==decision
    with engine.db() as db:
        row=db.execute("SELECT reason,body FROM calls WHERE id='write'").fetchone()
        raw=row["reason"]
        assert engine.open(row["body"])["args"]["content"]==payload
    assert "case 48217 internal margin" not in raw and payload not in raw
    assert "case 48217 internal margin" in canonical(engine.read_reason(raw))
    from pathlib import Path
    assert b"case 48217 internal margin" not in Path(engine.path).read_bytes()
    assert payload.encode() not in Path(engine.path).read_bytes()
    app=public_app(create_app(engine,KEYS))
    response=request(app)
    assert response.status_code==200 and response.headers["cache-control"]=="no-store"
    assert "case 48217 internal margin" in response.text
    assert request(app,token=KEYS["machine"]).status_code==403


@pytest.mark.parametrize("mutation",["plaintext","ciphertext"])
def test_tampered_context_cannot_forward(engine,mutation):
    _,result=authorize(engine)
    assert result["decision"]=="ALLOW"
    with engine.db() as db:
        raw=db.execute("SELECT reason FROM calls WHERE id='write'").fetchone()[0]
        value=json.loads(raw)
        if mutation=="plaintext":
            raw=canonical(engine.read_reason(raw))
        else:
            value["body"]=value["body"][:-4]+"AAAA"
            raw=canonical(value)
        db.execute("UPDATE calls SET reason=? WHERE id='write'",(raw,))
    with pytest.raises(Rejected,match="DECISION_CONTEXT_INVALID"):
        engine.forward("m","write")
    with engine.db() as db:
        assert db.execute("SELECT state FROM calls WHERE id='write'").fetchone()[0]=="READY"


def test_legacy_plain_context_migrates_and_old_ready_authority_is_revoked(tmp_path,observer):
    path,key=tmp_path/"old.sqlite3",Fernet.generate_key()
    old=Engine(path,key,{"workspace":"/files","tools":{"mcp":["read_file","write_file"]}},policy_router=make_policy(observer))
    authorize(old)
    with old.db() as db:
        raw=db.execute("SELECT reason FROM calls WHERE id='write'").fetchone()[0]
        original=old.read_reason(raw)
        # Simulate an actual pre-upgrade on-disk row, without touching an old run.
        db.execute("UPDATE calls SET reason=? WHERE id='write'",(canonical(original),))
    upgraded=Engine(path,key,old.grant,policy_router=make_policy(observer),preserve_history_on_policy_change=True)
    with upgraded.db() as db:
        row=db.execute("SELECT state,reason FROM calls WHERE id='write'").fetchone()
    assert row["state"]=="STALE" and upgraded.read_reason(row["reason"])==original
    assert b"case 48217 internal margin" not in path.read_bytes()
    with pytest.raises(Rejected):
        upgraded.forward("m","write")
    reopened=Engine(path,key,old.grant,policy_router=make_policy(observer),preserve_history_on_policy_change=True)
    with reopened.db() as db:
        assert db.execute("SELECT reason FROM calls WHERE id='write'").fetchone()[0]==row["reason"]
