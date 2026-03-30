from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional
import hashlib
import logging
import subprocess

import yaml

from agent_factory.registry.models import AgentMeta, Division

LOGGER = logging.getLogger(__name__)

DIVISION_DIRS = [
    "engineering",
    "design",
    "marketing",
    "paid-media",
    "sales",
    "product",
    "project-management",
    "testing",
    "support",
    "spatial-computing",
    "specialized",
    "game-development",
    "academic",
]

DIR_TO_DIVISION = {
    "engineering": Division.ENGINEERING,
    "design": Division.DESIGN,
    "marketing": Division.MARKETING,
    "paid-media": Division.MARKETING,
    "sales": Division.SALES,
    "product": Division.PRODUCT,
    "project-management": Division.PROJECT_MANAGEMENT,
    "testing": Division.TESTING,
    "support": Division.SUPPORT,
    "spatial-computing": Division.SPATIAL_COMPUTING,
    "specialized": Division.SPECIALIZED,
    "game-development": Division.GAME_DEVELOPMENT,
    "academic": Division.ACADEMIC,
}

MANDATORY_DISCUSSION_ROLES = {
    "senior-developer",
    "ai-engineer",
    "sprint-prioritizer",
    "agentic-identity-architect",
}

MANDATORY_WHEN_TOOLS_NEEDED = {"mcp-builder"}


