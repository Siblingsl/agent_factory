from __future__ import annotations

from dataclasses import dataclass

from agent_factory.core.state import AgentSpec
from agent_factory.engine.tool_capability_index import ToolCapabilityIndex
from agent_factory.engine.tool_descriptor import ToolCapabilityDescriptor, ToolCategory
from agent_factory.engine.tool_selector import AgentContext, SelectionStrategy, SubTask, ToolSelector


@dataclass(slots=True)
class PlannedToolChain:
    task_type: str
    primary_tool_id: str
    fallback_tool_ids: list[str]
    composition_tool_ids: list[str]
    rationale: str


def _default_catalog() -> list[ToolCapabilityDescriptor]:
    return [
        ToolCapabilityDescriptor(
            tool_id="web_search_primary",
            name="Web Search",
            category=ToolCategory.WEB_ACCESS,
            description="Search public web sources and return concise findings",
            avg_latency_ms=900,
            cost_per_call=0.003,
            success_rate=0.95,
            fallback_tool_ids=["web_search_backup"],
            composable_with=["file_ops_primary", "mcp_router"],
            source="builtin",
        ),
        ToolCapabilityDescriptor(
            tool_id="web_search_backup",
            name="Web Search Backup",
            category=ToolCategory.WEB_ACCESS,
            description="Backup web fetch capability with broader tolerance",
            avg_latency_ms=1200,
            cost_per_call=0.0025,
            success_rate=0.91,
            composable_with=["file_ops_primary", "mcp_router"],
            source="mcp",
        ),
        ToolCapabilityDescriptor(
            tool_id="code_exec_primary",
            name="Code Execution Sandbox",
            category=ToolCategory.CODE_EXEC,
            description="Run generated code in isolated sandbox with limits",
            avg_latency_ms=650,
            cost_per_call=0.004,
            success_rate=0.97,
            fallback_tool_ids=["code_exec_backup"],
            composable_with=["file_ops_primary"],
            requires_sandbox=True,
            source="builtin",
        ),
        ToolCapabilityDescriptor(
            tool_id="code_exec_backup",
            name="Code Execution Backup",
            category=ToolCategory.CODE_EXEC,
            description="Backup code execution in constrained runtime",
            avg_latency_ms=900,
            cost_per_call=0.0038,
            success_rate=0.9,
            composable_with=["file_ops_primary"],
            requires_sandbox=True,
            source="mcp",
        ),
        ToolCapabilityDescriptor(
            tool_id="file_ops_primary",
            name="File Ops",
            category=ToolCategory.FILE_OPS,
            description="Read and write project files with policy checks",
            avg_latency_ms=120,
            cost_per_call=0.0005,
            success_rate=0.99,
            composable_with=["code_exec_primary", "web_search_primary", "mcp_router"],
            source="builtin",
        ),
        ToolCapabilityDescriptor(
            tool_id="mcp_router",
            name="MCP Router",
            category=ToolCategory.API_CALL,
            description="Route external API or MCP tool requests",
            avg_latency_ms=450,
            cost_per_call=0.002,
            success_rate=0.93,
            fallback_tool_ids=["web_search_backup"],
            composable_with=["web_search_primary", "file_ops_primary"],
            source="mcp",
        ),
    ]


def _normalize_requested_tools(tools: list[str]) -> list[str]:
    normalized: list[str] = []
    for tool in tools:
        key = tool.strip().lower()
        if key in {"", "none"}:
            continue
        if key not in normalized:
            normalized.append(key)
    return normalized


def _tool_task_description(tool_key: str, spec: AgentSpec) -> str:
    base = f"Agent {spec.name} requires {tool_key} capability"
    mapping = {
        "web_search": f"{base} for web retrieval and source grounding",
        "code_exec": f"{base} for safe execution and validation loops",
        "file_ops": f"{base} for artifact generation and file management",
        "mcp": f"{base} for external API and MCP integrations",
    }
    return mapping.get(tool_key, base)


async def build_tool_chains_for_spec(spec: AgentSpec) -> list[PlannedToolChain]:
    requested = _normalize_requested_tools(spec.tools)
    if not requested:
        return []

    index = ToolCapabilityIndex()
    await index.build(_default_catalog())
    selector = ToolSelector(index)

    plans: list[PlannedToolChain] = []
    for tool_key in requested:
        task = SubTask(description=_tool_task_description(tool_key, spec), task_type=tool_key)
        context = AgentContext(task_type=tool_key, metadata={"agent": spec.name})
        execution_plan = await selector.select(
            task=task,
            context=context,
            strategy=SelectionStrategy.BALANCED,
        )
        plans.append(
            PlannedToolChain(
                task_type=tool_key,
                primary_tool_id=execution_plan.primary_tool.tool_id,
                fallback_tool_ids=[t.tool_id for t in execution_plan.fallback_chain],
                composition_tool_ids=[t.tool_id for t in execution_plan.composition],
                rationale=execution_plan.selection_rationale,
            )
        )
    return plans
