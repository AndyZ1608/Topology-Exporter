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

    def collect_projects(self) -> dict[str, dict]:
        """
        Collect all projects from Keystone.

        Returns:
            Dict mapping project_id to normalized project data.
        """
        if not self.conn:
            logger.warning("No connection - skipping project collection")
            return {}

        try:
            projects = {}
            for project in self.conn.identity.projects():
                projects[project.id] = {
                    "id": project.id,
                    "name": project.name,
                    "domain_id": project.domain_id,
                    "enabled": project.enabled,
                    "description": project.description,
                }
            self._projects_cache = projects
            logger.info(f"Collected {len(projects)} projects")
            return projects
        except Exception as exc:
            logger.error("Failed to collect projects (%s)", type(exc).__name__)
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
        except Exception as exc:
            logger.error("Failed to collect domains (%s)", type(exc).__name__)
            return {}

    def get_project_info(self, project_id: str) -> Optional[dict]:
        """Get detailed project information."""
        if not self._projects_cache and self.conn:
            self.collect_projects()
        return self._projects_cache.get(project_id)
