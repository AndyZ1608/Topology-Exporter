"""
OpenStack connection manager.
"""
import logging
from typing import Optional
import openstack
from openstack.connection import Connection

from app.config import settings

logger = logging.getLogger(__name__)


class OpenStackConnectionManager:
    """Manages OpenStack connection lifecycle."""

    def __init__(self):
        self._connection: Optional[Connection] = None
        self._demo_mode = settings.DEMO_MODE

    @property
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self._demo_mode

    def get_connection(self) -> Optional[Connection]:
        """Get or create OpenStack connection."""
        if self._demo_mode:
            logger.info("Running in DEMO_MODE - no real OpenStack connection")
            return None

        if self._connection is not None:
            return self._connection

        try:
            # Load from clouds.yaml
            if settings.clouds_yaml and settings.clouds_yaml.exists():
                self._connection = openstack.connect(
                    cloud=settings.OS_CLOUD,
                    clouds_yaml=str(settings.clouds_yaml),
                )
                logger.info(f"Connected to OpenStack cloud: {settings.OS_CLOUD}")
                return self._connection

            # Fallback to environment variables
            self._connection = openstack.connect(
                auth_url=settings.OS_AUTH_URL,
                appCredentialId=None,
                appCredentialName=None,
                username=settings.OS_USERNAME,
                password=settings.OS_PASSWORD,
                project_name=settings.OS_PROJECT_NAME,
                user_domain_name=settings.OS_USER_DOMAIN_NAME,
                project_domain_name=settings.OS_PROJECT_DOMAIN_NAME,
                region_name=settings.OS_REGION_NAME,
            )
            logger.info(f"Connected to OpenStack via environment variables")
            return self._connection

        except Exception as e:
            logger.error(f"Failed to connect to OpenStack: {e}")
            raise

    def close(self):
        """Close the connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            self._connection = None

    def reconnect(self):
        """Force reconnect."""
        self.close()
        return self.get_connection()


# Global connection manager instance
connection_manager = OpenStackConnectionManager()


def get_connection() -> Optional[Connection]:
    """Dependency for getting OpenStack connection."""
    return connection_manager.get_connection()
