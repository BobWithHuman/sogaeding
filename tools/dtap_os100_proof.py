"""Bind the pinned 100-task audit and earlier official no-model integration evidence."""

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/20261018-dtap-os100"
EVIDENCE = ROOT / "artifacts/20261018-dtap-os100/offline-final-06"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    audit_path = ARTIFACT / "audit/os100-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        audit["checked"] != 100
        or audit["failures"]
        or audit["injections"]
        != {
            "tool": 63,
            "environment": 33,
            "environment+tool": 4,
        }
    ):
        raise ValueError("OS100_ALL_CASES_AUDIT_NOT_PASSED")
    selection = ROOT / "artifacts/management-dtap-100-20261018/selection.json"
    if sha(selection) != "05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b":
        raise ValueError("PINNED_SELECTION_CHANGED")
    plan = json.loads((EVIDENCE / "plan.json").read_text(encoding="utf-8"))
    if plan["manifest"]["mode"] != "OFFLINE" or plan["manifest"]["runtime_ready"] != 3:
        raise ValueError("OFFICIAL_OFFLINE_INTEGRATION_NOT_PROVEN")
    with sqlite3.connect(EVIDENCE / "broker-data/provider.sqlite3") as db:
        states = db.execute(
            "SELECT arm,state,count(*) FROM jobs GROUP BY arm,state ORDER BY arm,state"
        ).fetchall()
    if states != [("engine-off", "COMPLETED", 3), ("engine-on", "COMPLETED", 3)]:
        raise ValueError("OFFICIAL_OFFLINE_LEDGER_NOT_COMPLETED")
    snapshots = {}
    for arm in ("engine-off", "engine-on"):
        for key in plan["manifest"]["task_keys"]:
            result_path = (
                EVIDENCE
                / "arms"
                / arm
                / hashlib.sha256(key.encode("utf-8")).hexdigest()
                / "result.json"
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if (
                not result.get("actor_initialized")
                or not result.get("actor_completed")
                or result.get("judge", {}).get("error")
            ):
                raise ValueError("OFFICIAL_OFFLINE_CASE_INCOMPLETE:" + arm + ":" + key)
            snapshots.setdefault(key, []).append(result["initial_snapshot"]["image"])
            if not any(e.get("stage") == "POST" for e in result["events"]):
                raise ValueError("ACTUAL_GATEWAY_POST_ABSENT:" + arm + ":" + key)
            if key.endswith("consent-violations/1") and arm == "engine-on":
                if not any(
                    e.get("stage") == "PRE" and e.get("decision") == "DENY"
                    for e in result["events"]
                ):
                    raise ValueError("ACTUAL_GATEWAY_SEMANTIC_DENY_ABSENT")
            if key.endswith("consent-violations/12"):
                injection = result_path.parent / "data/environment-injection-results.json"
                if not injection.is_file() or not all(
                    item.get("success") is True
                    for item in json.loads(injection.read_text(encoding="utf-8"))
                ):
                    raise ValueError("OFFICIAL_ENVIRONMENT_INJECTION_NOT_OBSERVED")
    if any(len(pair) != 2 or pair[0] != pair[1] for pair in snapshots.values()):
        raise ValueError("PAIRED_INITIAL_IMAGES_NOT_IDENTICAL")
    paths = [ROOT / "src/app/common.py"]
    paths += sorted((ROOT / "src/app/benchmark").glob("*.py"))
    paths += sorted((ROOT / "src/app/transparent").glob("*.py"))
    paths += [
        ROOT / "tools" / name
        for name in (
            "dtap_runtime.py",
            "dtap_runtime_task.py",
            "dtap_runtime_injection.py",
            "dtap_os100_audit.py",
            "dtap_os100_proof.py",
            "prepare_tls.py",
        )
    ]
    paths += [ROOT / "scripts/dtap_eval.ps1", ROOT / "scripts/dtap_official_runtime.ps1"]
    paths += sorted((ROOT / "agentgateway").rglob("*.*"))
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_file()}
    proof = {
        "profile": "PINNED_OS_FILESYSTEM_INDIRECT_100",
        "selection_sha256": sha(selection),
        "audit_sha256": sha(audit_path),
        "official_offline_cases": sorted(snapshots),
        "official_offline_pairs_with_identical_initial_image": len(snapshots),
        "servers": {
            "OS-filesystem": {
                "actual_schema_verified": True,
                "complete_slots": True,
                "gateway_integration_verified": True,
            }
        },
        "environments": {
            "os-filesystem": {
                "image_digest": "sha256:7dc11a71388793b859cf7332f0d474784164d5e15bae751b28dab85a92b10732",
                "paired_snapshot_verified": True,
            }
        },
        "injections": ["tool", "environment"],
        "judge_domains": ["os-filesystem"],
        "verified_runtime_files": files,
        "claim_limit": "All 100 official configurations parsed and bound; three distinct official paths exercised with fake providers. Actual model outcomes NOT_RUN.",
    }
    output = ARTIFACT / "verified-capabilities.json"
    output.write_text(
        json.dumps(proof, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "files": len(files),
                "audit_cases": audit["checked"],
                "offline_pairs": len(snapshots),
                "proof_sha256": sha(output),
            }
        )
    )


if __name__ == "__main__":
    main()



