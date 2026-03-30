from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class GateCheckResult:
    name: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GateSummary:
    status: str
    validation_passed: bool
    block_reasons: list[str]
    next_action: str
    checks: list[GateCheckResult]
    release_signals: dict[str, bool]


def scan_for_placeholders(repo_path: Path) -> GateCheckResult:
    blocked_patterns = [
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\bplaceholder\b",
        r"return\s+['\"]input_echo['\"]",
        r"NotImplementedError",
    ]
    findings: list[str] = []
    root = repo_path / "agent_factory"
    if not root.exists():
        return GateCheckResult(
            name="placeholder_scan",
            passed=False,
            message="agent_factory package not found",
        )
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix not in {".py", ".ts", ".js"}:
            continue
        if "ci" in file_path.parts:
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for pattern in blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append(f"{file_path.relative_to(repo_path)} -> {pattern}")
    return GateCheckResult(
        name="placeholder_scan",
        passed=not findings,
        message="clean" if not findings else "; ".join(findings[:10]),
        details={"findings": findings},
    )


def check_required_bootstrap_files(repo_path: Path) -> GateCheckResult:
    required = [
        "agent_factory_mvp/ci/run_gates.py",
        ".github/workflows/ci-gate.yml",
        ".github/pull_request_template.md",
        "agent_factory/ci/run_gates.py",
        "docs/FEATURE_PROGRESS.md",
        "governance/doc_code_map.yaml",
        "governance/bootstrap_context.yaml",
    ]
    missing = [f for f in required if not (repo_path / f).exists()]
    return GateCheckResult(
        name="required_files_check",
        passed=not missing,
        message="all bootstrap files present" if not missing else f"missing: {missing}",
        details={"missing": missing},
    )


def check_doc_impact_template(repo_path: Path) -> GateCheckResult:
    template = repo_path / ".github" / "pull_request_template.md"
    if not template.exists():
        return GateCheckResult("doc_impact_check", False, "PR template missing")
    content = template.read_text(encoding="utf-8", errors="ignore")
    required_fragments = ["Doc Impact", "`none`", "`updated`", "`blocked`"]
    missing = [f for f in required_fragments if f not in content]
    return GateCheckResult(
        name="doc_impact_check",
        passed=not missing,
        message="Doc Impact section valid" if not missing else f"missing fragments: {missing}",
        details={"missing_fragments": missing},
    )


