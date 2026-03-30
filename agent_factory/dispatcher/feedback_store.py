from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib
import json
import math

from agent_factory.core.state import FactoryStateV3


@dataclass(slots=True)
class CombinationStats:
    combination_hash: str
    sample_count: int
    avg_quality: float
    success_rate: float
    avg_tokens: float
    avg_minutes: float
    avg_gate_attempts: float


@dataclass(slots=True)
class DispatchOutcome:
    session_id: str
    timestamp: datetime
    domain: str
    agent_type: str
    spec_embedding: list[float]
    discussion_team: list[str]
    dev_team_assignments: dict[str, list[str]]
    execution_mode: str
    combination_hash: str
    overall_success: bool
    quality_score: float
    test_coverage: float
    quality_gate_attempts: int
    actual_token_usage: int
    actual_duration_minutes: float
    estimated_token_usage: int
    failure_types: list[str]
    failure_roles: list[str]
    discussion_convergence_rounds: int
    user_rating: Optional[int] = None
    user_feedback_text: Optional[str] = None

    @classmethod
    def compute_combination_hash(cls, slugs: list[str]) -> str:
        return hashlib.sha256(json.dumps(sorted(slugs)).encode("utf-8")).hexdigest()[:16]

    @classmethod
    def from_state(cls, state: FactoryStateV3) -> "DispatchOutcome":
        spec = state.get("agent_spec")
        report = state.get("test_report")
        phase1 = state.get("dispatch_plan_phase1")
        phase2 = state.get("dispatch_plan_phase2")
        quality_attempts = max(1, state.get("retry_count", 0) + 1)
        discussion_team = phase1.roles if phase1 else []
        dev_roles = phase2.roles if phase2 else []

        embedding_seed = " ".join((spec.purpose if spec else []) + (spec.tools if spec else []))
        spec_embedding = _simple_embedding(embedding_seed)
        return cls(
            session_id=state.get("session_id", "unknown"),
            timestamp=datetime.now(timezone.utc),
            domain=state.get("domain", "general") or "general",
            agent_type=spec.name if spec else "unknown_agent",
            spec_embedding=spec_embedding,
            discussion_team=discussion_team,
            dev_team_assignments={"main": dev_roles},
            execution_mode=state.get("execution_mode", "standard").value
            if hasattr(state.get("execution_mode"), "value")
            else str(state.get("execution_mode", "standard")),
            combination_hash=cls.compute_combination_hash(discussion_team),
            overall_success=bool(report and report.passed),
            quality_score=report.coverage / 100 if report else 0.0,
            test_coverage=report.coverage if report else 0.0,
            quality_gate_attempts=quality_attempts,
            actual_token_usage=state.get("token_usage", {}).get("total", 0),
            actual_duration_minutes=0.0,
            estimated_token_usage=state.get("cost_estimate").estimated_tokens
            if state.get("cost_estimate")
            else 0,
            failure_types=[state.get("failure").failure_type.value]
            if state.get("failure")
            else [],
            failure_roles=dev_roles,
            discussion_convergence_rounds=phase1.discussion_rounds if phase1 else 0,
        )


class DispatchOutcomeStore:
    """
    Lightweight store for dispatch feedback data.
    Uses memory + jsonl append for local development and formal scaffolding.
    """

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path("output/dispatch_outcomes.jsonl")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: list[DispatchOutcome] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self.storage_path.exists():
            return
        for line in self.storage_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            row["timestamp"] = datetime.fromisoformat(row["timestamp"])
            self._rows.append(DispatchOutcome(**row))

    async def write(self, outcome: DispatchOutcome) -> None:
        self._rows.append(outcome)
        payload = asdict(outcome)
        payload["timestamp"] = outcome.timestamp.isoformat()
        with self.storage_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    async def query_similar_tasks(
        self,
        spec_embedding: list[float],
        top_k: int = 20,
        min_similarity: float = 0.75,
    ) -> list[DispatchOutcome]:
        scored: list[tuple[float, DispatchOutcome]] = []
        for row in self._rows:
            sim = _cosine_similarity(spec_embedding, row.spec_embedding)
            if sim >= min_similarity:
                scored.append((sim, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:top_k]]

    async def get_combination_stats(self, combination_hash: str) -> Optional[CombinationStats]:
        rows = [r for r in self._rows if r.combination_hash == combination_hash]
        if not rows:
            return None
        sample = len(rows)
        return CombinationStats(
            combination_hash=combination_hash,
            sample_count=sample,
            avg_quality=sum(r.quality_score for r in rows) / sample,
            success_rate=sum(1 for r in rows if r.overall_success) / sample,
            avg_tokens=sum(r.actual_token_usage for r in rows) / sample,
            avg_minutes=sum(r.actual_duration_minutes for r in rows) / sample,
            avg_gate_attempts=sum(r.quality_gate_attempts for r in rows) / sample,
        )


def _simple_embedding(text: str, dims: int = 32) -> list[float]:
    tokens = [t for t in re_tokenize(text) if t]
    if not tokens:
        return [0.0] * dims
    vec = [0.0] * dims
    for tok in tokens:
        idx = int(hashlib.sha1(tok.encode("utf-8")).hexdigest(), 16) % dims
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(x * x for x in v1)) or 1.0
    n2 = math.sqrt(sum(x * x for x in v2)) or 1.0
    return dot / (n1 * n2)


def re_tokenize(text: str) -> list[str]:
    chars = []
    token = []
    for ch in text.lower():
        if ch.isalnum() or ch in {"_", "-"}:
            token.append(ch)
            continue
        if token:
            chars.append("".join(token))
            token = []
    if token:
        chars.append("".join(token))
    return chars
