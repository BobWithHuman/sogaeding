"""Public pinned upstream lockfile inventory only; never reads project packages/secrets."""
import hashlib
import json
import tomllib
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / "artifacts/20261016-hook-gw-dev"
    raw = (directory / "agentgateway-Cargo.lock").read_bytes()
    expected = "38fb7a6c71b8d71768cbb947184ddfb140e66278f9fa3780f1038f68869d1386"
    if hashlib.sha256(raw).hexdigest() != expected:
        raise SystemExit("Public pinned upstream lockfile digest mismatch")
    target = directory / "agentgateway-osv.json"
    if target.exists():
        raise SystemExit("Preserve existing evidence")
    packages = [x for x in tomllib.loads(raw.decode())["package"] if x.get("source", "").startswith("registry+")]
    results = []
    for start in range(0, len(packages), 500):
        batch = packages[start:start + 500]
        queries = [{"package": {"name": x["name"], "ecosystem": "crates.io"}, "version": x["version"]} for x in batch]
        request = urllib.request.Request("https://api.osv.dev/v1/querybatch", json.dumps({"queries": queries}).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read(4 * 1024 * 1024))
        if len(data["results"]) != len(batch) or any(x.get("next_page_token") for x in data["results"]):
            raise SystemExit("Incomplete/paginated response requires follow-up; not a clean result")
        results.extend({"name": x["name"], "version": x["version"], **r} for x, r in zip(batch, data["results"], strict=True))
    output = {"utc": datetime.now(UTC).isoformat(), "source_sha256": expected, "packages_queried": len(results),
              "scope": "Upstream source lockfile; feature/target/build reachability NOT_PROVEN; not a binary VEX or OS CVE scan", "results": results}
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    vulnerable = [x for x in results if x.get("vulns")]
    print(json.dumps({"packages_queried": len(results), "matched_packages": len(vulnerable), "matches": vulnerable}))


if __name__ == "__main__":
    main()
