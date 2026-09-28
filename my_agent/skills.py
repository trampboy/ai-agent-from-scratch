"""P6 — Skills discovery and prompt injection."""

from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel


class SkillInfo(BaseModel):
    # TODO(P6): name, description, path, etc.
    pass


def discover_skills(skills_path: str) -> List[SkillInfo]:
    raise NotImplementedError("P6: scan skills directory")


def generate_skills_prompt(skills: List[SkillInfo]) -> str:
    raise NotImplementedError("P6: build skills section for system prompt")
