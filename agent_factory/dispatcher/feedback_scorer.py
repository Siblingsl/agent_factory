from __future__ import annotations

from dataclasses import dataclass

from agent_factory.dispatcher.feedback_store import (
    CombinationStats,
    DispatchOutcome,
    DispatchOutcomeStore,
)


@dataclass(slots=True)
class ScoredTeam:
    slugs: list[str]
    combination_hash: str
    semantic_score: float
    history_factor: float
    cost_factor: float
    final_score: float
    combo_stats: CombinationStats | None


class FeedbackAwareScorer:
    def __init__(self, outcome_store: DispatchOutcomeStore):
        self.store = outcome_store

    async def score_candidate_team(
        self,
        candidate_slugs: list[str],
        current_spec_embedding: list[float],
        semantic_score: float,
    ) -> ScoredTeam:
        combination_hash = DispatchOutcome.compute_combination_hash(candidate_slugs)
        combo_stats = await self.store.get_combination_stats(combination_hash)
        similar_tasks = await self.store.query_similar_tasks(current_spec_embedding, top_k=20)
        similar_success = [
            t
            for t in similar_tasks
            if t.combination_hash == combination_hash and t.overall_success
        ]

        history_factor = self._compute_history_factor(
            combo_stats,
            similar_tasks_count=len(similar_tasks),
            similar_success_count=len(similar_success),
        )
        cost_factor = self._compute_cost_factor(combo_stats)

        if combo_stats and combo_stats.sample_count >= 3:
            final_score = semantic_score * 0.4 + history_factor * 0.4 + cost_factor * 0.2
        else:
            final_score = semantic_score

        return ScoredTeam(
            slugs=candidate_slugs,
            combination_hash=combination_hash,
            semantic_score=semantic_score,
            history_factor=history_factor,
            cost_factor=cost_factor,
            final_score=final_score,
            combo_stats=combo_stats,
        )

    def _compute_history_factor(
        self,
        stats: CombinationStats | None,
        similar_tasks_count: int,
        similar_success_count: int,
    ) -> float:
        if stats is None or stats.sample_count < 3:
            return 0.5
        global_sr = stats.success_rate
        similar_sr = similar_success_count / similar_tasks_count if similar_tasks_count else global_sr
        base = global_sr * 0.6 + similar_sr * 0.4
        gate_penalty = max(0.0, (stats.avg_gate_attempts - 1.0) * 0.1)
        return max(0.0, min(1.0, base - gate_penalty))

    def _compute_cost_factor(self, stats: CombinationStats | None) -> float:
        if stats is None:
            return 0.5
        global_avg_tokens = 120_000.0
        efficiency = global_avg_tokens / max(stats.avg_tokens, 1.0)
        return max(0.1, min(1.0, efficiency))
