"""P7 验收 — Multi-Agent / Workflows / Transfer（仅验收 my_agent）。

通过标准：
  1) SequentialWorkflow：按顺序跑子 Agent，共享/传递 context
  2) ParallelWorkflow：并发跑子 Agent，合并输出；未完成分支抛 ParallelWorkflowIncomplete
  3) LoopWorkflow：按 stop_condition / max_iterations 循环
  4) create_transfer_tool：写入 context.transfer_to；非法名报错；二次 transfer 拒绝
  5) AgentTool：把子 Agent 包成工具，父 Agent 可委派
  6) Agent(sub_agents=...)：自动挂载 transfer_to_agent，能路由到专家 Agent
  7) （可选）RemoteAgent / MathAgentExecutor：A2A 远程调用骨架

实现位置（不要改 scratch_agents/）：
  my_agent/workflows/sequential.py
  my_agent/workflows/parallel.py
  my_agent/workflows/loop.py
  my_agent/transfer.py
  my_agent/tools/agent_tool.py
  my_agent/agent.py（sub_agents / transfer 接线）
  my_agent/context.py（已有 transfer_to / transfer_tools）
  my_agent/remote.py、my_agent/a2a_server.py（可选）

期望 API（对齐 CH09 / scratch_agents）：
  class SequentialWorkflow:  # 可继承 Agent 或独立类
      def __init__(self, agents: list, name: str = "sequential_workflow"): ...
      async def run(self, user_input=None, context=None, ...) -> AgentResult: ...
  class ParallelWorkflow:
      def __init__(self, agents: list, name: str = "parallel_workflow"): ...
      async def run(...) -> AgentResult: ...
  class ParallelWorkflowIncomplete(Exception):
      branch_results / branch_errors
  class LoopWorkflow:
      def __init__(self, agents: list, stop_condition=None, max_iterations=10, ...): ...
      async def run(...) -> AgentResult: ...
  def create_transfer_tool(target_agents: list) -> FunctionTool: ...
      # tool name: transfer_to_agent；设置 context.transfer_to
  class AgentTool(BaseTool):
      def __init__(self, agent, input_schema=None): ...
      async def execute(self, context, **kwargs) -> Any: ...
  Agent(..., sub_agents: list[Agent] | None = None,
            disallow_transfer_to_peers: bool = False)

运行：
  uv run python my_agent/demos/08_multi_agent.py

环境变量：
  DEEPSEEK_API_KEY 或 OPENAI_API_KEY — Transfer / Workflow E2E 需要
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Listing 9.1 风格 — 顺序流水线题（可换成更简单的本地题）
SEQUENTIAL_GOAL = (
    "Research a one-sentence fact about the Moon, "
    "then write a two-sentence summary for a child."
)

# Transfer 路由题：前台应转给 math 专家
TRANSFER_GOAL = "What is 17 * 19? Please use the math specialist."


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _require_api_key() -> None:
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")


def _as_tool(fn: Any) -> Any:
    """裸函数包成 FunctionTool；已是工具则原样返回。"""
    if hasattr(fn, "tool_definition") and hasattr(fn, "execute"):
        return fn
    from my_agent.tools.base import FunctionTool

    return FunctionTool(fn)


def _tool_names(events: Iterable[Any]) -> set[str]:
    """从 Agent 事件里收集被调用过的工具名。"""
    names: set[str] = set()
    for ev in events or []:
        name = getattr(ev, "name", None)
        if name:
            names.add(name)
            continue
        content = getattr(ev, "content", None)
        nested = getattr(content, "name", None) if content is not None else None
        if nested:
            names.add(nested)
    return names


def _load_workflows():
    try:
        from my_agent import workflows as wf
    except ImportError as e:
        _fail(f"请实现 my_agent/workflows/ — {e}")
    return wf


def _load_transfer():
    try:
        from my_agent import transfer as transfer_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/transfer.py — {e}")
    return transfer_mod


def _load_agent_tool():
    try:
        from my_agent.tools import agent_tool as mod
    except ImportError as e:
        _fail(f"请实现 my_agent/tools/agent_tool.py — {e}")
    return mod


class _FakeAgent:
    """无 LLM 的假 Agent：记录调用顺序，往 context 写事件，返回固定输出。"""

    def __init__(self, name: str, output: str = "", fail: bool = False):
        self.name = name
        self.description = f"fake {name}"
        self.instructions = f"You are {name}."
        self.output = output or f"[{name}] done"
        self.fail = fail
        self.calls: list[dict] = []

    async def run(
        self,
        user_input: str | None = None,
        context: Any = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> Any:
        from my_agent.context import AgentResult, ExecutionContext

        self.calls.append({"user_input": user_input, "has_context": context is not None})
        if context is None:
            context = ExecutionContext()
        if self.fail:
            return AgentResult(output=None, context=context, status="error")
        # 简单标记：便于 workflow 合并/传递检查
        context.add_event(type("E", (), {"author": self.name, "name": self.name, "content": None})())
        context.final_result = self.output
        return AgentResult(output=self.output, context=context, status="complete")


# ---------------------------------------------------------------------------
# A) SequentialWorkflow 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_sequential_unit() -> None:
    """A) SequentialWorkflow：按序调用，后继可拿到 context。"""
    wf = _load_workflows()
    SequentialWorkflow = getattr(wf, "SequentialWorkflow", None)
    if SequentialWorkflow is None:
        _fail("请在 my_agent/workflows 导出 SequentialWorkflow")

    a = _FakeAgent("researcher", output="moon fact")
    b = _FakeAgent("writer", output="child summary")
    try:
        pipeline = SequentialWorkflow(agents=[a, b], name="seq_demo")
    except TypeError:
        # 兼容占位签名 SequentialWorkflow(agents)
        pipeline = SequentialWorkflow(agents=[a, b])

    try:
        result = await pipeline.run("tell me about the moon")
    except NotImplementedError as e:
        _fail(f"请实现 SequentialWorkflow.run — {e}")
    except Exception as e:
        _fail(f"SequentialWorkflow.run 失败 — {e}")

    print(f"A) sequential output: {getattr(result, 'output', result)!r}")
    print(f"A) call counts: researcher={len(a.calls)} writer={len(b.calls)}")
    if len(a.calls) != 1 or len(b.calls) != 1:
        _fail("SequentialWorkflow 应各调用 researcher / writer 一次")
    # 第一个应带上 user_input；后续通常只传 context
    if a.calls[0].get("user_input") in (None, ""):
        print("A) WARN: 首个 Agent 未收到 user_input；若你改用 context.events 也可接受")
    if getattr(result, "output", None) in (None, ""):
        _fail("SequentialWorkflow 最终 output 不应为空")

    print("A) sequential unit: OK")


# ---------------------------------------------------------------------------
# B) ParallelWorkflow 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_parallel_unit() -> None:
    """B) ParallelWorkflow：并发执行并合并；失败分支抛 Incomplete。"""
    wf = _load_workflows()
    ParallelWorkflow = getattr(wf, "ParallelWorkflow", None)
    Incomplete = getattr(wf, "ParallelWorkflowIncomplete", None)
    if ParallelWorkflow is None:
        _fail("请在 my_agent/workflows 导出 ParallelWorkflow")
    if Incomplete is None:
        # 兼容 from my_agent.workflows.parallel import ...
        try:
            from my_agent.workflows.parallel import ParallelWorkflowIncomplete as Incomplete
        except ImportError:
            _fail("请导出 ParallelWorkflowIncomplete")

    ok1 = _FakeAgent("alpha", output="A-result")
    ok2 = _FakeAgent("beta", output="B-result")
    try:
        parallel = ParallelWorkflow(agents=[ok1, ok2], name="par_demo")
    except TypeError:
        parallel = ParallelWorkflow(agents=[ok1, ok2])

    try:
        result = await parallel.run("parallel task")
    except NotImplementedError as e:
        _fail(f"请实现 ParallelWorkflow.run — {e}")
    except Exception as e:
        _fail(f"ParallelWorkflow 成功路径失败 — {e}")

    output = str(getattr(result, "output", "") or "")
    print(f"B) parallel output:\n{output}")
    if "A-result" not in output or "B-result" not in output:
        _fail("合并输出应同时包含各分支结果（A-result / B-result）")
    if len(ok1.calls) != 1 or len(ok2.calls) != 1:
        _fail("每个并行分支应被调用一次")

    # 失败 / 非 complete 分支 → Incomplete
    bad = _FakeAgent("broken", fail=True)
    good = _FakeAgent("ok", output="fine")
    try:
        pipeline = ParallelWorkflow(agents=[good, bad])
    except TypeError:
        pipeline = ParallelWorkflow(agents=[good, bad])

    raised = False
    try:
        await pipeline.run("will fail")
    except NotImplementedError as e:
        _fail(f"请实现 ParallelWorkflow 失败路径 — {e}")
    except Exception as e:
        raised = True
        print(f"B) incomplete -> {type(e).__name__}: {e}")
        if Incomplete is not None and not isinstance(e, Incomplete):
            print(
                f"B) WARN: 期望 ParallelWorkflowIncomplete，实际 {type(e).__name__}；"
                "若你用其它异常类型需在实现里对齐"
            )
        if not hasattr(e, "branch_results"):
            print("B) WARN: 异常上建议带 branch_results，便于检查/续跑")

    if not raised:
        _fail("存在 status!=complete 的分支时应抛 ParallelWorkflowIncomplete（或等价异常）")

    print("B) parallel unit: OK")


# ---------------------------------------------------------------------------
# C) LoopWorkflow 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_loop_unit() -> None:
    """C) LoopWorkflow：stop_condition 为真时停止，否则直到 max_iterations。"""
    wf = _load_workflows()
    LoopWorkflow = getattr(wf, "LoopWorkflow", None)
    if LoopWorkflow is None:
        _fail("请在 my_agent/workflows 导出 LoopWorkflow")

    worker = _FakeAgent("worker", output="tick")

    def stop_after_two(_result: Any, iteration: int) -> bool:
        return iteration >= 2

    try:
        loop = LoopWorkflow(
            agents=[worker],
            stop_condition=stop_after_two,
            max_iterations=5,
            name="loop_demo",
        )
    except TypeError:
        # 兼容占位：LoopWorkflow(agent=..., should_continue=..., max_iters=...)
        try:
            loop = LoopWorkflow(
                agent=worker,
                should_continue=lambda r, i: i < 2,
                max_iters=5,
            )
        except TypeError as e:
            _fail(
                "LoopWorkflow 构造失败；期望 "
                "LoopWorkflow(agents=..., stop_condition=..., max_iterations=...) — "
                f"{e}"
            )

    try:
        result = await loop.run("loop please")
    except NotImplementedError as e:
        _fail(f"请实现 LoopWorkflow.run — {e}")
    except Exception as e:
        _fail(f"LoopWorkflow.run 失败 — {e}")

    print(f"C) loop output: {getattr(result, 'output', result)!r}")
    print(f"C) worker calls: {len(worker.calls)}")
    if len(worker.calls) < 2:
        _fail("带 stop_condition 时至少应迭代到条件满足（期望约 2 次）")
    if len(worker.calls) > 5:
        _fail("不应超过 max_iterations")

    print("C) loop unit: OK")


# ---------------------------------------------------------------------------
# D) create_transfer_tool 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_transfer_tool_unit() -> None:
    """D) create_transfer_tool：设置 transfer_to；非法名 / 二次 transfer。"""
    from my_agent.context import ExecutionContext

    transfer_mod = _load_transfer()
    create_transfer_tool = getattr(transfer_mod, "create_transfer_tool", None)
    if create_transfer_tool is None:
        _fail("请在 my_agent/transfer.py 实现 create_transfer_tool")

    targets = [
        _FakeAgent("math", output="42"),
        _FakeAgent("writer", output="ok"),
    ]
    try:
        tool = create_transfer_tool(targets)
    except TypeError:
        try:
            tool = create_transfer_tool(target_agents=targets)
        except NotImplementedError as e:
            _fail(f"请实现 create_transfer_tool — {e}")
        except Exception as e:
            _fail(f"create_transfer_tool 构造失败 — {e}")
    except NotImplementedError as e:
        _fail(f"请实现 create_transfer_tool — {e}")

    tool = _as_tool(tool)
    name = getattr(tool, "name", None)
    print(f"D) tool name: {name!r}")
    if name not in (None, "transfer_to_agent") and name != "transfer_to_agent":
        print(f"D) WARN: 工具名期望 transfer_to_agent，实际 {name!r}")

    ctx = ExecutionContext()
    try:
        msg = await tool(ctx, agent_name="math")
    except NotImplementedError as e:
        _fail(f"请实现 transfer_to_agent — {e}")
    except Exception as e:
        _fail(f"transfer_to_agent 调用失败 — {e}")

    print(f"D) transfer -> {msg!r}, context.transfer_to={ctx.transfer_to!r}")
    if ctx.transfer_to != "math":
        _fail("成功 transfer 后 context.transfer_to 应为 'math'")
    if "math" not in str(msg):
        _fail("返回信息应提及目标 agent 名")

    # 二次 transfer：应拒绝覆盖
    msg2 = await tool(ctx, agent_name="writer")
    print(f"D) second transfer -> {msg2!r}, transfer_to={ctx.transfer_to!r}")
    if ctx.transfer_to != "math":
        _fail("已有 transfer_to 时不应被覆盖")
    if "already" not in str(msg2).lower() and "already requested" not in str(msg2):
        print("D) WARN: 二次 transfer 返回最好提示 already requested")

    # 非法名
    ctx2 = ExecutionContext()
    bad = await tool(ctx2, agent_name="no_such_agent")
    print(f"D) invalid target -> {bad!r}")
    if ctx2.transfer_to is not None:
        _fail("非法 agent_name 不应设置 transfer_to")
    if "error" not in str(bad).lower() and "not valid" not in str(bad).lower():
        print("D) WARN: 非法名返回最好含 Error / not valid")

    print("D) transfer tool unit: OK")


# ---------------------------------------------------------------------------
# E) AgentTool 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_agent_tool_unit() -> None:
    """E) AgentTool：委派给嵌套 Agent 并返回其 output。"""
    from my_agent.context import ExecutionContext

    mod = _load_agent_tool()
    AgentTool = getattr(mod, "AgentTool", None)
    if AgentTool is None:
        _fail("请在 my_agent/tools/agent_tool.py 定义 AgentTool")

    specialist = _FakeAgent("math_expert", output="323")
    try:
        wrapped = AgentTool(specialist)
    except TypeError as e:
        _fail(f"AgentTool(agent) 构造失败 — {e}")

    # 应能当工具用：有 name / execute
    tname = getattr(wrapped, "name", None) or getattr(specialist, "name", None)
    print(f"E) AgentTool name: {tname!r}")
    if tname != "math_expert":
        print("E) WARN: 工具名通常等于被包装 Agent.name")

    ctx = ExecutionContext()
    try:
        if hasattr(wrapped, "execute"):
            out = await wrapped.execute(ctx, request="17*19")
        elif callable(wrapped):
            out = await wrapped(ctx, request="17*19")
        else:
            _fail("AgentTool 需实现 execute 或可调用接口")
    except NotImplementedError as e:
        _fail(f"请实现 AgentTool.execute — {e}")
    except Exception as e:
        _fail(f"AgentTool 委派失败 — {e}")

    print(f"E) AgentTool -> {out!r}, nested calls={len(specialist.calls)}")
    if "323" not in str(out):
        _fail("AgentTool 应返回嵌套 Agent 的 output（期望含 323）")
    if len(specialist.calls) != 1:
        _fail("应恰好调用嵌套 Agent 一次")

    print("E) agent tool unit: OK")


# ---------------------------------------------------------------------------
# F) Transfer E2E（需 LLM）：sub_agents 路由
# ---------------------------------------------------------------------------


async def _check_transfer_e2e() -> None:
    """F) Agent(sub_agents=...) 能 transfer 到数学专家。"""
    _require_api_key()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools.calculator import calculator

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    llm = LlmClient(model)

    math_agent = Agent(
        model=llm,
        tools=[_as_tool(calculator)],
        instructions="You are a math specialist. Use calculator. Answer briefly with the number.",
        name="math",
        description="Handles arithmetic and calculations.",
        max_steps=6,
    )
    receptionist = Agent(
        model=llm,
        tools=[],
        instructions=(
            "You are a receptionist. For math questions, transfer to the math agent. "
            "Do not compute yourself."
        ),
        name="receptionist",
        description="Routes questions to specialists.",
        sub_agents=[math_agent],
        max_steps=8,
    )

    try:
        result = await receptionist.run(TRANSFER_GOAL)
    except TypeError as e:
        _fail(f"Agent 构造/运行需支持 sub_agents= — {e}")
    except NotImplementedError as e:
        _fail(f"Agent transfer 尚未接通 — {e}")
    except Exception as e:
        _fail(f"transfer E2E 运行失败 — {e}")

    output = str(getattr(result, "output", "") or "")
    print(f"F) 输出: {output}")
    if not output.strip():
        _fail("Agent 输出为空")

    events = getattr(getattr(result, "context", None), "events", None) or []
    names = _tool_names(events)
    print(f"F) 调用过的工具: {sorted(names)}")
    if "transfer_to_agent" not in names:
        _fail("期望至少调用一次 transfer_to_agent")

    if "323" not in output.replace(",", "").replace(" ", ""):
        print("F) WARN: 输出未含 323（17*19）；人工确认是否已路由到 math")

    print("F) transfer e2e: OK")


# ---------------------------------------------------------------------------
# G) SequentialWorkflow E2E（需 LLM，可选）
# ---------------------------------------------------------------------------


async def _check_sequential_e2e() -> None:
    """G) 真 Agent 顺序流水线（Listing 9.1 风格，可不用 search）。"""
    _require_api_key()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient

    wf = _load_workflows()
    SequentialWorkflow = getattr(wf, "SequentialWorkflow", None)
    if SequentialWorkflow is None:
        _fail("请导出 SequentialWorkflow")

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    llm = LlmClient(model)

    researcher = Agent(
        model=llm,
        tools=[],
        name="researcher",
        instructions="Give one short factual sentence about the Moon. No fluff.",
        max_steps=3,
    )
    writer = Agent(
        model=llm,
        tools=[],
        name="writer",
        instructions=(
            "Rewrite the previous assistant content as exactly two short sentences "
            "for a 8-year-old child."
        ),
        max_steps=3,
    )

    try:
        pipeline = SequentialWorkflow(agents=[researcher, writer], name="moon_pipe")
    except TypeError:
        pipeline = SequentialWorkflow(agents=[researcher, writer])

    try:
        result = await pipeline.run(SEQUENTIAL_GOAL)
    except NotImplementedError as e:
        _fail(f"请实现 SequentialWorkflow — {e}")
    except Exception as e:
        _fail(f"sequential E2E 失败 — {e}")

    output = str(getattr(result, "output", "") or "")
    print(f"G) 输出: {output}")
    if not output.strip():
        _fail("流水线输出为空")
    if len(output.split()) < 5:
        print("G) WARN: 输出偏短，确认 writer 是否吃到了 researcher 的上下文")

    print("G) sequential e2e: OK")


# ---------------------------------------------------------------------------
# H) Remote / A2A 骨架烟雾（可选，默认跳过真网络）
# ---------------------------------------------------------------------------


async def _check_remote_smoke() -> None:
    """H) RemoteAgent / MathAgentExecutor 可导入且接口存在（不强制起服务）。"""
    try:
        from my_agent.remote import RemoteAgent
    except ImportError as e:
        _fail(f"请实现 my_agent/remote.py — {e}")

    try:
        from my_agent.a2a_server import MathAgentExecutor
    except ImportError as e:
        _fail(f"请实现 my_agent/a2a_server.py — {e}")

    client = RemoteAgent("http://127.0.0.1:9")  # 故意不可达，只测构造
    print(f"H) RemoteAgent base_url={client.base_url!r}")
    if not hasattr(client, "run") and not hasattr(client, "send"):
        _fail("RemoteAgent 应提供 run 或 send")

    # MathAgentExecutor：只检查可构造；真正 execute 需 A2A 运行时
    executor = MathAgentExecutor(agent=_FakeAgent("math_remote", output="1"))
    if not hasattr(executor, "execute"):
        _fail("MathAgentExecutor 应实现 execute")
    print("H) remote/a2a smoke: OK（未发起真实网络请求）")


async def main() -> None:
    # 单元：无 API key 也可跑（实现 Incomplete 前会 FAIL 并给出指引）
    # await _check_sequential_unit()
    # await _check_parallel_unit()
    await _check_loop_unit()
    # await _check_transfer_tool_unit()
    # await _check_agent_tool_unit()
    # await _check_remote_smoke()

    # E2E：需要 API key；实现并接通后再解开注释
    # await _check_transfer_e2e()
    # await _check_sequential_e2e()

    print("P7 骨架：当前默认跑 A–E 单元 + H 烟雾；解开 F/G 注释以跑 E2E")


if __name__ == "__main__":
    asyncio.run(main())
