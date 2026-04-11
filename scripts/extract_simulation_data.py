"""Extract flat analytical tables from simulation JSONs for methodology optimization.

Produces three Parquet files from a directory of simulation outputs:
  1. turns.parquet     — one row per turn with signals, strategy, graph metrics
  2. scoring.parquet   — one row per signal×strategy×turn (score decomposition)
  3. interviews.parquet — one row per interview with terminal graph/outcome stats

Usage:
    uv run python scripts/extract_simulation_data.py [INPUT_DIR] [OUTPUT_DIR]

    INPUT_DIR  defaults to synthetic_interviews/v2
    OUTPUT_DIR defaults to analysis/simulation_extract
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def _to_float(val: object) -> float | None:
    """Coerce a value to float, returning None for non-numeric (e.g. raw LLM strings)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return None
    return None


def extract_interview(path: Path) -> dict:
    """Parse one simulation JSON into structured records."""
    with open(path) as f:
        data = json.load(f)

    meta = data["metadata"]
    interview_id = meta["session_id"]
    common = {
        "interview_id": interview_id,
        "concept": meta["concept_id"],
        "persona": meta["persona_id"],
        "methodology": meta["methodology"],
        "total_turns": meta["total_turns"],
        "status": meta["status"],
    }

    turns_records: list[dict] = []
    scoring_records: list[dict] = []

    for t in data["turns"]:
        turn_num = t["turn_number"]
        signals = t.get("signals") or {}
        sat = t.get("saturation_metrics") or {}
        alts = t.get("strategy_alternatives") or []

        # Score margin: difference between rank 1 and rank 2
        alt_scores = sorted([a["score"] for a in alts], reverse=True) if alts else []
        score_margin = (alt_scores[0] - alt_scores[1]) if len(alt_scores) >= 2 else None

        turn_row = {
            **common,
            "turn": turn_num,
            "phase": signals.get("meta.interview.phase"),
            "strategy_selected": t.get("strategy_selected"),
            "score_margin": score_margin,
            "rank1_score": alt_scores[0] if alt_scores else None,
            # Graph growth this turn
            "nodes_added": len(t.get("nodes_added") or []),
            "edges_added": len(t.get("edges_added") or []),
            # Key signals (flattened) — coerce to float, some may be raw LLM strings
            "engagement": _to_float(signals.get("llm.intellectual_engagement")),
            "certainty": _to_float(signals.get("llm.certainty")),
            "specificity": _to_float(signals.get("llm.specificity")),
            "response_depth": _to_float(signals.get("llm.response_depth")),
            "valence": _to_float(signals.get("llm.valence")),
            "node_count": signals.get("graph.node_count"),
            "orphan_count": signals.get("graph.orphan_count"),
            "max_depth": signals.get("graph.max_depth"),
            "strategy_repetition": signals.get("temporal.strategy_repetition_count"),
            "turns_since_strategy_change": signals.get("temporal.turns_since_strategy_change"),
            "conversation_saturation": signals.get("meta.conversation.saturation"),
            "canonical_saturation": signals.get("meta.canonical.saturation"),
            "is_late_stage": signals.get("meta.interview.is_late_stage"),
            "global_response_trend": signals.get("llm.global_response_trend"),
            # Saturation metrics
            "new_info_rate": sat.get("new_info_rate"),
            "is_saturated": sat.get("is_saturated"),
            "consecutive_low_info": sat.get("consecutive_low_info"),
            # Termination
            "should_continue": t.get("should_continue"),
            "termination_reason": t.get("termination_reason"),
            # Node-level summary
            "tracked_nodes": len(t.get("node_signals") or {}),
            "exhausted_nodes": sum(
                1
                for ns in (t.get("node_signals") or {}).values()
                if ns.get("graph.node.exhausted")
            ),
        }
        turns_records.append(turn_row)

        # Score decomposition rows
        for entry in t.get("score_decomposition") or []:
            for sc in entry.get("signal_contributions") or []:
                scoring_records.append(
                    {
                        "interview_id": interview_id,
                        "persona": common["persona"],
                        "concept": common["concept"],
                        "turn": turn_num,
                        "phase": signals.get("meta.interview.phase"),
                        "strategy": entry["strategy"],
                        "node_id": entry.get("node_id", ""),
                        "signal_name": sc["name"],
                        "signal_value": str(sc["value"]),
                        "signal_weight": sc["weight"],
                        "contribution": sc["contribution"],
                        "base_score": entry["base_score"],
                        "phase_multiplier": entry["phase_multiplier"],
                        "phase_bonus": entry["phase_bonus"],
                        "final_score": entry["final_score"],
                        "rank": entry["rank"],
                        "selected": entry["selected"],
                    }
                )

    # Interview-level summary from final graph state
    graph = data.get("graph", {})
    summary = graph.get("summary", {})
    canonical = data.get("canonical_graph", {})
    last_turn = data["turns"][-1] if data["turns"] else {}
    last_signals = last_turn.get("signals", {})

    # Strategy diversity
    strategies_used = [t.get("strategy_selected") for t in data["turns"]]
    unique_strategies = set(s for s in strategies_used if s)

    interview_row = {
        **common,
        "termination_reason": last_turn.get("termination_reason"),
        # Final graph
        "final_nodes": summary.get("total_nodes", 0),
        "final_edges": summary.get("total_edges", 0),
        "edge_node_ratio": (
            summary.get("total_edges", 0) / summary["total_nodes"]
            if summary.get("total_nodes")
            else 0
        ),
        "canonical_slots": len(canonical.get("slots", [])),
        "node_types": len(summary.get("nodes_by_type", {})),
        "edge_types": len(summary.get("edges_by_type", {})),
        # Strategy diversity
        "unique_strategies": len(unique_strategies),
        "strategy_diversity": len(unique_strategies) / max(len(strategies_used), 1),
        # Final signals
        "final_saturation": last_signals.get("meta.conversation.saturation"),
        "final_canonical_saturation": last_signals.get("meta.canonical.saturation"),
        "final_max_depth": last_signals.get("graph.max_depth"),
        # Per-type node counts
        **{f"nodes_{k}": v for k, v in summary.get("nodes_by_type", {}).items()},
        **{f"edges_{k}": v for k, v in summary.get("edges_by_type", {}).items()},
    }

    return {
        "turns": turns_records,
        "scoring": scoring_records,
        "interview": interview_row,
    }


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synthetic_interviews/v2")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("analysis/simulation_extract")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        sys.exit(1)

    all_turns: list[dict] = []
    all_scoring: list[dict] = []
    all_interviews: list[dict] = []

    for path in json_files:
        try:
            result = extract_interview(path)
            all_turns.extend(result["turns"])
            all_scoring.extend(result["scoring"])
            all_interviews.append(result["interview"])
        except Exception as e:
            print(f"WARN: skipping {path.name}: {e}")

    df_turns = pd.DataFrame(all_turns)
    df_scoring = pd.DataFrame(all_scoring)
    df_interviews = pd.DataFrame(all_interviews)

    # Save
    df_turns.to_parquet(output_dir / "turns.parquet", index=False)
    df_scoring.to_parquet(output_dir / "scoring.parquet", index=False)
    df_interviews.to_parquet(output_dir / "interviews.parquet", index=False)

    # Summary
    print(f"Extracted {len(json_files)} interviews")
    print(f"  turns.parquet:      {len(df_turns):,} rows")
    print(f"  scoring.parquet:    {len(df_scoring):,} rows")
    print(f"  interviews.parquet: {len(df_interviews):,} rows")
    print(f"Output: {output_dir}")

    # Quick stats
    if not df_interviews.empty:
        print("\nPersona distribution:")
        print(df_interviews["persona"].value_counts().to_string())
        print(f"\nMean turns: {df_interviews['total_turns'].mean():.1f}")
        print(f"Mean final nodes: {df_interviews['final_nodes'].mean():.1f}")
        print(f"Mean strategy diversity: {df_interviews['strategy_diversity'].mean():.2f}")

    # Signal effectiveness preview: % of rows where contribution != 0
    if not df_scoring.empty:
        activity = (
            df_scoring.groupby("signal_name")["contribution"]
            .apply(lambda x: (x != 0).mean())
            .sort_values()
            .reset_index(name="activity_rate")
        )
        dormant = activity[activity["activity_rate"] < 0.1]
        print(f"\nDormant signals (fire <10% of rows): {len(dormant)}/{len(activity)}")
        if not dormant.empty:
            print(dormant.to_string(index=False))


if __name__ == "__main__":
    main()
