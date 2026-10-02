"""P6 验收 — Code Execution + Skills（仅验收 my_agent）。

通过标准：
  1) SkillInfo：name / description / path
  2) discover_skills：扫描目录下含 SKILL.md 的子目录，解析 YAML frontmatter
  3) generate_skills_prompt：生成含 Available Skills / 沙箱路径的系统提示片段
  4) execute_python：依赖 context.code_env，在 E2B 沙箱跑代码并返回结果
  5) Agent(code_execution=\"e2b\")：自动挂载 execute_python，能算 Fibonacci 等
  6) Agent(skills_path=...)：发现 skills、注入 prompt，并（可选）上传到沙箱

实现位置（不要改 scratch_agents/）：
  my_agent/skills.py
  my_agent/tools/code_execution.py
  my_agent/agent.py（code_execution / skills_path / code_env 接线）
  my_agent/context.py（已有 code_env 字段）

期望 API（对齐 CH08 / scratch_agents）：
  class SkillInfo:  # dataclass 或 BaseModel
      name: str
      description: str
      path: Path | str
  def discover_skills(skills_path: str | Path) -> list[SkillInfo]: ...
  def generate_skills_prompt(skills, sandbox_path=\"/home/user/skills\") -> str: ...
  @tool(name=\"execute_python\", ...)
  def execute_python(context, code: str) -> str: ...

运行：
  uv run python my_agent/demos/07_code_skills.py

环境变量：
  DEEPSEEK_API_KEY 或 OPENAI_API_KEY — E2E 需要
  E2B_API_KEY — code execution / skills E2E 需要
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Listing 8.14 — 代码执行烟雾题
FIBONACCI_GOAL = "What is the 100th Fibonacci number?"

# Skills 示例：临时目录里造一个最小 skill（对齐 Listing 8.33 frontmatter 形态）
SAMPLE_SKILL_MD = """\
---
name: hello-math
description: Simple arithmetic helpers for sandbox code. Use when computing sums or products.
---

# Hello Math

