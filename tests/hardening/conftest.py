import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("real_product", "/workspace/tests/acceptance/conftest.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(scope="session")
def fault_product(tmp_path_factory):
    root = tmp_path_factory.mktemp("fault-product")
    mode = root / "mode.json"
    mode.write_text("{}")
    product = module.Product(root, {"INTERNAL_PORT": "8445", "FAULT_MODE_PATH": str(mode)})
    peer = subprocess.Popen(["python", "/workspace/tests/hardening/peer.py"], env=product.env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    product.mode = lambda value: mode.write_text(json.dumps(value))
    for _ in range(80):
        if peer.poll() is not None:
            raise RuntimeError("fault peer failed")
        try:
            with httpx.Client(verify=product.service_trust, trust_env=False, timeout=0.2) as client:
                client.post("https://127.0.0.1:8443/internal/checks", json={},
                            headers={"Authorization": "Bearer " + product.service})
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        raise RuntimeError("fault peer readiness timeout")
    try:
        yield product
    finally:
        peer.terminate()
        try:
            peer.wait(timeout=5)
        except subprocess.TimeoutExpired:
            peer.kill()
            peer.wait(timeout=5)
        product.stop()
        if os.getenv("EVIDENCE_DIR"):
            target = Path(os.environ["EVIDENCE_DIR"])
            target.mkdir(parents=True, exist_ok=True)
            (target / "fault-traces.json").write_text(json.dumps(product.records, indent=2))
