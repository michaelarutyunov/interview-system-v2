"""Question generation service for semi-structured interviews.

Generates natural, conversational follow-up questions using LLM based on:
- Selected strategy from methodology config (deepen, explore, clarify, etc.)
- Recent conversation context and utterances
- Current graph state (depth, node counts, recent concepts)
- Focus concept or node

Supports two question types:
- Follow-up questions: Strategy-driven questions during active interview
- Opening questions: Initial questions to start a new session

Uses methodology configs for strategy descriptions and topic anchoring.
"""

from typing import Optional, List, Dict, Any

import structlog

from src.llm.client import LLMClient
from src.llm.prompts.question import (
    get_question_system_prompt,
    get_question_user_prompt,
    get_opening_question_system_prompt,
    get_opening_question_user_prompt,
    get_graph_summary,
    format_question,
)
from src.domain.models.knowledge_graph import KGNode, GraphState
from src.core.schema_loader import load_methodology
from src.domain.models.methodology_schema import MethodologySchema

log = structlog.get_logger(__name__)


class QuestionService:
    """Service for generating interview questions using LLM.

    Generates natural, conversational questions based on:
    - Selected questioning strategy (deepen, explore, clarify, reflect, revitalize)
    - Current conversation context and recent utterances
    - Graph state (depth, node counts, recent concepts)
    - Focus concept or node ID
    - Active signals and signal descriptions (for strategy rationale)

    Supports follow-up question generation (during active interview)
    and opening question generation (for new sessions).
    """

    def __init__(
        self,
        llm_client: LLMClient,
        default_strategy: str = "deepen",
        methodology: str = "means_end_chain",
    ):
        """Initialize question service with LLM client and methodology configuration.

        Args:
            llm_client: LLM client instance for question generation (required)
            default_strategy: Default strategy name when not specified (e.g., "deepen")
            methodology: Methodology name for opening question generation
                (loaded from config/methodologies/*.yaml)
        """
        self.llm = llm_client
        self.default_strategy = default_strategy
        self.methodology = methodology

        log.info(
            "question_service_initialized",
            default_strategy=default_strategy,
            methodology=methodology,
        )

    async def generate_question(
        self,
        focus_concept: str,
        recent_utterances: Optional[List[Dict[str, str]]] = None,
        graph_state: Optional[GraphState] = None,
        recent_nodes: Optional[List[KGNode]] = None,
        strategy: Optional[str] = None,
        topic: Optional[str] = None,
        signals: Optional[Dict[str, Any]] = None,
        signal_descriptions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate follow-up question based on strategy, context, and graph state.

        Uses LLM to generate a natural, conversational question that:
        - Follows the selected questioning strategy (deepen, explore, clarify, etc.)
        - Anchors to the research topic to prevent drift
        - Incorporates signal rationale explaining why strategy was selected
        - References recent conversation context and graph state

        Args:
            focus_concept: Concept or node to focus the question on
            recent_utterances: Recent conversation turns with speaker/text keys
            graph_state: Current graph state for depth and coverage context
            recent_nodes: Recently added nodes (up to 3 shown in summary)
            strategy: Strategy name from methodology config (defaults to default_strategy)
            topic: Research topic to anchor questions to (prevents drift to abstract philosophy)
            signals: Active signal values for strategy rationale (signal_name -> value)
            signal_descriptions: Signal descriptions for rationale (signal_name -> description)

        Returns:
            Generated question string (cleaned, quoted, with appropriate punctuation)

        Raises:
            RuntimeError: If LLM call fails or returns invalid response
        """
        strategy = strategy or self.default_strategy

        log.info(
            "generating_question",
            focus=focus_concept,
            strategy=strategy,
            topic=topic,
        )

        # Build graph summary if we have state
        graph_summary = None
        depth_achieved = 0
        if graph_state and recent_nodes:
            recent_concepts = [n.label for n in recent_nodes[:3]]
            depth_achieved = graph_state.depth_metrics.max_depth
            graph_summary = get_graph_summary(
                nodes_by_type=graph_state.nodes_by_type,
                recent_concepts=recent_concepts,
                depth_achieved=depth_achieved,
            )

        # Load methodology schema for prompt
        methodology_schema: Optional[MethodologySchema] = None
        try:
            methodology_schema = self.load_methodology_schema()
        except Exception:
            pass  # Methodology is optional for follow-up prompts

        # Get prompts - include topic anchoring and methodology
        system_prompt = get_question_system_prompt(
            strategy, topic=topic, methodology=methodology_schema
        )
        user_prompt = get_question_user_prompt(
            focus_concept=focus_concept,
            recent_utterances=recent_utterances,
            graph_summary=graph_summary,
            strategy=strategy,
            topic=topic,
            depth_achieved=depth_achieved,
            signals=signals,
            signal_descriptions=signal_descriptions,
        )

        try:
            response = await self.llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.8,  # Higher for variety
                max_tokens=200,
            )

            question = format_question(response.content)

            log.info(
                "question_generated",
                strategy=strategy,
                question_length=len(question),
                latency_ms=response.latency_ms,
            )

            return question

        except Exception as e:
            log.error("question_generation_failed", error=str(e))
            raise RuntimeError(f"Question generation failed: {e}")

    def load_methodology_schema(self):
        """Load methodology schema from YAML config for opening question generation.

        Returns:
            MethodologySchema with method metadata (name, goal, description, opening_bias)

        Raises:
            FileNotFoundError: If methodology YAML file not found in config/methodologies/
        """
        return load_methodology(self.methodology)

    async def generate_opening_question(
        self,
        objective: str,
    ) -> str:
        """Generate opening question for a new interview session.

        Creates an inviting, open-ended question to begin the interview
        based on the research objective and methodology configuration.
        Uses methodology-specific opening_bias to guide question style.

        Args:
            objective: Interview objective describing what we're studying

        Returns:
            Opening question string (cleaned, with appropriate punctuation)

        Raises:
            RuntimeError: If LLM call fails or methodology schema not found
        """
        log.info("generating_opening_question", objective=objective[:100])

        # Load methodology schema
        methodology_schema = self.load_methodology_schema()

        system_prompt = get_opening_question_system_prompt(
            methodology=methodology_schema
        )
        user_prompt = get_opening_question_user_prompt(
            objective=objective,
            methodology=methodology_schema,
        )

        try:
            response = await self.llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.9,  # Even higher for variety
                max_tokens=150,
            )

            question = format_question(response.content)

            log.info(
                "opening_question_generated",
                objective=objective[:100],
                question_length=len(question),
            )

            return question

        except Exception as e:
            log.error("opening_question_failed", error=str(e))
            raise RuntimeError(f"Opening question generation failed: {e}")
