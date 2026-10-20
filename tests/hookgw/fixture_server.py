"""OFFLINE TRANSPORT FIXTURE ONLY. Never installed by the product launcher.

Scripted observations exercise strict refs/composition; they do not measure IPI accuracy.
"""
import asyncio
import ssl
from pathlib import Path

import uvicorn

from app.common import canonical
from app.pdp.diagnostics import AnalysisFailure
from app.pdp.semantic import span_catalog
from app.transparent.engine import Engine
from app.transparent.server import create_app, public_app, secret, ticket


class FixtureJudge:
    is_fixture = True
    async def analyze(self, snapshot):
        candidate = snapshot["candidate"]
        args = candidate["args"]
        text = canonical(candidate)
        # Exact safe fixture corpus only. This is not a natural-language judge.
        if candidate["route"] != "mcp" or args.get("path") not in (
            "fixtures/hookgw/notes.txt", "fixtures/hookgw/attack.txt", "fixtures/hookgw/normal-output.txt", "fixtures/hookgw/forbidden-output.txt"
        ):
            raise AnalysisFailure("JUDGE_NOT_CONFIGURED", "PAIR")
        def obs(view):
            ref = {"source_id": "candidate", "start": 0, "end": min(len(text), 100), "quote": text[:100]}
            relation, external, reason = "DIRECT", "NONE", "USER_INTENT_SUPPORTED"
            if view == "B" and snapshot["sources"]:
                source = snapshot["sources"][-1]
                quote = source["analysis_text"][:100]
                ref = {"source_id": source["source_id"], "start": 0, "end": len(quote), "quote": quote}
                relation, external, reason = "DATA_DEPENDENT", "TASK_DATA", "TASK_DATA_SUPPORTED"
                if args.get("path", "").endswith("forbidden-output.txt"):
                    external, reason = "NEW_INSTRUCTION", "EXTERNAL_INSTRUCTION_DEPENDENCY"
            sid = next(s["span_id"] for s in span_catalog(snapshot, view)["spans"] if s["source_id"] == ref["source_id"])
            return {"task_relation": relation, "external_use": external, "reason": reason, "evidence_span_ids": [sid]}
        return [obs("A"), obs("B")]


if __name__ == "__main__":
    import json
    runtime = Path("/runtime")
    grant = json.loads((runtime / "grant.json").read_text())
    engine = Engine("/data/control.sqlite3", secret("storage.key").encode(), grant, FixtureJudge())
    app = create_app(engine, {"machine": secret("machine.token"), "human": secret("human.token"), "machine_id": secret("machine.id"), "ticket": ticket})
    async def run():
        opts = dict(host="0.0.0.0", ssl_certfile="/runtime/control.pem", ssl_keyfile="/runtime/control.key", access_log=False, proxy_headers=False, log_level="critical")
        await asyncio.gather(uvicorn.Server(uvicorn.Config(public_app(app), port=8030, **opts)).serve(),
                             uvicorn.Server(uvicorn.Config(app, port=8050, ssl_ca_certs="/runtime/ca.pem", ssl_cert_reqs=ssl.CERT_REQUIRED, **opts)).serve())
    asyncio.run(run())
