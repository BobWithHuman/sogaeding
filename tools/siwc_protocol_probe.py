"""One new public-prompt SIWC request; never a replay or a DTAP score."""

import argparse
import asyncio
import hashlib
import os
from pathlib import Path

import httpx

from app.benchmark.runtime_budget import StopRun
from app.benchmark.siwc_auth import EFFORT, MODEL, RESOURCE, Credentials
from app.benchmark.siwc_transport import completed_stream, response_media
from app.common import SafeError, canonical, strict_json

REQUEST = {
    "model": MODEL,
    "reasoning": {"effort": EFFORT},
    "input": [{"role": "user", "content": "Reply with exactly CONNECTED."}],
    "store": False,
    "stream": True,
}
MAX_BYTES, SECONDS = 2_097_152, 60
ERROR_CODES = {
    "invalid_request_error",
    "unsupported_parameter",
    "unsupported_value",
    "invalid_value",
    "model_not_found",
    "invalid_model",
    "permission_denied",
    "insufficient_quota",
    "rate_limit_exceeded",
    "subscription_sharing_usage_limit_exceeded",
    "subscription_sharing_usage_unavailable",
    "server_error",
}
ERROR_PARAMS = {"model", "reasoning", "reasoning.effort", "input", "stream", "store"}
STREAM_CODES = {
    "SIWC_SSE_REQUIRED",
    "SIWC_RESPONSE_BYTES_UNKNOWN",
    "SIWC_PLAN_USAGE_UNAVAILABLE_STOP_BOTH",
    "SIWC_INCOMPLETE_OR_FAILED_UNKNOWN",
    "SIWC_DUPLICATE_TERMINAL_UNKNOWN",
    "SIWC_STREAM_NOT_COMPLETED_UNKNOWN",
    "SIWC_STREAM_EVENT_INVALID_UNKNOWN",
    "SIWC_STREAM_USAGE_INVALID_UNKNOWN",
    "SIWC_OUTPUT_AFTER_TERMINAL_UNKNOWN",
    "SIWC_OUTPUT_ITEM_INVALID_UNKNOWN",
    "SIWC_OUTPUT_ITEM_DUPLICATE_UNKNOWN",
    "SIWC_OUTPUT_ITEM_BINDING_UNKNOWN",
    "SIWC_OUTPUT_ITEMS_INCOMPLETE_UNKNOWN",
    "SIWC_OUTPUT_TERMINAL_MISMATCH_UNKNOWN",
    "SIWC_TOOL_NAMESPACE_BINDING_INVALID",
    "PROBE_TOOL_RESPONSE_REQUIRED",
    "PROBE_TOOL_ARGUMENTS_INVALID",
    "PROBE_PERMISSION_JSON_REQUIRED",
    "PROBE_PERMISSION_DECISION_REQUIRED",
    "SIWC_PERMISSION_FINAL_TEXT_REQUIRED",
}
AUTH_CODES = {
    "SIWC_ACCOUNT_LABEL_INVALID",
    "SIWC_CREDENTIAL_SYMLINK",
    "SIWC_OWNER_ONLY_STORAGE_REQUIRED",
    "SIWC_CREDENTIAL_TYPE_INVALID",
    "SIWC_LOGIN_REQUIRED_NO_API_FALLBACK",
    "SIWC_METADATA_HTTP_REJECTED",
    "SIWC_DISCOVERY_BINDING_INVALID",
    "SIWC_ID_SIGNATURE_REJECTED",
    "SIWC_ID_NONCE_OR_SUBJECT_REJECTED",
    "SIWC_REAUTH_REQUIRED_NO_API_FALLBACK",
    "SIWC_PLAN_PERMISSION_OR_TOKEN_INVALID",
    "SIWC_ACCOUNT_BINDING_CHANGED",
    "SIWC_REFRESH_NOT_YET_ALLOWED",
    "SIWC_REFRESH_IDENTITY_CHANGED",
    "PROBE_ACCOUNT_CHANGED",
    "PROBE_CATALOG_BINDING_INVALID",
}


