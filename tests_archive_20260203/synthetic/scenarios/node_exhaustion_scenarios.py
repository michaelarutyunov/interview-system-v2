"""Synthetic interview scenarios for testing node exhaustion behavior.

This module defines test scenarios that exercise various aspects of the
node exhaustion system including backtracking, uncertainty detection,
fatigue recovery, phase transitions, and strategy repetition.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class UserTurn:
    """A single user turn in a synthetic interview.

    Attributes:
        response_text: Simulated user response
        response_depth: Depth classification (surface/shallow/deep)
        graph_changes: Summary of graph changes produced (if any)
        focus_node_id: Node ID that was focused for this turn
        strategy_used: Strategy used for this turn
    """

    response_text: str
    response_depth: str
    graph_changes: Optional[Dict[str, int]] = None
    focus_node_id: Optional[str] = None
    strategy_used: Optional[str] = None

    def __post_init__(self):
        if self.graph_changes is None:
            self.graph_changes = {"nodes_added": 0, "edges_added": 0}


@dataclass
class InterviewScenario:
    """Test scenario for synthetic interviews.

    Attributes:
        name: Unique scenario identifier
        description: Human-readable description of what this scenario tests
        user_turns: List of simulated user responses
        expected_behaviors: List of expected system behaviors to validate
        initial_nodes: List of nodes to pre-populate in the graph
        turn_count: Number of turns in the interview
        metadata: Additional scenario metadata
    """

    name: str
    description: str
    user_turns: List[UserTurn]
    expected_behaviors: List[str]
    initial_nodes: List[Dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.turn_count == 0:
            self.turn_count = len(self.user_turns)


@dataclass
class ValidationResult:
    """Result of validating a scenario run.

    Attributes:
        scenario_name: Name of the scenario that was validated
        passed: Whether all validations passed
        validation_results: Dict of validation name -> bool
        details: Additional details about the validation
    """

    scenario_name: str
    passed: bool
    validation_results: Dict[str, bool]
    details: Dict[str, Any]


# =============================================================================
# Scenario Definitions
# =============================================================================


def create_exhaustion_detection_scenario() -> InterviewScenario:
    """Scenario: Interview that exhausts a node, then backtracks.

    Tests:
    - Exhaustion signal detection after multiple turns without yield
    - Backtracking to non-exhausted nodes
    - Node deprioritization after exhaustion
    """
    turns = [
        # Turn 1: Focus on node1, get deep response (yield)
        UserTurn(
            response_text="I use it every morning to make coffee before work",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 2: Focus on node1 again, get shallow response
        UserTurn(
            response_text="It's pretty good I guess",
            response_depth="shallow",
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 3: Focus on node1 again, get shallow response (no yield)
        UserTurn(
            response_text="Yeah, it works fine",
            response_depth="shallow",
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 4: Focus on node1 again, get surface response (no yield)
        UserTurn(
            response_text="I don't know, it's just a coffee maker",
            response_depth="surface",
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 5: System should backtrack to node2
        UserTurn(
            response_text="I bought it at the local store last year",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="node2",
            strategy_used="deepen",
        ),
    ]

    return InterviewScenario(
        name="exhaustion_detection",
        description="Node gets exhausted after multiple turns without yield, system backtracks",
        user_turns=turns,
        expected_behaviors=[
            "node1_exhausted_after_turn_4",
            "node2_selected_on_turn_5",
            "exhausted_node_deprioritized",
        ],
        initial_nodes=[
            {"id": "node1", "label": "Coffee Maker", "depth": 0},
            {"id": "node2", "label": "Purchase", "depth": 1},
        ],
        metadata={
            "category": "exhaustion",
            "focus_nodes": ["node1", "node2"],
            "exhaustion_node": "node1",
        },
    )


def create_multi_branch_exploration_scenario() -> InterviewScenario:
    """Scenario: Interview that explores multiple branches.

    Tests:
    - Breadth-first exploration across branches
    - Node state tracking across multiple nodes
    - Orphan node prioritization
    """
    turns = [
        # Turn 1: Start with root node
        UserTurn(
            response_text="I drink coffee to wake up in the morning",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="root",
            strategy_used="deepen",
        ),
        # Turn 2: Explore branch A
        UserTurn(
            response_text="I usually have a latte with oat milk",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="branch_a",
            strategy_used="deepen",
        ),
        # Turn 3: Back to explore branch B (breadth)
        UserTurn(
            response_text="Sometimes I have an espresso in the afternoon",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="branch_b",
            strategy_used="broaden",
        ),
        # Turn 4: Explore branch C (another breadth move)
        UserTurn(
            response_text="On weekends I like cold brew",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="branch_c",
            strategy_used="broaden",
        ),
    ]

    return InterviewScenario(
        name="multi_branch_exploration",
        description="Explore multiple branches to test breadth-first behavior",
        user_turns=turns,
        expected_behaviors=[
            "all_branches_explored",
            "breadth_strategy_selected_on_turn_3",
            "node_states_tracked_correctly",
        ],
        initial_nodes=[
            {"id": "root", "label": "Coffee", "depth": 0},
            {"id": "branch_a", "label": "Morning Coffee", "depth": 1},
            {"id": "branch_b", "label": "Afternoon Coffee", "depth": 1},
            {"id": "branch_c", "label": "Weekend Coffee", "depth": 1},
        ],
        metadata={
            "category": "exploration",
            "focus_nodes": ["root", "branch_a", "branch_b", "branch_c"],
        },
    )


def create_uncertainty_response_scenario() -> InterviewScenario:
    """Scenario: Interview with hedging/uncertain responses.

    Tests:
    - Hedging language signal detection
    - Uncertainty-triggered strategy selection
    - Depth adjustment based on confidence
    """
    turns = [
        # Turn 1: User is uncertain
        UserTurn(
            response_text="I think maybe I use it for coffee, but I'm not sure",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="clarify",
        ),
        # Turn 2: Still uncertain
        UserTurn(
            response_text="It depends, sometimes I guess, probably",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="clarify",
        ),
        # Turn 3: Finally confident
        UserTurn(
            response_text="Yes, I definitely use it for coffee every morning",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
    ]

    return InterviewScenario(
        name="uncertainty_response",
        description="User shows uncertainty, system adapts with clarification",
        user_turns=turns,
        expected_behaviors=[
            "high_hedging_detected_on_turn_1",
            "clarify_strategy_selected",
            "depth_increases_after_confidence",
        ],
        initial_nodes=[
            {"id": "node1", "label": "Usage", "depth": 0},
        ],
        metadata={
            "category": "uncertainty",
            "hedging_levels": ["high", "high", "none"],
        },
    )


def create_fatigue_recovery_scenario() -> InterviewScenario:
    """Scenario: Interview with shallow responses, then revitalization.

    Tests:
    - Fatigue detection from shallow responses
    - Engagement signal tracking
    - Recovery when user becomes engaged again
    """
    turns = [
        # Turn 1: Shallow response (fatigue starting)
        UserTurn(
            response_text="It's okay I guess",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="ease",
        ),
        # Turn 2: Surface response (fatigue high)
        UserTurn(
            response_text="I don't know",
            response_depth="surface",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="ease",
        ),
        # Turn 3: Another shallow response
        UserTurn(
            response_text="Not really",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="ease",
        ),
        # Turn 4: Revitalization! User becomes engaged
        UserTurn(
            response_text="Actually, I remember one time when I made this amazing "
            "cappuccino for my friends and they loved it!",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
    ]

    return InterviewScenario(
        name="fatigue_recovery",
        description="User shows fatigue then recovers engagement",
        user_turns=turns,
        expected_behaviors=[
            "fatigue_detected_by_turn_2",
            "ease_strategy_selected_during_fatigue",
            "engagement_recovered_on_turn_4",
            "deep_strategy_selected_after_recovery",
        ],
        initial_nodes=[
            {"id": "node1", "label": "Experience", "depth": 0},
        ],
        metadata={
            "category": "fatigue",
            "fatigue_detected": [False, True, True, False],
        },
    )


def create_phase_transitions_scenario() -> InterviewScenario:
    """Scenario: Interview progresses through early -> mid -> late phases.

    Tests:
    - Phase detection (exploratory -> focused -> closing)
    - Phase-based strategy selection
    - Phase boundary transitions
    """
    turns = [
        # Turn 1-3: Exploratory phase (breadth focus)
        UserTurn(
            response_text="I drink coffee for energy and social reasons",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="root",
            strategy_used="broaden",
        ),
        UserTurn(
            response_text="I also like tea sometimes",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="node2",
            strategy_used="broaden",
        ),
        # Turn 4-6: Focused phase (depth focus)
        UserTurn(
            response_text="The energy boost is really important for my work",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="energy",
            strategy_used="deepen",
        ),
        UserTurn(
            response_text="I need it to stay focused during long meetings",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="focus",
            strategy_used="deepen",
        ),
        # Turn 7-8: Closing phase (synthesis focus)
        UserTurn(
            response_text="So overall, coffee helps me with work energy and social connections",
            response_depth="deep",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="root",
            strategy_used="synthesis",
        ),
        UserTurn(
            response_text="Yeah, that about covers it",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="root",
            strategy_used="closing",
        ),
    ]

    return InterviewScenario(
        name="phase_transitions",
        description="Interview progresses through all phases",
        user_turns=turns,
        expected_behaviors=[
            "exploratory_phase_detected_early",
            "focused_phase_detected_mid",
            "closing_phase_detected_late",
            "strategy_selection_adapts_to_phase",
        ],
        initial_nodes=[
            {"id": "root", "label": "Coffee", "depth": 0},
            {"id": "node2", "label": "Tea", "depth": 1},
            {"id": "energy", "label": "Energy", "depth": 1},
            {"id": "focus", "label": "Focus", "depth": 2},
        ],
        metadata={
            "category": "phases",
            "phase_sequence": [
                "exploratory",
                "exploratory",
                "focused",
                "focused",
                "closing",
                "closing",
            ],
        },
    )


def create_orphan_node_priority_scenario() -> InterviewScenario:
    """Scenario: Interview prioritizes orphan nodes.

    Tests:
    - Orphan detection (nodes with no edges)
    - Orphan prioritization in scoring
    - Orphan node connection to graph
    """
    turns = [
        # Turn 1: Create root node with edges
        UserTurn(
            response_text="I drink coffee every morning",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="root",
            strategy_used="deepen",
        ),
        # Turn 2: Create orphan node (no edges yet)
        UserTurn(
            response_text="I also have a toaster",
            response_depth="shallow",
            graph_changes={"nodes_added": 1, "edges_added": 0},  # Orphan!
            focus_node_id="orphan",
            strategy_used="cover_element",
        ),
        # Turn 3: System should prioritize connecting the orphan
        UserTurn(
            response_text="The toaster is in the same kitchen as the coffee maker",
            response_depth="deep",
            graph_changes={"nodes_added": 0, "edges_added": 1},  # Connected!
            focus_node_id="orphan",
            strategy_used="bridge",
        ),
    ]

    return InterviewScenario(
        name="orphan_node_priority",
        description="System prioritizes connecting orphan nodes",
        user_turns=turns,
        expected_behaviors=[
            "orphan_detected_on_turn_2",
            "orphan_prioritized_on_turn_3",
            "orphan_connected_to_graph",
        ],
        initial_nodes=[
            {"id": "root", "label": "Coffee", "depth": 0},
            {"id": "orphan", "label": "Toaster", "depth": 0},
        ],
        metadata={"category": "orphans", "orphan_node": "orphan"},
    )


def create_probe_deeper_opportunity_scenario() -> InterviewScenario:
    """Scenario: Deep responses without yield indicate opportunity to probe deeper.

    Tests:
    - Deep response detection
    - Yield vs depth distinction
    - Probe deeper strategy selection
    """
    turns = [
        # Turn 1: Deep response with yield
        UserTurn(
            response_text="I use my coffee maker every morning because it helps "
            "me wake up and prepare for work",
            response_depth="deep",
            graph_changes={"nodes_added": 2, "edges_added": 2},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 2: Deep response without yield (more detail available)
        UserTurn(
            response_text="The morning routine is really important to me because "
            "it sets the tone for the whole day",
            response_depth="deep",
            graph_changes={"nodes_added": 0, "edges_added": 0},  # No yield!
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 3: Still deep, no yield
        UserTurn(
            response_text="I've been doing this for about 5 years now",
            response_depth="deep",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
    ]

    return InterviewScenario(
        name="probe_deeper_opportunity",
        description="Deep responses without yield indicate opportunity to keep probing",
        user_turns=turns,
        expected_behaviors=[
            "deep_responses_detected",
            "no_yield_on_turns_2_and_3",
            "deepen_strategy_continues_despite_no_yield",
        ],
        initial_nodes=[
            {"id": "node1", "label": "Morning Routine", "depth": 0},
        ],
        metadata={
            "category": "depth",
            "depth_sequence": ["deep", "deep", "deep"],
            "yield_sequence": [True, False, False],
        },
    )


def create_strategy_repetition_scenario() -> InterviewScenario:
    """Scenario: Same strategy used repeatedly on same node.

    Tests:
    - Strategy repetition detection
    - Strategy repetition penalty
    - Strategy switching when repetition is high
    """
    turns = [
        # Turn 1-4: Same strategy (deepen) on same node
        UserTurn(
            response_text="I use it for coffee",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        UserTurn(
            response_text="It's a nice coffee maker",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        UserTurn(
            response_text="I like it",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        UserTurn(
            response_text="It works well",
            response_depth="shallow",
            graph_changes={"nodes_added": 0, "edges_added": 0},
            focus_node_id="node1",
            strategy_used="deepen",
        ),
        # Turn 5: System should switch strategies
        UserTurn(
            response_text="I also use it for tea sometimes",
            response_depth="deep",
            graph_changes={"nodes_added": 1, "edges_added": 1},
            focus_node_id="node1",
            strategy_used="broaden",
        ),
    ]

    return InterviewScenario(
        name="strategy_repetition",
        description="System detects strategy repetition and switches strategies",
        user_turns=turns,
        expected_behaviors=[
            "strategy_repetition_detected",
            "repetition_penalty_applied",
            "strategy_switched_on_turn_5",
        ],
        initial_nodes=[
            {"id": "node1", "label": "Coffee Maker", "depth": 0},
        ],
        metadata={
            "category": "repetition",
            "strategy_sequence": ["deepen", "deepen", "deepen", "deepen", "broaden"],
        },
    )


# =============================================================================
# Scenario Registry
# =============================================================================

ALL_SCENARIOS = [
    create_exhaustion_detection_scenario(),
    create_multi_branch_exploration_scenario(),
    create_uncertainty_response_scenario(),
    create_fatigue_recovery_scenario(),
    create_phase_transitions_scenario(),
    create_orphan_node_priority_scenario(),
    create_probe_deeper_opportunity_scenario(),
    create_strategy_repetition_scenario(),
]


def get_scenario_by_name(name: str) -> Optional[InterviewScenario]:
    """Get a scenario by name.

    Args:
        name: Scenario name

    Returns:
        InterviewScenario if found, None otherwise
    """
    for scenario in ALL_SCENARIOS:
        if scenario.name == name:
            return scenario
    return None


def get_scenarios_by_category(category: str) -> List[InterviewScenario]:
    """Get all scenarios for a specific category.

    Args:
        category: Category name (exhaustion, exploration, uncertainty, etc.)

    Returns:
        List of matching scenarios
    """
    return [
        scenario
        for scenario in ALL_SCENARIOS
        if scenario.metadata.get("category") == category
    ]
