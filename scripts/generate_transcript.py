#!/usr/bin/env python3
"""Generate a structured markdown transcript from a simulation JSON file.

Usage:
    python scripts/generate_transcript.py synthetic_interviews/<filename>.json
    python scripts/generate_transcript.py  # processes most recent JSON

Output is saved to reports/transcripts/<timestamp>_transcript.md
where <timestamp> is extracted from the source filename.
"""

import json
import re
import sys
from pathlib import Path

OUTPUT_DIR = Path("reports/transcripts")


def _word_count(text: str) -> int:
    return len(text.split())


def _node_type_label(node_type: str) -> str:
    """Convert snake_case node type to a readable label."""
    return node_type.replace("_", " ").title()


def _resolve_focus_node_from_decomposition(
    turn: dict, nodes_by_id: dict
) -> tuple[str | None, str | None]:
    """Backfill focus node from score_decomposition for old JSON files.

    Looks for the selected entry that has a non-empty node_id — this is the
    node-level selected candidate (as opposed to the conversation-level one with
    node_id="").

    Returns:
        (focus_node_id, focus_node_label) or (None, None) if not found.
    """
    decomp = turn.get("score_decomposition") or []
    for entry in decomp:
        if entry.get("selected") and entry.get("node_id"):
            node_id = entry["node_id"]
            node_data = nodes_by_id.get(node_id, {})
            label = node_data.get("label")
            return node_id, label
    return None, None


def _find_focus_node_in_question(question: str, node_label: str) -> str:
    """Produce a short explainer for where the focus node appears in the question.

    Checks if the node label (or key words from it) appears verbatim in the question.
    Falls back to a generic description if not found.
    """
    label_lower = node_label.lower()
    question_lower = question.lower()

    # Try exact match first
    if label_lower in question_lower:
        return f'Directly referenced as "{node_label}"'

    # Try matching key words (3+ chars) from the label
    words = [w for w in re.split(r"[\s,;]+", label_lower) if len(w) >= 4]
    matched = [w for w in words if w in question_lower]
    if matched:
        return f'Key concept "{", ".join(matched)}" from this node echoed in question wording'

    # No surface match — the node shaped the question topically
    return f"Focus node ({node_label}) shaped question direction via strategy selection"


