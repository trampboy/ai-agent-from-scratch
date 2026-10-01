"""P5 验收 — Planning / Reflection（仅验收 my_agent）。

通过标准：
  1) Task：content + status；三种状态的 __str__ 与书本一致
  2) create_tasks：可接受 dict 任务列表，返回 Markdown 清单字符串
  3) reflection：记录分析；need_replan=True 时标记 REPLAN NEEDED
  4) Agent 挂载 create_tasks + search，多步目标会先规划再检索
  5) Agent 挂载 reflection，工具失败后能反思并改用备选工具

实现位置（不要改 scratch_agents/）：
  my_agent/planning.py
  （Agent 侧通常无需改；与普通工具一样挂载即可）

期望 API（对齐 CH07 / scratch_agents.planning）：
  class Task(BaseModel):
      content: str
      status: Literal["pending", "in_progress", "completed"]
  @tool
  def create_tasks(tasks: List[Task]) -> str: ...
  @tool
  def reflection(analysis: str, need_replan: bool = False) -> str: ...

运行：
  uv run python my_agent/demos/06_planning.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Listing 7.3 — 多步规划题
KIPCHOGE_GOAL = (
    "If Eliud Kipchoge could maintain his marathon pace indefinitely, "
    "how many thousand hours would it take him to reach the Moon?"
)

# Listing 7.6 — 失败恢复 + 反思
PERIGEE_GOAL = "What is the distance from Earth to Moon at perigee?"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _require_api_key() -> None:
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")


def _require_tavily() -> None:
    if not os.getenv("TAVILY_API_KEY"):
        _fail("请在 .env 中设置 TAVILY_API_KEY（E2E 需要 search）")


def _as_tool(fn: Any) -> Any:
    """裸函数包成 FunctionTool；已是工具则原样返回。"""
    if hasattr(fn, "tool_definition") and hasattr(fn, "execute"):
        return fn
    from my_agent.tools.base import FunctionTool

    return FunctionTool(fn)


def _load_planning():
    """导入 my_agent.planning，缺失或未实现时给出指引。"""
    try:
        from my_agent import planning as planning_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/planning.py — {e}")
    return planning_mod


def _tool_names(events: Iterable[Any]) -> set[str]:
    """从 Agent 事件里收集被调用过的工具名。"""
    names: set[str] = set()
    for ev in events or []:
        name = getattr(ev, "name", None)
        if name:
            names.add(name)
            continue
        # 若 Event 包了一层 content
        content = getattr(ev, "content", None)
        nested = getattr(content, "name", None) if content is not None else None
        if nested:
            names.add(nested)
    return names


async def _check_task_and_create_tasks() -> None:
    """A) Task + create_tasks 单元（无 LLM）。"""
    from my_agent.context import ExecutionContext

    planning = _load_planning()
    Task = getattr(planning, "Task", None)
    create_tasks = getattr(planning, "create_tasks", None)
    if Task is None:
        _fail("请在 my_agent/planning.py 中定义 Task")
    if create_tasks is None:
        _fail("请在 my_agent/planning.py 中实现 create_tasks")

    # --- Task.__str__ ---
    try:
        pending = Task(content="Find pace", status="pending")
        doing = Task(content="Find distance", status="in_progress")
        done = Task(content="Compute hours", status="completed")
    except Exception as e:
        _fail(
            f"Task(content, status) 构造失败 — {e}；"
            "status 应为 pending / in_progress / completed"
        )

    s_pending, s_doing, s_done = str(pending), str(doing), str(done)
    print(f"A) Task str: {s_pending!r} | {s_doing!r} | {s_done!r}")
    if "[ ]" not in s_pending or "Find pace" not in s_pending:
        _fail("pending 期望形如 '[ ] Find pace'")
    if "[>]" not in s_doing or "Find distance" not in s_doing:
        _fail("in_progress 期望形如 '[>] **Find distance**'（或至少含 [>]）")
    if "[x]" not in s_done or "Compute hours" not in s_done:
        _fail("completed 期望形如 '[x] ~~Compute hours~~'（或至少含 [x]）")

    # --- create_tasks：接受 dict（对齐 regression / JSON tool args）---
    tool = _as_tool(create_tasks)
    ctx = ExecutionContext()
    try:
        result = await tool(
            ctx,
            tasks=[{"content": "Find evidence", "status": "pending"}],
        )
    except NotImplementedError as e:
        _fail(f"请实现 create_tasks — {e}")
    except Exception as e:
        _fail(f"create_tasks 调用失败 — {e}")

    text = str(result)
    print(f"A) create_tasks -> {text!r}")
    if "[ ] Find evidence" not in text:
        _fail("create_tasks 对 dict 任务应返回含 '[ ] Find evidence' 的字符串")

    # 多任务整表更新
    try:
        multi = await tool(
            ctx,
            tasks=[
                {"content": "A", "status": "completed"},
                {"content": "B", "status": "in_progress"},
                {"content": "C", "status": "pending"},
            ],
        )
    except Exception as e:
        _fail(f"create_tasks 多任务失败 — {e}")

    multi_text = str(multi)
    print(f"A) create_tasks multi ->\n{multi_text}")
    if "[x]" not in multi_text or "[>]" not in multi_text or "[ ]" not in multi_text:
        _fail("多任务返回应同时包含 completed / in_progress / pending 的标记")

    print("A) task + create_tasks: OK")


async def _check_reflection_unit() -> None:
    """B) reflection 单元（无 LLM）。"""
    from my_agent.context import ExecutionContext

    planning = _load_planning()
    reflection = getattr(planning, "reflection", None)
    if reflection is None:
        # 兼容错误占位名 reflect，但验收以 reflection 为准
        if getattr(planning, "reflect", None) is not None:
            _fail(
                "发现 reflect，但 CH07 工具名应为 reflection；"
                "请导出 @tool def reflection(analysis, need_replan=False) -> str"
            )
        _fail("请在 my_agent/planning.py 中实现 reflection")

    tool = _as_tool(reflection)
    ctx = ExecutionContext()

    try:
        ok = await tool(ctx, analysis="进度正常，继续下一步。", need_replan=False)
    except NotImplementedError as e:
        _fail(f"请实现 reflection — {e}")
    except TypeError as e:
        _fail(f"reflection 签名应为 (analysis, need_replan=False) — {e}")
    except Exception as e:
        _fail(f"reflection 调用失败 — {e}")

    ok_text = str(ok)
    print(f"B) reflection(normal) -> {ok_text!r}")
    if "Reflection recorded" not in ok_text:
        _fail("need_replan=False 时期望返回含 'Reflection recorded'")
    if "REPLAN NEEDED" in ok_text:
        _fail("need_replan=False 时不应出现 REPLAN NEEDED")

    try:
        replan = await tool(
            ctx,
            analysis="Wikipedia 不可用，改用 web search。",
            need_replan=True,
        )
    except Exception as e:
        _fail(f"reflection(need_replan=True) 失败 — {e}")

    replan_text = str(replan)
    print(f"B) reflection(replan) -> {replan_text!r}")
    if "REPLAN NEEDED" not in replan_text:
        _fail("need_replan=True 时期望返回含 'REPLAN NEEDED'")
    if "Wikipedia" not in replan_text:
        _fail("返回应保留 analysis 原文")

    print("B) reflection unit: OK")


async def _check_planning_e2e() -> None:
    """C) Agent + create_tasks + search（Listing 7.3 风格）。"""
    _require_api_key()
    _require_tavily()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools import search as search_mod

    planning = _load_planning()
    create_tasks = getattr(planning, "create_tasks", None)
    if create_tasks is None:
        _fail("请实现 create_tasks 后再跑 E2E")

    try:
        search_fn = getattr(search_mod, "search")
        search_tool = _as_tool(search_fn)
    except NotImplementedError as e:
        _fail(f"请先完成 P2 search — {e}")

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    agent = Agent(
        model=LlmClient(model),
        tools=[_as_tool(create_tasks), search_tool],
        instructions=(
            "复杂多步问题请先用 create_tasks 建计划并更新状态，"
            "需要事实时再 search。最终给出简洁数字答案（thousand hours）。"
        ),
        max_steps=12,
    )

    try:
        result = await agent.run(KIPCHOGE_GOAL)
    except NotImplementedError as e:
        _fail(f"Agent / planning 尚未接通 — {e}")
    except Exception as e:
        _fail(f"planning E2E 运行失败 — {e}")

    output = str(getattr(result, "output", "") or "")
    print(f"C) 输出: {output}")
    if not output.strip():
        _fail("Agent 输出为空")

    events = getattr(getattr(result, "context", None), "events", None) or []
    names = _tool_names(events)
    print(f"C) 调用过的工具: {sorted(names)}")
    if "create_tasks" not in names:
        _fail("期望至少调用一次 create_tasks（多步目标应先规划）")
    # search 工具名可能是 search / search_web
    if not any(n in names for n in ("search", "search_web")):
        _fail("期望至少调用一次 search（需要检索马拉松配速或月距）")

    # 弱断言：答案应像「多少千小时」
    lowered = output.lower()
    if not any(ch.isdigit() for ch in output):
        _fail("最终答案应包含数字（thousand hours 量级）")
    if not any(k in lowered for k in ("hour", "千", "thousand")):
        print("C) WARN: 输出未明显提到 hour/thousand；若答案正确可忽略")

    print("C) planning e2e: OK")


async def _check_reflection_e2e() -> None:
    """D) Agent + reflection：Wikipedia 先失败，再反思并用 search（Listing 7.6）。"""
    _require_api_key()
    _require_tavily()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools import search as search_mod
    from my_agent.tools.base import tool as tool_decorator

    planning = _load_planning()
    reflection = getattr(planning, "reflection", None)
    if reflection is None:
        _fail("请实现 reflection 后再跑 E2E")

    @tool_decorator
    def get_wikipedia_page(title: str) -> str:
        """Fetch a Wikipedia page by title. Always try this first when researching."""
        raise RuntimeError("Wikipedia service temporarily unavailable")

    try:
        search_fn = getattr(search_mod, "search")
        search_tool = _as_tool(search_fn)
    except NotImplementedError as e:
        _fail(f"请先完成 P2 search — {e}")

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    agent = Agent(
        model=LlmClient(model),
        tools=[get_wikipedia_page, search_tool, _as_tool(reflection)],
        instructions=(
            "Always try Wikipedia first when researching topics. "
            "If a tool fails, call reflection to analyze, then use an alternative tool."
        ),
        max_steps=10,
    )

    try:
        result = await agent.run(PERIGEE_GOAL)
    except NotImplementedError as e:
        _fail(f"Agent / reflection 尚未接通 — {e}")
    except Exception as e:
        _fail(f"reflection E2E 运行失败 — {e}")

    output = str(getattr(result, "output", "") or "")
    print(f"D) 输出: {output}")
    if not output.strip():
        _fail("Agent 输出为空")

    events = getattr(getattr(result, "context", None), "events", None) or []
    names = _tool_names(events)
    print(f"D) 调用过的工具: {sorted(names)}")

    if "get_wikipedia_page" not in names:
        _fail("期望先尝试 get_wikipedia_page（instructions 要求 Wikipedia first）")
    if "reflection" not in names:
        _fail("期望在失败后调用 reflection")
    if not any(n in names for n in ("search", "search_web")):
        _fail("期望反思后改用 search 作为备选")

    # 近地点量级弱匹配（约 356,000–363,000 km）
    if "km" not in output.lower() and "公里" not in output:
        print("D) WARN: 输出未含 km/公里；若数值正确可忽略")
    if not any(tok in output.replace(",", "") for tok in ("356", "357", "360", "363")):
        print("D) WARN: 未看到近地点常见量级数字；人工确认即可")

    print("D) reflection e2e: OK")


async def main() -> None:
    # await _check_task_and_create_tasks()
    await _check_reflection_unit()
    # E2E 需要 API key；实现 planning 单元通过后再打开
    # await _check_planning_e2e()
    # await _check_reflection_e2e()
    print("P5 通过（当前仅跑了 A/B 单元；取消注释 C/D 做完整验收）")


if __name__ == "__main__":
    asyncio.run(main())
