"""Freeze public source/contracts and safe fixtures before each F3 command."""

import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "artifacts" / sys.argv[1] / (sys.argv[2] + "-source")
target.mkdir(parents=True, exist_ok=False)
paths = set()
for folder in ("src", "tests", "tools", "scripts", "docs/mvp", "fixtures", "agentgateway"):
    paths.update(
        p.relative_to(root).as_posix()
        for p in (root / folder).rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in (".py", ".ps1", ".html", ".js", ".mjs", ".json", ".md", ".txt", ".toml", ".yaml")
    )
paths.update(
    p.name
    for p in root.iterdir()
    if p.is_file()
    and (
        p.name.startswith(("Dockerfile", "compose", "requirements"))
        or p.name in ("README.md", ".dockerignore", "pyproject.toml")
    )
)
manifest = []
for name in sorted(paths):
    source, destination = root / name, target / "source" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    manifest.append({"path": name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
summary = {
    "captured_at": datetime.now(UTC).isoformat(),
    "files": len(manifest),
    "fingerprint": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
}
(target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(target / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
