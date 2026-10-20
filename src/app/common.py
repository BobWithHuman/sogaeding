"""Shared strict wire validation, masking, TLS and safe errors."""
import hashlib
import json
import os
import re
import ssl
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from jsonschema import Draft202012Validator, FormatChecker

SPEC = "MVP-SPEC-4"
POLICY = "mvp-2026-10-14-f3-v2"
AUDIENCE = "https://127.0.0.1:8001/mcp"
CONTRACT_DIR = Path(os.getenv("CONTRACT_DIR", "/workspace/docs/mvp/contracts"))
API = json.loads((CONTRACT_DIR / "openapi.json").read_text(encoding="utf-8"))
TOOLS = json.loads((CONTRACT_DIR / "tools.schema.json").read_text(encoding="utf-8"))
RUNTIME = Path(os.getenv("RUNTIME_DIR", "/runtime"))


class SafeError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


def uid():
    return str(uuid4())


def stamp(value=None):
    return datetime.fromtimestamp(value, UTC).isoformat() if value is not None else datetime.now(UTC).isoformat()


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def action(tool, args, backend="demo.v1"):
    return canonical({"tool_name": tool, "backend_id": backend, "args": args})


def secret_file(label):
    return (RUNTIME / label).read_text(encoding="ascii").strip()


def cipher():
    return Fernet(secret_file("storage.key").encode())


def sensitive(text):
    return mask(text) != text


def mask(text):
    value = str(text)
    markers = ["DEMO_SECRET_DO_NOT_SEND", "DEMO_SECRET"]
    markers.extend(secret_file(name) for name in ("service.token", "human.token", "judge.api-key") if (RUNTIME / name).exists())
    for marker in markers:
        value = value.replace(marker, "[REDACTED]")
    value = re.sub(r"(?i)(?:bearer\s+|sk-)[a-z0-9_\-]{16,}", "[REDACTED]", value)
    value = re.sub(r"(?i)((?:api[_-]?key|password|secret|token)\s*[:=]\s*)[^\s,;]+",
                   r"\1[REDACTED]", value)
    value = re.sub(r"\b[A-Za-z0-9_-]{40,}\b", "[REDACTED]", value)
    return value


def masked_tree(value):
    if isinstance(value, str):
        return mask(value)
    if isinstance(value, dict):
        return {key: masked_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [masked_tree(item) for item in value]
    return value


def validate(name, value):
    doc = dict(API)
    doc["$ref"] = f"#/components/schemas/{name}"
    if not Draft202012Validator(doc, format_checker=FormatChecker()).is_valid(value):
        raise SafeError("INVALID_ARGUMENTS", 422)


def validate_tool(tool, args):
    if tool not in TOOLS["$defs"]:
        raise SafeError("UNSUPPORTED_TOOL", 422)
    if not Draft202012Validator(TOOLS["$defs"][tool], format_checker=FormatChecker()).is_valid(args):
        raise SafeError("INVALID_ARGUMENTS", 422)


def strict_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate key")
            out[key] = value
        return out
    def invalid_constant(_):
        raise ValueError("invalid constant")
    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)
        pending = [(result, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 16:
                raise ValueError("depth")
            if isinstance(item, dict):
                pending.extend((x, depth + 1) for x in item.values())
            elif isinstance(item, list):
                pending.extend((x, depth + 1) for x in item)
        return result
    except (ValueError, RecursionError, UnicodeDecodeError) as exc:
        raise SafeError("INVALID_ARGUMENTS", 422) from exc


def tls_context(client=False):
    ctx = ssl.create_default_context(cafile=str(RUNTIME / "ca.pem"))
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    if client:
        ctx.load_cert_chain(str(RUNTIME / "gateway-client.pem"), str(RUNTIME / "gateway-client.key"))
    return ctx
