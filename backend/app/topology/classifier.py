"""
Device classification engine for firewall, load balancer, etc. detection.
"""
import logging
import re
from typing import Optional
from pathlib import Path
import yaml

from app.config import settings

logger = logging.getLogger(__name__)


class ClassificationRule:
    """A single classification rule."""

    def __init__(self, name: str, patterns: list[str]):
        self.name = name
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def matches(self, text: str) -> bool:
        """Check if text matches any pattern."""
        if not text:
            return False
        return any(pattern.search(text) for pattern in self.patterns)


class InterfaceClassifier:
    """Classifies firewall interfaces (MGMT, WAN, LAN, etc.)."""

    def __init__(self, config: dict = None):
        self.rules = {}
        if config:
            self._load_from_config(config)

    def _load_from_config(self, config: dict):
        """Load interface classification rules from config."""
        interfaces = config.get("interfaces", {})
        for role, rules in interfaces.items():
            self.rules[role] = rules.get("network_patterns", [])

    def classify_interface(self, port: dict, network: dict = None) -> str:
        """
        Classify a firewall interface.

        Returns: MGMT, WAN, LAN, TRUNK, HA, UNKNOWN
        """
        # 1. Check port tags
        tags = port.get("tags", [])
        for tag in tags:
            if tag.lower() in ["mgmt", "management"]:
                return "MGMT"
            if tag.lower() in ["wan", "external"]:
                return "WAN"
            if tag.lower() in ["lan", "internal"]:
                return "LAN"
            if tag.lower() in ["trunk"]:
                return "TRUNK"
            if tag.lower() in ["ha", "heartbeat"]:
                return "HA"

        # 2. Check network tags
        if network:
            network_tags = network.get("tags", [])
            for tag in network_tags:
                if tag.lower() in ["mgmt", "management"]:
                    return "MGMT"
                if tag.lower() in ["wan", "external"]:
                    return "WAN"
                if tag.lower() in ["lan", "internal"]:
                    return "LAN"
                if tag.lower() in ["trunk"]:
                    return "TRUNK"
                if tag.lower() in ["ha", "heartbeat"]:
                    return "HA"

        # 3. Check network naming patterns
        if network:
            network_name = network.get("name", "").lower()
            for role, patterns in self.rules.items():
                for pattern in patterns:
                    if re.search(pattern, network_name, re.IGNORECASE):
                        return role

        # 4. Fallback to UNKNOWN
        return "UNKNOWN"


