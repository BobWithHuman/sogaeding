"""Stage B public-source snapshot, including tool/config inputs but no runtime."""
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "artifacts" / sys.argv[1] / (sys.argv[2] + "-source")
target.mkdir(parents=True, exist_ok=False)
previous = json.loads((root / "artifacts/20261013-harden-a/r1/manifest.json").read_text(encoding="utf-8"))
paths = {item["path"] for item in previous}
for folder in ("src", "tests", "tools", "scripts"):
    paths.update(p.relative_to(root).as_posix() for p in (root / folder).rglob("*")
                 if p.is_file() and p.suffix in (".py", ".ps1", ".html", ".js", ".mjs", ".json")
                 and "__pycache__" not in p.parts)
paths.update(p.name for p in root.iterdir() if p.is_file() and
             (p.name.startswith(("Dockerfile", "compose", "requirements")) or p.name == ".dockerignore"))
manifest = []
for name in sorted(paths):
    source = root / name
    destination = target / "source" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    manifest.append({"path": name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
current = {item["path"]: item["sha256"] for item in manifest}
summary = {"captured_at": datetime.now(UTC).isoformat(), "files": len(manifest),
           "fingerprint": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
           "a_manifest_mismatches": [item["path"] for item in previous if current[item["path"]] != item["sha256"]]}
(target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(target / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
