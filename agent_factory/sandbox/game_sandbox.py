from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GameSandboxConfig:
    unity_image: str = "unity-editor-headless:2023.3-lts"
    godot_image: str = "godot-headless:4.x"
    unity_memory: str = "4g"
    godot_memory: str = "2g"
    network_mode: str = "none"
