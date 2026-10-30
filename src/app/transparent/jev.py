"""Pinned, opt-in TypeSafe transport. Model outputs never grant authority.

Official wire reference: https://docs.typesafe.ai/api and /confidence.
No SDK, retries, fallback, environment proxy, debug body, or model calls at import.
The separate provider ledger always records attempts and actual usage. Explicit
unlimited mode imposes no request/token quota or token reservation. Historical
bounded configurations retain their original reservations and binding.
"""

import asyncio
import math
import re
import secrets
from app.private_files import private_connect, read_private
import sqlite3
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import httpx

from app.common import SafeError, canonical, mask, strict_json
from app.pdp.diagnostics import AnalysisFailure, detail, failure_details
from app.transparent.privacy import PrivacyError, TransmissionMasker, contains_pii

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
MAX_REQUEST_BYTES = 24576
MAX_RESPONSE_BYTES = 65536
RESERVED_INPUT_TOKENS = 64000
QUESTION_ID = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
OPTION_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
POLICY_ID = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")
RESPONSE_CONTRACT = "jev-response-3"
# Product compatibility assumption, not a provider precision guarantee. Two
# displayed decimal places allow +/- .005 in pmax, in reported confidence and,
# per option, in the probability total (live replies summed to .99).
DISPLAY_HALF_UNIT = 0.005
# candidate_policy.RISK_THRESHOLD; repeated to keep this transport free of policy imports.
RISK_SELECTION = 0.90


class ResponseValidationError(ValueError):
    def __init__(self, stage, issue, **metadata):
        self.metadata = detail("JEV_RESPONSE_INVALID", metadata={"response_stage": stage, "response_issue": issue, **metadata})
        super().__init__("JEV_RESPONSE_INVALID")


class ValidatedAnswers(dict):
    """Policy sees conservative confidence. Raw numeric comparison is transient.

    Attributes are not JSON dictionary fields and are never logged or persisted.
    No dynamic question/option names or actual numeric distributions in diagnostics.
    """
    def __init__(self, values, comparisons):
        super().__init__(values)
        self.confidence_comparisons = comparisons


def usage_observation(value):
    """Independently bounded counters survive invalid answers; unknown is not zero."""
    raw = value.get("usage") if isinstance(value, dict) else None
    if raw is None:
        return None, "UNKNOWN_MISSING"
    if not isinstance(raw, dict):
        return None, "UNKNOWN_INVALID"
    known = {}
    for field in ("input_tokens", "output_tokens"):
        number = raw.get(field)
        known[field] = number if type(number) is int and number >= 0 else None
    count = sum(v is not None for v in known.values())
    return (known if count else None), "VALID" if count == 2 else "PARTIAL" if count else "UNKNOWN_MISSING" if all(raw.get(k) is None for k in known) else "UNKNOWN_INVALID"


@dataclass(frozen=True)
class JevSettings:
    enabled: bool = False
    model: str = MODEL
    key_path: str | Path | None = None
    budget_path: str | Path | None = None
    request_limit: int | None = None
    input_token_limit: int | None = None
    policy_id: str | None = None
    data_policy: str = "masked_minimal_v1"
    unlimited: bool = False

    def authorized(self):
        if not isinstance(self.key_path, (str, Path)) or not isinstance(self.budget_path, (str, Path)):
            return False
        limits_valid = (self.unlimited is True and self.request_limit is None and self.input_token_limit is None
                        or self.unlimited is False and type(self.request_limit) is int
                        and 1 <= self.request_limit <= 1000 and type(self.input_token_limit) is int
                        and RESERVED_INPUT_TOKENS <= self.input_token_limit <= 64000000)
        return bool(
            self.enabled is True and self.model == MODEL and self.data_policy in ("nonpersonal_only", "masked_minimal_v1")
            and self.key_path is not None and Path(self.key_path).name == "jev.api-key"
            and self.budget_path is not None
            and Path(self.budget_path).name == "typesafe-budget.sqlite3"
            and limits_valid
            and isinstance(self.policy_id, str) and POLICY_ID.fullmatch(self.policy_id)
        )


def _probability(value):
    return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)


def _display_value(value):
    """A finite probability shown with at most two decimals (e.g. .93, .0)."""
    return type(value) in (int, float) and math.isfinite(value) and (Fraction(str(value)) * 100).denominator == 1


