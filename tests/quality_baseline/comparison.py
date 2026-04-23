"""Quality baseline comparison functions.

Compares per-turn pipeline outputs (concepts, relationships, strategy, focus)
against saved fixtures to detect regressions from optimization changes.

Metrics:
- concept_jaccard: Jaccard similarity on concept label sets per turn
- node_type_accuracy: Fraction of shared concepts with matching node_type
- relationship_jaccard: Jaccard on (source, target, edge_type) tuples
- strategy_match_rate: Exact match rate on strategy selection
- focus_match_rate: Exact match rate on focus node label
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnComparison:
    turn_number: int
    concept_jaccard: float
    node_type_accuracy: float
    relationship_jaccard: float
    strategy_match: bool
    focus_match: bool


@dataclass
class SessionComparison:
    session_id: str
    methodology: str
    concept_id: str
    persona_id: str
    turns: list[TurnComparison]

    # Aggregated metrics
    mean_concept_jaccard: float
    mean_node_type_accuracy: float
    mean_relationship_jaccard: float
    strategy_match_rate: float
    focus_match_rate: float


def jaccard(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def compare_turn(fixture_turn: dict, new_turn: dict) -> TurnComparison:
    """Compare a single turn's outputs against the fixture."""
    tn = fixture_turn["turn_number"]

    # Concept labels
    f_labels = {c["label"] for c in fixture_turn["concepts"]}
    n_labels = {c["label"] for c in new_turn["concepts"]}
    cj = jaccard(f_labels, n_labels)

    # Node type accuracy for shared concepts
    f_types = {c["label"]: c["node_type"] for c in fixture_turn["concepts"]}
    n_types = {c["label"]: c["node_type"] for c in new_turn["concepts"]}
    shared = f_labels & n_labels
    if shared:
        type_matches = sum(1 for lbl in shared if f_types.get(lbl) == n_types.get(lbl))
        nta = type_matches / len(shared)
    else:
        nta = 1.0 if not f_labels and not n_labels else 0.0

    # Relationships as (source, target, edge_type) tuples
    f_rels = {
        (r["source_label"], r["target_label"], r["edge_type"])
        for r in fixture_turn["relationships"]
    }
    n_rels = {
        (r["source_label"], r["target_label"], r["edge_type"])
        for r in new_turn["relationships"]
    }
    rj = jaccard(f_rels, n_rels)

    return TurnComparison(
        turn_number=tn,
        concept_jaccard=cj,
        node_type_accuracy=nta,
        relationship_jaccard=rj,
        strategy_match=fixture_turn["strategy"] == new_turn["strategy"],
        focus_match=fixture_turn["focus_node_label"] == new_turn["focus_node_label"],
    )


def compare_sessions(fixture: dict, new_data: dict) -> SessionComparison:
    """Compare a full session against its fixture."""
    f_turns = {t["turn_number"]: t for t in fixture["turns"]}
    n_turns = {t["turn_number"]: t for t in new_data["turns"]}

    common_turns = sorted(set(f_turns) & set(n_turns))
    turn_comparisons = []
    for tn in common_turns:
        tc = compare_turn(f_turns[tn], n_turns[tn])
        turn_comparisons.append(tc)

    if not turn_comparisons:
        return SessionComparison(
            session_id=fixture["session_id"],
            methodology=fixture["methodology"],
            concept_id=fixture["concept_id"],
            persona_id=fixture["persona_id"],
            turns=[],
            mean_concept_jaccard=0.0,
            mean_node_type_accuracy=0.0,
            mean_relationship_jaccard=0.0,
            strategy_match_rate=0.0,
            focus_match_rate=0.0,
        )

    n = len(turn_comparisons)
    return SessionComparison(
        session_id=fixture["session_id"],
        methodology=fixture["methodology"],
        concept_id=fixture["concept_id"],
        persona_id=fixture["persona_id"],
        turns=turn_comparisons,
        mean_concept_jaccard=sum(tc.concept_jaccard for tc in turn_comparisons) / n,
        mean_node_type_accuracy=sum(tc.node_type_accuracy for tc in turn_comparisons)
        / n,
        mean_relationship_jaccard=sum(
            tc.relationship_jaccard for tc in turn_comparisons
        )
        / n,
        strategy_match_rate=sum(1 for tc in turn_comparisons if tc.strategy_match) / n,
        focus_match_rate=sum(1 for tc in turn_comparisons if tc.focus_match) / n,
    )


def check_thresholds(comparison: SessionComparison, thresholds: dict) -> list[str]:
    """Check if a session comparison passes all thresholds. Returns list of failures."""
    failures = []

    if comparison.mean_concept_jaccard < thresholds.get("concept_jaccard", 0.85):
        failures.append(
            f"concept_jaccard={comparison.mean_concept_jaccard:.3f} "
            f"< {thresholds['concept_jaccard']:.3f}"
        )
    if comparison.mean_node_type_accuracy < thresholds.get("node_type_accuracy", 0.80):
        failures.append(
            f"node_type_accuracy={comparison.mean_node_type_accuracy:.3f} "
            f"< {thresholds['node_type_accuracy']:.3f}"
        )
    if comparison.mean_relationship_jaccard < thresholds.get(
        "relationship_jaccard", 0.70
    ):
        failures.append(
            f"relationship_jaccard={comparison.mean_relationship_jaccard:.3f} "
            f"< {thresholds['relationship_jaccard']:.3f}"
        )
    if comparison.strategy_match_rate < thresholds.get("strategy_match_rate", 0.70):
        failures.append(
            f"strategy_match_rate={comparison.strategy_match_rate:.3f} "
            f"< {thresholds['strategy_match_rate']:.3f}"
        )
    if comparison.focus_match_rate < thresholds.get("focus_match_rate", 0.60):
        failures.append(
            f"focus_match_rate={comparison.focus_match_rate:.3f} "
            f"< {thresholds['focus_match_rate']:.3f}"
        )

    return failures


# Default thresholds — tuned for LLM non-determinism tolerance.
# These are generous because LLM extraction varies across runs even with
# identical inputs. Tightening these requires multiple comparison runs
# to establish the natural variance baseline.
DEFAULT_THRESHOLDS = {
    "concept_jaccard": 0.85,
    "node_type_accuracy": 0.80,
    "relationship_jaccard": 0.70,
    "strategy_match_rate": 0.70,
    "focus_match_rate": 0.60,
}
