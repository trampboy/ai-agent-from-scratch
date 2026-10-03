"""P7 — Run agents one after another."""

from __future__ import annotations

from typing import Any, List

from my_agent import Agent
from my_agent.context import ExecutionContext, AgentResult



class SequentialWorkflow:
    def __init__(self, agents: List[Agent]):
        self.agents = agents

    async def run(self, user_input: str, **kwargs: Any) -> AgentResult:
        is_first_agent = True
        context = ExecutionContext()
        result = None
        for agent in self.agents:
            if is_first_agent:
                result = await agent.run(user_input=user_input, context=context, **kwargs)
                is_first_agent = False
            else:
                context.final_result = None
                context.current_step = 0
                result = await agent.run(context=context)
        return result



            
