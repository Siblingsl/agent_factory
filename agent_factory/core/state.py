from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TypedDict
import time
import uuid


class ExecutionMode(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    THOROUGH = "thorough"

    @property
    def discussion_team_size(self) -> int:
        return {
            ExecutionMode.FAST: 0,
            ExecutionMode.STANDARD: 4,
            ExecutionMode.THOROUGH: 6,
        }[self]

    @property
    def discussion_rounds(self) -> int:
        return {
            ExecutionMode.FAST: 0,
            ExecutionMode.STANDARD: 3,
            ExecutionMode.THOROUGH: 5,
        }[self]

    @property
    def token_budget(self) -> int:
        return {
            ExecutionMode.FAST: 50_000,
            ExecutionMode.STANDARD: 120_000,
            ExecutionMode.THOROUGH: 300_000,
        }[self]


class TargetLanguage(str, Enum):
    PYTHON = "python"
    NODEJS = "nodejs"

    @classmethod
    def from_value(cls, value: str | None) -> "TargetLanguage":
        if not value:
            return cls.PYTHON
        normalized = value.strip().lower()
        if normalized in {"node", "nodejs", "node.js", "typescript", "ts"}:
            return cls.NODEJS
        return cls.PYTHON


@dataclass(slots=True)
class AgentSpec:
    name: str
    purpose: list[str]
    tools: list[str]
    target_user: str
    dependencies: list[str]
    target_language: TargetLanguage

    def to_prompt_str(self) -> str:
        return (
            f"Agent: {self.name}\n"
            f"Purpose: {', '.join(self.purpose)}\n"
            f"Tools: {', '.join(self.tools)}\n"
            f"Target user: {self.target_user}\n"
            f"Language: {self.target_language.value}\n"
        )


@dataclass(slots=True)
class CostEstimate:
    estimated_tokens: int
    estimated_minutes: float
    estimated_usd: float
    rationale: str


@dataclass(slots=True)
class DispatchPlan:
    phase: str
    roles: list[str]
    discussion_rounds: int = 0
    decision_explanation: str = ""
    cost_estimate: Optional[CostEstimate] = None


@dataclass(slots=True)
class TechSpec:
    architecture: str
    tech_stack: list[str]
    task_breakdown: list[str]
    risk_register: list[str]
    dependencies: list[str]
    dev_dependencies: list[str] = field(default_factory=list)
    tools_needed: list[str] = field(default_factory=list)
    discussion_disagreements: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DevelopmentArtifacts:
    entry_file: str
    files: dict[str, str]
    dependencies: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TestReport:
    passed: bool
    coverage: float
    checks: dict[str, bool]
    summary: str
    failures: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DeliveryPackage:
    output_dir: str
    target_language: TargetLanguage
    entry_file: str
    validation_passed: bool
    validation_report: dict[str, Any]
    artifacts: list[str]


class FactoryStateV3(TypedDict, total=False):
    session_id: str
    user_input: str
    execution_mode: ExecutionMode
    target_language: str
    agent_spec: Optional[AgentSpec]
    domain: Optional[str]
    relevant_divisions: list[str]
    cost_estimate: Optional[CostEstimate]
    dispatch_plan_phase1: Optional[DispatchPlan]
    tech_spec: Optional[TechSpec]
    dispatch_plan_phase2: Optional[DispatchPlan]
    development_artifacts: Optional[DevelopmentArtifacts]
    test_report: Optional[TestReport]
    retry_count: int
    failure: Any
    recovery_result: Any
    failed_node: Optional[str]
    delivery_package: Optional[DeliveryPackage]
    status: str
    token_usage: dict[str, int]
    discussion_disagreements: list[str]
    human_decision: Optional[str]
    last_error: Optional[str]
    block_reasons: list[str]


def create_initial_state(
    user_input: str,
    execution_mode: ExecutionMode = ExecutionMode.STANDARD,
    target_language: TargetLanguage = TargetLanguage.PYTHON,
) -> FactoryStateV3:
    return FactoryStateV3(
        session_id=str(uuid.uuid4()),
        user_input=user_input,
        execution_mode=execution_mode,
        target_language=target_language.value,
        agent_spec=None,
        domain=None,
        relevant_divisions=[],
        cost_estimate=None,
        dispatch_plan_phase1=None,
        tech_spec=None,
        dispatch_plan_phase2=None,
        development_artifacts=None,
        test_report=None,
        retry_count=0,
        failure=None,
        recovery_result=None,
        failed_node=None,
        delivery_package=None,
        status="created",
        token_usage={"discussion": 0, "development": 0, "testing": 0, "total": 0},
        discussion_disagreements=[],
        human_decision=None,
        last_error=None,
        block_reasons=[],
        created_at=time.time(),  # type: ignore[typeddict-item]
    )
