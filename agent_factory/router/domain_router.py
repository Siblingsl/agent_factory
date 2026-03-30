from __future__ import annotations

import re

from agent_factory.core.state import AgentSpec
from agent_factory.registry.models import Division


class DomainRouter:
    DOMAIN_SIGNALS: dict[str, list[Division]] = {
        "game": [Division.GAME_DEVELOPMENT, Division.SPECIALIZED],
        "xr": [Division.SPATIAL_COMPUTING, Division.ENGINEERING],
        "weather": [Division.ENGINEERING, Division.SPECIALIZED, Division.TESTING],
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

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        for term in keywords:
            normalized = term.strip().lower()
            if not normalized:
                continue
            if any("\u4e00" <= ch <= "\u9fff" for ch in normalized):
                if normalized in text:
                    return True
                continue
            pattern = rf"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])"
            if re.search(pattern, text):
                return True
        return False

    def detect_domain(self, spec: AgentSpec) -> str:
        text = " ".join(spec.purpose + spec.tools).lower()
        if self._contains_any(text, ["game", "unity", "unreal", "godot", "游戏"]):
            return "game"
        if self._contains_any(text, ["weather", "forecast", "meteorology", "天气", "气象"]):
            return "weather"
        if self._contains_any(text, ["xr", "ar", "vr", "spatial"]):
            return "xr"
        if self._contains_any(text, ["web3", "blockchain", "solidity", "区块链"]):
            return "web3"
        if self._contains_any(text, ["enterprise", "crm", "erp", "工单", "企业"]):
            return "enterprise"
        if self._contains_any(text, ["mobile", "android", "ios"]):
            return "mobile"
        if self._contains_any(text, ["data", "analysis", "etl", "数据"]):
            return "data"
        if self._contains_any(text, ["marketing", "growth", "campaign", "营销"]):
            return "marketing"
        return "general"

    def route(self, spec: AgentSpec) -> set[Division]:
        detected = self.detect_domain(spec)
        domain_divisions = set(self.DOMAIN_SIGNALS.get(detected, self.DOMAIN_SIGNALS["general"]))
        return domain_divisions.union(self.CORE_DIVISIONS)
