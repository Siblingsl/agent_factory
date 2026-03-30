from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CheckOutcome:
    name: str
    passed: bool
    message: str


def coverage_from_checks(checks: list[CheckOutcome]) -> float:
    if not checks:
        return 0.0
    passed = sum(1 for c in checks if c.passed)
    return round((passed / len(checks)) * 100.0, 2)