def _numeric_issue(value, *, integer=False, maximum=1):
    if type(value) not in ((int,) if integer else (int, float)):
        return "TYPE"
    if type(value) is float and not math.isfinite(value):
        return "NONFINITE"
    if not 0 <= value <= maximum:
        return "RANGE"
    return None


def _sensitive_value(value):
    if contains_pii(value):
        return True
    return credential_value(value)


def credential_value(value):
    if isinstance(value, str):
        return mask(value) != value or bool(re.search(
            r'''(?i)(?:api[_-]?key|password|secret|token)["']?\s*[:=]\s*["']?[^\s,;]+''', value))
    if isinstance(value, dict):
        return any(credential_value(str(key) + "=" + canonical(item)) or credential_value(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(credential_value(item) for item in value)
    return False


def validate_questions(questions):
    """Question content is server-owned; callers must not put source text here."""
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 24:
        raise ValueError()
    for key, item in questions.items():
        if not isinstance(key, str) or not QUESTION_ID.fullmatch(key) or not isinstance(item, dict):
            raise ValueError()
        kind = item.get("type")
        if kind == "choice":
            if set(item) != {"type", "instructions", "criteria"}:
                raise ValueError()
            criteria = item["criteria"]
            if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 16:
                raise ValueError()
            if any(not isinstance(k, str) or not OPTION_ID.fullmatch(k)
                   or (v is not None and (not isinstance(v, str) or len(v) > 2048))
                   for k, v in criteria.items()):
                raise ValueError()
        elif kind == "noul":
            if set(item) != {"type", "instructions"}:
                raise ValueError()
        else:
            raise ValueError()
        if not isinstance(item["instructions"], str) or not 1 <= len(item["instructions"]) <= 4096:
            raise ValueError()


def computed_confidence(probability, choices):
    """Normalize the supplied decimal number exactly, without threshold tolerance.

    Binary subtraction/division made .92 across five choices fall below .90.
    Fraction uses the received number's decimal representation; a genuinely
    smaller probability or provider confidence is never rounded to a threshold.
    This helper is called only after finite numeric/option validation.
    """
    exact = max(Fraction(0), min(Fraction(1), (choices * Fraction(str(probability)) - 1) / (choices - 1)))
    result = float(exact)
    # A rational just below .90 can itself round to float .90 (e.g. nine
    # choices). Compare decimal representations, as used for received numbers,
    # and take the adjacent lower float only when conversion overstates it.
    return math.nextafter(result, 0.0) if Fraction(str(result)) > exact else result


def validate_response(value, questions):
    """Strict security shape plus bounded display compatibility; never raises trust."""
    validate_questions(questions)
    def fields(item, expected, stage, **meta):
        if not isinstance(item, dict):
            raise ResponseValidationError(stage, "TYPE", **meta)
        if set(item) != expected:
            raise ResponseValidationError(stage, "FIELDS", missing_fields=len(expected - set(item)), extra_fields=len(set(item) - expected), **meta)
    fields(value, {"model", "answers", "usage"}, "ENVELOPE")
    if value["model"] != MODEL:
        raise ResponseValidationError("MODEL", "MISMATCH", model_match=False)
    answers, raw_usage = value["answers"], value["usage"]
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ResponseValidationError("QUESTIONS", "COVERAGE", missing_questions=len(set(questions) - set(answers)) if isinstance(answers, dict) else len(questions), extra_questions=len(set(answers) - set(questions)) if isinstance(answers, dict) else 0)
    fields(raw_usage, {"input_tokens", "output_tokens"}, "USAGE")
    for field in ("input_tokens", "output_tokens"):
        # Public SDK permits unreported/null counters. They remain UNKNOWN and
        # never release a reservation. Bad types/ranges still fail closed.
        number = raw_usage[field]
        if number is not None and (type(number) is not int or number < 0):
            raise ResponseValidationError("USAGE", "TYPE" if type(number) is not int else "RANGE", usage_field=field.upper())
    usage, _ = usage_observation(value)
    validated, comparisons = {}, []
    for index, (key, question) in enumerate(questions.items()):
        answer = answers[key]
        if not isinstance(answer, dict) or answer.get("type") != question["type"]:
            raise ResponseValidationError("ANSWER", "TYPE", question_index=index)
        if question["type"] == "noul":
            fields(answer, {"type", "noul"}, "ANSWER", question_index=index)
            if issue := _numeric_issue(answer["noul"]):
                raise ResponseValidationError("PROBABILITY", issue, question_index=index)
            validated[key] = dict(answer)
            continue
        fields(answer, {"type", "choice", "probabilities", "confidence"}, "ANSWER", question_index=index)
        probs = answer["probabilities"]
        if not isinstance(probs, dict) or set(probs) != set(question["criteria"]):
            raise ResponseValidationError("OPTIONS", "COVERAGE", question_index=index, missing_options=len(set(question["criteria"]) - set(probs)) if isinstance(probs, dict) else len(question["criteria"]), extra_options=len(set(probs) - set(question["criteria"])) if isinstance(probs, dict) else 0)
        if issue := next((problem for v in probs.values() if (problem := _numeric_issue(v))), None):
            raise ResponseValidationError("PROBABILITY", issue, question_index=index)
        total = sum(probs.values())
        shown = dict(probs)
        normalized = False
        if not math.isclose(total, 1, rel_tol=0, abs_tol=1e-6):
            # Only two-decimal display values within their rounding drift are accepted;
            # they are normalized exactly before any confidence is derived.
            if not (all(_display_value(v) for v in probs.values())
                    and abs(total - 1) <= DISPLAY_HALF_UNIT * len(probs) + 1e-9):
                raise ResponseValidationError("PROBABILITY", "SUM", question_index=index)
            probs = {option: float(Fraction(str(v)) / Fraction(str(total))) for option, v in probs.items()}
            normalized = True
        selected = answer["choice"]
        if not isinstance(selected, str) or selected not in probs or probs[selected] != max(probs.values()):
            raise ResponseValidationError("PROBABILITY", "ARGMAX", question_index=index)
        n = len(probs)
        # A rounded total may have been derived from the shown or the normalized pmax;
        # either must agree, and the smallest derivation is the one ever used.
        derived = [computed_confidence(max(probs.values()), n)]
        if normalized:
            derived.append(computed_confidence(max(shown.values()), n))
        expected = min(derived)
        reported = answer["confidence"]
        if issue := _numeric_issue(reported):
            raise ResponseValidationError("CONFIDENCE", issue, question_index=index)
        bound = DISPLAY_HALF_UNIT * n / (n - 1) + DISPLAY_HALF_UNIT + 1e-6
        if all(abs(reported - value) > bound for value in derived):
            raise ResponseValidationError("CONFIDENCE", "CONSISTENCY", question_index=index)
        if normalized and min(derived + [reported]) < RISK_SELECTION <= max(reported, derived[-1]):
            # Normalization must not pull a reply the provider showed at >= .90 below the
            # risk-selection line; such a reply stays invalid (fail closed) as before.
            raise ResponseValidationError("CONFIDENCE", "THRESHOLD_AMBIGUOUS", question_index=index)
        effective = min(reported, expected)
        validated[key] = {**answer, "probabilities": dict(probs), "confidence": effective}
        comparisons.append({"question": key, "question_index": index, "provider": reported, "computed": expected,
                            "effective": effective, "probabilities_normalized": normalized})
    return ValidatedAnswers(validated, comparisons), usage


class JevClient:
    """Raw observations only. The caller owns routing, state isolation and policy."""

    def __init__(self, settings=None, *, transport=None):
        self.settings = settings if settings is not None else JevSettings()
        # MockTransport is the only injectable transport; cannot replace TLS in LIVE.
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError("Only an explicit offline MockTransport may be injected")
        self._transport = transport
        self._masker = TransmissionMasker(secrets.token_bytes(32))

    def _read_key(self, view):
        try:
            path = Path(self.settings.key_path)
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
                raise OSError()
            key = read_private(path, 4096).decode("ascii").strip()
            if not 16 <= len(key) <= 2048 or any(c.isspace() for c in key):
                raise OSError()
            return key
        except (OSError, TypeError, UnicodeError):
            raise AnalysisFailure("MISSING_API_KEY", view) from None

    def preflight(self):
        """Validate local credentials without network or budget reservation."""
        if not self.settings.authorized():
            raise AnalysisFailure("JEV_NOT_AUTHORIZED")
        self._read_key("SERVER")

    def _claim(self, analysis_id, view):
        settings = self.settings
        path = Path(settings.budget_path)
        binding = canonical({"provider": "typesafe", "model": MODEL, "policy_id": settings.policy_id,
                             "request_limit": settings.request_limit,
                             "input_token_limit": settings.input_token_limit,
                             **({"unlimited":True} if settings.unlimited else {})})
        with private_connect(path, timeout=1) as db:
            db.execute("BEGIN IMMEDIATE")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables - {"jev_policy", "jev_attempts", "jev_diagnostics"}:
                raise AnalysisFailure("JEV_BUDGET_BINDING", view)
            db.execute("CREATE TABLE IF NOT EXISTS jev_policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), binding TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS jev_attempts (analysis_id TEXT, view TEXT, started REAL, status TEXT, input_reserved INTEGER, usage TEXT, PRIMARY KEY(analysis_id,view))")
            previous = db.execute("SELECT binding FROM jev_policy WHERE singleton=1").fetchone()
            if previous and previous[0] != binding:
                raise AnalysisFailure("JEV_BUDGET_BINDING", view)
            if not previous:
                db.execute("INSERT INTO jev_policy VALUES (1,?)", (binding,))
            count, tokens = db.execute("SELECT count(*),coalesce(sum(input_reserved),0) FROM jev_attempts").fetchone()
            if not settings.unlimited and (count >= settings.request_limit or tokens + RESERVED_INPUT_TOKENS > settings.input_token_limit):
                raise AnalysisFailure("REQUEST_BUDGET_EXHAUSTED", view)
            try:
                db.execute("INSERT INTO jev_attempts VALUES (?,?,?,'STARTED',?,NULL)",
                           (analysis_id, view, time.time(), 0 if settings.unlimited else RESERVED_INPUT_TOKENS))
            except sqlite3.IntegrityError:
                raise AnalysisFailure("REQUEST_BUDGET_EXHAUSTED", view) from None

    def _record(self, analysis_id, view, status, usage, metadata):
        with private_connect(self.settings.budget_path, timeout=1) as db:
            db.execute("UPDATE jev_attempts SET status=?,usage=? WHERE analysis_id=? AND view=?",
                       (status, canonical(usage) if usage else None, analysis_id, view))
            # Optional new diagnostics never rewrite legacy attempts during reads.
            db.execute("CREATE TABLE IF NOT EXISTS jev_diagnostics (analysis_id TEXT,view TEXT,details TEXT,PRIMARY KEY(analysis_id,view))")
            db.execute("INSERT OR REPLACE INTO jev_diagnostics VALUES(?,?,?)", (analysis_id, view, canonical(detail(metadata.get("code", "ADAPTER_ERROR"), view, metadata))))

    async def observe(self, view, state, questions, analysis_id):
        if not isinstance(self.settings, JevSettings) or not self.settings.authorized():
            raise AnalysisFailure("JEV_NOT_AUTHORIZED", view)
        if view not in ("A", "B") or not isinstance(analysis_id, str) or not 1 <= len(analysis_id) <= 128:
            raise AnalysisFailure("JEV_INPUT_INVALID", view)
        try:
            validate_questions(questions)
            if not isinstance(state, (dict, list, str)):
                raise ValueError()
            body = canonical({"model": MODEL, "state": state, "questions": questions}).encode("utf-8")
            # Also enforces depth16/duplicate-safe/finite JSON before any reservation.
            frozen = strict_json(body)
            questions = frozen["questions"]
        except (SafeError, ValueError, TypeError, RecursionError):
            raise AnalysisFailure("JEV_INPUT_INVALID", view) from None
        if len(body) > MAX_REQUEST_BYTES:
            raise AnalysisFailure("JEV_CONTEXT_LIMIT", view)
        if self.settings.data_policy == "nonpersonal_only" and contains_pii(frozen):
            raise AnalysisFailure("JEV_PII_INPUT", view)
        key = self._read_key(view)
        text = body.decode("utf-8")
        if key in text or credential_value(frozen):
            raise AnalysisFailure("JEV_SENSITIVE_INPUT", view)
        if self.settings.data_policy == "masked_minimal_v1":
            try:
                if contains_pii(questions):
                    raise PrivacyError("PERSONAL_QUESTION")
                frozen["state"] = self._masker.transform(frozen["state"], analysis_id)
                for question in questions.values():
                    question["instructions"] += self._masker.NOTE
                validate_questions(questions)
                body = canonical(frozen).encode("utf-8")
            except (PrivacyError, ValueError, TypeError, RecursionError):
                raise AnalysisFailure("JEV_PRIVACY_TRANSFORM_FAILED", view) from None
            if len(body) > MAX_REQUEST_BYTES:
                raise AnalysisFailure("JEV_CONTEXT_LIMIT", view)
        try:
            if Path(self.settings.budget_path).is_symlink():
                raise OSError()
            self._claim(analysis_id, view)
        except AnalysisFailure:
            raise
        except (OSError, sqlite3.Error):
            raise AnalysisFailure("JEV_BUDGET_BINDING", view) from None
        status, usage = "FAILED", None
        metadata = {"response_contract": RESPONSE_CONTRACT, "response_stage": "UNKNOWN", "response_issue": "UNKNOWN", "usage_status": "UNKNOWN_MISSING", "usage_complete": False, "http_status": "UNKNOWN", "content_type": "UNKNOWN", "json_valid": "UNKNOWN", "model_match": "UNKNOWN", "response_bytes": "UNKNOWN"}
        try:
            value = await asyncio.wait_for(self._request(body, key, view, metadata), timeout=20)
            usage, usage_status = usage_observation(value)
            metadata.update(usage_status=usage_status, usage_complete=usage_status == "VALID")
            if isinstance(value, dict) and "model" in value:
                metadata["model_match"] = value["model"] == MODEL
            try:
                answers, _ = validate_response(value, questions)
            except ResponseValidationError as exc:
                raise AnalysisFailure("JEV_RESPONSE_INVALID", view, {**metadata, **exc.metadata}) from None
            except (ValueError, TypeError, OverflowError):
                raise AnalysisFailure("JEV_RESPONSE_INVALID", view, {**metadata, "response_stage": "UNKNOWN"}) from None
            metadata.update(code="JEV_RESPONSE_VALID", response_stage="COMPLETE", response_issue="NONE", model_match=True,
                            confidence_basis="MIN_PROVIDER_COMPUTED", confidence_adjusted=any(x["provider"] != x["effective"] for x in answers.confidence_comparisons),
                            confidence_difference_observed=any(abs(x["provider"] - x["computed"]) > 1e-6 for x in answers.confidence_comparisons))
            status = "COMPLETED"
            return answers
        except asyncio.CancelledError:
            status = "CANCELLED"
            metadata["code"] = "ANALYSIS_CANCELLED"
            raise
        except AnalysisFailure as exc:
            metadata.update(failure_details(exc, enriched=True)[0])
            raise
        except (TimeoutError, httpx.TimeoutException):
            metadata["code"] = "API_TIMEOUT"
            raise AnalysisFailure("API_TIMEOUT", view, metadata) from None
        except httpx.TransportError:
            metadata["code"] = "API_CONNECTION"
            raise AnalysisFailure("API_CONNECTION", view, metadata) from None
        except Exception:
            metadata["code"] = "ADAPTER_ERROR"
            raise AnalysisFailure("ADAPTER_ERROR", view, metadata) from None
        finally:
            self._record(analysis_id, view, status, usage, metadata)

    async def _request(self, body, key, view, metadata):
        transport = self._transport or httpx.AsyncHTTPTransport(verify=True, retries=0, trust_env=False)
        async with httpx.AsyncClient(transport=transport, verify=True, trust_env=False,
                                     follow_redirects=False, timeout=15) as client:
            async with client.stream("POST", ENDPOINT, content=body,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"}) as response:
                metadata.update(response_stage="HTTP", http_status=response.status_code)
                ctype = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                metadata["content_type"] = "JSON" if ctype == "application/json" else "NON_JSON" if ctype else "MISSING"
                if response.status_code != 200:
                    code = ("API_AUTHENTICATION" if response.status_code in (401, 403) else
                            "API_RATE_LIMIT" if response.status_code in (429, 529) else
                            "JEV_CONTEXT_LIMIT" if response.status_code in (400, 413, 422) else "API_ERROR")
                    raise AnalysisFailure(code, view, {**metadata, "response_issue": "STATUS"})
                if ctype != "application/json":
                    raise AnalysisFailure("JEV_RESPONSE_INVALID", view, {**metadata, "response_stage": "CONTENT_TYPE", "response_issue": "MEDIA_TYPE"})
                data = bytearray()
                metadata["response_stage"] = "RESPONSE_SIZE"
                async for chunk in response.aiter_bytes():
                    if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise AnalysisFailure("JEV_RESPONSE_INVALID", view, {**metadata, "response_bytes": MAX_RESPONSE_BYTES + 1, "response_issue": "LIMIT"})
                    data.extend(chunk)
                metadata.update(response_stage="JSON", response_bytes=len(data))
                try:
                    value = strict_json(bytes(data))
                except SafeError:
                    raise AnalysisFailure("JEV_RESPONSE_INVALID", view, {**metadata, "json_valid": False, "response_issue": "INVALID_JSON"}) from None
                metadata["json_valid"] = True
                return value
