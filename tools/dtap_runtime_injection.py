"""Execute the original injection server using the reviewed MCP SDK adapter."""

import runpy
import sys

from app.benchmark.mcp_compat import module

sys.modules["fastmcp"] = module()
runpy.run_path("/official-injection.py", run_name="__main__")
