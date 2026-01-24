"""Synthetic respondent service for testing.

Generates contextually appropriate respondent answers using:
- Persona system with 5 predefined personas
- Natural response patterns (detailed, medium, brief, deflections)
- Interview context awareness (previous concepts, turn number, coverage)
- Deflection patterns for authentic respondent behavior
"""

import random
from typing import Dict, Any, List, Optional

from src.llm.client import LLMClient, get_llm_client
from src.llm.prompts.synthetic import (
    get_available_personas,
    get_synthetic_system_prompt,
    get_synthetic_system_prompt_with_deflection,
    get_synthetic_user_prompt,
    parse_synthetic_response,
    PERSONAS,
)


class SyntheticService:
    """Service for generating synthetic respondent responses.

    Orchestrates LLM calls with persona prompts to generate
    realistic responses for testing the interview system.
    """

    DEFAULT_PERSONA = "health_conscious"
    DEFLECTION_CHANCE = 0.2

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        deflection_chance: float = 0.2,
    ):
        """Initialize synthetic service.

        Args:
            llm_client: LLM client for generating responses (creates default if None)
            deflection_chance: Probability of using deflection prompts (0.0-1.0)
        """
        if llm_client is None:
            llm_client = get_llm_client()
        self.llm_client = llm_client
        self.deflection_chance = deflection_chance

    async def generate_response(
        self,
        question: str,
        session_id: str,
        persona: str = DEFAULT_PERSONA,
        graph_state: Optional[Any] = None,
        interview_context: Optional[Dict[str, Any]] = None,
        use_deflection: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Generate a synthetic response to an interview question.

        Args:
            question: The interviewer's question
            session_id: Session identifier
            persona: Persona ID (must be in get_available_personas())
            graph_state: Optional graph state with recent_nodes attribute
            interview_context: Optional dict with product_name, turn_number, coverage_achieved
            use_deflection: Override deflection behavior (None = use chance)

        Returns:
            Dict with keys: response, persona, persona_name, question, latency_ms,
                          tokens_used, used_deflection

        Raises:
            ValueError: If persona is not in get_available_personas()
        """
        # Validate persona
        available_personas = get_available_personas()
        if persona not in available_personas:
            raise ValueError(
                f"Unknown persona: {persona}. "
                f"Available: {', '.join(available_personas.keys())}"
            )

        # Extract previous concepts from graph state
        previous_concepts = self._extract_previous_concepts(graph_state)

        # Determine whether to use deflection
        if use_deflection is None:
            use_deflection = random.random() < self.deflection_chance

        # Build prompts
        system_prompt = (
            get_synthetic_system_prompt_with_deflection()
            if use_deflection
            else get_synthetic_system_prompt()
        )
        user_prompt = get_synthetic_user_prompt(
            question=question,
            persona=persona,
            previous_concepts=previous_concepts,
            interview_context=interview_context,
        )

        # Call LLM
        llm_response = await self.llm_client.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.8,
            max_tokens=256,
        )

        # Parse response
        response = parse_synthetic_response(llm_response.content)

        return {
            "response": response,
            "persona": persona,
            "persona_name": PERSONAS[persona]["name"],
            "question": question,
            "latency_ms": llm_response.latency_ms,
            "tokens_used": llm_response.usage,
            "used_deflection": use_deflection,
        }

    async def generate_multi_response(
        self,
        question: str,
        session_id: str,
        personas: Optional[List[str]] = None,
        graph_state: Optional[Any] = None,
        interview_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate responses for multiple personas.

        Args:
            question: The interviewer's question
            session_id: Session identifier
            personas: List of persona IDs (None = all available)
            graph_state: Optional graph state
            interview_context: Optional interview context

        Returns:
            List of response dicts from generate_response()
        """
        if personas is None:
            personas = list(get_available_personas().keys())

        responses = []
        for persona in personas:
            response = await self.generate_response(
                question=question,
                session_id=session_id,
                persona=persona,
                graph_state=graph_state,
                interview_context=interview_context,
            )
            responses.append(response)

        return responses

    async def generate_interview_sequence(
        self,
        session_id: str,
        questions: List[str],
        persona: str = DEFAULT_PERSONA,
        product_name: str = "this product",
    ) -> List[Dict[str, Any]]:
        """Generate responses for a complete interview sequence.

        Args:
            session_id: Session identifier
            questions: List of interview questions
            persona: Persona ID
            product_name: Product name for context

        Returns:
            List of response dicts with interview_context for each turn
        """
        responses = []
        for turn_number, question in enumerate(questions, start=1):
            # Build interview context
            interview_context = {
                "product_name": product_name,
                "turn_number": turn_number,
                "coverage_achieved": 0.0,  # Placeholder
            }

            response = await self.generate_response(
                question=question,
                session_id=session_id,
                persona=persona,
                interview_context=interview_context,
            )
            responses.append(response)

        return responses

    def _extract_previous_concepts(self, graph_state: Optional[Any]) -> List[str]:
        """Extract concept labels from graph state.

        Args:
            graph_state: Graph state object with recent_nodes attribute

        Returns:
            List of concept labels (last 10)
        """
        if graph_state is None:
            return []

        # Handle both dict and object access
        recent_nodes = getattr(graph_state, "recent_nodes", None)
        if recent_nodes is None:
            return []

        # Extract labels from nodes
        concepts = [node.label for node in recent_nodes]

        # Return last 10 concepts
        return concepts[-10:]


def get_synthetic_service(
    llm_client: Optional[LLMClient] = None,
) -> SyntheticService:
    """Factory for synthetic service.

    Args:
        llm_client: Optional LLM client (creates default if None)

    Returns:
        SyntheticService instance
    """
    if llm_client is None:
        llm_client = get_llm_client()

    return SyntheticService(llm_client=llm_client)
