"""P4 — Long-term / task memory."""

from __future__ import annotations

from typing import Any, List


class TaskMemoryManager:
    async def add(self, **kwargs: Any) -> None:
        raise NotImplementedError("P4: store long-term memory")

    async def search(self, query: str, **kwargs: Any) -> List[Any]:
        raise NotImplementedError("P4: retrieve relevant memories")
