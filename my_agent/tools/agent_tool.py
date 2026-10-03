"""P7 — Treat another Agent as a tool."""

from __future__ import annotations

from typing import Any

from my_agent.agent import Agent
from my_agent.context import ExecutionContext


class AgentTool:
    """Wrap a specialist agent so a parent agent can call it as a tool."""

    def __init__(self, agent: Agent, **kwargs: Any):
        self.agent = agent
        self.kwargs = kwargs

    async def execute(self, context: ExecutionContext, **kwargs: Any) -> Any:
        request = kwargs['request']
        result = await self.agent.run(user_input=request, context=context)
        return result.output