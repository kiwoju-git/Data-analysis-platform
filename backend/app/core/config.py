import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_workspace_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "DataLabStudio"
    return Path.home() / ".datalabstudio"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATALAB_", env_file=".env", extra="ignore")

    app_name: str = "DataLab Studio"
    environment: str = "development"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    git_commit: str | None = None
    max_upload_bytes: int = 100 * 1024 * 1024
    workspace_root: Path = Field(default_factory=default_workspace_root)
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173"],
    )

    @field_validator("bind_host")
    @classmethod
    def require_loopback_bind(cls, value: str) -> str:
        allowed_hosts = {"127.0.0.1", "localhost"}
        if value not in allowed_hosts:
            raise ValueError("DATALAB_BIND_HOST must be 127.0.0.1 or localhost")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
