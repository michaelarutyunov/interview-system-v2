"""
Application settings management.

Settings are loaded from environment variables with .env file support.
All configuration is validated using Pydantic.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment.

    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ==========================================================================
    # Paths
    # ==========================================================================

    config_dir: Path = Field(
        default=Path("config"),
        description="Directory containing YAML configuration files"
    )
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory for database and other data files"
    )

    # ==========================================================================
    # Database
    # ==========================================================================

    database_path: Path = Field(
        default=Path("data/interview.db"),
        description="Path to SQLite database file"
    )

    # ==========================================================================
    # LLM Configuration
    # ==========================================================================

    llm_provider: str = Field(
        default="anthropic",
        description="LLM provider to use"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    llm_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="LLM model identifier"
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature"
    )
    llm_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=4096,
        description="Maximum tokens in LLM response"
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Timeout for LLM API calls"
    )

    # ==========================================================================
    # Interview Defaults
    # ==========================================================================

    default_max_turns: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Default maximum turns per interview"
    )
    default_target_coverage: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Default target coverage ratio"
    )

    # ==========================================================================
    # Server Configuration
    # ==========================================================================

    host: str = Field(
        default="127.0.0.1",
        description="Server host address"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )


# Global settings instance
settings = Settings()
