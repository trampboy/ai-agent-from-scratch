"""P0 — Tool protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
import inspect

from my_agent.tools import helpers


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(
        self,
        name: str | None = None,
        description: str | None = None,
        tool_definition: Dict[str, Any] | None = None,
        requires_confirmation: bool = False,
        confirmation_message_template: str | None = None,
    ):
        self.name = name or self.__class__.__name__
        self.description = description or self.__doc__ or ""
        self._tool_definition = tool_definition
        self.requires_confirmation = requires_confirmation
        self.confirmation_message_template = confirmation_message_template

    @property
    def tool_definition(self) -> Dict[str, Any] | None:
        return self._tool_definition

    def get_confirmation_message(self, arguments: dict) -> str:
        raise NotImplementedError("P0/P4: format confirmation prompt")

    async def process_llm_request(self, context: Any, request: Any) -> None:
        """Optional hook to mutate LlmRequest before the call (later phases)."""
        return None

    @abstractmethod
    async def execute(self, context: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def __call__(self, context: Any, **kwargs: Any) -> Any:
        return await self.execute(context, **kwargs)

class FunctionTool(BaseTool):
    """Wrap a Python function as a BaseTool."""

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
        tool_definition: Dict[str, Any] | None = None,
        sandbox_executable: bool = False,
        requires_confirmation: bool = False,
        confirmation_message_template: str = "",
    ):
        resolved_name = name or func.__name__
        resolved_desc = description or (func.__doc__ or "").strip()
        super().__init__(resolved_name, resolved_desc, tool_definition, requires_confirmation, confirmation_message_template)
        self.func = func
        self.sandbox_executable = sandbox_executable
        parameters = helpers.function_to_input_schema(func)
        self._tool_definition = helpers.format_tool_definition(resolved_name, resolved_desc, parameters)
        self.needs_context = "context" in inspect.signature(func).parameters

    async def execute(self, context: Any, **kwargs: Any) -> Any:
        if self.needs_context:
            result = self.func(context, **kwargs)
        else:
            result = self.func(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


def tool(
    func: Optional[Callable] = None,
    *,
    name: str | None = None,
    description: str | None = None,
    requires_confirmation: bool = False,
) -> Any:
    """Decorator that turns a function into a FunctionTool."""
    return FunctionTool(func=func, name=name, description=description, requires_confirmation=requires_confirmation)
