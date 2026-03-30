from __future__ import annotations

from functools import lru_cache
from dataclasses import asdict
from pathlib import Path
import logging
import re
import time

from agent_factory.config.settings import settings
from agent_factory.core.state import (
    AgentSpec,
    ExecutionMode,
    FactoryStateV3,
    TargetLanguage,
    TechSpec,
)
from agent_factory.cost.estimator import CostEstimator
from agent_factory.delivery.packager import package_delivery
from agent_factory.development.graph import run_development_graph
from agent_factory.discussion.parallel_graph import run_parallel_discussion
from agent_factory.dispatcher.feedback_store import DispatchOutcome
from agent_factory.dispatcher.master_dispatcher import MasterDispatcher
from agent_factory.engine.tool_planning import build_tool_chains_for_spec
from agent_factory.recovery.failure_classifier import FailureClassifier
from agent_factory.recovery.strategy_engine import RecoveryStrategy, RecoveryStrategyEngine
from agent_factory.recovery.recovery_journal import RecoveryJournal
from agent_factory.registry.loader import AgentRegistry
from agent_factory.router.domain_router import DomainRouter
from agent_factory.testing.graph import run_quality_gate

LOGGER = logging.getLogger(__name__)


def _slugify_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", value.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        return "generated_agent"
    if re.match(r"^[a-z0-9_]+$", cleaned):
        return cleaned
    return "generated_agent"


def _extract_name(user_input: str) -> str:
    m = re.search(r"(?:叫|名为|named)\s*[:：]?\s*([a-zA-Z0-9_\- ]{3,40})", user_input)
    if m:
        return _slugify_name(m.group(1))
    brief = "_".join(user_input.strip().split()[:4])
    return _slugify_name(brief)[:40] or "generated_agent"


def _detect_tools(user_input: str) -> list[str]:
    text = user_input.lower()
    tools: list[str] = []
    if any(k in text for k in ["web", "浏览器", "搜索", "crawl", "scrape"]):
        tools.append("web_search")
    if any(k in text for k in ["code", "代码", "执行", "python", "node"]):
        tools.append("code_exec")
    if any(k in text for k in ["file", "文件", "读写", "storage"]):
        tools.append("file_ops")
    if any(k in text for k in ["mcp", "api", "第三方", "external"]):
        tools.append("mcp")
    return tools or ["none"]


def _default_dependencies(language: TargetLanguage, tools: list[str]) -> list[str]:
    if language == TargetLanguage.NODEJS:
        deps = ["@anthropic-ai/sdk@0.37.0", "dotenv@16.4.7"]
        if "web_search" in tools:
            deps.append("undici@6.20.0")
        return deps
    deps = ["pydantic==2.9.2", "python-dotenv==1.0.1"]
    if "web_search" in tools:
        deps.append("httpx==0.27.2")
    return deps


@lru_cache(maxsize=1)
def _get_registry() -> AgentRegistry:
    return AgentRegistry(Path(settings.registry_path))


@lru_cache(maxsize=1)
def _get_dispatcher() -> MasterDispatcher:
    return MasterDispatcher(registry=_get_registry())


@lru_cache(maxsize=1)
def _get_router() -> DomainRouter:
    return DomainRouter()


@lru_cache(maxsize=1)
def _get_failure_classifier() -> FailureClassifier:
    return FailureClassifier()


@lru_cache(maxsize=1)
def _get_recovery_engine() -> RecoveryStrategyEngine:
    return RecoveryStrategyEngine()


@lru_cache(maxsize=1)
def _get_recovery_journal() -> RecoveryJournal:
    return RecoveryJournal()


async def intake_node(state: FactoryStateV3) -> FactoryStateV3:
    user_input = state["user_input"]
    language = TargetLanguage.from_value(state.get("target_language"))
    spec = AgentSpec(
        name=_extract_name(user_input),
        purpose=[line.strip(" -") for line in user_input.splitlines() if line.strip()][:3]
        or [user_input.strip()],
        tools=_detect_tools(user_input),
        target_user="general",
        dependencies=_default_dependencies(language, _detect_tools(user_input)),
        target_language=language,
    )
    state["target_language"] = language.value
    state["agent_spec"] = spec
    state["status"] = "intake_done"
    return state


async def domain_router_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    if not spec:
        raise ValueError("agent_spec is required before domain routing")
    router = _get_router()
    divisions = router.route(spec)
    state["domain"] = router.detect_domain(spec)
    state["relevant_divisions"] = [d.value for d in sorted(divisions, key=lambda x: x.value)]
    state["status"] = "domain_routed"
    return state


async def cost_estimate_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    if not spec:
        raise ValueError("agent_spec is required before cost estimate")
    mode = state.get("execution_mode", ExecutionMode.STANDARD)
    estimator = CostEstimator()
    estimate = estimator.estimate(spec=spec, mode=mode)
    state["cost_estimate"] = estimate
    state["status"] = "cost_estimated"
    return state