def _load_feature_progress(repo_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = repo_path / "docs" / "FEATURE_PROGRESS.md"
    if not path.exists():
        return [], ["docs/FEATURE_PROGRESS.md not found"]
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    features: list[dict[str, Any]] = []
    errors: list[str] = []
    current: dict[str, Any] | None = None
    title_pattern = re.compile(r"^###\s+(.+)\s+\[完成度:\s*(\d{1,3})%\]\s*$")
    id_pattern = re.compile(r"^\s*-\s*feature_id:\s*(\S+)\s*$")
    for idx, line in enumerate(lines, start=1):
        m_title = title_pattern.match(line)
        if m_title:
            progress = int(m_title.group(2))
            if progress < 0 or progress > 100:
                errors.append(f"line {idx}: invalid progress {progress}")
            current = {"title": m_title.group(1), "progress": progress, "feature_id": None, "line": idx}
            features.append(current)
            continue
        m_id = id_pattern.match(line)
        if m_id and current is not None:
            current["feature_id"] = m_id.group(1)
    for f in features:
        if not f["feature_id"]:
            errors.append(f"line {f['line']}: missing feature_id under heading '{f['title']}'")
    return features, errors


def check_progress_markers(repo_path: Path) -> GateCheckResult:
    features, errors = _load_feature_progress(repo_path)
    if not features:
        errors.append("no feature headings found")
    return GateCheckResult(
        name="progress_marker_check",
        passed=not errors,
        message="feature progress markers valid" if not errors else "; ".join(errors[:8]),
        details={"feature_count": len(features), "errors": errors},
    )


def check_selftest_records(repo_path: Path) -> GateCheckResult:
    features, feature_errors = _load_feature_progress(repo_path)
    records_path = repo_path / "selftests"
    if not records_path.exists():
        return GateCheckResult(
            name="selftest_records_check",
            passed=False,
            message="selftests directory missing",
            details={"errors": ["selftests directory missing"]},
        )

    files = sorted(records_path.rglob("*.selftest.yaml"))
    if not files:
        return GateCheckResult(
            name="selftest_records_check",
            passed=False,
            message="no selftest files found",
            details={"errors": ["no selftest files found"]},
        )

    errors = list(feature_errors)
    by_feature: dict[str, dict[str, Any]] = {}
    for fp in files:
        payload = yaml.safe_load(fp.read_text(encoding="utf-8", errors="ignore"))
        if not isinstance(payload, dict):
            errors.append(f"{fp.name}: invalid yaml object")
            continue
        for key in ["feature_id", "feature_title", "progress", "self_test"]:
            if key not in payload:
                errors.append(f"{fp.name}: missing key {key}")
        self_test = payload.get("self_test", {})
        for key in ["command", "executed_at", "result", "report_path"]:
            if key not in self_test:
                errors.append(f"{fp.name}: self_test missing {key}")
        if self_test.get("result") not in {"pass", "fail"}:
            errors.append(f"{fp.name}: invalid self_test.result")
        progress = payload.get("progress")
        if not isinstance(progress, int) or progress < 1 or progress > 100:
            errors.append(f"{fp.name}: progress must be int 1-100")
        by_feature[str(payload.get("feature_id"))] = payload

    for feature in features:
        fid = str(feature["feature_id"])
        if fid not in by_feature:
            errors.append(f"feature {fid} missing selftest record")
            continue
        rec = by_feature[fid]
        rec_progress = int(rec.get("progress", 0))
        if rec_progress != int(feature["progress"]):
            errors.append(
                f"feature {fid} progress mismatch: feature={feature['progress']} selftest={rec_progress}"
            )
        if rec_progress == 100 and rec.get("self_test", {}).get("result") != "pass":
            errors.append(f"feature {fid} has progress 100 but selftest is not pass")

    return GateCheckResult(
        name="selftest_records_check",
        passed=not errors,
        message="selftest records valid" if not errors else "; ".join(errors[:10]),
        details={"errors": errors, "record_count": len(files)},
    )


def check_doc_code_consistency(repo_path: Path) -> GateCheckResult:
    map_path = repo_path / "governance" / "doc_code_map.yaml"
    if not map_path.exists():
        return GateCheckResult(
            name="declaration_implementation_consistency",
            passed=False,
            message="governance/doc_code_map.yaml missing",
        )
    payload = yaml.safe_load(map_path.read_text(encoding="utf-8", errors="ignore")) or {}
    mappings = payload.get("mappings", [])
    errors: list[str] = []
    for idx, mapping in enumerate(mappings, start=1):
        doc_path = mapping.get("doc")
        requires = mapping.get("requires", [])
        if not doc_path or not isinstance(requires, list):
            errors.append(f"mapping#{idx}: invalid schema")
            continue
        if not (repo_path / doc_path).exists():
            errors.append(f"mapping#{idx}: doc missing -> {doc_path}")
        missing = [p for p in requires if not (repo_path / p).exists()]
        if missing:
            errors.append(f"mapping#{idx}: missing implementation paths -> {missing}")
    return GateCheckResult(
        name="declaration_implementation_consistency",
        passed=not errors,
        message="doc-code mappings valid" if not errors else "; ".join(errors[:8]),
        details={"errors": errors, "mapping_count": len(mappings)},
    )


def check_drift_exception_ttl(repo_path: Path) -> GateCheckResult:
    path = repo_path / "governance" / "drift_exceptions.yaml"
    if not path.exists():
        return GateCheckResult(
            name="drift_exception_ttl_check",
            passed=True,
            message="no drift exceptions",
            details={"exceptions": 0},
        )
    payload = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
    exceptions = payload.get("exceptions", [])
    errors: list[str] = []
    now = datetime.now(timezone.utc)
    for item in exceptions:
        due = item.get("due_at")
        ex_id = item.get("drift_exception_id", "unknown")
        if not due:
            errors.append(f"{ex_id}: missing due_at")
            continue
        due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
        if due_dt + timedelta(days=2) < now:
            errors.append(f"{ex_id}: exception expired at {due_dt.isoformat()}")
    return GateCheckResult(
        name="drift_exception_ttl_check",
        passed=not errors,
        message="drift exceptions within ttl" if not errors else "; ".join(errors[:6]),
        details={"errors": errors, "exceptions": len(exceptions)},
    )


def check_branch_protection_policy(repo_path: Path) -> GateCheckResult:
    context_path = repo_path / "governance" / "bootstrap_context.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8", errors="ignore")) if context_path.exists() else {}
    repo_mode = (context or {}).get("repo_mode", "local")
    if repo_mode == "local":
        return GateCheckResult(
            name="branch_protection_check",
            passed=True,
            message="local mode: branch protection is marked N/A",
            details={"repo_mode": "local"},
        )

    evidence_path = repo_path / "governance" / "branch_protection_evidence.yaml"
    if not evidence_path.exists():
        return GateCheckResult(
            name="branch_protection_check",
            passed=False,
            message="branch protection evidence missing",
        )
    payload = yaml.safe_load(evidence_path.read_text(encoding="utf-8", errors="ignore")) or {}
    required_flags = [
        "main_branch_no_direct_push",
        "required_ci_gate_enabled",
        "required_reviewer_enabled",
        "admin_bypass_disabled",
    ]
    missing = [f for f in required_flags if payload.get(f) is not True]
    return GateCheckResult(
        name="branch_protection_check",
        passed=not missing,
        message="branch protection evidence valid" if not missing else f"missing true flags: {missing}",
        details={"missing_flags": missing},
    )


