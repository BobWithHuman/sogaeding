"""Create new, role-separated browser fixture runtime; never replace old data."""
import json
import shutil
import sys
from pathlib import Path

from prepare_tls import generate

root = Path(__file__).resolve().parents[1]
target = root / "artifacts" / "runtime-browser-b"
generate(target)
for role, names in {
    "control": ["ca.pem", "control.pem", "control.key", "human.token", "service.token", "storage.key"],
    "gateway": ["ca.pem", "gateway.pem", "gateway.key", "gateway-client.pem", "gateway-client.key", "service.token"],
}.items():
    (target / role).mkdir()
    for name in names:
        shutil.copyfile(target / name, target / role / name)
shutil.copyfile(target / "effects-storage.key", target / "gateway/storage.key")
(target / "fixtures").mkdir()
for name in ("issues.json", "PUBLIC_README.txt"):
    shutil.copyfile(root / "fixtures" / name, target / "fixtures" / name)
fixture = json.loads((target / "fixtures/issues.json").read_text(encoding="utf-8"))
payload = '<img src="/xss-canary" onerror="window.__xss=1;fetch(\'/xss-probe\')"><script>window.__xss=2</script>'
fixture["43"]["title"] = payload
fixture["43"]["body"] = payload + " DEMO_SECRET_DO_NOT_SEND " + "긴 값 " * 1500
(target / "fixtures/issues.json").write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
print("Dedicated browser runtime and hostile local fixture prepared; no credential output.")
sys.exit(0)
