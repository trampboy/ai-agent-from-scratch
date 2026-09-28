"""P7 — Simple A2A server / executor stub."""

from __future__ import annotations

from typing import Any


class MathAgentExecutor:
    """Example remote agent executor (math specialist)."""

    async def execute(self, **kwargs: Any) -> Any:
        raise NotImplementedError("P7: handle incoming A2A task")
