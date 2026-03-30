import asyncio
from agent import GatePythonWeatherAgentBuildAWeatheAgent


def test_agent_invoke():
    async def _run():
        agent = GatePythonWeatherAgentBuildAWeatheAgent()
        out = await agent.invoke({"k": "v"})
        assert out["status"] == "ok"
    asyncio.run(_run())
