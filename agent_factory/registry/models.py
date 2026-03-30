from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Division(str, Enum):
    ENGINEERING = "engineering"
    DESIGN = "design"
    MARKETING = "marketing"
    SALES = "sales"
    PRODUCT = "product"
    PROJECT_MANAGEMENT = "project-management"
    TESTING = "testing"
    SUPPORT = "support"
    SPATIAL_COMPUTING = "spatial-computing"
    SPECIALIZED = "specialized"
    GAME_DEVELOPMENT = "game-development"
    ACADEMIC = "academic"


@dataclass(slots=True)
class AgentMeta:
    slug: str
    name: str
    description: str
    color: str
    emoji: str
    vibe: str
    division: Division
    services: list[str]
    system_prompt: str
    capability: list[str] = field(default_factory=list)
    factory_phases: list[str] = field(default_factory=list)
    is_mandatory_discussion: bool = False
    is_mandatory_when_tools: bool = False
