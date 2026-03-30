from __future__ import annotations

from agent_factory.core.state import AgentSpec


def generate_tutorial(spec: AgentSpec) -> str:
    return f"""# Tutorial

## What This Agent Does
{chr(10).join(f"- {p}" for p in spec.purpose)}

## Typical Flow
1. Prepare environment variables.
2. Start the agent runtime.
3. Call `invoke` with JSON payload.
4. Inspect output and logs.

## Notes
- Language: `{spec.target_language.value}`
- Tools: `{", ".join(spec.tools)}`
"""
