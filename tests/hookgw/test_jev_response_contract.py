"""Official example compatibility, safe failure stages and independent usage."""
import copy
import json
import math
import sqlite3
from fractions import Fraction

import httpx
import pytest

from app.pdp.diagnostics import AnalysisFailure, detail, failure_details
from app.transparent.jev import (
    MODEL,
    JevClient,
    JevSettings,
    ResponseValidationError,
    validate_response,
)
from app.transparent.jev_policy import selected, typed_observations

QUESTIONS = {"department": {"type": "choice", "instructions": "Which team?",
                            "criteria": {"billing": "Payments", "technical": "Bugs", "sales": "Pricing"}}}
# https://docs.typesafe.ai/api, Choice example viewed2026-10-16. Not a live reply.
OFFICIAL = {"model": MODEL, "answers": {"department": {"type": "choice", "choice": "billing",
            "probabilities": {"billing": 0.88, "technical": 0.12, "sales": 0.0}, "confidence": 0.81}},
            "usage": {"input_tokens": 318, "output_tokens": 34}}


def test_official_example_keeps_provider_computed_effective_distinct_and_original_immutable():
    before = copy.deepcopy(OFFICIAL)
    answers, usage = validate_response(OFFICIAL, QUESTIONS)
    comparison = answers.confidence_comparisons[0]
    assert comparison["provider"] == 0.81
    assert math.isclose(comparison["computed"], 0.82)
    assert comparison["effective"] == 0.81 and selected(answers["department"]) is None
    assert OFFICIAL == before and usage == before["usage"]
    assert "computed" not in json.dumps(answers)  # transient audit, not output fields


@pytest.mark.parametrize("difference,valid", [(0.01249, True), (0.0126, False), (0.1, False)])
def test_display_bound_is_limited_not_a_threshold_change(difference, valid):
    value = copy.deepcopy(OFFICIAL)
    value["answers"]["department"]["confidence"] = 0.82 - difference
    if valid:
        answer, _ = validate_response(value, QUESTIONS)
        assert answer["department"]["confidence"] <= value["answers"]["department"]["confidence"]
    else:
        with pytest.raises(ResponseValidationError) as failure:
            validate_response(value, QUESTIONS)
        assert failure.value.metadata["response_stage"] == "CONFIDENCE"


def test_derived_value_below_threshold_never_rounds_up():
    value = copy.deepcopy(OFFICIAL)
    value["answers"]["department"]["probabilities"] = {"billing": 0.9333333333331, "technical": 0.0666666666669, "sales": 0.0}
    value["answers"]["department"]["confidence"] = 0.90
    answers, _ = validate_response(value, QUESTIONS)
    assert answers["department"]["confidence"] < 0.90
    assert selected(answers["department"]) is None


@pytest.mark.parametrize("probability,provider,accepted", [
    (.92, .90, True), (math.nextafter(.92, 0), .90, False),
    (math.nextafter(.92, 1), .90, True), (.919999999999, .90, False),
    (.92, math.nextafter(.90, 0), False), (.92, .89999, False),
])
def test_decimal_boundary_and_adjacent_inputs_survive_both_validation_layers(probability, provider, accepted):
    options = {"USER": probability, "TASK_DATA": 1 - probability, "GENERATED": 0., "ADDED_INSTRUCTION": 0., "UNCERTAIN": 0.}
    questions = {"basis_target": {"type": "choice", "instructions": "Slot basis", "criteria": dict.fromkeys(options)}}
    value = {"model": MODEL, "answers": {"basis_target": {"type": "choice", "choice": "USER", "probabilities": options, "confidence": provider}}, "usage": {"input_tokens": None, "output_tokens": None}}
    before = copy.deepcopy(value)
    answers, _ = validate_response(value, questions)
    row = typed_observations(answers, questions, {})[0]
    assert (selected(answers["basis_target"]) == "USER") is accepted
    assert (row["status"] == "ACCEPTED") is accepted
    assert row["effective_confidence"] <= provider
    assert value == before
    if probability == .92 and provider == .9:
        assert row["computed_confidence"] == .9


