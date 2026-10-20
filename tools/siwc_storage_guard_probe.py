"""Physical negative permissions in tmpfs, never the real database."""

import json
import tempfile
from pathlib import Path

from app.benchmark.runtime_budget import StopRun
from app.benchmark.runtime_login import check_broker_storage

root = Path(tempfile.mkdtemp())
data = root / "broker-data"
data.mkdir()
data.chmod(0o2770)
db = data / "provider.sqlite3"
db.write_text("PUBLIC")
db.chmod(0o660)
check_broker_storage(root)
checked = []
for name, path, bad, good in [
    ("db_world_access", db, 0o666, 0o660),
    ("directory_world_access", data, 0o2777, 0o2770),
]:
    path.chmod(bad)
    try:
        check_broker_storage(root)
    except StopRun:
        checked.append(name)
    else:
        raise RuntimeError("INVALID_MODE_ACCEPTED")
    path.chmod(good)
db.unlink()
target = data / "public-target"
target.write_text("PUBLIC")
target.chmod(0o660)
db.symlink_to(target)
try:
    check_broker_storage(root)
except StopRun:
    checked.append("symlink")
else:
    raise RuntimeError("SYMLINK_ACCEPTED")
print(
    json.dumps(
        {
            "result": "PASS",
            "valid_role_binding": True,
            "rejected": checked,
            "provider_api_calls": 0,
            "model_requests": 0,
        }
    )
)
