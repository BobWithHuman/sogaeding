import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/runtime-f3-01/fixtures/issues.json"
data = json.loads(target.read_text(encoding="utf-8"))
payload = '<img src="/xss-canary" onerror="window.__xss=1;fetch(\'/xss-probe\')"><script>window.__xss=2</script>'
data["43"] = {
    "issue_id": 43,
    "title": payload,
    "body": payload + " DEMO_SECRET_DO_NOT_SEND " + "긴 값 " * 1500,
}
target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
print("Own F3 issue43 XSS fixture prepared; no model request.")
