"""Generate a scoring decomposition CSV from a simulation JSON artifact.

Reads the live score_decomposition field serialized per turn by the pipeline.
This captures the actual two-stage scoring: Stage 1 (strategy-level scores with
node_id="") and Stage 2 (node-level scores for the selected strategy). Includes
signal adjustments, phase multipliers, and phase bonuses — the same values that
determined strategy and node selection.

For older JSON files without score_decomposition, a placeholder row is emitted
per turn so the file remains usable with a clear annotation.

Output schema (one row per turn × candidate × active_signal):
    turn_number, phase, strategy, node_id, signal_name, signal_value,
    signal_weight, weighted_contribution, phase_multiplier, phase_bonus,
    base_score, final_score, rank, selected
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

# Allow running from scripts/ or from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


CSV_FIELDNAMES = [
    "turn_number",
    "phase",
    "strategy",
    "node_id",
    "node_label",
    "signal_name",
    "signal_value",
    "signal_weight",
    "weighted_contribution",
    "phase_multiplier",
    "phase_bonus",
    "base_score",
    "final_score",
    "rank",
    "selected",
    "gated",
    "gate_signal",
]


def _rows_from_decomposition(
    turn_number: int,
    phase: str,
    decomposition: list[dict[str, Any]],
    node_labels: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build CSV rows from a live score_decomposition list."""
    _node_labels = node_labels or {}
    rows: list[dict[str, Any]] = []
    for candidate in decomposition:
        is_gated = candidate.get("gated", False)
        node_id = candidate.get("node_id", "")
        contribs = candidate.get("signal_contributions") or []
        base = {
            "turn_number": turn_number,
            "phase": phase,
            "strategy": candidate["strategy"],
            "node_id": node_id,
            "node_label": _node_labels.get(node_id, ""),
            "phase_multiplier": candidate.get("phase_multiplier", 1.0),
            "phase_bonus": candidate.get("phase_bonus", 0.0),
            "base_score": candidate.get("base_score", 0.0),
            "final_score": candidate.get("final_score", 0.0),
            "rank": candidate.get("rank", ""),
            "selected": candidate.get("selected", False),
            "gated": is_gated,
            "gate_signal": candidate.get("gate_signal", ""),
        }
        if is_gated:
            # Gated pairs have no signal contributions — emit single summary row
            rows.append(
                {
                    **base,
                    "signal_name": "(gated)",
                    "signal_value": "",
                    "signal_weight": "",
                    "weighted_contribution": 0,
                }
            )
        elif contribs:
            for sc in contribs:
                rows.append(
                    {
                        **base,
                        "signal_name": sc["name"],
                        "signal_value": sc["value"],
                        "signal_weight": sc["weight"],
                        "weighted_contribution": sc["contribution"],
                    }
                )
        else:
            rows.append(
                {
                    **base,
                    "signal_name": "(no signals fired)",
                    "signal_value": "",
                    "signal_weight": "",
                    "weighted_contribution": 0,
                }
            )
    return rows


def generate_scoring_csv(json_path: Path, output_path: Path | None = None) -> Path:
    """Generate a scoring decomposition CSV from a simulation JSON artifact.

    Args:
        json_path: Path to the simulation JSON file.
        output_path: Optional explicit output path. If not provided, uses
            <json_stem>_scoring.csv next to the JSON.

    Returns:
        Path to the written CSV file.
    """
    with open(json_path) as f:
        data = json.load(f)

    all_rows: list[dict[str, Any]] = []

    # Build node_id → label lookup from graph section
    node_labels: dict[str, str] = {}
    for node in data.get("graph", {}).get("nodes", []):
        nid = node.get("id", "")
        label = node.get("label", "")
        if nid and label:
            node_labels[nid] = label

    for turn in data.get("turns", []):
        turn_number: int = turn.get("turn_number", 0)
        signals: dict[str, Any] = turn.get("signals") or {}
        phase: str = signals.get("meta.interview.phase", "unknown")
        decomposition = turn.get("score_decomposition")

        if not decomposition:
            # Old JSON without live decomposition — emit placeholder row
            strategy = turn.get("strategy_selected") or ""
            if strategy:
                all_rows.append(
                    {
                        "turn_number": turn_number,
                        "phase": phase,
                        "strategy": strategy,
                        "node_id": "",
                        "node_label": "",
                        "signal_name": "N/A (no score_decomposition in this JSON)",
                        "signal_value": "",
                        "signal_weight": "",
                        "weighted_contribution": "",
                        "phase_multiplier": "",
                        "phase_bonus": "",
                        "base_score": "",
                        "final_score": "",
                        "rank": 1,
                        "selected": True,
                        "gated": False,
                        "gate_signal": "",
                    }
                )
            continue

        all_rows.extend(
            _rows_from_decomposition(turn_number, phase, decomposition, node_labels)
        )

    if output_path:
        csv_path = output_path
    else:
        # Derive CSV path: replace .json suffix with _scoring.csv
        csv_path = json_path.with_name(json_path.stem + "_scoring.csv")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    return csv_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_scoring_csv.py <path_to_simulation.json>")
        sys.exit(1)

    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"File not found: {json_file}")
        sys.exit(1)

    csv_file = generate_scoring_csv(json_file)
    print(f"Scoring CSV written to: {csv_file}")
