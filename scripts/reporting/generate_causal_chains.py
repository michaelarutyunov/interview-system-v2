#!/usr/bin/env python3
"""Extract causal chains from a simulated interview JSON.

Validates that the interview produces meaningful causal structure by extracting
chains from the saved graph and classifying them against the methodology's schema.

Usage:
    python scripts/reporting/generate_causal_chains.py synthetic_interviews/<file>.json
    python scripts/reporting/generate_causal_chains.py <json> --output <path>
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Analytical overrides: methodology name -> list of [src, tgt] conforming pairs.
# Entries added only when a methodology's YAML has no permitted_connections.
ANALYTICAL_OVERRIDES: dict[str, list[list[str]]] = {}


def _build_utterance_turn_map(data: dict) -> dict[str, int]:
    """Map utterance IDs to turn numbers via quote-in-response matching.

    Each node carries source_quotes and source_utterance_ids.
    Match the first quote against each turn's response text.
    """
    utt_to_turn: dict[str, int] = {}
    turns = data["turns"]
    for node in data["graph"]["nodes"]:
        quotes = node.get("source_quotes", []) or []
        utt_ids = node.get("source_utterance_ids", []) or []
        if not quotes or not utt_ids:
            continue
        q = quotes[0]
        for turn in turns:
            resp = turn.get("response", "") or ""
            if q and q in resp:
                for uid in utt_ids:
                    utt_to_turn[uid] = turn["turn_number"]
                break
    return utt_to_turn


def _map_canonical_slots(data: dict) -> tuple[list[dict], dict]:
    """Build canonical node representations from slots, mapping utterances via surface nodes."""
    surface_by_id = {n["id"]: n for n in data["graph"]["nodes"]}
    canon_nodes: list[dict] = []
    for slot in data["canonical_graph"]["slots"]:
        all_utt_ids: list[str] = []
        all_quotes: list[str] = []
        for snid in slot.get("surface_node_ids", []):
            snode = surface_by_id.get(snid)
            if snode:
                all_utt_ids.extend(snode.get("source_utterance_ids", []) or [])
                all_quotes.extend(snode.get("source_quotes", []) or [])
        canon_nodes.append(
            {
                "id": slot["slot_id"],
                "label": slot["slot_name"],
                "node_type": slot["node_type"],
                "source_utterance_ids": all_utt_ids,
                "source_quotes": all_quotes[:5],
            }
        )
    canon_by_id = {n["id"]: n for n in canon_nodes}
    return canon_nodes, canon_by_id


def _check_coverage(data: dict, utt_to_turn: dict) -> None:
    """Warn if utterance coverage is incomplete."""
    all_utts: set[str] = set()
    for n in data["graph"]["nodes"]:
        for u in n.get("source_utterance_ids", []) or []:
            all_utts.add(u)
    missing = all_utts - set(utt_to_turn)
    if missing:
        print(
            f"WARNING: {len(missing)}/{len(all_utts)} utterances unmapped to turns. "
            "Turn numbers will be marked as '?' for affected edges.",
            file=sys.stderr,
        )


def _edge_min_turn(edge: dict, utt_to_turn: dict) -> int | None:
    turns_seen = [
        utt_to_turn[u] for u in edge.get("source_utterance_ids", []) if u in utt_to_turn
    ]
    return min(turns_seen) if turns_seen else None


def _walk_chains(
    edges: list[dict],
    node_by_id: dict[str, dict],
    edge_type: str = "leads_to",
) -> list[tuple[list[str], list[dict]]]:
    """Return maximal paths of length >= 2 over edges of given type.

    Filters superseded nodes. Never traverses revises.
    Maximal = drop any path that is a strict prefix of another.
    """
    active_nodes = {
        nid: n for nid, n in node_by_id.items() if not n.get("superseded_by")
    }
    adj: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for e in edges:
        if e["edge_type"] != edge_type:
            continue
        s, t = e["source_node_id"], e["target_node_id"]
        if s not in active_nodes or t not in active_nodes:
            continue
        adj[s].append((t, e))

    incoming: dict[str, int] = defaultdict(int)
    for s, outs in adj.items():
        for t, _ in outs:
            incoming[t] += 1
    roots = [nid for nid in active_nodes if incoming[nid] == 0 and nid in adj]

    all_paths: list[tuple[list[str], list[dict]]] = []

    def dfs(node_id: str, path_nodes: list[str], path_edges: list[dict]) -> None:
        if node_id not in adj or not adj[node_id]:
            if len(path_nodes) >= 2:
                all_paths.append((path_nodes[:], path_edges[:]))
            return
        extended = False
        for nxt, edge in adj[node_id]:
            if nxt in path_nodes:
                continue
            extended = True
            dfs(nxt, path_nodes + [nxt], path_edges + [edge])
        if not extended and len(path_nodes) >= 2:
            all_paths.append((path_nodes[:], path_edges[:]))

    for r in roots:
        dfs(r, [r], [])

    # Maximal filter
    all_paths.sort(key=lambda p: -len(p[0]))
    maximal: list[tuple[list[str], list[dict]]] = []
    seen_sequences: set[tuple[str, ...]] = set()
    for nodes_p, edges_p in all_paths:
        key = tuple(nodes_p)
        is_prefix = any(
            len(key) < len(other) and other[: len(key)] == key
            for other in seen_sequences
        )
        if not is_prefix:
            maximal.append((nodes_p, edges_p))
            seen_sequences.add(key)
    return maximal


def _classify_chain(
    path_nodes: list[str],
    node_by_id: dict[str, dict],
    node_levels: dict[str, int],
    full_chain_levels: list[int],
    max_terminal_level: int,
) -> str:
    """Return tier: full, advanced, developing, started, lateral, other."""
    types = [node_by_id[nid]["node_type"] for nid in path_nodes]
    levels = [node_levels.get(t, 0) for t in types]

    if len(set(types)) == 1:
        return "lateral"

    if levels == list(range(min(full_chain_levels), max_terminal_level + 1)):
        return "full"

    max_level = max(levels)
    if max_level >= 4:
        return "advanced"
    if max_level == 3:
        return "developing"
    if max_level == 2:
        return "started"
    return "other"


def _render_chain(
    path_nodes: list[str],
    path_edges: list[dict],
    node_by_id: dict[str, dict],
    utt_to_turn: dict,
    prefix: str = "",
) -> str:
    def _node_turn(i: int) -> int | None:
        # N nodes have N-1 edges; last node inherits last edge's turn
        edge = path_edges[i] if i < len(path_edges) else path_edges[-1]
        return _edge_min_turn(edge, utt_to_turn)

    parts = [
        " → ".join(
            f"`{node_by_id[nid]['label']}` ({node_by_id[nid]['node_type']}, "
            f"t={_node_turn(i) or '?'})"
            for i, nid in enumerate(path_nodes)
        )
    ]
    lines = [f"### Chain{prefix}", f"**Path**: {parts[0]}", ""]
    lines.append("**Evidence**:")
    for e in path_edges:
        src = node_by_id[e["source_node_id"]]
        tgt = node_by_id[e["target_node_id"]]
        t = _edge_min_turn(e, utt_to_turn)
        quotes = e.get("source_quotes", []) or []
        quote = quotes[0] if quotes else "(no quote)"
        lines.append(f'- `{src["label"]} → {tgt["label"]}` (t={t or "?"}): _"{quote}"_')
    lines.append("")
    return "\n".join(lines)


def generate_causal_chains(
    json_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Generate causal chain extraction markdown from simulation JSON.

    Args:
        json_path: Path to simulation JSON.
        output_path: Optional explicit output path.

    Returns:
        Path to written markdown file.
    """
    data = json.loads(json_path.read_text())
    for key in ("metadata", "graph", "canonical_graph", "turns"):
        if key not in data:
            raise ValueError(f"Malformed JSON: missing '{key}'")

    meta = data["metadata"]
    methodology = meta["methodology"]

    meth_path = Path(f"config/methodologies/{methodology}.yaml")
    if not meth_path.exists():
        raise FileNotFoundError(f"Methodology YAML not found: {meth_path}")

    meth = yaml.safe_load(meth_path.read_text())
    ontology = meth.get("ontology", {})

    node_levels = {n["name"]: n.get("level", 0) for n in ontology.get("nodes", [])}
    terminal_levels = {
        n["name"]: n.get("terminal", False) for n in ontology.get("nodes", [])
    }

    edge_rules = {}
    for e in ontology.get("edges", []):
        edge_rules[e["name"]] = e.get("permitted_connections", [])

    # Resolve constraints
    constraint_source = "yaml"
    leads_to_rules = edge_rules.get("leads_to", [])
    if methodology in ANALYTICAL_OVERRIDES:
        leads_to_rules = ANALYTICAL_OVERRIDES[methodology]
        constraint_source = "analytical_override"
    has_constraints = bool(leads_to_rules) and leads_to_rules != [["*", "*"]]

    sorted_types = [t for t, _ in sorted(node_levels.items(), key=lambda x: x[1])]
    full_chain_levels = sorted(set(node_levels.values()) - {0})
    full_chain_types = [
        t for t in sorted_types if node_levels.get(t, 0) in full_chain_levels
    ]
    max_terminal_level = max(
        (node_levels[t] for t in terminal_levels if terminal_levels[t]),
        default=max(full_chain_levels, default=0),
    )

    # Build utterance maps
    utt_to_turn = _build_utterance_turn_map(data)
    _check_coverage(data, utt_to_turn)

    # Prepare graph data
    surface_nodes = data["graph"]["nodes"]
    surface_edges = data["graph"]["edges"]
    surface_by_id = {n["id"]: n for n in surface_nodes}

    canon_nodes, canon_by_id = _map_canonical_slots(data)

    canon_edges = []
    for e in data["canonical_graph"]["edges"]:
        ce = dict(e)
        ce["source_node_id"] = ce.pop("source_slot_id", e.get("source_node_id"))
        ce["target_node_id"] = ce.pop("target_slot_id", e.get("target_node_id"))
        canon_edges.append(ce)

    # Walk chains
    surf_paths = _walk_chains(surface_edges, surface_by_id)
    can_paths = _walk_chains(canon_edges, canon_by_id)

    # Classify
    surf_by_tier: dict[str, list] = defaultdict(list)
    for path_nodes, path_edges in surf_paths:
        tier = _classify_chain(
            path_nodes,
            surface_by_id,
            node_levels,
            full_chain_levels,
            max_terminal_level,
        )
        if tier != "lateral":
            surf_by_tier[tier].append((path_nodes, path_edges))

    can_by_tier: dict[str, list] = defaultdict(list)
    for path_nodes, path_edges in can_paths:
        tier = _classify_chain(
            path_nodes, canon_by_id, node_levels, full_chain_levels, max_terminal_level
        )
        if tier != "lateral":
            can_by_tier[tier].append((path_nodes, path_edges))

    # Stats
    superseded_count = sum(1 for n in surface_nodes if n.get("superseded_by"))
    rev_count_surface = sum(1 for e in surface_edges if e["edge_type"] == "revises")
    rev_count_canon = sum(1 for e in canon_edges if e["edge_type"] == "revises")
    surf_leads_to = sum(1 for e in surface_edges if e["edge_type"] == "leads_to")
    can_leads_to = sum(1 for e in canon_edges if e["edge_type"] == "leads_to")
    surf_node_types = sorted(set(n["node_type"] for n in surface_nodes))
    can_node_types = sorted(
        set(s["node_type"] for s in data["canonical_graph"]["slots"])
    )

    # Orphans
    surf_involved = set()
    for e in surface_edges:
        if e["edge_type"] == "leads_to":
            surf_involved.add(e["source_node_id"])
            surf_involved.add(e["target_node_id"])
    surf_orphans = [
        n
        for n in surface_nodes
        if n["id"] not in surf_involved and not n.get("superseded_by")
    ]

    # Revisions
    revisions = []
    surf_by_id_all = {n["id"]: n for n in surface_nodes}
    for e in surface_edges:
        if e["edge_type"] == "revises":
            old = surf_by_id_all.get(e["source_node_id"])
            new = surf_by_id_all.get(e["target_node_id"])
            if old and new:
                revisions.append((old, new))

    # Build markdown
    if output_path:
        out_path = output_path
    else:
        out_path = Path(f"reports/causal_chains/{json_path.stem}_causal_chains.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    md = f"""# Causal Chain Extraction — {json_path.name}

## Source specs
- **Session ID**: {meta.get("session_id", "N/A")}
- **Concept**: {meta.get("concept_name", "N/A")} (`{meta.get("concept_id", "N/A")}`)
- **Methodology**: `{methodology}`
- **Persona**: {meta.get("persona_name", "N/A")} (`{meta.get("persona_id", "N/A")}`)
- **Total turns**: {meta.get("total_turns", "N/A")}
- **Status**: {meta.get("status", "N/A")}
- **Saved at**: {meta.get("saved_at", "N/A")}

## Extraction config
- **Constraint source**: {constraint_source}
- **Permitted connections** (leads_to):
"""
    if has_constraints:
        for pair in leads_to_rules:
            md += f"  - {pair[0]} → {pair[1]}\n"
    else:
        md += "  - (permissive only — no constraints defined)\n"

    md += f"""- **Superseded nodes excluded**: {superseded_count}
- **Revises edges excluded from traversal**: {rev_count_surface + rev_count_canon} ({rev_count_surface} surface, {rev_count_canon} canonical)

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | {len(surface_nodes)} | {len(canon_nodes)} |
| Edges (leads_to) | {surf_leads_to} | {can_leads_to} |
| Edges (revises) | {rev_count_surface} | {rev_count_canon} |
| Node types | {", ".join(surf_node_types)} | {", ".join(can_node_types)} |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|-----------------|
| Full | {" → ".join(full_chain_types)} | {len(surf_by_tier.get("full", []))} | {len(can_by_tier.get("full", []))} |
| Advanced | Reaches instrumental_value or terminal_value, but incomplete | {len(surf_by_tier.get("advanced", []))} | {len(can_by_tier.get("advanced", []))} |
| Developing | Reaches psychosocial_consequence but not values | {len(surf_by_tier.get("developing", []))} | {len(can_by_tier.get("developing", []))} |
| Started | attribute → functional_consequence only | {len(surf_by_tier.get("started", []))} | {len(can_by_tier.get("started", []))} |
| Lateral (excluded) | Same-type only chains | {len(surf_paths) - sum(len(v) for v in surf_by_tier.values())} | {len(can_paths) - sum(len(v) for v in can_by_tier.values())} |

---

## Full chains — complete laddering
"""
    for i, (pn, pe) in enumerate(surf_by_tier.get("full", []), 1):
        md += _render_chain(pn, pe, surface_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [surface]"
        )
    for i, (pn, pe) in enumerate(can_by_tier.get("full", []), 1):
        md += _render_chain(pn, pe, canon_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [canonical]"
        )
    if not surf_by_tier.get("full") and not can_by_tier.get("full"):
        md += "_No full chains found._\n\n"

    md += "## Advanced chains — value-reaching but incomplete\n\n"
    for i, (pn, pe) in enumerate(surf_by_tier.get("advanced", []), 1):
        md += _render_chain(pn, pe, surface_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [surface]"
        )
    for i, (pn, pe) in enumerate(can_by_tier.get("advanced", []), 1):
        md += _render_chain(pn, pe, canon_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [canonical]"
        )
    if not surf_by_tier.get("advanced") and not can_by_tier.get("advanced"):
        md += "_No advanced chains found._\n\n"

    md += "## Developing chains — consequence-level progression\n\n"
    for i, (pn, pe) in enumerate(surf_by_tier.get("developing", []), 1):
        md += _render_chain(pn, pe, surface_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [surface]"
        )
    for i, (pn, pe) in enumerate(can_by_tier.get("developing", []), 1):
        md += _render_chain(pn, pe, canon_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [canonical]"
        )
    if not surf_by_tier.get("developing") and not can_by_tier.get("developing"):
        md += "_No developing chains found._\n\n"

    md += "## Started chains — attribute-to-functional only\n\n"
    for i, (pn, pe) in enumerate(surf_by_tier.get("started", []), 1):
        md += _render_chain(pn, pe, surface_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [surface]"
        )
    for i, (pn, pe) in enumerate(can_by_tier.get("started", []), 1):
        md += _render_chain(pn, pe, canon_by_id, utt_to_turn).replace(
            "### Chain", f"### Chain {i} [canonical]"
        )
    if not surf_by_tier.get("started") and not can_by_tier.get("started"):
        md += "_No started chains found._\n\n"

    md += "## Revisions (positive validation signal)\n\n"
    if revisions:
        for old, new in revisions:
            md += f"- `{old['label']}` → `{new['label']}`.\n"
            old_q = (old.get("source_quotes") or ["(no quote)"])[0]
            new_q = (new.get("source_quotes") or ["(no quote)"])[0]
            md += f'  - Original: _"{old_q}"_\n'
            md += f'  - Revision: _"{new_q}"_\n'
    else:
        md += "_No revisions found._\n\n"

    md += "## Orphan nodes (no incoming or outgoing leads_to edges)\n\n"
    if surf_orphans:
        for n in surf_orphans:
            q = (n.get("source_quotes") or ["(no quote)"])[0]
            md += f'- `{n["label"]}` ({n["node_type"]}) — _"{q}"_\n'
    else:
        md += "_No orphan nodes found._\n\n"

    md += f"""\n## Retracted chains (dropped due to supersession)
- **Count**: {superseded_count}
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Constraints from: `{constraint_source}`
- Overrides applied: {"yes" if methodology in ANALYTICAL_OVERRIDES else "no"}
- Known limitations: Canonical slot layer may hide language variation relevant to laddering validity.
"""

    out_path.write_text(md)
    print(f"Wrote {out_path}")
    for tier in ("full", "advanced", "developing", "started"):
        print(
            f"{tier}: surface={len(surf_by_tier.get(tier, []))}, "
            f"canonical={len(can_by_tier.get(tier, []))}"
        )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract causal chains from a simulated interview JSON."
    )
    parser.add_argument("json_file", type=Path, help="Path to simulation JSON")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output markdown path (optional)"
    )
    args = parser.parse_args()

    if not args.json_file.exists():
        print(f"File not found: {args.json_file}", file=sys.stderr)
        sys.exit(1)

    out = generate_causal_chains(args.json_file, args.output)
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
