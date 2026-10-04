"""P8 — GAIA-style evaluation helpers."""

from __future__ import annotations

from typing import Any
import os
from pydantic import BaseModel, Field
from my_agent.agent import Agent
from my_agent.llm import LlmClient
from my_agent.tools.calculator import calculator
import asyncio

class GaiaOutput(BaseModel):
    is_solvable: bool=Field(description="是否可解决")
    final_answer: str = Field(description="最终答案")
    unsolvable_reason: str = Field(default="", description="不可解决的原因")

def is_correct(pred:str | None, ans:str | None):
    if pred is None or ans is None:
        return pred == ans
    return pred.strip().lower() == ans.strip().lower()


def _as_tool(fn: Any) -> Any:
    """裸函数包成 FunctionTool；已是工具则原样返回。"""
    if hasattr(fn, "tool_definition") and hasattr(fn, "execute"):
        return fn
    from my_agent.tools.base import FunctionTool

    return FunctionTool(fn)

async def run_gaia_sample(problems: list = [], models: list=[]) -> Any:
    if not problems:
        return {
            "deepseek/deepseek-chat": []
        }

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
        raise RuntimeError(f"Agent 构造失败 — {e}")
        
    branch_results = await asyncio.gather(
                *[  
                    agent.run(problem['Question'])
                    for problem in problems
                ],
                return_exceptions=True
            )
    return {
        "deepseek/deepseek-chat": [
            {
                "task_id": problem['task_id'],
                "model": "deepseek/deepseek-chat",
                "correct": is_correct(branch_result.output, problem['Final answer']),
                "prediction": branch_result.output,
                "answer": problem['Final answer'],
            }
            for problem, branch_result in zip(problems, branch_results)
        ]
    }
