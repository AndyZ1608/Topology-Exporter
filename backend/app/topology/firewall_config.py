"""Explicit firewall mappings for infrastructure OpenStack cannot discover."""

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger(__name__)


class FirewallEndpoint(BaseModel):
    external_network: str | None = None
    physical_network: str | None = None


class FirewallMapping(BaseModel):
    id: str
    name: str
    vendor: str | None = None
    type: Literal["external", "openstack"] = "external"
    mode: str | None = None
    members: list[str] = Field(default_factory=list)
    server_ids: list[str] = Field(default_factory=list)
    upstream: FirewallEndpoint = Field(default_factory=FirewallEndpoint)
    downstream: FirewallEndpoint = Field(default_factory=FirewallEndpoint)


def load_firewall_mappings(path: Path | None) -> list[FirewallMapping]:
    """Load validated mappings; an invalid file never breaks discovery startup."""
    if path is None or not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as config_file:
            document = yaml.safe_load(config_file) or {}
        mappings = [FirewallMapping.model_validate(item) for item in document.get("firewalls", [])]
        mapping_ids = [mapping.id for mapping in mappings]
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ValueError("firewall mapping IDs must be unique")
        return mappings
    except (OSError, TypeError, ValueError, yaml.YAMLError, ValidationError) as exc:
        logger.error("Could not load firewall mappings (%s)", type(exc).__name__)
        return []
