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

    # Main LLM (for question generation)
    llm_main_provider: str = Field(
        default="anthropic",
        description="LLM provider for question generation"
    )
    llm_main_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Main LLM model identifier (question generation)"
    )
    llm_main_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Main LLM sampling temperature"
    )
    llm_main_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=8192,
        description="Maximum tokens in main LLM response"
    )
    llm_main_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Timeout for main LLM API calls"
    )

    # Light LLM (for scoring tasks)
    llm_light_provider: str = Field(
        default="anthropic",
        description="LLM provider for scoring tasks"
    )
    llm_light_model: str = Field(
        default="claude-haiku-4-20250514",
        description="Light LLM model identifier (scoring tasks)"
    )
    llm_light_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Light LLM sampling temperature (lower for consistency)"
    )
    llm_light_max_tokens: int = Field(
        default=512,
        ge=1,
        le=4096,
        description="Maximum tokens in light LLM response"
    )
    llm_light_timeout_seconds: float = Field(
        default=15.0,
        ge=1.0,
        description="Timeout for light LLM API calls"
    )

    # API Keys (can be shared or separate)
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key (used for both main and light)"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (optional, for GPT models)"
    )

    # Legacy configuration (for backward compatibility)
    llm_provider: str = Field(
        default="anthropic",
        description="Legacy LLM provider (defaults to llm_main_provider)"
    )
    llm_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Legacy LLM model (defaults to llm_main_model)"
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Legacy LLM temperature (defaults to llm_main_temperature)"
    )
    llm_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=4096,
        description="Legacy max tokens (defaults to llm_main_max_tokens)"
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Legacy timeout (defaults to llm_main_timeout_seconds)"
    )

    # ==========================================================================
    # Interview Defaults
    # ==========================================================================

    default_max_turns: int = Field(
        default=10,
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
