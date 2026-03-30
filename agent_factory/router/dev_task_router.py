from __future__ import annotations

from enum import Enum

from agent_factory.core.state import TechSpec


class TaskType(str, Enum):
    CORE_LOGIC = "core_logic"
    FRONTEND_UI = "frontend_ui"
    MCP_INTEGRATION = "mcp_integration"
    RAG_PIPELINE = "rag_pipeline"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    GAME_MECHANICS = "game_mechanics"
    XR_INTERFACE = "xr_interface"
    SMART_CONTRACT = "smart_contract"
    MOBILE = "mobile"
    IDENTITY_CONFIG = "identity_config"


class DevTaskRouter:
    TASK_ROLE_MAP = {
        TaskType.CORE_LOGIC: ["backend-architect", "ai-engineer"],
        TaskType.FRONTEND_UI: ["frontend-developer", "ui-designer"],
        TaskType.MCP_INTEGRATION: ["mcp-builder", "backend-architect"],
        TaskType.RAG_PIPELINE: ["ai-data-remediation-engineer", "ai-engineer"],
        TaskType.DEPLOYMENT: ["devops-automator"],
        TaskType.DOCUMENTATION: ["technical-writer"],
        TaskType.GAME_MECHANICS: ["unity-architect", "game-designer"],
        TaskType.XR_INTERFACE: ["xr-interface-architect", "spatial-ux-designer"],
        TaskType.SMART_CONTRACT: ["solidity-smart-contract-engineer"],
        TaskType.MOBILE: ["mobile-app-builder"],
        TaskType.IDENTITY_CONFIG: ["agentic-identity-architect"],
    }

    def route(self, spec: TechSpec) -> dict[str, list[str]]:
        mapping: dict[str, list[str]] = {}
        for task in spec.task_breakdown:
            t = self._infer_task_type(task.lower())
            mapping[task] = self.TASK_ROLE_MAP.get(t, ["senior-developer"])
        if not mapping:
            mapping["core implementation"] = self.TASK_ROLE_MAP[TaskType.CORE_LOGIC]
        return mapping

    def _infer_task_type(self, text: str) -> TaskType:
        if "ui" in text or "frontend" in text:
            return TaskType.FRONTEND_UI
        if "mcp" in text or "integration" in text:
            return TaskType.MCP_INTEGRATION
        if "deploy" in text or "docker" in text:
            return TaskType.DEPLOYMENT
        if "doc" in text or "readme" in text:
            return TaskType.DOCUMENTATION
        if "identity" in text or "manifest" in text:
            return TaskType.IDENTITY_CONFIG
        if "rag" in text or "retrieval" in text:
            return TaskType.RAG_PIPELINE
        return TaskType.CORE_LOGIC
