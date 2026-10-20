"""SIWC Responses/SSE compatibility, exclusively ChatGPT plan credentials."""

import asyncio
import copy
import time
from uuid import uuid4

import httpx

from app.benchmark.runtime_budget import BudgetStop, StopRun
from app.benchmark.siwc_auth import EFFORT, MODEL, RESOURCE
from app.common import canonical, strict_json

NAMESPACE = "OS_filesystem"
FIELDS = {
    "model",
    "reasoning",
    "store",
    "stream",
    "parallel_tool_calls",
    "input",
    "tools",
    "include",
}


def actor_request(body):
    if (
        set(body) - FIELDS
        or body.get("model") != MODEL
        or body.get("reasoning") != {"effort": EFFORT}
        or body.get("store") is not False
        or body.get("stream") is not True
        or body.get("parallel_tool_calls") is not False
        or not isinstance(body.get("input"), list)
        or not isinstance(body.get("tools"), list)
    ):
        raise StopRun("SIWC_ACTOR_LUNA_LOW_CONTRACT")
    value = copy.deepcopy(body)
    names = set()
    for tool in value["tools"]:
        if (
            tool.get("type") != "function"
            or not isinstance(tool.get("name"), str)
            or tool["name"] in names
        ):
            raise StopRun("SIWC_EXACT_FUNCTION_TOOLS_REQUIRED")
        names.add(tool["name"])
    value["tools"] = [
        {
            "type": "namespace",
            "name": NAMESPACE,
            "description": "Registered OS-filesystem tools.",
            "tools": value["tools"],
        }
    ]
    for item in value["input"]:
        if item.get("role") == "system":
            raise StopRun("SIWC_SYSTEM_ITEM_UNSUPPORTED")
        if item.get("type") == "function_call":
            if item.get("name") not in names or item.get("namespace", NAMESPACE) != NAMESPACE:
                raise StopRun("SIWC_HISTORY_TOOL_BINDING_INVALID")
            item["namespace"] = NAMESPACE
    return value, names


def permission_request(body):
    # Exact original conditional simulator request, distinct from human approval.
    if (
        set(body) - {"model", "messages", "temperature", "max_completion_tokens"}
        or body.get("model") != MODEL
        or body.get("temperature") != 0.1
        or body.get("max_completion_tokens") != 500
        or not isinstance(body.get("messages"), list)
    ):
        raise StopRun("SIWC_PERMISSION_SHAPE_CHANGED")
    history = []
    for item in body["messages"]:
        if (
            set(item) != {"role", "content"}
            or item["role"] not in ("system", "user", "assistant")
            or not isinstance(item["content"], str)
        ):
            raise StopRun("SIWC_PERMISSION_MESSAGE_INVALID")
        history.append(
            {
                "role": "developer" if item["role"] == "system" else item["role"],
                "content": item["content"],
            }
        )
    return {
        "model": MODEL,
        "reasoning": {"effort": EFFORT},
        "store": False,
        "stream": True,
        "parallel_tool_calls": False,
        "input": history,
    }, set()


def response_media(response):
    # MIME tokens are case-insensitive. Never persist arbitrary header text,
    # response bodies, request IDs or provider credentials as diagnostics.
    value = response.headers.get("content-type", "").partition(";")[0].strip().lower()
    return (
        value
        if value in {"text/event-stream", "application/json", "text/html", "text/plain", ""}
        else "other"
    )


