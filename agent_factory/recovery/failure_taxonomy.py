from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureDomain(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_EXECUTION = "tool_execution"
    CODE_EXECUTION = "code_execution"
    INTEGRATION = "integration"
    QUALITY_GATE = "quality_gate"
    SANDBOX = "sandbox"
    EXTERNAL_SERVICE = "external_service"
    CONTRACT = "contract"


class FailureType(str, Enum):
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_CONTEXT_TOO_LONG = "llm_context_too_long"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    IMPORT_ERROR = "import_error"
    TEST_FAILURE = "test_failure"
    SECURITY_VULNERABILITY = "security_vulnerability"
    PERFORMANCE_BELOW_THRESHOLD = "performance_below_threshold"
    CONTRACT_VIOLATION = "contract_violation"
    MCP_CONNECTION_FAILED = "mcp_connection_failed"
    MCP_CONFIG_INVALID = "mcp_config_invalid"
    SANDBOX_OOM = "sandbox_oom"
    SANDBOX_TIMEOUT = "sandbox_timeout"
    NETWORK_ERROR = "network_error"


class RecoverySeverity(str, Enum):
    TRANSIENT = "transient"
    RECOVERABLE = "recoverable"
    STRUCTURAL = "structural"
    FATAL = "fatal"


@dataclass(slots=True)
class ClassifiedFailure:
    domain: FailureDomain
    failure_type: FailureType
    severity: RecoverySeverity
    raw_error: str
    context: dict[str, Any] = field(default_factory=dict)
    affected_components: list[str] = field(default_factory=list)
