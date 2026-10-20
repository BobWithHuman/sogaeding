"""Two verified TLS listeners in the one Control service; internal requires mTLS."""
import asyncio
import os
import ssl

import uvicorn

from app.common import RUNTIME
from app.control.main import app


async def main():
    public = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("CONTROL_PORT", "8000")),
                            ssl_certfile=str(RUNTIME / "control.pem"),
                            ssl_keyfile=str(RUNTIME / "control.key"), access_log=False,
                            proxy_headers=False, log_level="critical")
    internal = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("INTERNAL_PORT", "8443")),
                              ssl_certfile=str(RUNTIME / "control.pem"),
                              ssl_keyfile=str(RUNTIME / "control.key"),
                              ssl_ca_certs=str(RUNTIME / "ca.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED,
                              access_log=False, proxy_headers=False, log_level="critical")
    await asyncio.gather(uvicorn.Server(public).serve(), uvicorn.Server(internal).serve())


if __name__ == "__main__":
    asyncio.run(main())
