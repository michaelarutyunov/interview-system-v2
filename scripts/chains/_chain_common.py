"""Shared utilities for causal chain extraction, classification, and grouping.

Extracted from generate_causal_chains.py to avoid duplication across
chain analysis scripts. No logic changes from the original — pure extraction.
"""

import sys
from collections import defaultdict
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Chain rules loading
# ---------------------------------------------------------------------------

_CONFIDENCE_RANK = {"high": 2, "medium": 1, "low": 0}


def _confidence_tier(value: str | float | int) -> str:
    """Convert a confidence value to a tier string.

    Accepts both string tiers ("high", "medium", "low") and numeric values
    (0.0–1.0 scale: >=0.8 → high, >=0.6 → medium, else → low).
    """
    if isinstance(value, str):
        return value if value in _CONFIDENCE_RANK else "low"
    if isinstance(value, (int, float)):
        if value >= 0.8:
            return "high"
        if value >= 0.6:
            return "medium"
        return "low"
    return "low"


def _load_chain_rules(
    methodology: str,
) -> tuple[dict[str, list[list[str]] | str | None], dict]:
    """Load chain construction rules for a methodology.

    Returns (chain_edges, filters) where:
      chain_edges: mapping of edge_type -> traversal rule
        Rule formats:
          - None / "unconstrained": all edges of this type pass
          - "upward": src_level < tgt_level
          - "upward_or_lateral": src_level <= tgt_level
          - "reverse": flip direction, include if reversed edge is upward
          - [...] (list): old type-pair allowlist (backward compat)
      filters: optional chain_edge_filters dict from the YAML, e.g.:
          exclude_frame: [contaminated]
          min_confidence: medium

    Fail-fast: raises FileNotFoundError if no chain_rules YAML exists for the
    methodology, and KeyError if the YAML lacks a `chain_edges` key.
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
    return data["chain_edges"], data.get("chain_edge_filters", {})


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
        if len(missing) == 0:
            return "full"
        elif len(missing) == 1:
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
            f"Reaches {_names(sorted_levels_desc[0])} (missing one level) or {_names(sorted_levels_desc[1])}"
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


def _node_min_turn(node: dict, utt_to_turn: dict) -> int | None:
    turns_seen = [
        utt_to_turn[u] for u in node.get("source_utterance_ids", []) if u in utt_to_turn
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
    filters: dict | None = None,
) -> list[tuple[list[str], list[dict]]]:
    """Return maximal paths of length >= 2 using edge types defined in chain_rules.

    For each edge type rule:
      - None / "unconstrained" → traverse all edges of that type
      - "upward"              → only if src_level < tgt_level
      - "upward_or_lateral"   → only if src_level <= tgt_level
      - "reverse"             → flip src↔tgt, include if new src_level < new tgt_level
      - [...] (list)          → old type-pair allowlist (backward compat)

    filters (from chain_edge_filters in chain_rules YAML):
      exclude_frame: list of frame values to exclude (e.g. ["contaminated"])
      min_confidence: minimum confidence level ("high", "medium", or "low")

    Superseded nodes and revises edges are always excluded.
    Maximal = drop any path that is a strict prefix of another.
    """
    active_nodes = {
        nid: n for nid, n in node_by_id.items() if not n.get("superseded_by")
    }

    exclude_frames: set[str] = set((filters or {}).get("exclude_frame", []))
    min_conf_str: str = (filters or {}).get("min_confidence", "low")
    min_conf_rank: int = _CONFIDENCE_RANK.get(min_conf_str, 0)

    adj: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for e in edges:
        edge_type = e["edge_type"]
        if edge_type not in chain_rules:
            continue
        s, t = e["source_node_id"], e["target_node_id"]
        if s not in active_nodes or t not in active_nodes:
            continue
        # Apply chain_edge_filters: exclude contaminated frames and low-confidence edges
        edge_frame = e.get("frame") or e.get("properties", {}).get("frame")
        if exclude_frames and edge_frame in exclude_frames:
            continue
        if min_conf_rank > 0:
            edge_conf_tier = _confidence_tier(e.get("confidence", "low"))
            if _CONFIDENCE_RANK.get(edge_conf_tier, 0) < min_conf_rank:
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
