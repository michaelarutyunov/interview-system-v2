#!/usr/bin/env python3
"""Generate a two-level grouped view of causal chains using prefix-trie clustering.

Builds a prefix trie from extracted chain node-ID sequences, identifies
"story families" (shared prefixes with ≥2 chains, ≥3 nodes deep), and
renders them with their divergent branches.

Usage:
    python scripts/chains/generate_chain_groups.py synthetic_interviews/<file>.json
    python scripts/chains/generate_chain_groups.py <json> -o report.md
    python scripts/chains/generate_chain_groups.py <json> --append existing.md
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from scripts.chains._chain_common import (
    _build_utterance_turn_map,
    _check_coverage,
    _classify_chain,
    _derive_tiers,
    _load_chain_rules,
    _map_canonical_slots,
    _tier_descriptions,
    _walk_chains,
)


# ---------------------------------------------------------------------------
# Prefix trie construction
# ---------------------------------------------------------------------------


def _build_prefix_trie(
    chains: list[tuple[list[str], list[dict]]],
) -> dict:
    """Build a prefix trie from chain node-ID sequences.

    Returns a nested dict structure:
        {
            node_id: {
                '_chains': [(nodes, edges), ...],   # chains passing through this prefix
                '_next': { next_node_id: { ... } }  # children
            }
        }

    Each trie node stores all chains that share the prefix ending at this node.
    The root level contains the first node of each chain.
    """
    trie: dict = {}

    for nodes, edges in chains:
        if not nodes:
            continue
        current = trie
        for i, nid in enumerate(nodes):
            if nid not in current:
                current[nid] = {"_chains": [], "_next": {}}
            current[nid]["_chains"].append((nodes, edges))
            current = current[nid]["_next"]

    return trie


# ---------------------------------------------------------------------------
# Family identification
# ---------------------------------------------------------------------------


def _identify_families(
    trie: dict,
    node_by_id: dict[str, dict],
    utt_to_turn: dict[str, int],
    node_levels: dict[str, int],
    min_chains: int = 2,
    min_depth: int = 2,
) -> list[dict]:
    """Identify story families from the prefix trie.

    A family is a trie node at depth >= min_depth (0-indexed) with >= min_chains
    chains passing through it. Returns families sorted by chain count (desc),
    then depth (desc).

    Each family dict:
        prefix_nodes: list of node dicts forming the shared stem
        chains: list of (node_ids, edges) passing through this prefix
        depth: number of nodes in the shared prefix
        branches: list of branch dicts, each with:
            next_node: the diverging node dict
            chains: chains in this branch
    """
    families: list[dict] = []

    def _walk_trie(
        current: dict,
        prefix_nodes: list[str],
        depth: int,
    ) -> None:
        for nid, entry in current.items():
            if not isinstance(entry, dict) or "_chains" not in entry:
                continue
            chain_count = len(entry["_chains"])
            path = prefix_nodes + [nid]

            if depth >= min_depth and chain_count >= min_chains:
                # Build branches: each child is a branch
                branches = []
                for child_nid, child_entry in entry["_next"].items():
                    if isinstance(child_entry, dict):
                        branches.append(
                            {
                                "next_node": node_by_id.get(child_nid, {}),
                                "next_node_id": child_nid,
                                "chain_count": len(child_entry.get("_chains", [])),
                            }
                        )

                # Sort branches by chain count descending
                branches.sort(key=lambda b: -b["chain_count"])

                families.append(
                    {
                        "prefix_nodes": [node_by_id.get(pn, {}) for pn in path],
                        "prefix_node_ids": path,
                        "chains": entry["_chains"],
                        "depth": depth + 1,
                        "chain_count": chain_count,
                        "branches": branches,
                    }
                )

            _walk_trie(entry["_next"], path, depth + 1)

    _walk_trie(trie, [], 0)

    # De-duplicate: if family A's prefix is a prefix of family B, keep only
    # the deepest one (most specific) when they have the same chain count.
    families.sort(key=lambda f: (-f["chain_count"], -f["depth"]))

    filtered: list[dict] = []
    for f in families:
        # Check if this family is subsumed by a deeper one we already kept
        f_prefix = tuple(f["prefix_node_ids"])
        is_subsumed = any(
            len(f_prefix) < len(tuple(other["prefix_node_ids"]))
            and tuple(other["prefix_node_ids"])[: len(f_prefix)] == f_prefix
            and other["chain_count"] == f["chain_count"]
            for other in filtered
        )
        if not is_subsumed:
            filtered.append(f)

    # Drop degenerate families: identical chains with no divergence
    filtered = [f for f in filtered if len(f["branches"]) > 0]

    return filtered


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _node_turn_str(node: dict, utt_to_turn: dict[str, int]) -> str:
    """Derive turn string from a node's utterance IDs."""
    utt_ids = node.get("source_utterance_ids", []) or []
    for uid in utt_ids:
        if uid in utt_to_turn:
            return str(utt_to_turn[uid])
    return "?"


