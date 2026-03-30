from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolCategory(str, Enum):
    WEB_ACCESS = "web_access"
    CODE_EXEC = "code_exec"
    FILE_OPS = "file_ops"
    API_CALL = "api_call"
    ANALYSIS = "analysis"


@dataclass(slots=True)
class ToolCapabilityDescriptor:
    tool_id: str
    name: str
    category: ToolCategory
    description: str
    capability_embedding: list[float] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    cost_per_call: float = 0.0
    rate_limit_per_min: Optional[int] = None
    success_rate: float = 1.0
    failure_modes: list[str] = field(default_factory=list)
    requires_env_vars: list[str] = field(default_factory=list)
    requires_sandbox: bool = False
    source: str = "builtin"
    fallback_tool_ids: list[str] = field(default_factory=list)
    composable_with: list[str] = field(default_factory=list)
