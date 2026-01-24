"""
Application settings management.

Settings are loaded from environment variables with .env file support.
All configuration is validated using Pydantic.
"""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment.

    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ==========================================================================
    # Paths
    # ==========================================================================

    config_dir: Path = Field(
        default=Path("config"),
        description="Directory containing YAML configuration files",
    )
    data_dir: Path = Field(
        default=Path("data"), description="Directory for database and other data files"
    )

    # ==========================================================================
    # Database
    # ==========================================================================

    database_path: Path = Field(
        default=Path("data/interview.db"), description="Path to SQLite database file"
    )

    # ==========================================================================
    # LLM Configuration
    # ==========================================================================

    # Main LLM (for question generation)
    llm_main_provider: str = Field(
        default="anthropic", description="LLM provider for question generation"
    )
    llm_main_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Main LLM model identifier (question generation)",
    )
    llm_main_temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Main LLM sampling temperature"
    )
    llm_main_max_tokens: int = Field(
        default=1024, ge=1, le=8192, description="Maximum tokens in main LLM response"
    )
    llm_main_timeout_seconds: float = Field(
        default=30.0, ge=1.0, description="Timeout for main LLM API calls"
    )

    # Light LLM (for scoring tasks)
    llm_light_provider: str = Field(
        default="anthropic", description="LLM provider for scoring tasks"
    )
    llm_light_model: str = Field(
        default="claude-haiku-4-20250514",
        description="Light LLM model identifier (scoring tasks)",
    )
    llm_light_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Light LLM sampling temperature (lower for consistency)",
    )
    llm_light_max_tokens: int = Field(
        default=512, ge=1, le=4096, description="Maximum tokens in light LLM response"
    )
    llm_light_timeout_seconds: float = Field(
        default=15.0, ge=1.0, description="Timeout for light LLM API calls"
    )

    # API Keys (can be shared or separate)
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key (used for both main and light)"
    )
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key (optional, for GPT models)"
    )

    # Legacy configuration (for backward compatibility)
    llm_provider: str = Field(
        default="anthropic",
        description="Legacy LLM provider (defaults to llm_main_provider)",
    )
    llm_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Legacy LLM model (defaults to llm_main_model)",
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Legacy LLM temperature (defaults to llm_main_temperature)",
    )
    llm_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=4096,
        description="Legacy max tokens (defaults to llm_main_max_tokens)",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Legacy timeout (defaults to llm_main_timeout_seconds)",
    )

    # ==========================================================================
    # Interview Defaults
    # ==========================================================================

    default_max_turns: int = Field(
        default=10, ge=1, le=50, description="Default maximum turns per interview"
    )
    default_target_coverage: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Default target coverage ratio"
    )

    # ==========================================================================
    # Server Configuration
    # ==========================================================================

    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")


# ============================================================================
# Interview Configuration (from YAML)
# ============================================================================


class PhaseConfig(BaseModel):
    """Configuration for a single interview phase.

    Simplified deterministic model: each phase has a fixed number of turns.
    Phase transitions are based solely on turn count.
    """

    n_turns: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of turns for this phase (null = indefinite)",
    )


class SessionConfig(BaseModel):
    """Interview session configuration."""

    max_turns: int = Field(
        default=20, ge=1, le=100, description="Maximum turns before forcing close"
    )
    target_coverage: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Target coverage ratio"
    )
    min_turns: int = Field(
        default=5, ge=1, le=20, description="Minimum turns before early termination"
    )


class StrategyServiceConfig(BaseModel):
    """Strategy service configuration."""

    alternatives_count: int = Field(
        default=3, ge=1, le=10, description="Number of alternative strategies to track"
    )
    alternatives_min_score: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum score for alternatives"
    )


class SessionServiceConfig(BaseModel):
    """Session service configuration."""

    context_utterance_limit: int = Field(
        default=10, ge=1, le=50, description="Number of recent utterances in context"
    )
    context_node_limit: int = Field(
        default=5, ge=1, le=20, description="Number of recent nodes in context"
    )
    extraction_context_limit: int = Field(
        default=5, ge=1, le=20, description="Recent utterances for extraction context"
    )


class PhasesConfig(BaseModel):
    """All phase configurations."""

    exploratory: PhaseConfig = Field(default_factory=PhaseConfig)
    focused: PhaseConfig = Field(default_factory=PhaseConfig)
    closing: PhaseConfig = Field(default_factory=PhaseConfig)


class InterviewConfig(BaseModel):
    """
    Complete interview configuration loaded from interview_config.yaml.

    This contains all interview-specific parameters that were previously
    hardcoded across multiple services.
    """

    session: SessionConfig = Field(default_factory=SessionConfig)
    phases: PhasesConfig = Field(default_factory=PhasesConfig)
    strategy_service: StrategyServiceConfig = Field(
        default_factory=StrategyServiceConfig
    )
    session_service: SessionServiceConfig = Field(default_factory=SessionServiceConfig)

    @field_validator("session")
    @classmethod
    def sync_max_turns_with_phases(
        cls, v: SessionConfig, info: ValidationInfo
    ) -> SessionConfig:
        """
        Calculate max_turns from phase n_turns if using default.

        If max_turns is the default value (20), calculate it as the sum of
        all phase n_turns. This ensures phase configuration changes are
        automatically reflected in max_turns.

        Note: UI/API can still override via request.config={"max_turns": custom}
        """
        phases = info.data.get("phases")
        if isinstance(phases, PhasesConfig) and v.max_turns == 20:  # Only if using default
            phase_sum = 0
            for phase in [phases.exploratory, phases.focused, phases.closing]:
                if phase and phase.n_turns:
                    phase_sum += phase.n_turns
            if phase_sum > 0:
                v.max_turns = phase_sum
        return v


def load_interview_config(config_path: Optional[Path] = None) -> InterviewConfig:
    """
    Load interview configuration from YAML file.

    Args:
        config_path: Path to interview_config.yaml. If None, uses default path.

    Returns:
        InterviewConfig with validated settings

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config validation fails
    """
    if config_path is None:
        # Default path: config/interview_config.yaml relative to project root
        try:
            current = Path(__file__).resolve().parent.parent.parent

            # Look for config/interview_config.yaml
            check_path = current / "config" / "interview_config.yaml"
            if check_path.exists():
                config_path = check_path
            else:
                # Fallback to current working directory
                cwd_config = Path.cwd() / "config" / "interview_config.yaml"
                if cwd_config.exists():
                    config_path = cwd_config
                else:
                    # Use default config if file not found
                    return InterviewConfig()
        except Exception:
            # Use default config on any error
            return InterviewConfig()

    config_path = Path(config_path).resolve()

    if not config_path.exists():
        # Return default config if file not found
        return InterviewConfig()

    with open(str(config_path)) as f:
        config_data = yaml.safe_load(f)

    if not config_data:
        return InterviewConfig()

    return InterviewConfig(**config_data)


# Global settings instance
settings = Settings()

# Global interview config instance
interview_config = load_interview_config()
