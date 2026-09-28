"""P0 验收 — LLM 客户端 + 工具 schema + 计算器。

通过标准：
1. calculator(add, 2, 3) == 5
2. FunctionTool/@tool 能包装 calculator，并提供 tool_definition
3. LlmClient.generate 返回助手文本和/或针对 calculator 的 ToolCall

运行：
  uv run python my_agent/demos/01_llm_and_tools.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


async def main() -> None:
    from my_agent.tools.calculator import calculator
    from my_agent.tools.base import FunctionTool, tool
    from my_agent.llm import LlmClient, LlmRequest
    from my_agent.types import Message, ToolCall

    # 1) calculator
    try:
        result = calculator("add", 2, 3)
    except NotImplementedError as e:
        _fail(f"请实现 tools/calculator.py — {e}")
    if result != 5:
        _fail(f"calculator('add', 2, 3) 期望 5，实际 {result!r}")
    print("通过: calculator")

    # 2) 工具包装
    try:
        wrapped = FunctionTool(calculator)
        definition = wrapped.tool_definition
    except NotImplementedError as e:
        _fail(f"请实现 tools/base.py 的 FunctionTool — {e}")
    if not definition:
        _fail("FunctionTool.tool_definition 必须是非空 dict")
    print("通过: FunctionTool.tool_definition")
    print(definition)

    # 可选：@tool 装饰器冒烟
    try:
        decorated = tool(calculator)
        _ = decorated.tool_definition
        print("通过: @tool 装饰器")
    except NotImplementedError:
        print("跳过: @tool 装饰器尚未实现")

    # 3) LLM 往返（需要 API key）
    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")

    client = LlmClient(model)
    request = LlmRequest(
        instructions=["你是有用的助手。需要时使用工具。"],
        contents=[Message(role="user", content="2 + 3 等于多少？请使用 calculator 工具。")],
        tools=[wrapped],
    )
    try:
        response = await client.generate(request)
    except NotImplementedError as e:
        _fail(f"请实现 llm.py — {e}")

    if response.error_message:
        _fail(f"LLM 错误: {response.error_message}")
    if not response.content:
        _fail("LlmResponse.content 为空")

    has_tool = any(isinstance(item, ToolCall) for item in response.content)
    has_text = any(isinstance(item, Message) for item in response.content)
    if not (has_tool or has_text):
        _fail("期望 response.content 中有 Message 和/或 ToolCall")
    print(f"通过: LlmClient.generate (tool_call={has_tool}, text={has_text})")
    print("P0 通过")


if __name__ == "__main__":
    asyncio.run(main())