def _node_level_str(node_type: str, node_levels: dict[str, int]) -> str:
    lvl = node_levels.get(node_type)
    return f"L{lvl}" if lvl is not None else "?"


def _render_family_mermaid(
    fam: dict,
    node_by_id: dict[str, dict],
    utt_to_turn: dict[str, int],
    node_levels: dict[str, int],
    family_index: int,
) -> str:
    """Render a single story family as a Mermaid graph TD diagram."""
    prefix_nodes = fam["prefix_nodes"]
    branches = fam["branches"]

    def _safe_label(node: dict) -> str:
        label = node.get("label", "?")
        # Escape mermaid-unfriendly characters
        label = label.replace('"', "'").replace("[", "(").replace("]", ")")
        if len(label) > 45:
            label = label[:42] + "..."
        return label

    lines = ["```mermaid", "graph TD"]
    node_ids = []

    # Prefix trunk nodes
    for i, node in enumerate(prefix_nodes):
        nid = f"p{family_index}_{i}"
        node_ids.append(nid)
        t = _node_turn_str(node, utt_to_turn)
        nt = node.get("node_type", "?")
        lvl = _node_level_str(nt, node_levels)
        label = _safe_label(node)
        lines.append(f'    {nid}["t={t}: {label}<br/>{nt} {lvl}"]')

    # Trunk edges
    for i in range(len(node_ids) - 1):
        lines.append(f"    {node_ids[i]} --> {node_ids[i + 1]}")

    # Branch nodes (from the last prefix node)
    last_prefix = node_ids[-1] if node_ids else None
    branch_ids = []
    for bi, branch in enumerate(branches):
        bnode = branch.get("next_node", {})
        if not bnode:
            continue
        bid = f"p{family_index}_b{bi}"
        branch_ids.append(bid)
        t = _node_turn_str(bnode, utt_to_turn)
        nt = bnode.get("node_type", "?")
        lvl = _node_level_str(nt, node_levels)
        label = _safe_label(bnode)
        count = branch.get("chain_count", 0)
        lines.append(
            f'    {bid}["t={t}: {label}<br/>{nt} {lvl}<br/>({count} chain{"" if count == 1 else "s"})"]'
        )

    # Branch edges
    if last_prefix:
        for bid in branch_ids:
            lines.append(f"    {last_prefix} --> {bid}")

    # Style prefix vs branch nodes
    if node_ids:
        lines.append("    classDef prefix fill:#e8f0fe,stroke:#4285f4,color:#333")
        lines.append(f"    class {','.join(node_ids)} prefix")
    if branch_ids:
        lines.append("    classDef branch fill:#e6f4ea,stroke:#34a853,color:#333")
        lines.append(f"    class {','.join(branch_ids)} branch")

    lines.append("```")
    return "\n".join(lines)


