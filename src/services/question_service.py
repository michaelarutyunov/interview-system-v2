"""
Question generation service.

Generates follow-up questions based on:
- Strategy (Phase 2: hardcoded "deepen")
- Recent conversation context
- Current graph state
- Focus concept

Uses LLM for natural language generation.
"""

from typing import Optional, List, Dict

import structlog

from src.llm.client import LLMClient, get_generation_llm_client
from src.llm.prompts.question import (
    get_question_system_prompt,
    get_question_user_prompt,
    get_opening_question_system_prompt,
    get_opening_question_user_prompt,
    get_graph_summary,
    format_question,
)
from src.domain.models.knowledge_graph import KGNode, GraphState

log = structlog.get_logger(__name__)


class QuestionService:
    """
    Service for generating interview questions.

    Generates natural, conversational questions using LLM
    based on strategy and conversation context.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        default_strategy: str = "deepen",
    ):
        """
        Initialize question service.

        Args:
            llm_client: LLM client instance (creates default if None)
            default_strategy: Default strategy for Phase 2 (hardcoded "deepen")
        """
        self.llm = llm_client or get_generation_llm_client()
        self.default_strategy = default_strategy

        log.info("question_service_initialized", default_strategy=default_strategy)

    async def generate_question(
        self,
        focus_concept: str,
        recent_utterances: Optional[List[Dict[str, str]]] = None,
        graph_state: Optional[GraphState] = None,
        recent_nodes: Optional[List[KGNode]] = None,
        strategy: Optional[str] = None,
    ) -> str:
        """
        Generate a follow-up question.

        Args:
            focus_concept: Concept to focus the question on
            recent_utterances: Recent conversation turns
            graph_state: Current graph state for context
            recent_nodes: Recently added nodes
            strategy: Strategy to use (defaults to default_strategy)

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
        )

        # Build graph summary if we have state
        graph_summary = None
        if graph_state and recent_nodes:
            recent_concepts = [n.label for n in recent_nodes[:3]]
            graph_summary = get_graph_summary(
                nodes_by_type=graph_state.nodes_by_type,
                recent_concepts=recent_concepts,
                depth_achieved=graph_state.max_depth,
            )

        # Get prompts
        system_prompt = get_question_system_prompt(strategy)
        user_prompt = get_question_user_prompt(
            focus_concept=focus_concept,
            recent_utterances=recent_utterances,
            graph_summary=graph_summary,
            strategy=strategy,
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

    async def generate_opening_question(
        self,
        concept_name: str,
        concept_description: str = "",
    ) -> str:
        """
        Generate an opening question for a new session.

        Args:
            concept_name: Name of the concept/product
            concept_description: Optional description

        Returns:
            Opening question string

        Raises:
            RuntimeError: If LLM call fails
        """
        log.info("generating_opening_question", concept=concept_name)

        system_prompt = get_opening_question_system_prompt()
        user_prompt = get_opening_question_user_prompt(
            concept_name=concept_name,
            description=concept_description,
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
                concept=concept_name,
                question_length=len(question),
            )

            return question

        except Exception as e:
            log.error("opening_question_failed", error=str(e))
            raise RuntimeError(f"Opening question generation failed: {e}")

    def select_focus_concept(
        self,
        recent_nodes: List[KGNode],
        graph_state: GraphState,
        strategy: Optional[str] = None,
    ) -> str:
        """
        Select which concept to focus the next question on.

        Phase 2: Simple heuristics
        Phase 3: Full strategy-based selection

        Args:
            recent_nodes: Recently added nodes
            graph_state: Current graph state
            strategy: Strategy (affects selection)

        Returns:
            Concept label to focus on
        """
        strategy = strategy or self.default_strategy

        if not recent_nodes:
            return "the topic"  # Fallback

        if strategy == "deepen":
            # Focus on most recent concept to ladder up
            return recent_nodes[0].label

        elif strategy == "broaden":
            # Focus on a recent concept but ask for alternatives
            return recent_nodes[0].label

        elif strategy == "cover":
            # Would look at uncovered elements (Phase 3)
            return recent_nodes[0].label

        elif strategy == "close":
            # Summarize what we've learned
            return "what we've discussed"

        # Default: most recent
        return recent_nodes[0].label

    async def generate_fallback_question(self, focus_concept: str) -> str:
        """
        Generate a simple fallback question without LLM.

        Used when LLM is unavailable.

        Args:
            focus_concept: Concept to ask about

        Returns:
            Simple fallback question
        """
        log.warning("using_fallback_question", focus=focus_concept)

        # Simple laddering fallback
        return f"Why is {focus_concept} important to you?"
