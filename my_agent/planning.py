"""P5 — Planning and reflection."""

from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel


class Task(BaseModel):
    """A planned unit of work."""

    # TODO(P5): define task fields
    pass


async def create_tasks(**kwargs: Any) -> List[Task]:
    raise NotImplementedError("P5: ask LLM to decompose a goal into tasks")


async def reflect(**kwargs: Any) -> Any:
    raise NotImplementedError("P5: reflection step after actions")
