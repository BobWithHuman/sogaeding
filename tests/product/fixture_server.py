"""Explicit test command only: real product/TLS/storage, fixed Jev observations."""
import json
import os
from pathlib import Path

import httpx
from conftest import Observer

from app.transparent.engine import Engine
from app.transparent.jev import MODEL, JevClient
from app.transparent.jev_config import load_runtime_settings, make_policy
from app.transparent.server import RUNTIME, create_app, secret, serve_app, ticket


async def synthetic_http(request):
    body=json.loads(request.content)
    content=body["state"]["candidate"].get("args",{}).get("content","")
    behavior="EXTERNAL_ADOPTION" if "AUDIT_UNREQUESTED_EXFIL" in content else "LEGITIMATE"
    observer=Observer(b=behavior,b_confidence=1. if behavior=="EXTERNAL_ADOPTION" else .8)
    view="B" if any(name in body["questions"] for name in ("behavior","current_behavior","benchmark_behavior")) else "A"
    answers=await observer.observe(view,body["state"],body["questions"],"synthetic-http")
    return httpx.Response(200,json={"model":MODEL,"answers":dict(answers),"usage":{"input_tokens":10,"output_tokens":5}})


if __name__=="__main__":
    grant=json.loads((RUNTIME/"grant.json").read_text())
    client=JevClient(load_runtime_settings(Path(os.environ["JEV_POLICY_FILE"])),transport=httpx.MockTransport(synthetic_http))
    client.is_fixture=True
    engine=Engine("/data/control.sqlite3",secret("storage.key").encode(),grant,
                  policy_router=make_policy(client),preserve_history_on_policy_change=True)
    keys={"machine":secret("machine.token"),"human":secret("human.token"),
          "machine_id":secret("machine.id"),"ticket":ticket}
    serve_app(create_app(engine,keys),Path(RUNTIME))
