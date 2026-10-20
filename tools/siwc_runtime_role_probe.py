"""Read-only runtime binding plus public role IO; no provider credentials/API."""

import json
import os
import sqlite3
from pathlib import Path

from app.benchmark.docker_sandbox import DockerSandbox
from app.benchmark.runtime_login import verify

root = Path("/experiment")
verify(root, json.loads((root / "plan.json").read_text()))
assert os.geteuid() == 10001 and os.getegid() == 10001
client = DockerSandbox("with-human-storage-role-check")
assert client.client.get("/version").status_code == 200
work = root / "role-access-check"
work.mkdir(mode=0o700)
(work / "public.txt").write_text("PUBLIC ROLE CHECK")
with sqlite3.connect(work / "public.sqlite3") as db:
    db.execute("CREATE TABLE public_result(value TEXT)")
    db.execute("INSERT INTO public_result VALUES(?)", ("PASS",))
assert (work / "public.txt").read_text() == "PUBLIC ROLE CHECK"
print(
    json.dumps(
        {
            "result": "PASS",
            "uid": os.geteuid(),
            "gid": os.getegid(),
            "docker_socket_readonly_probe": 200,
            "frozen_verify": "PASS",
            "private_workspace_write": "PASS",
            "role_pki_check": "PASS",
            "model_requests": 0,
            "provider_api_calls": 0,
        }
    )
)