def safe_failure(error):
    # Never include exception messages/args, provider bodies or path strings.
    known_classes = {
        "StopRun",
        "PermissionError",
        "FileNotFoundError",
        "KeyError",
        "SafeError",
        "ValueError",
        "TypeError",
        "OSError",
        "RuntimeError",
        "AttributeError",
        "NameError",
        "ImportError",
        "ModuleNotFoundError",
        "JSONDecodeError",
        "ConnectError",
        "ReadError",
        "ReadTimeout",
        "ConnectTimeout",
        "PoolTimeout",
        "WriteTimeout",
        "RemoteProtocolError",
        "SSLError",
    }
    name = type(error).__name__
    detail = {"exception_class": name if name in known_classes else "OTHER"}
    if isinstance(error, StopRun):
        return {
            **detail,
            "error_kind": "VALIDATION_REJECTED",
            "safe_code": str(error) if str(error) in AUTH_CODES else "OTHER",
        }
    for cls, name in [
        (PermissionError, "FILE_PERMISSION"),
        (FileNotFoundError, "FILE_NOT_FOUND"),
        (httpx.TimeoutException, "NETWORK_TIMEOUT"),
        (httpx.HTTPError, "NETWORK_FAILURE"),
        (KeyError, "LOCAL_DATA_SHAPE"),
        (SafeError, "LOCAL_VALIDATION"),
        (ValueError, "LOCAL_VALUE"),
        (TypeError, "LOCAL_TYPE"),
        (OSError, "LOCAL_OS"),
    ]:
        if isinstance(error, cls):
            return {**detail, "error_kind": name}
    return {**detail, "error_kind": "UNEXPECTED_EXCEPTION"}


def authenticate(manifest, progress, *, credentials_factory=Credentials):
    progress("CREDENTIAL_OPEN")
    credentials = credentials_factory(account="main")
    progress("ACCOUNT_METADATA")
    account = credentials.metadata()
    if account["account_binding_sha256"] != manifest["account_binding_sha256"]:
        raise StopRun("PROBE_ACCOUNT_CHANGED")
    progress("CATALOG_METADATA")
    # Reuse the trusted account check already performed; do not add another
    # model-catalog network request to this transport diagnostic.
    checked = credentials.read(credentials.root / "main-model-check.json")
    if (
        checked.get("account_binding_sha256") != account["account_binding_sha256"]
        or checked.get("model") != MODEL
        or checked.get("reasoning_effort") != EFFORT
    ):
        raise StopRun("PROBE_CATALOG_BINDING_INVALID")
    progress("OAUTH_ACCESS")
    return credentials.access()


def safe_body_summary(raw):
    result = {"body_kind": "OTHER", "structured_error_code": None, "structured_error_param": None}
    if not raw.strip():
        return {**result, "body_kind": "EMPTY"}
    if raw.lstrip().startswith((b"data:", b"event:")):
        return {**result, "body_kind": "SSE"}
    try:
        value = strict_json(raw)
    except (SafeError, ValueError, TypeError):
        return result
    if not isinstance(value, dict):
        return {**result, "body_kind": "JSON_OTHER"}
    error = value.get("error")
    if isinstance(error, dict):
        code, param = error.get("code"), error.get("param")
        return {
            **result,
            "body_kind": "JSON_ERROR",
            "structured_error_code": code
            if isinstance(code, str) and code in ERROR_CODES
            else "OTHER",
            "structured_error_param": param
            if isinstance(param, str) and param in ERROR_PARAMS
            else None,
        }
    return {
        **result,
        "body_kind": "JSON_RESPONSE" if value.get("object") == "response" else "JSON_OTHER",
    }


async def request_once(
    access, *, transport=None, progress=None, request=None, validate_result=None
):
    # This is the only inference POST in this diagnostic. No redirects/retries.
    report = {
        "state": "UNKNOWN",
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "billing": "chatgpt-plan",
        "api_key_fallback": False,
        "benchmark_score": "NOT_APPLICABLE",
        "http_status": None,
        "media_type": None,
        "usage": None,
        "error_kind": None,
        "stage": "RESPONSES_PREPARATION",
        "responses_post_attempted": False,
    }
    raw = bytearray()
    stream_detail = {}
    try:
        async with (
            asyncio.timeout(SECONDS),
            httpx.AsyncClient(
                transport=transport, trust_env=False, follow_redirects=False, timeout=SECONDS
            ) as client,
        ):
            report.update(stage="RESPONSES_REQUEST", responses_post_attempted=True)
            if progress:
                progress(report)
            async with client.stream(
                "POST",
                RESOURCE + "/responses",
                content=canonical(REQUEST if request is None else request).encode(),
                headers={
                    "Authorization": "Bearer " + access,
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            ) as response:
                report.update(http_status=response.status_code, media_type=response_media(response))
                async for block in response.aiter_bytes():
                    if len(raw) + len(block) > MAX_BYTES:
                        return {**report, "error_kind": "RESPONSE_BYTES_LIMIT"}
                    raw.extend(block)
        report.update(safe_body_summary(bytes(raw)), body_bytes=len(raw))
        if not 200 <= report["http_status"] < 300:
            return {**report, "error_kind": "HTTP_REJECTED"}
        if report["media_type"] not in ("text/event-stream", ""):
            return {**report, "error_kind": "NON_SSE_RESPONSE"}
        replay = httpx.Response(
            report["http_status"],
            headers={"content-type": report["media_type"]},
            content=bytes(raw),
        )
        try:
            result = await completed_stream(replay, maximum=MAX_BYTES, diagnostic=stream_detail)
        finally:
            report["stream_detail"] = stream_detail
        usage = result.get("usage")
        if not isinstance(usage, dict) or not all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
        ):
            return {**report, "error_kind": "USAGE_UNKNOWN"}
        report["usage"] = {k: usage[k] for k in ("input_tokens", "output_tokens")}
        validation = validate_result(result) if validate_result else {}
        return {
            **report,
            **validation,
            "state": "COMPLETED",
            "stream_validation": "HEADERLESS_FULL_SSE"
            if not report["media_type"]
            else "DECLARED_SSE",
            "usage": {k: usage[k] for k in ("input_tokens", "output_tokens")},
        }
    except (httpx.HTTPError, TimeoutError):
        return {**report, "error_kind": "TRANSPORT_OR_TIMEOUT"}
    except StopRun as error:
        return {
            **report,
            "error_kind": "STREAM_OR_PROTOCOL_INVALID",
            "stream_stop": str(error) if str(error) in STREAM_CODES else "OTHER",
        }
    except (SafeError, ValueError, TypeError):
        return {**report, "error_kind": "STREAM_OR_PROTOCOL_INVALID"}
    except Exception as error:
        return {**report, **safe_failure(error)}


