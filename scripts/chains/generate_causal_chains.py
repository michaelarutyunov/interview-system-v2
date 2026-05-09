#!/usr/bin/env python3
"""Extract causal chains from a simulated interview JSON.

Validates that the interview produces meaningful causal structure by extracting
chains from the saved graph and classifying them against the methodology's schema.

Chain construction rules are loaded from config/chain_rules/<methodology>.yaml.
Each file specifies which edge types constitute narrative progression and optional
permitted node-type pairs per edge. Falls back to leads_to (unconstrained) when
no chain_rules file exists.

Usage:
    python scripts/chains/generate_causal_chains.py synthetic_interviews/<file>.json
    python scripts/chains/generate_causal_chains.py <json> -o report.md
    python scripts/chains/generate_causal_chains.py <json> --append existing.md
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from scripts.chains._chain_common import (
    _check_coverage,
    _classify_chain,
    _derive_tiers,
    _edge_min_turn,
    _load_chain_rules,
    _map_canonical_slots,
    _node_min_turn,
    _tier_descriptions,
    _walk_chains,
    _build_utterance_turn_map,
)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_chain(
    path_nodes: list[str],
    path_edges: list[dict],
    node_by_id: dict[str, dict],
    utt_to_turn: dict,
    node_levels: dict[str, int],
    chain_num: int = 0,
) -> str:
    def _node_level(node_type: str) -> str:
        lvl = node_levels.get(node_type)
        return f"L{lvl}" if lvl is not None else "?"

    path_steps = []
    for nid in path_nodes:
        node = node_by_id[nid]
        nt = node["node_type"]
        t = _node_min_turn(node, utt_to_turn)
        path_steps.append(
            f"`{node['label']}` ({nt}, {_node_level(nt)}, t={t if t is not None else '?'})"
        )
    lines = [
        f"### Chain {chain_num}",
        "**Path**:",
        "",
        "  → " + "  \n  → ".join(path_steps) + "  ",
        "",
    ]
    lines.append("**Evidence**:")
    for e in path_edges:
        src = node_by_id[e["source_node_id"]]
        tgt = node_by_id[e["target_node_id"]]
        quotes = e.get("source_quotes", []) or []
        if not quotes:
            quotes = (src.get("source_quotes", []) or []) + (
                tgt.get("source_quotes", []) or []
            )
        quote = quotes[0] if quotes else "(no quote)"
        # Determine turn from the same source as the quote
        t = _edge_min_turn(e, utt_to_turn)
        if not e.get("source_quotes"):
            # Quote fell back to node — use that node's turn
            src_quotes = src.get("source_quotes", []) or []
            if quote in src_quotes:
                node_t = _node_min_turn(src, utt_to_turn)
                if node_t is not None:
                    t = node_t
            else:
                tgt_quotes = tgt.get("source_quotes", []) or []
                if quote in tgt_quotes:
                    node_t = _node_min_turn(tgt, utt_to_turn)
                    if node_t is not None:
                        t = node_t
        reversed_mark = " (reversed)" if e.get("_reversed") else ""
        lines.append(
            f'- `{src["label"]} → {tgt["label"]}` [{e["edge_type"]}{reversed_mark}] (t={t if t is not None else "?"}): _"{quote}"_'
        )
    lines.append("\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_causal_chains(json_path: Path) -> str:
    """Generate causal chain extraction markdown from simulation JSON.

    Returns the full markdown string. Stats are printed to stderr.
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

    # Tier derivation — methodology-agnostic
    sorted_levels_desc, max_level, num_tiers = _derive_tiers(node_levels)
    tier_descs = (
        _tier_descriptions(node_levels, sorted_levels_desc, num_tiers)
        if num_tiers
        else {}
    )

    # Chain construction rules
    chain_rules, chain_filters = _load_chain_rules(methodology)
    chain_rules_source = (
        f"config/chain_rules/{methodology}.yaml"
        if Path(f"config/chain_rules/{methodology}.yaml").exists()
        else "fallback (leads_to unconstrained)"
    )

    # Utterance mapping
    utt_to_turn = _build_utterance_turn_map(data)
    _check_coverage(data, utt_to_turn)

    # Graph data
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

    # Walk and classify chains
    if num_tiers == 0:
        surf_paths = can_paths = []
        no_levels_note = True
    else:
        surf_paths = _walk_chains(
            surface_edges, surface_by_id, chain_rules, node_levels, chain_filters
        )
        can_paths = _walk_chains(
            canon_edges, canon_by_id, chain_rules, node_levels, chain_filters
        )
        no_levels_note = False

    surf_by_tier: dict[str, list] = defaultdict(list)
    can_by_tier: dict[str, list] = defaultdict(list)

    for path_nodes, path_edges in surf_paths:
        tier = _classify_chain(
            path_nodes,
            surface_by_id,
            node_levels,
            sorted_levels_desc,
            num_tiers,
            max_level,
        )
        if tier != "lateral":
            surf_by_tier[tier].append((path_nodes, path_edges))

    for path_nodes, path_edges in can_paths:
        tier = _classify_chain(
            path_nodes,
            canon_by_id,
            node_levels,
            sorted_levels_desc,
            num_tiers,
            max_level,
        )
        if tier != "lateral":
            can_by_tier[tier].append((path_nodes, path_edges))

    # Stats
    superseded_count = sum(1 for n in surface_nodes if n.get("superseded_by"))
    rev_count_surface = sum(1 for e in surface_edges if e["edge_type"] == "revises")
    rev_count_canon = sum(1 for e in canon_edges if e["edge_type"] == "revises")
    chain_edge_types = list(chain_rules.keys())
    surf_chain_edges = sum(1 for e in surface_edges if e["edge_type"] in chain_rules)

    surf_involved = set()
    for e in surface_edges:
        if e["edge_type"] in chain_rules:
            surf_involved.add(e["source_node_id"])
            surf_involved.add(e["target_node_id"])
    surf_orphans = [
        n
        for n in surface_nodes
        if n["id"] not in surf_involved and not n.get("superseded_by")
    ]

    revisions = []
    for e in surface_edges:
        if e["edge_type"] == "revises":
            old = surface_by_id.get(e["source_node_id"])
            new = surface_by_id.get(e["target_node_id"])
            if old and new:
                revisions.append((old, new))

    # Build markdown
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
- **Chain rules source**: `{chain_rules_source}`
- **Chain edge types**: {", ".join(chain_edge_types)}
- **Permitted connections**:
"""
    for edge_name, rule in chain_rules.items():
        if rule is None or rule == "unconstrained":
            md += f"  - `{edge_name}`: unconstrained\n"
        elif isinstance(rule, list):
            md += f"  - `{edge_name}`: {len(rule)} permitted pairs (legacy type-pair)\n"
        else:
            md += f"  - `{edge_name}`: {rule}\n"

    md += f"""- **Superseded nodes excluded**: {superseded_count}
