"""Shared response hardening; preserve a route's explicit browser CSP."""
from starlette.datastructures import MutableHeaders


def apply_security_headers(headers, *, https):
    defaults = {
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    }
    if https:
        defaults["Strict-Transport-Security"] = "max-age=31536000"
    for key, value in defaults.items():
        headers.setdefault(key, value)


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        async def hardened(message):
            if message["type"] == "http.response.start":
                apply_security_headers(MutableHeaders(scope=message), https=scope.get("scheme") == "https")
            await send(message)
        return await self.app(scope, receive, hardened)
