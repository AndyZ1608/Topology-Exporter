"""
Application configuration using Pydantic Settings.
"""
import json
import os
from pathlib import Path
from typing import Optional, List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "OpenStack Topology Explorer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # OpenStack
    OS_CLOUD: str = os.getenv("OS_CLOUD", "openstack")
    CLOUDS_YAML_PATH: Optional[str] = os.getenv("CLOUDS_YAML_PATH")
    OS_AUTH_URL: Optional[str] = os.getenv("OS_AUTH_URL")
    OS_USERNAME: Optional[str] = os.getenv("OS_USERNAME")
    OS_PASSWORD: Optional[str] = os.getenv("OS_PASSWORD")
    OS_PROJECT_NAME: Optional[str] = os.getenv("OS_PROJECT_NAME")
    OS_USER_DOMAIN_NAME: str = os.getenv("OS_USER_DOMAIN_NAME", "Default")
    OS_PROJECT_DOMAIN_NAME: str = os.getenv("OS_PROJECT_DOMAIN_NAME", "Default")
    OS_REGION_NAME: str = os.getenv("OS_REGION_NAME", "RegionOne")

    # TLS
    TLS_VERIFY: bool = os.getenv("TLS_VERIFY", "true").lower() != "false"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./topology.db")

    # Sync
    TOPOLOGY_SYNC_INTERVAL: int = int(os.getenv("TOPOLOGY_SYNC_INTERVAL", "60"))

    # Demo mode
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

    # Classification config
    CLASSIFICATION_CONFIG_PATH: Optional[str] = os.getenv("CLASSIFICATION_CONFIG_PATH")

    # Aggregation
    VM_AGGREGATION_THRESHOLD: int = int(os.getenv("VM_AGGREGATION_THRESHOLD", "10"))

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from JSON string or use default."""
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Try splitting by comma for simple cases
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        # Return default if empty or invalid
        return ["http://localhost:5173", "http://localhost:3000"]

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100

    # Timeouts
    OPENSTACK_TIMEOUT: int = 30
    REQUEST_TIMEOUT: int = 60

    @property
    def clouds_yaml(self) -> Optional[Path]:
        """Get clouds.yaml path."""
        if self.CLOUDS_YAML_PATH:
            return Path(self.CLOUDS_YAML_PATH)
        # Check default locations
        default_locations = [
            Path.home() / ".config" / "openstack" / "clouds.yaml",
            Path.home() / ".openstack" / "clouds.yaml",
            Path.cwd() / "clouds.yaml",
        ]
        for loc in default_locations:
            if loc.exists():
                return loc
        return None

    @property
    def classification_config_path(self) -> Optional[Path]:
        """Get classification config path."""
        if self.CLASSIFICATION_CONFIG_PATH:
            return Path(self.CLASSIFICATION_CONFIG_PATH)
        # Check default locations
        default_locations = [
            Path.cwd() / "config" / "classification.yaml",
            Path(__file__).parent.parent.parent / "config" / "classification.yaml",
        ]
        for loc in default_locations:
            if loc.exists():
                return loc
        return None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
