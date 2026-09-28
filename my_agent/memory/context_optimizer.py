"""P4 — Context window optimization (summarize / truncate / compress)."""

from __future__ import annotations

from typing import Any


async def optimize_context(**kwargs: Any) -> Any:
    raise NotImplementedError("P4: shrink history before next LLM call")
