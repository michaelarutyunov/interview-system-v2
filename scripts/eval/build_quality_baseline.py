#!/usr/bin/env python3
"""Build quality baseline fixtures from existing synthetic interviews.

Selects passing interviews from Phase 4.1 reviews and snapshots per-turn
outputs (concepts, relationships, strategy, focus node) as JSON fixtures
for regression comparison.

Usage:
    uv run python scripts/eval/build_quality_baseline.py
    uv run python scripts/eval/build_quality_baseline.py --all   # include CJM
"""

import argparse
import json
from pathlib import Path

INTERVIEWS_DIR = Path("synthetic_interviews")
FIXTURES_DIR = Path("tests/fixtures/quality_baseline")

# Phase 4.1 interviews that passed review criteria, covering 4 methodologies.
BASELINE_SESSIONS = {
    # MEC Strict — baseline_cooperative (PASS)
    "20260415_224733_glp1_food_mec_strict_baseline_cooperative.json": "means_end_chain_v2_strict",
    # JTBD — baseline_cooperative (PASS)
    "20260415_225117_glp1_food_jtbd_baseline_cooperative.json": "jobs_to_be_done_v2",
    # CIT — baseline_cooperative (PASS)
    "20260415_225511_cold_brew_discovery_cit_baseline_cooperative.json": "critical_incident_v2",
    # RG — baseline_cooperative (PASS)
    "20260415_225923_plant_milk_comparison_rg_baseline_cooperative.json": "repertory_grid_v2",
    # CIT regression re-test — baseline_cooperative (PASS)
    "20260415_231223_cold_brew_discovery_cit_baseline_cooperative.json": "critical_incident_v2",
    # MEC Strict — baseline_cooperative (later run with latency data)
    "20260417_140252_glp1_food_mec_strict_baseline_cooperative.json": "means_end_chain_v2_strict",
}

# CJM sessions both failed review (advance_stage didn't fire, no validate close)
CJM_SESSIONS = {
    "20260417_114113_coffee_subscription_cjm_baseline_cooperative.json": "customer_journey_mapping_v2",
}


def build_node_label_map(interview: dict) -> dict[str, str]:
    """Build node_id → label map from the full graph."""
    return {n["id"]: n["label"] for n in interview["graph"]["nodes"]}


def extract_turn_snapshot(turn: dict, node_labels: dict[str, str]) -> dict:
    """Extract per-turn outputs for comparison."""
    concepts = [
        {"label": n["label"], "node_type": n["node_type"]}
        for n in turn.get("nodes_added", [])
    ]

    relationships = []
    for e in turn.get("edges_added", []):
        src = node_labels.get(e["source_node_id"], e["source_node_id"])
        tgt = node_labels.get(e["target_node_id"], e["target_node_id"])
        relationships.append(
            {
                "source_label": src,
                "target_label": tgt,
                "edge_type": e["edge_type"],
            }
        )

    return {
        "turn_number": turn["turn_number"],
        "strategy": turn.get("strategy_selected", ""),
        "focus_node_label": turn.get("focus_node_label", ""),
        "concepts": concepts,
        "relationships": relationships,
    }


def build_fixture(filename: str) -> dict:
    """Build a complete fixture from an interview JSON file."""
    path = INTERVIEWS_DIR / filename
    data = json.loads(path.read_text())
    meta = data["metadata"]
    node_labels = build_node_label_map(data)

    turns = []
    for turn in data["turns"]:
        # Skip turn 0 (system opening, no extraction)
        if turn["turn_number"] == 0:
            continue
        turns.append(extract_turn_snapshot(turn, node_labels))

    return {
        "source_file": filename,
        "session_id": meta["session_id"],
        "methodology": meta["methodology"],
        "concept_id": meta["concept_id"],
        "persona_id": meta["persona_id"],
        "total_turns": len(turns),
        "turns": turns,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build quality baseline fixtures")
    parser.add_argument("--all", action="store_true", help="Include CJM sessions")
    args = parser.parse_args()

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    sessions = dict(BASELINE_SESSIONS)
    if args.all:
        sessions.update(CJM_SESSIONS)

    built = []
    for filename, methodology in sorted(sessions.items()):
        path = INTERVIEWS_DIR / filename
        if not path.exists():
            print(f"  SKIP {filename} (not found)")
            continue

        fixture = build_fixture(filename)
        fixture_path = FIXTURES_DIR / f"{fixture['session_id']}.json"
        fixture_path.write_text(json.dumps(fixture, indent=2))
        built.append((methodology, filename, fixture["total_turns"]))
        print(f"  OK   {methodology}: {filename} ({fixture['total_turns']} turns)")

    print(f"\nBuilt {len(built)} fixtures in {FIXTURES_DIR}/")

    # Summary
    methods = set(m for m, _, _ in built)
    print(f"Methodologies: {', '.join(sorted(methods))}")
    print(f"Total turns: {sum(t for _, _, t in built)}")


if __name__ == "__main__":
    main()
