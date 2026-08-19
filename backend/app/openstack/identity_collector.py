"""
Keystone identity collector for projects and domains.
"""
import logging
from typing import Optional
from openstack.connection import Connection

logger = logging.getLogger(__name__)


class IdentityCollector:
    """Collects identity information from Keystone."""

    def __init__(self, conn: Optional[Connection] = None):
        self.conn = conn
        self._projects_cache: dict = {}
        self._domains_cache: dict = {}

    @staticmethod
    def _value(resource, name, default=None):
        value = getattr(resource, name, None)
        if value is not None:
            return value
        try:
            value = resource.get(name)
        except (AttributeError, TypeError):
            value = None
        return default if value is None else value

    def find_domain(self, domain_name: str) -> dict:
        """Find one enabled domain by exact name using the system token."""
        if not self.conn:
            raise RuntimeError("No system-scoped connection for domain discovery")

        try:
            for domain in self.conn.identity.domains(name=domain_name):
                if self._value(domain, "name") == domain_name:
                    result = {
                        "id": self._value(domain, "id"),
                        "name": self._value(domain, "name"),
                        "enabled": bool(self._value(domain, "enabled", True)),
                    }
                    if not result["enabled"]:
                        raise RuntimeError(f"Topology domain is disabled: {domain_name}")
                    self._domains_cache[result["id"]] = result
                    return result
        except Exception:
            logger.exception("Failed to discover topology domain name=%s", domain_name)
            raise
        raise RuntimeError(f"Topology domain not found: {domain_name}")

    def collect_projects(self, domain_id: str | None = None) -> dict[str, dict]:
        """
        Collect projects from Keystone, optionally restricted to one domain.

        Returns:
            Dict mapping project_id to normalized project data.
        """
        if not self.conn:
            logger.warning("No connection - skipping project collection")
            return {}

        try:
            projects = {}
            query = {"domain_id": domain_id} if domain_id else {}
            for project in self.conn.identity.projects(**query):
                project_domain_id = self._value(project, "domain_id")
                if domain_id and project_domain_id != domain_id:
                    continue
                project_id = self._value(project, "id")
                projects[project_id] = {
                    "id": project_id,
                    "name": self._value(project, "name"),
                    "domain_id": project_domain_id,
                    "enabled": bool(self._value(project, "enabled", True)),
                    "description": self._value(project, "description"),
                }
            self._projects_cache = projects
            logger.info(f"Collected {len(projects)} projects")
            return projects
        except Exception:
            logger.exception("Failed to collect projects domain_id=%s", domain_id)
            raise

    def get_project_name(self, project_id: str) -> str:
        """Get project name by ID."""
        if project_id in self._projects_cache:
            return self._projects_cache[project_id]["name"]

        # Try to fetch from cache
        if not self._projects_cache and self.conn:
            self.collect_projects()

        if project_id in self._projects_cache:
            return self._projects_cache[project_id]["name"]
        return project_id

    def collect_domains(self) -> dict[str, dict]:
        """Collect all domains."""
        if not self.conn:
            return {}

        try:
            domains = {}
            for domain in self.conn.identity.domains():
                domains[domain.id] = {
                    "id": domain.id,
                    "name": domain.name,
                    "enabled": domain.enabled,
                }
            self._domains_cache = domains
            logger.info(f"Collected {len(domains)} domains")
            return domains
        except Exception:
            logger.exception("Failed to collect domains")
            raise

    def get_project_info(self, project_id: str) -> Optional[dict]:
        """Get detailed project information."""
        if not self._projects_cache and self.conn:
            self.collect_projects()
        return self._projects_cache.get(project_id)