class AgentRegistry:
    def __init__(self, repo_path: Path, auto_sync: bool = False):
        self.repo_path = Path(repo_path)
        self._agents: dict[str, AgentMeta] = {}
        self._version_hash: str = ""
        self._load_all()
        if auto_sync:
            self.sync_from_remote()

    @property
    def version_hash(self) -> str:
        return self._version_hash

    def _load_all(self) -> None:
        self._agents.clear()
        for division_dir in DIVISION_DIRS:
            division_path = self.repo_path / division_dir
            if not division_path.exists():
                continue
            division = DIR_TO_DIVISION[division_dir]
            for md_file in division_path.rglob("*.md"):
                if md_file.name.startswith("_") or md_file.name.lower() == "readme.md":
                    continue
                meta = self._parse_agent_file(md_file, division)
                if meta:
                    self._agents[meta.slug] = meta

        if not self._agents:
            self._load_builtin_agents()

        self._version_hash = self._compute_version_hash()

    def _load_builtin_agents(self) -> None:
        builtin = [
            AgentMeta(
                slug="senior-developer",
                name="Senior Developer",
                description="Architecture governance, technical quality decisions.",
                color="blue",
                emoji="bot",
                vibe="analytical",
                division=Division.ENGINEERING,
                services=["architecture", "code_review"],
                system_prompt="Focus on architecture, maintainability, and correctness.",
                capability=["architecture_design", "code_generation"],
                factory_phases=["discussion", "development", "testing"],
                is_mandatory_discussion=True,
            ),
            AgentMeta(
                slug="ai-engineer",
                name="AI Engineer",
                description="LLM integration and agent logic implementation.",
                color="cyan",
                emoji="bot",
                vibe="practical",
                division=Division.ENGINEERING,
                services=["llm", "prompting", "evaluation"],
                system_prompt="Focus on model interfaces, prompts, and evaluation loops.",
                capability=["llm_integration", "evaluation"],
                factory_phases=["discussion", "development"],
                is_mandatory_discussion=True,
            ),
            AgentMeta(
                slug="sprint-prioritizer",
                name="Sprint Prioritizer",
                description="Product scope and milestones alignment.",
                color="green",
                emoji="bot",
                vibe="structured",
                division=Division.PRODUCT,
                services=["prioritization", "scope_management"],
                system_prompt="Prioritize deliverable milestones and reduce risk early.",
                capability=["roadmap", "task_prioritization"],
                factory_phases=["discussion"],
                is_mandatory_discussion=True,
            ),
            AgentMeta(
                slug="agentic-identity-architect",
                name="Agentic Identity Architect",
                description="Defines target agent identity, behavior boundaries and contract.",
                color="purple",
                emoji="bot",
                vibe="systemic",
                division=Division.SPECIALIZED,
                services=["identity", "contract_design"],
                system_prompt="Design stable identity and constraints for the generated agent.",
                capability=["identity_config", "contract"],
                factory_phases=["discussion", "development", "delivery"],
                is_mandatory_discussion=True,
            ),
            AgentMeta(
                slug="mcp-builder",
                name="MCP Builder",
                description="Integrates external tools through MCP configuration.",
                color="orange",
                emoji="bot",
                vibe="integration-first",
                division=Division.SPECIALIZED,
                services=["mcp_config", "tool_adapter"],
                system_prompt="Build robust MCP configuration and integration tests.",
                capability=["mcp_integration"],
                factory_phases=["development", "testing"],
                is_mandatory_when_tools=True,
            ),
            AgentMeta(
                slug="qa-engineer",
                name="QA Engineer",
                description="Testing strategy and reliability checks.",
                color="red",
                emoji="bot",
                vibe="defensive",
                division=Division.TESTING,
                services=["test_planning", "quality_gate"],
                system_prompt="Validate behavior using high-signal tests and edge cases.",
                capability=["testing", "quality_gate"],
                factory_phases=["discussion", "testing"],
            ),
            AgentMeta(
                slug="backend-architect",
                name="Backend Architect",
                description="Service decomposition and runtime design.",
                color="blue",
                emoji="bot",
                vibe="reliable",
                division=Division.ENGINEERING,
                services=["backend_design", "performance"],
                system_prompt="Design production-grade backends with clean contracts.",
                capability=["backend", "scalability"],
                factory_phases=["development"],
            ),
        ]
        self._agents = {a.slug: a for a in builtin}
        LOGGER.info("Using builtin registry seed with %s roles.", len(self._agents))

    def _parse_agent_file(self, path: Path, division: Division) -> Optional[AgentMeta]:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore")

        metadata, body = _parse_frontmatter(content)
        slug = path.stem
        capability = self._infer_capability(body, slug, division)
        phases = self._infer_phases(slug, division, capability)

        return AgentMeta(
            slug=slug,
            name=metadata.get("name", slug.replace("-", " ").title()),
            description=metadata.get("description", ""),
            color=metadata.get("color", "gray"),
            emoji=metadata.get("emoji", "bot"),
            vibe=metadata.get("vibe", ""),
            division=division,
            services=_to_list(metadata.get("services")),
            system_prompt=body.strip(),
            capability=capability,
            factory_phases=phases,
            is_mandatory_discussion=slug in MANDATORY_DISCUSSION_ROLES,
            is_mandatory_when_tools=slug in MANDATORY_WHEN_TOOLS_NEEDED,
        )

    def _infer_capability(self, body: str, slug: str, division: Division) -> list[str]:
        text = f"{slug} {division.value} {body}".lower()
        tags: list[str] = []
        if any(k in text for k in ["code", "python", "typescript", "backend", "开发", "编程"]):
            tags.append("code_generation")
        if any(k in text for k in ["test", "qa", "验证", "quality"]):
            tags.append("testing")
        if any(k in text for k in ["mcp", "integration", "api"]):
            tags.append("integration")
        if any(k in text for k in ["architecture", "设计", "arch"]):
            tags.append("architecture_design")
        if not tags:
            tags.append("general_problem_solving")
        return sorted(set(tags))

    def _infer_phases(self, slug: str, division: Division, capability: list[str]) -> list[str]:
        phases = {"discussion", "development"}
        if "testing" in capability or division == Division.TESTING:
            phases.add("testing")
        if division in {Division.PRODUCT, Division.PROJECT_MANAGEMENT, Division.ACADEMIC}:
            phases.discard("development")
        if slug in MANDATORY_DISCUSSION_ROLES:
            phases.add("discussion")
        if slug in MANDATORY_WHEN_TOOLS_NEEDED:
            phases.add("development")
        return sorted(phases)

    def _compute_version_hash(self) -> str:
        if self.repo_path.exists():
            try:
                proc = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.repo_path,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout.strip()
            except Exception:
                pass
        digest = hashlib.sha256()
        for slug in sorted(self._agents.keys()):
            payload = asdict(self._agents[slug])
            payload["division"] = self._agents[slug].division.value
            digest.update(yaml.safe_dump(payload, sort_keys=True).encode("utf-8"))
        return digest.hexdigest()[:16]

    def sync_from_remote(self) -> None:
        if self.repo_path.exists():
            subprocess.run(["git", "pull", "origin", "main"], cwd=self.repo_path, check=False)
        self._load_all()

    def get_agent_meta(self, slug: str) -> Optional[AgentMeta]:
        return self._agents.get(slug)

    def get_all_agents(self) -> dict[str, AgentMeta]:
        return dict(self._agents)

    def list_slugs(self) -> list[str]:
        return sorted(self._agents.keys())

    def get_agents_by_division(self, division: Division) -> list[AgentMeta]:
        return [m for m in self._agents.values() if m.division == division]

    def get_agents_for_phase(self, phase: str) -> list[AgentMeta]:
        return [m for m in self._agents.values() if phase in m.factory_phases]

    def query_by_divisions(self, divisions: list[str] | list[Division]) -> list[AgentMeta]:
        allowed = {Division(d) if isinstance(d, str) else d for d in divisions}
        return [m for m in self._agents.values() if m.division in allowed]


def _to_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    stripped = content.lstrip()
    if not stripped.startswith("---"):
        return {}, content

    lines = stripped.splitlines()
    if len(lines) < 3:
        return {}, content

    boundary_indexes = [i for i, line in enumerate(lines) if line.strip() == "---"]
    if len(boundary_indexes) < 2:
        return {}, content

    first, second = boundary_indexes[0], boundary_indexes[1]
    header = "\n".join(lines[first + 1 : second]).strip()
    body = "\n".join(lines[second + 1 :]).strip()
    metadata = yaml.safe_load(header) if header else {}
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, body
