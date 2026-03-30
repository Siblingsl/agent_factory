from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class ToolUsageRow:
    tool_id: str
    task_type: str
    success: bool
    latency_ms: float
    failure_type: str | None
    timestamp: datetime


@dataclass(slots=True)
class ToolStats:
    sample_count: int
    success_rate: float
    avg_latency_ms: float


class ToolUsageTracker:
    def __init__(self):
        self._rows: list[ToolUsageRow] = []

    async def record_success(self, tool_id: str, task_type: str, latency_ms: float) -> None:
        self._rows.append(
            ToolUsageRow(
                tool_id=tool_id,
                task_type=task_type,
                success=True,
                latency_ms=latency_ms,
                failure_type=None,
                timestamp=datetime.utcnow(),
            )
        )

    async def record_failure(self, tool_id: str, task_type: str, failure_type: str) -> None:
        self._rows.append(
            ToolUsageRow(
                tool_id=tool_id,
                task_type=task_type,
                success=False,
                latency_ms=0.0,
                failure_type=failure_type,
                timestamp=datetime.utcnow(),
            )
        )

    async def get_tool_stats(self, tool_id: str, task_type: str) -> ToolStats | None:
        cutoff = datetime.utcnow() - timedelta(days=30)
        rows = [
            r
            for r in self._rows
            if r.tool_id == tool_id and r.task_type == task_type and r.timestamp >= cutoff
        ]
        if not rows:
            return None
        sample = len(rows)
        success_rows = [r for r in rows if r.success]
        success_rate = len(success_rows) / sample
        avg_latency = (
            sum(r.latency_ms for r in success_rows) / len(success_rows) if success_rows else 0.0
        )
        return ToolStats(sample_count=sample, success_rate=success_rate, avg_latency_ms=avg_latency)
