from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GatePythonWeatherAgentBuildAWeatheAgent:
    name: str = "gate_python_weather_agent_build_a_weathe"
    purpose: str = "named gate_python_weather_agent build a weather assistant with web search"
    tools: tuple[str, ...] = ('web_search', 'code_exec',)

    async def invoke(self, payload: Any) -> dict[str, Any]:
        return {
            "agent": self.name,
            "purpose": self.purpose,
            "tools": list(self.tools),
            "input": payload,
            "status": "ok",
        }

    def get_manifest(self) -> dict[str, Any]:
        return {
            "agent_id": self.name,
            "agent_name": self.name,
            "version": "1.0.0",
            "description": self.purpose,
            "supported_input_types": ["json", "text"],
            "supported_output_types": ["json"],
            "primary_use_cases": ["automation"],
            "tools_available": list(self.tools),
            "mcp_servers": [],
            "skills_loaded": [],
            "max_context_tokens": 8000,
            "max_response_tokens": 1024,
            "max_concurrent_sessions": 8,
            "timeout_seconds": 60,
            "required_env_vars": [],
            "required_services": [],
            "min_memory_mb": 256,
            "factory_metadata": {},
        }

    async def health_check(self) -> dict[str, str]:
        return {"status": "healthy"}

    async def ready_check(self) -> bool:
        return True


if __name__ == "__main__":
    import asyncio

    async def _main() -> None:
        agent = GatePythonWeatherAgentBuildAWeatheAgent()
        result = await agent.invoke({"hello": "world"})
        print(result)

    asyncio.run(_main())
