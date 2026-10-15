import os
from functools import lru_cache
from ipaddress import IPv4Address
from pathlib import Path

from pydantic import Field, field_validator, model_validator
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
    frontend_dist: Path | None = None
    trusted_lan: bool = False
    trusted_lan_hosts: list[str] = Field(default_factory=list)
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:8600",
            "http://localhost:8600",
        ],
    )

    @field_validator("bind_host")
    @classmethod
    def validate_bind_host(cls, value: str) -> str:
        allowed_hosts = {"127.0.0.1", "localhost", "0.0.0.0"}
        if value not in allowed_hosts:
            raise ValueError("DATALAB_BIND_HOST must be a supported loopback or LAN bind")
        return value

    @field_validator("trusted_lan_hosts")
    @classmethod
    def validate_lan_hosts(cls, values: list[str]) -> list[str]:
        for value in values:
            address = IPv4Address(value)
            if address.is_unspecified or address.is_multicast or address.is_loopback:
                raise ValueError("LAN hosts must be assigned non-loopback IPv4 addresses")
        if len(values) != len(set(values)):
            raise ValueError("LAN hosts must be unique")
        return values

    @model_validator(mode="after")
    def validate_frontend_dist(self) -> "Settings":
        if self.trusted_lan:
            if (
                self.bind_host != "0.0.0.0"
                or self.frontend_dist is None
                or self.environment != "production"
            ):
                raise ValueError(
                    "Trusted LAN requires the built release UI and an explicit LAN bind"
                )
        elif self.bind_host == "0.0.0.0" or self.trusted_lan_hosts:
            raise ValueError("Non-release API binding must remain 127.0.0.1 or localhost")
        if self.frontend_dist is not None:
            root = self.frontend_dist.resolve()
            workspace = self.workspace_root.resolve()
            if root == workspace or root in workspace.parents or workspace in root.parents:
                raise ValueError("Frontend static files must be separate from the workspace")
            if not (root / "index.html").is_file():
                raise ValueError("DATALAB_FRONTEND_DIST must contain index.html")
            self.frontend_dist = root
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
