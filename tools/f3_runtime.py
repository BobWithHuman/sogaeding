"""New role-separated F3 runtime; existing PKI, databases and B are untouched."""

import shutil
from pathlib import Path

from prepare_tls import generate

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/runtime-f3-01"
generate(target)
for role, names in {
    "control": [
        "ca.pem",
        "control.pem",
        "control.key",
        "human.token",
        "service.token",
        "storage.key",
    ],
    "gateway": [
        "ca.pem",
        "gateway.pem",
        "gateway.key",
        "gateway-client.pem",
        "gateway-client.key",
        "service.token",
    ],
}.items():
    (target / role).mkdir()
    for name in names:
        shutil.copyfile(target / name, target / role / name)
shutil.copyfile(target / "effects-storage.key", target / "gateway/storage.key")
(target / "driver").mkdir()
for name in ("ca.pem", "human.token", "service.token", "gateway-client.pem", "gateway-client.key"):
    shutil.copyfile(target / name, target / "driver" / name)
(target / "fixtures").mkdir()
shutil.copyfile(root / "fixtures/PUBLIC_README.txt", target / "fixtures/PUBLIC_README.txt")
(target / "fixtures/issues.json").write_text(
    '{"42":{"issue_id":42,"title":"배포 현황","body":"배포가 완료되었습니다."},"43":{"issue_id":43,"title":"별도 작업","body":"별도 이슈"}}',
    encoding="utf-8",
)
print("New F3 PKI/role mounts/fixture prepared. No credential output.")
