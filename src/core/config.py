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
    #
    # Three-client architecture for task-optimized LLM selection:
    # - extraction: Extract nodes/edges/stance from user responses
    # - scoring: Extract diagnostic signals for strategy scoring
    # - generation: Generate interview questions
    #
    # Defaults are defined in src/llm/client.py. Set environment variables
    # below only to override defaults (e.g., LLM_EXTRACTION_PROVIDER=kimi)

    # Optional provider overrides (defaults defined in client.py)
    llm_extraction_provider: Optional[str] = Field(
        default=None,
        description="Override extraction LLM provider (default: anthropic)",
    )
    llm_scoring_provider: Optional[str] = Field(
        default=None, description="Override scoring LLM provider (default: kimi)"
    )
    llm_generation_provider: Optional[str] = Field(
        default=None,
        description="Override generation LLM provider (default: anthropic)",
    )

    # API Keys (required for providers you use)
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )
    kimi_api_key: Optional[str] = Field(
        default=None, description="Kimi (Moonshot AI) API key"
    )
    deepseek_api_key: Optional[str] = Field(
        default=None, description="DeepSeek API key"
    )
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key (optional, for GPT models)"
    )

    # ==========================================================================
    # Interview Defaults
    # ==========================================================================

    default_max_turns: int = Field(
        default=10, ge=1, le=50, description="Default maximum turns per interview"
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
    min_turns: int = Field(
        default=5, ge=1, le=20, description="Minimum turns before early termination"
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
        if (
            isinstance(phases, PhasesConfig) and v.max_turns == 20
        ):  # Only if using default
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
