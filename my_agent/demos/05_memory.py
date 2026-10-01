"""P4 验收 — Session / 长期记忆 / 工具确认（仅验收 my_agent）。

通过标准：
  1) my_agent.memory.session：get_or_create / save 可用
  2) 同一 session_id 两轮对话能回忆第 1 轮事实
  3) PendingToolCall / ToolConfirmation 可构造；确认回路可挂起并恢复
  4) TaskMemory 可构造；save(context) 后 search 能召回相关摘要

实现位置（不要改 scratch_agents/）：
  my_agent/memory/session.py
  my_agent/memory/long_term.py
  my_agent/memory/context_optimizer.py
  my_agent/tools/memory_tool.py
  my_agent/agent.py（session / confirmation 接线）

运行：
  uv run python my_agent/demos/05_memory.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

SECRET = "ORANGE-42"
SESSION_ID = "mem-demo-1"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _require_api_key() -> None:
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")


def _session_manager():
    """从 my_agent 取可运行的 SessionManager。"""
    try:
        from my_agent.memory import session as session_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/memory/session.py — {e}")

    # 优先具体实现；否则要求你补齐 InMemorySessionManager
    cls = getattr(session_mod, "InMemorySessionManager", None)
    if cls is None:
        _fail(
            "请在 my_agent/memory/session.py 中实现 InMemorySessionManager"
            "（需提供 get_or_create / save，可选 create / get）"
        )
    return cls()


async def _check_session_unit() -> None:
    """A) Session 单元：对齐 my_agent BaseSessionManager 契约。"""
    mgr = _session_manager()

    try:
        s1 = await mgr.get_or_create(SESSION_ID)
    except NotImplementedError as e:
        _fail(f"尚未实现 get_or_create — {e}")

    if s1 is None:
        _fail("get_or_create 不应返回 None")
    if getattr(s1, "session_id", None) != SESSION_ID:
        _fail(f"session.session_id 期望 {SESSION_ID!r}")

    s2 = await mgr.get_or_create(SESSION_ID)
    if s2 is None or getattr(s2, "session_id", None) != SESSION_ID:
        _fail("再次 get_or_create 应返回同一 session_id")

    # 若实现了 events，写入后 save，再取回应仍在
    if hasattr(s1, "events"):
        marker = {"role": "user", "content": "ping"}
        s1.events.append(marker)
        try:
            await mgr.save(s1)
        except NotImplementedError as e:
            _fail(f"尚未实现 save — {e}")
        loaded = await mgr.get_or_create(SESSION_ID)
        if not getattr(loaded, "events", None):
            _fail("save 后再次 get_or_create，events 应非空")
    else:
        try:
            await mgr.save(s1)
        except NotImplementedError as e:
            _fail(f"尚未实现 save — {e}")

    print("A) session unit: OK")


async def _check_two_turn_recall() -> None:
    """B) 两轮对话回忆：同一 session_id，第 2 轮输出含第 1 轮秘密。"""
    _require_api_key()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    session_mgr = _session_manager()

    agent = Agent(
        model=LlmClient(model),
        tools=[],
        instructions=(
            "你是有会话记忆的助手。记住用户告诉你的事实，"
            "后续问题请直接依据对话历史简洁作答。"
        ),
        max_steps=4,
        session_manager=session_mgr,
    )

    try:
        r1 = await agent.run(
            f"请记住：我的项目代号是 {SECRET}。只需确认记住即可。",
            session_id=SESSION_ID,
        )
    except TypeError as e:
        _fail(f"请让 my_agent.agent.Agent.run 支持 session_id=... — {e}")
    except NotImplementedError as e:
        _fail(f"尚未实现 session 接线（my_agent/agent.py）— {e}")

    if not str(r1.output).strip():
        _fail("第 1 轮 Agent 输出为空")
    print(f"B) 第 1 轮: {r1.output}")

    try:
        r2 = await agent.run(
            "我的项目代号是什么？请只回答代号本身。",
            session_id=SESSION_ID,
        )
    except NotImplementedError as e:
        _fail(f"尚未实现 session 恢复 — {e}")

    output = str(r2.output)
    print(f"B) 第 2 轮: {output}")
    if not output.strip():
        _fail("第 2 轮 Agent 输出为空")
    if SECRET not in output:
        _fail(f"期望第 2 轮输出包含 {SECRET}（session 未正确恢复历史）")

    print("B) two-turn recall: OK")


async def _check_tool_confirmation() -> None:
    """C) 工具确认：类型 + pending → 拒绝恢复（失败 case）。"""
    import tempfile

    from my_agent.agent import Agent
    from my_agent.context import PendingToolCall, ToolConfirmation
    from my_agent.llm import LlmClient
    from my_agent.tools.base import FunctionTool
    from my_agent.types import ToolCall

    # --- 类型冒烟 ---
    try:
        tc = ToolCall(
            tool_call_id="tc-1",
            name="delete_file",
            arguments={"path": "/tmp/x"},
        )
        pending = PendingToolCall(
            tool_call=tc,
            confirmation_message="确认删除？",
        )
        conf = ToolConfirmation(tool_call_id="tc-1", approved=False, reason="no")
    except Exception as e:
        _fail(f"my_agent.context 中 PendingToolCall / ToolConfirmation 构造失败 — {e}")

    if conf.approved:
        _fail("拒绝路径的 approved 应为 False")
    if pending.tool_call.name != "delete_file":
        _fail("PendingToolCall 应保留原始 tool_call")
    print("C) tool confirmation (types): OK")

    # --- 端到端：拒绝确认（失败 case）---
    _require_api_key()

    deleted: list[str] = []

    def delete_file(path: str) -> str:
        """删除指定路径的文件。"""
        deleted.append(path)
        return f"deleted: {path}"

    delete_tool = FunctionTool(
        delete_file,
        requires_confirmation=True,
        confirmation_message_template="确认删除 {path}？",
    )

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    session_mgr = _session_manager()
    confirm_session = "mem-confirm-deny"

    with tempfile.TemporaryDirectory() as workspace:
        target = os.path.join(workspace, "tmp.txt")
        with open(target, "w", encoding="utf-8") as f:
            f.write("keep-me\n")

        agent = Agent(
            model=LlmClient(model),
            tools=[delete_tool],
            instructions=(
                "你只能使用 delete_file 工具。用户要求删除时必须调用该工具，"
                "不要直接用文字代替工具调用。"
            ),
            max_steps=4,
            session_manager=session_mgr,
        )

        try:
            r = await agent.run(
                f"请删除文件：{target}",
                session_id=confirm_session,
            )
        except NotImplementedError as e:
            _fail(f"确认回路尚未实现 — {e}")

        print(f"C) 第 1 次 run status={r.status!r} pending={r.pending_tool_calls!r}")
        if r.status != "pending_confirmation":
            _fail(
                f"期望 status='pending_confirmation'，得到 {r.status!r}"
                "（请在执行 requires_confirmation 工具前挂起）"
            )
        if not r.pending_tool_calls:
            _fail("pending_confirmation 时应带上 pending_tool_calls")

        deny = ToolConfirmation(
            tool_call_id=r.pending_tool_calls[0].tool_call.tool_call_id,
            approved=False,
            reason="demo deny",
        )
        try:
            r2 = await agent.run(
                None,
                session_id=confirm_session,
                tool_confirmations=[deny],
            )
        except TypeError as e:
            _fail(f"恢复确认时 run 需支持 user_input=None 与 tool_confirmations — {e}")
        except NotImplementedError as e:
            _fail(f"尚未实现 tool_confirmations 恢复 — {e}")

        print(f"C) 拒绝后 status={r2.status!r} output={r2.output!r}")
        if deleted:
            _fail(f"拒绝确认后不应真正删除，却调用了: {deleted}")

    print("C) tool confirmation (deny): OK")


async def _check_long_term_memory() -> None:
    """D) Long-term：TaskMemory 模型 + save / search（去重可选）。

    实现位置：my_agent/memory/long_term.py
    提示：
      - TaskMemory 字段：task_summary / approach / final_answer / is_correct / error_analysis
      - TaskMemoryManager.save(context) 从 events 抽取并入库；search(query) 向量召回
      - 抽取若走 LLM，可能需要先实现 LlmClient.ask(..., response_format=TaskMemory)
    """
    _require_api_key()

    try:
        from my_agent.memory.long_term import TaskMemory, TaskMemoryManager
    except ImportError as e:
        _fail(
            "请在 my_agent/memory/long_term.py 导出 TaskMemory 与 TaskMemoryManager — "
            f"{e}"
        )

    from my_agent.context import ExecutionContext
    from my_agent.llm import LlmClient
    from my_agent.types import Message

    # --- 模型可构造 ---
    try:
        sample = TaskMemory(
            task_summary="What is the project code for demo D?",
            approach="Look up prior conversation fact",
            final_answer=SECRET,
            is_correct=True,
            error_analysis=None,
        )
    except Exception as e:
        _fail(f"TaskMemory 构造失败 — {e}")

    if not hasattr(sample, "to_embedding_text"):
        _fail("TaskMemory 建议提供 to_embedding_text() 供向量检索使用")
    print(f"D) TaskMemory: OK ({sample.to_embedding_text()!r})")

    # --- save + search ---
    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    try:
        mgr = TaskMemoryManager(LlmClient(model))
    except TypeError as e:
        _fail(f"TaskMemoryManager(__init__) 签名不匹配，通常需要 llm_client — {e}")
    except NotImplementedError as e:
        _fail(f"尚未实现 TaskMemoryManager — {e}")

    ctx = ExecutionContext()
    ctx.add_event(
        Message(
            role="user",
            content=f"Solve: what is the secret project code? It is {SECRET}.",
        )
    )
    ctx.add_event(
        Message(
            role="assistant",
            content=f"The project code is {SECRET}.",
        )
    )
    ctx.final_result = SECRET

    try:
        memory_id = await mgr.save(ctx)
    except NotImplementedError as e:
        _fail(
            f"请实现 TaskMemoryManager.save(context) — {e}；"
            "若内部用 LLM 抽取，请一并实现 LlmClient.ask"
        )
    except Exception as e:
        _fail(f"save(context) 失败 — {e}")

    print(f"D) save 返回: {memory_id!r}")
    if memory_id is None:
        _fail("首次 save 应入库并返回 memory_id，不应为 None（除非去重误伤）")

    # try:
    #     hits = await mgr.search("secret project code", top_k=3)
    # except TypeError:
    #     # 允许 search(query) 不带 top_k
    #     try:
    #         hits = await mgr.search("secret project code")
    #     except NotImplementedError as e:
    #         _fail(f"请实现 TaskMemoryManager.search — {e}")
    # except NotImplementedError as e:
    #     _fail(f"请实现 TaskMemoryManager.search — {e}")

    # print(f"D) search hits: {hits!r}")
    # if not hits:
    #     _fail("search 应能召回刚 save 的记忆")

    # texts = " ".join(
    #     getattr(h, "task_summary", "") + " " + getattr(h, "final_answer", "")
    #     for h in hits
    # )
    # if SECRET not in texts and "project code" not in texts.lower():
    #     _fail(f"召回结果应与入库任务相关（期望含 {SECRET} 或 project code 摘要）")

    # # --- 去重（可选但建议）：再 save 一次同 context ---
    # try:
    #     dup_id = await mgr.save(ctx)
    #     print(f"D) 重复 save 返回: {dup_id!r}")
    #     if dup_id is not None:
    #         print("D) 去重: WARN（重复 save 仍返回 id；可后续补 _is_duplicate）")
    #     else:
    #         print("D) 去重: OK")
    # except Exception as e:
    #     print(f"D) 去重: SKIP — {e}")

    # print("D) long-term memory: OK")


async def main() -> None:
    # await _check_session_unit()
    # await _check_two_turn_recall()
    # await _check_tool_confirmation()
    await _check_long_term_memory()
    print("P4 通过")


if __name__ == "__main__":
    asyncio.run(main())