class DeviceClassifier:
    """Classifies devices (firewall, load balancer, VM, etc.)."""

    def __init__(self):
        self.classification_rules: dict[str, list[ClassificationRule]] = {}
        self._load_default_rules()
        self._load_config_rules()

    def _load_default_rules(self):
        """Load default classification patterns."""
        # Firewall patterns
        self.classification_rules["firewall"] = [
            ClassificationRule("palo_alto", [r"^PAN\d+", r"panorama", r"(?i)palo"]),
            ClassificationRule("fortinet", [r"(?i)forti(gate|manager|analyzer)", r"(?i)fortinet"]),
            ClassificationRule("checkpoint", [r"(?i)checkpoint", r"(?i)cloudguard", r"^CP-"]),
            ClassificationRule("juniper", [r"(?i)srx", r"(?i)juniper", r"(?i)firefly"]),
            ClassificationRule("cisco", [r"(?i)asa", r"(?i)firepower", r"(?i)cisco-fw"]),
            ClassificationRule("linux_iptables", [r"(?i)fw", r"(?i)firewall", r"(?i)router"]),
            ClassificationRule("pfsense", [r"(?i)pfsense", r"(?i)opnsense"]),
        ]

        # Load balancer patterns
        self.classification_rules["load_balancer"] = [
            ClassificationRule("octavia", [r"(?i)octavia", r"(?i)loadbalancer"]),
            ClassificationRule("haproxy", [r"(?i)haproxy", r"(?i)lb-"]),
            ClassificationRule("nginx", [r"(?i)nginx-lb", r"(?i)nginx-lb"]),
        ]

        # Kubernetes patterns
        self.classification_rules["kubernetes"] = [
            ClassificationRule("k8s", [r"(?i)k8s", r"(?i)kubernetes"]),
            ClassificationRule("worker", [r"(?i)worker", r"(?i)node-"]),
            ClassificationRule("control_plane", [r"(?i)control-plane", r"(?i)master", r"(?i)controller"]),
        ]

        # Router patterns
        self.classification_rules["router"] = [
            ClassificationRule("neutron_router", [r"(?i)neutron-router", r"(?i)router-"]),
        ]

    def _load_config_rules(self):
        """Load classification rules from config file."""
        config_path = settings.classification_config_path
        if not config_path:
            return

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            devices = config.get("devices", {})
            for device_type, device_config in devices.items():
                patterns = device_config.get("patterns", [])
                if patterns:
                    self.classification_rules[device_type] = [
                        ClassificationRule(device_type, patterns)
                    ]

            logger.info(f"Loaded classification rules from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load classification config: {e}")

    def classify(
        self,
        server: dict,
        ports: list[dict] = None,
        manual_override: dict = None,
    ) -> str:
        """
        Classify a device.

        Priority:
        1. Manual classification from DB
        2. Server metadata
        3. Server tags
        4. Classification rules
        5. Default = vm
        """
        # 1. Manual override (from DB)
        if manual_override and manual_override.get("role"):
            return manual_override["role"]

        # 2. Server metadata
        metadata = server.get("metadata", {})
        if metadata.get("device_role"):
            return metadata["device_role"]

        # 3. Server tags
        tags = server.get("tags", [])
        for tag in tags:
            if tag.startswith("device_role="):
                return tag.split("=", 1)[1]

        # 4. Classification rules
        server_name = server.get("name", "")

        for device_type, rules in self.classification_rules.items():
            for rule in rules:
                if rule.matches(server_name):
                    return device_type

        # 5. Check number of ports (firewalls often have multiple NICs)
        if ports and len(ports) >= 2:
            # Additional heuristics could go here
            pass

        # 6. Default
        return "vm"

    def get_device_vendor(self, server: dict) -> Optional[str]:
        """Extract device vendor from metadata or name."""
        metadata = server.get("metadata", {})

        # Check metadata
        if metadata.get("device_vendor"):
            return metadata["device_vendor"]

        # Check tags
        tags = server.get("tags", [])
        for tag in tags:
            if tag.startswith("device_vendor="):
                return tag.split("=", 1)[1]

        # Try to infer from name
        server_name = server.get("name", "").lower()
        if "palo" in server_name:
            return "Palo Alto"
        if "forti" in server_name:
            return "Fortinet"
        if "checkpoint" in server_name or "cloudguard" in server_name:
            return "Check Point"
        if "juniper" in server_name or "srx" in server_name:
            return "Juniper"
        if "cisco" in server_name:
            return "Cisco"

        return None

    def get_ha_group(self, server: dict) -> Optional[str]:
        """Extract HA group from metadata or tags."""
        metadata = server.get("metadata", {})

        # Check metadata
        if metadata.get("device_group"):
            return metadata["device_group"]

        # Check tags
        tags = server.get("tags", [])
        for tag in tags:
            if tag.startswith("device_group="):
                return tag.split("=", 1)[1]

        return None

    def get_classification_metadata(self, server: dict) -> dict:
        """Get all classification-related metadata."""
        return {
            "vendor": self.get_device_vendor(server),
            "ha_group": self.get_ha_group(server),
            "role": self.classify(server),
        }


class ClassificationEngine:
    """Main classification engine combining device and interface classification."""

    def __init__(self):
        self.device_classifier = DeviceClassifier()
        self.interface_classifier = InterfaceClassifier()

        # Manual overrides (loaded from DB)
        self._manual_overrides: dict[str, dict] = {}

    def set_manual_overrides(self, overrides: dict[str, dict]):
        """Set manual classification overrides."""
        self._manual_overrides = overrides

    def classify_server(
        self,
        server: dict,
        ports: list[dict],
        networks: dict = None,
    ) -> dict:
        """
        Classify a server and its interfaces.

        Returns classification info including role, vendor, ha_group, interfaces.
        """
        server_id = server["id"]
        manual_override = self._manual_overrides.get(server_id)

        # Classify device type
        role = self.device_classifier.classify(server, ports, manual_override)
        vendor = self.device_classifier.get_device_vendor(server)
        ha_group = self.device_classifier.get_ha_group(server)

        # Classify interfaces if it's a firewall
        interfaces = {}
        if role == "firewall" and networks:
            for port in ports:
                network = networks.get(port.get("network_id"))
                interface_role = self.interface_classifier.classify_interface(port, network)
                interfaces[port["id"]] = {
                    "role": interface_role,
                    "network_id": port.get("network_id"),
                    "ip_addresses": [ip.get("ip_address") for ip in port.get("fixed_ips", []) if ip.get("ip_address")],
                }

        return {
            "role": role,
            "vendor": vendor,
            "ha_group": ha_group,
            "interfaces": interfaces,
            "manual_override": bool(manual_override),
        }

    def get_ha_groups(self, servers: list[dict], ports: dict) -> dict[str, list[str]]:
        """
        Group firewall servers into HA groups.

        Returns: {ha_group_name: [server_id, ...]}
        """
        ha_groups: dict[str, list[str]] = {}

        for server in servers:
            role = self.device_classifier.classify(server)
            if role == "firewall":
                ha_group = self.device_classifier.get_ha_group(server)
                if ha_group:
                    if ha_group not in ha_groups:
                        ha_groups[ha_group] = []
                    ha_groups[ha_group].append(server["id"])

        return ha_groups
