from __future__ import annotations

import unittest

from agent_factory.core.nodes import (
    cost_estimate_node,
    development_node,
    dispatch_phase1_node,
    dispatch_phase2_node,
    domain_router_node,
    intake_node,
    route_post_dispatch_phase1,
    tool_plan_node,
)
from agent_factory.core.state import ExecutionMode, TargetLanguage, create_initial_state


class MainFlowToolPlanIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_fast_mode_routes_to_tool_plan_and_embeds_plan_into_artifacts(self) -> None:
        state = create_initial_state(
            user_input="named unit_flow_tool_agent build a web assistant with mcp and code execution",
            execution_mode=ExecutionMode.FAST,
            target_language=TargetLanguage.PYTHON,
        )

        state = await intake_node(state)
        state = await domain_router_node(state)
        state = await cost_estimate_node(state)
        state = await dispatch_phase1_node(state)

        self.assertEqual(route_post_dispatch_phase1(state), "tool_plan")

        state = await tool_plan_node(state)
        self.assertTrue(state.get("tool_plans"))
        self.assertEqual(state.get("status"), "tool_plan_ready")

        state = await dispatch_phase2_node(state)
        state = await development_node(state)

        artifacts = state.get("development_artifacts")
        self.assertIsNotNone(artifacts)
        assert artifacts is not None
        self.assertIn("tool_plans", artifacts.metadata)
        self.assertTrue(artifacts.metadata["tool_plans"])

        architecture_doc = artifacts.files.get("docs/ARCHITECTURE.md", "")
        self.assertIn("## Tool Plan", architecture_doc)
        self.assertIn("primary=", architecture_doc)


if __name__ == "__main__":
    unittest.main()
