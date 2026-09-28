"""P1 — Execution state and agent results.

Later phases add session / memory / code_env / transfer fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


@dataclass
class ExecutionContext:
    """Central storage for all execution state."""

    execution_id: str = ""
    events: List[Any] = field(default_factory=list)
    current_step: int = 0
    state: Dict[str, Any] = field(default_factory=dict)
    final_result: Optional[str | BaseModel] = None
    # P4+
    session: Optional[Any] = None
    session_manager: Optional[Any] = None
    memory_manager: Optional[Any] = None
    # P6+
    code_env: Optional[Any] = None
    # P7+
    transfer_to: Optional[str] = None
    transfer_tools: Dict[str, Any] = field(default_factory=dict)

    def add_event(self, event: Any) -> None:
        raise NotImplementedError("P1: append event to history")

    def increment_step(self) -> None:
        raise NotImplementedError("P1: advance current_step")


@dataclass
class AgentResult:
    """Result of an agent execution."""

    output: Any
    context: ExecutionContext
    status: str = "complete"  # complete | pending_confirmation | error
    pending_tool_calls: list = field(default_factory=list)


class PendingToolCall(BaseModel):
    """Tool call awaiting user confirmation (P4 human-in-the-loop)."""

    tool_call: Any
    confirmation_message: str


class ToolConfirmation(BaseModel):
    """User response to a pending tool call (P4)."""

    tool_call_id: str
    approved: bool
    modified_arguments: dict | None = None
    reason: str | None = None
