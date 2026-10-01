"""P5 — Planning and reflection."""

from __future__ import annotations

from typing import Any, List, Literal

from litellm import Field
from pydantic import BaseModel, Field

from my_agent.tools import tool


class Task(BaseModel):
    """A planned unit of work."""
    content: str=Field(description="任务内容")
    status: Literal["pending", "in_progress", "completed"]=Field(description="任务状态") 

    def __str__(self) -> str:
        if self.status == "pending":
            return f"[ ] {self.content}"
        elif self.status == "in_progress":
            return f"[>] **{self.content}**"
        elif self.status == "completed":
            return f"[x] ~~{self.content}~~"
        return self.content

@tool
async def create_tasks(context, tasks: List[Task]) -> str:
    """创建或者更新任务"""
    return "\n".join(str(Task.model_validate(t)) for t in tasks)

async def reflect(**kwargs: Any) -> Any:
    raise NotImplementedError("P5: reflection step after actions")
