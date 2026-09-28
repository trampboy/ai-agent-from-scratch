"""P7 — Treat another Agent as a tool."""

from __future__ import annotations

from typing import Any


class AgentTool:
    """Wrap a specialist agent so a parent agent can call it as a tool."""

    def __init__(self, agent: Any, **kwargs: Any):
        self.agent = agent
        self.kwargs = kwargs

    async def execute(self, context: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("P7: invoke nested agent and return result")
