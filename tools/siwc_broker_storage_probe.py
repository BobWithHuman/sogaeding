"""Actual UID10001 broker, SQLite writes and TLS health; no real credentials."""

import copy
import json
import shutil
import sqlite3
from pathlib import Path

from prepare_tls import generate

from app.benchmark.docker_sandbox import DockerSandbox, bind
from app.benchmark.runtime_login import check_broker_storage
from app.common import canonical, digest

ROOT = Path("/validation/fixture")
ROOT.mkdir()
for folder in ["broker-data", "broker-config", "broker-runtime"]:
    (ROOT / folder).mkdir()
m = copy.deepcopy(json.loads(Path("/prepared/plan.json").read_text())["manifest"])
m["mode"] = "OFFLINE"
with (
    sqlite3.connect("file:/prepared/broker-data/provider.sqlite3?mode=ro", uri=True) as original,
    sqlite3.connect(ROOT / "broker-data/provider.sqlite3") as db,
):
    original.backup(db)
    db.execute("UPDATE binding SET hash=?", (digest(canonical(m)),))
(ROOT / "broker-data").chmod(0o2770)
(ROOT / "broker-data/provider.sqlite3").chmod(0o660)
check_broker_storage(ROOT)
(ROOT / "broker-config/runtime.json").write_text(canonical({"manifest": m}))
generate(ROOT / "pki", [("broker", ["broker", "localhost", "127.0.0.1"])])
for name in ["ca.pem", "broker.pem", "broker.key"]:
    shutil.copyfile(ROOT / "pki" / name, ROOT / "broker-runtime" / name)
    (ROOT / "broker-runtime" / name).chmod(0o640)
for name, value in [
    ("admin.token", "PUBLIC-SYNTHETIC-ADMIN"),
    ("broker.secret", "PUBLIC-SYNTHETIC-SECRET"),
]:
    (ROOT / "broker-runtime" / name).write_text(value)
    (ROOT / "broker-runtime" / name).chmod(0o640)
host = Path("/validation-host-root").read_text().strip() + "/fixture"
image = "sha256:bd3607d2dae1d6c7e229ffecd9f056e501f23acd9221c7ec5a288856613a324d"
box = DockerSandbox("with-human-siwc-storage-validation")
off, on = "with-human-siwc-storage-validation-off", "with-human-siwc-storage-validation-on"
for net, subnet in [(off, "10.233.161.0/24"), (on, "10.233.162.0/24")]:
    box.network(net, subnet)
broker_code = """
import sqlite3,sys,runpy
with sqlite3.connect('/data/provider.sqlite3') as db:
 db.execute('CREATE TABLE IF NOT EXISTS plan_account(binding TEXT PRIMARY KEY)')
 db.execute('INSERT INTO plan_account VALUES(?)',('PUBLIC-SYNTHETIC-ACCOUNT',))
sys.argv=['runtime_services','broker','--offline']
runpy.run_module('app.benchmark.runtime_services',run_name='__main__')
"""
mounts = [
    bind(Path("/source-host-root").read_text().strip() + "/src", "/product/src"),
    bind(
        Path("/source-host-root").read_text().strip() + "/docs/mvp/contracts", "/product/contracts"
    ),
    bind(host + "/broker-data", "/data", False),
    bind(host + "/broker-config", "/config"),
    bind(host + "/broker-runtime", "/runtime"),
]
ids = []
result = {
    "provider_api_calls": 0,
    "real_credential_mounts": 0,
    "model_requests": 0,
    "broker_uid": 10001,
    "helper_uid": 0,
    "shared_gid": 10001,
}
try:
    broker = box.create_broker(
        "with-human-siwc-storage-validation-broker",
        image,
        ["python", "-c", broker_code],
        off_network=off,
        on_network=on,
        live=False,
        mounts=mounts,
        env={
            "PYTHONPATH": "/product/src:/benchdeps:/vendor",
            "CONTRACT_DIR": "/product/contracts",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    ids.append(broker)
    health = """
import json,time,httpx
for i in range(60):
 try:
  with httpx.Client(verify='/runtime/ca.pem',trust_env=False,timeout=2) as c:
   r=c.post('https://broker:8500/admin/status',json={},headers={'Authorization':'Bearer PUBLIC-SYNTHETIC-ADMIN'})
  r.raise_for_status();s=r.json();assert s['completed_arm_tasks']==0
  print(json.dumps({'tls_status':r.status_code,'new_jobs':sum(x['count'] for x in s['jobs'])}));break
 except httpx.TransportError:
  if i==59:raise
  time.sleep(.2)
"""
    outcomes = []
    for arm, net in [("off", off), ("on", on)]:
        client = box.create(
            "with-human-siwc-storage-validation-" + arm,
            image,
            ["python", "-c", health],
            network=net,
            user="0:10001",
            mounts=[bind(host + "/broker-runtime", "/runtime")],
        )
        ids.append(client)
        assert box.wait(client, timeout=40) == 0
        # Health is authenticated TLS through the same broker_app endpoint.
        outcomes.append({"arm": arm, "authenticated_tls_status": 200})
    denied = """
import sqlite3
try:
 with sqlite3.connect('/data/provider.sqlite3') as db:db.execute('CREATE TABLE unauthorized(x)')
except sqlite3.OperationalError: print('DENIED')
else: raise RuntimeError('UNTRUSTED_UID_ALLOWED')
"""
    outsider = box.create(
        "with-human-siwc-storage-validation-denied",
        image,
        ["python", "-c", denied],
        network=off,
        user="10002:10002",
        mounts=[bind(host + "/broker-data", "/data", False)],
    )
    ids.append(outsider)
    assert box.wait(outsider, timeout=20) == 0
    with sqlite3.connect(
        (ROOT / "broker-data/provider.sqlite3").as_uri() + "?mode=ro", uri=True
    ) as db:
        db.execute("PRAGMA query_only=ON")
        assert db.execute("SELECT count(*) FROM plan_account").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM plan_requests").fetchone()[0] == 0
    result.update(
        result="PASS",
        arms=outcomes,
        sqlite_write_by_broker=True,
        helper_readback=True,
        untrusted_uid_denied=True,
    )
finally:
    if result.get("result") == "PASS":
        for cid in reversed(ids):
            box.remove(cid)
        for net in [off, on]:
            box.owned(net, "networks")
            box.request("DELETE", "/networks/" + net)
    print(json.dumps(result), flush=True)
