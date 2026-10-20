"""Original guide pages and narrow source diff, read-only inputs."""
import difflib
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

root = Path.cwd()
out = root / "artifacts/20261013-browser-b-review/scope"
out.mkdir(parents=True, exist_ok=False)
old = root / "artifacts/20261013-harden-a/r1"
manifest = json.loads((old / "manifest.json").read_text())
changed = [item["path"] for item in manifest if hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() != item["sha256"]]
assert changed == ["src/app/control/main.py", "src/app/web/ui.js"]
for name in changed:
    diff = difflib.unified_diff((old / "source" / name).read_text(encoding="utf-8").splitlines(keepends=True),
                                (root / name).read_text(encoding="utf-8").splitlines(keepends=True),
                                fromfile="A/" + name, tofile="B/" + name)
    (out / (Path(name).name + ".diff")).write_text("".join(diff), encoding="utf-8")
selection = {"R1": [13, 14], "G1": [35, 47], "G2": [28, 29, 30, 31, 123, 124, 125, 133, 135],
             "G3": [66, 67, 68, 69, 110, 111, 112, 164, 169, 171, 507, 509, 511],
             "G4": [24, 37, 38], "C1": [14, 15, 26]}
guides = []
for entry in json.loads((root / "references/manifest.json").read_text(encoding="utf-8")):
    if entry["id"] not in selection:
        continue
    file = Path(entry["local_path"])
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    assert sha == entry["sha256"]
    reader = PdfReader(file)
    for page in selection[entry["id"]]:
        (out / f"{entry['id']}-{page}.txt").write_text(reader.pages[page - 1].extract_text(), encoding="utf-8")
    guides.append({"id": entry["id"], "sha256": sha, "pages": selection[entry["id"]]})
record = {"checked_at": datetime.now(UTC).isoformat(), "a_manifest_changes": changed, "guides": guides,
          "requirements_dev_lock_sha256": hashlib.sha256((root / "requirements-dev.lock").read_bytes()).hexdigest()}
(out / "summary.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps({"a_source_changes": changed, "original_guides_verified": len(guides), "scope": "Stage B related pages, not full 20/49 review"}))