async def completed_stream(response, *, maximum, diagnostic=None):
    # Only fixed counters/booleans/enums. No provider text, IDs or credentials.
    detail = diagnostic if diagnostic is not None else {}
    detail.update(
        body_bytes=0,
        events=0,
        completed_events=0,
        terminal_seen=False,
        pending_bytes=0,
        pending_kind="EMPTY",
        terminal_status="MISSING",
        model_matches=False,
        trailing_done_ignored=False,
    )
    media = response_media(response)
    if not 200 <= response.status_code < 300 or media not in ("text/event-stream", ""):
        raise StopRun("SIWC_SSE_REQUIRED")
    # Missing MIME only makes this eligible for full SSE validation. Explicit
    # conflicting MIME is still rejected; no prefix alone proves completion.
    headerless = media == ""
    pending = bytearray()
    total = 0
    complete = None
    terminal_seen = False
    first_event = True
    added_items, done_items = {}, {}
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        detail["body_bytes"] = total
        if total > maximum:
            raise StopRun("SIWC_RESPONSE_BYTES_UNKNOWN")
        pending.extend(chunk)
        # SSE permits LF or CRLF. No partial UTF-8 is decoded before delimiter.
        while b"\n\n" in pending.replace(b"\r\n", b"\n"):
            normalized = pending.replace(b"\r\n", b"\n")
            event, _, rest = normalized.partition(b"\n\n")
            pending = bytearray(rest)
            if first_event:
                event = event.removeprefix(b"\xef\xbb\xbf")
                first_event = False
            lines = event.split(b"\n")
            if headerless and any(
                line and not line.startswith((b":", b"data:", b"event:", b"id:", b"retry:"))
                for line in lines
            ):
                raise StopRun("SIWC_STREAM_EVENT_INVALID_UNKNOWN")
            data = b"\n".join(line[5:].lstrip(b" ") for line in lines if line.startswith(b"data:"))
            if not data or data == b"[DONE]":
                continue
            value = strict_json(data)
            if not isinstance(value, dict) or not isinstance(value.get("type"), str):
                raise StopRun("SIWC_STREAM_EVENT_INVALID_UNKNOWN")
            kind = value.get("type")
            detail["events"] += 1
            if headerless:
                names = [line[6:].strip() for line in lines if line.startswith(b"event:")]
                if (
                    (not kind.startswith("response.") and kind != "error")
                    or len(names) > 1
                    or (names and names[0] != kind.encode())
                ):
                    raise StopRun("SIWC_STREAM_EVENT_INVALID_UNKNOWN")
            if terminal_seen and kind != "response.completed":
                raise StopRun("SIWC_OUTPUT_AFTER_TERMINAL_UNKNOWN")
            if kind in ("response.output_item.added", "response.output_item.done"):
                index, item = value.get("output_index"), value.get("item")
                if (
                    type(index) is not int
                    or not 0 <= index < 4096
                    or not isinstance(item, dict)
                    or not isinstance(item.get("id"), str)
                    or not item["id"]
                    or item.get("type") not in ("reasoning", "function_call", "message")
                ):
                    raise StopRun("SIWC_OUTPUT_ITEM_INVALID_UNKNOWN")
                if kind == "response.output_item.added":
                    if index in added_items or index in done_items:
                        raise StopRun("SIWC_OUTPUT_ITEM_DUPLICATE_UNKNOWN")
                    added_items[index] = (item["id"], item["type"])
                else:
                    if index in done_items or (
                        index in added_items and added_items[index] != (item["id"], item["type"])
                    ):
                        raise StopRun("SIWC_OUTPUT_ITEM_BINDING_UNKNOWN")
                    done_items[index] = item
            if kind in ("response.failed", "response.incomplete", "error"):
                error = (value.get("response") or {}).get("error") or value.get("error") or {}
                code = error.get("code") if isinstance(error, dict) else None
                if code in (
                    "subscription_sharing_usage_limit_exceeded",
                    "subscription_sharing_usage_unavailable",
                ):
                    raise StopRun("SIWC_PLAN_USAGE_UNAVAILABLE_STOP_BOTH")
                raise StopRun("SIWC_INCOMPLETE_OR_FAILED_UNKNOWN")
            if kind == "response.completed":
                detail["completed_events"] += 1
                if terminal_seen:
                    raise StopRun("SIWC_DUPLICATE_TERMINAL_UNKNOWN")
                terminal_seen = True
                complete = value.get("response")
                if not isinstance(complete, dict):
                    raise StopRun("SIWC_STREAM_EVENT_INVALID_UNKNOWN")
                detail["terminal_seen"] = True
                status = complete.get("status")
                detail["terminal_status"] = (
                    status
                    if status
                    in ("completed", "failed", "incomplete", "in_progress", "cancelled", "queued")
                    else "OTHER"
                )
                detail["model_matches"] = complete.get("model") == MODEL
    detail["pending_bytes"] = len(pending)
    detail["pending_kind"] = (
        "EMPTY"
        if not pending.strip()
        else "DONE_SENTINEL"
        if pending.strip() == b"data: [DONE]"
        else "UNFRAMED"
    )
    # Some peers omit the final blank line on the optional DONE sentinel.
    # An already parsed response.completed remains mandatory. Never accept an
    # undelimited JSON response, a partial output, or arbitrary trailing data.
    if terminal_seen and pending.strip() == b"data: [DONE]":
        detail["trailing_done_ignored"] = True
        pending.clear()
    if (
        pending.strip()
        or not isinstance(complete, dict)
        or complete.get("status") != "completed"
        or complete.get("model") != MODEL
    ):
        raise StopRun("SIWC_STREAM_NOT_COMPLETED_UNKNOWN")
    usage = complete.get("usage")
    if not isinstance(usage, dict) or not all(
        type(usage.get(key)) is int and usage[key] >= 0 for key in ("input_tokens", "output_tokens")
    ):
        raise StopRun("SIWC_STREAM_USAGE_INVALID_UNKNOWN")
    if set(added_items) - set(done_items) or sorted(done_items) != list(range(len(done_items))):
        raise StopRun("SIWC_OUTPUT_ITEMS_INCOMPLETE_UNKNOWN")
    if done_items:
        # SIWC can send output only in output_item.done, with an empty output
        # array on response.completed. Only complete items, never deltas or an
        # added item's unfinished arguments/encrypted content, can be forwarded.
        output = [done_items[i] for i in range(len(done_items))]
        if len({item["id"] for item in output}) != len(output):
            raise StopRun("SIWC_OUTPUT_ITEM_DUPLICATE_UNKNOWN")
        terminal_output = complete.get("output")
        if terminal_output not in (None, []) and terminal_output != output:
            raise StopRun("SIWC_OUTPUT_TERMINAL_MISMATCH_UNKNOWN")
        complete = {**complete, "output": output}
    return complete


