from __future__ import annotations

import unittest

from agent_factory.core.state import AgentSpec, TargetLanguage
from agent_factory.engine.tool_planning import build_tool_chains_for_spec


class ToolPlanningTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_tool_chains_for_requested_tools(self) -> None:
        spec = AgentSpec(
            name="unit_tool_agent",
            purpose=["search and summarize web content"],
            tools=["web_search", "code_exec", "mcp"],
            target_user="developer",
            dependencies=["pydantic==2.9.2"],
            target_language=TargetLanguage.PYTHON,
        )

        chains = await build_tool_chains_for_spec(spec)
        by_task = {c.task_type: c for c in chains}

        self.assertIn("web_search", by_task)
        self.assertIn("code_exec", by_task)
        self.assertIn("mcp", by_task)

        web_chain = by_task["web_search"]
        self.assertTrue(web_chain.primary_tool_id)
        self.assertTrue(web_chain.primary_tool_id.startswith("web_search_"))
        self.assertGreaterEqual(len(web_chain.composition_tool_ids), 1)
        self.assertIsInstance(web_chain.fallback_tool_ids, list)

        code_chain = by_task["code_exec"]
        self.assertTrue(code_chain.primary_tool_id.startswith("code_exec_"))

    async def test_ignores_none_tool(self) -> None:
        spec = AgentSpec(
            name="unit_no_tool_agent",
            purpose=["simple responder"],
            tools=["none"],
            target_user="general",
            dependencies=["pydantic==2.9.2"],
            target_language=TargetLanguage.PYTHON,
        )
        chains = await build_tool_chains_for_spec(spec)
        self.assertEqual(chains, [])


if __name__ == "__main__":
    unittest.main()
