"""P2 — Web search tool (Tavily)."""

from __future__ import annotations

from typing import Any
import os
from tavily import TavilyClient


async def search(query: str, **kwargs: Any) -> Any:
    """Search the web and return results usable by the agent."""
    try:
        client = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
        results = client.search(query=query, num_results=5, topic="general")
        return results.get("results", [])
    except Exception as e:
        raise RuntimeError(f"Error: {e}")
