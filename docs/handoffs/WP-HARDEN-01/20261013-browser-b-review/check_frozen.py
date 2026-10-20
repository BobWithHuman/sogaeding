"""Read-only frozen-source/tool checks for the separate AI review."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path.cwd()
out = root / "artifacts/20261013-browser-b-review"
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / "artifacts/20261013-browser-b/demo-launcher-smoke-source/manifest.json").read_text())
fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
mismatches = [item["path"] for item in manifest if hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() != item["sha256"]]
assert fingerprint == "c37acf3dcba04e83c912aff8ea7152179e05721cb2d438a61e257b8bc13e9ed9"
assert len(manifest) == 87 and not mismatches
download = json.loads((root / "artifacts/browser-tools-b/download-manifest.json").read_text())
exe_sha = hashlib.sha256((root / "artifacts/browser-tools-b/firefox-1538/firefox/firefox.exe").read_bytes()).hexdigest()
assert exe_sha == download["executable_sha256"]
record = {"checked_at": datetime.now(UTC).isoformat(), "files": len(manifest), "source_fingerprint": fingerprint,
          "mismatches": mismatches, "firefox_executable_sha256": exe_sha,
          "signature_status": download["signature_status"], "scope": "Source/executable bytes; no publisher authentication claim",
          "review_fixture_manifest": [{"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                     for p in sorted((root / "docs/handoffs/WP-HARDEN-01/20261013-browser-b-review").glob("*")) if p.is_file()]}
filename = "frozen-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json"
(out / filename).write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps({"files": 87, "mismatches": 0, "source_fingerprint": fingerprint, "evidence": filename}))
