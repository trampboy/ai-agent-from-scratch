"""P0 — LLM request/response layer (LiteLLM).

Implement:
- LlmRequest / LlmResponse models
- build_messages(request) -> provider message list
- LlmClient.generate / ask / _parse_response
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field
from litellm import acompletion
from my_agent.types import Message, ToolCall
import json



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


# # 1) system
# {"role": "system", "content": "你是有用的助手。"}

# # 2) user
# {"role": "user", "content": "2 + 3 等于多少？"}

# # 3) assistant（纯文本）
# {"role": "assistant", "content": "我来算一下。"}

# # 3') assistant（工具调用；可与 content 并存，content 可为 None）
# {
#     "role": "assistant",
#     "content": None,
#     "tool_calls": [
#         {
#             "id": "call_abc123",
#             "type": "function",
#             "function": {
#                 "name": "calculator",
#                 "arguments": "{\"operation\": \"add\", \"a\": 2, \"b\": 3}"  # JSON 字符串
#             }
#         }
#     ]
# }

# # 4) tool（必须对应上一次 assistant.tool_calls[].id）
# {
#     "role": "tool",
#     "tool_call_id": "call_abc123",
#     "content": "5"   # 字符串；LiteLLM 示例里也可带 name
# }
def build_messages(request: LlmRequest) -> List[dict]:
    """Convert LlmRequest into LiteLLM/OpenAI-style messages."""
    messages = []
    for instruction in request.instructions:
        messages.append(Message(role="system", content=instruction))
    for message in request.contents:
        messages.append(Message(role=message.role, content=message.content))
    return messages


class LlmClient:
    """LLM API client via LiteLLM."""

    def __init__(self, model: str, **config: Any):
        self.model = model
        self.config = config

    async def generate(self, request: LlmRequest) -> LlmResponse:
        try:
            response = await acompletion(
                model=self.model,
                messages=build_messages(request),
                tools=request.tools,
                tool_choice=request.tool_choice,
                model_id=request.model_id,
            )
            print(response)
            return self._parse_response(response)
        except Exception as e:
            return LlmResponse(error_message=str(e))

    async def ask(
        self,
        prompt: str,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Union[str, BaseModel]:
        raise NotImplementedError("P0: one-shot prompt helper")

    def _parse_response(self, response: Any) -> LlmResponse:
        content = []
        if response.choices[0].message.content:
            content.append(Message(role="assistant", content=response.choices[0].message.content))
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                content.append(ToolCall(tool_call_id=tool_call.id, name=tool_call.function.name, arguments=json.loads(tool_call.function.arguments)))
        return LlmResponse(
            content=content, 
            usage_metadata={"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens},
        )
