"""P8 — GAIA-style evaluation helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

class GaiaOutput(BaseModel):
    is_solvable: bool=Field(description="是否可解决")
    final_answer: str = Field(description="最终答案")
    unsolvable_reason: str = Field(default="", description="不可解决的原因")

def is_correct(pred:str | None, ans:str | None):
    if pred is None or ans is None:
        return pred == ans
    return pred.strip().lower() == ans.strip().lower()

async def run_gaia_sample(**kwargs: Any) -> Any:
    raise NotImplementedError("P8: load GAIA sample and score agent answers")
