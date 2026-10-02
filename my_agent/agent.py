"""P1 — ReAct agent loop.

Grow this class across phases (callbacks, session, memory, skills, transfer).
Start with: tools + instructions + max_steps + run().
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Type

from pydantic import BaseModel

from my_agent.context import AgentResult
from my_agent.llm import LlmClient, LlmRequest
from my_agent.context import ExecutionContext, PendingToolCall
from my_agent.types import Message, ToolCall, ToolResult
from e2b_code_interpreter import Sandbox
from my_agent.tools.code_execution import execute_python


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
        tool_confirmations = kwargs.get("tool_confirmations") or []

        if self.code_execution == 'e2b':
            sandbox = Sandbox.create(timeout=200)
            context.code_env = sandbox
            self.tools.append(execute_python)

        session_id = kwargs.get("session_id")
        session = None
        if session_id and self.session_manager:
            session = await self.session_manager.get_or_create(session_id)
            context.session = session
            context.events = session.events if session.events else []
            context.state = session.state

        if user_input:
            context.add_event(Message(role="user", content=user_input))

        # 判断是否已经被批准
        pending_tool_calls = context.state.get("pending_tool_calls") or []
        for tool_confirmation in tool_confirmations:
            pending = next((p for p in pending_tool_calls if p.tool_call.tool_call_id == tool_confirmation.tool_call_id), None)
            if pending is None:
                continue
            
            tool_call = pending.tool_call
            tool = next(t for t in self.tools if t.name == tool_call.name)
            if tool_confirmation.approved:
                args = tool_confirmation.modified_arguments or tool_call.arguments
                tool_output = await tool(context, **args)
                context.add_event(ToolResult(tool_call_id=tool_call.tool_call_id, name=tool_call.name, status="success", content=[tool_output]))
            else:
                context.add_event(ToolResult(tool_call_id=tool_call.tool_call_id, name=tool_call.name, status="error", content=['用户拒绝']))
            
            context.state.pop("pending_tool_calls", None)

        try:
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

                        # 如果该工具需要用户确认是否执行    
                        print('tool.requires_confirmation', tool.requires_confirmation)
                        if tool.requires_confirmation is True:
                            pendingToolCalls = [PendingToolCall(tool_call=message, confirmation_message=tool.confirmation_message_template)]
                            context.state["pending_tool_calls"] = pendingToolCalls
                            if session:
                                session.events = list(context.events)
                                session.state = context.state
                                await self.session_manager.save(session)
                            return AgentResult(status="pending_confirmation", pending_tool_calls=pendingToolCalls, context=context, output="权限需要用户确认")


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
                        
                        try:
                            output = await tool(context, **message.arguments)
                            tool_result = ToolResult(tool_call_id=message.tool_call_id, name=message.name, status="success", content=[output])
                        except Exception as e:
                            tool_result = ToolResult(tool_call_id=message.tool_call_id, name=message.name, status="error", content=[str(e)])
                        

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
        finally:
            if context.code_env is not None:
                sandbox = context.code_env
                context.code_env = None
                sandbox.kill()

            
