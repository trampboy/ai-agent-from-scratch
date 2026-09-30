"""P3 验收 — RAG + 文件工具 + callbacks。

通过标准：
  1) chunk_text 行为正确
  2) Agent 能 list/read 工作区文件并答出文件中的事实
  3) approval / compressor 基本行为正确

运行：
  uv run python my_agent/demos/04_rag_files.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

SECRET = "ORANGE-42"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _check_rag_unit() -> None:
    """A) RAG 单元：切块行为。"""
    from my_agent.rag import chunk_text

    try:
        chunk_text("abc", chunk_size=1, overlap=1)
        _fail("非法 overlap 应抛 ValueError")
    except ValueError:
        pass

    got = chunk_text("abcdef", chunk_size=3, overlap=1)
    if got != ["abc", "cde", "ef"]:
        _fail(f"chunk_text 期望 ['abc', 'cde', 'ef']，得到 {got!r}")
    print("A) chunk_text: OK")


async def _check_file_agent() -> None:
    """B) 文件工具 + Agent：读工作区事实。"""
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools.base import FunctionTool
    from my_agent.tools import file_tools as ft

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")

    with tempfile.TemporaryDirectory() as workspace:
        note_path = os.path.join(workspace, "note.txt")
        ft.write_file(note_path, f"answer_code = {SECRET}\n")

        list_tool = FunctionTool(ft.list_files)
        read_tool = FunctionTool(ft.read_file)

        agent = Agent(
            model=LlmClient(model),
            tools=[list_tool, read_tool],
            instructions=(
                "你只能通过 list_files / read_file 查看工作区。"
                "回答简洁，务必包含文件中的 answer_code。"
            ),
            max_steps=8,
        )

        question = (
            f"工作区目录是 {workspace}。"
            "请列出文件并读取 note.txt，告诉我 answer_code 是什么？"
        )
        try:
            result = await agent.run(question)
        except NotImplementedError as e:
            _fail(f"尚未实现 — {e}")

        output = str(result.output)
        print(f"B) Agent 输出: {output}")
        if not output.strip():
            _fail("Agent 输出为空")
        if SECRET not in output:
            _fail(f"期望输出包含 {SECRET}")
    print("B) file agent: OK")


async def _check_callbacks() -> None:
    """C) Callback 冒烟：approval + compressor 短路路径。"""
    from my_agent.callbacks import approval_callback, search_compressor
    from my_agent.context import ExecutionContext
    from my_agent.types import ToolCall, ToolResult

    ctx = ExecutionContext()

    safe = ToolCall(tool_call_id="1", name="list_files", arguments={"path": "."})
    if await approval_callback(ctx, safe) is not None:
        _fail("非危险工具的 approval 应返回 None")

    danger = ToolCall(tool_call_id="2", name="delete_file", arguments={"path": "x"})
    with patch("builtins.input", return_value="n"):
        denied = await approval_callback(ctx, danger)
    if not denied or "delete_file" not in str(denied):
        _fail("拒绝危险工具时应返回说明字符串")

    with patch("builtins.input", return_value="y"):
        if await approval_callback(ctx, danger) is not None:
            _fail("同意危险工具时应返回 None")

    other = ToolResult(
        tool_call_id="3", name="read_file", status="success", content=["hi"]
    )
    if await search_compressor(ctx, other) is not None:
        _fail("非 search 的 compressor 应返回 None")

    ctx.add_event(ToolCall(tool_call_id="4", name="search", arguments={"query": "q"}))
    short = ToolResult(tool_call_id="4", name="search", status="success", content=["short"])
    if await search_compressor(ctx, short) is not None:
        _fail("短搜索结果的 compressor 应返回 None")

    print("C) callbacks: OK")


async def main() -> None:
    _check_rag_unit()
    await _check_file_agent()
    await _check_callbacks()
    print("P3 通过")


if __name__ == "__main__":
    asyncio.run(main())