async def dispatch_phase1_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    if not spec:
        raise ValueError("agent_spec is required before phase1 dispatch")
    dispatcher = _get_dispatcher()
    mode = state.get("execution_mode", ExecutionMode.STANDARD)
    plan = await dispatcher.dispatch_phase1(
        spec=spec,
        mode=mode,
        relevant_divisions=state.get("relevant_divisions", []),
    )
    state["dispatch_plan_phase1"] = plan
    state["status"] = "phase1_dispatched"
    return state


async def discussion_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    plan = state.get("dispatch_plan_phase1")
    mode = state.get("execution_mode", ExecutionMode.STANDARD)
    if not spec or not plan:
        raise ValueError("discussion requires agent_spec and dispatch_plan_phase1")
    result = await run_parallel_discussion(
        spec=spec,
        team_slugs=plan.roles,
        execution_mode=mode,
        registry=_get_registry(),
    )
    state["tech_spec"] = result.tech_spec
    state["discussion_disagreements"] = result.disagreements
    state["token_usage"]["discussion"] = result.estimated_tokens
    state["token_usage"]["total"] = sum(state["token_usage"].values())
    state["status"] = "discussion_done"
    return state


async def tool_plan_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    if not spec:
        raise ValueError("tool planning requires agent_spec")
    chains = await build_tool_chains_for_spec(spec)
    state["tool_plans"] = [asdict(chain) for chain in chains]
    if state.get("tech_spec"):
        state["tech_spec"].tools_needed = [chain.task_type for chain in chains]
    state["status"] = "tool_plan_ready"
    return state


async def dispatch_phase2_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    if not spec:
        raise ValueError("agent_spec is required before phase2 dispatch")
    if not state.get("tech_spec"):
        state["tech_spec"] = TechSpec(
            architecture="fast-track-single-pass",
            tech_stack=["python" if spec.target_language.value == "python" else "nodejs"],
            task_breakdown=[
                "Implement core invoke path",
                "Add runtime contract helpers",
                "Generate packaging metadata",
            ],
            risk_register=["Fast mode bypassed deliberation stage"],
            dependencies=spec.dependencies,
            tools_needed=[t for t in spec.tools if t != "none"],
        )
    plans = state.get("tool_plans") or []
    if state.get("tech_spec") and plans:
        state["tech_spec"].tools_needed = [str(p.get("task_type", "")).strip() for p in plans if p.get("task_type")]
        plan_steps = [
            (
                f"Integrate tool chain for {p.get('task_type')}: "
                f"primary={p.get('primary_tool_id')} fallback={','.join(p.get('fallback_tool_ids', [])) or 'none'}"
            )
            for p in plans
        ]
        existing = set(state["tech_spec"].task_breakdown)
        for step in plan_steps:
            if step not in existing:
                state["tech_spec"].task_breakdown.append(step)
    dispatcher = _get_dispatcher()
    plan = await dispatcher.dispatch_phase2(
        spec=spec,
        tech_spec=state.get("tech_spec"),
        relevant_divisions=state.get("relevant_divisions", []),
    )
    state["dispatch_plan_phase2"] = plan
    state["status"] = "phase2_dispatched"
    return state


async def development_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    tech_spec = state.get("tech_spec")
    plan = state.get("dispatch_plan_phase2")
    if not spec or not tech_spec or not plan:
        raise ValueError("development requires spec, tech_spec and phase2 plan")
    artifacts = await run_development_graph(
        spec=spec,
        tech_spec=tech_spec,
        role_slugs=plan.roles,
        tool_plans=state.get("tool_plans", []),
    )
    state["development_artifacts"] = artifacts
    state["token_usage"]["development"] = 22_000 + len(plan.roles) * 1_200 + len(state.get("tool_plans", [])) * 600
    state["token_usage"]["total"] = sum(state["token_usage"].values())
    state["status"] = "development_done"
    return state


async def quality_gate_node(state: FactoryStateV3) -> FactoryStateV3:
    spec = state.get("agent_spec")
    artifacts = state.get("development_artifacts")
    if not spec or not artifacts:
        raise ValueError("quality gate requires agent_spec and development_artifacts")
    report = await run_quality_gate(spec=spec, artifacts=artifacts)
    state["test_report"] = report
    state["token_usage"]["testing"] = 9_000
    state["token_usage"]["total"] = sum(state["token_usage"].values())
    state["status"] = "quality_gate_checked"
    if not report.passed:
        state["last_error"] = "; ".join(report.failures) or "quality gate failed"
        state["failed_node"] = "quality_gate"
    return state


async def failure_classifier_node(state: FactoryStateV3) -> FactoryStateV3:
    classifier = _get_failure_classifier()
    raw_error = state.get("last_error") or "unknown pipeline error"
    failure = await classifier.classify(
        error_text=raw_error,
        context={
            "failed_node": state.get("failed_node"),
            "domain": state.get("domain"),
            "session_id": state.get("session_id"),
        },
    )
    state["failure"] = failure
    state["status"] = "failure_classified"
    return state


