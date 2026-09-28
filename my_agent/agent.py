"""P1 — ReAct agent loop.

Grow this class across phases (callbacks, session, memory, skills, transfer).
Start with: tools + instructions + max_steps + run().
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Type

from pydantic import BaseModel

from my_agent.context import AgentResult
from my_agent.llm import LlmClient


class Agent:
    """Tool-calling agent with a ReAct loop."""

    def __init__(
        self,
        model: LlmClient,
        tools: List[Any] | None = None,
        instructions: str = "",
        max_steps: int = 10,
        name: str = "agent",
        description: str = "",
        output_type: Optional[Type[BaseModel]] = None,
        before_tool_callbacks: list[Callable] | None = None,
        after_tool_callbacks: list[Callable] | None = None,
        session_manager: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        before_llm_callbacks: list[Callable] | None = None,
        code_execution: str | None = None,
        skills_path: str | None = None,
        **kwargs: Any,
    ):
        self.model = model
        self.tools = tools or []
        self.instructions = instructions
        self.max_steps = max_steps
        self.name = name
        self.description = description
        self.output_type = output_type
        self.before_tool_callbacks = before_tool_callbacks or []
        self.after_tool_callbacks = after_tool_callbacks or []
        self.session_manager = session_manager
        self.memory_manager = memory_manager
        self.before_llm_callbacks = before_llm_callbacks or []
        self.code_execution = code_execution
        self.skills_path = skills_path
        self.kwargs = kwargs

    async def run(self, user_input: str, **kwargs: Any) -> AgentResult:
        """Execute the ReAct loop until final answer or max_steps."""
        raise NotImplementedError("P1: implement ReAct loop")