async def run_release_validation(repo_path: Path) -> GateCheckResult:
    try:
        from agent_factory.core.factory_graph import build_factory_graph_v3
        from agent_factory.core.state import ExecutionMode, TargetLanguage, create_initial_state
    except Exception as exc:
        return GateCheckResult(
            name="release_validation_bundle_check",
            passed=False,
            message=f"cannot import core workflow: {exc}",
        )

    workflow = build_factory_graph_v3(enable_interrupts=False)
    matrix = [
        (
            TargetLanguage.PYTHON,
            "named gate_python_weather_agent build a weather assistant with web search",
        ),
        (
            TargetLanguage.NODEJS,
            "named gate_node_weather_agent build a weather assistant with web search",
        ),
    ]
    sample_results: list[dict[str, Any]] = []
    errors: list[str] = []
    release_signals = {
        "dependency_install": True,
        "smoke_test": True,
        "contract_tests": True,
        "domain_tests": True,
        "sandbox_verification": True,
        "evidence_bundle_complete": True,
    }

    for language, prompt in matrix:
        state = create_initial_state(
            user_input=prompt,
            execution_mode=ExecutionMode.FAST,
            target_language=language,
        )
        try:
            final_state = await _invoke_workflow(workflow, state)
        except Exception as exc:
            errors.append(f"{language.value}: workflow execution failed: {exc}")
            for key in release_signals:
                release_signals[key] = False
            continue

        package = final_state.get("delivery_package")
        if package is None:
            errors.append(f"{language.value}: delivery_package missing")
            for key in release_signals:
                release_signals[key] = False
            continue

        output_dir = Path(package.output_dir)
        validation_report = package.validation_report
        dep_ok = bool(validation_report.get("dependency_install", {}).get("success"))
        contract_ok = bool(validation_report.get("contract", {}).get("passed"))
        domain_ok = "web_search" in (final_state.get("agent_spec").tools if final_state.get("agent_spec") else [])
        sandbox_ok = (output_dir / "validation_report.json").exists()
        smoke_ok, smoke_message = run_smoke_test(language.value, output_dir)
        evidence_ok = all(
            (output_dir / p).exists()
            for p in [
                "validation_report.json",
                "factory_metadata.json",
                "docs/README.md",
            ]
        )

        release_signals["dependency_install"] &= dep_ok
        release_signals["contract_tests"] &= contract_ok
        release_signals["domain_tests"] &= domain_ok
        release_signals["sandbox_verification"] &= sandbox_ok
        release_signals["smoke_test"] &= smoke_ok
        release_signals["evidence_bundle_complete"] &= evidence_ok

        sample_results.append(
            {
                "language": language.value,
                "output_dir": str(output_dir),
                "dependency_install": dep_ok,
                "contract_tests": contract_ok,
                "domain_tests": domain_ok,
                "sandbox_verification": sandbox_ok,
                "smoke_test": smoke_ok,
                "smoke_message": smoke_message,
                "evidence_bundle_complete": evidence_ok,
            }
        )

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_signals": release_signals,
        "samples": sample_results,
        "errors": errors,
    }
    evidence_path = repo_path / "output" / "ci_evidence"
    evidence_path.mkdir(parents=True, exist_ok=True)
    bundle_path = evidence_path / "release_validation_bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    all_ok = all(release_signals.values()) and not errors
    return GateCheckResult(
        name="release_validation_bundle_check",
        passed=all_ok,
        message="release validation signals all passed" if all_ok else f"signals failed, see {bundle_path}",
        details={"bundle_path": str(bundle_path), "release_signals": release_signals, "errors": errors},
    )