def _render_families_markdown(
    families: list[dict],
    node_by_id: dict[str, dict],
    utt_to_turn: dict[str, int],
    node_levels: dict[str, int],
    tier_descs: dict[str, str],
    sorted_levels_desc: list[int],
    num_tiers: int,
    max_level: int,
    total_chains: int,
    methodology: str,
    chain_rules_source: str,
    include_mermaid: bool = False,
) -> str:
    """Render story families and their branches as markdown."""
    md = f"""# Chain Group Analysis

## Summary
- **Methodology**: `{methodology}`
- **Chain rules**: `{chain_rules_source}`
- **Total chains walked**: {total_chains}
- **Story families identified**: {len(families)}
- **Derivation**: Prefix-trie clustering on node-ID sequences.
  A story family is a shared prefix of ≥3 nodes present in ≥2 chains.
  Branches are divergent suffixes from the family's last common node.

---

"""
    if not families:
        md += "_No story families found — chains are too short or singleton._\n\n"
        return md

    # Group families by depth for readability
    for fi, fam in enumerate(families, 1):
        prefix_nodes = fam["prefix_nodes"]
        depth = fam["depth"]
        chain_count = fam["chain_count"]
        branches = fam["branches"]

        # Build prefix path display
        prefix_lines = []
        for ni, node in enumerate(prefix_nodes):
            t = _node_turn_str(node, utt_to_turn)
            nt = node.get("node_type", "?")
            lvl = _node_level_str(nt, node_levels)
            prefix_lines.append(f"  {ni + 1}. t={t} `{node['label']}` ({nt}, {lvl})")

        prefix_path_str = "\n".join(prefix_lines)

        # Classify chains in this family
        tiers = defaultdict(int)
        for nodes_p, _ in fam["chains"]:
            tier = _classify_chain(
                nodes_p,
                node_by_id,
                node_levels,
                sorted_levels_desc,
                num_tiers,
                max_level,
            )
            if tier != "lateral":
                tiers[tier] += 1

        tier_summary = (
            ", ".join(f"{count} {tier}" for tier, count in sorted(tiers.items()))
            if tiers
            else "no classified chains"
        )

        md += f"### Family {fi}: {prefix_nodes[0]['label'][:60]}\n\n"
        md += f"**{chain_count} chains**, {depth} shared nodes, {len(branches)} branches. "
        md += f"Tiers: {tier_summary}.\n\n"
        md += "**Shared prefix:**\n\n"
        md += prefix_path_str + "\n\n"

        if include_mermaid:
            md += _render_family_mermaid(fam, node_by_id, utt_to_turn, node_levels, fi)
            md += "\n\n"

        if branches:
            md += "**Branches** (divergent nodes from the last shared node):\n\n"
            for bi, branch in enumerate(branches, 1):
                bnode = branch["next_node"]
                if not bnode:
                    continue
                t = _node_turn_str(bnode, utt_to_turn)
                nt = bnode.get("node_type", "?")
                lvl = _node_level_str(nt, node_levels)
                md += (
                    f"- **Branch {bi}** ({branch['chain_count']} chains): "
                    f"t={t} `{bnode['label']}` ({nt}, {lvl})\n"
                )
            md += "\n"
        else:
            md += "_Single path — no branching at this prefix._\n\n"

        # Show one representative chain (shortest, for readability)
        rep_chains = sorted(fam["chains"], key=lambda c: len(c[0]))
        if rep_chains:
            rep_nodes, _ = rep_chains[0]
            full_path = " → ".join(f"`{node_by_id[nid]['label']}`" for nid in rep_nodes)
            md += f"**Shortest full chain:** {full_path}\n\n"

        md += "---\n\n"

    return md


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_chain_groups(json_path: Path, include_mermaid: bool = False) -> str:
    """Generate grouped chain analysis markdown from simulation JSON.

    Args:
        json_path: Path to simulation JSON.
        include_mermaid: If True, embed Mermaid graph TD diagrams per family.

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

    sorted_levels_desc, max_level, num_tiers = _derive_tiers(node_levels)
    tier_descs = (
        _tier_descriptions(node_levels, sorted_levels_desc, num_tiers)
        if num_tiers
        else {}
    )

    chain_rules, chain_filters = _load_chain_rules(methodology)
    chain_rules_source = (
        f"config/chain_rules/{methodology}.yaml"
        if Path(f"config/chain_rules/{methodology}.yaml").exists()
        else "fallback"
    )

    utt_to_turn = _build_utterance_turn_map(data)
    _check_coverage(data, utt_to_turn)

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

    # Walk surface chains for grouping (canonical chains are sparse by design)
    if num_tiers == 0:
        surf_paths = []
    else:
        surf_paths = _walk_chains(
            surface_edges, surface_by_id, chain_rules, node_levels, chain_filters
        )

    # Use surface chains only for grouping (canonical chains are sparse by design)
    # Build trie from all non-lateral surface chains
    usable_chains = []
    for nodes_p, edges_p in surf_paths:
        tier = _classify_chain(
            nodes_p,
            surface_by_id,
            node_levels,
            sorted_levels_desc,
            num_tiers,
            max_level,
        )
        if tier != "lateral" and tier != "started":
            usable_chains.append((nodes_p, edges_p))

    trie = _build_prefix_trie(usable_chains)
    families = _identify_families(
        trie,
        surface_by_id,
        utt_to_turn,
        node_levels,
        min_chains=2,
        min_depth=2,
    )

    print(
        f"chains: total={len(surf_paths)} usable={len(usable_chains)} "
        f"families={len(families)}",
        file=sys.stderr,
    )

    return _render_families_markdown(
        families,
        surface_by_id,
        utt_to_turn,
        node_levels,
        tier_descs,
        sorted_levels_desc,
        num_tiers,
        max_level,
        total_chains=len(usable_chains),
        methodology=methodology,
        chain_rules_source=chain_rules_source,
        include_mermaid=include_mermaid,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate grouped causal chain analysis."
    )
    parser.add_argument("json_file", type=Path, help="Path to simulation JSON")
    parser.add_argument("-o", "--output", type=Path, help="Write to file (overwrite)")
    parser.add_argument("--append", type=Path, help="Append to existing file")
    parser.add_argument(
        "--mermaid", action="store_true", help="Embed Mermaid diagrams per family"
    )
    args = parser.parse_args()

    if not args.json_file.exists():
        print(f"File not found: {args.json_file}", file=sys.stderr)
        sys.exit(1)

    md = generate_chain_groups(args.json_file, include_mermaid=args.mermaid)

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
