"""Tests for configuration module."""

import os
import pytest
from pathlib import Path


def test_settings_defaults():
    """Settings have sensible defaults."""
    from src.core.config import Settings

    # Create fresh settings (don't use global)
    s = Settings()

    assert s.llm_provider == "anthropic"
    assert s.llm_model == "claude-sonnet-4-20250514"
    assert s.default_max_turns == 20
    assert s.default_target_coverage == 0.8
    assert s.debug == False


def test_settings_from_env():
    """Settings can be overridden via environment variables."""
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_MAX_TURNS"] = "30"

    try:
        from src.core.config import Settings
        s = Settings()

        assert s.debug == True
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
