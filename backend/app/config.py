"""Validated application configuration loaded from environment variables."""

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, SecretStr
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def parse_cors_origins(value: Any) -> list[str]:
    """Accept either a JSON array or a comma-separated list of origins."""
    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return DEFAULT_CORS_ORIGINS.copy()

        if raw_value.startswith("["):
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise ValueError("CORS_ORIGINS must be valid JSON or comma-separated") from exc
        else:
            value = raw_value.split(",")

    if not isinstance(value, (list, tuple, set)):
        raise ValueError("CORS_ORIGINS must contain a list of origins")

    origins = [str(origin).strip() for origin in value if str(origin).strip()]
    if not origins:
        raise ValueError("CORS_ORIGINS must contain at least one origin")
    return origins


CorsOrigins = Annotated[
    list[str],
    NoDecode,
    BeforeValidator(parse_cors_origins),
]


class Settings(BaseSettings):
    """Application settings with a single, testable source of validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    APP_NAME: str = "OpenStack Topology Explorer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    OS_CLOUD: str = "openstack"
    CLOUDS_YAML_PATH: str | None = None
    OS_AUTH_URL: str | None = None
    OS_USERNAME: str | None = None
    OS_PASSWORD: SecretStr | None = None
    OS_PROJECT_NAME: str | None = None
    OS_USER_DOMAIN_NAME: str = "Default"
    OS_PROJECT_DOMAIN_NAME: str = "Default"
    OS_REGION_NAME: str = "RegionOne"

    TLS_VERIFY: bool = True
    DATABASE_URL: str = "sqlite:///./topology.db"

    TOPOLOGY_SYNC_INTERVAL: int = 60
    DEMO_MODE: bool = False
    CLASSIFICATION_CONFIG_PATH: str | None = None
    FIREWALL_CONFIG_PATH: str | None = None
    VM_AGGREGATION_THRESHOLD: int = 10

    CORS_ORIGINS: CorsOrigins = DEFAULT_CORS_ORIGINS.copy()
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    OPENSTACK_TIMEOUT: int = 30
    REQUEST_TIMEOUT: int = 60

    @property
    def clouds_yaml(self) -> Path | None:
        """Return an explicitly configured or conventional clouds.yaml path."""
        if self.CLOUDS_YAML_PATH:
            return Path(self.CLOUDS_YAML_PATH)

        for location in (
            Path.cwd() / "config" / "clouds.yaml",
            Path.home() / ".config" / "openstack" / "clouds.yaml",
            Path.home() / ".openstack" / "clouds.yaml",
            Path.cwd() / "clouds.yaml",
        ):
            if location.exists():
                return location
        return None

    @property
    def classification_config_path(self) -> Path | None:
        """Return an explicitly configured or conventional classification file."""
        if self.CLASSIFICATION_CONFIG_PATH:
            return Path(self.CLASSIFICATION_CONFIG_PATH)

        for location in (
            Path.cwd() / "config" / "classification.yaml",
            Path(__file__).parent.parent.parent / "config" / "classification.yaml",
        ):
            if location.exists():
                return location
        return None

    @property
    def firewall_config_path(self) -> Path | None:
        """Return the explicit firewall mapping file when configured."""
        if self.FIREWALL_CONFIG_PATH:
            return Path(self.FIREWALL_CONFIG_PATH)
        location = Path.cwd() / "config" / "firewalls.yaml"
        return location if location.exists() else None


settings = Settings()
