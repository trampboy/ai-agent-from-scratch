"""P6 — Code execution tool (E2B sandbox)."""

from __future__ import annotations

from typing import Any

from my_agent.tools import tool
import json

@tool
async def execute_python(context, code: str) -> str:
    """Execute Python code in a sandboxed environment. 
    Use this to perform calculations, data processing, or any Python operations.
    """
    if context.code_env is None:
        raise RuntimeError('code_env 未设置')
    result = context.code_env.run_code(code)
    return json.dumps(result.to_json(), indent=2, ensure_ascii=False)