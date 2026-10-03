"""Configuration safeguards."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_local_security_defaults():
    with pytest.raises(ValidationError, match="AUTH_REQUIRED"):
        Settings(environment="production")


def test_production_accepts_explicit_secure_settings():
    settings = Settings(
        environment="production",
        auth_required=True,
        jwt_secret="a-unique-jwt-secret-that-is-long-enough",
        admin_password="a-unique-admin-password",
        cors_origins="https://wisdom.example.com",
    )
    assert settings.is_production