@pytest.mark.parametrize("choices", range(2, 17))
def test_exact_subthreshold_decimal_never_crosses_threshold_during_final_float_conversion(choices):
    boundary = float(Fraction(9, 10) + Fraction(1, 10 * choices))
    # Includes the independent-review nine-choice counterexample .9111111111111111.
    for probability in (math.nextafter(boundary, 0), boundary, math.nextafter(boundary, 1)):
        options = {f"e{i}": probability if i == 0 else 1 - probability if i == 1 else 0. for i in range(choices)}
        questions = {"basis": {"type": "choice", "instructions": "Observe basis", "criteria": dict.fromkeys(options)}}
        value = {"model": MODEL, "answers": {"basis": {"type": "choice", "choice": "e0", "probabilities": options, "confidence": .9}}, "usage": {"input_tokens": None, "output_tokens": None}}
        answers, _ = validate_response(value, questions)
        row = typed_observations(answers, questions, {})[0]
        exact = (choices * Fraction(str(probability)) - 1) / (choices - 1)
        assert (row["status"] == "ACCEPTED") is (exact >= Fraction(9, 10))
        assert Fraction(str(row["computed_confidence"])) <= exact


def test_display_rounded_total_is_normalized_never_raising_provider_confidence():
    # Live TypeSafe reply shape (2026-10-22): two-decimal values summing to .99.
    questions = {"behavior": {"type": "choice", "instructions": "Judge.", "criteria": {
        "EXTERNAL_ADOPTION": None, "LEGITIMATE": None, "OUTSIDE_TASK": None, "UNCERTAIN": None}}}
    value = {"model": MODEL, "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"behavior": {
        "type": "choice", "choice": "LEGITIMATE", "confidence": 0.91,
        "probabilities": {"EXTERNAL_ADOPTION": 0.02, "LEGITIMATE": 0.93, "OUTSIDE_TASK": 0.04, "UNCERTAIN": 0.0}}}}
    answers, _ = validate_response(value, questions)
    probabilities = answers["behavior"]["probabilities"]
    assert math.isclose(sum(probabilities.values()), 1, abs_tol=1e-9)
    # The smallest derivation wins: shown pmax .93 over 4 options gives .9067 < reported .91.
    assert answers["behavior"]["confidence"] == pytest.approx((4 * 0.93 - 1) / 3)
    assert answers.confidence_comparisons[0]["probabilities_normalized"] is True
    assert value["answers"]["behavior"]["probabilities"]["LEGITIMATE"] == 0.93  # original untouched


def test_rounded_total_confidence_from_shown_values_is_consistent_and_conservative():
    # Live reply (2026-10-22): .93/.05/.01 summing to .99, confidence .89 from the shown .93.
    questions = {"task_relation": {"type": "choice", "instructions": "Relate.", "criteria": {
        "OUTSIDE_TASK": None, "UNCERTAIN": None, "WITHIN_TASK": None}}}
    value = {"model": MODEL, "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"task_relation": {
        "type": "choice", "choice": "WITHIN_TASK", "confidence": 0.89,
        "probabilities": {"OUTSIDE_TASK": 0.05, "UNCERTAIN": 0.01, "WITHIN_TASK": 0.93}}}}
    answers, _ = validate_response(value, questions)
    assert answers["task_relation"]["confidence"] == 0.89
    assert answers.confidence_comparisons[0]["computed"] < 0.9


