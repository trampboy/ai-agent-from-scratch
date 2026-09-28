"""P2 — MCP tool bridge (optional)."""

from __future__ import annotations

from typing import Any, List


async def load_mcp_tools(**kwargs: Any) -> List[Any]:
    raise NotImplementedError("P2: connect to MCP server and wrap tools")
