from __future__ import annotations

from dataclasses import dataclass
import math

from agent_factory.engine.tool_descriptor import ToolCapabilityDescriptor, ToolCategory


@dataclass(slots=True)
class ScoredTool:
    descriptor: ToolCapabilityDescriptor
    semantic_score: float
    adjusted_score: float


class ToolCapabilityIndex:
    def __init__(self):
        self._descriptors: dict[str, ToolCapabilityDescriptor] = {}

    async def build(self, all_tools: list[ToolCapabilityDescriptor]) -> None:
        for tool in all_tools:
            tool.capability_embedding = _embed(f"{tool.name} {tool.description}")
            self._descriptors[tool.tool_id] = tool

    async def search(
        self,
        task_description: str,
        top_k: int = 5,
        filter_category: ToolCategory | None = None,
        max_cost_per_call: float | None = None,
    ) -> list[ScoredTool]:
        task_embedding = _embed(task_description)
        scored: list[ScoredTool] = []
        for desc in self._descriptors.values():
            if filter_category and desc.category != filter_category:
                continue
            if max_cost_per_call is not None and desc.cost_per_call > max_cost_per_call:
                continue
            semantic = _cosine(task_embedding, desc.capability_embedding)
            adjusted = self._adjust_score(semantic, desc)
            scored.append(
                ScoredTool(
                    descriptor=desc,
                    semantic_score=semantic,
                    adjusted_score=adjusted,
                )
            )
        scored.sort(key=lambda x: x.adjusted_score, reverse=True)
        return scored[:top_k]

    def _adjust_score(self, semantic_score: float, desc: ToolCapabilityDescriptor) -> float:
        reliability_bonus = (desc.success_rate - 0.5) * 0.3
        cost_penalty = min(desc.cost_per_call * 10, 0.2)
        latency_bonus = max(0.0, (2000 - desc.avg_latency_ms) / 10_000)
        return semantic_score + reliability_bonus - cost_penalty + latency_bonus

    @property
    def descriptors(self) -> dict[str, ToolCapabilityDescriptor]:
        return dict(self._descriptors)


def _embed(text: str, dims: int = 32) -> list[float]:
    vec = [0.0] * dims
    for token in text.lower().split():
        vec[hash(token) % dims] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    n1 = math.sqrt(sum(x * x for x in a)) or 1.0
    n2 = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (n1 * n2)
