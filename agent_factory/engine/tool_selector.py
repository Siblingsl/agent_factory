from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from agent_factory.engine.tool_capability_index import ScoredTool, ToolCapabilityIndex
from agent_factory.engine.tool_descriptor import ToolCapabilityDescriptor


class SelectionStrategy(str, Enum):
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    RELIABLE = "reliable"
    BALANCED = "balanced"


@dataclass(slots=True)
class SubTask:
    description: str
    task_type: str = "general"


@dataclass(slots=True)
class AgentContext:
    task_type: str
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class ToolExecutionPlan:
    primary_tool: ToolCapabilityDescriptor
    fallback_chain: list[ToolCapabilityDescriptor]
    composition: list[ToolCapabilityDescriptor]
    selection_rationale: str


class NoSuitableToolError(RuntimeError):
    pass


class ToolSelector:
    def __init__(self, index: ToolCapabilityIndex):
        self.index = index

    async def select(
        self,
        task: SubTask,
        context: AgentContext,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
    ) -> ToolExecutionPlan:
        candidates = await self.index.search(task.description, top_k=5)
        ranked = self._rank_by_strategy(candidates, strategy)
        if not ranked:
            raise NoSuitableToolError(f"no suitable tool for: {task.description}")
        primary = ranked[0].descriptor
        fallback_chain = self._build_fallback_chain(primary, ranked[1:])
        composition = self._detect_composition_need(task, primary, ranked)
        return ToolExecutionPlan(
            primary_tool=primary,
            fallback_chain=fallback_chain,
            composition=composition,
            selection_rationale=self._explain(ranked, strategy),
        )

    def _rank_by_strategy(
        self, candidates: list[ScoredTool], strategy: SelectionStrategy
    ) -> list[ScoredTool]:
        if strategy == SelectionStrategy.CHEAPEST:
            return sorted(candidates, key=lambda x: (x.descriptor.cost_per_call, -x.adjusted_score))
        if strategy == SelectionStrategy.FASTEST:
            return sorted(candidates, key=lambda x: (x.descriptor.avg_latency_ms, -x.adjusted_score))
        if strategy == SelectionStrategy.RELIABLE:
            return sorted(candidates, key=lambda x: (x.descriptor.success_rate, x.adjusted_score), reverse=True)
        return sorted(candidates, key=lambda x: x.adjusted_score, reverse=True)

    def _build_fallback_chain(
        self, primary: ToolCapabilityDescriptor, alternatives: list[ScoredTool]
    ) -> list[ToolCapabilityDescriptor]:
        known = self.index.descriptors
        declared = [known[fid] for fid in primary.fallback_tool_ids if fid in known]
        semantic = [
            item.descriptor
            for item in alternatives
            if item.descriptor.source != primary.source
        ][:2]
        merged = []
        for desc in declared + semantic:
            if desc.tool_id != primary.tool_id and desc.tool_id not in {d.tool_id for d in merged}:
                merged.append(desc)
        return merged

    def _detect_composition_need(
        self,
        task: SubTask,
        primary: ToolCapabilityDescriptor,
        ranked: list[ScoredTool],
    ) -> list[ToolCapabilityDescriptor]:
        text = task.description.lower()
        if any(k in text for k in ["and", "then", "并", "并且", "after"]):
            chain = [primary]
            for item in ranked[1:]:
                if item.descriptor.tool_id in primary.composable_with:
                    chain.append(item.descriptor)
                if len(chain) >= 2:
                    break
            return chain
        return [primary]

    def _explain(self, ranked: list[ScoredTool], strategy: SelectionStrategy) -> str:
        if not ranked:
            return "no candidates"
        top = ranked[0]
        return (
            f"strategy={strategy.value}; selected={top.descriptor.tool_id}; "
            f"semantic={top.semantic_score:.3f}; adjusted={top.adjusted_score:.3f}"
        )
