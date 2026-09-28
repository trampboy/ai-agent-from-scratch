"""P7 — Loop workflow (retry / until condition)."""

from __future__ import annotations

from typing import Any, Callable, Optional


class LoopWorkflow:
    def __init__(self, agent: Any, should_continue: Optional[Callable] = None, max_iters: int = 5):
        self.agent = agent
        self.should_continue = should_continue
        self.max_iters = max_iters

    async def run(self, user_input: str, **kwargs: Any) -> Any:
        raise NotImplementedError("P7: loop until stop condition or max_iters")
