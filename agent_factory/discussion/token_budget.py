from __future__ import annotations

from dataclasses import dataclass

from agent_factory.core.state import ExecutionMode


@dataclass(slots=True)
class DiscussionBudget:
    max_tokens: int
    warning_threshold: int


def budget_for_mode(mode: ExecutionMode) -> DiscussionBudget:
    max_tokens = {
        ExecutionMode.FAST: 0,
        ExecutionMode.STANDARD: 20_000,
        ExecutionMode.THOROUGH: 40_000,
    }[mode]
    return DiscussionBudget(max_tokens=max_tokens, warning_threshold=int(max_tokens * 0.9))
