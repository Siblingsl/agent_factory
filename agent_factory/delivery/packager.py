from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone
from dataclasses import asdict

from agent_factory.config.settings import settings
from agent_factory.core.state import DeliveryPackage, FactoryStateV3, TargetLanguage
from agent_factory.delivery.contract_validator import AgentContractValidator
from agent_factory.delivery.language_aware_packager import (
    LanguageAwarePackager,
    TargetLanguage as PackageLanguage,
)
from agent_factory.delivery.tutorial_generator import generate_tutorial


async def package_delivery(state: FactoryStateV3, degraded: bool) -> DeliveryPackage:
    spec = state.get("agent_spec")
    tech_spec = state.get("tech_spec")
    artifacts = state.get("development_artifacts")
    if not spec or not tech_spec or not artifacts:
        raise ValueError("packaging requires spec, tech_spec and development_artifacts")

    language = TargetLanguage.from_value(state.get("target_language"))
    output_dir = Path(settings.output_root) / spec.name
    output_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in artifacts.files.items():
        path = output_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    entry_src = output_dir / artifacts.entry_file
    normalized_entry = output_dir / (
        "agent.ts" if language == TargetLanguage.NODEJS else "agent.py"
    )
    if entry_src != normalized_entry and entry_src.exists():
        normalized_entry.write_text(entry_src.read_text(encoding="utf-8"), encoding="utf-8")

    packager = LanguageAwarePackager(PackageLanguage(language.value))
    packager.generate_dependency_file(
        deps=tech_spec.dependencies,
        dev_deps=tech_spec.dev_dependencies,
        output_dir=output_dir,
    )
    packager.generate_dockerfile(output_dir, agent_name="agent")

    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    readme_text = packager.generate_quickstart_section(
        agent_name="agent",
        tools_needed=tech_spec.tools_needed,
    )
    (docs_dir / "README.md").write_text(readme_text, encoding="utf-8")
    (docs_dir / "TUTORIAL.md").write_text(generate_tutorial(spec), encoding="utf-8")

    dep_result = await packager.verify_dependencies_in_sandbox(output_dir)
    validator = AgentContractValidator()
    contract_report = await validator.validate(str(output_dir))

    validation_passed = dep_result.success and contract_report.passed
    issues = [asdict(issue) for issue in contract_report.issues]
    validation_report = {
        "dependency_install": {
            "success": dep_result.success,
            "error": dep_result.error,
            "logs": dep_result.install_logs,
        },
        "contract": {
            "passed": contract_report.passed,
            "issues": issues,
        },
        "degraded": degraded,
    }

    (output_dir / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    factory_metadata = {
        "factory_version": "0.1.0",
        "production_timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_mode": state.get("execution_mode").value
        if hasattr(state.get("execution_mode"), "value")
        else str(state.get("execution_mode")),
        "target_language": language.value,
        "discussion_team": state.get("dispatch_plan_phase1").roles
        if state.get("dispatch_plan_phase1")
        else [],
        "discussion_rounds": state.get("dispatch_plan_phase1").discussion_rounds
        if state.get("dispatch_plan_phase1")
        else 0,
        "token_usage": state.get("token_usage", {}),
        "quality_gate_attempts": state.get("retry_count", 0) + 1,
        "tool_plans": state.get("tool_plans", []),
        "degraded": degraded,
    }
    (output_dir / "factory_metadata.json").write_text(
        json.dumps(factory_metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    artifact_paths = sorted(
        str(p.relative_to(output_dir)).replace("\\", "/")
        for p in output_dir.rglob("*")
        if p.is_file()
    )

    return DeliveryPackage(
        output_dir=str(output_dir),
        target_language=language,
        entry_file=normalized_entry.name,
        validation_passed=validation_passed,
        validation_report=validation_report,
        artifacts=artifact_paths,
    )