async def _invoke_workflow(workflow: Any, state: dict[str, Any]) -> dict[str, Any]:
    try:
        return await workflow.ainvoke(
            state,
            config={"configurable": {"thread_id": f"ci-gate-{state.get('session_id', 'unknown')}"}},
        )
    except TypeError:
        return await workflow.ainvoke(state)


def run_smoke_test(language: str, output_dir: Path) -> tuple[bool, str]:
    try:
        if language == "python":
            cmd = [sys.executable, str(output_dir / "agent.py")]
        else:
            cmd = ["node", str(output_dir / "agent.js")]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
        ok = proc.returncode == 0
        text = (proc.stdout + "\n" + proc.stderr).strip()
        return ok, text[:400]
    except Exception as exc:
        return False, str(exc)


def run_checks(repo_path: Path) -> tuple[list[GateCheckResult], dict[str, bool]]:
    checks: list[GateCheckResult] = [
        scan_for_placeholders(repo_path),
        check_required_bootstrap_files(repo_path),
        check_doc_impact_template(repo_path),
        check_progress_markers(repo_path),
        check_selftest_records(repo_path),
        check_doc_code_consistency(repo_path),
        check_drift_exception_ttl(repo_path),
        check_branch_protection_policy(repo_path),
    ]
    release_bundle_check = asyncio.run(run_release_validation(repo_path))
    checks.append(release_bundle_check)

    release_signals = {
        "placeholder_scan": _find(checks, "placeholder_scan").passed,
        "declaration_implementation_consistency": _find(
            checks, "declaration_implementation_consistency"
        ).passed,
        "dependency_install": bool(
            release_bundle_check.details.get("release_signals", {}).get("dependency_install", False)
        ),
        "smoke_test": bool(
            release_bundle_check.details.get("release_signals", {}).get("smoke_test", False)
        ),
        "contract_tests": bool(
            release_bundle_check.details.get("release_signals", {}).get("contract_tests", False)
        ),
        "domain_tests": bool(
            release_bundle_check.details.get("release_signals", {}).get("domain_tests", False)
        ),
        "sandbox_verification": bool(
            release_bundle_check.details.get("release_signals", {}).get("sandbox_verification", False)
        ),
        "evidence_bundle_complete": bool(
            release_bundle_check.details.get("release_signals", {}).get("evidence_bundle_complete", False)
        ),
    }
    return checks, release_signals


def _find(checks: list[GateCheckResult], name: str) -> GateCheckResult:
    for c in checks:
        if c.name == name:
            return c
    return GateCheckResult(name=name, passed=False, message="missing check")


def summarize(checks: list[GateCheckResult], release_signals: dict[str, bool]) -> GateSummary:
    failed_checks = [c for c in checks if not c.passed]
    failed_signals = [k for k, v in release_signals.items() if not v]
    block_reasons = [c.name for c in failed_checks] + failed_signals
    block_reasons = sorted(set(block_reasons))
    blocked = bool(block_reasons)
    return GateSummary(
        status="blocked" if blocked else "passed",
        validation_passed=not blocked,
        block_reasons=block_reasons,
        next_action="fix_blockers_only" if blocked else "allow_next_stage_or_delivery",
        checks=checks,
        release_signals=release_signals,
    )


def print_report(summary: GateSummary) -> None:
    print("--- CI Gate Results ---")
    for item in summary.checks:
        status = "PASS" if item.passed else "FAIL"
        print(f"{status:4} | {item.name} | {item.message}")

    print("\n--- Release Signals ---")
    for key, passed in summary.release_signals.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status:4} | {key}")

    payload = {
        "status": summary.status,
        "validation_passed": summary.validation_passed,
        "block_reasons": summary.block_reasons,
        "next_action": summary.next_action,
    }
    print("\n--- Gate Summary ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Agent Factory CI gates.")
    parser.add_argument("--repo_path", type=str, default=".", help="Path to repository root")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero if any gate fails")
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    checks, release_signals = run_checks(repo_path)
    summary = summarize(checks, release_signals)
    print_report(summary)

    if args.strict and not summary.validation_passed:
        return 1
    return 0 if summary.validation_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
