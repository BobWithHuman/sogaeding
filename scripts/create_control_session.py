"""Verified HTTPS session issuance for PowerShell 5 without global CA installation.

stdout is the one-time authorized response, consumed in memory by the launcher.
It must never be redirected to an evidence file.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request


def main():
    url, ca = sys.argv[1:3]
    if url != "https://127.0.0.1:8000":
        raise ValueError("Only the verified local Control endpoint is supported")
    context = ssl.create_default_context(cafile=ca)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    token = os.environ["HUMAN_USER_TOKEN"]
    payload = sys.stdin.buffer.read(32769)
    if len(payload) > 32768:
        raise ValueError("Request too large")
    request = urllib.request.Request(url + "/v1/sessions", data=payload, method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect,
                                         urllib.request.HTTPSHandler(context=context))
    with opener.open(request, timeout=3) as response:
        value = json.loads(response.read(32768))
    sys.stdout.write(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.URLError):
        print("Verified Control session creation failed", file=sys.stderr)
        sys.exit(1)
