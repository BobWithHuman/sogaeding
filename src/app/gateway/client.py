"""No redirects, environment proxy inheritance, HTTP, or retry for risk writes."""
import os

import httpx

from app.common import SafeError, secret_file, tls_context, validate


class ControlClient:
    def __init__(self):
        self.url = os.getenv("CONTROL_BASE_URL", "https://control:8443")
        if self.url != "https://control:8443" and self.url != "https://127.0.0.1:8443":
            raise ValueError("Control must use the configured mTLS endpoint")

    async def post(self, path, payload, schema):
        try:
            async with httpx.AsyncClient(verify=tls_context(client=True), trust_env=False,
                                         timeout=25 if path=='/internal/checks' else 1, follow_redirects=False) as client:
                response = await client.post(self.url + path, json=payload,
                    headers={"Authorization": "Bearer " + secret_file("service.token")})
                if not 200 <= response.status_code < 300:
                    # Error code is an allowlisted identifier, never reflect an arbitrary response.
                    codes = {x for x in __import__("app.common", fromlist=["API"]).API[
                        "components"]["schemas"]["CheckReply"]["properties"]["reason_codes"]["items"]["enum"]}
                    error = response.json()
                    value = error.get("code") if isinstance(error, dict) else None
                    raise SafeError(value if isinstance(value, str) and value in codes else "PDP_UNAVAILABLE", 503)
                value = response.json()
                try:
                    validate(schema, value)
                except SafeError as exc:
                    raise SafeError("PDP_UNAVAILABLE", 503) from exc
                return value
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise SafeError("PDP_UNAVAILABLE", 503) from exc
