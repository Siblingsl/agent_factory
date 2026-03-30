from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ContractIssue:
    severity: str
    message: str


@dataclass(slots=True)
class ContractValidationReport:
    passed: bool
    issues: list[ContractIssue] = field(default_factory=list)


class AgentContractValidator:
    REQUIRED_METHOD_MARKERS = ["invoke", "manifest", "health_check", "ready_check"]

    async def validate(self, agent_package_dir: str) -> ContractValidationReport:
        base = Path(agent_package_dir)
        issues: list[ContractIssue] = []

        entry = self._detect_entry(base)
        if not entry:
            issues.append(ContractIssue(severity="CRITICAL", message="missing entry file"))
            return ContractValidationReport(passed=False, issues=issues)

        content = entry.read_text(encoding="utf-8", errors="ignore")
        normalized = content.lower()
        for marker in self.REQUIRED_METHOD_MARKERS:
            if marker not in normalized:
                issues.append(
                    ContractIssue(
                        severity="CRITICAL",
                        message=f"entry file missing contract marker: {marker}",
                    )
                )

        metadata = base / "factory_metadata.json"
        if not metadata.exists():
            issues.append(
                ContractIssue(severity="WARNING", message="factory_metadata.json not found")
            )

        docs_readme = base / "docs" / "README.md"
        if not docs_readme.exists():
            issues.append(ContractIssue(severity="WARNING", message="docs/README.md missing"))

        return ContractValidationReport(
            passed=not any(i.severity == "CRITICAL" for i in issues),
            issues=issues,
        )

    def _detect_entry(self, base: Path) -> Path | None:
        for name in ("agent.py", "agent.ts", "agent.js"):
            candidate = base / name
            if candidate.exists():
                return candidate
        return None
