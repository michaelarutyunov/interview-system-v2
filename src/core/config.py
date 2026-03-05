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
    # Provider and model settings are in config/interview_config.yaml (llm: section).
    # Only API keys remain here as environment variables.

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
    xai_api_key: Optional[str] = Field(
        default=None, description="xAI API key (for Grok models)"
    )

    # ==========================================================================
    # LLM Pricing (per million tokens)
    # ==========================================================================
    # Prices as of 2026-02. Source: provider pricing pages
    # Format: cost per 1M tokens (input and output separate)

    # Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
    anthropic_sonnet_input: float = Field(
        default=3.00,
        description="Claude Sonnet input price per million tokens (USD)",
    )
    anthropic_sonnet_output: float = Field(
        default=15.00,
        description="Claude Sonnet output price per million tokens (USD)",
    )

    # Kimi: https://platform.moonshot.ai/docs/pricing
    kimi_k2_input: float = Field(
        default=0.60,
        description="Kimi K2 input price per million tokens (USD)",
    )
    kimi_k2_output: float = Field(
        default=2.50,
        description="Kimi K2 output price per million tokens (USD)",
    )

    # DeepSeek: https://platform.deepseek.com/api-docs/#/pricelist
    # Note: Not currently used by default in any client type
    deepseek_chat_input: float = Field(
        default=0.14,
        description="DeepSeek Chat input price per million tokens (USD)",
    )
    deepseek_chat_output: float = Field(
        default=0.28,
        description="DeepSeek Chat output price per million tokens (USD)",
    )

    # xAI Grok: https://docs.x.ai/docs/models#models-and-pricing
    # Note: Not currently used by default in any client type
    grok_41_fast_input: float = Field(
        default=0.20,
        description="Grok 4.1 Fast input price per million tokens (USD)",
    )
    grok_41_fast_output: float = Field(
        default=0.50,
        description="Grok 4.1 Fast output price per million tokens (USD)",
    )

    # ==========================================================================
    # Server Configuration
    # ==========================================================================

    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # ==========================================================================
    # Feature Flags
    # ==========================================================================

    enable_srl: bool = Field(
        default=True,
        description="Enable SRL preprocessing stage for linguistic analysis",
    )

    enable_canonical_slots: bool = Field(
        default=True,
        description="Enable canonical slot discovery for deduplication (dual-graph architecture)",
    )

    enable_question_self_selection: bool = Field(
        default=True,
        description="Enable self-selection prompt for question generation (generates 3 candidates, scores internally, outputs best)",
    )


    def get_pricing_for_model(self, model_name: str) -> tuple[float, float]:
        """
        Get input and output pricing for a given model.

        Args:
            model_name: Model identifier (e.g., "claude-sonnet-4-6", "kimi-k2-0905-preview")

        Returns:
            Tuple of (input_price_per_million, output_price_per_million) in USD

        Raises:
            ValueError: If model_name is not recognized
        """
        # Normalize model name to lowercase for case-insensitive matching
        model_lower = model_name.lower()

        if "sonnet" in model_lower or "claude" in model_lower:
            return (self.anthropic_sonnet_input, self.anthropic_sonnet_output)
        elif "kimi" in model_lower or "moonshot" in model_lower or "k2" in model_lower:
            return (self.kimi_k2_input, self.kimi_k2_output)
        elif "deepseek" in model_lower:
            return (self.deepseek_chat_input, self.deepseek_chat_output)
        elif "grok" in model_lower:
            return (self.grok_41_fast_input, self.grok_41_fast_output)
        else:
            raise ValueError(
                f"Unknown model '{model_name}' for pricing lookup. "
                f"Supported models: claude-sonnet-4-6, kimi-k2-0905-preview, deepseek-chat, grok-4.1-fast"
            )


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
    """Configuration settings for interview session boundaries.

    Defines the maximum number of turns before forcing session close
    and the minimum turns required before early termination is allowed.
    """

    max_turns: int = Field(
        default=20, ge=1, le=100, description="Maximum turns before forcing close"
    )


