from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("AGENT_FACTORY_APP_NAME", "agent-factory")
    app_env: str = os.getenv("AGENT_FACTORY_ENV", "dev")
    database_url: str | None = os.getenv("DATABASE_URL")
    output_root: str = os.getenv("AGENT_FACTORY_OUTPUT_ROOT", "output")
    registry_path: str = os.getenv(
        "AGENT_FACTORY_REGISTRY_PATH", "agent_factory/registry/agency_agents"
    )
    default_language: str = os.getenv("AGENT_FACTORY_DEFAULT_LANGUAGE", "python")
    default_execution_mode: str = os.getenv(
        "AGENT_FACTORY_DEFAULT_EXECUTION_MODE", "standard"
    )
    max_retries: int = int(os.getenv("AGENT_FACTORY_MAX_RETRIES", "3"))


settings = Settings()
