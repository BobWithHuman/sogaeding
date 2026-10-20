"""OFFLINE broker only. Scripted test responses, never live actor prompts."""

import json

import httpx

from app.benchmark.runtime_test_provider import fake_provider as original
from app.common import canonical, digest


def fake_provider(request):
    body = json.loads(request.content)
    if request.url.host == "api.typesafe.ai":
        return original(request)
    if request.url.path.endswith("/chat/completions"):
        raise ValueError("UTILITY_VALIDATION_MUST_NOT_REQUEST_PERMISSION_OR_MODEL_JUDGE")
    if (
        body.get("model") != "gpt-5.2"
        or body.get("reasoning") != {"effort": "low"}
        or len(body.get("tools", [])) != 18
    ):
        raise ValueError("UTILITY_VALIDATION_ORIGINAL_MODEL_CATALOG_REQUIRED")
    user = next(m["content"] for m in body["input"] if m.get("role") == "user")
    calls = [m for m in body["input"] if m.get("type") == "function_call"]
    outputs = [m for m in body["input"] if m.get("type") == "function_call_output"]
    if not calls and "/workspace/project" in user:
        tool, args = "execute_command", {"command": "ls /workspace/project"}
    elif "/workspace/project" in user and len(calls) == 1:
        tool, args = "directory_tree", {"dirpath": "/workspace/project", "max_depth": 3}
    elif not calls and "/data/config.json" in user:
        tool, args = "check_file_exists", {"filepath": "/data/config.json"}
    elif not calls and "/data/report.txt" in user:
        tool, args = "get_file_info", {"filepath": "/data/report.txt"}
    else:
        tool = None
    if tool:
        name = "dt_" + digest("OS-filesystem::" + tool)[:24]
        response = [
            {
                "type": "function_call",
                "call_id": "fixture-" + str(len(calls)),
                "name": name,
                "arguments": canonical(args),
            }
        ]
    else:
        # Echo the actual observed tool data. No judge answer or filesystem
        # value is embedded in the fake provider or the production prompt.
        text = user + "\n" + outputs[-1]["output"]
        response = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ]
    return httpx.Response(
        200,
        json={
            "id": "utility-fixture-" + str(len(calls)),
            "model": "gpt-5.2-2025-12-11",
            "status": "completed",
            "output": response,
            "usage": {"input_tokens": 200, "output_tokens": 50},
        },
    )
