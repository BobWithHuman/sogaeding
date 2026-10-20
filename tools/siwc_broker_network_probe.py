"""No credential/provider API: exercise actual broker network ordering in Docker."""

import json

from app.benchmark.docker_sandbox import DockerSandbox

WORKER = "sha256:bd3607d2dae1d6c7e229ffecd9f056e501f23acd9221c7ec5a288856613a324d"
NAME = "with-human-siwc-network-validation-r3"
box = DockerSandbox(NAME)
containers = []
networks = [NAME + "-off", NAME + "-on"]
result = {"provider_api_calls": 0, "model_requests": 0, "credential_mounts": 0}
try:
    for net, subnet in zip(networks, ["10.233.159.0/24", "10.233.160.0/24"], strict=True):
        box.network(net, subnet)
    server = """
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
socket.getaddrinfo('api.openai.com',443) # DNS only, no API or authentication.
class Ready(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  socket.getaddrinfo('api.openai.com',443) # Egress/DNS still works after attach.
  self.send_response(200);self.end_headers();self.wfile.write(b'STARTUP_DNS_READY')
HTTPServer(('0.0.0.0',8500),Ready).serve_forever()
"""
    broker = box.create_broker(
        NAME + "-broker",
        WORKER,
        ["python", "-c", server],
        off_network=networks[0],
        on_network=networks[1],
        live=True,
    )
    containers.append(broker)
    result["broker_networks"] = sorted(box.owned(broker)["NetworkSettings"]["Networks"])
    arms = []
    for arm, net in zip(["off", "on"], networks, strict=True):
        client = box.create(NAME + "-" + arm, WORKER, ["sleep", "90"], network=net)
        containers.append(client)
        readiness = """
import time, urllib.request, urllib.error
for attempt in range(50):
 try:
  print(urllib.request.urlopen('http://broker:8500/ready',timeout=2).read().decode());break
 except urllib.error.URLError:
  if attempt == 49: raise
  time.sleep(.2)
"""
        code, text = box.exec(client, ["python", "-c", readiness])
        attached = sorted(box.owned(client)["NetworkSettings"]["Networks"])
        assert code == 0 and text.strip() == "STARTUP_DNS_READY", (code, text)
        assert attached == [net], attached
        arms.append({"arm": arm, "broker_response": text.strip(), "networks": attached})
    assert "bridge" in result["broker_networks"]
    result.update(result="PASS", arms=arms, public_dns_available_during_boot=True)
except Exception as error:
    result.update(result="FAIL", error_type=type(error).__name__)
    raise
finally:
    if result.get("result") == "PASS":
        for cid in reversed(containers):
            box.remove(cid)
        for net in networks:
            box.owned(net, "networks")
            box.request("DELETE", "/networks/" + net)
    print(json.dumps(result), flush=True)
