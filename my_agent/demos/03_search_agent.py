"""P2 验收 — 带搜索的 Agent。

通过标准：
  挂载 search 工具的 Agent 能回答简单事实问题且不崩溃，
  且 result.output 为非空字符串。

运行：
  uv run python my_agent/demos/03_search_agent.py
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
    if not os.getenv("TAVILY_API_KEY"):
        _fail("请在 .env 中设置 TAVILY_API_KEY")

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools.base import FunctionTool
    from my_agent.tools import search as search_mod

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")

    try:
        # 按你对外暴露的 search 入口包装即可
        search_fn = getattr(search_mod, "search")
        search_tool = FunctionTool(search_fn) if not hasattr(search_fn, "tool_definition") else search_fn
    except NotImplementedError as e:
        _fail(f"请实现 tools/search.py — {e}")

    agent = Agent(
        model=LlmClient(model),
        tools=[search_tool],
        instructions="查事实请使用 search，回答简洁并略作引用。",
        max_steps=6,
    )

    try:
        result = await agent.run("What is the capital of France?")
    except NotImplementedError as e:
        _fail(f"尚未实现 — {e}")

    if not str(result.output).strip():
        _fail("Agent 输出为空")
    print(f"输出: {result.output}")
    print("P2 通过")


if __name__ == "__main__":
    asyncio.run(main())
