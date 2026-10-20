"""Final source/hash, independent cases, safe-output checks; never emit secrets."""
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

root = Path.cwd()
out = root / "artifacts/20261013-browser-b-review"
final = json.loads((root / "artifacts/20261013-browser-b/demo-normal-smoke-source/manifest.json").read_text())
initial = json.loads((root / "artifacts/20261013-browser-b/demo-launcher-smoke-source/manifest.json").read_text())
fingerprint = hashlib.sha256(json.dumps(final, sort_keys=True).encode()).hexdigest()
assert len(final) == 88 and fingerprint == "9553fd7be6fb9c60a88c853939216530abad0ababa59a393cac4fa7a9b7b5159"
mismatches = [entry["path"] for entry in final if hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]]
assert not mismatches
old = {entry["path"]: entry["sha256"] for entry in initial}
new = {entry["path"]: entry["sha256"] for entry in final}
changed = [name for name in old if old[name] != new[name]]
added = sorted(set(new) - set(old))
assert set(changed) == {"tools/browser_demo.mjs", "scripts/browser_demo.ps1"}
assert added == ["tools/browser_prepare_profile.mjs"]
for name in ("src/app/control/main.py", "src/app/web/ui.js", "tools/browser_helpers.mjs", "tools/browser_driver.py", "tools/browser_profile_ca.py", "tests/web/browser_acceptance.mjs", "requirements-dev.lock"):
    assert old[name] == new[name]
download = json.loads((root / "artifacts/browser-tools-b/download-manifest.json").read_text())
assert hashlib.sha256((root / "artifacts/browser-tools-b/firefox-1538/firefox/firefox.exe").read_bytes()).hexdigest() == download["executable_sha256"]
assert hashlib.sha256((root / "artifacts/browser-tools-b/firefox-1538.zip").read_bytes()).hexdigest() == download["archive_sha256"]
cases = []
for label in ("browser-r1", "browser-extra"):
    data = json.loads((out / label / "cases.json").read_text(encoding="utf-8"))
    assert all(case["result"] == "PASS" for case in data)
    cases.extend({"case_id": case["case_id"], "result": case["result"], "session_id": case["session_id"],
                  "executor_invocations": case["server"]["executor_invocations"], "actual_effects": case["server"]["actual_effects"]} for case in data)
commands = []
for file in sorted(out.glob("*-command.json")):
    value = json.loads(file.read_text(encoding="utf-8-sig"))
    assert all(key in value for key in ("started_at", "completed_at", "exit_code", "source_fingerprint", "safe_output_path"))
    commands.append({"label": file.stem, "started_at": value["started_at"], "completed_at": value["completed_at"], "exit_code": value["exit_code"], "source_fingerprint": value["source_fingerprint"]})
secrets = [file.read_text().strip() for file in (root / "artifacts/runtime-browser-b").rglob("*.token")]
secrets.extend(value for key, value in os.environ.items() if key in ("OPENAI_API_KEY", "HUMAN_USER_TOKEN", "GATEWAY_SERVICE_TOKEN") and value)
hits = []
checked = 0
for folder in (out, root / "docs/handoffs/WP-HARDEN-01/20261013-browser-b-review"):
    for file in folder.rglob("*"):
        if file.is_file() and file.suffix in (".json", ".txt", ".md", ".py", ".ps1", ".mjs", ".diff"):
            contents = file.read_text(encoding="utf-8", errors="replace")
            checked += 1
            if any(secret and secret in contents for secret in secrets):
                hits.append(file.relative_to(root).as_posix())
assert not hits
record = {"checked_at": datetime.now(UTC).isoformat(), "final_source_fingerprint": fingerprint, "files": 88, "mismatches": mismatches,
          "changes_from_initial_review": changed, "added": added, "product_core_unchanged": True,
          "browser_executable_sha256": download["executable_sha256"], "browser_archive_sha256": download["archive_sha256"],
          "known_credentials_text_files_checked": checked, "credential_hits": hits, "cases": cases, "commands": commands,
          "live_calls": 0, "official_independent_diagnosis": False}
(out / "final-verification.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps({"source_files": 88, "mismatches": 0, "independent_browser_cases": len(cases), "credential_hits": 0}))
