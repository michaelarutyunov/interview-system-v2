# Chain Rules Specification
## Current Version: 1.0

Chain construction rules for the post-hoc analytical chain extractor (`scripts/reporting/generate_causal_chains.py`). These rules are **reporting-only** — they do not affect the live interview engine.

## Engine vs Reporting Distinction

| Layer | Config source | Used by | Purpose |
|-------|-------------|---------|---------|
| Engine | Methodology YAML `ontology.edges[].chain_relevant: true` | `ChainTopologySignalDetector` (live) | Filters edges for `gap.above`, `gap.below`, etc. during interview |
| Reporting | `config/chain_rules/{methodology}.yaml` | `generate_causal_chains.py` (post-hoc) | Filters edges when extracting causal chains for export |

The engine uses **edge type only** (e.g., all `triggers` edges pass if `chain_relevant: true`). The reporting script additionally evaluates **direction** (ontology levels) and can include reversed downward edges.

## Direction-Based Format (April 2026)

Replaces the legacy type-pair allowlist format. Each chain-relevant edge type maps to a direction rule:

| Rule | Semantics | Example |
|------|-----------|---------|
| `upward` | `src_level < tgt_level` — moving toward terminal | L0→L1, L1→L3 (skip ok) |
| `upward_or_lateral` | `src_level <= tgt_level` — allows same-level elaboration | L3→L3 emotional chaining |
| `reverse` | Flip src↔tgt, include if new direction is upward | L4→L1 becomes L1→L4 |
| `unconstrained` | All edges of this type pass (MEC pattern) | — |

### JTBD Example

```yaml
# config/chain_rules/jobs_to_be_done_v2.yaml
chain_edges:
  triggers: upward
  implies: upward
  supports: upward_or_lateral
  drives: upward
  addresses: reverse
  achieves: reverse
```

`addresses` and `achieves` are non-chain-relevant in the methodology YAML (engine ignores them). Adding them to chain_rules with `reverse` recovers pain→solution links that the extraction captured in the opposite direction (solution→pain). Reversed edges are included in chain traversal with `_reversed: True` and rendered as `[addresses (reversed)]`.

### MEC Example

```yaml
# config/chain_rules/means_end_chain_v2_strict.yaml
chain_edges:
  leads_to: unconstrained
```

MEC constrains edge validity at extraction time via `permitted_connections` on the `leads_to` edge in the methodology YAML. The chain_rules trust the extraction and apply no further filtering.

## Architectural Split: MEC vs JTBD

The two methodology families use opposite strategies:

| | Extraction guidance | chain_rules |
|---|-------------------|-------------|
| **MEC** | `permitted_connections` on edges in methodology YAML (LLM sees type-pair hints) | `unconstrained` (trust extraction) |
| **JTBD** | No `permitted_connections` (LLM sees bare semantic descriptions) | Direction-based filtering (post-hoc) |

This split was discovered April 2026 when JTBD interviews produced 0 full chains. The root cause: the LLM extracted semantically valid edges but without type-pair guidance, 75% of edges used level-skipping patterns (L0→L3, L1→L4) that the legacy type-pair allowlist rejected. The direction-based format fixed this by accepting any upward edge regardless of how many levels it skips.

## Implementation

### Edge Filtering: `_edge_passes()`

Located in `scripts/reporting/generate_causal_chains.py`. Evaluates each edge against its direction rule:

1. **Old type-pair list** (backward compat): checks `[src_type, tgt_type] in permitted`
2. **`unconstrained` / None**: always passes
3. **`reverse`**: if `src_level > tgt_level`, returns `(True, True)` — the `True` second value signals the caller to swap src↔tgt and clone the edge dict
4. **`upward`**: `src_level < tgt_level`
5. **`upward_or_lateral`**: `src_level <= tgt_level`

### Chain Walking: `_walk_chains()`

Builds adjacency from filtered edges. For reverse edges, clones the edge dict with swapped source/target and `_reversed: True`. Then performs DFS from root nodes, dropping sub-paths that are strict prefixes of longer paths (maximal only).

### Rendering

`_render_chain()` appends ` (reversed)` to the edge type display for reversed edges: `[achieves (reversed)]`.

## Chain Completeness Tiers

Applied after chain walking. Tiers are derived from the methodology's ontology level count:

| Tier | Criteria |
|------|----------|
| `full` | ≥3 nodes, reaches terminal (max level), all intermediate levels present |
| `advanced` | ≥3 nodes, reaches terminal with exactly 1 missing level, OR reaches second-highest level |
| `developing` | ≥3 nodes, does not meet full/advanced criteria |
| `started` | <3 nodes |
| `lateral` | All nodes same type (excluded from output) |

## Relationship to Other Config

| Config file | What it controls | Layer |
|-------------|-----------------|-------|
| `config/methodologies/{m}.yaml` → `ontology.edges[].chain_relevant` | Edge types considered for chain topology signals | Engine |
| `config/methodologies/{m}.yaml` → `ontology.edges[].permitted_connections` | Type-pair hints shown to extraction LLM | Extraction |
| `config/methodologies/{m}.yaml` → `ontology.nodes[].level` | Ontology level for each node type | Both |
| `config/chain_rules/{m}.yaml` | Edge direction rules for post-hoc chain extraction | Reporting |
| `config/chain_rules/{m}.yaml` (absent) | Falls back to `leads_to: unconstrained` | Reporting |

## Source Files

- `scripts/reporting/generate_causal_chains.py` — chain walking, classification, rendering
- `config/chain_rules/*.yaml` — direction rules per methodology
- `src/signals/graph/chain_topology_signals.py` — engine-side chain topology (uses `chain_relevant`, not chain_rules)
- `src/domain/models/methodology_schema.py` — `get_chain_relevant_edge_types()`, `get_edge_descriptions_with_connections()`
