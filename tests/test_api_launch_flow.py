from __future__ import annotations

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from agent_factory.api.main import SESSIONS, app


class ApiLaunchFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        SESSIONS.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        SESSIONS.clear()

    def test_start_resume_python_session_reaches_delivery(self) -> None:
        final_state = self._run_happy_path(
            language="python",
            prompt="named api_launch_python_agent build a weather assistant with web search",
        )
        self.assertEqual(final_state.get("status"), "delivered")
        delivery = final_state.get("delivery_package", {})
        self.assertTrue(delivery.get("validation_passed"))
        self.assertEqual(delivery.get("target_language"), "python")
        self._assert_no_metadata_missing_warning(delivery)
        report = Path(delivery.get("output_dir", "")) / "validation_report.json"
        self.assertTrue(report.exists(), "validation report should exist after real flow run")

    def test_start_resume_node_session_reaches_delivery(self) -> None:
        final_state = self._run_happy_path(
            language="nodejs",
            prompt="named api_launch_node_agent build a weather assistant with web search and mcp",
        )
        self.assertEqual(final_state.get("status"), "delivered")
        delivery = final_state.get("delivery_package", {})
        self.assertTrue(delivery.get("validation_passed"))
        self.assertEqual(delivery.get("target_language"), "nodejs")
        self.assertEqual(delivery.get("entry_file"), "agent.ts")
        self._assert_no_metadata_missing_warning(delivery)

    def test_start_rejects_invalid_language(self) -> None:
        response = self.client.post(
            "/start",
            json={"input": "build assistant", "language": "ruby"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("language 必须为 'python' 或 'nodejs'", response.json().get("detail", ""))

    def _run_happy_path(self, language: str, prompt: str) -> dict:
        start = self.client.post(
            "/start",
            json={
                "input": prompt,
                "language": language,
                "execution_mode": "standard",
            },
        )
        self.assertEqual(start.status_code, 200, start.text)
        payload = start.json()
        session_id = payload["session_id"]
        self.assertTrue(payload["interrupted"])
        self.assertEqual(payload["checkpoint"], "tech_spec_review")
        self.assertEqual(payload["status"], "awaiting_tech_spec_review")

        status = self.client.get(f"/status/{session_id}")
        self.assertEqual(status.status_code, 200, status.text)
        self.assertTrue(status.json()["interrupted"])
        self.assertEqual(status.json()["status"], "awaiting_tech_spec_review")

        result = self.client.get(f"/result/{session_id}")
        self.assertEqual(result.status_code, 200, result.text)
        result_payload = result.json()
        self.assertIn("tool_plans", result_payload)
        self.assertTrue(result_payload["tool_plans"])

        resume = self.client.post(
            f"/resume/{session_id}",
            json={"approved": True},
        )
        self.assertEqual(resume.status_code, 200, resume.text)
        final_state = resume.json()

        final_status = self.client.get(f"/status/{session_id}")
        self.assertEqual(final_status.status_code, 200, final_status.text)
        self.assertFalse(final_status.json()["interrupted"])

        return final_state

    def _assert_no_metadata_missing_warning(self, delivery: dict) -> None:
        contract = delivery.get("validation_report", {}).get("contract", {})
        issues = contract.get("issues", [])
        has_warning = any(
            "factory_metadata.json not found" in str(item.get("message", ""))
            for item in issues
            if isinstance(item, dict)
        )
        self.assertFalse(has_warning, "factory_metadata warning should be resolved")


if __name__ == "__main__":
    unittest.main()
