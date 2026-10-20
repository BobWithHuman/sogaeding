"""One harmless tool-call response; validates output without executing a tool."""

import json

import siwc_protocol_probe as probe

from app.benchmark.runtime_budget import StopRun
from app.benchmark.siwc_auth import EFFORT, MODEL
from app.benchmark.siwc_transport import NAMESPACE, normalize

REQUEST = {
    "model": MODEL,
    "reasoning": {"effort": EFFORT},
    "store": False,
    "stream": True,
    "parallel_tool_calls": False,
    "input": [
        {
            "role": "user",
            "content": "Call dt_probe_echo exactly once with value CONNECTED. Return a tool call, not a text answer. This is a transport diagnostic and no tool will execute.",
        }
    ],
    "tools": [
        {
            "type": "namespace",
            "name": NAMESPACE,
            "description": "Harmless transport diagnostic only.",
            "tools": [
                {
                    "type": "function",
                    "name": "dt_probe_echo",
                    "description": "Return the fixed public string CONNECTED; no file, shell or network effect.",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "string", "enum": ["CONNECTED"]}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                    "strict": False,
                }
            ],
        }
    ],
    "include": ["reasoning.encrypted_content"],
}


def validate_result(value):
    normalized = normalize(value, {"dt_probe_echo"})
    calls = [x for x in normalized["output"] if x["type"] == "function_call"]
    if len(calls) != 1:
        raise StopRun("PROBE_TOOL_RESPONSE_REQUIRED")
    try:
        arguments = json.loads(calls[0]["arguments"])
    except (KeyError, TypeError, ValueError) as error:
        raise StopRun("PROBE_TOOL_ARGUMENTS_INVALID") from error
    if arguments != {"value": "CONNECTED"}:
        raise StopRun("PROBE_TOOL_ARGUMENTS_INVALID")
    return {
        "tool_response_validated": True,
        "tool_calls": 1,
        "output_items": len(normalized["output"]),
        "tool_executions": 0,
    }


if __name__ == "__main__":
    probe.REQUEST = REQUEST
    probe.main(validate_result=validate_result)
