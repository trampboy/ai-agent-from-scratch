"""P7 — Loop workflow (retry / until condition)."""

from __future__ import annotations

from typing import Any, Callable, Optional, List
from my_agent import Agent
from my_agent.context import ExecutionContext, AgentResult

class LoopWorkflow:
    def __init__(self, agents: List[Agent], stop_condition: Optional[Callable] = None, max_iterations: int = 5, name: str = None):
        self.agents = agents
        self.stop_condition = stop_condition
        self.max_iters = max_iterations
        self.name = name

    async def run(self, user_input: str, context: ExecutionContext | None = None, **kwargs: Any) -> Any:
        if context is None:
            context = ExecutionContext()

        is_first_agent = True
        for iteration in range(1, self.max_iters + 1):
            for agent in self.agents:
                if is_first_agent:
                    result = await agent.run(user_input=user_input, context=context, **kwargs)
                else:
                    result = await agent.run(context=context, **kwargs)
                context = result.context
            if result and self.stop_condition and self.stop_condition(result, iteration):
                return result
        return result