def normalize(value, names, *, permission=False):
    value = copy.deepcopy(value)
    output = value.get("output")
    if not isinstance(output, list):
        raise StopRun("SIWC_OUTPUT_INVALID")
    for item in output:
        if item.get("type") == "function_call":
            if (
                permission
                or item.get("namespace") != NAMESPACE
                or item.get("name") not in names
                or not isinstance(item.get("call_id"), str)
                or not item["call_id"].strip()
            ):
                raise StopRun("SIWC_TOOL_NAMESPACE_BINDING_INVALID")
            del item["namespace"]
        elif item.get("type") not in ("message", "reasoning"):
            raise StopRun("SIWC_UNENROLLED_OUTPUT_KIND")
    if not permission:
        return value
    text = "\n".join(
        p["text"]
        for item in output
        if item["type"] == "message"
        for p in item.get("content", [])
        if p.get("type") == "output_text"
    )
    if not text:
        raise StopRun("SIWC_PERMISSION_FINAL_TEXT_REQUIRED")
    return {
        "id": value.get("id"),
        "model": MODEL,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": {
            "prompt_tokens": value["usage"]["input_tokens"],
            "completion_tokens": value["usage"]["output_tokens"],
        },
    }


class PlanMeter:
    def __init__(self, budget):
        self.budget = budget
        with budget.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS plan_requests(id TEXT PRIMARY KEY, task TEXT, arm TEXT, role TEXT, model TEXT, state TEXT, at REAL, usage TEXT, seconds INTEGER)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS plan_http_observations(request_id TEXT PRIMARY KEY, status INTEGER NOT NULL, media TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS plan_stream_observations(request_id TEXT PRIMARY KEY, detail TEXT NOT NULL)"
            )

    def observe_stream(self, rid, detail):
        allowed = {
            "body_bytes",
            "events",
            "completed_events",
            "terminal_seen",
            "pending_bytes",
            "pending_kind",
            "terminal_status",
            "model_matches",
            "trailing_done_ignored",
        }
        if set(detail) != allowed or any(
            not isinstance(v, (bool, int, str)) for v in detail.values()
        ):
            raise StopRun("SIWC_STREAM_DIAGNOSTIC_INVALID")
        if (
            any(
                type(detail[k]) is not int or not 0 <= detail[k] <= 1_073_741_824
                for k in ("body_bytes", "events", "completed_events", "pending_bytes")
            )
            or any(
                type(detail[k]) is not bool
                for k in ("terminal_seen", "model_matches", "trailing_done_ignored")
            )
            or detail["pending_kind"] not in ("EMPTY", "DONE_SENTINEL", "UNFRAMED")
            or detail["terminal_status"]
            not in (
                "MISSING",
                "OTHER",
                "completed",
                "failed",
                "incomplete",
                "in_progress",
                "cancelled",
                "queued",
            )
        ):
            raise StopRun("SIWC_STREAM_DIAGNOSTIC_INVALID")
        with self.budget.db() as db:
            if (
                db.execute(
                    "INSERT INTO plan_stream_observations SELECT id,? FROM plan_requests WHERE id=? AND state='STARTED'",
                    (canonical(detail), rid),
                ).rowcount
                != 1
            ):
                raise StopRun("SIWC_STREAM_OBSERVATION_UNBOUND")

    def observe_http(self, rid, response):
        with self.budget.db() as db:
            if (
                db.execute(
                    "INSERT INTO plan_http_observations SELECT id,?,? FROM plan_requests WHERE id=? AND state='STARTED'",
                    (response.status_code, response_media(response), rid),
                ).rowcount
                != 1
            ):
                raise StopRun("SIWC_HTTP_OBSERVATION_UNBOUND")

    def reserve(self, job, seconds):
        rid = str(uuid4())
        limits = self.budget.manifest["chatgpt_plan"]["limits"]
        with self.budget.db() as db:
            self.budget._active(db)
            if (
                job["arm"] not in ("engine-off", "engine-on")
                or job["task"] not in self.budget.manifest["task_keys"]
                or job["provider"] not in ("actor", "environment")
            ):
                raise StopRun("SIWC_ROLE_OR_TASK_UNBOUND")
            if not db.execute(
                "SELECT 1 FROM jobs WHERE task=? AND arm=? AND state='CLAIMED'",
                (job["task"], job["arm"]),
            ).fetchone():
                raise StopRun("SIWC_ACTIVE_TASK_REQUIRED")
            for where, args, count, elapsed in [
                ("1=1", (), limits["requests"], limits["seconds"]),
                ("arm=?", (job["arm"],), limits["per_arm_requests"], limits["seconds"]),
                (
                    "task=? AND arm=? AND role=?",
                    (job["task"], job["arm"], job["provider"]),
                    limits["per_task_requests"],
                    limits["per_task_seconds"],
                ),
            ]:
                used = db.execute(
                    "SELECT count(*),coalesce(sum(seconds),0) FROM plan_requests WHERE " + where,
                    args,
                ).fetchone()
                if used[0] + 1 > count or used[1] + seconds > elapsed:
                    raise BudgetStop("CAP_EXHAUSTED_CHATGPT_PLAN")
            db.execute(
                "INSERT INTO plan_requests VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    rid,
                    job["task"],
                    job["arm"],
                    job["provider"],
                    MODEL,
                    "STARTED",
                    time.time(),
                    None,
                    seconds,
                ),
            )
        return rid

    def record(self, rid, usage=None):
        valid = isinstance(usage, dict) and all(
            type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")
        )
        with self.budget.db() as db:
            if (
                db.execute(
                    "UPDATE plan_requests SET state=?,usage=? WHERE id=? AND state='STARTED'",
                    ("COMPLETED" if valid else "UNKNOWN", canonical(usage) if valid else None, rid),
                ).rowcount
                != 1
            ):
                raise StopRun("SIWC_REQUEST_FINAL_NO_REPLAY")
        return valid


