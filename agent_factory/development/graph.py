from __future__ import annotations

from dataclasses import dataclass

from agent_factory.core.state import AgentSpec, DevelopmentArtifacts, TechSpec
from agent_factory.development.nodes import (
    build_config_files,
    build_entry_file,
    build_node_runtime_file,
    build_tests,
)
from agent_factory.router.dev_task_router import DevTaskRouter


@dataclass(slots=True)
class DevelopmentTask:
    description: str
    owners: list[str]


async def run_development_graph(
    spec: AgentSpec,
    tech_spec: TechSpec,
    role_slugs: list[str],
) -> DevelopmentArtifacts:
    router = DevTaskRouter()
    task_roles = router.route(tech_spec)
    tasks = [
        DevelopmentTask(description=task, owners=owners)
        for task, owners in task_roles.items()
    ]

    entry_file, entry_content = build_entry_file(spec, tech_spec)
    files: dict[str, str] = {entry_file: entry_content}
    node_runtime = build_node_runtime_file(spec)
    if node_runtime:
        files[node_runtime[0]] = node_runtime[1]
    files.update(build_config_files(spec, tech_spec))
    files.update(build_tests(spec))
    files["docs/ARCHITECTURE.md"] = _architecture_doc(spec, tech_spec, tasks, role_slugs)
    files["docs/API.md"] = _api_doc(spec, entry_file)

    return DevelopmentArtifacts(
        entry_file=entry_file,
        files=files,
        dependencies=tech_spec.dependencies,
        metadata={
            "task_count": len(tasks),
            "assigned_roles": role_slugs,
            "task_owners": {t.description: t.owners for t in tasks},
        },
    )


def _architecture_doc(
    spec: AgentSpec, tech_spec: TechSpec, tasks: list[DevelopmentTask], role_slugs: list[str]
) -> str:
    task_lines = "\n".join(f"- {t.description} :: {', '.join(t.owners)}" for t in tasks)
    return f"""# Architecture

Agent: `{spec.name}`
Language: `{spec.target_language.value}`
Execution Model: layered workflow

## Tech Stack
{chr(10).join(f"- {item}" for item in tech_spec.tech_stack)}

## Task Routing
{task_lines}

## Assigned Roles
{chr(10).join(f"- {r}" for r in role_slugs)}
"""

TODO : 123

def _api_doc(spec: AgentSpec, entry_file: str) -> str:
    return f"""# API

Main entry: `{entry_file}`

Invoke contract:
- input: JSON-serializable payload
- output: object with `status`, `input`, `agent`
"""