def generate_transcript(json_path: Path) -> Path:
    """Generate a markdown transcript from a simulation JSON file.

    Args:
        json_path: Path to the simulation JSON file.

    Returns:
        Path to the generated markdown file.
    """
    data = json.loads(json_path.read_text())
    meta = data["metadata"]
    turns = data["turns"]

    # Build node lookup: id → full node dict (includes source_quotes)
    nodes_by_id: dict = {n["id"]: n for n in data["graph"]["nodes"]}

    # Concepts extracted from turn N's response live in turn N+1's nodes_added
    # (process_turn(response_N) returns nodes that are stored in turn N+1).
    # Build a map: answer_turn_number → nodes_added from the following turn.
    nodes_from_answer: dict[int, list] = {}
    for i, t in enumerate(turns[:-1]):
        next_turn = turns[i + 1]
        nodes_from_answer[t["turn_number"]] = next_turn.get("nodes_added") or []
    # Last turn: no following turn, so no extracted concepts to display
    if turns:
        nodes_from_answer[turns[-1]["turn_number"]] = []

    # Extract timestamp from filename (pattern: YYYYMMDD_HHMMSS_...)
    stem = json_path.stem
    ts_match = re.match(r"(\d{8}_\d{6})", stem)
    timestamp = ts_match.group(1) if ts_match else stem

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{timestamp}_transcript.md"

    lines: list[str] = []

    # ─── Section 1: Brief header ──────────────────────────────────────────────
    lines.append(f"# Interview Transcript — {timestamp}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Concept | {meta.get('concept_name', meta.get('concept_id'))} |")
    lines.append(f"| Methodology | {meta.get('methodology', 'N/A')} |")
    lines.append(f"| Persona | {meta.get('persona_name', meta.get('persona_id'))} |")
    lines.append(f"| Total turns | {meta.get('total_turns')} |")
    lines.append(f"| Status | {meta.get('status')} |")
    lines.append("")

    # ─── Section 2: Turn breakdown table ─────────────────────────────────────
    lines.append("## Turn Breakdown")
    lines.append("")
    lines.append(
        "| Turn | Strategy | Focus Node | Concepts Extracted | Response Words |"
    )
    lines.append(
        "|------|----------|------------|-------------------|----------------|"
    )

    for turn in turns:
        n = turn["turn_number"]
        strategy = turn.get("strategy_selected") or "—"
        focus_label = turn.get("focus_node_label")
        if not focus_label:
            _, focus_label = _resolve_focus_node_from_decomposition(turn, nodes_by_id)
        concepts_count = len(nodes_from_answer.get(n, []))
        word_count = _word_count(turn.get("response", ""))
        lines.append(
            f"| {n} | {strategy} | {focus_label or '—'} | {concepts_count} | {word_count} |"
        )

    lines.append("")

    # ─── Section 3: Q&A detail ────────────────────────────────────────────────
    lines.append("## Turn-by-Turn Q&A")
    lines.append("")

    for turn in turns:
        n = turn["turn_number"]
        question = turn.get("question", "")
        response = turn.get("response", "")
        strategy = turn.get("strategy_selected") or "N/A"
        focus_node_id = turn.get("focus_node_id")
        focus_node_label = turn.get("focus_node_label")
        # Backfill from score_decomposition for old JSON files lacking the field
        if not focus_node_id:
            focus_node_id, focus_node_label = _resolve_focus_node_from_decomposition(
                turn, nodes_by_id
            )
        # Concepts extracted from THIS turn's answer (live in next turn's nodes_added)
        nodes_added = nodes_from_answer.get(n, [])

        lines.append("---")
        lines.append("")

        if n == 0:
            lines.append("### Turn 0 — Opening Question")
            lines.append("")
            lines.append(f"**Q:** {question}")
            lines.append("")
            lines.append(f"**A:** {response}")
            lines.append("")
            # Show concepts extracted from the opening answer
            t0_nodes = nodes_from_answer.get(0, [])
            if t0_nodes:
                lines.append("**Concepts extracted:**")
                lines.append("")
                for node_entry in t0_nodes:
                    node_id = node_entry["id"]
                    label = node_entry["label"]
                    node_type = node_entry.get("node_type", "unknown")
                    full_node = nodes_by_id.get(node_id, {})
                    quotes = full_node.get("source_quotes") or []
                    type_str = _node_type_label(node_type)
                    lines.append(f"- **{label}** *({type_str})*")
                    for q in quotes:
                        lines.append(f'  - *"{q}"*')
                lines.append("")
            else:
                lines.append("*No concepts extracted from opening answer.*")
                lines.append("")
            continue

        # Turn header with strategy
        lines.append(f"### Turn {n} — Strategy: `{strategy}`")
        lines.append("")

        # Question block
        lines.append("#### Question")
        lines.append("")
        lines.append(f"> {question}")
        lines.append("")

        # Focus node block (turns 1+)
        if focus_node_label and focus_node_id:
            node_data = nodes_by_id.get(focus_node_id, {})
            node_type = node_data.get("node_type", "unknown")
            explainer = _find_focus_node_in_question(question, focus_node_label)
            lines.append("**Focus node:**")
            lines.append("")
            lines.append(
                f"- **Label:** {focus_node_label} *(type: {_node_type_label(node_type)})*"
            )
            lines.append(f"- **In question:** {explainer}")
            # Show the first source quote for context
            source_quotes = node_data.get("source_quotes") or []
            if source_quotes:
                first_quote = source_quotes[0]
                lines.append(f'- **First introduced:** "{first_quote}"')
        else:
            lines.append("**Focus node:** *not recorded (pre-fix run)*")
        lines.append("")

        # Answer block
        lines.append("#### Answer")
        lines.append("")
        lines.append(f"> {response}")
        lines.append("")

        # Concepts extracted
        if nodes_added:
            lines.append("**Concepts extracted:**")
            lines.append("")
            for node_entry in nodes_added:
                node_id = node_entry["id"]
                label = node_entry["label"]
                node_type = node_entry.get("node_type", "unknown")
                # Get source quotes from full graph
                full_node = nodes_by_id.get(node_id, {})
                quotes = full_node.get("source_quotes") or []
                type_str = _node_type_label(node_type)
                lines.append(f"- **{label}** *({type_str})*")
                for q in quotes:
                    lines.append(f'  - *"{q}"*')
            lines.append("")
        else:
            lines.append("*No new concepts extracted this turn.*")
            lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path


def _find_most_recent_json() -> Path:
    candidates = sorted(
        Path("synthetic_interviews").glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No JSON files found in synthetic_interviews/")
    return candidates[0]


def main() -> None:
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
    else:
        json_path = _find_most_recent_json()
        print(f"No path given — using most recent: {json_path}")

    if not json_path.exists():
        print(f"Error: file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    out_path = generate_transcript(json_path)
    print(f"Transcript saved to: {out_path}")


if __name__ == "__main__":
    main()
