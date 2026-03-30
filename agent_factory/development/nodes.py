from __future__ import annotations

from agent_factory.core.state import AgentSpec, TargetLanguage, TechSpec


def build_entry_file(spec: AgentSpec, tech_spec: TechSpec) -> tuple[str, str]:
    language = spec.target_language
    if language == TargetLanguage.NODEJS:
        file_name = "agent.ts"
        content = _node_entry(spec, tech_spec)
    else:
        file_name = "agent.py"
        content = _python_entry(spec, tech_spec)
    return file_name, content


def build_node_runtime_file(spec: AgentSpec) -> tuple[str, str] | None:
    if spec.target_language != TargetLanguage.NODEJS:
        return None
    cls_name = spec.name.title().replace("_", "") + "Agent"
    return (
        "agent.js",
        f"""class {cls_name} {{
  constructor() {{
    this.name = "{spec.name}";
    this.purpose = "{'; '.join(spec.purpose)}";
    this.tools = [{", ".join(repr(t) for t in spec.tools)}];
  }}

  async invoke(payload) {{
    return {{
      agent: this.name,
      purpose: this.purpose,
      tools: this.tools,
      input: payload,
      status: "ok",
    }};
  }}
}}

if (require.main === module) {{
  const agent = new {cls_name}();
  agent.invoke({{ hello: "world" }}).then((r) => console.log(r));
}}

module.exports = {{ {cls_name} }};
""",
    )


def build_config_files(spec: AgentSpec, tech_spec: TechSpec) -> dict[str, str]:
    return {
        "agent_config.yaml": _agent_config(spec, tech_spec),
        "system_prompt.md": _system_prompt(spec),
        "agent_identity.yaml": _identity(spec),
    }


def build_tests(spec: AgentSpec) -> dict[str, str]:
    if spec.target_language == TargetLanguage.NODEJS:
        return {
            "tests/agent.spec.ts": _node_test(spec),
            "tsconfig.json": _tsconfig(),
        }
    return {"tests/test_agent.py": _python_test(spec)}


def _python_entry(spec: AgentSpec, tech_spec: TechSpec) -> str:
    purpose = "; ".join(spec.purpose)
    tools = ", ".join(spec.tools)
    return f"""from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class {spec.name.title().replace("_", "")}Agent:
    name: str = "{spec.name}"
    purpose: str = "{purpose}"
    tools: tuple[str, ...] = ({", ".join(repr(t) for t in spec.tools)},)

    async def invoke(self, payload: Any) -> dict[str, Any]:
        return {{
            "agent": self.name,
            "purpose": self.purpose,
            "tools": list(self.tools),
            "input": payload,
            "status": "ok",
        }}

    def get_manifest(self) -> dict[str, Any]:
        return {{
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
            "factory_metadata": {{}},
        }}

    async def health_check(self) -> dict[str, str]:
        return {{"status": "healthy"}}

    async def ready_check(self) -> bool:
        return True


if __name__ == "__main__":
    import asyncio

    async def _main() -> None:
        agent = {spec.name.title().replace("_", "")}Agent()
        result = await agent.invoke({{"hello": "world"}})
        print(result)

    asyncio.run(_main())
"""


def _node_entry(spec: AgentSpec, tech_spec: TechSpec) -> str:
    purpose = "; ".join(spec.purpose)
    tools = ", ".join(spec.tools)
    return f"""export class {spec.name.title().replace("_", "")}Agent {{
  readonly name = "{spec.name}";
  readonly purpose = "{purpose}";
  readonly tools = [{", ".join(repr(t) for t in spec.tools)}];

  async invoke(payload: unknown): Promise<Record<string, unknown>> {{
    return {{
      agent: this.name,
      purpose: this.purpose,
      tools: this.tools,
      input: payload,
      status: "ok",
    }};
  }}

  getManifest(): Record<string, unknown> {{
    return {{
      agent_id: this.name,
      agent_name: this.name,
      version: "1.0.0",
      description: this.purpose,
      supported_input_types: ["json", "text"],
      supported_output_types: ["json"],
      primary_use_cases: ["automation"],
      tools_available: this.tools,
      mcp_servers: [],
      skills_loaded: [],
      max_context_tokens: 8000,
      max_response_tokens: 1024,
      max_concurrent_sessions: 8,
      timeout_seconds: 60,
      required_env_vars: [],
      required_services: [],
      min_memory_mb: 256,
      factory_metadata: {{}},
    }};
  }}

  async health_check(): Promise<Record<string, string>> {{
    return {{ status: "healthy" }};
  }}

  async ready_check(): Promise<boolean> {{
    return true;
  }}
}}

if (require.main === module) {{
  const agent = new {spec.name.title().replace("_", "")}Agent();
  agent.invoke({{ hello: "world" }}).then((r) => console.log(r));
}}
"""


def _python_test(spec: AgentSpec) -> str:
    cls_name = spec.name.title().replace("_", "") + "Agent"
    return f"""import asyncio
from agent import {cls_name}


def test_agent_invoke():
    async def _run():
        agent = {cls_name}()
        out = await agent.invoke({{"k": "v"}})
        assert out["status"] == "ok"
    asyncio.run(_run())
"""


def _node_test(spec: AgentSpec) -> str:
    cls_name = spec.name.title().replace("_", "") + "Agent"
    return f"""import {{ describe, it, expect }} from "vitest";
import {{ {cls_name} }} from "../agent";

describe("{spec.name}", () => {{
  it("invoke returns ok", async () => {{
    const agent = new {cls_name}();
    const out = await agent.invoke({{ k: "v" }});
    expect(out.status).toBe("ok");
  }});
}});
"""


def _tsconfig() -> str:
    return """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "esModuleInterop": true,
    "strict": true,
    "skipLibCheck": true,
    "outDir": "dist"
  },
  "include": ["*.ts", "tests/**/*.ts"]
}
"""


def _agent_config(spec: AgentSpec, tech_spec: TechSpec) -> str:
    return f"""name: {spec.name}
language: {spec.target_language.value}
architecture: {tech_spec.architecture}
tools:
{chr(10).join(f"  - {t}" for t in spec.tools)}
"""


def _system_prompt(spec: AgentSpec) -> str:
    lines = "\n".join(f"- {p}" for p in spec.purpose)
    return f"""# System Prompt

You are `{spec.name}`.

Objectives:
{lines}
"""


def _identity(spec: AgentSpec) -> str:
    return f"""agent_id: {spec.name}
persona: reliable-executor
constraints:
  - follow runtime contract
  - provide explicit failure messages
"""
