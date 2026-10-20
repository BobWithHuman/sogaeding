import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
fixture = json.loads((root / "fixtures/f3/cases.json").read_text(encoding="utf-8"))
case = next(row for row in fixture["cases"] if row["id"] == sys.argv[1])
target = root / "artifacts/runtime-f3-01/fixtures/issues.json"
target.write_text(
    json.dumps(
        {
            "42": {"issue_id": 42, **case["issue"]},
            "43": {"issue_id": 43, "title": "별도작업", "body": "별도이슈"},
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
print(json.dumps({"fixture": sys.argv[1], "applied": True}))
