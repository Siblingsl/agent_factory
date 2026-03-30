from __future__ import annotations

from agent_factory.core.state import AgentSpec
from agent_factory.registry.models import Division


class DomainRouter:
    DOMAIN_SIGNALS: dict[str, list[Division]] = {
        "game": [Division.GAME_DEVELOPMENT, Division.SPECIALIZED],
        "xr": [Division.SPATIAL_COMPUTING, Division.ENGINEERING],
        "web3": [Division.ENGINEERING, Division.SPECIALIZED],
        "enterprise": [Division.SUPPORT, Division.SPECIALIZED, Division.ENGINEERING],
        "mobile": [Division.ENGINEERING, Division.DESIGN],
        "data": [Division.ENGINEERING, Division.SPECIALIZED],
        "marketing": [Division.MARKETING, Division.SALES, Division.PRODUCT],
        "general": list(Division),
    }

    CORE_DIVISIONS = {
        Division.ENGINEERING,
        Division.PRODUCT,
        Division.PROJECT_MANAGEMENT,
        Division.TESTING,
    }

    def detect_domain(self, spec: AgentSpec) -> str:
        text = " ".join(spec.purpose + spec.tools).lower()
        if any(k in text for k in ["game", "unity", "unreal", "godot", "游戏"]):
            return "game"
        if any(k in text for k in ["xr", "ar", "vr", "spatial"]):
            return "xr"
        if any(k in text for k in ["web3", "blockchain", "solidity", "区块链"]):
            return "web3"
        if any(k in text for k in ["enterprise", "crm", "erp", "工单", "企业"]):
            return "enterprise"
        if any(k in text for k in ["mobile", "android", "ios"]):
            return "mobile"
        if any(k in text for k in ["data", "analysis", "etl", "数据"]):
            return "data"
        if any(k in text for k in ["marketing", "growth", "campaign", "营销"]):
            return "marketing"
        return "general"

    def route(self, spec: AgentSpec) -> set[Division]:
        detected = self.detect_domain(spec)
        domain_divisions = set(self.DOMAIN_SIGNALS.get(detected, self.DOMAIN_SIGNALS["general"]))
        return domain_divisions.union(self.CORE_DIVISIONS)
