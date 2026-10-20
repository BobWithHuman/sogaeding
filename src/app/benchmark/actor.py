"""Separate Responses API backend; not a Codex CLI experiment."""

from uuid import uuid4

import httpx

from app.common import canonical

MODEL = "gpt-5.2"
EFFORT = "low"
ENDPOINT = "https://api.openai.com/v1/responses"


def model_material(task_instruction, system_prompt):
    if not all(isinstance(s, str) and s.strip() for s in (task_instruction, system_prompt)):
        raise ValueError("ACTUAL_USER_AND_SYSTEM_REQUIRED")
    # Takes exactly two allowlisted strings, never a Task/Attack/judge dict.
    return [
        {"role": "developer", "content": system_prompt},
        {"role": "user", "content": task_instruction},
    ]


class ResponsesBackend:
    def __init__(self, ledger, arm, *, model=MODEL, effort=EFFORT, transport=None, key=None):
        if model != MODEL or effort != EFFORT or arm not in ("engine-off", "engine-on"):
            raise ValueError("FIXED_MODEL_EFFORT_TWO_ARMS_REQUIRED")
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError("ONLY_EXPLICIT_OFFLINE_MOCK_TRANSPORT")
        if transport is None or key is not None:
            raise ValueError("LIVE_DISABLED_PENDING_FULL_COVERAGE_AND_COST_REVIEW")
        self.ledger, self.arm, self.transport, self.key = ledger, arm, transport, key
        self.model, self.effort = model, effort

    def wire(self, messages, tools):
        if self.model != MODEL or self.effort != EFFORT:
            raise ValueError("MODEL_EFFORT_CHANGED_BEFORE_TRANSMISSION")
        value = {
            "model": MODEL,
            "reasoning": {"effort": EFFORT},
            "input": messages,
            "tools": tools,
            "parallel_tool_calls": False,
            "max_output_tokens": 2048,
            "store": False,
        }
        if len(canonical(value).encode()) > 65536:
            raise ValueError("ACTOR_WIRE_CONTEXT_LIMIT")
        return value

    async def respond(self, messages, tools):
        body = self.wire(messages, tools)
        request_id = str(uuid4())
        # UTF-8 bytes + protocol allowance is a conservative reservation bound,
        # not an exact tokenizer count. Actual usage remains separately recorded.
        self.ledger.reserve(
            request_id, "actor", self.arm, len(canonical(body).encode()) + 4096, 2048
        )
        recorded = False
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=60, trust_env=False, follow_redirects=False
            ) as client:
                response = await client.post(
                    ENDPOINT,
                    json=body,
                    headers={"Authorization": "Bearer " + (self.key or "PUBLIC-OFFLINE-FAKE")},
                )
                response.raise_for_status()
                if len(response.content) > 131072:
                    raise ValueError("ACTOR_RESPONSE_LIMIT")
                value = response.json()
                resolved = value.get("model")
                if resolved != MODEL and not (
                    isinstance(resolved, str) and resolved.startswith(MODEL + "-")
                ):
                    raise ValueError("RESOLVED_MODEL_MISMATCH")
                complete = self.ledger.record(request_id, value.get("usage"))
                recorded = True
                if not complete:
                    raise ValueError("USAGE_UNKNOWN_STOP_NO_RETRY")
                return value
        except BaseException:
            # Request may already have reached the provider. Keep reservation;
            # state UNKNOWN never means free budget or automatic retransmission.
            if not recorded:
                self.ledger.record(request_id, None)
            raise
