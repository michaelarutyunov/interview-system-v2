"""Generate per-turn diagnostics report for edge extraction observability.

Queries kg_nodes, kg_edges, kg_rejected_edges, scoring_history, and utterances
to produce a turn-by-turn markdown report with node/edge/rejection details.

Output: reports/interviews/<timestamp>/05_turn_diagnostics.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

import aiosqlite


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate per-turn diagnostics report")
    p.add_argument(
        "--session-id", required=True, help="Session ID to generate report for"
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: reports/interviews/<timestamp>)",
    )
    return p.parse_args()


async def main() -> None:
    args = _parse_args()
    session_id = args.session_id
    db_path = os.environ.get("DATABASE_PATH", "data/interview.db")

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # --- Session metadata ---
        cursor = await db.execute(
            "SELECT methodology, concept_name, config FROM sessions WHERE id = ?",
            (session_id,),
        )
        session_row = await cursor.fetchone()
        if not session_row:
            print(f"Session {session_id} not found")
            return
        methodology = session_row["methodology"]
        concept = session_row["concept_name"]
        config = json.loads(session_row["config"])
        total_turns = config.get("max_turns", 0)

        # --- Nodes by turn ---
        cursor = await db.execute(
            """SELECT id, label, node_type, source_utterance_ids, recorded_at
               FROM kg_nodes WHERE session_id = ? ORDER BY recorded_at""",
            (session_id,),
        )
        nodes = await cursor.fetchall()
        nodes_by_turn: dict[int, list[dict]] = defaultdict(list)
        for row in nodes:
            source_ids = json.loads(row["source_utterance_ids"])
            cursor2 = await db.execute(
                "SELECT turn_number FROM utterances WHERE id = ? AND session_id = ?",
                (source_ids[0], session_id) if source_ids else ("", session_id),
            )
            utt_row = await cursor2.fetchone()
            turn = utt_row["turn_number"] if utt_row else 0
            nodes_by_turn[turn].append(
                {
                    "id": row["id"],
                    "label": row["label"],
                    "node_type": row["node_type"],
                }
            )

        # --- Edges by confirmation turn (stored in properties.turn_number) ---
        cursor = await db.execute(
            """SELECT id, source_node_id, target_node_id, edge_type, confidence,
                      properties
               FROM kg_edges WHERE session_id = ? ORDER BY recorded_at""",
            (session_id,),
        )
        edges = await cursor.fetchall()
        edges_by_turn: dict[int, list[dict]] = defaultdict(list)
        for row in edges:
            props = json.loads(row["properties"]) if row["properties"] else {}
            turn = props.get("turn_number", 0)
            edges_by_turn[turn].append(
                {
                    "id": row["id"],
                    "source_node_id": row["source_node_id"],
                    "target_node_id": row["target_node_id"],
                    "edge_type": row["edge_type"],
                    "confidence": row["confidence"],
                    "assertion": props.get("assertion", ""),
                    "direction": props.get("direction", ""),
                    "frame": props.get("frame", ""),
                }
            )

        # --- Node label + turn lookup ---
        node_labels: dict[str, str] = {}
        node_types: dict[str, str] = {}
        node_turns: dict[str, int] = {}
        for turn, nd_list in nodes_by_turn.items():
            for nd in nd_list:
                node_labels[nd["id"]] = nd["label"]
                node_types[nd["id"]] = nd["node_type"]
                node_turns[nd["id"]] = turn

        # --- Rejected edges ---
        try:
            cursor = await db.execute(
                """SELECT turn_number, source_node_id, target_node_id,
                          rejection_reason, reasoning_summary
                   FROM kg_rejected_edges WHERE session_id = ?
                   ORDER BY turn_number, recorded_at""",
                (session_id,),
            )
            rejected_rows = await cursor.fetchall()
        except Exception:
            rejected_rows = []
        rejected_by_turn: dict[int, list[dict]] = defaultdict(list)
        for row in rejected_rows:
            rejected_by_turn[row["turn_number"]].append(
                {
                    "source_node_id": row["source_node_id"],
                    "target_node_id": row["target_node_id"],
                    "rejection_reason": row["rejection_reason"],
                    "reasoning_summary": row["reasoning_summary"],
                }
            )

        # --- Strategy per turn ---
        cursor = await db.execute(
            """SELECT turn_number, strategy_selected
               FROM scoring_history WHERE session_id = ?
               ORDER BY turn_number""",
            (session_id,),
        )
        strategy_rows = await cursor.fetchall()
        strategy_by_turn: dict[int, str] = {
            r["turn_number"]: r["strategy_selected"] for r in strategy_rows
        }

        # --- Utterances for context ---
        cursor = await db.execute(
            """SELECT turn_number, speaker, text FROM utterances
               WHERE session_id = ? ORDER BY turn_number, speaker""",
            (session_id,),
        )
        utterances = await cursor.fetchall()

    # --- Generate markdown ---
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or f"reports/interviews/{ts}"
    os.makedirs(out_dir, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Turn Diagnostics — {ts}")
    lines.append("")
    lines.append(f"- **Session**: `{session_id}`")
    lines.append(f"- **Methodology**: `{methodology}`")
    lines.append(f"- **Concept**: {concept}")
    lines.append(f"- **Total turns**: {total_turns}")
    lines.append("")

    max_turn = max(
        [t for t in nodes_by_turn if nodes_by_turn[t]]
        + [t for t in edges_by_turn if edges_by_turn[t]]
        + [t for t in rejected_by_turn if rejected_by_turn[t]]
        + list(strategy_by_turn.keys()),
        default=0,
    )

    for turn in range(max_turn + 1):
        strategy = strategy_by_turn.get(turn, "—")
        lines.append(f"## Turn {turn} — {strategy}")
        lines.append("")

        # Utterance context: show system Q at this turn and user response
        # (which is at turn+1 for the opening question at turn 0)
        turn_utts = [u for u in utterances if u["turn_number"] == turn]
        for u in turn_utts:
            text_preview = u["text"][:200].replace("\n", " ")
            lines.append(f"> **{u['speaker']}**: {text_preview}...")
        # Show user response: either at this turn (turns 1+) or at turn+1 (turn 0)
        if turn == 0:
            next_utts = [
                u
                for u in utterances
                if u["turn_number"] == 1 and u["speaker"] == "user"
            ]
            for u in next_utts:
                text_preview = u["text"][:200].replace("\n", " ")
                lines.append(f"> **{u['speaker']}**: {text_preview}...")
        if turn_utts or (turn == 0):
            lines.append("")

        # Nodes
        turn_nodes = nodes_by_turn.get(turn, [])
        if turn_nodes:
            lines.append(f"### Nodes extracted ({len(turn_nodes)})")
            lines.append("")
            lines.append("| ID | Label | Type |")
            lines.append("|----|-------|------|")
            for n in turn_nodes:
                nid = n["id"][:12]
                label = n["label"][:80]
                ntype = n["node_type"]
                lines.append(f"| `{nid}` | {label} | `{ntype}` |")
            lines.append("")

        # Edges confirmed
        turn_edges = edges_by_turn.get(turn, [])
        if turn_edges:
            lines.append(f"### Edges confirmed ({len(turn_edges)})")
            lines.append("")
            lines.append(
                "| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |"
            )
            lines.append(
                "|--------|---|----|--------|---|------|------|-----------|-----------|-------|"
            )
            for e in turn_edges:
                src = node_labels.get(e["source_node_id"], e["source_node_id"][:12])
                tgt = node_labels.get(e["target_node_id"], e["target_node_id"][:12])
                src_t = node_turns.get(e["source_node_id"], "?")
                tgt_t = node_turns.get(e["target_node_id"], "?")
                lines.append(
                    f"| {src[:35]} | t={src_t} | → | {tgt[:35]} | t={tgt_t} | "
                    f"`{e['edge_type']}` | {e['confidence']:.1f} | "
                    f"{e['assertion']} | {e['direction']} | {e['frame']} |"
                )
            lines.append("")

        # Rejected
        turn_rejected = rejected_by_turn.get(turn, [])
        if turn_rejected:
            # Count by reason
            reason_counts: dict[str, int] = defaultdict(int)
            for r in turn_rejected:
                reason_counts[r["rejection_reason"]] += 1
            lines.append(f"### Rejected candidates ({len(turn_rejected)})")
            lines.append("")
            lines.append("| Reason | Count |")
            lines.append("|--------|-------|")
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| `{reason}` | {count} |")
            lines.append("")

            # Detailed table
            lines.append("<details>")
            lines.append("<summary>Per-pair details</summary>")
            lines.append("")
            lines.append("| Source | → | Target | Reason | Reasoning |")
            lines.append("|--------|---|--------|--------|-----------|")
            for r in turn_rejected:
                src = node_labels.get(r["source_node_id"], r["source_node_id"][:12])
                tgt = node_labels.get(r["target_node_id"], r["target_node_id"][:12])
                reasoning = (
                    r["reasoning_summary"][:120] if r["reasoning_summary"] else "—"
                )
                lines.append(
                    f"| {src[:40]} | → | {tgt[:40]} | `{r['rejection_reason']}` | {reasoning} |"
                )
            lines.append("")
            lines.append("</details>")
            lines.append("")

    out_path = os.path.join(out_dir, "05_turn_diagnostics.md")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Written {out_path} ({len(lines)} lines)")


if __name__ == "__main__":
    asyncio.run(main())
