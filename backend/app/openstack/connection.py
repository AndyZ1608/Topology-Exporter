"""OpenStack connection factory with explicit system and project scopes."""

import logging
from importlib.metadata import version
from typing import Optional

import openstack
from openstack.config import OpenStackConfig
from openstack.connection import Connection

from app.config import settings

logger = logging.getLogger(__name__)


class OpenStackConnectionManager:
    """Create one Keystone-only system connection and project connections."""

    def __init__(self):
        self._system_connection: Optional[Connection] = None
        self._project_connections: dict[str, Connection] = {}
        self._demo_mode = settings.DEMO_MODE

    @property
    def is_demo_mode(self) -> bool:
        return self._demo_mode

    @staticmethod
    def _password() -> str | None:
        return settings.OS_PASSWORD.get_secret_value() if settings.OS_PASSWORD else None

    @staticmethod
    def _connection_options() -> dict:
        return {
            "region_name": settings.OS_REGION_NAME,
            "interface": settings.OS_INTERFACE,
            "identity_api_version": settings.OS_IDENTITY_API_VERSION,
            "verify": settings.TLS_VERIFY,
            "api_timeout": settings.OPENSTACK_TIMEOUT,
        }

    @staticmethod
    def _cloud_auth_options(cloud_config) -> dict:
        """Extract base user/password fields without inheriting any scope."""
        auth = cloud_config.config.get("auth", {})
        allowed = (
            "auth_url",
            "username",
            "password",
            "user_id",
            "user_domain_id",
            "user_domain_name",
        )
        return {key: auth[key] for key in allowed if auth.get(key) is not None}

    def get_system_connection(self) -> Optional[Connection]:
        """Return a system-scoped connection used exclusively for Keystone."""
        if self._demo_mode:
            logger.info("Running in DEMO_MODE - no real OpenStack connection")
            return None
        if self._system_connection is not None:
            return self._system_connection

        try:
            logger.info("openstacksdk version=%s", version("openstacksdk"))
            if settings.clouds_yaml and settings.clouds_yaml.exists():
                loader = OpenStackConfig(config_files=[str(settings.clouds_yaml)])
                cloud_config = loader.get_one(
                    cloud=settings.OS_CLOUD,
                    **self._connection_options(),
                )
                self._system_connection = openstack.connect(
                    load_yaml_config=False,
                    load_envvars=False,
                    system_scope="all",
                    **self._cloud_auth_options(cloud_config),
                    **self._connection_options(),
                )
            else:
                self._system_connection = openstack.connect(
                    load_yaml_config=False,
                    load_envvars=False,
                    auth_url=settings.OS_AUTH_URL,
                    username=settings.OS_USERNAME,
                    password=self._password(),
                    user_domain_name=settings.OS_USER_DOMAIN_NAME,
                    system_scope="all",
                    **self._connection_options(),
                )
            logger.info("System-scoped OpenStack connection created for Keystone discovery")
            return self._system_connection
        except Exception:
            logger.exception("Failed to create system-scoped OpenStack connection")
            raise

    def get_project_connection(self, project: dict) -> Connection:
        """Return a strictly project-scoped connection using the same user."""
        project_id = project["id"]
        if project_id in self._project_connections:
            return self._project_connections[project_id]

        system_connection = self.get_system_connection()
        if system_connection is None:
            raise RuntimeError("No OpenStack system connection available")

        try:
            # connect_as_project() preserves unrelated auth settings. Explicit
            # connect_as clears system_scope while setting project scope.
            connection = system_connection.connect_as(
                system_scope=None,
                project_id=project_id,
                project_domain_id=project.get("domain_id"),
            )
            self._project_connections[project_id] = connection
            return connection
        except Exception:
            logger.exception(
                "Failed to create project-scoped connection project=%s id=%s",
                project.get("name"),
                project_id,
            )
            raise

    def get_connection(self) -> Optional[Connection]:
        """Backward-compatible alias for the Keystone system connection."""
        return self.get_system_connection()

    def close(self):
        """Close all cached connections."""
        connections = [
            *self._project_connections.values(),
            self._system_connection,
        ]
        seen: set[int] = set()
        for connection in connections:
            if connection is None or id(connection) in seen:
                continue
            seen.add(id(connection))
            try:
                connection.close()
            except Exception:
                logger.exception("Error closing OpenStack connection")
        self._project_connections.clear()
        self._system_connection = None

    def reconnect(self):
        self.close()
        return self.get_system_connection()


connection_manager = OpenStackConnectionManager()


def get_connection() -> Optional[Connection]:
    """Dependency for the Keystone-only system connection."""
    return connection_manager.get_system_connection()
