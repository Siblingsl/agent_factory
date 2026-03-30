from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DeliverySandboxConfig:
    runtime: str = "clean-container"
    image_python: str = "python:3.12-slim"
    image_node: str = "node:20-slim"
    strict_network: bool = False
    memory_limit: str = "512m"
