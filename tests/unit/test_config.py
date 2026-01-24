"""Tests for configuration module."""

import os
import pytest


def test_settings_defaults():
    """Settings have sensible defaults."""
    from src.core.config import Settings

    # Create fresh settings (don't use global)
    s = Settings()

    assert s.llm_provider == "anthropic"
    assert s.llm_model == "claude-sonnet-4-5-20250929"
    assert s.default_max_turns == 10  # Settings default (not interview_config)
    assert s.default_target_coverage == 0.8
    # Note: debug may be True from .env file


def test_settings_from_env():
    """Settings can be overridden via environment variables."""
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_MAX_TURNS"] = "30"

    try:
        from src.core.config import Settings

        s = Settings()

        assert s.debug
        assert s.default_max_turns == 30
    finally:
        del os.environ["DEBUG"]
        del os.environ["DEFAULT_MAX_TURNS"]


def test_settings_validation():
    """Settings validate constraints."""
    from src.core.config import Settings
    from pydantic import ValidationError

    # Temperature out of range
    with pytest.raises(ValidationError):
        Settings(llm_temperature=3.0)

    # Coverage out of range
    with pytest.raises(ValidationError):
        Settings(default_target_coverage=1.5)


def test_global_settings_available():
    """Global settings instance is importable."""
    from src.core.config import settings

    assert settings is not None
    assert hasattr(settings, "database_path")