- **Revises edges excluded from traversal**: {rev_count_surface + rev_count_canon}

## Graph summary
- **Conversation nodes**: {len(surface_nodes)}
- **Themes (canonical slots)**: {len(canon_nodes)}
- **Chain edges traversed**: {surf_chain_edges}
- **Edges (revises)**: {rev_count_surface}

"""

    if no_levels_note:
        md += "_This methodology has no level structure defined — chain tier classification not applicable._\n\n"
    else:
        active_tiers = [
            t for t in ["full", "advanced", "developing"] if t in tier_descs
        ]
        md += "## Chain completeness summary\n"
        md += "| Tier | Description | Count |\n"
        md += "|------|-------------|-------|\n"
        for tier in active_tiers:
            md += (
                f"| {tier.capitalize()} | {tier_descs[tier]} "
                f"| {len(surf_by_tier.get(tier, []))} |\n"
            )
        lateral_surf = len(surf_paths) - sum(len(v) for v in surf_by_tier.values())
        md += f"| Lateral (excluded) | Same-type only chains | {lateral_surf} |\n"
        md += "\n---\n\n"

        global_chain_num = 0
        for tier in active_tiers:
            heading = {
                "full": "Full chains — complete, no missing levels",
                "advanced": "Advanced chains — near-complete (one gap) or near-terminal",
                "developing": "Developing chains — mid-level progression",
                "started": "Started — fewer than 3 nodes",
            }[tier]
            md += f"## {heading}\n\n"
            for pn, pe in surf_by_tier.get(tier, []):
                global_chain_num += 1
                md += _render_chain(
                    pn,
                    pe,
                    surface_by_id,
                    utt_to_turn,
                    node_levels,
                    chain_num=global_chain_num,
                )
            for pn, pe in can_by_tier.get(tier, []):
                global_chain_num += 1
                md += _render_chain(
                    pn,
                    pe,
                    canon_by_id,
                    utt_to_turn,
                    node_levels,
                    chain_num=global_chain_num,
                )
            if not surf_by_tier.get(tier) and not can_by_tier.get(tier):
                md += f"_No {tier} chains found._\n\n"

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

    md += "## Orphan nodes (no incoming or outgoing chain edges)\n\n"
    if surf_orphans:
        for n in surf_orphans:
            q = (n.get("source_quotes") or ["(no quote)"])[0]
            nt = n["node_type"]
            lvl = node_levels.get(nt)
            lvl_str = f"L{lvl}" if lvl is not None else "?"
            utt_ids = n.get("source_utterance_ids", []) or []
            t = None
            for uid in utt_ids:
                if uid in utt_to_turn:
                    t = utt_to_turn[uid]
                    break
            t_str = f", t={t}" if t is not None else ""
            md += f'- `{n["label"]}` ({nt}, {lvl_str}{t_str}) — _"{q}"_\n'
    else:
        md += "_No orphan nodes found._\n\n"

    md += f"""\n## Retracted chains (dropped due to supersession)
- **Count**: {superseded_count}
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `{chain_rules_source}`
- Tiers derived from {len(set(node_levels.values()))} distinct ontology levels (num_tiers={num_tiers})
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
"""

    # Stats to stderr
    for tier in ["full", "advanced", "developing", "started"]:
        print(
            f"{tier}: surface={len(surf_by_tier.get(tier, []))}, "
            f"canonical={len(can_by_tier.get(tier, []))}",
            file=sys.stderr,
        )

    return md


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract causal chains from a simulated interview JSON."
    )
    parser.add_argument("json_file", type=Path, help="Path to simulation JSON")
    parser.add_argument("-o", "--output", type=Path, help="Write to file (overwrite)")
    parser.add_argument("--append", type=Path, help="Append to existing file")
    args = parser.parse_args()

    if not args.json_file.exists():
        print(f"File not found: {args.json_file}", file=sys.stderr)
        sys.exit(1)

    md = generate_causal_chains(args.json_file)

    if args.append:
        args.append.parent.mkdir(parents=True, exist_ok=True)
        with open(args.append, "a") as f:
            f.write(md)
        print(f"Appended to {args.append}", file=sys.stderr)
    elif args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(md)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
