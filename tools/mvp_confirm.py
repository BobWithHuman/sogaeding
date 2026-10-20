"""Separate human terminal: exact candidate review, human auth, no actor/model call."""
import argparse
import importlib.util
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def channel():
    spec = importlib.util.spec_from_file_location("confirm_human_channel", Path(__file__).with_name("hookgw_hook.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send


def terminal(value):
    text = json.dumps(value, ensure_ascii=False, indent=2)
    return "".join(c if c == "\n" or not unicodedata.category(c).startswith("C") else "\\u%04x" % ord(c) for c in text)


def guarded_host(path):
    host = Path(path).absolute()
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (host, *host.parents)):
        raise ValueError("HUMAN_HOST_REJECTED")
    host = host.resolve()
    default = ROOT / "artifacts/runtime-mvp-demo/host"
    behavior = ROOT / "artifacts/runtime-mvp-demo/revisions/behavior-v5-1/host"
    fixture = ROOT / "artifacts"
    relative = host.relative_to(fixture) if host.is_relative_to(fixture) else None
    if host not in (default, behavior) and (relative is None or not relative.parts[0].startswith("20261017-mvp-semantic-")):
        raise ValueError("HUMAN_HOST_REJECTED")
    profile = json.loads((host / "profile.json").read_text(encoding="utf-8-sig"))
    url = urlsplit(profile["control_url"])
    if url.scheme != "https" or url.hostname != "127.0.0.1" or not url.port or url.path or url.query or url.fragment or url.username:
        raise ValueError("HUMAN_HOST_REJECTED")
    return host


def pending_rows(value):
    if (not isinstance(value, dict) or set(value) != {"version", "pending", "truncated"}
            or value["version"] != "demo-confirm-1" or not isinstance(value["pending"], list)
            or len(value["pending"]) > 8 or type(value["truncated"]) is not bool):
        raise ValueError("PENDING_RESPONSE_INVALID")
    for row in value["pending"]:
        if (not isinstance(row, dict) or set(row) != {"call", "approval_binding", "candidate", "request", "source_excerpts", "uncertainty", "expires_at"}
                or not isinstance(row["call"], str) or not 1 <= len(row["call"]) <= 1024
                or not isinstance(row["approval_binding"], str) or not re.fullmatch(r"[a-f0-9]{64}", row["approval_binding"])
                or not isinstance(row["candidate"], dict) or len(json.dumps(row).encode()) > 100000):
            raise ValueError("PENDING_RESPONSE_INVALID")
    return value["pending"]


def review_once(host, *, input_fn=input, output_fn=print, send=None, quiet_empty=False):
    send = send or channel()
    response = send(host, "/demo/pending", {}, human=True, method="GET", timeout=5)
    rows = pending_rows(response)
    if not rows:
        if not quiet_empty:
            output_fn("No pending PDP confirmation. No approval, model call or tool execution was made.")
        return "NONE"
    if response["truncated"]:
        output_fn("Only the bounded pending list is shown; each selection is reviewed separately.")
    for i, row in enumerate(rows, 1):
        candidate = row["candidate"]
        output_fn(terminal({"number": i, "tool": candidate.get("tool"), "target": candidate.get("args", {}).get("path")}))
    answer = input_fn("Choose a candidate number, or Enter to cancel: ").strip()
    if not answer:
        return "CANCELLED"
    if not answer.isascii() or not answer.isdigit() or not 1 <= int(answer) <= len(rows):
        raise ValueError("SELECTION_INVALID")
    row = rows[int(answer)-1]
    output_fn("PDP CONFIRM is still uncertain. Host Allow is separate. Review the complete exact candidate and evidence:")
    output_fn(terminal({k: row[k] for k in ("candidate", "request", "source_excerpts", "uncertainty", "expires_at")}))
    decision = input_fn("Type approve or reject for ONLY this exact candidate; Enter cancels: ").strip().lower()
    if decision not in {"approve", "reject"}:
        return "CANCELLED"
    result = send(host, "/approval", {"call": row["call"], "approve": decision == "approve", "approval_binding": row["approval_binding"]}, human=True, timeout=5)
    if not isinstance(result, dict) or result.get("state") not in {"APPROVED", "DENIED", "REJECTED"}:
        raise ValueError("APPROVAL_RESPONSE_INVALID")
    outcome = "The original waiting MCP call may resume once; no new model call is made here." if result["state"] == "APPROVED" else "The waiting call stops. No execution, implicit approval or actor retry is permitted."
    output_fn("PDP confirmation: " + result["state"] + ". " + outcome)
    return result["state"]


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--host", type=Path, default=ROOT / "artifacts/runtime-mvp-demo/host")
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    try:
        host = guarded_host(args.host)
        deadline = time.monotonic() + (600 if args.watch else 0)
        if args.watch:
            print("Waiting up to 600 seconds for a PDP confirmation. No approval or model call is made while waiting.")
        while True:
            status = review_once(host, quiet_empty=args.watch)
            if status != "NONE" or time.monotonic() >= deadline:
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        print("Human review interrupted. A submitted choice may have been recorded; inspect history. No implicit approval or retry.")
        return 130
    except Exception:
        print("HUMAN_CONFIRM_UNAVAILABLE_OR_BINDING_REJECTED. A submitted choice may have been recorded; inspect history. Do not retry the actor action.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
