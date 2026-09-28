"""P4 — Memory tools exposed to the agent."""

from __future__ import annotations

from typing import Any


def remember(**kwargs: Any) -> Any:
    raise NotImplementedError("P4: store a memory item")


def recall(**kwargs: Any) -> Any:
    raise NotImplementedError("P4: retrieve memory items")
