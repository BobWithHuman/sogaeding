"""Offline contract transport. Never imported by a live SIWC broker."""

import json

import httpx

from app.benchmark.runtime_test_provider import fake_provider as legacy
from app.benchmark.siwc_auth import MODEL
from app.benchmark.siwc_transport import NAMESPACE
from app.common import canonical


class FixtureCredentials:
    def metadata(self):
        return {"account_label": "fixture", "account_binding_sha256": "PUBLIC-OFFLINE-ACCOUNT"}

    def access(self):
        return "PUBLIC-OFFLINE-PLAN"


def fake_provider(request, *, functional=False):
    if request.url.host == "api.typesafe.ai":
        return legacy(request)
    body = json.loads(request.content)
    if (
        body.get("model") != MODEL
        or body.get("reasoning") != {"effort": "low"}
        or body.get("stream") is not True
        or body.get("store") is not False
        or "max_output_tokens" in body
    ):
        raise ValueError("OFFLINE_PLAN_CONTRACT")
    if body.get("tools"):
        tools = body["tools"]
        if len(tools) != 1 or tools[0]["type"] != "namespace" or tools[0]["name"] != NAMESPACE:
            raise ValueError("OFFLINE_NAMESPACE_REQUIRED")
        projected = {**body, "model": "gpt-5.2", "tools": tools[0]["tools"]}
        value = legacy(
            httpx.Request("POST", str(request.url), json=projected), functional=functional
        ).json()
        for item in value.get("output", []):
            if item.get("type") == "function_call":
                item["namespace"] = NAMESPACE
        value["model"] = MODEL
    else:
        value = {
            "id": "fixture-permission",
            "model": MODEL,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"decision":"APPROVED","reasoning":"OFFLINE_SIMULATOR_ONLY"}',
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 5},
        }
    events = []
    for index, item in enumerate(value["output"]):
        item.setdefault("id", value["id"] + "-item-" + str(index))
        events.append({"type": "response.output_item.done", "output_index": index, "item": item})
    value["output"] = []
    events.append({"type": "response.completed", "response": value})
    # Match the actual SIWC shape that exposed the former terminal-only bug.
    return httpx.Response(
        200, content="".join("data: " + canonical(e) + "\n\n" for e in events).encode()
    )
