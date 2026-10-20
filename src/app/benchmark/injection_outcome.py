"""Separate confirmed official setup rejection from transport uncertainty."""

import json


def inspect_results(injections, results):
    if not isinstance(results, list) or len(results) != len(injections):
        return {
            "verified": False,
            "domain_failure": False,
            "kinds": ["INJECTION_RESULT_COUNT_MISMATCH"],
        }
    kinds = []
    completed = 0
    domain = True
    for row in results:
        if not isinstance(row, dict):
            kinds.append("INJECTION_RESULT_UNVERIFIED")
            domain = False
            continue
        if row.get("success") is not True:
            kinds.append("INJECTION_TRANSPORT_FAILED")
            domain = False
            continue
        try:
            data = json.loads(row.get("result"))
        except (TypeError, ValueError):
            kinds.append("INJECTION_RESULT_UNVERIFIED")
            domain = False
            continue
        if not isinstance(data, dict):
            kinds.append("INJECTION_RESULT_UNVERIFIED")
            domain = False
            continue
        if data.get("status") == "error" or data.get("success") is False:
            message = str(data.get("message", data.get("error", "")))
            kind = "INJECTION_RESULT_UNVERIFIED"
            if "already exists. Use inject_append" in message:
                kind = "OFFICIAL_INJECTION_FILE_ALREADY_EXISTS"
            elif "No such file or directory" in message:
                kind = "OFFICIAL_INJECTION_PARENT_MISSING"
            else:
                domain = False
            kinds.append(kind)
        elif data.get("status") == "success" or data.get("success") is True:
            completed += 1
        else:
            kinds.append("INJECTION_RESULT_UNVERIFIED")
            domain = False
    return {
        "verified": not kinds,
        "domain_failure": bool(kinds) and domain,
        "kinds": kinds,
        "completed_steps": completed,
        "expected_steps": len(injections),
    }


def confirmed_pre_actor_setup_failure(result):
    events = result.get("events", [])
    failures = [e for e in events if e.get("kind") == "benchmark_setup_failure"]
    return (
        bool(failures)
        and all(e.get("verified_domain_failure") is True for e in failures)
        and not any(
            e.get("kind")
            in (
                "actor_response",
                "observed_tool",
                "tool_result",
                "turn_finished",
                "actor_incomplete",
            )
            or e.get("stage") in ("PRE", "POST")
            for e in events
        )
        and result.get("lifecycle_close_observed") is True
        and not str(result.get("execution_state", "")).startswith("UNKNOWN")
    )
