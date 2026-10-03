"""P6 — Skills discovery and prompt injection."""

from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field
from pathlib import Path
import re


class SkillInfo(BaseModel):
    name: str = Field(description="Skill 名称")
    description: str = Field(description="Skill 描述")
    path: Path = Field(description="Skill 地址")

# SAMPLE_SKILL_MD = """\
# ---
# name: hello-math
# description: Simple arithmetic helpers for sandbox code. Use when computing sums or products.
# ---

# # Hello Math

# ```python
# def add(a, b):
#     return a + b
# ```
# """
def discover_skills(skills_path: str) -> List[SkillInfo]:

    root = Path(skills_path)
    if not root.exists():
        return []

    skillInfos: List[SkillInfo] = []
    for item in sorted(root.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        skill_md = item / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if m is None:
            continue

        frontmatter = {}
        for line in m.group(1).split('\n'):
            key, value = line.split(":", 1)
            print('key：', key)
            print('value：', value)
            frontmatter[key.strip()] = value.strip().strip("'\"")
            print('frontmatter', frontmatter)
        skillInfos.append(SkillInfo(name=frontmatter['name'], description=frontmatter['description'], path=Path(item)))    
    return skillInfos
    
def generate_skills_prompt(skills: List[SkillInfo], sandbox_path="/home/user/skills") -> str:
    if not skills:
        return ""
    
    lines = [
        "## Available Skills",
        "The following skills are available in the sandbox environment:"
        ""
    ]

    for skill in skills:
        lines.append(f"### {skill.name}")
        lines.append(f"- Description: {skill.description}")
        lines.append(f"- Path: {sandbox_path}/{skill.name}/")
        lines.append(f"Read the SKILL.md for usage instructions: {sandbox_path}/{skill.name}/SKILL.md")
        lines.append("")
        lines.append("You can import and use these skills in your Python code. Read the SKILL.md file first to understand how to use each skill.")

    return "\n".join(lines)
