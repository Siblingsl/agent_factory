from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Awaitable, Callable

from agent_factory.engine.tool_selector import AgentContext, ToolExecutionPlan
from agent_factory.engine.tool_usage_tracker import ToolUsageTracker


ToolFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ToolExecutionError(RuntimeError):
    pass


class AllToolsFailed(RuntimeError):
    def __init__(self, message: str, attempted_tools: list[str]):
        super().__init__(message)
        self.attempted_tools = attempted_tools


@dataclass(slots=True)
class ToolResult:
    output: dict[str, Any]
    metadata: dict[str, Any]


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_seconds: float = 30.0):
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.open_until = 0.0

    def is_open(self) -> bool:
        return time.time() < self.open_until

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = time.time() + self.cooldown_seconds


class FallbackAwareToolExecutor:
    def __init__(self, tools: dict[str, ToolFn], tracker: ToolUsageTracker | None = None):
        self.tools = tools
        self.tracker = tracker or ToolUsageTracker()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    async def execute(
        self, plan: ToolExecutionPlan, inputs: dict, context: AgentContext
    ) -> ToolResult:
        chain = [plan.primary_tool] + plan.fallback_chain
        last_error: Exception | None = None

        for idx, tool in enumerate(chain):
            breaker = self._get_circuit_breaker(tool.tool_id)
            if breaker.is_open():
                continue

            try:
                started = time.monotonic()
                output = await self._invoke_tool(tool.tool_id, inputs)
                elapsed_ms = (time.monotonic() - started) * 1000
                breaker.record_success()
                await self.tracker.record_success(tool.tool_id, context.task_type, elapsed_ms)
                metadata = {"tool_id": tool.tool_id, "used_fallback": idx > 0, "fallback_level": idx}
                return ToolResult(output=output, metadata=metadata)
            except Exception as exc:
                breaker.record_failure()
                await self.tracker.record_failure(tool.tool_id, context.task_type, type(exc).__name__)
                last_error = exc

        raise AllToolsFailed(
            f"tool chain failed: {last_error}",
            attempted_tools=[t.tool_id for t in chain],
        )

    async def _invoke_tool(self, tool_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        fn = self.tools.get(tool_id)
        if not fn:
            raise ToolExecutionError(f"tool not registered: {tool_id}")
        result = await fn(inputs)
        if not isinstance(result, dict):
            raise ToolExecutionError(f"tool {tool_id} returned non-dict output")
        return result

    def _get_circuit_breaker(self, tool_id: str) -> CircuitBreaker:
        if tool_id not in self._circuit_breakers:
            self._circuit_breakers[tool_id] = CircuitBreaker()
        return self._circuit_breakers[tool_id]
