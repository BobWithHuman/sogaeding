"""Independent TLS fixture gate, deliberately separate from product transport."""
import asyncio
import importlib.util
import ssl

import httpx
import httpx2
import pytest


def prepare(path):
    spec = importlib.util.spec_from_file_location("prepare_tls", "/workspace/tools/prepare_tls.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(path)


@pytest.mark.asyncio
async def test_tls_fixture_certificate_matrix(tmp_path):
    directory = tmp_path / "pki"
    prepare(directory)
    trust = ssl.create_default_context(cafile=str(directory / "ca.pem"))

    async def serve(reader, writer):
        await reader.read(32768)
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()
        writer.close()

    for leaf, mtls in [("control", False), ("wrong-host", False), ("expired", False),
                       ("control", True)]:
        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        server_ctx.load_cert_chain(directory / f"{leaf}.pem", directory / f"{leaf}.key")
        if mtls:
            server_ctx.load_verify_locations(directory / "ca.pem")
            server_ctx.verify_mode = ssl.CERT_REQUIRED
        server = await asyncio.start_server(serve, "127.0.0.1", 0, ssl=server_ctx)
        port = server.sockets[0].getsockname()[1]
        try:
            for client_type in (httpx.AsyncClient, httpx2.AsyncClient):
                async with client_type(verify=trust, trust_env=False, timeout=1) as client:
                    if leaf == "control" and not mtls:
                        assert (await client.get(f"https://127.0.0.1:{port}")).text == "ok"
                    else:
                        with pytest.raises((httpx.HTTPError, httpx2.HTTPError)):
                            await client.get(f"https://127.0.0.1:{port}")
                async with client_type(trust_env=False, timeout=1) as client:
                    with pytest.raises((httpx.HTTPError, httpx2.HTTPError)):
                        await client.get(f"https://127.0.0.1:{port}")
            if mtls:
                mtls_trust = ssl.create_default_context(cafile=str(directory / "ca.pem"))
                mtls_trust.load_cert_chain(directory / "gateway-client.pem", directory / "gateway-client.key")
                async with httpx.AsyncClient(verify=mtls_trust, trust_env=False) as client:
                    assert (await client.get(f"https://127.0.0.1:{port}")).status_code == 200
                # A server-only EKU cert cannot impersonate the service client.
                wrong_client = ssl.create_default_context(cafile=str(directory / "ca.pem"))
                wrong_client.load_cert_chain(directory / "gateway.pem", directory / "gateway.key")
                async with httpx.AsyncClient(verify=wrong_client, trust_env=False, timeout=1) as client:
                    with pytest.raises(httpx.HTTPError):
                        await client.get(f"https://127.0.0.1:{port}")
        finally:
            server.close()
            await server.wait_closed()


@pytest.mark.asyncio
async def test_no_plaintext_tls_fallback(tmp_path):
    directory = tmp_path / "pki"
    prepare(directory)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(directory / "control.pem", directory / "control.key")
    arrivals = []

    async def handler(reader, writer):
        arrivals.append(True)
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 0, ssl=context)
    port = server.sockets[0].getsockname()[1]
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=1) as client:
            # Never transmit credentials on this deliberate plaintext negative test.
            with pytest.raises(httpx.HTTPError):
                await client.get(f"http://127.0.0.1:{port}/healthz")
        assert arrivals == []
    finally:
        server.close()
        await server.wait_closed()
