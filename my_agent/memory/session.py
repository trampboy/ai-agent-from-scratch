"""P4 — Session management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSessionManager(ABC):
    @abstractmethod
    async def get_or_create(self, session_id: str, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def save(self, session: Any, **kwargs: Any) -> None:
        raise NotImplementedError
