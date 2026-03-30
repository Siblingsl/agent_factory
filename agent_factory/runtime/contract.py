from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import os
from typing import Any, AsyncIterator, Optional


class TooManyConcurrentSessionsError(RuntimeError):
    pass


class InputTooLargeError(RuntimeError):
    pass


@dataclass(slots=True)
class AgentCapabilityManifest:
    agent_id: str
    agent_name: str
    version: str
    description: str
    supported_input_types: list[str]
    supported_output_types: list[str]
    primary_use_cases: list[str]
    tools_available: list[str]
    mcp_servers: list[str]
    skills_loaded: list[str]
    max_context_tokens: int
    max_response_tokens: int
    max_concurrent_sessions: int
    timeout_seconds: int
    required_env_vars: list[str]
    required_services: list[str]
    min_memory_mb: int
    factory_metadata: dict[str, Any]


@dataclass(slots=True)
class AgentInvokeRequest:
    session_id: str
    input: Any
    system_override: Optional[str] = None
    stream: bool = False
    timeout_override: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentInvokeResponse:
    session_id: str
    output: Any
    success: bool
    error: Optional[str] = None
    token_usage: Optional[dict[str, Any]] = None
    tool_calls_made: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRuntimeContract(ABC):
    def __init__(self):
        self._active_sessions = 0

    @abstractmethod
    async def invoke(self, request: AgentInvokeRequest) -> AgentInvokeResponse:
        pass

    @abstractmethod
    async def stream(self, request: AgentInvokeRequest) -> AsyncIterator[str]:
        pass

    @abstractmethod
    def get_manifest(self) -> AgentCapabilityManifest:
        pass

    async def _ping_mcp_server(self, server: str) -> bool:
        return True

    async def _ping_llm(self) -> str:
        return "ok"

    async def health_check(self) -> dict[str, Any]:
        checks: dict[str, str] = {}
        for server in self.get_manifest().mcp_servers:
            try:
                ok = await self._ping_mcp_server(server)
                checks[f"mcp.{server}"] = "ok" if ok else "degraded"
            except Exception:
                checks[f"mcp.{server}"] = "failed"
        checks["llm"] = await self._ping_llm()

        status = "healthy"
        if any(v == "failed" for v in checks.values()):
            status = "unhealthy"
        elif any(v == "degraded" for v in checks.values()):
            status = "degraded"
        return {"status": status, "checks": checks}

    async def ready_check(self) -> bool:
        for env_var in self.get_manifest().required_env_vars:
            if not os.environ.get(env_var):
                return False
        return True

    async def graceful_shutdown(self, timeout_seconds: int = 30) -> None:
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while self._active_sessions > 0 and asyncio.get_event_loop().time() <= deadline:
            await asyncio.sleep(0.1)

    async def _enforce_resource_limits(self, request: AgentInvokeRequest) -> None:
        manifest = self.get_manifest()
        if self._active_sessions >= manifest.max_concurrent_sessions:
            raise TooManyConcurrentSessionsError("max concurrent sessions exceeded")
        if len(str(request.input)) > manifest.max_context_tokens * 4:
            raise InputTooLargeError("input exceeds max_context_tokens")
