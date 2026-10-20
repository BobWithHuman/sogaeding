"""Explicit fake HTTP integration only; never installed as the product server."""
import asyncio
import json
import ssl
from pathlib import Path

import uvicorn
from test_jev_policy import FakeHTTP

from app.transparent.engine import Engine
from app.transparent.jev_policy import JevPolicy
from app.transparent.server import create_app, public_app, secret, ticket


class FixtureHTTP(FakeHTTP):
    def respond(self, request):
        candidate = json.loads(request.content)["state"]["candidate"]
        # Fixed fixture routing, not an attack detector or semantic ground truth.
        if candidate["route"] != "mcp" or candidate["args"].get("path") not in ("fixtures/hookgw/normal-output.txt", "fixtures/hookgw/forbidden-output.txt"):
            raise ValueError("OFFLINE_FIXTURE_SCOPE")
        self.mode = "attack" if candidate["args"]["path"].endswith("forbidden-output.txt") else "normal"
        return super().respond(request)


if __name__ == "__main__":
    target = Path("/tmp/jev-fixture")
    target.mkdir()
    fake = FixtureHTTP(target)
    fake.client.is_fixture = True
    engine = Engine("/data/control.sqlite3", secret("storage.key").encode(), json.loads(Path("/runtime/grant.json").read_text()), policy_router=JevPolicy(fake.client))
    app = create_app(engine, {"machine": secret("machine.token"), "human": secret("human.token"), "machine_id": secret("machine.id"), "ticket": ticket})
    async def serve():
        opts = dict(host="0.0.0.0", ssl_certfile="/runtime/control.pem", ssl_keyfile="/runtime/control.key", access_log=False, proxy_headers=False, log_level="critical")
        await asyncio.gather(uvicorn.Server(uvicorn.Config(public_app(app), port=8030, **opts)).serve(),
                             uvicorn.Server(uvicorn.Config(app, port=8050, ssl_ca_certs="/runtime/ca.pem", ssl_cert_reqs=ssl.CERT_REQUIRED, **opts)).serve())
    asyncio.run(serve())
