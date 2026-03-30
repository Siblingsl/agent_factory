from __future__ import annotations

from dataclasses import dataclass

from agent_factory.core.state import ExecutionMode


@dataclass(slots=True)
class BudgetCheckResult:
    allowed: bool
    warning: bool
    used: int
    budget: int
    phase: str


class CostController:
    PHASE_BUDGETS = {
        ExecutionMode.FAST: {"discussion": 0, "development": 30_000, "testing": 20_000, "total": 50_000},
        ExecutionMode.STANDARD: {
            "discussion": 20_000,
            "development": 80_000,
            "testing": 20_000,
            "total": 120_000,
        },
        ExecutionMode.THOROUGH: {
            "discussion": 40_000,
            "development": 200_000,
            "testing": 60_000,
            "total": 300_000,
        },
    }

    def check_budget(self, phase: str, used: int, mode: ExecutionMode) -> BudgetCheckResult:
        budgets = self.PHASE_BUDGETS[mode]
        budget = budgets.get(phase, budgets["total"])
        warning = used > budget * 0.9
        return BudgetCheckResult(
            allowed=used <= budget,
            warning=warning,
            used=used,
            budget=budget,
            phase=phase,
        )
