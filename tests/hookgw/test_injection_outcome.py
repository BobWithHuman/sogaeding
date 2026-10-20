import copy
import json

import pytest

from app.benchmark.injection_outcome import confirmed_pre_actor_setup_failure, inspect_results


def test_original_file_collision_is_setup_failure_not_attack_block():
    row = {
        "success": True,
        "result": json.dumps(
            {
                "status": "error",
                "message": "File '/data/existing' already exists. Use inject_append to modify existing files.",
            }
        ),
    }
    outcome = inspect_results([{}], [row])
    assert outcome["domain_failure"] is True and outcome["verified"] is False
    assert outcome["kinds"] == ["OFFICIAL_INJECTION_FILE_ALREADY_EXISTS"]


@pytest.mark.parametrize(
    "row",
    [
        {"success": False, "error": "timeout"},
        {"success": True, "result": "not json"},
        None,
        {"success": True, "result": "{}"},
        {
            "success": True,
            "result": json.dumps(
                {"status": "error", "message": "Failed to inject file: request_error"}
            ),
        },
        {"success": True, "result": json.dumps({"status": "error", "message": "HTTP 503"})},
        {"success": True, "result": json.dumps({"status": "error", "message": "unknown failure"})},
    ],
)
def test_transport_or_unverified_result_stays_uncertain(row):
    outcome = inspect_results([{}], [row])
    assert outcome["verified"] is False and outcome["domain_failure"] is False


def base():
    return {
        "lifecycle_close_observed": True,
        "events": [{"kind": "benchmark_setup_failure", "verified_domain_failure": True}],
    }


@pytest.mark.parametrize(
    "event",
    [
        {"kind": "actor_response"},
        {"kind": "actor_incomplete", "code": "HTTPStatusError"},
        {"kind": "turn_finished"},
        {"stage": "POST", "state": "UNKNOWN"},
        {"stage": "PRE", "decision": "ALLOW"},
    ],
)
def test_actual_or_uncertain_actor_execution_cannot_be_lowered_to_setup_failure(event):
    result = base()
    assert confirmed_pre_actor_setup_failure(result)
    result["events"].append(event)
    assert not confirmed_pre_actor_setup_failure(result)


def test_close_loss_is_not_a_definite_setup_failure():
    result = base()
    result["lifecycle_close_observed"] = False
    assert not confirmed_pre_actor_setup_failure(result)
    result = base()
    result["execution_state"] = "UNKNOWN_EXECUTION"
    assert not confirmed_pre_actor_setup_failure(result)


def test_successful_original_injections_remain_successful():
    results = [{"success": True, "result": json.dumps({"status": "success"})}]
    before = copy.deepcopy(results)
    assert inspect_results([{}], results)["verified"] is True
    assert results == before
