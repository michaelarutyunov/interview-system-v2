"""
Question generation service.

Generates follow-up questions based on:
- Strategy (Phase 2: hardcoded "deepen")
- Recent conversation context
- Current graph state
- Focus concept

Uses LLM for natural language generation.
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
    """
    Service for generating interview questions.

    Generates natural, conversational questions using LLM
    based on strategy and conversation context.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        default_strategy: str = "deepen",
        methodology: str = "means_end_chain",
    ):
        """
        Initialize question service.

        Args:
            llm_client: LLM client instance (required)
            default_strategy: Default strategy for Phase 2 (hardcoded "deepen")
            methodology: Methodology name for opening question generation
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
        """
        Generate a follow-up question.

        Args:
            focus_concept: Concept to focus the question on
            recent_utterances: Recent conversation turns
            graph_state: Current graph state for context
            recent_nodes: Recently added nodes
            strategy: Strategy to use (defaults to default_strategy)
            topic: Research topic to anchor questions to (prevents drift)
            signals: Active signal values (for strategy rationale in prompt)
            signal_descriptions: Signal descriptions (for strategy rationale in prompt)

        Returns:
            Generated question string

        Raises:
            RuntimeError: If LLM call fails
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
        """Load methodology schema for opening question generation.

        Returns:
            MethodologySchema instance

        Raises:
            FileNotFoundError: If methodology schema not found
        """
        return load_methodology(self.methodology)

    async def generate_opening_question(
        self,
        objective: str,
    ) -> str:
        """
        Generate an opening question for a new session.

        Args:
            objective: Interview objective (what we're studying)

        Returns:
            Opening question string

        Raises:
            RuntimeError: If LLM call fails
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
