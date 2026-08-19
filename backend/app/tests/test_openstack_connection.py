"""Explicit OpenStack scope construction tests."""

import logging

import pytest

from app.config import settings
from app.openstack.connection import OpenStackConnectionManager


class FakeConnection:
    def __init__(self):
        self.scope_calls = []
        self.closed = False

    def connect_as(self, **kwargs):
        self.scope_calls.append(kwargs)
        return FakeConnection()

    def close(self):
        self.closed = True


def test_environment_connection_is_system_scoped_without_global_project(monkeypatch):
    captured = {}
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "CLOUDS_YAML_PATH", None)
    monkeypatch.setattr(
        "app.openstack.connection.openstack.connect",
        lambda **kwargs: captured.update(kwargs) or FakeConnection(),
    )

    OpenStackConnectionManager().get_system_connection()

    assert captured["system_scope"] == "all"
    assert captured["load_yaml_config"] is False
    assert captured["load_envvars"] is False
    assert "project_name" not in captured
    assert "project_id" not in captured
    assert captured["interface"] == "internal"
    assert captured["identity_api_version"] == 3


def test_custom_cloud_is_rescoped_before_use(monkeypatch, tmp_path):
    clouds_file = tmp_path / "clouds.yaml"
    clouds_file.write_text("clouds: {}\n", encoding="utf-8")
    captured = {}
    system_connection = FakeConnection()

    class FakeCloudConfig:
        config = {"auth": {
            "auth_url": "https://keystone.example/v3",
            "username": "topology-reader",
            "password": "secret",
            "user_domain_name": "Default",
            "project_name": "must-not-leak",
        }}

    class FakeLoader:
        def __init__(self, config_files):
            captured["config_files"] = config_files

        def get_one(self, **kwargs):
            captured["options"] = kwargs
            return FakeCloudConfig()

    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "CLOUDS_YAML_PATH", str(clouds_file))
    monkeypatch.setattr("app.openstack.connection.OpenStackConfig", FakeLoader)
    monkeypatch.setattr(
        "app.openstack.connection.openstack.connect",
        lambda **kwargs: captured.update(connect=kwargs) or system_connection,
    )

    OpenStackConnectionManager().get_system_connection()

    assert captured["config_files"] == [str(clouds_file)]
    assert captured["options"]["api_timeout"] == settings.OPENSTACK_TIMEOUT
    assert captured["connect"]["system_scope"] == "all"
    assert captured["connect"]["username"] == "topology-reader"
    assert "project_name" not in captured["connect"]


def test_project_connection_explicitly_clears_system_scope(monkeypatch):
    system_connection = FakeConnection()
    manager = OpenStackConnectionManager()
    manager._demo_mode = False
    manager._system_connection = system_connection

    project_connection = manager.get_project_connection({
        "id": "project-1",
        "name": "NOC",
        "domain_id": "domain-mbfs",
    })

    assert project_connection is manager.get_project_connection({
        "id": "project-1", "name": "NOC", "domain_id": "domain-mbfs"
    })
    assert system_connection.scope_calls == [{
        "system_scope": None,
        "project_id": "project-1",
        "project_domain_id": "domain-mbfs",
    }]


def test_connection_failure_logs_traceback(monkeypatch, caplog):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "CLOUDS_YAML_PATH", None)
    monkeypatch.setattr(
        "app.openstack.connection.openstack.connect",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("authentication failed")),
    )

    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
        OpenStackConnectionManager().get_system_connection()

    assert any(record.exc_info is not None for record in caplog.records)
    assert "Traceback" in caplog.text