class PlanTransport:
    def __init__(self, budget, credentials, *, live=False, transport=None):
        if live and transport is not None:
            raise StopRun("MOCK_FORBIDDEN_IN_USER_RUN")
        if not live and not isinstance(transport, httpx.MockTransport):
            raise StopRun("OFFLINE_EXPLICIT_FAKE_REQUIRED")
        self.budget, self.credentials, self.live, self.transport = (
            budget,
            credentials,
            live,
            transport,
        )
        self.meter = PlanMeter(budget)
        self.account = None

    async def send(self, job, path, body):
        role = job["provider"]
        if role == "actor" and path == "responses":
            wire, names = actor_request(body)
        elif role == "environment" and path == "chat/completions":
            wire, names = permission_request(body)
        else:
            raise StopRun("SIWC_NO_JUDGE_OR_API_FALLBACK")
        raw = canonical(wire).encode()
        profile = self.budget.manifest["providers"][role]["per_request"]
        if len(raw) > profile["wire_bytes"]:
            raise StopRun("SIWC_CONTEXT_BYTES_LIMIT")
        account = self.credentials.metadata()
        if self.account is not None and self.account != account:
            raise StopRun("SIWC_ACCOUNT_CHANGED_STOP_BOTH")
        self.account = account
        access = await asyncio.to_thread(self.credentials.access)
        if access.encode() in raw:
            raise StopRun("SIWC_ACTUAL_CREDENTIAL_IN_INPUT")
        rid = self.meter.reserve(job, profile["seconds"])
        recorded = False
        started = time.monotonic()
        try:
            async with (
                asyncio.timeout(profile["seconds"]),
                httpx.AsyncClient(
                    transport=self.transport,
                    timeout=profile["seconds"],
                    trust_env=False,
                    follow_redirects=False,
                ) as client,
            ):
                async with client.stream(
                    "POST",
                    RESOURCE + "/responses",
                    content=raw,
                    headers={
                        "Authorization": "Bearer " + access,
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                ) as response:
                    self.meter.observe_http(rid, response)
                    if response.status_code in (401, 403):
                        raise StopRun("SIWC_AUTH_STOP_BOTH_NO_FALLBACK")
                    if response.status_code == 429:
                        raise StopRun("SIWC_PLAN_LIMIT_STOP_BOTH_NO_FALLBACK")
                    response.raise_for_status()
                    stream_detail = {}
                    try:
                        result = await completed_stream(
                            response, maximum=profile["response_bytes"], diagnostic=stream_detail
                        )
                    finally:
                        self.meter.observe_stream(rid, stream_detail)
            usage = result.get("usage")
            if isinstance(usage, dict):
                usage = {**usage, "elapsed_ms": int((time.monotonic() - started) * 1000)}
            if not self.meter.record(rid, usage):
                recorded = True
                raise StopRun("SIWC_USAGE_UNKNOWN_NO_RETRY")
            recorded = True
            return normalize(result, names, permission=role == "environment")
        except BaseException as error:
            if not recorded:
                self.meter.record(rid)
            code = str(error) if isinstance(error, StopRun) else "SIWC_TRANSPORT_UNKNOWN_NO_RETRY"
            self.budget.stop(code)
            raise StopRun(code) from None
