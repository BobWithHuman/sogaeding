"""Test-only safe shape/status observer around the unchanged product MCP bridge."""
import json
import runpy
import sys
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

host = Path(sys.argv[1])
original = urllib.request.OpenerDirector.open


def observed(self, request, *args, **kwargs):
    body = json.loads(request.data)
    record = {"endpoint": urllib.parse.urlparse(request.full_url).path, "method": body.get("method"), "keys": list(body), "params_keys": list(body.get("params", {}))}
    try:
        response = original(self, request, *args, **kwargs)
        record.update(status=response.status, content_type=response.headers.get("content-type"))
        return response
    except urllib.error.HTTPError as exc:
        record.update(status=exc.code)
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
        with (host.parent / "bridge-diagnostic.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps(record) + "\n")


urllib.request.OpenerDirector.open = observed
runpy.run_path(str(Path(__file__).with_name("hookgw_mcp.py")), run_name="__main__")
