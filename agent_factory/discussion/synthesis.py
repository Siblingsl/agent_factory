from __future__ import annotations

from collections import Counter

from agent_factory.core.state import AgentSpec, TechSpec
from agent_factory.discussion.bulletin_board import BulletinPost


def synthesize_tech_spec(agent_spec: AgentSpec, posts: list[BulletinPost]) -> TechSpec:
    claims = [claim for post in posts for claim in post.key_claims]
    claim_counter = Counter(claims)
    top_claims = [c for c, _ in claim_counter.most_common(8)] or [
        "modular architecture",
        "runtime contract compliance",
        "automated quality gate",
    ]

    task_breakdown = _claims_to_tasks(top_claims)
    risk_register = _extract_risks(posts)
    tools_needed = [t for t in agent_spec.tools if t != "none"]

    return TechSpec(
        architecture="layered-langgraph-workflow",
        tech_stack=_stack_for_language(agent_spec.target_language.value),
        task_breakdown=task_breakdown,
        risk_register=risk_register,
        dependencies=agent_spec.dependencies,
        dev_dependencies=_dev_dependencies(agent_spec.target_language.value),
        tools_needed=tools_needed,
        discussion_disagreements=_extract_disagreements(posts),
    )


def _claims_to_tasks(claims: list[str]) -> list[str]:
    tasks = []
    for claim in claims:
        normalized = claim.strip()
        if not normalized:
            continue
        tasks.append(f"Implement: {normalized}")
    if not tasks:
        tasks.append("Implement: core workflow graph and node orchestration")
    return tasks


def _extract_risks(posts: list[BulletinPost]) -> list[str]:
    risks = []
    for p in posts:
        text = p.content.lower()
        if "risk" in text or "风险" in text:
            risks.append(f"{p.author_slug}: {p.content[:120]}")
    return risks[:10]


def _extract_disagreements(posts: list[BulletinPost]) -> list[str]:
    disagreed = []
    for p in posts:
        content = p.content.lower()
        if any(k in content for k in ["disagree", "tradeoff", "冲突", "分歧"]):
            disagreed.append(f"{p.author_slug}: {p.content[:100]}")
    return disagreed[:10]


def _stack_for_language(language: str) -> list[str]:
    if language == "nodejs":
        return ["Node.js 20", "TypeScript", "Fastify/FastAPI-compatible contract"]
    return ["Python 3.11+", "FastAPI", "LangGraph-compatible orchestration"]


def _dev_dependencies(language: str) -> list[str]:
    if language == "nodejs":
        return ["typescript@5.6.2", "tsx@4.19.1", "vitest@2.1.2"]
    return ["pytest==8.3.3", "pytest-asyncio==0.24.0"]
