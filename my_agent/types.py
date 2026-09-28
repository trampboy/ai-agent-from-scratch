"""P0 — Core conversation types.

Target surface (align with the book, names may differ):
- Message, ToolCall, ToolResult
- ContentItem = Union[...]
- Event (execution history record)
"""

from __future__ import annotations

from typing import List, Literal, Union

from pydantic import BaseModel


class Message(BaseModel):
    """A text message in the conversation."""

    type: Literal["message"] = "message"
    role: Literal["system", "user", "assistant"]
    content: str


class ToolCall(BaseModel):
    """LLM request to execute a tool."""

    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    name: str
    arguments: dict


class ToolResult(BaseModel):
    """Result from tool execution."""

    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str
    name: str
    status: Literal["success", "error"]
    content: list


ContentItem = Union[Message, ToolCall, ToolResult]


class Event(BaseModel):
    """A recorded occurrence during agent execution."""

    # TODO(P0): flesh out fields to match how Agent records history
    content: ContentItem | None = None
    step: int | None = None
