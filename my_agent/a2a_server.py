"""P7 — Simple A2A server / executor stub."""

from __future__ import annotations

from typing import Any

from my_agent.agent import Agent


class MathAgentExecutor:
    """Example remote agent executor (math specialist)."""
    def __init__(self, agent: Agent):
        self.agent = agent

    async def execute(self, context, **kwargs: Any) -> Any:
        text = context.message["parts"]
        result = await self.agent.run(user_input=text, context=context)
        return {
            "type": "artifact",
            "parts": [{"type": "text", "text": str(result.output)}]
        }

        
