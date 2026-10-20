"""Test-only metadata observer around unchanged product hook logic."""
import json
import sys
import urllib.error
from pathlib import Path

import hookgw_hook

host = Path(sys.argv[1])
original = hookgw_hook.send


def observed(profile, endpoint, body, *args, **kwargs):
    record = {"endpoint": endpoint, "event": body.get("event"), "session": body.get("session"),
              "turn": body.get("turn"), "call": body.get("call"), "tool": body.get("tool"), "route": body.get("route")}
    try:
        result = original(profile, endpoint, body, *args, **kwargs)
        record.update({key: result[key] for key in ("state", "decision", "reason", "code") if key in result})
        return result
    except urllib.error.HTTPError as exc:
        record["status"] = exc.code
        try:
            code = json.loads(exc.read(1024)).get("code")
            if isinstance(code, str) and code.isupper() and len(code) < 80:
                record["safe_code"] = code
        except Exception:
            pass
        raise
    except Exception as exc:
        record["error_type"] = type(exc).__name__
        raise
    finally:
        with (host.parent / "hook-diagnostic.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps(record) + "\n")


hookgw_hook.send = observed
hookgw_hook.main()
