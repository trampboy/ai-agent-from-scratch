"""P1 — ReAct agent loop.

Grow this class across phases (callbacks, session, memory, skills, transfer).
Start with: tools + instructions + max_steps + run().
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Type

from pydantic import BaseModel

from my_agent.context import AgentResult
from my_agent.llm import LlmClient, LlmRequest
from my_agent.context import ExecutionContext
from my_agent.types import Message, ToolCall, ToolResult


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
        context = ExecutionContext()
        context.session_manager = self.session_manager

        session_id = kwargs.get("session_id")
        session = None
        if session_id and self.session_manager:
            session = await self.session_manager.get_or_create(session_id)
            context.session = session
            context.events = session.events if session.events else []
            context.state = session.state

        context.add_event(Message(role="user", content=user_input))
        while not context.final_result and context.current_step < self.max_steps:
            response = await self.model.generate(LlmRequest(
                instructions=[self.instructions],
                contents=context.events,
                tools=self.tools,
                tool_choice="auto"
            ))
            
            if response.error_message:
                raise RuntimeError(response.error_message)
            
            if not response.content:
                raise RuntimeError("No response from model")

            # 判断是否存在tool_calls
            has_tool_calls = any(isinstance(message, ToolCall) for message in response.content)
            for message in response.content:
                if isinstance(message, ToolCall):
                    tool = next(t for t in self.tools if t.name == message.name)
                    context.add_event(ToolCall(tool_call_id=message.tool_call_id, name=message.name, arguments=message.arguments))

                    skip_tool = False
                    for callback in self.before_tool_callbacks:
                        cb_result = callback(context, message)
                        if hasattr(cb_result, "__await__"):
                            cb_result = await cb_result
                        if cb_result is not None:
                            context.add_event(ToolResult(tool_call_id=message.tool_call_id, name=message.name, status="success", content=[cb_result]))
                            skip_tool = True
                            break
                    if skip_tool:
                        context.increment_step()
                        continue
                            
                    output = await tool(context, **message.arguments)
                    tool_result = ToolResult(tool_call_id=message.tool_call_id, name=message.name, status="success", content=[output])

                    for callback in self.after_tool_callbacks:
                        cb_result = callback(context, tool_result)
                        if hasattr(cb_result, "__await__"):
                            cb_result = await cb_result
                        if cb_result is not None:
                            tool_result = cb_result

                    context.add_event(tool_result)
                    context.increment_step()
                elif isinstance(message, Message):
                    if not has_tool_calls:
                        context.final_result = message.content
                        context.add_event(message)
                    else:
                        context.add_event(message)
                        context.increment_step()
        if session:
            session.events = list(context.events)
            session.state = context.state
            await self.session_manager.save(session)
        return AgentResult(
            output=context.final_result,
            context=context,
            status="complete" if context.final_result else "error",
        )

            
