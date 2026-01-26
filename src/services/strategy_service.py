"""Strategy selector service.

Orchestrates multi-dimensional strategy selection using the two-tier scoring system.

Two-tier approach:
- Tier 1: Hard constraints (boolean vetoes)
- Tier 2: Weighted additive scoring for ranking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import structlog

from src.core.config import interview_config
from src.core.concept_loader import load_concept
from src.domain.models.knowledge_graph import GraphState
from src.domain.models.turn import Focus
from src.domain.models.extraction import ExtractionResult
from src.services.scoring.two_tier import TwoTierScoringEngine, ScoringResult
from src.services.scoring.llm_signals import QualitativeSignalExtractor


logger = structlog.get_logger(__name__)


@dataclass
class StrategyCandidate:
    """A scored (strategy, focus) combination."""

    strategy: Dict[str, Any]
    focus: Union[Focus, Dict[str, Any]]  # Accept both for backward compatibility
    score: float
    scoring_result: Optional[ScoringResult] = None  # Full two-tier result

    def get_focus_dict(self) -> Dict[str, Any]:
        """Get focus as dict for backward compatibility."""
        if isinstance(self.focus, Focus):
            return self.focus.to_dict()
        return self.focus

    def get_focus_typed(self) -> Optional[Focus]:
        """Get focus as typed Focus model."""
        if isinstance(self.focus, Focus):
            return self.focus
        return Focus.from_dict(self.focus)


@dataclass
class SelectionResult:
    """Result of strategy selection."""

    selected_strategy: Dict[str, Any]
    selected_focus: Union[Focus, Dict[str, Any]]  # Accept both for compatibility
    final_score: float
    scoring_result: Optional[ScoringResult] = None  # Full two-tier result
    alternative_strategies: List[StrategyCandidate] = field(default_factory=list)
    selection_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def get_selected_focus_dict(self) -> Dict[str, Any]:
        """Get selected focus as dict for backward compatibility."""
        if isinstance(self.selected_focus, Focus):
            return self.selected_focus.to_dict()
        return self.selected_focus


# Strategy definitions (two-tier system)
STRATEGIES = [
    {
        "id": "deepen",
        "name": "Deepen Understanding",
        "type_category": "depth",
        "priority_base": 1.0,
        "enabled": True,
    },
    {
        "id": "broaden",
        "name": "Explore Breadth",
        "type_category": "breadth",
        "priority_base": 0.9,
        "enabled": True,
    },
    {
        "id": "cover_element",
        "name": "Cover Stimulus Element",
        "type_category": "coverage",
        "priority_base": 1.1,
        "enabled": True,
    },
    {
        "id": "closing",
        "name": "Closing Interview",
        "type_category": "closing",
        "priority_base": 0.5,  # Lower base - only use when appropriate
        "enabled": True,
        # Phase system controls timing via phase multipliers (no min_turns needed)
    },
    {
        "id": "reflection",
        "name": "Reflection / Meta-Question",
        "type_category": "reflection",
        "priority_base": 0.7,  # Emergency fallback
        "enabled": True,
        "emergency_only": True,  # Only when all else fails
    },
]


class StrategyService:
    """
    Orchestrates strategy selection using two-tier hybrid scoring.

    Features:
    - Applicability filtering based on state conditions
    - Dynamic focus generation per strategy type
    - Fallback logic when no strategies applicable
    - Top alternatives for transparency
    """

    def __init__(
        self,
        scoring_engine: TwoTierScoringEngine,
        config: Optional[Dict[str, Any]] = None,
        signal_extractor: Optional[QualitativeSignalExtractor] = None,
    ):
        """
        Initialize strategy selector.

        Args:
            scoring_engine: Configured TwoTierScoringEngine with all scorers
            config: Selector configuration (deprecated - use interview_config.yaml)
            signal_extractor: Optional qualitative signal extractor for enhanced scoring
        """
        self.scoring_engine = scoring_engine
        self.config: Dict[str, Any] = config or {}
        self.signal_extractor = signal_extractor

        # Load strategies from scoring.yaml config (bead ztd)
        # Strategies are now defined in config/scoring.yaml instead of hardcoded
        config_strategies = scoring_engine.config.get("strategies", [])
        if config_strategies:
            self.strategies = {
                s["id"]: s for s in config_strategies if s.get("enabled", True)
            }
        else:
            # Fallback to hardcoded STRATEGIES if config doesn't have strategies
            # This maintains backward compatibility
            logger.warning(
                "No strategies found in scoring config, using hardcoded STRATEGIES fallback"
            )
            self.strategies = {s["id"]: s for s in STRATEGIES if s.get("enabled", True)}

        # Load from centralized interview config (Phase 4: ADR-008)
        self._alternatives_count = interview_config.strategy_service.alternatives_count
        self._alternatives_min_score = (
            interview_config.strategy_service.alternatives_min_score
        )

        # Phase configuration from centralized config (deterministic n_turns model)
        self._exploratory_n_turns = interview_config.phases.exploratory.n_turns or 8
        self._focused_n_turns = interview_config.phases.focused.n_turns or 12
        self._closing_n_turns = interview_config.phases.closing.n_turns or 2
        # Calculate phase boundaries
        self._exploratory_end = self._exploratory_n_turns
        self._focused_end = self._exploratory_end + self._focused_n_turns

        # Allow override via config parameter for backward compatibility
        if config:
            self._alternatives_count = config.get(
                "alternatives_count", self._alternatives_count
            )
            self._alternatives_min_score = config.get(
                "alternatives_min_score", self._alternatives_min_score
            )
            self._exploratory_n_turns = config.get(
                "exploratory_min_turns", self._exploratory_n_turns
            )
            self._focused_n_turns = config.get("focused_n_turns", self._focused_n_turns)
            self._closing_n_turns = config.get("closing_n_turns", self._closing_n_turns)
            # Recalculate boundaries if overridden
            self._exploratory_end = self._exploratory_n_turns
            self._focused_end = self._exploratory_end + self._focused_n_turns

        logger.info(
            "StrategyService initialized (two-tier)",
            num_strategies=len(self.strategies),
            strategy_ids=list(self.strategies.keys()),
        )

    async def select(
        self,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        mode: str = "coverage_driven",  # NEW: Interview mode
        current_user_input: Optional[str] = None,
        current_extraction: Optional[ExtractionResult] = None,
    ) -> SelectionResult:
        """
        Select the best strategy for the current state.

        Algorithm:
        1. Determine interview phase
        2. Filter applicable strategies
        3. Generate focuses for each applicable strategy
        4. Score all (strategy, focus) pairs using two-tier engine
        5. Select highest-scoring non-vetoed combination
        6. Return result with top alternatives

        Args:
            graph_state: Current graph state
            recent_nodes: List of recent nodes from last N turns
            conversation_history: Recent conversation turns (for Tier 1 scorers)
            mode: Interview mode (coverage_driven or graph_driven) - NEW
            current_user_input: Current turn's user input (for qual signals)
            current_extraction: Current turn's extraction result (for qual signals)

        Returns:
            SelectionResult with selected strategy, focus, and alternatives
        """
        logger.debug(
            "Starting strategy selection (two-tier)",
            turn_count=graph_state.properties.get("turn_count", 0),
            mode=mode,
        )

        conversation_history = conversation_history or []

        # Store mode in graph_state properties for scorers to access
        graph_state.properties["interview_mode"] = mode

        # Determine phase before scoring
        phase = self._determine_phase(graph_state)
        graph_state.set_phase(phase)

        logger.debug(
            "Phase determined",
            phase=phase,
            turn_count=graph_state.properties.get("turn_count", 0),
        )

        # Extract qualitative signals (with current turn context)
        if self.signal_extractor:
            # Build enhanced conversation history including current turn
            enhanced_history = list(conversation_history)

            if current_user_input:
                current_turn_entry = {
                    "speaker": "user",
                    "text": current_user_input,
                }

                # Add extraction metadata if available
                if current_extraction:
                    current_turn_entry["extraction"] = {  # type: ignore[assignment]
                        "concepts": [
                            c.model_dump() for c in current_extraction.concepts
                        ],
                        "relationships": [
                            r.model_dump() for r in current_extraction.relationships
                        ],
                        "is_extractable": current_extraction.is_extractable,
                        "avg_confidence": (
                            sum(c.confidence for c in current_extraction.concepts)
                            / len(current_extraction.concepts)
                            if current_extraction.concepts
                            else 0.0
                        ),
                    }

                enhanced_history.append(current_turn_entry)

            # Extract signals
            try:
                signals = await self.signal_extractor.extract(
                    conversation_history=enhanced_history,
                    turn_number=graph_state.properties.get("turn_count", 1),
                )
                # Store in graph_state for scorers to access
                graph_state.properties["qualitative_signals"] = signals.to_dict()

                logger.info(
                    "qualitative_signals_extracted",
                    turn_number=graph_state.properties.get("turn_count", 1),
                    signals_count=sum(
                        1
                        for s in [
                            signals.uncertainty,
                            signals.reasoning,
                            signals.emotional,
                            signals.contradiction,
                            signals.knowledge_ceiling,
                            signals.concept_depth,
                        ]
                        if s is not None
                    ),
                )
            except Exception as e:
                logger.warning(
                    "qualitative_signal_extraction_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continue without signals (graceful degradation)

        # Compute and update saturation tracking properties
        # These are used by SaturationScorer to detect topic exhaustion
        if current_extraction:
            # Calculate new_info_rate: proportion of NEW concepts this turn
            # A "new" concept is one not seen before (first mention)
            total_concepts = len(current_extraction.concepts)
            if total_concepts > 0:
                # Count how many concepts are new (not in recent nodes)
                new_concept_count = 0
                recent_node_labels = {
                    n.get("label", "").lower() for n in recent_nodes if n.get("label")
                }

                for concept in current_extraction.concepts:
                    if concept.text.lower() not in recent_node_labels:
                        new_concept_count += 1

                new_info_rate = new_concept_count / total_concepts
            else:
                new_info_rate = 1.0  # No concepts = high opportunity for new info

            # Track consecutive low-info turns
            # Low info = fewer than 20% new concepts
            low_info_threshold = 0.2
            previous_consecutive = graph_state.properties.get(
                "consecutive_low_info_turns", 0
            )

            if new_info_rate < low_info_threshold:
                consecutive_low_info = previous_consecutive + 1
            else:
                consecutive_low_info = 0  # Reset on good turn

            graph_state.properties["new_info_rate"] = new_info_rate
            graph_state.properties["consecutive_low_info_turns"] = consecutive_low_info

            logger.debug(
                "saturation_metrics_computed",
                new_info_rate=f"{new_info_rate:.2f}",
                consecutive_low_info=consecutive_low_info,
                total_concepts=total_concepts,
            )

        # Score all (strategy, focus) combinations
        candidates: List[StrategyCandidate] = []

        for strategy in self.strategies.values():
            # Generate possible focuses (pass recent_nodes to avoid graph_state.properties dependency)
            focuses = self._get_possible_focuses(strategy, graph_state, recent_nodes)

            if not focuses:
                logger.debug(
                    "No focuses generated for strategy",
                    strategy_id=strategy["id"],
                )
                continue

            # Score each (strategy, focus) pair
            for focus in focuses:
                # Convert Focus model to dict for scoring engine compatibility
                focus_dict = focus.model_dump() if isinstance(focus, Focus) else focus

                try:
                    scoring_result = await self.scoring_engine.score_candidate(
                        strategy=strategy,
                        focus=focus_dict,
                        graph_state=graph_state,
                        recent_nodes=recent_nodes,
                        conversation_history=conversation_history,
                        phase=phase,  # Pass phase to scoring engine
                    )

                    candidate = StrategyCandidate(
                        strategy=strategy,
                        focus=focus_dict,
                        score=scoring_result.final_score,
                        scoring_result=scoring_result,
                    )
                    candidates.append(candidate)

                    logger.debug(
                        "Candidate scored",
                        strategy_id=strategy["id"],
                        focus_type=focus_dict.get("focus_type"),
                        score=scoring_result.final_score,
                        vetoed_by=scoring_result.vetoed_by,
                    )

                except Exception as e:
                    logger.warning(
                        "Failed to score candidate",
                        strategy_id=strategy["id"],
                        focus_type=focus_dict.get("focus_type"),
                        error=str(e),
                    )
                    continue

        # Handle no valid candidates
        if not candidates:
            logger.warning("No valid candidates - using fallback")
            return await self._get_fallback_result(
                graph_state, recent_nodes, conversation_history
            )

        # Filter out vetoed candidates (scoring_result may be None for fallback candidates)
        non_vetoed = [
            c
            for c in candidates
            if c.scoring_result is None or c.scoring_result.vetoed_by is None
        ]

        # If all vetoed, use closing strategy per ADR-004
        if not non_vetoed:
            logger.info("All candidates vetoed - using closing strategy")
            closing_strategy = self.strategies.get("closing")
            if closing_strategy:
                closing_focus = {
                    "focus_type": "closing",
                    "focus_description": "Closing interview",
                }
                # Return closing strategy without re-scoring
                return SelectionResult(
                    selected_strategy=closing_strategy,
                    selected_focus=closing_focus,
                    final_score=0.0,
                    scoring_result=None,
                )
            # Fallback to top candidate even if vetoed
            non_vetoed = candidates

        # Sort non-vetoed candidates by score (descending)
        non_vetoed.sort(key=lambda c: c.score, reverse=True)

        # Select top candidate
        top_candidate = non_vetoed[0]

        # Get alternatives (top N, excluding selected, score >= threshold)
        alternatives = [
            c
            for c in non_vetoed[1 : self._alternatives_count + 1]
            if c.score >= self._alternatives_min_score
        ]

        logger.info(
            "Strategy selected (two-tier)",
            strategy_id=top_candidate.strategy["id"],
            focus_type=top_candidate.focus.get("focus_type")
            if isinstance(top_candidate.focus, dict)
            else top_candidate.focus.focus_type,
            score=top_candidate.score,
            num_alternatives=len(alternatives),
            vetoed_by=top_candidate.scoring_result.vetoed_by
            if top_candidate.scoring_result
            else None,
        )

        return SelectionResult(
            selected_strategy=top_candidate.strategy,
            selected_focus=top_candidate.focus,
            final_score=top_candidate.score,
            scoring_result=top_candidate.scoring_result,
            alternative_strategies=alternatives,
        )

    def _determine_phase(self, graph_state: GraphState) -> str:
        """
        Determine interview phase based on turn count (deterministic).

        Phase transition rules (based solely on turn count):
        - exploratory: turns 1 to _exploratory_end (exclusive)
        - focused: turns _exploratory_end to _focused_end (exclusive)
        - closing: turns _focused_end onwards (until session.max_turns)

        Example with defaults (8, 12, 2):
        - exploratory: turns 1-7
        - focused: turns 8-19
        - closing: turns 20-21

        Args:
            graph_state: Current graph state

        Returns:
            Phase string: 'exploratory', 'focused', or 'closing'
        """
        turn_count = graph_state.properties.get("turn_count", 0)

        # Phases are 0-indexed (turn 0 = first turn)
        if turn_count < self._exploratory_end:
            return "exploratory"
        elif turn_count < self._focused_end:
            return "focused"
        else:
            return "closing"

    def _get_possible_focuses(
        self,
        strategy: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Union[Focus, Dict[str, Any]]]:
        """
        Generate possible focus targets for a strategy.

        Focus generation logic per strategy type:
        - deepen: focus on most recent high-confidence node
        - broaden: single open focus
        - cover_element: one focus per uncovered element
        - closing: single closing focus
        - reflection: single reflection/meta-question focus

        Args:
            strategy: Strategy dict
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph (passed from select() to avoid properties dependency)

        Returns:
            List of possible focuses (as typed Focus models for new code, dicts for compatibility)
        """
        strategy_id = strategy["id"]
        focuses: List[Union[Focus, Dict[str, Any]]] = []

        # Use passed recent_nodes, or fall back to graph_state.properties (for backward compatibility)
        if recent_nodes is None:
            recent_nodes = graph_state.properties.get("recent_nodes", [])

        # Depth strategy: focus on most recent node
        if strategy_id == "deepen":
            # Get recent nodes from graph_state (passed in properties)
            recent_nodes = graph_state.properties.get("recent_nodes", [])
            if recent_nodes:
                # Focus on the most recent node
                last_node = recent_nodes[-1]
                # Create typed Focus model
                focuses.append(
                    Focus(
                        focus_type="depth_exploration",
                        node_id=last_node.get("id"),
                        element_id=None,
                        focus_description=f"Deepen: {last_node.get('label', 'topic')}",
                        confidence=0.8,
                    )
                )
            else:
                # Fallback: open depth focus
                focuses.append(
                    Focus(
                        focus_type="depth_exploration",
                        node_id=None,
                        element_id=None,
                        focus_description="Deepen understanding",
                        confidence=0.5,
                    )
                )

        # Breadth strategy: single open focus
        elif strategy_id == "broaden":
            focuses.append(
                Focus(
                    focus_type="breadth_exploration",
                    node_id=None,
                    element_id=None,
                    focus_description="Explore new aspects",
                    confidence=1.0,
                )
            )

        # Coverage strategy: one focus per uncovered or shallow element
        elif strategy_id == "cover_element":
            coverage_state = graph_state.coverage_state

            if coverage_state:
                # Phase 5: Use new coverage_state structure with depth tracking
                elements = coverage_state.elements or {}

                # Priority 1: Uncovered elements (high priority)
                uncovered = [
                    elem_id for elem_id, data in elements.items() if not data.covered
                ]

                # Priority 2: Shallow elements (depth < 0.5, medium priority)
                shallow = [
                    elem_id
                    for elem_id, data in elements.items()
                    if data.covered and data.depth_score < 0.5
                ]

                # Sort uncovered by element ID (deterministic ordering)
                for element in sorted(uncovered):
                    focuses.append(
                        Focus(
                            focus_type="coverage_gap",
                            node_id=None,
                            element_id=element,
                            focus_description=f"Cover: {element}",
                            confidence=1.0,
                        )
                    )

                # Sort shallow by depth score (lowest first = most shallow)
                shallow_sorted = sorted(shallow, key=lambda e: elements[e].depth_score)
                for element in shallow_sorted:
                    focuses.append(
                        Focus(
                            focus_type="deepen_coverage",
                            node_id=None,
                            element_id=element,
                            focus_description=f"Deepen: {element} (depth={elements[element].depth_score:.2f})",
                            confidence=0.9,
                        )
                    )
            else:
                # P0 Fix: Enhanced fallback when coverage_state is NULL
                # Try old coverage_state structure first (backward compatibility)
                coverage_state_old = graph_state.properties.get("coverage_state", {})
                elements_seen = set(coverage_state_old.get("elements_seen", []))
                elements_total = coverage_state_old.get("elements_total", [])

                uncovered = [e for e in elements_total if e not in elements_seen]

                # If old format also fails, try loading concept directly
                if not uncovered:
                    logger.warning(
                        "coverage_state_missing_using_concept_fallback",
                        message="coverage_state is NULL, attempting to load from concept config",
                    )

                    concept_id = graph_state.properties.get("concept_id")
                    if concept_id:
                        try:
                            concept = load_concept(concept_id)
                            # Generate focuses for all elements (no coverage tracking)
                            for element in concept.elements:
                                uncovered.append(element.id)
                                logger.debug(
                                    "coverage_fallback_element_added",
                                    element_id=element.id,
                                    element_label=element.label,
                                )
                        except Exception as e:
                            logger.error(
                                "coverage_fallback_concept_load_failed",
                                concept_id=concept_id,
                                error=str(e),
                            )

                # Generate focuses for uncovered elements
                for element in uncovered:
                    focuses.append(
                        Focus(
                            focus_type="coverage_gap",
                            node_id=None,
                            element_id=element,
                            focus_description=f"Cover: {element}",
                            confidence=1.0,
                        )
                    )

        # Closing strategy: single closing focus
        elif strategy_id == "closing":
            # Phase system controls when closing is available via phase multipliers
            # No min_turns gate needed - phase profiles handle timing
            focuses.append(
                Focus(
                    focus_type="closing",
                    node_id=None,
                    element_id=None,
                    focus_description="Closing interview - thank you for sharing",
                    confidence=1.0,
                )
            )

        # Reflection strategy: single meta-question focus
        elif strategy_id == "reflection":
            focuses.append(
                Focus(
                    focus_type="reflection",
                    node_id=None,
                    element_id=None,
                    focus_description="Reflection - is there anything else you'd like to share?",
                    confidence=1.0,
                )
            )

        # Bridge strategy: link to recent, then shift to peripheral
        elif strategy_id == "bridge":
            # Try to find a peripheral node (low degree) to bridge to
            # For now, use open exploration with bridge context
            focuses.append(
                Focus(
                    focus_type="lateral_bridge",
                    node_id=None,
                    element_id=None,
                    focus_description="Bridge to related area - link to what was said, then explore a new angle",
                    confidence=0.7,
                )
            )

        # Contrast strategy: introduce counter-example
        elif strategy_id == "contrast":
            # Try to find a node with opposite stance for contrast
            # For now, use open exploration with contrast context
            focuses.append(
                Focus(
                    focus_type="counter_example",
                    node_id=None,
                    element_id=None,
                    focus_description="Contrast - consider the opposite case or a different perspective",
                    confidence=0.7,
                )
            )

        # Ease strategy: simplify/soften the question
        elif strategy_id == "ease":
            focuses.append(
                Focus(
                    focus_type="rapport_repair",
                    node_id=None,
                    element_id=None,
                    focus_description="Ease - simplify the question and make it more conversational",
                    confidence=1.0,
                )
            )

        # Synthesis strategy: summarize and invite extension
        elif strategy_id == "synthesis":
            focuses.append(
                Focus(
                    focus_type="synthesis",
                    node_id=None,
                    element_id=None,
                    focus_description="Synthesis - summarize what you've heard and invite correction or addition",
                    confidence=0.8,
                )
            )

        return focuses

    async def _get_fallback_result(
        self,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],  # noqa: ARG001 - reserved for future use
        conversation_history: List[Dict[str, str]],  # noqa: ARG001 - reserved for future use
    ) -> SelectionResult:
        """Return fallback strategy when no candidates available.

        Per ADR-004: Force closing strategy when all candidates vetoed.
        """
        # Try closing strategy first
        closing_strategy = self.strategies.get("closing")
        if closing_strategy:
            # Phase system controls when closing is available via phase multipliers
            # No min_turns gate needed - phase profiles handle timing
            closing_focus = Focus(
                focus_type="closing",
                node_id=None,
                element_id=None,
                focus_description="Closing interview",
            )
            return SelectionResult(
                selected_strategy=closing_strategy,
                selected_focus=closing_focus,
                final_score=0.0,
                scoring_result=None,
            )

        # Otherwise use reflection strategy
        reflection_strategy = self.strategies.get("reflection")
        if reflection_strategy:
            reflection_focus = Focus(
                focus_type="reflection",
                node_id=None,
                element_id=None,
                focus_description="Is there anything else you'd like to share?",
            )
            return SelectionResult(
                selected_strategy=reflection_strategy,
                selected_focus=reflection_focus,
                final_score=0.0,
                scoring_result=None,
            )

        # Last resort: broaden
        broaden_strategy = self.strategies.get("broaden")
        if broaden_strategy:
            broaden_focus = Focus(
                focus_type="breadth_exploration",
                node_id=None,
                element_id=None,
                focus_description="Fallback: Explore new aspects",
            )
            return SelectionResult(
                selected_strategy=broaden_strategy,
                selected_focus=broaden_focus,
                final_score=0.0,
                scoring_result=None,
            )

        # Ultimate fallback: hardcoded broadening strategy
        logger.error("No fallback strategies available in self.strategies")
        broaden_focus = Focus(
            focus_type="breadth_exploration",
            node_id=None,
            element_id=None,
            focus_description="Let's explore something new",
        )
        return SelectionResult(
            selected_strategy={
                "id": "broaden",
                "name": "Broaden",
                "description": "Fallback broadening strategy",
            },
            selected_focus=broaden_focus,
            final_score=0.0,
            scoring_result=None,
        )

    async def extract_and_store_sentiment(
        self,
        graph_state: GraphState,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[float]:
        """
        Extract sentiment from qualitative signals and store in graph_state.

        This method should be called after qualitative signal extraction to
        compute turn-level sentiment from emotional_signal.intensity and store
        it in graph_state.properties["turn_sentiments"] for historical access.

        Per bead sxj: Add sentiment to conversation turns using existing signals.

        Args:
            graph_state: Current graph state (will be modified to store sentiment)
            conversation_history: Recent conversation turns (for fallback extraction)

        Returns:
            Sentiment value from -1.0 (high_negative) to +1.0 (high_positive),
            or None if no sentiment could be extracted
        """
        from src.services.scoring.signal_helpers import add_sentiment_to_turn

        turn_number = graph_state.properties.get("turn_count", 1)

        # Try to get sentiment from LLM-extracted emotional_signal
        qualitative_signals = graph_state.properties.get("qualitative_signals")
        if qualitative_signals:
            emotional_signal = qualitative_signals.get("emotional")
            if emotional_signal:
                # Convert emotional signal dict to proper format if needed
                # LLM extraction returns a dict with __dict__ format
                if isinstance(emotional_signal, dict):
                    # Check if it's already unpacked from __dict__
                    if "intensity" in emotional_signal:
                        sentiment = add_sentiment_to_turn(
                            graph_state, turn_number, emotional_signal
                        )
                        logger.debug(
                            "sentiment_extracted_from_llm_signals",
                            turn_number=turn_number,
                            sentiment=sentiment,
                        )
                        return sentiment

        # Fallback: Simple rule-based sentiment extraction
        # This provides basic sentiment tracking even without LLM signals
        sentiment = self._extract_sentiment_fallback(conversation_history or [])
        if sentiment is not None:
            # Store fallback sentiment
            if "turn_sentiments" not in graph_state.properties:
                graph_state.properties["turn_sentiments"] = {}
            graph_state.properties["turn_sentiments"][str(turn_number)] = sentiment
            logger.debug(
                "sentiment_extracted_fallback",
                turn_number=turn_number,
                sentiment=sentiment,
            )
            return sentiment

        return None

    def _extract_sentiment_fallback(
        self, conversation_history: List[Dict[str, str]]
    ) -> Optional[float]:
        """
        Simple rule-based sentiment extraction as fallback.

        Analyzes the most recent user response for positive/negative sentiment
        indicators when LLM signals are not available.

        Args:
            conversation_history: List of conversation turn dicts

        Returns:
            Sentiment value from -1.0 to +1.0, or None if no clear sentiment
        """
        # Get the most recent user response
        user_text = None
        for turn in reversed(conversation_history):
            if turn.get("speaker") == "user":
                user_text = turn.get("text", "")
                break

        if not user_text:
            return None

        # Simple sentiment word lists
        positive_words = [
            "love",
            "like",
            "great",
            "good",
            "excellent",
            "amazing",
            "wonderful",
            "enjoy",
            "prefer",
            "excited",
            "happy",
            "pleased",
            "fantastic",
            "awesome",
            "yes",
            "definitely",
            "absolutely",
            "certainly",
        ]
        negative_words = [
            "hate",
            "dislike",
            "bad",
            "terrible",
            "awful",
            "horrible",
            "worst",
            "disappointed",
            "sad",
            "angry",
            "frustrated",
            "annoyed",
            "upset",
            "no",
            "don't",
            "can't",
            "won't",
            "not",
            "never",
            "hard",
            "difficult",
        ]

        text_lower = user_text.lower()

        # Count sentiment indicators
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        # Check for intensifiers
        intensifiers = ["very", "really", "extremely", "absolutely", "totally"]
        has_intensifier = any(intensifier in text_lower for intensifier in intensifiers)

        # Calculate sentiment
        if positive_count == 0 and negative_count == 0:
            return None  # No clear sentiment

        if positive_count > negative_count:
            base_sentiment = 0.5
            if has_intensifier or positive_count >= 2:
                return 1.0
            return base_sentiment
        elif negative_count > positive_count:
            base_sentiment = -0.5
            if has_intensifier or negative_count >= 2:
                return -1.0
            return base_sentiment
        else:
            # Mixed or balanced - slightly positive or neutral
            return 0.1

    def __repr__(self) -> str:
        return (
            f"StrategyService("
            f"num_strategies={len(self.strategies)}, "
            f"alternatives_count={self._alternatives_count})"
        )
