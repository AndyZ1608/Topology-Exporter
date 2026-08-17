"""
Demo/Mock data generator for development and testing.
"""
import logging
from typing import Optional
from app.topology.graph_builder import GraphBuilder
from app.schemas.topology import TopologyResponse

logger = logging.getLogger(__name__)


class DemoDataGenerator:
    """
    Generates demo topology data matching the specified demo scenario.

    Demo topology:
    - NOC Project
      - PAN01, PAN02 (Palo Alto Firewalls)
      - NOC-WAN (External Network)
      - VLAN10-AV, VLAN20-PAM, VLAN30-Monitor (Internal Networks)
      - AV01, AV02 (AV Servers)
      - PAM01, PAM02 (PAM Servers)
      - MON01, MON02, MON03 (Monitor Servers)
    """

    # UUIDs for demo data
    PROJECT_ID = "11111111-1111-1111-1111-111111111111"
    PROJECT_NAME = "NOC"

    # Networks
    WAN_NETWORK_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    VLAN10_NETWORK_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    VLAN20_NETWORK_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    VLAN30_NETWORK_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"

    # Subnets
    WAN_SUBNET_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    VLAN10_SUBNET_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    VLAN20_SUBNET_ID = "00000000-0000-0000-0000-000000000001"
    VLAN30_SUBNET_ID = "00000000-0000-0000-0000-000000000002"

    # Firewalls
    PAN01_ID = "22222222-2222-2222-2222-222222222221"
    PAN02_ID = "22222222-2222-2222-2222-222222222222"

    # Servers
    AV01_ID = "33333333-3333-3333-3333-333333333331"
    AV02_ID = "33333333-3333-3333-3333-333333333332"
    PAM01_ID = "33333333-3333-3333-3333-333333333341"
    PAM02_ID = "33333333-3333-3333-3333-333333333342"
    MON01_ID = "33333333-3333-3333-3333-333333333351"
    MON02_ID = "33333333-3333-3333-3333-333333333352"
    MON03_ID = "33333333-3333-3333-3333-333333333353"

    # Ports
    PAN01_WAN_PORT = "44444444-4444-4444-4444-444444444401"
    PAN01_LAN_PORT = "44444444-4444-4444-4444-444444444402"
    PAN02_WAN_PORT = "44444444-4444-4444-4444-444444444403"
    PAN02_LAN_PORT = "44444444-4444-4444-4444-444444444404"

    def __init__(self):
        self.graph_builder = GraphBuilder()

    def generate(self) -> TopologyResponse:
        """Generate the complete demo topology."""
        logger.info("Generating demo topology data...")

        # Define projects
        projects = {
            self.PROJECT_ID: {
                "id": self.PROJECT_ID,
                "name": self.PROJECT_NAME,
                "domain_id": "default",
                "enabled": True,
                "description": "Network Operations Center",
            }
        }

        # Define networks
        networks = {
            self.WAN_NETWORK_ID: {
                "id": self.WAN_NETWORK_ID,
                "name": "NOC-WAN",
                "project_id": self.PROJECT_ID,
                "router:external": True,
                "provider:network_type": "vlan",
                "provider:physical_network": "physnet1",
                "provider:segmentation_id": 100,
                "shared": False,
                "status": "ACTIVE",
                "subnets": [self.WAN_SUBNET_ID],
                "tags": ["wan", "external"],
            },
            self.VLAN10_NETWORK_ID: {
                "id": self.VLAN10_NETWORK_ID,
                "name": "VLAN10-AV",
                "project_id": self.PROJECT_ID,
                "router:external": False,
                "provider:network_type": "vlan",
                "provider:physical_network": "physnet1",
                "provider:segmentation_id": 10,
                "shared": False,
                "status": "ACTIVE",
                "subnets": [self.VLAN10_SUBNET_ID],
                "tags": ["vlan10", "av"],
            },
            self.VLAN20_NETWORK_ID: {
                "id": self.VLAN20_NETWORK_ID,
                "name": "VLAN20-PAM",
                "project_id": self.PROJECT_ID,
                "router:external": False,
                "provider:network_type": "vlan",
                "provider:physical_network": "physnet1",
                "provider:segmentation_id": 20,
                "shared": False,
                "status": "ACTIVE",
                "subnets": [self.VLAN20_SUBNET_ID],
                "tags": ["vlan20", "pam"],
            },
            self.VLAN30_NETWORK_ID: {
                "id": self.VLAN30_NETWORK_ID,
                "name": "VLAN30-Monitor",
                "project_id": self.PROJECT_ID,
                "router:external": False,
                "provider:network_type": "vlan",
                "provider:physical_network": "physnet1",
                "provider:segmentation_id": 30,
                "shared": False,
                "status": "ACTIVE",
                "subnets": [self.VLAN30_SUBNET_ID],
                "tags": ["vlan30", "monitoring"],
            },
        }

        # Define subnets
        subnets = {
            self.WAN_SUBNET_ID: {
                "id": self.WAN_SUBNET_ID,
                "name": "NOC-WAN-Subnet",
                "network_id": self.WAN_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "cidr": "203.0.113.0/24",
                "gateway_ip": "203.0.113.1",
                "ip_version": 4,
                "enable_dhcp": False,
                "dns_nameservers": [],
                "allocation_pools": [],
                "tags": [],
            },
            self.VLAN10_SUBNET_ID: {
                "id": self.VLAN10_SUBNET_ID,
                "name": "VLAN10-AV-Subnet",
                "network_id": self.VLAN10_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "cidr": "10.0.10.0/24",
                "gateway_ip": "10.0.10.1",
                "ip_version": 4,
                "enable_dhcp": True,
                "dns_nameservers": ["10.0.10.2"],
                "allocation_pools": [{"start": "10.0.10.10", "end": "10.0.10.250"}],
                "tags": [],
            },
            self.VLAN20_SUBNET_ID: {
                "id": self.VLAN20_SUBNET_ID,
                "name": "VLAN20-PAM-Subnet",
                "network_id": self.VLAN20_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "cidr": "10.0.20.0/24",
                "gateway_ip": "10.0.20.1",
                "ip_version": 4,
                "enable_dhcp": True,
                "dns_nameservers": ["10.0.20.2"],
                "allocation_pools": [{"start": "10.0.20.10", "end": "10.0.20.250"}],
                "tags": [],
            },
            self.VLAN30_SUBNET_ID: {
                "id": self.VLAN30_SUBNET_ID,
                "name": "VLAN30-Monitor-Subnet",
                "network_id": self.VLAN30_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "cidr": "10.0.30.0/24",
                "gateway_ip": "10.0.30.1",
                "ip_version": 4,
                "enable_dhcp": True,
                "dns_nameservers": ["10.0.30.2"],
                "allocation_pools": [{"start": "10.0.30.10", "end": "10.0.30.250"}],
                "tags": [],
            },
        }

        # Define servers (firewalls first)
        servers = {
            # Firewalls
            self.PAN01_ID: {
                "id": self.PAN01_ID,
                "name": "PAN01",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-01-15T10:00:00Z",
                "metadata": {
                    "device_role": "firewall",
                    "device_vendor": "Palo Alto",
                    "device_group": "PAN-HA",
                },
                "addresses": {
                    "wan": [{"addr": "203.0.113.11", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:11:00:01"}],
                    "vlan10": [{"addr": "10.0.10.2", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:11:00:02"}],
                },
                "fixed_ips": ["203.0.113.11", "10.0.10.2"],
                "mac_addresses": ["fa:16:3e:11:00:01", "fa:16:3e:11:00:02"],
                "flavor_id": "m1.large",
                "flavor_name": "m1.large",
                "host": "compute-node-01",
                "tags": ["firewall", "ha"],
            },
            self.PAN02_ID: {
                "id": self.PAN02_ID,
                "name": "PAN02",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-01-15T10:00:00Z",
                "metadata": {
                    "device_role": "firewall",
                    "device_vendor": "Palo Alto",
                    "device_group": "PAN-HA",
                },
                "addresses": {
                    "wan": [{"addr": "203.0.113.12", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:12:00:01"}],
                    "vlan10": [{"addr": "10.0.10.3", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:12:00:02"}],
                },
                "fixed_ips": ["203.0.113.12", "10.0.10.3"],
                "mac_addresses": ["fa:16:3e:12:00:01", "fa:16:3e:12:00:02"],
                "flavor_id": "m1.large",
                "flavor_name": "m1.large",
                "host": "compute-node-02",
                "tags": ["firewall", "ha"],
            },
            # AV Servers
            self.AV01_ID: {
                "id": self.AV01_ID,
                "name": "av01",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-02-01T08:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan10": [{"addr": "10.0.10.11", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:aa:00:01"}],
                },
                "fixed_ips": ["10.0.10.11"],
                "mac_addresses": ["fa:16:3e:aa:00:01"],
                "flavor_id": "m1.small",
                "flavor_name": "m1.small",
                "host": "compute-node-01",
                "tags": [],
            },
            self.AV02_ID: {
                "id": self.AV02_ID,
                "name": "av02",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-02-01T08:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan10": [{"addr": "10.0.10.12", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:aa:00:02"}],
                },
                "fixed_ips": ["10.0.10.12"],
                "mac_addresses": ["fa:16:3e:aa:00:02"],
                "flavor_id": "m1.small",
                "flavor_name": "m1.small",
                "host": "compute-node-01",
                "tags": [],
            },
            # PAM Servers
            self.PAM01_ID: {
                "id": self.PAM01_ID,
                "name": "pam01",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-02-10T09:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan20": [{"addr": "10.0.20.11", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:bb:00:01"}],
                },
                "fixed_ips": ["10.0.20.11"],
                "mac_addresses": ["fa:16:3e:bb:00:01"],
                "flavor_id": "m1.small",
                "flavor_name": "m1.small",
                "host": "compute-node-01",
                "tags": [],
            },
            self.PAM02_ID: {
                "id": self.PAM02_ID,
                "name": "pam02",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-02-10T09:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan20": [{"addr": "10.0.20.12", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:bb:00:02"}],
                },
                "fixed_ips": ["10.0.20.12"],
                "mac_addresses": ["fa:16:3e:bb:00:02"],
                "flavor_id": "m1.small",
                "flavor_name": "m1.small",
                "host": "compute-node-02",
                "tags": [],
            },
            # Monitor Servers
            self.MON01_ID: {
                "id": self.MON01_ID,
                "name": "monitor01",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-03-01T10:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan30": [{"addr": "10.0.30.15", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:cc:00:01"}],
                },
                "fixed_ips": ["10.0.30.15"],
                "mac_addresses": ["fa:16:3e:cc:00:01"],
                "flavor_id": "m1.medium",
                "flavor_name": "m1.medium",
                "host": "compute-node-01",
                "tags": [],
            },
            self.MON02_ID: {
                "id": self.MON02_ID,
                "name": "monitor02",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-03-01T10:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan30": [{"addr": "10.0.30.16", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:cc:00:02"}],
                },
                "fixed_ips": ["10.0.30.16"],
                "mac_addresses": ["fa:16:3e:cc:00:02"],
                "flavor_id": "m1.medium",
                "flavor_name": "m1.medium",
                "host": "compute-node-01",
                "tags": [],
            },
            self.MON03_ID: {
                "id": self.MON03_ID,
                "name": "monitor03",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "created_at": "2024-03-01T10:00:00Z",
                "metadata": {},
                "addresses": {
                    "vlan30": [{"addr": "10.0.30.17", "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:cc:00:03"}],
                },
                "fixed_ips": ["10.0.30.17"],
                "mac_addresses": ["fa:16:3e:cc:00:03"],
                "flavor_id": "m1.medium",
                "flavor_name": "m1.medium",
                "host": "compute-node-02",
                "tags": [],
            },
        }

        # Define ports
        ports = {
            # PAN01 ports
            self.PAN01_WAN_PORT: {
                "id": self.PAN01_WAN_PORT,
                "name": "PAN01-WAN",
                "network_id": self.WAN_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.PAN01_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:11:00:01",
                "fixed_ips": [{"ip_address": "203.0.113.11", "subnet_id": self.WAN_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": ["wan"],
            },
            self.PAN01_LAN_PORT: {
                "id": self.PAN01_LAN_PORT,
                "name": "PAN01-LAN",
                "network_id": self.VLAN10_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.PAN01_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:11:00:02",
                "fixed_ips": [{"ip_address": "10.0.10.2", "subnet_id": self.VLAN10_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": ["lan"],
            },
            # PAN02 ports
            self.PAN02_WAN_PORT: {
                "id": self.PAN02_WAN_PORT,
                "name": "PAN02-WAN",
                "network_id": self.WAN_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.PAN02_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:12:00:01",
                "fixed_ips": [{"ip_address": "203.0.113.12", "subnet_id": self.WAN_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-02",
                "security_groups": [],
                "tags": ["wan"],
            },
            self.PAN02_LAN_PORT: {
                "id": self.PAN02_LAN_PORT,
                "name": "PAN02-LAN",
                "network_id": self.VLAN10_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.PAN02_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:12:00:02",
                "fixed_ips": [{"ip_address": "10.0.10.3", "subnet_id": self.VLAN10_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-02",
                "security_groups": [],
                "tags": ["lan"],
            },
            # AV01 port
            "av01-port": {
                "id": "av01-port",
                "name": "av01",
                "network_id": self.VLAN10_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.AV01_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:aa:00:01",
                "fixed_ips": [{"ip_address": "10.0.10.11", "subnet_id": self.VLAN10_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": [],
            },
            # AV02 port
            "av02-port": {
                "id": "av02-port",
                "name": "av02",
                "network_id": self.VLAN10_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.AV02_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:aa:00:02",
                "fixed_ips": [{"ip_address": "10.0.10.12", "subnet_id": self.VLAN10_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": [],
            },
            # PAM01 port
            "pam01-port": {
                "id": "pam01-port",
                "name": "pam01",
                "network_id": self.VLAN20_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.PAM01_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:bb:00:01",
                "fixed_ips": [{"ip_address": "10.0.20.11", "subnet_id": self.VLAN20_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": [],
            },
            # PAM02 port
            "pam02-port": {
                "id": "pam02-port",
                "name": "pam02",
                "network_id": self.VLAN20_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.PAM02_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:bb:00:02",
                "fixed_ips": [{"ip_address": "10.0.20.12", "subnet_id": self.VLAN20_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-02",
                "security_groups": [],
                "tags": [],
            },
            # MON01 port
            "mon01-port": {
                "id": "mon01-port",
                "name": "mon01",
                "network_id": self.VLAN30_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.MON01_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:cc:00:01",
                "fixed_ips": [{"ip_address": "10.0.30.15", "subnet_id": self.VLAN30_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": [],
            },
            # MON02 port
            "mon02-port": {
                "id": "mon02-port",
                "name": "mon02",
                "network_id": self.VLAN30_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.MON02_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:cc:00:02",
                "fixed_ips": [{"ip_address": "10.0.30.16", "subnet_id": self.VLAN30_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-01",
                "security_groups": [],
                "tags": [],
            },
            # MON03 port
            "mon03-port": {
                "id": "mon03-port",
                "name": "mon03",
                "network_id": self.VLAN30_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": self.MON03_ID,
                "device_owner": "compute:nova",
                "device_owner_category": "compute",
                "mac_address": "fa:16:3e:cc:00:03",
                "fixed_ips": [{"ip_address": "10.0.30.17", "subnet_id": self.VLAN30_SUBNET_ID}],
                "status": "ACTIVE",
                "binding_host_id": "compute-node-02",
                "security_groups": [],
                "tags": [],
            },
        }

        # Define routers (connecting internal networks to external)
        routers = {
            "noc-router": {
                "id": "noc-router",
                "name": "NOC-Router",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "external_gateway_info": {
                    "network_id": self.WAN_NETWORK_ID,
                    "enable_snat": True,
                    "external_fixed_ips": [],
                },
                "interfaces": [
                    {"port_id": "router-if-vlan10", "network_id": self.VLAN10_NETWORK_ID},
                    {"port_id": "router-if-vlan20", "network_id": self.VLAN20_NETWORK_ID},
                    {"port_id": "router-if-vlan30", "network_id": self.VLAN30_NETWORK_ID},
                ],
            }
        }

        # Add router interface ports
        router_ports = {
            "router-if-vlan10": {
                "id": "router-if-vlan10",
                "name": "router-if-vlan10",
                "network_id": self.VLAN10_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": "noc-router",
                "device_owner": "network:router_interface",
                "device_owner_category": "router_interface",
                "mac_address": "fa:16:3e:dd:00:01",
                "fixed_ips": [{"ip_address": "10.0.10.1", "subnet_id": self.VLAN10_SUBNET_ID}],
                "status": "ACTIVE",
                "security_groups": [],
                "tags": [],
            },
            "router-if-vlan20": {
                "id": "router-if-vlan20",
                "name": "router-if-vlan20",
                "network_id": self.VLAN20_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": "noc-router",
                "device_owner": "network:router_interface",
                "device_owner_category": "router_interface",
                "mac_address": "fa:16:3e:dd:00:02",
                "fixed_ips": [{"ip_address": "10.0.20.1", "subnet_id": self.VLAN20_SUBNET_ID}],
                "status": "ACTIVE",
                "security_groups": [],
                "tags": [],
            },
            "router-if-vlan30": {
                "id": "router-if-vlan30",
                "name": "router-if-vlan30",
                "network_id": self.VLAN30_NETWORK_ID,
                "project_id": self.PROJECT_ID,
                "device_id": "noc-router",
                "device_owner": "network:router_interface",
                "device_owner_category": "router_interface",
                "mac_address": "fa:16:3e:dd:00:03",
                "fixed_ips": [{"ip_address": "10.0.30.1", "subnet_id": self.VLAN30_SUBNET_ID}],
                "status": "ACTIVE",
                "security_groups": [],
                "tags": [],
            },
        }
        ports.update(router_ports)

        # Add floating IPs for monitors
        floating_ips = {
            "fip-mon01": {
                "id": "fip-mon01",
                "floating_ip_address": "203.0.113.101",
                "fixed_ip_address": "10.0.30.15",
                "port_id": "mon01-port",
                "router_id": "noc-router",
                "project_id": self.PROJECT_ID,
                "status": "ACTIVE",
                "floating_network_id": self.WAN_NETWORK_ID,
            },
        }

        # No trunks in demo
        trunks = {}
        security_groups = {}

        # Build topology
        topology = self.graph_builder.build_from_openstack(
            projects=projects,
            servers=servers,
            networks=networks,
            subnets=subnets,
            ports=ports,
            routers=routers,
            floating_ips=floating_ips,
            trunks=trunks,
            security_groups=security_groups,
        )

        # Override to add Internet relationship via router path
        from app.schemas.topology import TopologyEdge
        from app.topology.normalizer import TopologyNormalizer

        # Add Internet node
        normalizer = TopologyNormalizer()
        internet_node = normalizer.create_internet_node()

        # Find external network node
        wan_node = None
        for node in topology.nodes:
            if node.resource_id == self.WAN_NETWORK_ID:
                wan_node = node
                break

        if wan_node:
            # Add router to external network edge
            router_edge = TopologyEdge(
                id="edge-router-wan",
                source="router:noc-router",
                target=f"network:{self.WAN_NETWORK_ID}",
                relationship="external_gateway",
                inferred=False,
                confidence=1.0,
            )
            topology.edges.append(router_edge)

            # Add external network to Internet edge
            internet_edge = TopologyEdge(
                id="edge-wan-internet",
                source=f"network:{self.WAN_NETWORK_ID}",
                target="internet",
                relationship="internet_uplink",
                inferred=True,
                confidence=0.95,
            )
            topology.edges.append(internet_edge)

        # Update metadata
        topology.metadata["demo_mode"] = True
        topology.metadata["demo_scenario"] = "NOC with Palo Alto HA"

        logger.info(f"Generated demo topology: {len(topology.nodes)} nodes, {len(topology.edges)} edges")

        return topology


# Global demo generator
demo_generator = DemoDataGenerator()


def get_demo_topology() -> TopologyResponse:
    """Get the demo topology data."""
    return demo_generator.generate()
