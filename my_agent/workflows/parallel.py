"""P7 — Run agents in parallel."""

from __future__ import annotations

from typing import Any, List


class ParallelWorkflowIncomplete(Exception):
    """Raised when a parallel branch fails or awaits approval."""

    def __init__(self, branch_results: dict, branch_errors: dict):
        self.branch_results = branch_results
        self.branch_errors = branch_errors
        super().__init__("parallel workflow incomplete")


class ParallelWorkflow:
    def __init__(self, agents: List[Any]):
        self.agents = agents

    async def run(self, user_input: str, **kwargs: Any) -> Any:
        raise NotImplementedError("P7: fan-out / fan-in parallel agents")
