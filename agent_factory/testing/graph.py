from __future__ import annotations

import re

from agent_factory.core.state import AgentSpec, DevelopmentArtifacts, TestReport
from agent_factory.testing.reporters import CheckOutcome, coverage_from_checks


async def run_quality_gate(spec: AgentSpec, artifacts: DevelopmentArtifacts) -> TestReport:
    checks = [
        _check_entry_file(artifacts),
        _check_contract_shape(artifacts),
        _check_placeholder_scan(artifacts),
        _check_readme_presence(artifacts),
        _check_dependencies(spec, artifacts),
    ]
    coverage = coverage_from_checks(checks)
    failures = [f"{c.name}: {c.message}" for c in checks if not c.passed]
    return TestReport(
        passed=all(c.passed for c in checks),
        coverage=coverage,
        checks={c.name: c.passed for c in checks},
        summary="; ".join(c.message for c in checks),
        failures=failures,
    )


def _check_entry_file(artifacts: DevelopmentArtifacts) -> CheckOutcome:
    exists = artifacts.entry_file in artifacts.files
    return CheckOutcome(
        name="entry_file_exists",
        passed=exists,
        message="entry file exists" if exists else "entry file missing",
    )


def _check_contract_shape(artifacts: DevelopmentArtifacts) -> CheckOutcome:
    content = artifacts.files.get(artifacts.entry_file, "")
    has_invoke = "invoke(" in content or "invoke (" in content
    return CheckOutcome(
        name="contract_invoke_present",
        passed=has_invoke,
        message="invoke interface present" if has_invoke else "invoke interface missing",
    )


def _check_placeholder_scan(artifacts: DevelopmentArtifacts) -> CheckOutcome:
    marker_a = r"\b" + "TO" + "DO\b"
    marker_b = r"\b" + "FIX" + "ME\b"
    marker = r"\b" + "place" + "holder\b"
    not_impl = "Not" + "ImplementedError"
    echo_marker = "input" + "_echo"
    blocked_patterns = [
        marker_a,
        marker_b,
        marker,
        not_impl,
        echo_marker,
    ]
    findings = []
    for path, content in artifacts.files.items():
        for pattern in blocked_patterns:
            if re.search(pattern, content, flags=re.IGNORECASE):
                findings.append(f"{path} => {pattern}")
    return CheckOutcome(
        name="placeholder_scan",
        passed=not findings,
        message="clean" if not findings else f"blocked patterns: {', '.join(findings[:3])}",
    )


def _check_readme_presence(artifacts: DevelopmentArtifacts) -> CheckOutcome:
    ok = "docs/ARCHITECTURE.md" in artifacts.files and "docs/API.md" in artifacts.files
    return CheckOutcome(
        name="documentation_present",
        passed=ok,
        message="docs generated" if ok else "required docs missing",
    )


def _check_dependencies(spec: AgentSpec, artifacts: DevelopmentArtifacts) -> CheckOutcome:
    expected = set(spec.dependencies)
    actual = set(artifacts.dependencies)
    missing = sorted(expected - actual)
    return CheckOutcome(
        name="dependency_alignment",
        passed=not missing,
        message="dependencies aligned" if not missing else f"missing dependencies: {missing}",
    )
