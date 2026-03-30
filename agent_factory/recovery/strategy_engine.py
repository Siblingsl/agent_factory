from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_factory.recovery.failure_taxonomy import ClassifiedFailure, FailureType


class RecoveryStrategy(str, Enum):
    RETRY_IMMEDIATE = "retry_immediate"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_WITH_CONTEXT = "retry_with_context"
    DECOMPOSE_AND_RETRY = "decompose_and_retry"
    PARTIAL_ROLLBACK = "partial_rollback"
    SUBSTITUTE_ROLE = "substitute_role"
    SUBSTITUTE_TOOL = "substitute_tool"
    REDUCE_SCOPE = "reduce_scope"
    GRACEFUL_DEGRADE = "graceful_degrade"
    ESCALATE_TO_HUMAN = "escalate_to_human"


@dataclass(slots=True)
class RecoveryResult:
    action: RecoveryStrategy
    can_continue: bool
    next_node: str
    human_message: str | None = None
    options: list[str] = field(default_factory=list)
    substitute_role_slug: str | None = None
    remediation_instruction: str = ""
    degraded_spec: dict[str, Any] | None = None
    degradation_notice: str | None = None


class RecoveryStrategyEngine:
    STRATEGY_MAP = {
        FailureType.LLM_TIMEOUT: [RecoveryStrategy.RETRY_WITH_BACKOFF],
        FailureType.LLM_RATE_LIMIT: [RecoveryStrategy.RETRY_WITH_BACKOFF],
        FailureType.NETWORK_ERROR: [
            RecoveryStrategy.RETRY_IMMEDIATE,
            RecoveryStrategy.RETRY_WITH_BACKOFF,
        ],
        FailureType.SYNTAX_ERROR: [
            RecoveryStrategy.RETRY_WITH_CONTEXT,
            RecoveryStrategy.SUBSTITUTE_ROLE,
        ],
        FailureType.RUNTIME_ERROR: [
            RecoveryStrategy.RETRY_WITH_CONTEXT,
            RecoveryStrategy.DECOMPOSE_AND_RETRY,
        ],
        FailureType.IMPORT_ERROR: [RecoveryStrategy.RETRY_WITH_CONTEXT],
        FailureType.TEST_FAILURE: [
            RecoveryStrategy.SUBSTITUTE_ROLE,
            RecoveryStrategy.PARTIAL_ROLLBACK,
            RecoveryStrategy.GRACEFUL_DEGRADE,
        ],
        FailureType.SECURITY_VULNERABILITY: [
            RecoveryStrategy.SUBSTITUTE_ROLE,
            RecoveryStrategy.ESCALATE_TO_HUMAN,
        ],
        FailureType.CONTRACT_VIOLATION: [
            RecoveryStrategy.RETRY_WITH_CONTEXT,
            RecoveryStrategy.REDUCE_SCOPE,
            RecoveryStrategy.ESCALATE_TO_HUMAN,
        ],
        FailureType.PERFORMANCE_BELOW_THRESHOLD: [
            RecoveryStrategy.SUBSTITUTE_ROLE,
            RecoveryStrategy.REDUCE_SCOPE,
            RecoveryStrategy.GRACEFUL_DEGRADE,
        ],
        FailureType.MCP_CONFIG_INVALID: [RecoveryStrategy.SUBSTITUTE_ROLE],
        FailureType.MCP_CONNECTION_FAILED: [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.SUBSTITUTE_TOOL,
        ],
        FailureType.SANDBOX_OOM: [
            RecoveryStrategy.RETRY_WITH_CONTEXT,
            RecoveryStrategy.REDUCE_SCOPE,
        ],
        FailureType.SANDBOX_TIMEOUT: [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.REDUCE_SCOPE,
        ],
    }

    SUBSTITUTE_ROLE_MAP = {
        FailureType.SYNTAX_ERROR: "code-reviewer",
        FailureType.RUNTIME_ERROR: "backend-architect",
        FailureType.TEST_FAILURE: "qa-engineer",
        FailureType.SECURITY_VULNERABILITY: "security-engineer",
        FailureType.PERFORMANCE_BELOW_THRESHOLD: "performance-benchmarker",
        FailureType.MCP_CONFIG_INVALID: "mcp-builder",
        FailureType.CONTRACT_VIOLATION: "agentic-identity-architect",
    }

    async def execute_recovery(
        self,
        failure: ClassifiedFailure,
        state: dict[str, Any],
        attempt_number: int,
        max_attempts: int = 3,
    ) -> RecoveryResult:
        if attempt_number > max_attempts:
            return RecoveryResult(
                action=RecoveryStrategy.ESCALATE_TO_HUMAN,
                can_continue=False,
                next_node="human_recovery",
                human_message=self._compose_escalation(failure, state),
                options=["retry", "degrade", "abort"],
            )

        strategies = self.STRATEGY_MAP.get(
            failure.failure_type,
            [RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.ESCALATE_TO_HUMAN],
        )
        idx = min(attempt_number - 1, len(strategies) - 1)
        chosen = strategies[idx]
        return await self._apply_strategy(chosen, failure, state)

    async def _apply_strategy(
        self,
        strategy: RecoveryStrategy,
        failure: ClassifiedFailure,
        state: dict[str, Any],
    ) -> RecoveryResult:
        if strategy == RecoveryStrategy.SUBSTITUTE_ROLE:
            return await self._substitute_role(failure, state)
        if strategy == RecoveryStrategy.GRACEFUL_DEGRADE:
            return await self._graceful_degrade(failure, state)
        if strategy == RecoveryStrategy.ESCALATE_TO_HUMAN:
            return RecoveryResult(
                action=strategy,
                can_continue=False,
                next_node="human_recovery",
                human_message=self._compose_escalation(failure, state),
                options=["retry", "degrade", "abort"],
            )
        next_node = state.get("failed_node") or "development"
        return RecoveryResult(
            action=strategy,
            can_continue=True,
            next_node=next_node,
            remediation_instruction=f"apply {strategy.value} for {failure.failure_type.value}",
        )

    async def _substitute_role(
        self, failure: ClassifiedFailure, state: dict[str, Any]
    ) -> RecoveryResult:
        substitute_slug = self.SUBSTITUTE_ROLE_MAP.get(failure.failure_type, "senior-developer")
        return RecoveryResult(
            action=RecoveryStrategy.SUBSTITUTE_ROLE,
            can_continue=True,
            next_node="targeted_remediation",
            substitute_role_slug=substitute_slug,
            remediation_instruction=self._compose_remediation_prompt(
                failure=failure, substitute_slug=substitute_slug
            ),
        )

    async def _graceful_degrade(
        self, failure: ClassifiedFailure, state: dict[str, Any]
    ) -> RecoveryResult:
        degraded_spec = {
            "removed_components": failure.affected_components,
            "reason": failure.failure_type.value,
        }
        return RecoveryResult(
            action=RecoveryStrategy.GRACEFUL_DEGRADE,
            can_continue=True,
            next_node="graceful_packager",
            degraded_spec=degraded_spec,
            degradation_notice=(
                "Some features were removed during graceful degrade due to "
                f"{failure.failure_type.value}: {failure.affected_components}"
            ),
            remediation_instruction="deliver reduced scope with explicit warning",
        )

    def _compose_escalation(self, failure: ClassifiedFailure, state: dict[str, Any]) -> str:
        return (
            f"Recovery exceeded threshold for {failure.failure_type.value} at "
            f"node={state.get('failed_node', 'unknown')}."
        )

    def _compose_remediation_prompt(self, failure: ClassifiedFailure, substitute_slug: str) -> str:
        return (
            f"Assign {substitute_slug} to remediate {failure.failure_type.value}. "
            f"Use failure context: {failure.raw_error[:240]}"
        )
