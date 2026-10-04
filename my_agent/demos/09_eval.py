"""P8 验收 — Evaluation（仅验收 my_agent）。

通过标准：
  1) prompts：评测提示词可导入，且含 question/answer 等占位符
  2) is_correct：大小写不敏感的 exact match；None → False
  3) GaiaOutput：结构化输出字段齐全（is_solvable / final_answer / ...）
  4) OPR：(# passed) / (total evaluations)
  5) 自建用例：Agent + calculator 跑一小撮算术题，用 is_correct 打分
  6) （可选）run_gaia_sample / run_experiment：对 GAIA 子集或自建问题跑评测

实现位置（不要改 scratch_agents/）：
  my_agent/eval/prompts.py
  my_agent/eval/gaia.py
  my_agent/eval/__init__.py（按需 re-export）

期望 API（对齐 CH10 / scratch_agents.eval）：
  # prompts.py
  ANSWER_RELEVANCY_PROMPT: str          # {question} {answer}
  CITATION_RELIABILITY_PROMPT: str      # {question} {answer} {sources}
  REQUIREMENT_COMPLIANCE_PROMPT: str    # {question} {requirements} {answer}
  EVALUATION_SYSTEM_PROMPT: str

  # gaia.py
  class GaiaOutput(BaseModel):
      is_solvable: bool
      unsolvable_reason: str = ""
      final_answer: str = ""
  def is_correct(prediction: str | None, answer: str) -> bool: ...
  async def evaluate_gaia_single(problem: dict, model: str) -> dict: ...
  async def run_experiment(problems, models, tools=None) -> dict[str, list]: ...
  # 教学简化入口（可包一层自建用例，不必真拉 GAIA 全集）：
  async def run_gaia_sample(**kwargs) -> Any: ...

运行：
  uv run python my_agent/demos/09_eval.py

环境变量：
  DEEPSEEK_API_KEY 或 OPENAI_API_KEY — E2E / LLM-as-judge 需要
  MY_AGENT_MODEL — 默认 deepseek/deepseek-chat
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# 自建评测用例（对齐 ch10 Listing：不用拉完整 GAIA 也能验收打分链路）
# ---------------------------------------------------------------------------

SAMPLE_CASES: list[dict[str, str]] = [
    {"question": "What is 7 * 8?", "answer": "56"},
    {"question": "What is 15 + 27?", "answer": "42"},
    {"question": "What is 100 / 4?", "answer": "25"},
]

# OPR 演示用假结果（对齐 ch10 §10.5）
SAMPLE_OPR_RESULTS: list[dict[str, Any]] = [
    {"metric": "answer_relevancy", "score": 0.95, "passed": True},
    {"metric": "citation_reliability", "score": 0.80, "passed": True},
    {"metric": "requirement_compliance", "score": 0.60, "passed": False},
    {"metric": "answer_relevancy", "score": 1.00, "passed": True},
    {"metric": "citation_reliability", "score": 0.45, "passed": False},
]


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _require_api_key() -> None:
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        _fail("请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")


def _load_prompts():
    """导入 my_agent.eval.prompts。"""
    try:
        from my_agent.eval import prompts as prompts_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/eval/prompts.py — {e}")
    return prompts_mod


def _load_gaia():
    """导入 my_agent.eval.gaia。"""
    try:
        from my_agent.eval import gaia as gaia_mod
    except ImportError as e:
        _fail(f"请实现 my_agent/eval/gaia.py — {e}")
    return gaia_mod


def _as_tool(fn: Any) -> Any:
    """裸函数包成 FunctionTool；已是工具则原样返回。"""
    if hasattr(fn, "tool_definition") and hasattr(fn, "execute"):
        return fn
    from my_agent.tools.base import FunctionTool

    return FunctionTool(fn)


# ---------------------------------------------------------------------------
# A) prompts 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_prompts_unit() -> None:
    """A) 评测提示词存在，且 format 占位符齐全。"""
    prompts_mod = _load_prompts()

    required = {
        "ANSWER_RELEVANCY_PROMPT": ("question", "answer"),
        "CITATION_RELIABILITY_PROMPT": ("question", "answer", "sources"),
        "REQUIREMENT_COMPLIANCE_PROMPT": ("question", "requirements", "answer"),
        "EVALUATION_SYSTEM_PROMPT": (),
    }

    for name, keys in required.items():
        text = getattr(prompts_mod, name, None)
        if text is None:
            _fail(f"请在 my_agent/eval/prompts.py 中定义 {name}")
        if not isinstance(text, str) or not text.strip():
            _fail(f"{name} 应为非空 str")
        if "TODO" in text:
            _fail(f"{name} 仍是占位 TODO，请写入正式评测提示词")
        for key in keys:
            placeholder = "{" + key + "}"
            if placeholder not in text:
                _fail(f"{name} 应包含占位符 {placeholder}")
        # 烟雾：format 不抛 KeyError
        if keys:
            try:
                text.format(**{k: f"<{k}>" for k in keys})
            except KeyError as e:
                _fail(f"{name}.format 失败 — 缺少键 {e}")

    print("A) prompts unit: OK")


# ---------------------------------------------------------------------------
# B) is_correct + GaiaOutput 单元（无 LLM）
# ---------------------------------------------------------------------------


async def _check_scoring_unit() -> None:
    """B) is_correct 与 GaiaOutput 契约。"""
    gaia_mod = _load_gaia()

    is_correct = getattr(gaia_mod, "is_correct", None)
    GaiaOutput = getattr(gaia_mod, "GaiaOutput", None)

    if is_correct is None:
        _fail("请在 my_agent/eval/gaia.py 中实现 is_correct")
    if GaiaOutput is None:
        _fail("请在 my_agent/eval/gaia.py 中定义 GaiaOutput")

    # --- is_correct ---
    cases = [
        ("56", "56", True),
        (" 56 ", "56", True),
        ("Paris", "paris", True),
        ("56", "57", False),
        (None, "56", False),
        ("", "56", False),
    ]
    for pred, ans, expect in cases:
        try:
            got = is_correct(pred, ans)
        except NotImplementedError as e:
            _fail(f"请实现 is_correct — {e}")
        if got is not expect:
            _fail(f"is_correct({pred!r}, {ans!r}) 期望 {expect}，得到 {got}")

    # --- GaiaOutput ---
    try:
        out = GaiaOutput(is_solvable=True, final_answer="56")
    except Exception as e:
        _fail(f"GaiaOutput 构造失败 — {e}")

    if getattr(out, "is_solvable", None) is not True:
        _fail("GaiaOutput.is_solvable 应可读")
    if getattr(out, "final_answer", None) != "56":
        _fail("GaiaOutput.final_answer 应可读")
    # unsolvable_reason 默认空串
    reason = getattr(out, "unsolvable_reason", None)
    if reason is None:
        _fail("GaiaOutput 应有 unsolvable_reason 字段")

    print(f"B) GaiaOutput sample: {out!r}")
    print("B) scoring unit: OK")


# ---------------------------------------------------------------------------
# C) OPR 计算（无 LLM；可放在 demo 内或 gaia/prompts 辅助函数）
# ---------------------------------------------------------------------------


def _overall_pass_rate(results: list[dict[str, Any]]) -> float:
    """OPR = (# passed) / total。优先用 my_agent.eval 导出的实现。"""
    gaia_mod = _load_gaia()
    fn = getattr(gaia_mod, "overall_pass_rate", None) or getattr(
        gaia_mod, "compute_opr", None
    )
    if callable(fn):
        return float(fn(results))

    # 骨架兜底：demo 内联（实现 P8 时建议挪进 eval/）
    if not results:
        return 0.0
    passed = sum(1 for r in results if r.get("passed"))
    return passed / len(results)


async def _check_opr_unit() -> None:
    """C) Overall Pass Rate。"""
    opr = _overall_pass_rate(SAMPLE_OPR_RESULTS)
    # 样例：3/5 = 0.6
    print(f"C) OPR: {opr:.1%} ({sum(1 for r in SAMPLE_OPR_RESULTS if r['passed'])}"
          f"/{len(SAMPLE_OPR_RESULTS)})")
    if abs(opr - 0.6) > 1e-9:
        _fail(f"SAMPLE_OPR_RESULTS 的 OPR 期望 0.6，得到 {opr}")

    if _overall_pass_rate([]) != 0.0:
        _fail("空结果列表的 OPR 应为 0.0")

    print("C) opr unit: OK")


# ---------------------------------------------------------------------------
# D) LLM-as-judge 烟雾（需要 API；可选）
# ---------------------------------------------------------------------------


async def _check_llm_judge_smoke() -> None:
    """D) 用 ANSWER_RELEVANCY_PROMPT + EVALUATION_SYSTEM_PROMPT 打一次分。"""
    _require_api_key()

    from my_agent.llm import LlmClient, LlmRequest
    from my_agent.types import Message

    prompts_mod = _load_prompts()
    relevancy = getattr(prompts_mod, "ANSWER_RELEVANCY_PROMPT", None)
    system = getattr(prompts_mod, "EVALUATION_SYSTEM_PROMPT", None)
    if not relevancy or not system:
        _fail("缺少 ANSWER_RELEVANCY_PROMPT / EVALUATION_SYSTEM_PROMPT")

    filled = relevancy.format(
        question="What is the capital of France?",
        answer="Paris is the capital of France.",
    )
    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    llm = LlmClient(model=model)

    try:
        request = LlmRequest(
            instructions=[system],
            contents=[Message(role="user", content=filled)],
        )
        response = await llm.generate(request)
    except NotImplementedError as e:
        _fail(f"请实现 LlmClient.generate — {e}")
    except Exception as e:
        _fail(f"LLM-as-judge 调用失败 — {e}")

    # 兼容 content 为 list[Event] 或 str
    content = getattr(response, "content", response)
    if isinstance(content, list) and content:
        text = str(getattr(content[0], "content", content[0]))
    else:
        text = str(content)

    print(f"D) judge 输出 (head):\n{text[:400]}")
    if not text.strip():
        _fail("judge 输出为空")

    print("D) llm judge smoke: OK")


# ---------------------------------------------------------------------------
# E) 自建用例 Agent 评测（需要 API）
# ---------------------------------------------------------------------------


async def _check_custom_cases_e2e() -> None:
    """E) Agent + calculator 跑 SAMPLE_CASES，用 is_correct 汇总准确率。"""
    _require_api_key()

    from my_agent.agent import Agent
    from my_agent.llm import LlmClient
    from my_agent.tools.calculator import calculator

    gaia_mod = _load_gaia()
    is_correct = getattr(gaia_mod, "is_correct", None)
    if is_correct is None:
        _fail("请先实现 is_correct（见 B）")

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    try:
        agent = Agent(
            model=LlmClient(model),
            tools=[_as_tool(calculator)],
            instructions=(
                "You are a general AI assistant. "
                "Use the calculator tool for math. "
                "Answer with as few words as possible; prefer the bare number."
            ),
            max_steps=5,
        )
    except Exception as e:
        _fail(f"Agent 构造失败 — {e}")

    correct_count = 0
    for tc in SAMPLE_CASES:
        try:
            result = await agent.run(tc["question"])
        except NotImplementedError as e:
            _fail(f"Agent.run 未实现 — {e}")
        except Exception as e:
            _fail(f"跑题失败 Q={tc['question']!r} — {e}")

        prediction = str(getattr(result, "output", "") or "")
        # 宽松一点：答案可能夹在句子里，先试 exact，再试子串
        ok = is_correct(prediction, tc["answer"])
        if not ok and tc["answer"] in prediction.replace(",", ""):
            ok = True
        correct_count += int(ok)
        print(
            f"E) Q={tc['question']!r} pred={prediction[:80]!r} "
            f"ans={tc['answer']!r} correct={ok}"
        )

    accuracy = correct_count / len(SAMPLE_CASES)
    print(f"E) Accuracy: {correct_count}/{len(SAMPLE_CASES)} ({accuracy:.0%})")
    if correct_count < 2:
        _fail("自建算术用例至少应做对 2/3（检查 calculator / Agent / is_correct）")

    print("E) custom cases e2e: OK")


# ---------------------------------------------------------------------------
# F) GAIA / run_experiment 骨架（可选；可先只接自建 problems）
# ---------------------------------------------------------------------------


async def _check_gaia_sample() -> None:
    """F) run_gaia_sample 或 run_experiment 对一小撮问题产出按 model 分组的结果。"""
    _require_api_key()

    gaia_mod = _load_gaia()
    run_gaia_sample = getattr(gaia_mod, "run_gaia_sample", None)
    run_experiment = getattr(gaia_mod, "run_experiment", None)

    model = os.getenv("MY_AGENT_MODEL", "deepseek/deepseek-chat")
    # 自建 problems，字段名对齐 GAIA：Question / Final answer / task_id
    problems = [
        {
            "task_id": f"sample-{i}",
            "Question": tc["question"],
            "Final answer": tc["answer"],
        }
        for i, tc in enumerate(SAMPLE_CASES)
    ]

    results: Any = None
    if callable(run_gaia_sample):
        try:
            results = await run_gaia_sample(problems=problems, models=[model])
        except NotImplementedError as e:
            _fail(f"请实现 run_gaia_sample — {e}")
        except TypeError:
            # 允许更自由的 kwargs
            try:
                results = await run_gaia_sample()
            except NotImplementedError as e:
                _fail(f"请实现 run_gaia_sample — {e}")
            except Exception as e:
                _fail(f"run_gaia_sample 失败 — {e}")
        except Exception as e:
            _fail(f"run_gaia_sample 失败 — {e}")
    elif callable(run_experiment):
        try:
            results = await run_experiment(problems, [model])
        except NotImplementedError as e:
            _fail(f"请实现 run_experiment — {e}")
        except Exception as e:
            _fail(f"run_experiment 失败 — {e}")
    else:
        _fail("请实现 run_gaia_sample 或 run_experiment")

    print(f"F) results type={type(results).__name__} value(head)={str(results)[:300]!r}")
    if not results:
        _fail("评测结果不应为空")

    # 期望 dict[model] -> list[result]，每条含 correct / prediction / answer
    if isinstance(results, dict):
        rows = results.get(model) or next(iter(results.values()), [])
    elif isinstance(results, list):
        rows = results
    else:
        _fail("结果应为 dict[str, list] 或 list")

    if not rows:
        _fail("结果列表为空")

    sample = rows[0]
    if not isinstance(sample, dict):
        _fail("单条结果应为 dict")
    for key in ("correct", "prediction", "answer"):
        if key not in sample:
            print(f"F) WARN: 单条结果缺少键 {key!r}（建议对齐 evaluate_gaia_single）")

    print("F) gaia sample: OK")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


async def main() -> None:
    # 单元（无 API）
    # await _check_prompts_unit()
    # await _check_scoring_unit()
    # await _check_opr_unit()

    # E2E（需要 API）— 按需解开
    # await _check_llm_judge_smoke()
    # await _check_custom_cases_e2e()
    await _check_gaia_sample()

    print("P8 骨架：当前默认跑 A/B/C 单元；解开 D/E/F 注释以跑 E2E")


if __name__ == "__main__":
    asyncio.run(main())