def verify_bundle(root, expected):
    raw = (root / "manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise StopRun("PROBE_MANIFEST_MISMATCH")
    manifest = strict_json(raw)
    if (
        manifest["request"] != REQUEST
        or manifest["max_responses_requests"] != 1
        or manifest["seconds"] != SECONDS
        or manifest["response_bytes"] != MAX_BYTES
    ):
        raise StopRun("PROBE_LIMITS_CHANGED")
    for name, digest in manifest["sources"].items():
        original = root / name
        path = original.resolve()
        if (
            original.is_symlink()
            or not path.is_relative_to(root.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise StopRun("PROBE_SOURCE_MISMATCH")
    return manifest


def claim(root):
    fd = os.open(root / "one-request.claim", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)


def save(root, report):
    temporary = root / "result.pending.json"
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(canonical(report))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, root / "result.json")


def main(*, validate_result=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-sha256", required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--send-one-request", action="store_true")
    modes.add_argument("--check-login", action="store_true")
    args = parser.parse_args()
    bundle, output = Path("/project"), Path("/evidence")
    try:
        manifest = verify_bundle(bundle, args.manifest_sha256)
        if not args.send_one_request and not args.check_login:
            public = output / "access-check.public"
            if public.exists():
                if public.is_symlink() or public.read_text() != "PUBLIC-PROBE-WRITE-CHECK":
                    raise StopRun("PROBE_EVIDENCE_ACCESS_INVALID")
            else:
                fd = os.open(public, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, "w") as stream:
                    stream.write("PUBLIC-PROBE-WRITE-CHECK")
            print(
                canonical(
                    {
                        "state": "DIAGNOSTIC_PREPARED",
                        "inference": "NOT_RUN",
                        "max_responses_requests": 1,
                        "model": MODEL,
                        "reasoning_effort": EFFORT,
                    }
                )
            )
            return
        # Auth-only verification is repeatable and cannot dispatch inference.
        # A send claim is consumed on all failures and is never reset.
        if args.send_one_request:
            claim(output)
        report = {
            "state": "STARTED",
            "requests_maximum": 1,
            "usage": None,
            "benchmark_score": "NOT_APPLICABLE",
            "stage": "AUTH_PREPARATION",
            "responses_post_attempted": False,
        }

        def persist(value):
            if args.send_one_request:
                save(output, value)

        def stage(name):
            report["stage"] = name
            persist(report)

        persist(report)
        try:
            access = authenticate(manifest, stage, credentials_factory=Credentials)
            if args.check_login:
                report = {
                    "state": "AUTH_READY",
                    "inference": "NOT_RUN",
                    "responses_post_attempted": False,
                }
            else:
                stage("RESPONSES_PREPARATION")
                report = asyncio.run(
                    request_once(access, progress=persist, validate_result=validate_result)
                )
        except Exception as error:
            report = {**report, "state": "UNKNOWN", **safe_failure(error)}
        persist(report)
        print(canonical(report))
    except Exception:
        print(canonical({"state": "NOT_SENT_OR_EXISTING_CLAIM", "automatic_retry": False}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
