#!/usr/bin/env python3
"""Extract causal chains from a simulated interview JSON.

Validates that the interview produces meaningful causal structure by extracting
chains from the saved graph and classifying them against the methodology's schema.

Chain construction rules are loaded from config/chain_rules/<methodology>.yaml.
Each file specifies which edge types constitute narrative progression and optional
permitted node-type pairs per edge. Falls back to leads_to (unconstrained) when
no chain_rules file exists.

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


# ---------------------------------------------------------------------------
# Chain rules loading
# ---------------------------------------------------------------------------


def _load_chain_rules(methodology: str) -> dict[str, list[list[str]] | str | None]:
    """Load chain construction rules for a methodology.

    Returns mapping of edge_type -> rule.
    Rule formats:
      - None / "unconstrained": all edges of this type pass
      - "upward": src_level < tgt_level
      - "upward_or_lateral": src_level <= tgt_level
      - "reverse": flip direction, include if reversed edge is upward
      - [...] (list): old type-pair allowlist (backward compat)

    Fail-fast: raises FileNotFoundError if no chain_rules YAML exists for the
    methodology, and KeyError if the YAML lacks a `chain_edges` key. Methodologies
    without chain topology (e.g. flat/dimensional ontologies) should not be passed
    to this reporting script — add an explicit rules file or skip the script.
    """
    path = Path(f"config/chain_rules/{methodology}.yaml")
    if not path.exists():
        raise FileNotFoundError(
            f"No chain_rules file for methodology '{methodology}' "
            f"(expected: {path}). Methodologies without chain topology should "
            f"not run through generate_causal_chains.py — add an explicit rules "
            f"file or skip this script for this methodology."
        )
    data = yaml.safe_load(path.read_text())
    if "chain_edges" not in data:
        raise KeyError(
            f"chain_rules file '{path}' is missing required 'chain_edges' key."
        )
    return data["chain_edges"]


# ---------------------------------------------------------------------------
# Tier derivation from ontology level count
# ---------------------------------------------------------------------------


def _derive_tiers(node_levels: dict[str, int]) -> tuple[list[int], int, int]:
    """Derive tier count and level thresholds from the methodology's ontology.

    Returns (sorted_levels_desc, max_level, num_tiers).
    num_tiers = min(4, distinct_level_count) — can't have more tiers than levels.
    """
    distinct = sorted(set(node_levels.values()))
    if not distinct or max(distinct) == 0:
        return [], 0, 0
    sorted_desc = sorted(distinct, reverse=True)
    num_tiers = min(4, len(distinct))
    return sorted_desc, sorted_desc[0], num_tiers


def _classify_chain(
    path_nodes: list[str],
    node_by_id: dict[str, dict],
    node_levels: dict[str, int],
    sorted_levels_desc: list[int],
    num_tiers: int,
    max_level: int,
) -> str:
    """Classify a chain path into a tier.

    Chains require ≥3 nodes (shorter paths are just pairs).
    Tiers:
      full       — ≥3 nodes, reaches Lmax, all levels between min and max present
      advanced   — ≥3 nodes, reaches Lmax with exactly 1 missing intermediate level,
                   OR reaches Lmax-1 (second-highest defined level)
      developing — ≥3 nodes, everything else
      started    — <3 nodes (not a full chain)
      lateral    — all nodes same type
    """
    types = [node_by_id[nid]["node_type"] for nid in path_nodes]
    levels = [node_levels.get(t, 0) for t in types]

    if len(set(types)) == 1:
        return "lateral"

    chain_len = len(path_nodes)
    if chain_len < 3:
        return "started"

    max_l = max(levels)
    if max_l >= max_level:
        # Reaches terminal — check for missing intermediate levels.
        # Use the ontology minimum (0) as the floor, not the chain's own min,
        # so a chain starting at L3 can't be "full" — it must span from low levels.
        onto_min = min(node_levels.values()) if node_levels else 0
        expected = set(range(onto_min, max_l + 1))
        present = set(levels)
        missing = expected - present
        if len(missing) <= 1:
            return "full"
        elif len(missing) <= 2:
            return "advanced"
        else:
            return "developing"

    if num_tiers >= 3 and max_l >= sorted_levels_desc[1]:
        return "advanced"

    return "developing"


def _tier_descriptions(
    node_levels: dict[str, int],
    sorted_levels_desc: list[int],
    num_tiers: int,
) -> dict[str, str]:
    """Build human-readable descriptions for each active tier."""
    types_by_level: dict[int, list[str]] = defaultdict(list)
    for name, level in node_levels.items():
        types_by_level[level].append(name)

    def _names(level: int) -> str:
        return " / ".join(types_by_level.get(level, ["?"]))

    descs: dict[str, str] = {}
    descs["full"] = (
        f"Reaches {_names(sorted_levels_desc[0])} — complete chain, no missing levels"
    )
    if num_tiers >= 3:
        descs["advanced"] = (
            f"Reaches {_names(sorted_levels_desc[0])} (with one gap) or {_names(sorted_levels_desc[1])}"
        )
    if num_tiers >= 4:
        descs["developing"] = "Mid-level progression, terminal not reached"
    descs["started"] = "Incomplete — fewer than 3 nodes"
    return descs


# ---------------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------------


def _build_utterance_turn_map(data: dict) -> dict[str, int]:
    """Map utterance IDs to turn numbers via quote-in-response matching."""
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
    """Build canonical node representations from slots."""
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
    all_utts: set[str] = set()
    for n in data["graph"]["nodes"]:
        for u in n.get("source_utterance_ids", []) or []:
            all_utts.add(u)
    missing = all_utts - set(utt_to_turn)
    if missing:
        print(
            f"WARNING: {len(missing)}/{len(all_utts)} utterances unmapped to turns.",
            file=sys.stderr,
        )


def _edge_passes(
    src_id: str,
    tgt_id: str,
    rule: list[list[str]] | str | None,
    active_nodes: dict[str, dict],
    node_levels: dict[str, int],
) -> tuple[bool, bool]:
    """Check whether an edge passes the chain rule.

    Args:
        src_id, tgt_id: source and target node IDs
        rule: chain rule — None, str direction, or list of type pairs
        active_nodes: node_id → node dict (for node_type lookup)
        node_levels: node_type → ontology level

    Returns:
        (passes, use_reversed) — use_reversed=True means src↔tgt should be swapped
        for traversal and the edge flagged as reversed.
    """
    src_type = active_nodes[src_id]["node_type"]
    tgt_type = active_nodes[tgt_id]["node_type"]
    src_level = node_levels.get(src_type)
    tgt_level = node_levels.get(tgt_type)

    # Old type-pair allowlist (backward compat)
    if isinstance(rule, list):
        return ([src_type, tgt_type] in rule, False)

    # Unconstrained or None
    if rule is None or rule == "unconstrained":
        return (True, False)

    # Reverse: flip direction, include if upward after reversal
    if rule == "reverse":
        if src_level is None or tgt_level is None:
            return (False, False)
        if src_level > tgt_level:
            return (True, True)  # valid reversal
        return (False, False)

    # Direction-based rules require level info
    if src_level is None or tgt_level is None:
        return (False, False)

    if rule == "upward":
        return (src_level < tgt_level, False)
    if rule == "upward_or_lateral":
        return (src_level <= tgt_level, False)

    return (False, False)


def _edge_min_turn(edge: dict, utt_to_turn: dict) -> int | None:
    turns_seen = [
        utt_to_turn[u] for u in edge.get("source_utterance_ids", []) if u in utt_to_turn
    ]
    return min(turns_seen) if turns_seen else None


# ---------------------------------------------------------------------------
# Chain walking
# ---------------------------------------------------------------------------


def _walk_chains(
    edges: list[dict],
    node_by_id: dict[str, dict],
    chain_rules: dict[str, list[list[str]] | str | None],
    node_levels: dict[str, int],
) -> list[tuple[list[str], list[dict]]]:
    """Return maximal paths of length >= 2 using edge types defined in chain_rules.

    For each edge type rule:
      - None / "unconstrained" → traverse all edges of that type
      - "upward"              → only if src_level < tgt_level
      - "upward_or_lateral"   → only if src_level <= tgt_level
      - "reverse"             → flip src↔tgt, include if new src_level < new tgt_level
      - [...] (list)          → old type-pair allowlist (backward compat)

    Superseded nodes and revises edges are always excluded.
    Maximal = drop any path that is a strict prefix of another.
    """
    active_nodes = {
        nid: n for nid, n in node_by_id.items() if not n.get("superseded_by")
    }

    adj: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for e in edges:
        edge_type = e["edge_type"]
        if edge_type not in chain_rules:
            continue
        s, t = e["source_node_id"], e["target_node_id"]
        if s not in active_nodes or t not in active_nodes:
            continue
        rule = chain_rules[edge_type]
        passes, use_reversed = _edge_passes(s, t, rule, active_nodes, node_levels)
        if not passes:
            continue
        if use_reversed:
            # Clone edge with swapped source/target and _reversed flag
            rev_edge = dict(e)
            rev_edge["source_node_id"] = t
            rev_edge["target_node_id"] = s
            rev_edge["_reversed"] = True
            adj[t].append((s, rev_edge))
        else:
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


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_chain(
    path_nodes: list[str],
    path_edges: list[dict],
    node_by_id: dict[str, dict],
    utt_to_turn: dict,
    node_levels: dict[str, int],
    prefix: str = "",
) -> str:
    def _node_turn(i: int) -> int | None:
        edge = path_edges[i] if i < len(path_edges) else path_edges[-1]
        return _edge_min_turn(edge, utt_to_turn)

    def _node_level(node_type: str) -> str:
        lvl = node_levels.get(node_type)
        return f"L{lvl}" if lvl is not None else "?"

    path_steps = []
    for i, nid in enumerate(path_nodes):
        nt = node_by_id[nid]["node_type"]
        path_steps.append(
            f"`{node_by_id[nid]['label']}` ({nt}, {_node_level(nt)}, t={_node_turn(i) or '?'})"
        )
    lines = [f"### Chain{prefix}", "**Path**:", "", "  → " + "  \n  → ".join(path_steps) + "  ", ""]
    lines.append("**Evidence**:")
    for e in path_edges:
        src = node_by_id[e["source_node_id"]]
        tgt = node_by_id[e["target_node_id"]]
        t = _edge_min_turn(e, utt_to_turn)
        # KGEdge has no source_quotes field (only KGNode does).
        # Derive edge evidence from the connected nodes' verbatim quotes.
        quotes = e.get("source_quotes", []) or []
        if not quotes:
            quotes = (src.get("source_quotes", []) or []) + (
                tgt.get("source_quotes", []) or []
            )
        quote = quotes[0] if quotes else "(no quote)"
        reversed_mark = " (reversed)" if e.get("_reversed") else ""
        lines.append(
            f'- `{src["label"]} → {tgt["label"]}` [{e["edge_type"]}{reversed_mark}] (t={t or "?"}): _"{quote}"_'
        )
    lines.append("\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_causal_chains(
    json_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Generate causal chain extraction markdown from simulation JSON."""
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
    chain_rules = _load_chain_rules(methodology)
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
            surface_edges, surface_by_id, chain_rules, node_levels
        )
        can_paths = _walk_chains(canon_edges, canon_by_id, chain_rules, node_levels)
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
    # Canonical chain edge counts and node types are computed in the render phase

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

    # Output path
    if output_path:
        out_path = output_path
    else:
        out_path = Path(f"reports/causal_chains/{json_path.stem}_causal_chains.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

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

        for tier in active_tiers:
            heading = {
                "full": "Full chains — complete, no missing levels",
                "advanced": "Advanced chains — near-complete (one gap) or near-terminal",
                "developing": "Developing chains — mid-level progression",
                "started": "Started — fewer than 3 nodes",
            }[tier]
            md += f"## {heading}\n\n"
            for i, (pn, pe) in enumerate(surf_by_tier.get(tier, []), 1):
                md += _render_chain(
                    pn, pe, surface_by_id, utt_to_turn, node_levels
                ).replace("### Chain", f"### Chain {i}")
            for i, (pn, pe) in enumerate(can_by_tier.get(tier, []), 1):
                md += _render_chain(
                    pn, pe, canon_by_id, utt_to_turn, node_levels
                ).replace("### Chain", f"### Chain {i}")
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
            # Derive turn from source utterance IDs
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

    out_path.write_text(md)
    print(f"Wrote {out_path}")
    for tier in ["full", "advanced", "developing", "started"]:
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
