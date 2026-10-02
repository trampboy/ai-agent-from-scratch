"""P6 — Code execution tool (E2B sandbox)."""

from __future__ import annotations

from typing import Any

from my_agent.tools import tool

@tool
async def execute_python(context, code: str) -> str:
    if context.code_env is None:
        raise RuntimeError('code_env 未设置')
    result = context.code_env.run_code(str)
    return result.to_json()