"""Connection configuration and credential-safe logging tests."""

import logging

import pytest

from app.config import settings
from app.openstack.connection import OpenStackConnectionManager


def test_custom_clouds_yaml_uses_sdk_config_loader(monkeypatch, tmp_path):
    clouds_file = tmp_path / "clouds.yaml"
    clouds_file.write_text("clouds: {}\n", encoding="utf-8")
    captured = {}

    class FakeLoader:
        def __init__(self, config_files):
            captured["config_files"] = config_files

        def get_one(self, **kwargs):
            captured["options"] = kwargs
            return "cloud-region"

    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "CLOUDS_YAML_PATH", str(clouds_file))
    monkeypatch.setattr("app.openstack.connection.OpenStackConfig", FakeLoader)
    monkeypatch.setattr(
        "app.openstack.connection.openstack.connect",
        lambda **kwargs: captured.setdefault("connect", kwargs) or object(),
    )

    manager = OpenStackConnectionManager()
    manager.get_connection()

    assert captured["config_files"] == [str(clouds_file)]
    assert captured["options"]["api_timeout"] == settings.OPENSTACK_TIMEOUT
    assert captured["connect"] == {"config": "cloud-region"}


def test_connection_error_does_not_log_exception_message(monkeypatch, caplog):
    secret = "super-secret-token"
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "CLOUDS_YAML_PATH", None)
    monkeypatch.setattr(
        "app.openstack.connection.openstack.connect",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError(secret)),
    )

    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
        OpenStackConnectionManager().get_connection()

    assert secret not in caplog.text
    assert "RuntimeError" in caplog.text
