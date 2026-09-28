"""手写 Agent（对照书本的教学复刻）。

按 Phase 实现；编码时不要照抄 scratch_agents。
Phase 清单见 my_agent/README.md。
"""

from my_agent.types import ContentItem, Event, Message, ToolCall, ToolResult
from my_agent.context import AgentResult, ExecutionContext, PendingToolCall, ToolConfirmation
from my_agent.llm import LlmClient, LlmRequest, LlmResponse
from my_agent.agent import Agent

__all__ = [
    "Message",
    "ToolCall",
    "ToolResult",
    "Event",
    "ContentItem",
    "ExecutionContext",
    "AgentResult",
    "PendingToolCall",
    "ToolConfirmation",
    "LlmClient",
    "LlmRequest",
    "LlmResponse",
    "Agent",
]
