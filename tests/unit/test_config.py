"""Tests for configuration module."""

import os
import pytest


def test_settings_defaults():
    """Settings have sensible defaults."""
    from src.core.config import Settings

    # Create fresh settings (don't use global)
    s = Settings()

    # Settings class no longer has llm_provider, llm_model, llm_temperature
    # These are now in LLM client defaults
    assert s.default_max_turns == 10  # Settings default (not interview_config)
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

    # Max turns out of range
    with pytest.raises(ValidationError):
        Settings(default_max_turns=100)


def test_global_settings_available():
    """Global settings instance is importable."""
    from src.core.config import settings

    assert settings is not None
    assert hasattr(settings, "database_path")