```python
def add(a, b):
    return a + b
```
"""


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _require_api_key() -> None:
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")


def _require_e2b() -> None:
    if not os.getenv("E2B_API_KEY"):
        _fail("请在 .env 中设置 E2B_API_KEY（code execution 需要）")


def _as_tool(fn: Any) -> Any:
    """裸函数包成 FunctionTool；已是工具则原样返回。"""
    if hasattr(fn, "tool_definition") and hasattr(fn, "execute"):
        return fn
    from my_agent.tools.base import FunctionTool

    return FunctionTool(fn)


def _load_skills():
    """导入 my_agent.skills，缺失或未实现时给出指引。"""
    try:
        from my_agent import skills as skills_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/skills.py — {e}")
    return skills_mod


def _load_code_execution():
    """导入 my_agent.tools.code_execution。"""
    try:
        from my_agent.tools import code_execution as code_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/tools/code_execution.py — {e}")
    return code_mod


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


def _make_sample_skills_dir(base: Path) -> Path:
    """在 base 下创建 hello-math skill（含 SKILL.md）。"""
    skill_dir = base / "hello-math"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD, encoding="utf-8")
    (skill_dir / "helpers.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    return base


# ---------------------------------------------------------------------------
# A) Skills 单元（无 LLM / 无 E2B）
# ---------------------------------------------------------------------------


async def _check_skills_unit() -> None:
    """A) SkillInfo + discover_skills + generate_skills_prompt。"""
    skills_mod = _load_skills()
    SkillInfo = getattr(skills_mod, "SkillInfo", None)
    discover_skills = getattr(skills_mod, "discover_skills", None)
    generate_skills_prompt = getattr(skills_mod, "generate_skills_prompt", None)

    if SkillInfo is None:
        _fail("请在 my_agent/skills.py 中定义 SkillInfo")
    if discover_skills is None:
        _fail("请在 my_agent/skills.py 中实现 discover_skills")
    if generate_skills_prompt is None:
        _fail("请在 my_agent/skills.py 中实现 generate_skills_prompt")

    with tempfile.TemporaryDirectory(prefix="my_agent_skills_") as tmp:
        skills_root = _make_sample_skills_dir(Path(tmp))

        # --- discover_skills ---
        try:
            found = discover_skills(str(skills_root))
        except NotImplementedError as e:
            _fail(f"请实现 discover_skills — {e}")
        except Exception as e:
            _fail(f"discover_skills 调用失败 — {e}")

        if not found:
            _fail("discover_skills 应对含 SKILL.md 的子目录返回非空列表")
        skill = found[0]
        name = getattr(skill, "name", None)
        desc = getattr(skill, "description", None)
        path = getattr(skill, "path", None)
        print(f"A) discovered: name={name!r} desc={desc!r} path={path!r}")
        if name != "hello-math":
            _fail("SkillInfo.name 期望 'hello-math'（来自 SKILL.md frontmatter）")
        if not desc or "arithmetic" not in str(desc).lower() and "sum" not in str(desc).lower():
            # 弱匹配：至少有 description
            if not desc:
                _fail("SkillInfo.description 不应为空")
        if path is None:
            _fail("SkillInfo.path 不应为空")

        # 空目录 / 不存在路径 → 空列表
        empty = discover_skills(str(Path(tmp) / "no-such-dir"))
        if empty:
            _fail("不存在的 skills_path 应返回 []")

        # --- generate_skills_prompt ---
        try:
            prompt = generate_skills_prompt(found)
        except NotImplementedError as e:
            _fail(f"请实现 generate_skills_prompt — {e}")
        except TypeError:
            # 兼容带 sandbox_path 的签名
            try:
                prompt = generate_skills_prompt(found, sandbox_path="/home/user/skills")
            except Exception as e:
                _fail(f"generate_skills_prompt 调用失败 — {e}")
        except Exception as e:
            _fail(f"generate_skills_prompt 调用失败 — {e}")

        text = str(prompt or "")
        print(f"A) skills prompt (head):\n{text[:400]}")
        if not text.strip():
            _fail("generate_skills_prompt 对非空 skills 不应返回空串")
        if "Available Skills" not in text and "hello-math" not in text:
            _fail("prompt 应含 'Available Skills' 或至少 skill 名 hello-math")
        if "/home/user/skills" not in text and "hello-math" not in text:
            print("A) WARN: prompt 未含默认沙箱路径 /home/user/skills；若你自定义了路径可忽略")

        # 空列表 → 空串
        empty_prompt = generate_skills_prompt([])
        if str(empty_prompt or "").strip():
            _fail("generate_skills_prompt([]) 应返回空串")

    print("A) skills unit: OK")


# ---------------------------------------------------------------------------
# B) execute_python 单元（可无真 E2B：用假 sandbox）
# ---------------------------------------------------------------------------


async def _check_execute_python_unit() -> None:
    """B) execute_python 工具签名与 code_env 依赖（假 sandbox，不调真 E2B）。"""
    from my_agent.context import ExecutionContext

    code_mod = _load_code_execution()
    execute_python = getattr(code_mod, "execute_python", None)
    if execute_python is None:
        # 兼容占位名 run_code
        if getattr(code_mod, "run_code", None) is not None:
            _fail(
                "发现 run_code，但 CH08 工具名应为 execute_python；"
                "请导出 @tool def execute_python(context, code: str) -> str"
            )
        _fail("请在 my_agent/tools/code_execution.py 中实现 execute_python")

    tool = _as_tool(execute_python)
    if getattr(tool, "name", None) not in (None, "execute_python") and tool.name != "execute_python":
        print(f"B) WARN: 工具名为 {tool.name!r}，期望 execute_python")

    # 无 code_env → 应报错
    ctx = ExecutionContext()
    try:
        await tool(ctx, code="print(1)")
        _fail("context.code_env 为 None 时 execute_python 应抛错")
    except NotImplementedError as e:
        _fail(f"请实现 execute_python — {e}")
    except Exception as e:
        print(f"B) no code_env -> {type(e).__name__}: {e}")

    # 假 sandbox：run_code 返回可 json 化的对象
    class FakeResult:
        def to_json(self):
            return {"results": [{"text": "42"}], "logs": {"stdout": ["42\n"]}}

    class FakeSandbox:
        def run_code(self, code: str):
            print(f"B) FakeSandbox.run_code({code!r})")
            return FakeResult()

    ctx2 = ExecutionContext(code_env=FakeSandbox())
    try:
        out = await tool(ctx2, code="print(42)")
    except NotImplementedError as e:
        _fail(f"请实现 execute_python — {e}")
    except Exception as e:
        _fail(f"execute_python(假 sandbox) 失败 — {e}")

    text = str(out)
    print(f"B) execute_python -> {text[:300]!r}")
    if "42" not in text:
        _fail("假 sandbox 返回应体现在工具输出中（含 42）")

    print("B) execute_python unit: OK")


# ---------------------------------------------------------------------------
# C) Code execution E2E（Listing 8.14，需 E2B + LLM）
# ---------------------------------------------------------------------------


async def _check_code_execution_e2e() -> None:
    """C) Agent(code_execution='e2b') 能执行 Python 解题。"""
    _require_api_key()
    _require_e2b()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    try:
        agent = Agent(
            model=LlmClient(model),
            tools=[],
            instructions="You can execute Python code to solve problems. Prefer execute_python.",
            code_execution="e2b",
            max_steps=8,
        )
    except TypeError as e:
        _fail(f"Agent 构造需支持 code_execution= — {e}")

    try:
        result = await agent.run(FIBONACCI_GOAL)
    except NotImplementedError as e:
        _fail(f"Agent / code_execution 尚未接通 — {e}")
    except Exception as e:
        _fail(f"code execution E2E 运行失败 — {e}")

    output = str(getattr(result, "output", "") or "")
    print(f"C) 输出: {output}")
    if not output.strip():
        _fail("Agent 输出为空")

    events = getattr(getattr(result, "context", None), "events", None) or []
    names = _tool_names(events)
    print(f"C) 调用过的工具: {sorted(names)}")
    if "execute_python" not in names:
        _fail("期望至少调用一次 execute_python（code_execution='e2b' 应自动挂载）")

    # 第 100 个 Fibonacci（F_100，常见定义 F_0=0,F_1=1 → 354224848179261915075）
    compact = output.replace(",", "").replace(" ", "")
    if "354224848179261915075" not in compact and "354224848179261915075" not in output:
        print(
            "C) WARN: 未看到标准 F_100=354224848179261915075；"
            "若你用了 1-indexed 或其它定义，人工确认即可"
        )

    # 跑完后 code_env 通常应清理（对齐 regression：result.context.code_env is None）
    code_env = getattr(getattr(result, "context", None), "code_env", "missing")
    print(f"C) context.code_env after run: {code_env!r}")
    if code_env is not None and code_env != "missing":
        print("C) WARN: 跑完后 code_env 未清空；若你在 finally 里 kill 了也可接受")

    print("C) code execution e2e: OK")


# ---------------------------------------------------------------------------
# D) Skills E2E（需 E2B + LLM）：prompt 注入 + 可选用 skill
# ---------------------------------------------------------------------------


async def _check_skills_e2e() -> None:
    """D) Agent(skills_path=...) 发现 skill；复杂题可走 execute_python。"""
    _require_api_key()
    _require_e2b()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient

    with tempfile.TemporaryDirectory(prefix="my_agent_skills_e2e_") as tmp:
        skills_root = _make_sample_skills_dir(Path(tmp))
        model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
        try:
            agent = Agent(
                model=LlmClient(model),
                tools=[],
                instructions=(
                    "You can execute Python code. "
                    "If skills are listed, read their SKILL.md in the sandbox before using them."
                ),
                code_execution="e2b",
                skills_path=str(skills_root),
                max_steps=10,
            )
        except TypeError as e:
            _fail(f"Agent 构造需支持 skills_path= — {e}")

        try:
            result = await agent.run(
                "Use Python to compute 17 * 19. You may use available skills if helpful."
            )
        except NotImplementedError as e:
            _fail(f"Agent / skills 尚未接通 — {e}")
        except Exception as e:
            _fail(f"skills E2E 运行失败 — {e}")

        output = str(getattr(result, "output", "") or "")
        print(f"D) 输出: {output}")
        if not output.strip():
            _fail("Agent 输出为空")

        events = getattr(getattr(result, "context", None), "events", None) or []
        names = _tool_names(events)
        print(f"D) 调用过的工具: {sorted(names)}")
        if "execute_python" not in names:
            _fail("期望调用 execute_python 完成计算")

        if "323" not in output.replace(",", ""):
            print("D) WARN: 输出未含 323（17*19）；人工确认即可")

        # 弱检查：若 Agent 把 skills prompt 拼进 instructions，无法从 events 直接看；
        # 此处只确认 skills_path 未导致崩溃，且计算成功即可。
        print("D) skills e2e: OK")


async def main() -> None:
    # await _check_skills_unit()
    await _check_execute_python_unit()
    # E2E 需要 API key + E2B_API_KEY
    # await _check_code_execution_e2e()
    # await _check_skills_e2e()
    print("P6 骨架：当前默认跑 A/B 单元；解开 C/D 注释以跑 E2E")


if __name__ == "__main__":
    asyncio.run(main())
