"""Small SDK transport adapter for pinned official FastMCP API calls.

This is real MCP over HTTP, not a result stub. Avoids installing the old
FastMCP 2.x release with known advisories merely for its Client import.
"""

from contextlib import AsyncExitStack
from types import ModuleType

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP as SDKFastMCP


class Client:
    def __init__(self, url, timeout=30.0):
        self.url, self.timeout = url, timeout

    async def __aenter__(self):
        self.stack = AsyncExitStack()
        streams = await self.stack.enter_async_context(streamablehttp_client(self.url))
        self.session = await self.stack.enter_async_context(ClientSession(streams[0], streams[1]))
        await self.session.initialize()
        return self

    async def call_tool(self, name, arguments):
        return await self.session.call_tool(name, arguments)

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)


class FastMCP(SDKFastMCP):
    def run(self, transport="http", host="localhost", port=8873):
        if transport != "http":
            raise ValueError("OFFICIAL_HTTP_INJECTION_ONLY")
        self.settings.host = host
        self.settings.port = port
        self.settings.stateless_http = True
        return super().run(transport="streamable-http")


def module():
    shim = ModuleType("fastmcp")
    shim.Client = Client
    shim.FastMCP = FastMCP
    return shim
