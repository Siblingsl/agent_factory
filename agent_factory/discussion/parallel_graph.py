from __future__ import annotations

from dataclasses import dataclass
import asyncio
import random
import time

from agent_factory.core.state import AgentSpec, ExecutionMode, TechSpec
from agent_factory.discussion.bulletin_board import BulletinBoard, BulletinPost
from agent_factory.discussion.synthesis import synthesize_tech_spec
from agent_factory.discussion.token_budget import budget_for_mode
from agent_factory.registry.loader import AgentRegistry
from agent_factory.registry.models import AgentMeta


@dataclass(slots=True)
class DiscussionResult:
    tech_spec: TechSpec
    disagreements: list[str]
    convergence_round: int
    estimated_tokens: int


@dataclass(slots=True)
class ParallelDiscussionState:
    agent_spec: AgentSpec
    discussion_team: list[AgentMeta]
    bulletin_board: BulletinBoard
    round_number: int
    max_rounds: int
    convergence_score: float
    role_positions: dict[str, str]
    disagreements: list[str]


async def run_parallel_discussion(
    spec: AgentSpec,
    team_slugs: list[str],
    execution_mode: ExecutionMode,
    registry: AgentRegistry,
) -> DiscussionResult:
    team = [registry.get_agent_meta(slug) for slug in team_slugs]
    participants = [t for t in team if t is not None]
    if not participants:
        participants = [a for a in registry.get_agents_for_phase("discussion")[:3]]

    board = BulletinBoard()
    state = ParallelDiscussionState(
        agent_spec=spec,
        discussion_team=participants,
        bulletin_board=board,
        round_number=1,
        max_rounds=execution_mode.discussion_rounds or 1,
        convergence_score=0.0,
        role_positions={},
        disagreements=[],
    )

    budget = budget_for_mode(execution_mode)
    token_estimate = 0
    convergence_round = 0

    for _ in range(state.max_rounds):
        snapshot = board.read_all()
        tasks = [
            _role_respond(agent, snapshot, state.round_number, spec)
            for agent in state.discussion_team
        ]
        new_posts = await asyncio.gather(*tasks)
        for post in new_posts:
            await board.publish(post)
            state.role_positions[post.author_slug] = post.position

        token_estimate += len(state.discussion_team) * 1600
        state.convergence_score = _compute_convergence(new_posts)
        state.disagreements.extend(_extract_round_disagreements(new_posts))
        convergence_round = state.round_number

        if token_estimate >= budget.warning_threshold and budget.max_tokens > 0:
            state.disagreements.append(
                f"token budget warning at round {state.round_number}: {token_estimate}/{budget.max_tokens}"
            )

        if state.convergence_score >= 0.85:
            break
        state.round_number += 1

    tech_spec = synthesize_tech_spec(spec, board.read_all())
    if state.disagreements:
        tech_spec.discussion_disagreements.extend(state.disagreements[:10])

    return DiscussionResult(
        tech_spec=tech_spec,
        disagreements=state.disagreements[:20],
        convergence_round=convergence_round,
        estimated_tokens=token_estimate,
    )


async def _role_respond(
    agent: AgentMeta,
    board_snapshot: list[BulletinPost],
    round_number: int,
    spec: AgentSpec,
) -> BulletinPost:
    await asyncio.sleep(0)
    recent_topics = ", ".join(p.position for p in board_snapshot[-5:]) if board_snapshot else "initial direction"
    angle = _angle_from_capability(agent.capability)
    key_claims = [
        f"{angle} for {spec.name}",
        f"ensure runtime contract compatibility",
        f"align implementation to {spec.target_language.value}",
    ]
    content = (
        f"Round {round_number}: propose {angle}. "
        f"Current references: {recent_topics}. "
        f"Primary objective is stable delivery with quality gate pass."
    )
    return BulletinPost.create(
        round_number=round_number,
        author_slug=agent.slug,
        author_name=agent.name,
        content=content,
        position=angle,
        key_claims=key_claims,
    )


def _compute_convergence(posts: list[BulletinPost]) -> float:
    if not posts:
        return 0.0
    positions = [p.position for p in posts]
    unique = len(set(positions))
    base = 1.0 / unique if unique else 0.0
    stability_bonus = min(0.4, len(posts) * 0.03)
    return min(0.99, base + stability_bonus)


def _extract_round_disagreements(posts: list[BulletinPost]) -> list[str]:
    disagreements: list[str] = []
    if len(set(p.position for p in posts)) > max(1, len(posts) // 2):
        disagreements.append("multiple competing solution positions remained in this round")
    for p in posts:
        if random.random() < 0.08:
            disagreements.append(f"{p.author_slug}: noted implementation tradeoff at {time.time():.0f}")
    return disagreements


def _angle_from_capability(capability: list[str]) -> str:
    if not capability:
        return "general architecture refinement"
    if "testing" in capability:
        return "test-driven acceptance criteria"
    if "integration" in capability:
        return "external tool integration plan"
    if "architecture_design" in capability:
        return "layered service boundary design"
    return "implementation execution plan"
