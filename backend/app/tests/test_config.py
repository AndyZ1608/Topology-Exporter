"""Regression tests for environment-backed application settings."""

from app.config import Settings


def test_cors_origins_accept_comma_separated_environment(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://noc.example, https://ops.example")

    configured = Settings(_env_file=None)

    assert configured.CORS_ORIGINS == [
        "https://noc.example",
        "https://ops.example",
    ]


def test_cors_origins_accept_json_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["https://noc.example", "https://ops.example"]',
    )

    configured = Settings(_env_file=None)

    assert configured.CORS_ORIGINS == [
        "https://noc.example",
        "https://ops.example",
    ]


def test_openstack_password_is_masked(monkeypatch):
    monkeypatch.setenv("OS_PASSWORD", "super-secret")

    configured = Settings(_env_file=None)

    assert "super-secret" not in repr(configured)
    assert configured.OS_PASSWORD is not None
    assert configured.OS_PASSWORD.get_secret_value() == "super-secret"
