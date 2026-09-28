"""P7 — Remote agent client (A2A)."""

from __future__ import annotations

from typing import Any


class RemoteAgent:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def send(self, message: str, **kwargs: Any) -> Any:
        raise NotImplementedError("P7: call remote A2A endpoint")
