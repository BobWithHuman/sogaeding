"""Separate local profile; reuse enrolled machine identity without global changes."""
import hashlib
import json
import os
import shutil
from pathlib import Path


def prepare(root):
    runtime = root.resolve() / "artifacts/runtime-hookgw"
    source, target = runtime / "host", runtime / "host-jev"
    profile = {"workspace": str(root.resolve()), "control_url": "https://127.0.0.1:8032", "gateway_url": "https://127.0.0.1:8042/mcp"}
    names = ("ca.pem", "machine.id", "machine.token", "human.token")
    if target.is_symlink() or any(not (source / n).is_file() or (source / n).is_symlink() for n in names):
        raise SystemExit("Trusted enrolled host credentials required")
    if target.exists():
        if {p.name for p in target.iterdir()} != {*names, "profile.json"} or json.loads((target / "profile.json").read_text(encoding="utf-8")) != profile or any(hashlib.sha256((target/n).read_bytes()).digest() != hashlib.sha256((source/n).read_bytes()).digest() for n in names):
            raise SystemExit("Existing Jev profile differs; preserved without replacement")
    else:
        target.mkdir(mode=0o700)
        for name in names:
            shutil.copyfile(source / name, target / name)
            os.chmod(target / name, 0o600)
        (target / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
        os.chmod(target / "profile.json", 0o600)
    print(json.dumps({"profile": "host-jev", "paid_requests": 0, "existing_profile_changed": False, "new_keys_created": 0, "endpoints": [profile["control_url"], profile["gateway_url"]]}))


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parents[1])
