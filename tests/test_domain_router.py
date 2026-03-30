from __future__ import annotations

import unittest

from agent_factory.core.state import AgentSpec, TargetLanguage
from agent_factory.router.domain_router import DomainRouter


class DomainRouterTests(unittest.TestCase):
    def test_weather_prompt_should_not_be_misdetected_as_xr(self) -> None:
        spec = AgentSpec(
            name="weather_agent",
            purpose=["build a weather assistant with web search"],
            tools=["web_search"],
            target_user="general",
            dependencies=["pydantic==2.9.2"],
            target_language=TargetLanguage.PYTHON,
        )

        router = DomainRouter()
        domain = router.detect_domain(spec)
        divisions = router.route(spec)

        self.assertEqual(domain, "weather")
        self.assertNotIn("spatial-computing", {d.value for d in divisions})


if __name__ == "__main__":
    unittest.main()
