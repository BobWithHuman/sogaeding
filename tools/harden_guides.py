"""Read adopted original PDF pages; pin hash and retain text for this run."""
import hashlib
import json
import sys
from pathlib import Path

from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]
target = root / "artifacts" / sys.argv[1] / "guide-pages"
target.mkdir(parents=True, exist_ok=False)
pages = {"R1": [13, 14], "G1": [35, 47], "G2": [133, 135, 137, 143],
         "G3": [153, 164, 171, 510, 511], "G4": [24, 38], "C1": [14, 15, 26]}
summary = []
for entry in json.loads((root / "references/manifest.json").read_text(encoding="utf-8")):
    if entry["id"] not in pages:
        continue
    path = Path(entry["local_path"])
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == entry["sha256"]
    reader = PdfReader(path)
    for number in pages[entry["id"]]:
        text = reader.pages[number - 1].extract_text()
        (target / f"{entry['id']}-{number}.txt").write_text(text, encoding="utf-8")
    summary.append({"id": entry["id"], "sha256": sha, "pages": pages[entry["id"]]})
(target / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
