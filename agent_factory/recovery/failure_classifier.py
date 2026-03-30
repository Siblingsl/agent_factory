from __future__ import annotations

import re

from agent_factory.recovery.failure_taxonomy import (
    ClassifiedFailure,
    FailureDomain,
    FailureType,
    RecoverySeverity,
)


class FailureClassifier:
    RULE_TREE: dict[str, tuple[FailureDomain, FailureType, RecoverySeverity]] = {
        "apitimeouterror|timeout|timed out": (
            FailureDomain.LLM_CALL,
            FailureType.LLM_TIMEOUT,
            RecoverySeverity.TRANSIENT,
        ),
        "ratelimit|429": (
            FailureDomain.LLM_CALL,
            FailureType.LLM_RATE_LIMIT,
            RecoverySeverity.TRANSIENT,
        ),
        "syntaxerror|unexpected token|invalid syntax": (
            FailureDomain.CODE_EXECUTION,
            FailureType.SYNTAX_ERROR,
            RecoverySeverity.RECOVERABLE,
        ),
        "module not found|modulenotfounderror|cannot import": (
            FailureDomain.CODE_EXECUTION,
            FailureType.IMPORT_ERROR,
            RecoverySeverity.RECOVERABLE,
        ),
        "memoryerror|oom|out of memory": (
            FailureDomain.SANDBOX,
            FailureType.SANDBOX_OOM,
            RecoverySeverity.RECOVERABLE,
        ),
        "test failed|assertionerror|quality gate": (
            FailureDomain.QUALITY_GATE,
            FailureType.TEST_FAILURE,
            RecoverySeverity.RECOVERABLE,
        ),
        "security": (
            FailureDomain.QUALITY_GATE,
            FailureType.SECURITY_VULNERABILITY,
            RecoverySeverity.STRUCTURAL,
        ),
        "contract": (
            FailureDomain.CONTRACT,
            FailureType.CONTRACT_VIOLATION,
            RecoverySeverity.STRUCTURAL,
        ),
        "connection refused|network": (
            FailureDomain.EXTERNAL_SERVICE,
            FailureType.MCP_CONNECTION_FAILED,
            RecoverySeverity.TRANSIENT,
        ),
    }

    async def classify(self, error_text: str, context: dict) -> ClassifiedFailure:
        for pattern, (domain, failure_type, severity) in self.RULE_TREE.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return ClassifiedFailure(
                    domain=domain,
                    failure_type=failure_type,
                    severity=severity,
                    raw_error=error_text,
                    context=context,
                    affected_components=self._extract_affected(error_text, context),
                )
        return ClassifiedFailure(
            domain=FailureDomain.QUALITY_GATE,
            failure_type=FailureType.RUNTIME_ERROR,
            severity=RecoverySeverity.RECOVERABLE,
            raw_error=error_text,
            context=context,
            affected_components=self._extract_affected(error_text, context),
        )

    def _extract_affected(self, error_text: str, context: dict) -> list[str]:
        affected: list[str] = []
        failed_node = context.get("failed_node")
        if failed_node:
            affected.append(str(failed_node))
        if "mcp" in error_text.lower():
            affected.append("mcp-builder")
        if not affected:
            affected.append("development")
        return affected
