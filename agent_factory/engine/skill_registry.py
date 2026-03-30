from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SkillInfo:
    name: str
    path: str
    description: str


class SkillRegistry:
    def __init__(self, root: Path | None = None):
        self.root = root or Path("skills")

    def list_skills(self) -> list[SkillInfo]:
        if not self.root.exists():
            return []
        skills = []
        for md in self.root.rglob("SKILL.md"):
            name = md.parent.name
            description = md.read_text(encoding="utf-8", errors="ignore").splitlines()[0] if md.exists() else ""
            skills.append(SkillInfo(name=name, path=str(md), description=description))
        return skills