async def recovery_strategy_node(state: FactoryStateV3) -> FactoryStateV3:
    failure = state.get("failure")
    if not failure:
        raise ValueError("failure is required before recovery strategy")
    retries = state.get("retry_count", 0) + 1
    strategy_engine = _get_recovery_engine()
    result = await strategy_engine.execute_recovery(
        failure=failure,
        state=state,
        attempt_number=retries,
        max_attempts=settings.max_retries,
    )
    state["retry_count"] = retries
    state["recovery_result"] = result
    state["status"] = "recovery_strategy_selected"

    await _get_recovery_journal().record(
        session_id=state.get("session_id", "unknown"),
        failure=failure,
        strategy=result.action,
        outcome="selected",
        duration_seconds=0.0,
    )
    return state


async def targeted_remediation_node(state: FactoryStateV3) -> FactoryStateV3:
    result = state.get("recovery_result")
    if not result:
        raise ValueError("recovery_result required for remediation")
    plan = state.get("dispatch_plan_phase2")
    if plan and result.substitute_role_slug:
        if result.substitute_role_slug not in plan.roles:
            plan.roles.append(result.substitute_role_slug)
    if state.get("tech_spec"):
        state["tech_spec"].risk_register.append(result.remediation_instruction)
    state["status"] = "remediation_applied"
    return state


async def human_recovery_node(state: FactoryStateV3) -> FactoryStateV3:
    decision = (state.get("human_decision") or "").strip().lower()
    if decision not in {"retry", "degrade", "abort"}:
        state["human_decision"] = "degrade"
    state["status"] = "await_human_recovery_decision"
    return state


async def graceful_packager_node(state: FactoryStateV3) -> FactoryStateV3:
    if not state.get("tech_spec"):
        state["tech_spec"] = TechSpec(
            architecture="degraded-single-module",
            tech_stack=[state.get("target_language", "python")],
            task_breakdown=["deliver reduced capability package"],
            risk_register=["degraded delivery due to repeated validation failures"],
            dependencies=state.get("agent_spec").dependencies if state.get("agent_spec") else [],
            tools_needed=["none"],
        )
    if state["tech_spec"]:
        state["tech_spec"].risk_register.append("graceful_degrade path executed")
    packaged = await package_delivery(state=state, degraded=True)
    state["delivery_package"] = packaged
    state["status"] = "graceful_packaged"
    return state


async def packaging_node(state: FactoryStateV3) -> FactoryStateV3:
    packaged = await package_delivery(state=state, degraded=False)
    state["delivery_package"] = packaged
    state["status"] = "packaged"
    return state


async def delivery_node(state: FactoryStateV3) -> FactoryStateV3:
    package = state.get("delivery_package")
    if not package:
        raise ValueError("delivery_package missing before delivery")
    state["status"] = "delivered" if package.validation_passed else "blocked"

    if package.validation_passed:
        outcome = DispatchOutcome.from_state(state)
        await _get_dispatcher().record_outcome(outcome)
    else:
        state.setdefault("block_reasons", []).append("delivery_validation_failed")
    return state


def route_post_dispatch_phase1(state: FactoryStateV3) -> str:
    mode = state.get("execution_mode", ExecutionMode.STANDARD)
    return "tool_plan" if mode == ExecutionMode.FAST else "discussion"


def route_quality_gate(state: FactoryStateV3) -> str:
    report = state.get("test_report")
    return "packaging" if report and report.passed else "failure_classifier"


def route_recovery_strategy(state: FactoryStateV3) -> str:
    result = state.get("recovery_result")
    if not result:
        return "human_recovery"
    if result.action in {
        RecoveryStrategy.RETRY_IMMEDIATE,
        RecoveryStrategy.RETRY_WITH_BACKOFF,
        RecoveryStrategy.RETRY_WITH_CONTEXT,
        RecoveryStrategy.DECOMPOSE_AND_RETRY,
        RecoveryStrategy.PARTIAL_ROLLBACK,
        RecoveryStrategy.SUBSTITUTE_TOOL,
    }:
        failed = state.get("failed_node") or "development"
        if failed not in {"discussion", "development", "quality_gate", "packaging"}:
            failed = "development"
        return failed
    mapping = {
        RecoveryStrategy.SUBSTITUTE_ROLE: "targeted_remediation",
        RecoveryStrategy.REDUCE_SCOPE: "targeted_remediation",
        RecoveryStrategy.GRACEFUL_DEGRADE: "graceful_packager",
        RecoveryStrategy.ESCALATE_TO_HUMAN: "human_recovery",
    }
    return mapping.get(result.action, "human_recovery")


def route_human_recovery(state: FactoryStateV3) -> str:
    decision = (state.get("human_decision") or "").strip().lower()
    if decision == "retry":
        failed = state.get("failed_node") or "development"
        return failed if failed in {"discussion", "development", "quality_gate", "packaging"} else "development"
    if decision == "degrade":
        return "graceful_packager"
    return "__end__"
