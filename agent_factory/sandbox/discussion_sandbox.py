from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DiscussionSandboxConfig:
    isolate_role_context: bool = True
    max_parallel_roles: int = 8
    network_enabled: bool = False
