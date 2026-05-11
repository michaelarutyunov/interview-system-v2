# ADR 0001: Rename Chain Topology Signals to Remove MEC Ontology Terms

**Date**: 2026-05-11  
**Status**: Accepted

---

## Context

Two chain-topology signal IDs embedded MEC (Means-End Chain) ontology vocabulary:

- `convgraph.node.chain.has_attribute_foundation` — "attribute" refers to an MEC-specific node type
- `convgraph.node.chain.has_terminal_apex` — "terminal apex" mirrors MEC parlance for the highest chain level

The underlying computation is purely level-relative (min-level and max-level comparisons). Both signals apply equally to JTBD and Critical Incident methodologies. Embedding MEC vocabulary into the signal ID creates a false affordance: readers assume the signal is MEC-specific when it is not.

---

## Decision

Rename both signals to generic, computation-descriptive identifiers:

| Old ID | New ID |
|--------|--------|
| `convgraph.node.chain.has_attribute_foundation` | `convgraph.node.chain.has_origin_level_ancestor` |
| `convgraph.node.chain.has_terminal_apex` | `convgraph.node.chain.has_max_level_ancestor` |

The rename is purely cosmetic: no computation changed, no weights changed, no strategy semantics changed.

---

## Consequences

- All YAML `signal_weights` and `valid_when` references updated.
- Sentinel class names updated in `chain_topology_signals.py`.
- Context docs (`signal-detection-graph.md`, `strategy-scoring.md`, `strategy-selection.md`) updated.
- Historical rows in the `methodology_signals` DB table retain the old string keys. These rows are not migrated because: (a) they are diagnostic/audit data only — not used in live scoring; (b) retroactive migration would require per-row schema knowledge; (c) the cost exceeds the benefit. Consumers of historical signal data must account for the rename boundary at the date of this commit.

---

## Alternatives Considered

- **Migrate DB rows**: Rejected. Historical signal rows in `methodology_signals` are append-only audit data. Renaming them retroactively would require knowing which rows predate this change and could corrupt audit integrity.
- **Add aliases**: Rejected. Aliases add complexity for a purely cosmetic rename. The system has no live consumers of the old names after this commit.
