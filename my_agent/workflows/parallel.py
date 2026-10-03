"""P7 — Run agents in parallel."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, List
import asyncio

from my_agent import Agent, AgentResult
from my_agent.context import ExecutionContext


class ParallelWorkflowIncomplete(Exception):
    """Raised when a parallel branch fails or awaits approval."""

    def __init__(self, branch_results: dict, branch_errors: dict):
        self.branch_results = branch_results
        self.branch_errors = branch_errors
        super().__init__("parallel workflow incomplete")


class ParallelWorkflow:
    def __init__(self, agents: List[Agent]):
        self.agents = agents

    async def run(self, user_input: str, context: ExecutionContext | None = None, **kwargs: Any) -> Any:
        seed = context or ExecutionContext()
        existing_event_count = len(seed.events)

        branches = [
            ExecutionContext(events=deepcopy(seed.events), state=deepcopy(seed.state))
            for _ in self.agents
        ]

        branch_results = await asyncio.gather(
            *[  
                agent.run(user_input=user_input, context=branch, **kwargs)
                for agent, branch in zip(self.agents, branches)
            ],
            return_exceptions=True
        )

        branch_errors = []
        merged_output = []
        merged_events = []
        for result in branch_results:
            if not result.status == 'complete':
                branch_errors.append(result.output)
                

        if branch_errors:
            raise ParallelWorkflowIncomplete(branch_results=branch_results, branch_errors=branch_errors)

        merged_output = []
        merged_events = deepcopy(seed.events)
        for agent, branch_result in zip(self.agents, branch_results):
            merged_output.append(f"[{agent.name}]")
            merged_output.append(f"{branch_result.output}")
            merged_events.append(branch_result.context.events[existing_event_count:])
        return AgentResult(context=ExecutionContext(events=merged_events), output="\n".join(merged_output), status='complete')
        
        


        
        



