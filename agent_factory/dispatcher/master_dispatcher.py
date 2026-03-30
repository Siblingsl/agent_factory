from __future__ import annotations

import asyncio
from dataclasses import dataclass
from itertools import islice
import logging

from agent_factory.core.state import AgentSpec, DispatchPlan, ExecutionMode, TechSpec
from agent_factory.dispatcher.feedback_scorer import FeedbackAwareScorer, ScoredTeam
from agent_factory.dispatcher.feedback_store import DispatchOutcome, DispatchOutcomeStore
from agent_factory.registry.loader import (
    MANDATORY_DISCUSSION_ROLES,
    MANDATORY_WHEN_TOOLS_NEEDED,
    AgentRegistry,
)
from agent_factory.registry.models import AgentMeta
from agent_factory.router.domain_router import DomainRouter

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CandidateTeam:
    slugs: list[str]
    semantic_score: float


class MasterDispatcher:
    def __init__(
        self,
        registry: AgentRegistry,
        outcome_store: DispatchOutcomeStore | None = None,
    ):
        self.registry = registry
        self.domain_router = DomainRouter()
        self.outcome_store = outcome_store or DispatchOutcomeStore()
        self.scorer = FeedbackAwareScorer(self.outcome_store)

    async def dispatch_phase1(
        self,
        spec: AgentSpec,
        mode: ExecutionMode,
        relevant_divisions: list[str],
    ) -> DispatchPlan:
        pool = self.registry.query_by_divisions(relevant_divisions or [d.value for d in self.domain_router.route(spec)])
        pool = [p for p in pool if "discussion" in p.factory_phases]
        spec_embedding = self._embed_spec(spec)
        candidates = self._build_candidate_teams(spec, pool, mode)

        scored: list[ScoredTeam] = await asyncio.gather(
            *[
                self.scorer.score_candidate_team(
                    candidate_slugs=c.slugs,
                    current_spec_embedding=spec_embedding,
                    semantic_score=c.semantic_score,
                )
                for c in candidates
            ]
        )
        best = sorted(scored, key=lambda t: t.final_score, reverse=True)[0]
        final_team = self._apply_mandatory_roles(best.slugs, spec, mode, phase="discussion")

        explanation = self._explain(scored=scored, selected=best)
        return DispatchPlan(
            phase="discussion",
            roles=final_team,
            discussion_rounds=mode.discussion_rounds,
            decision_explanation=explanation,
        )

    async def dispatch_phase2(
        self,
        spec: AgentSpec,
        tech_spec: TechSpec | None,
        relevant_divisions: list[str],
    ) -> DispatchPlan:
        pool = self.registry.query_by_divisions(relevant_divisions or [d.value for d in self.domain_router.route(spec)])
        pool = [p for p in pool if "development" in p.factory_phases]

        must_have = {"senior-developer", "ai-engineer"}
        if any(t != "none" for t in spec.tools):
            must_have |= MANDATORY_WHEN_TOOLS_NEEDED

        ranked = sorted(pool, key=lambda m: self._dev_match_score(spec, tech_spec, m), reverse=True)
        selected = []
        for slug in must_have:
            if self.registry.get_agent_meta(slug):
                selected.append(slug)
        for meta in ranked:
            if meta.slug not in selected:
                selected.append(meta.slug)
            if len(selected) >= 4:
                break

        return DispatchPlan(
            phase="development",
            roles=selected,
            discussion_rounds=0,
            decision_explanation=f"Selected {len(selected)} dev roles based on spec + tool needs.",
        )

    async def record_outcome(self, outcome: DispatchOutcome) -> None:
        await self.outcome_store.write(outcome)

    def _build_candidate_teams(
        self, spec: AgentSpec, pool: list[AgentMeta], mode: ExecutionMode
    ) -> list[CandidateTeam]:
        desired = mode.discussion_team_size or 3
        if not pool:
            return [CandidateTeam(slugs=list(MANDATORY_DISCUSSION_ROLES), semantic_score=0.5)]

        ranked = sorted(pool, key=lambda m: self._semantic_score(spec, m), reverse=True)
        top = list(islice(ranked, 8))
        candidates: list[CandidateTeam] = []

        for i in range(min(5, len(top))):
            team = [m.slug for m in top[i : i + desired]]
            if len(team) < desired:
                team += [m.slug for m in top[: desired - len(team)]]
            team = list(dict.fromkeys(team))
            avg_score = (
                sum(self._semantic_score(spec, self.registry.get_agent_meta(s) or top[0]) for s in team)
                / len(team)
            )
            candidates.append(CandidateTeam(slugs=team, semantic_score=avg_score))

        if not candidates:
            candidates.append(
                CandidateTeam(
                    slugs=[m.slug for m in top[:desired]],
                    semantic_score=0.6,
                )
            )
        return candidates

    def _apply_mandatory_roles(
        self, slugs: list[str], spec: AgentSpec, mode: ExecutionMode, phase: str
    ) -> list[str]:
        desired = mode.discussion_team_size if phase == "discussion" else 4
        merged = list(dict.fromkeys(slugs))
        if phase == "discussion":
            for slug in MANDATORY_DISCUSSION_ROLES:
                if self.registry.get_agent_meta(slug) and slug not in merged:
                    merged.insert(0, slug)
        if phase == "development" and any(t != "none" for t in spec.tools):
            for slug in MANDATORY_WHEN_TOOLS_NEEDED:
                if self.registry.get_agent_meta(slug) and slug not in merged:
                    merged.insert(0, slug)
        return merged[: max(desired, len(MANDATORY_DISCUSSION_ROLES))]

    def _dev_match_score(self, spec: AgentSpec, tech_spec: TechSpec | None, meta: AgentMeta) -> float:
        base = self._semantic_score(spec, meta)
        if tech_spec and any(k in " ".join(tech_spec.task_breakdown).lower() for k in ["mcp", "contract"]):
            if meta.slug == "mcp-builder":
                base += 0.3
        return min(base, 1.0)

    def _semantic_score(self, spec: AgentSpec, meta: AgentMeta) -> float:
        need = " ".join(spec.purpose + spec.tools).lower()
        ref = f"{meta.slug} {meta.name} {meta.description} {' '.join(meta.capability)}".lower()
        matched = sum(1 for token in need.split() if token and token in ref)
        denom = max(5, len(set(need.split())))
        return min(1.0, matched / denom + 0.2)

    def _embed_spec(self, spec: AgentSpec) -> list[float]:
        text = " ".join(spec.purpose + spec.tools + [spec.target_user])
        dims = 32
        vec = [0.0] * dims
        for token in text.split():
            idx = hash(token) % dims
            vec[idx] += 1.0
        total = sum(abs(x) for x in vec) or 1.0
        return [x / total for x in vec]

    def _explain(self, scored: list[ScoredTeam], selected: ScoredTeam) -> str:
        top_lines = [
            f"{i+1}. {','.join(item.slugs)} => final={item.final_score:.3f}"
            for i, item in enumerate(sorted(scored, key=lambda x: x.final_score, reverse=True)[:3])
        ]
        return (
            f"selected={','.join(selected.slugs)}; "
            f"semantic={selected.semantic_score:.3f}; "
            f"history={selected.history_factor:.3f}; "
            f"cost={selected.cost_factor:.3f}; "
            f"top={'; '.join(top_lines)}"
        )
