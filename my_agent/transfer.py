"""P7 — Agent-to-agent transfer tool factory."""

from __future__ import annotations

from typing import Any, List
from my_agent.agent import Agent
from my_agent.context import ExecutionContext
from my_agent.tools import tool
from my_agent.tools.base import FunctionTool




def create_transfer_tool(target_agents: List[Agent]) -> FunctionTool:
    target_names = [agent.name for agent in target_agents]

    @tool
    def transfer_to_agent(context: ExecutionContext, agent_name:str) -> str:
        if agent_name not in target_names:
            return f"Error: '{agent_name}' is not valid. Available: {target_agents}"
        if context.transfer_to is None:
            context.transfer_to = agent_name
            return f"Transferring to {agent_name}"
        return f"Transfer already requested to {context.transfer_to}"
    return transfer_to_agent