class SessionServiceConfig(BaseModel):
    """Configuration for SessionService context window limits.

    Controls how much historical data (utterances, nodes, context) is
    included when processing turns and generating questions.
    """

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
    """Configuration for all interview phases (exploratory, focused, closing).

    Each phase has its own turn limit and transition rules. Phase transitions
    are determined by turn count in the simplified deterministic model.
    """

    exploratory: PhaseConfig = Field(default_factory=PhaseConfig)
    focused: PhaseConfig = Field(default_factory=PhaseConfig)
    closing: PhaseConfig = Field(default_factory=PhaseConfig)


class DeduplicationConfig(BaseModel):
    """Thresholds for surface and canonical graph deduplication.

    Controls semantic similarity matching during node creation (surface graph)
    and slot discovery (canonical graph). Also controls the promotion lifecycle
    from candidate to active canonical slots.
    """

    surface_similarity_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for surface node semantic dedup",
    )
    canonical_similarity_threshold: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for merging canonical slots",
    )
    canonical_min_support_nodes: int = Field(
        default=2,
        ge=1,
        description="Minimum surface nodes mapped before candidate slot is promoted to active",
    )


class LLMCallConfig(BaseModel):
    """Configuration for a single LLM call type (provider + model + parameters)."""

    provider: str = Field(description="LLM provider: anthropic, kimi, deepseek, grok")
    model: str = Field(description="Model identifier for the provider")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=16384)
    timeout: float = Field(default=30.0, ge=1.0, le=120.0)
    effort: Optional[str] = Field(
        default=None, description="Anthropic extended thinking effort (low/medium/high)"
    )


class LLMConfig(BaseModel):
    """LLM provider and model configuration for each pipeline call type.

    Four independent call types, each configurable for A/B testing:
    - extraction: Stage 3 — concept/relationship extraction
    - slot_scoring: Stage 4.5 — canonical slot discovery
    - signal_scoring: Stage 6 — LLM signal detection (response_depth, engagement, etc.)
    - question_generation: Stage 8 + opening question
    """

    extraction: LLMCallConfig = Field(
        default_factory=lambda: LLMCallConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
            temperature=0.3,
            max_tokens=2048,
            timeout=30.0,
            effort="medium",
        )
    )
    slot_scoring: LLMCallConfig = Field(
        default_factory=lambda: LLMCallConfig(
            provider="kimi",
            model="kimi-k2-0905-preview",
            temperature=0.3,
            max_tokens=512,
            timeout=30.0,
        )
    )
    signal_scoring: LLMCallConfig = Field(
        default_factory=lambda: LLMCallConfig(
            provider="kimi",
            model="kimi-k2-0905-preview",
            temperature=0.3,
            max_tokens=512,
            timeout=30.0,
        )
    )
    question_generation: LLMCallConfig = Field(
        default_factory=lambda: LLMCallConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
            temperature=0.7,
            max_tokens=1024,
            timeout=30.0,
            effort="low",
        )
    )


class InterviewConfig(BaseModel):
    """
    Complete interview configuration loaded from interview_config.yaml.

    This contains all interview-specific parameters that were previously
    hardcoded across multiple services.
    """

    session: SessionConfig = Field(default_factory=SessionConfig)
    phases: PhasesConfig = Field(default_factory=PhasesConfig)
    session_service: SessionServiceConfig = Field(default_factory=SessionServiceConfig)
    deduplication: DeduplicationConfig = Field(default_factory=DeduplicationConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

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

    # Strip None values from YAML (keys with only comments parse as None)
    cleaned = {k: v for k, v in config_data.items() if v is not None}
    return InterviewConfig(**cleaned)


# Global settings instance
settings = Settings()

# Global interview config instance
interview_config = load_interview_config()
