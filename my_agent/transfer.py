"""P7 — Agent-to-agent transfer tool factory."""

from __future__ import annotations

from typing import Any


def create_transfer_tool(**kwargs: Any) -> Any:
    raise NotImplementedError("P7: build a tool that sets context.transfer_to")
