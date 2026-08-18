"""
Unit tests for the classification engine.
"""
import pytest
from app.topology.classifier import DeviceClassifier, InterfaceClassifier, ClassificationEngine


class TestDeviceClassifier:
    """Tests for DeviceClassifier."""

    @pytest.fixture
    def classifier(self):
        return DeviceClassifier()

    def test_firewall_like_name_is_not_implicitly_trusted(self, classifier):
        """A name alone must never create an infrastructure relationship."""
        server = {"name": "PAN01", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

        server = {"name": "palo-fw-01", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

    def test_classify_fortinet_by_name(self, classifier):
        """Test Fortinet detection by name."""
        server = {"name": "FortiGate-100F", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

        server = {"name": "fortinet-fw", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

    def test_classify_checkpoint_by_name(self, classifier):
        """Test Check Point detection by name."""
        server = {"name": "CP-12345", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

        server = {"name": "cloudguard-gw", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

    def test_classify_regular_vm(self, classifier):
        """Test regular VM classification."""
        server = {"name": "web-server-01", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

        server = {"name": "db-primary", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "vm"

    def test_classify_kubernetes_by_name(self, classifier):
        """Test Kubernetes detection by name."""
        server = {"name": "k8s-worker-01", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "kubernetes"

        server = {"name": "control-plane-01", "metadata": {}, "tags": []}
        assert classifier.classify(server) == "kubernetes"

    def test_classify_metadata_override(self, classifier):
        """Test metadata-based classification."""
        server = {
            "name": "generic-server",
            "metadata": {"device_role": "firewall"},
            "tags": []
        }
        assert classifier.classify(server) == "firewall"

    def test_classify_tag_override(self, classifier):
        """Test tag-based classification."""
        server = {
            "name": "generic-server",
            "metadata": {},
            "tags": ["device_role=firewall"]
        }
        assert classifier.classify(server) == "firewall"

    def test_classify_manual_override(self, classifier):
        """Test manual override from DB."""
        server = {"name": "generic-server", "metadata": {}, "tags": []}
        override = {"role": "load_balancer"}
        assert classifier.classify(server, manual_override=override) == "load_balancer"

    def test_get_device_vendor_palo(self, classifier):
        """Test vendor extraction for Palo Alto."""
        server = {
            "name": "PAN01",
            "metadata": {"device_vendor": "Palo Alto"},
            "tags": []
        }
        assert classifier.get_device_vendor(server) == "Palo Alto"

    def test_device_vendor_is_not_inferred_from_name(self, classifier):
        server = {"name": "PAN01", "metadata": {}, "tags": []}
        assert classifier.get_device_vendor(server) is None

        server = {"name": "fortigate-fw", "metadata": {}, "tags": []}
        assert classifier.get_device_vendor(server) is None

class TestInterfaceClassifier:
    """Tests for InterfaceClassifier."""

    @pytest.fixture
    def classifier(self):
        return InterfaceClassifier({
            "WAN": {"network_patterns": ["wan", "external"]},
            "LAN": {"network_patterns": ["lan", "internal"]},
            "MGMT": {"network_patterns": ["mgmt", "management"]},
            "HA": {"network_patterns": ["ha", "heartbeat"]},
        })

    def test_classify_by_port_tags(self, classifier):
        """Test interface classification by port tags."""
        port = {"tags": ["wan"]}
        assert classifier.classify_interface(port) == "WAN"

        port = {"tags": ["mgmt"]}
        assert classifier.classify_interface(port) == "MGMT"

    def test_classify_by_network_tags(self, classifier):
        """Test interface classification by network tags."""
        port = {"tags": []}
        network = {"tags": ["wan"]}
        assert classifier.classify_interface(port, network) == "WAN"

    def test_classify_by_network_name(self, classifier):
        """Test interface classification by network name patterns."""
        port = {"tags": []}
        network = {"name": "WAN-01"}
        assert classifier.classify_interface(port, network) == "WAN"

        network = {"name": "Internal-LAN"}
        assert classifier.classify_interface(port, network) == "LAN"

    def test_classify_unknown(self, classifier):
        """Test unknown interface classification."""
        port = {"tags": []}
        network = {"name": "random-network"}
        assert classifier.classify_interface(port, network) == "UNKNOWN"


class TestClassificationEngine:
    """Tests for ClassificationEngine."""

    @pytest.fixture
    def engine(self):
        return ClassificationEngine()

    def test_classify_server_firewall(self, engine):
        """Test server classification as firewall."""
        server = {
            "id": "server-1",
            "name": "PAN01",
            "metadata": {"device_role": "firewall", "device_vendor": "Palo Alto"},
            "tags": []
        }
        ports = [
            {"id": "port-1", "network_id": "net-1", "fixed_ips": [{"ip_address": "10.0.0.2"}]}
        ]
        networks = {"net-1": {"name": "wan-net", "tags": ["wan"]}}

        result = engine.classify_server(server, ports, networks)

        assert result["role"] == "firewall"
        assert result["vendor"] == "Palo Alto"
        assert "interfaces" in result
