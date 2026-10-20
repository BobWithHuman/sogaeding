"""Allowlisted failure details; never persist model text or exception messages."""

from app.common import SafeError

CODES = {
    "INVALID_SCHEMA", "UNKNOWN_SOURCE", "A_EXTERNAL_SOURCE", "QUOTE_BOUNDS",
    "QUOTE_MISMATCH", "SENSITIVE_QUOTE", "A_EXTERNAL_USE", "B_EXTERNAL_EVIDENCE_REQUIRED",
    "B_SAME_ISSUE_REQUIRED", "EVIDENCE_REQUIRED", "RESULT_PAIR_INVALID", "INVALID_JSON",
    "API_TIMEOUT", "PAIR_DEADLINE", "API_AUTHENTICATION", "API_RATE_LIMIT",
    "API_CONNECTION", "API_ERROR", "MODEL_REFUSAL", "RESPONSE_INCOMPLETE",
    "UNEXPECTED_OUTPUT", "MISSING_API_KEY", "REQUEST_BUDGET_EXHAUSTED",
    "ADAPTER_ERROR", "ANALYSIS_CANCELLED", "LEASE_EXPIRED", "SNAPSHOT_STALE",
    "JUDGE_NOT_CONFIGURED", "DETAIL_NOT_RECORDED", "INPUT_CONTEXT_LIMIT",
    "UNKNOWN_SPAN", "SPAN_VIEW_MISMATCH", "CATALOG_INCOMPLETE", "CATALOG_SOURCE_COLLISION",
    "SOURCE_HASH_MISMATCH", "VIEW_NOT_AVAILABLE", "TURN_ANALYSIS_STOPPED",
    "JEV_NOT_AUTHORIZED", "JEV_SETTINGS_INVALID", "JEV_INPUT_INVALID", "JEV_RESPONSE_INVALID",
    "JEV_CONTEXT_LIMIT", "JEV_USAGE_LIMIT", "JEV_BUDGET_BINDING", "JEV_SENSITIVE_INPUT",
    "JEV_RESPONSE_VALID",
    "RESOURCE_METADATA_UNAVAILABLE", "RESOURCE_METADATA_REQUIRED", "RESOURCE_METADATA_LIMIT",
    "RESOURCE_METADATA_BINDING_INVALID", "RECURSIVE_METADATA_INCOMPLETE",
    "RECURSIVE_METADATA_BINDING_INVALID", "RECURSIVE_METADATA_LIMIT",
}
VIEWS = {"A", "B", "PAIR", "SERVER"}
RESPONSE_STAGES = {"HTTP", "CONTENT_TYPE", "RESPONSE_SIZE", "JSON", "ENVELOPE", "MODEL", "QUESTIONS", "ANSWER", "OPTIONS", "PROBABILITY", "CONFIDENCE", "USAGE", "COMPLETE", "UNKNOWN"}
RESPONSE_ISSUES = {"STATUS", "MEDIA_TYPE", "LIMIT", "INVALID_JSON", "TYPE", "FIELDS", "MISMATCH", "COVERAGE", "NUMERIC", "NONFINITE", "RANGE", "SUM", "ARGMAX", "CONSISTENCY", "NONE", "UNKNOWN"}


def detail(code, view="SERVER", metadata=None):
    value = {"code": code if code in CODES else "ADAPTER_ERROR",
             "view": view if view in VIEWS else "SERVER"}
    # Diagnostics contain shape/hash only, never source IDs, quote or model text.
    for key, item in (metadata or {}).items():
        if key == "ref_kind" and item in ("USER_REQUEST", "CANDIDATE", "EXTERNAL_SOURCE", "SPAN_ID"):
            value[key] = item
        elif key in ("ref_index", "start", "end", "text_length", "quote_length") and type(item) is int and 0 <= item <= 2147483647:
            value[key] = item
        elif key in ("text_sha256", "quote_sha256", "id_sha256") and isinstance(item, str) and len(item) == 64 and all(c in "0123456789abcdef" for c in item):
            value[key] = item
        elif key == "exact_match" and type(item) is bool:
            value[key] = item
        elif key == "response_stage" and isinstance(item, str) and item in RESPONSE_STAGES:
            value[key] = item
        elif key == "response_issue" and isinstance(item, str) and item in RESPONSE_ISSUES:
            value[key] = item
        elif key == "http_status" and type(item) is int and 100 <= item <= 599:
            value[key] = item
        elif key == "content_type" and isinstance(item, str) and item in {"JSON", "NON_JSON", "MISSING", "UNKNOWN"}:
            value[key] = item
        elif key in {"response_bytes", "missing_fields", "extra_fields", "question_index", "missing_questions", "extra_questions", "missing_options", "extra_options"} and type(item) is int and 0 <= item <= 131072:
            value[key] = item
        elif key in {"json_valid", "model_match", "usage_complete", "confidence_adjusted", "confidence_difference_observed"} and type(item) is bool:
            value[key] = item
        elif key == "usage_status" and isinstance(item, str) and item in {"VALID", "PARTIAL", "UNKNOWN_MISSING", "UNKNOWN_INVALID"}:
            value[key] = item
        elif key == "confidence_basis" and item == "MIN_PROVIDER_COMPUTED":
            value[key] = item
        elif key == "response_contract" and item == "jev-response-2":
            value[key] = item
        elif key == "usage_field" and isinstance(item, str) and item in {"INPUT_TOKENS", "OUTPUT_TOKENS"}:
            value[key] = item
        elif key in {"http_status", "json_valid", "model_match", "response_bytes"} and item == "UNKNOWN":
            value[key] = item
    return value


class AnalysisFailure(SafeError):
    def __init__(self, code, view="SERVER", metadata=None):
        self.diagnostics = [detail(code, view, metadata)]
        super().__init__("ANALYSIS_UNAVAILABLE", 503)


def failure_details(error, enriched=False):
    if isinstance(error, AnalysisFailure):
        return [detail(row["code"], row["view"], row if enriched else None) for row in error.diagnostics[:2]]
    if isinstance(error, TimeoutError):
        return [detail("PAIR_DEADLINE", "PAIR")]
    return [detail("ADAPTER_ERROR")]
