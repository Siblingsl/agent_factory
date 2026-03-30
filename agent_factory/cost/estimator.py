from __future__ import annotations

from agent_factory.core.state import AgentSpec, CostEstimate, ExecutionMode


class CostEstimator:
    def estimate(self, spec: AgentSpec, mode: ExecutionMode) -> CostEstimate:
        purpose_weight = max(1, len(spec.purpose))
        tool_weight = max(1, len([t for t in spec.tools if t != "none"]))
        language_weight = 1.15 if spec.target_language.value == "nodejs" else 1.0
        complexity = purpose_weight * 0.9 + tool_weight * 1.2

        base_tokens = {
            ExecutionMode.FAST: 25_000,
            ExecutionMode.STANDARD: 75_000,
            ExecutionMode.THOROUGH: 180_000,
        }[mode]
        estimated_tokens = int(base_tokens * complexity * language_weight)
        estimated_minutes = round(estimated_tokens / 2500.0, 1)
        estimated_usd = round(estimated_tokens / 1_000_000 * 20, 2)
        return CostEstimate(
            estimated_tokens=estimated_tokens,
            estimated_minutes=estimated_minutes,
            estimated_usd=estimated_usd,
            rationale=(
                f"mode={mode.value}, purpose_weight={purpose_weight}, "
                f"tool_weight={tool_weight}, language={spec.target_language.value}"
            ),
        )
