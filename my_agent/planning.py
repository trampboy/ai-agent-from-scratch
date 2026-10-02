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
    """Create or update a task plan.
    WHEN TO USE:
    - Complex queries requiring multiple steps of research
    - Questions that need to combine information from different sources
    WHEN NOT TO USE:
    - Simple questions answerable with a single search
    - Tasks with obvious, straightforward procedures
    HOW TO USE:
    - Pass tasks as a list of objects, each with content and status
    - Regenerate the entire task list with updated statuses
    - Mark completed tasks as 'completed'
    - Mark the next task to work on as 'in_progress'
    - Keep future tasks as 'pending'
    """
    return "\n".join(str(Task.model_validate(t)) for t in tasks)

@tool
async def reflection(analysis, need_replan = False) -> str:
    if need_replan:
        return f"Reflection recorded(REPLAN NEEDED): {analysis}"
    return f"Reflection recorded: {analysis}"