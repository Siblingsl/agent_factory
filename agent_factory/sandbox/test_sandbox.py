from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TestSandboxConfig:
    runtime: str = "docker-compose"
    network_mode: str = "bridge"
    enable_network_simulation: bool = True
    memory_limit: str = "1g"
