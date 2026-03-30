from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
import logging

from agent_factory.core.state import FactoryStateV3
from agent_factory.core.nodes import (
    cost_estimate_node,
    delivery_node,
    development_node,
    dispatch_phase1_node,
    dispatch_phase2_node,
    discussion_node,
    failure_classifier_node,
    graceful_packager_node,
    human_recovery_node,
    intake_node,
    packaging_node,
    quality_gate_node,
    recovery_strategy_node,
    targeted_remediation_node,
    domain_router_node,
    route_human_recovery,
    route_post_dispatch_phase1,
    route_quality_gate,
    route_recovery_strategy,
)

LOGGER = logging.getLogger(__name__)


try:
    from langgraph.graph import END, StateGraph  # type: ignore
    from langgraph.checkpoint.memory import MemorySaver  # type: ignore

    LANGGRAPH_AVAILABLE = True
except Exception:
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]
    MemorySaver = None  # type: ignore[assignment]
    LANGGRAPH_AVAILABLE = False


NodeFn = Callable[[FactoryStateV3], Awaitable[FactoryStateV3]]


@dataclass(slots=True)
class LocalFactoryWorkflow:
    """
    Fallback orchestrator used when LangGraph is unavailable.
    Keeps node boundaries identical to the graph version.
    """

    async def ainvoke(self, state: FactoryStateV3) -> FactoryStateV3:
        current = await intake_node(state)
        current = await domain_router_node(current)
        current = await cost_estimate_node(current)
        current = await dispatch_phase1_node(current)

        if route_post_dispatch_phase1(current) == "discussion":
            current = await discussion_node(current)

        current = await dispatch_phase2_node(current)
        current = await development_node(current)
        current = await quality_gate_node(current)

        while route_quality_gate(current) == "failure_classifier":
            current = await failure_classifier_node(current)
            current = await recovery_strategy_node(current)
            next_step = route_recovery_strategy(current)
            if next_step == "targeted_remediation":
                current = await targeted_remediation_node(current)
                current = await quality_gate_node(current)
                continue
            if next_step == "graceful_packager":
                current = await graceful_packager_node(current)
                break
            if next_step == "human_recovery":
                current = await human_recovery_node(current)
                human_next = route_human_recovery(current)
                if human_next == END:
                    current["status"] = "aborted_by_human"
                    return current
                if human_next == "graceful_packager":
                    current = await graceful_packager_node(current)
                    break
                current = await quality_gate_node(current)
            else:
                current = await quality_gate_node(current)

        if current.get("status") not in {"graceful_packaged", "aborted_by_human"}:
            current = await packaging_node(current)
        current = await delivery_node(current)
        return current


def build_factory_graph_v3(
    checkpointer: Any | None = None, enable_interrupts: bool = True
) -> Any:
    """
    Build the formal main workflow.
    Uses LangGraph when available, otherwise returns a local async workflow.
    """

    if not LANGGRAPH_AVAILABLE:
        LOGGER.warning("LangGraph not installed. Falling back to LocalFactoryWorkflow.")
        return LocalFactoryWorkflow()

    graph = StateGraph(FactoryStateV3)

    graph.add_node("intake", intake_node)
    graph.add_node("domain_router", domain_router_node)
    graph.add_node("cost_estimate", cost_estimate_node)
    graph.add_node("dispatch_phase1", dispatch_phase1_node)
    graph.add_node("discussion", discussion_node)
    graph.add_node("dispatch_phase2", dispatch_phase2_node)
    graph.add_node("development", development_node)
    graph.add_node("quality_gate", quality_gate_node)
    graph.add_node("packaging", packaging_node)
    graph.add_node("delivery", delivery_node)

    graph.add_node("failure_classifier", failure_classifier_node)
    graph.add_node("recovery_strategy", recovery_strategy_node)
    graph.add_node("targeted_remediation", targeted_remediation_node)
    graph.add_node("human_recovery", human_recovery_node)
    graph.add_node("graceful_packager", graceful_packager_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "domain_router")
    graph.add_edge("domain_router", "cost_estimate")
    graph.add_edge("cost_estimate", "dispatch_phase1")

    graph.add_conditional_edges("dispatch_phase1", route_post_dispatch_phase1)
    graph.add_edge("discussion", "dispatch_phase2")
    graph.add_edge("dispatch_phase2", "development")
    graph.add_edge("development", "quality_gate")

    graph.add_conditional_edges("quality_gate", route_quality_gate)
    graph.add_edge("failure_classifier", "recovery_strategy")
    graph.add_conditional_edges("recovery_strategy", route_recovery_strategy)

    graph.add_edge("targeted_remediation", "quality_gate")
    graph.add_edge("graceful_packager", "delivery")

    graph.add_conditional_edges("human_recovery", route_human_recovery)

    graph.add_edge("packaging", "delivery")
    graph.add_edge("delivery", END)

    compile_kwargs: dict[str, Any] = {
        "checkpointer": checkpointer or (MemorySaver() if MemorySaver else None),
    }
    if enable_interrupts:
        compile_kwargs["interrupt_before"] = ["dispatch_phase1", "dispatch_phase2", "delivery"]
    return graph.compile(**compile_kwargs)