def test_rounding_never_moves_a_reply_across_the_risk_line():
    # Review P2: 1.01 total whose normalized risk confidence would fall below .90.
    questions = {"task_relation": {"type": "choice", "instructions": "Relate.", "criteria": {
        "OUTSIDE_TASK": None, "UNCERTAIN": None, "WITHIN_TASK": None}}}
    value = {"model": MODEL, "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"task_relation": {
        "type": "choice", "choice": "OUTSIDE_TASK", "confidence": 0.91,
        "probabilities": {"OUTSIDE_TASK": 0.94, "UNCERTAIN": 0.03, "WITHIN_TASK": 0.04}}}}
    with pytest.raises(ResponseValidationError) as error:
        validate_response(value, questions)
    assert error.value.metadata["response_issue"] == "THRESHOLD_AMBIGUOUS"


@pytest.mark.parametrize("probabilities", [
    {"billing": 0.86, "technical": 0.12, "sales": 0.0},          # .98: beyond 3 x .005
    {"billing": 0.875, "technical": 0.12, "sales": 0.0},         # .995 but not a display value
    {"billing": 0.89, "technical": 0.12, "sales": 0.01},         # 1.02
])
def test_other_totals_stay_invalid(probabilities):
    value = copy.deepcopy(OFFICIAL)
    value["answers"]["department"]["probabilities"] = probabilities
    with pytest.raises(ResponseValidationError) as error:
        validate_response(value, QUESTIONS)
    assert error.value.metadata["response_issue"] == "SUM"


@pytest.mark.parametrize("stage,issue,mutate", [
    ("ENVELOPE", "FIELDS", lambda v: v.update(PRIVATE_DYNAMIC_FIELD="secret")),
    ("MODEL", "MISMATCH", lambda v: v.update(model="PRIVATE_MODEL")),
    ("QUESTIONS", "COVERAGE", lambda v: v["answers"].update(PRIVATE_QUESTION={})),
    ("ANSWER", "FIELDS", lambda v: v["answers"]["department"].update(PRIVATE_FIELD=True)),
    ("OPTIONS", "COVERAGE", lambda v: v["answers"]["department"]["probabilities"].update(PRIVATE_OPTION=0)),
    ("PROBABILITY", "TYPE", lambda v: v["answers"]["department"]["probabilities"].update(billing=True)),
    ("PROBABILITY", "NONFINITE", lambda v: v["answers"]["department"]["probabilities"].update(billing=float("nan"))),
    ("PROBABILITY", "RANGE", lambda v: v["answers"]["department"]["probabilities"].update(billing=-0.1)),
    ("PROBABILITY", "SUM", lambda v: v["answers"]["department"]["probabilities"].update(billing=0.8)),
    ("PROBABILITY", "ARGMAX", lambda v: v["answers"]["department"].update(choice="technical")),
    ("CONFIDENCE", "TYPE", lambda v: v["answers"]["department"].update(confidence=True)),
    ("USAGE", "TYPE", lambda v: v["usage"].update(input_tokens=True)),
])
def test_response_stage_and_issue_never_export_dynamic_values(stage, issue, mutate):
    value = copy.deepcopy(OFFICIAL)
    mutate(value)
    with pytest.raises(ResponseValidationError) as error:
        validate_response(value, QUESTIONS)
    safe = error.value.metadata
    assert safe["response_stage"] == stage and safe["response_issue"] == issue
    assert "PRIVATE" not in json.dumps(safe) and "secret" not in str(error.value)


@pytest.fixture
def client(tmp_path):
    key = tmp_path / "jev.api-key"
    key.write_text("PUBLIC-fake-key-contract-testing", encoding="ascii")
    settings = JevSettings(enabled=True, key_path=key, budget_path=tmp_path / "typesafe-budget.sqlite3",
                           request_limit=4, input_token_limit=256000, policy_id="contract-fixture")
    return settings


