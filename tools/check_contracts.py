"""Validate checked-in contracts and examples; this does not test the app."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "mvp" / "contracts"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_local_refs(document: dict, label: str) -> None:
    """Require offline, in-document references, to avoid network resolution."""
    pending = [document]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            reference = item.get("$ref")
            if reference is not None:
                if not reference.startswith("#/"):
                    raise ValueError(f"{label}: external or unsupported $ref")
                target = document
                for component in reference[2:].split("/"):
                    target = target[component.replace("~1", "/").replace("~0", "~")]
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def example_validator(example: dict, api: dict, tool_contract: dict) -> Draft202012Validator:
    if "schema" in example:
        schema_name = example["schema"]
        document = copy.deepcopy(api)
        document["$ref"] = f"#/components/schemas/{schema_name}"
    else:
        tool_name = example["tool_schema"]
        document = copy.deepcopy(tool_contract)
        # The envelope oneOf belongs to the registry; validate only the raw tool input.
        document.pop("oneOf", None)
        document["$ref"] = f"#/$defs/{tool_name}"
    return Draft202012Validator(document, format_checker=FormatChecker())


def check_contracts() -> int:
    api = load_json(CONTRACTS / "openapi.json")
    tools = load_json(CONTRACTS / "tools.schema.json")
    examples = load_json(CONTRACTS / "examples.json")
    assert_local_refs(api, "OpenAPI")
    assert_local_refs(tools, "Tool schema")
    validate(api)
    Draft202012Validator.check_schema(tools)
    registry_names = {tool["name"] for tool in tools["x-mcp-tools"]}
    if registry_names != set(tools["$defs"]):
        raise ValueError("Tool registry and schema definitions differ")
    for tool in tools["x-mcp-tools"]:
        if tool["inputSchema"] != tools["$defs"][tool["name"]]:
            raise ValueError(f"Tool input schema drift: {tool['name']}")
    checked = 0
    seen = set()
    for example in examples["cases"]:
        if example["id"] in seen:
            raise ValueError(f"Duplicate example: {example['id']}")
        seen.add(example["id"])
        errors = list(example_validator(example, api, tools).iter_errors(example["request"]))
        if (not errors) != example["valid"]:
            detail = errors[0].message if errors else "unexpectedly accepted"
            raise ValueError(f"Example {example['id']}: {detail}")
        checked += 1
    return checked


if __name__ == "__main__":
    try:
        count = check_contracts()
    except (ValueError, KeyError) as exc:
        print(f"Contract check failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: OpenAPI, tool registry and {count} examples (schema checks only)")
