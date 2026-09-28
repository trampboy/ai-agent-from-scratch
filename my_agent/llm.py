"""P0 — LLM request/response layer (LiteLLM).

Implement:
- LlmRequest / LlmResponse models
- build_messages(request) -> provider message list
- LlmClient.generate / ask / _parse_response
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field


class LlmRequest(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    instructions: List[str] = Field(default_factory=list)
    contents: List[Any] = Field(default_factory=list)
    tools: List[Any] = Field(default_factory=list)
    tool_choice: Optional[str] = None
    model_id: Optional[str] = None

    def append_instructions(self, text: str) -> None:
        raise NotImplementedError("P0: append system instruction")


class LlmResponse(BaseModel):
    content: List[Any] = Field(default_factory=list)
    error_message: Optional[str] = None
    usage_metadata: Dict[str, Any] = Field(default_factory=dict)


def build_messages(request: LlmRequest) -> List[dict]:
    """Convert LlmRequest into LiteLLM/OpenAI-style messages."""
    raise NotImplementedError("P0: map Message/ToolCall/ToolResult to API messages")


class LlmClient:
    """LLM API client via LiteLLM."""

    def __init__(self, model: str, **config: Any):
        self.model = model
        self.config = config

    async def generate(self, request: LlmRequest) -> LlmResponse:
        raise NotImplementedError("P0: call litellm.acompletion and parse response")

    async def ask(
        self,
        prompt: str,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Union[str, BaseModel]:
        raise NotImplementedError("P0: one-shot prompt helper")

    def _parse_response(self, response: Any) -> LlmResponse:
        raise NotImplementedError("P0: convert provider response to LlmResponse")
