# Agent Factory (Formal Main Flow Scaffold)

This repository contains a formal, non-MVP scaffold of the Agent Factory main workflow described in `agent_factory_merged.md`.

## Implemented Main Flow

- Intake -> Domain Router -> Cost Estimate
- Dispatch Phase 1 (discussion team)
- Discussion stage (parallel board orchestration)
- Dispatch Phase 2 (development team)
- Development -> Quality Gate
- Failure Classifier -> Recovery Strategy -> Remediation/Human/Degrade
- Packaging -> Delivery
- Checkpoint-style interrupts are supported when LangGraph is installed.

## Structure

The folder layout follows the formal project structure from the design document:

- `agent_factory/core` workflow graph, nodes, and state
- `agent_factory/registry` dynamic role registry
- `agent_factory/router` domain/task routing
- `agent_factory/dispatcher` feedback-aware dispatch logic
- `agent_factory/discussion` async bulletin-board discussion
- `agent_factory/recovery` structured failure + recovery chain
- `agent_factory/delivery` language-aware packaging + contract validation
- `agent_factory/runtime` runtime contract base classes
- `agent_factory/api` FastAPI entrypoint + checkpoint APIs
- `agent_factory/ci` gate runner

## Quick Start

```bash
pip install -e .
uvicorn agent_factory.api.main:app --reload
```

## CI Gate

Run the bootstrap gate checks:

```bash
python -m agent_factory.ci.run_gates --strict
```
