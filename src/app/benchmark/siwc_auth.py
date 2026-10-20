"""Official SIWC public-client OAuth. No Codex credentials or API-key fallback.

Runs only in the protected helper/provider broker. Linux owner-only files plus
the launcher's Windows owner-only directory ACL protect the dedicated mount.
"""

import base64
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

import httpx
import jwt

from app.benchmark.runtime_budget import StopRun
from app.common import canonical, digest

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
TOKEN = ISSUER + "/api/accounts/oauth/token"
SCOPES = {
    "openid",
    "profile",
    "email",
    "offline_access",
    "resource.invoke",
    "chatgpt.tokens.use.direct",
}
MODEL = "gpt-5.6-luna"
EFFORT = "low"


class Credentials:
    def __init__(self, root=Path("/credentials"), account="main", *, transport=None):
        if not re.fullmatch(r"[a-z0-9-]{1,32}", account):
            raise StopRun("SIWC_ACCOUNT_LABEL_INVALID")
        self.root, self.account, self.transport = Path(root), account, transport
        if self.root.is_symlink():
            raise StopRun("SIWC_CREDENTIAL_SYMLINK")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.root / (account + ".json")
        self.verify_path(self.root, directory=True)

    def verify_path(self, path, *, directory=False):
        if path.is_symlink():
            raise StopRun("SIWC_CREDENTIAL_SYMLINK")
        if path.exists() and not os.getenv("DTAP_WINDOWS_HOST_ACL"):
            s = path.stat()
            if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) & 0o077:
                raise StopRun("SIWC_OWNER_ONLY_STORAGE_REQUIRED")
        if path.exists() and (not path.is_dir() if directory else not path.is_file()):
            raise StopRun("SIWC_CREDENTIAL_TYPE_INVALID")

    def read(self, path):
        self.verify_path(path)
        if not path.exists():
            raise StopRun("SIWC_LOGIN_REQUIRED_NO_API_FALLBACK")
        return json.loads(path.read_text())

    def write(self, path, value):
        self.verify_path(path)
        temp = self.root / (".pending-" + secrets.token_hex(12))
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(canonical(value))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    @contextmanager
    def lock(self):
        path = self.root / "credentials.lock"
        self.verify_path(path)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def client(self):
        return httpx.Client(
            transport=self.transport, trust_env=False, follow_redirects=False, timeout=20
        )

    def get(self, url, **kwargs):
        with self.client() as client:
            response = client.get(url, **kwargs)
        if response.status_code != 200 or len(response.content) > 1048576:
            raise StopRun("SIWC_METADATA_HTTP_REJECTED")
        return response.json()

    def discovery(self):
        value = self.get(ISSUER + "/.well-known/openid-configuration")
        if (
            value.get("issuer") != ISSUER
            or value.get("token_endpoint") != TOKEN
            or value.get("authorization_endpoint") != ISSUER + "/api/accounts/authorize"
            or value.get("jwks_uri") != ISSUER + "/.well-known/jwks.json"
            or value.get("revocation_endpoint") != ISSUER + "/api/accounts/oauth/revoke"
        ):
            raise StopRun("SIWC_DISCOVERY_BINDING_INVALID")
        return value

    def identity(self, token, client_id, nonce=None):
        self.discovery()
        keys = self.get(ISSUER + "/.well-known/jwks.json")["keys"]
        header = jwt.get_unverified_header(token)
        key = next(
            (
                k
                for k in keys
                if k.get("kid") == header.get("kid")
                and k.get("kty") == "RSA"
                and k.get("alg", "RS256") == "RS256"
                and k.get("use", "sig") == "sig"
            ),
            None,
        )
        if (
            header.get("alg") != "RS256"
            or not isinstance(header.get("kid"), str)
            or not header["kid"]
            or not key
        ):
            raise StopRun("SIWC_ID_SIGNATURE_REJECTED")
        value = jwt.decode(
            token,
            jwt.PyJWK.from_dict(key).key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        if (
            not isinstance(value["sub"], str)
            or not value["sub"]
            or value.get("azp", client_id) != client_id
            or isinstance(value["aud"], list)
            and len(value["aud"]) > 1
            and value.get("azp") != client_id
            or nonce is not None
            and not hmac.compare_digest(value.get("nonce", ""), nonce)
        ):
            raise StopRun("SIWC_ID_NONCE_OR_SUBJECT_REJECTED")
        return value["sub"]

    def post_token(self, body):
        with self.client() as client:
            response = client.post(TOKEN, data=body)
        if response.status_code != 200 or len(response.content) > 65536:
            raise StopRun("SIWC_REAUTH_REQUIRED_NO_API_FALLBACK")
        return response.json()

    def tokens(self, value, client_id, subject, old=None):
        scopes = set(value.get("scope", " ".join((old or {}).get("scopes", []))).split())
        if (
            not SCOPES <= scopes
            or value.get("token_type", "").casefold() != "bearer"
            or any(
                not isinstance(value.get(k), str) or not value[k]
                for k in ("access_token", "refresh_token")
            )
            or type(value.get("expires_in")) is not int
            or not 0 < value["expires_in"] <= 86400
        ):
            raise StopRun("SIWC_PLAN_PERMISSION_OR_TOKEN_INVALID")
        return {
            "client_id": client_id,
            "subject": subject,
            "scopes": sorted(scopes),
            "access_token": value["access_token"],
            "refresh_token": value["refresh_token"],
            "id_token": value.get("id_token", (old or {}).get("id_token")),
            "expires_at": time.time() + value["expires_in"],
            "earliest_refresh_at": value.get("earliest_refresh_at", 0),
        }

    def registration(self):
        return self.read(self.root / (self.account + "-registration.json"))

    def metadata(self):
        r = self.registration()
        return {
            "account_label": self.account,
            "account_binding_sha256": digest(
                canonical({"client_id": r["client_id"], "subject": r["subject"]})
            ),
        }

    def access(self):
        with self.lock():
            value = self.read(self.path)
            r = self.registration()
            if (value.get("client_id"), value.get("subject")) != (r["client_id"], r["subject"]):
                raise StopRun("SIWC_ACCOUNT_BINDING_CHANGED")
            if value["expires_at"] <= time.time() + 120:
                if value.get("earliest_refresh_at", 0) > time.time():
                    raise StopRun("SIWC_REFRESH_NOT_YET_ALLOWED")
                response = self.post_token(
                    {
                        "grant_type": "refresh_token",
                        "client_id": r["client_id"],
                        "refresh_token": value["refresh_token"],
                        "resource": RESOURCE,
                    }
                )
                if (
                    response.get("id_token")
                    and self.identity(response["id_token"], r["client_id"]) != r["subject"]
                ):
                    raise StopRun("SIWC_REFRESH_IDENTITY_CHANGED")
                value = self.tokens(response, r["client_id"], r["subject"], value)
                self.write(self.path, value)
            return value["access_token"]

    def models(self):
        value = self.get(RESOURCE + "/models", headers={"Authorization": "Bearer " + self.access()})
        models = value.get("models")
        if not isinstance(models, list):
            raise StopRun("SIWC_ACCOUNT_CATALOG_INVALID")
        target = next(
            (m for m in models if m.get("slug") == MODEL and m.get("visibility") == "list"), None
        )
        if not target:
            raise StopRun("SIWC_LUNA_NOT_AVAILABLE_NO_SUBSTITUTION")
        levels = target.get("supported_reasoning_levels")
        if levels is not None and not any(
            (level == EFFORT or isinstance(level, dict) and level.get("effort") == EFFORT)
            for level in levels
        ):
            raise StopRun("SIWC_LOW_NOT_AVAILABLE_NO_SUBSTITUTION")
        result = {
            **self.metadata(),
            "model": MODEL,
            "reasoning_effort": EFFORT,
            "model_catalog_checked_at": time.time(),
            "inference": "NOT_RUN",
            "billing": "chatgpt-plan",
            "plan_remaining": "UNKNOWN",
        }
        self.write(self.root / (self.account + "-model-check.json"), result)
        return result

    def sign_in(self, port=1459):
        """Foreground helper; opens no browser itself, callback never logs URLs."""
        rpath = self.root / (self.account + "-registration.json")
        pending_path = self.root / (self.account + "-pending-client.json")
        hostpath = self.root / "host.json"
        with self.lock():
            if not hostpath.exists():
                if rpath.exists() or pending_path.exists():
                    raise StopRun("SIWC_HOST_ID_MISSING_NO_REREGISTRATION")
                self.write(hostpath, {"host_id": "urn:uuid:" + str(uuid4())})
            host = self.read(hostpath)["host_id"]
            if not isinstance(host, str) or not re.fullmatch(r"urn:uuid:[0-9a-f-]{36}", host):
                raise StopRun("SIWC_HOST_ID_INVALID")
            registered = self.read(rpath) if rpath.exists() else None
            pending = self.read(pending_path) if pending_path.exists() else None
            saved = registered or pending
        state, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(3))
        redirect = f"http://127.0.0.1:{port}/auth/callback"
        query = {
            "client_id": saved["client_id"] if saved else "dynamic_agent_client",
            "ext_agent_host_id": host,
            "response_type": "code",
            "redirect_uri": redirect,
            "scope": " ".join(sorted(SCOPES)),
            "resource": RESOURCE,
            "state": state,
            "nonce": nonce,
            "code_challenge_method": "S256",
            "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("="),
        }
        if not saved:
            query["agent_name_hint"] = "With Human DTAP"
        outcome = []

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(handler):
                url = urlsplit(handler.path)
                values = parse_qs(url.query, keep_blank_values=True)
                valid = (
                    url.path == "/auth/callback"
                    and handler.headers.get("Host") == f"127.0.0.1:{port}"
                    and all(len(v) == 1 for v in values.values())
                    and hmac.compare_digest(values.get("state", [""])[0], state)
                )
                handler.send_response(200 if valid else 400)
                handler.end_headers()
                handler.wfile.write(
                    b"Continue in With Human DTAP." if valid else b"Invalid callback."
                )
                if valid:
                    outcome.append({k: v[0] for k, v in values.items()})

        # Container port is published on host 127.0.0.1 only by the launcher.
        with HTTPServer(("0.0.0.0", port), Callback) as server:
            server.timeout = 1
            self.write(
                self.root / "authorization-url.json",
                {"url": ISSUER + "/api/accounts/authorize?" + urlencode(query)},
            )
            deadline = time.monotonic() + 300
            while not outcome and time.monotonic() < deadline:
                server.handle_request()
        (self.root / "authorization-url.json").unlink(missing_ok=True)
        if not outcome:
            raise StopRun("SIWC_LOGIN_TIMEOUT")
        values = outcome[0]
        if values.get("error"):
            raise StopRun("SIWC_CONSENT_DECLINED")
        client_id = values.get("client_id", saved["client_id"] if saved else "")
        if (
            not re.fullmatch(r"oaiapp_[A-Za-z0-9_-]+", client_id)
            or saved
            and client_id != saved["client_id"]
            or not values.get("code")
        ):
            raise StopRun("SIWC_CALLBACK_CLIENT_INVALID")
        # An issued registration survives exchange/validation failure. Retrying
        # sign-in must not allocate a new client to sidestep account limits.
        if not registered:
            with self.lock():
                self.write(pending_path, {"client_id": client_id})
        response = self.post_token(
            {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": values["code"],
                "code_verifier": verifier,
                "redirect_uri": redirect,
                "resource": RESOURCE,
            }
        )
        subject = self.identity(response["id_token"], client_id, nonce)
        if registered and subject != registered["subject"]:
            raise StopRun("SIWC_ACCOUNT_SWITCH_REQUIRES_SEPARATE_LABEL")
        tokens = self.tokens(response, client_id, subject)
        with self.lock():
            self.write(rpath, {"client_id": client_id, "subject": subject})
            self.write(self.path, tokens)
            pending_path.unlink(missing_ok=True)
        return self.metadata()

    def revoke(self):
        confirmed = False
        with self.lock():
            value = self.read(self.path)
            endpoint = self.discovery()["revocation_endpoint"]
            try:
                with self.client() as client:
                    response = client.post(
                        endpoint,
                        data={
                            "token": value["refresh_token"],
                            "token_type_hint": "refresh_token",
                            "client_id": value["client_id"],
                        },
                    )
                confirmed = response.status_code == 200
            except httpx.HTTPError:
                pass
            self.path.unlink(missing_ok=True)
            (self.root / (self.account + "-model-check.json")).unlink(missing_ok=True)
        return {
            "local_tokens_cleared": True,
            "remote_revocation_confirmed": confirmed,
            "registration_and_host_preserved": True,
        }
