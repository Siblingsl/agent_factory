from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from agent_factory.recovery.failure_taxonomy import ClassifiedFailure
from agent_factory.recovery.strategy_engine import RecoveryStrategy


@dataclass(slots=True)
class RecoveryJournalRow:
    session_id: str
    timestamp: datetime
    failure_domain: str
    failure_type: str
    severity: str
    affected_components: list[str]
    strategy_applied: str
    outcome: str
    duration_s: float


class RecoveryJournal:
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path("output/recovery_journal.jsonl")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: list[RecoveryJournalRow] = []
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        for line in self.storage_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            row["timestamp"] = datetime.fromisoformat(row["timestamp"])
            self._rows.append(RecoveryJournalRow(**row))

    async def record(
        self,
        session_id: str,
        failure: ClassifiedFailure,
        strategy: RecoveryStrategy,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        row = RecoveryJournalRow(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            failure_domain=failure.domain.value,
            failure_type=failure.failure_type.value,
            severity=failure.severity.value,
            affected_components=failure.affected_components,
            strategy_applied=strategy.value,
            outcome=outcome,
            duration_s=duration_seconds,
        )
        self._rows.append(row)
        with self.storage_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        **row.__dict__,
                        "timestamp": row.timestamp.isoformat(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    async def get_failure_patterns(self, lookback_days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        rows = [r for r in self._rows if r.timestamp >= cutoff]
        by_key: dict[tuple[str, str], dict] = {}
        for row in rows:
            for component in row.affected_components:
                key = (row.failure_type, component)
                if key not in by_key:
                    by_key[key] = {
                        "failure_type": row.failure_type,
                        "role_or_tool": component,
                        "total": 0,
                        "success_count": 0,
                    }
                by_key[key]["total"] += 1
                if row.outcome in {"success", "selected"}:
                    by_key[key]["success_count"] += 1
        patterns = []
        for v in by_key.values():
            total = max(v["total"], 1)
            patterns.append(
                {
                    "failure_type": v["failure_type"],
                    "role_or_tool": v["role_or_tool"],
                    "total": v["total"],
                    "recovery_success_rate": v["success_count"] / total,
                }
            )
        patterns.sort(key=lambda x: x["total"], reverse=True)
        return patterns
