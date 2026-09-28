"""P1 验收 — 带计算器的 ReAct Agent。

通过标准：
  Agent.run("What is (12 + 8) * 3?") 的最终答案中包含 60。

运行：
  uv run python my_agent/demos/02_react_calc.py
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
    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools.base import FunctionTool
    from my_agent.tools.calculator import calculator

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")

    try:
        calc_tool = FunctionTool(calculator)
    except NotImplementedError as e:
        _fail(f"请先完成 P0 — {e}")

    agent = Agent(
        model=LlmClient(model),
        tools=[calc_tool],
        instructions="用 calculator 工具做数学计算，不要臆造数字。",
        max_steps=8,
    )

    try:
        result = await agent.run("What is (12 + 8) * 3?")
    except NotImplementedError as e:
        _fail(f"请实现 agent.py / context.py — {e}")

    output = str(result.output)
    print(f"输出: {output}")
    if "60" not in output:
        _fail("期望最终答案中包含 60")
    print("P1 通过")


if __name__ == "__main__":
    asyncio.run(main())
