"""P7 — Run agents one after another."""

from __future__ import annotations

from typing import Any, List


class SequentialWorkflow:
    def __init__(self, agents: List[Any]):
        self.agents = agents

    async def run(self, user_input: str, **kwargs: Any) -> Any:
        raise NotImplementedError("P7: sequential agent pipeline")