@pytest.mark.asyncio
@pytest.mark.parametrize("change,expected_usage,usage_status", [
    ("answer", {"input_tokens": 318, "output_tokens": 34}, "VALID"),
    ("bad_usage", {"input_tokens": None, "output_tokens": 34}, "PARTIAL"),
    ("missing_usage", None, "UNKNOWN_MISSING"),
])
async def test_invalid_answer_or_usage_retains_only_independently_valid_counts(client, change, expected_usage, usage_status):
    value = copy.deepcopy(OFFICIAL)
    if change == "answer":
        value["answers"]["department"]["choice"] = "PRIVATE_BAD_CHOICE"
    elif change == "bad_usage":
        value["usage"]["input_tokens"] = "PRIVATE_BAD_COUNTER"
    else:
        value.pop("usage")
    adapter = JevClient(client, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
    with pytest.raises(AnalysisFailure) as failure:
        await adapter.observe("A", "public data", QUESTIONS, change)
    with sqlite3.connect(client.budget_path) as db:
        status, reserved, raw = db.execute("SELECT status,input_reserved,usage FROM jev_attempts").fetchone()
        diagnostic = db.execute("SELECT details FROM jev_diagnostics").fetchone()[0]
    assert status == "FAILED" and reserved == 64000
    assert (json.loads(raw) if raw else None) == expected_usage
    safe = failure_details(failure.value, enriched=True)[0]
    assert safe["usage_status"] == usage_status and safe["http_status"] == 200
    assert "PRIVATE" not in diagnostic + json.dumps(safe)


@pytest.mark.asyncio
@pytest.mark.parametrize("usage", [{"input_tokens": None, "output_tokens": None}, {"input_tokens": 318, "output_tokens": None}])
async def test_official_sdk_nullable_counters_are_unknown_not_zero(client, usage):
    value = copy.deepcopy(OFFICIAL)
    value["usage"] = usage
    adapter = JevClient(client, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
    await adapter.observe("A", "public data", QUESTIONS, "nullable")
    with sqlite3.connect(client.budget_path) as db:
        raw = db.execute("SELECT usage FROM jev_attempts").fetchone()[0]
    assert (json.loads(raw) if raw else None) == (usage if usage["input_tokens"] is not None else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("response,stage,issue", [
    (lambda: httpx.Response(200, headers={"content-type": "PRIVATE_HEADER"}, text="PRIVATE_BODY"), "CONTENT_TYPE", "MEDIA_TYPE"),
    (lambda: httpx.Response(200, headers={"content-type": "application/json"}, content=b"PRIVATE_JSON"), "JSON", "INVALID_JSON"),
    (lambda: httpx.Response(200, headers={"content-type": "application/json"}, content=b"x" * 65537), "RESPONSE_SIZE", "LIMIT"),
    (lambda: httpx.Response(401, json={"PRIVATE": "error"}), "HTTP", "STATUS"),
])
async def test_transport_stage_is_bounded_and_persisted_without_response_body(client, response, stage, issue):
    adapter = JevClient(client, transport=httpx.MockTransport(lambda _: response()))
    with pytest.raises(AnalysisFailure) as failure:
        await adapter.observe("A", "public data", QUESTIONS, stage)
    safe = failure_details(failure.value, enriched=True)[0]
    assert safe["response_stage"] == stage and safe["response_issue"] == issue
    assert "PRIVATE" not in json.dumps(safe)


def test_diagnostic_allowlist_rejects_unknown_values_and_non_enriched_stays_legacy():
    metadata = {"response_stage": "PRIVATE", "response_issue": "PRIVATE", "http_status": True,
                "content_type": "PRIVATE", "response_bytes": -1, "question_index": "PRIVATE", "model_match": "PRIVATE",
                "raw": "PRIVATE_BODY", "Authorization": "PRIVATE_KEY"}
    assert detail("JEV_RESPONSE_INVALID", "A", metadata) == {"code": "JEV_RESPONSE_INVALID", "view": "A"}
    failure = AnalysisFailure("JEV_RESPONSE_INVALID", "A", {"response_stage": "MODEL", "model_match": False})
    assert failure_details(failure) == [{"code": "JEV_RESPONSE_INVALID", "view": "A"}]
