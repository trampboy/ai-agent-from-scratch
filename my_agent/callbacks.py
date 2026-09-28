"""P3 — Callbacks (approval, search compression, etc.)."""

from __future__ import annotations

from typing import Any


async def approval_callback(**kwargs: Any) -> Any:
    raise NotImplementedError("P3/P4: tool approval callback")


async def search_compressor(**kwargs: Any) -> Any:
    raise NotImplementedError("P3: compress search results before LLM sees them")
