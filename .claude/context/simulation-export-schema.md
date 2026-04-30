# Simulation Export Schema
## Current Version: 1.0

Stable contract between simulation output (JSON/CSV) and downstream scripts.
Any change to field names or structure must update this doc and the consuming scripts.

## Output Files

After `run_simulation.py` completes, two files are written to `synthetic_interviews/`:

| File | Content |
|------|---------|
| `{timestamp}_{concept}_{persona}.json` | Complete structured export |
| `{timestamp}_{concept}_{persona}_scoring.csv` | Flattened score decomposition |

## JSON Schema

### Top-Level Structure

```json
{
  "metadata": { ... },
  "graph": { "nodes": [], "edges": [], "summary": {}, "node_labels": {} },
  "canonical_graph": { "slots": [], "edges": [], "summary": {} },
  "turns": [ { ... }, ... ]
}
```

### `metadata` (STABLE — scripts depend on these keys)

| Field | Type | Description | Consumed by |
|-------|------|-------------|-------------|
| `concept_id` | str | Concept identifier | extract, redundancy, transcript |
| `concept_name` | str | Human-readable name | transcript |
| `methodology` | str | Methodology YAML name | extract, redundancy |
| `persona_id` | str | Persona identifier | extract, redundancy |
| `persona_name` | str | Human-readable name | transcript |
| `session_id` | str | UUID | extract, redundancy |
| `total_turns` | int | Total turns in interview | extract |
| `status` | str | Completion status | extract, transcript |

### `graph` (STABLE)

| Field | Type | Description | Consumed by |
|-------|------|-------------|-------------|
| `nodes[].id` | str (UUID) | Node identifier | all scripts |
| `nodes[].label` | str | Human-readable label | all scripts |
| `nodes[].node_type` | str | Ontology type | transcript |
| `nodes[].source_quotes` | str[] | Originating utterances | transcript |
| `edges[].source_node_id` | str (UUID) | Source node | mermaid |
| `edges[].target_node_id` | str (UUID) | Target node | mermaid |
| `edges[].edge_type` | str | Relationship type | mermaid |
| `summary.total_nodes` | int | Final node count | reviews, extract |
| `summary.total_edges` | int | Final edge count | reviews, extract |
| `summary.nodes_by_type` | dict | {type: count} | reviews, extract |
| `summary.edges_by_type` | dict | {type: count} | extract |
| `node_labels` | dict | {uuid: label} lookup | reviews |

### `canonical_graph` (STABLE)

| Field | Type | Description | Consumed by |
|-------|------|-------------|-------------|
| `slots[]` | list | Canonical slot objects | extract |
| `edges[]` | list | Canonical edges | — |
| `summary.total_slots` | int | Final slot count | reviews |
| `summary.total_edges` | int | Final canonical edges | reviews |

### `turns[]` (STABLE)

| Field | Type | Description | Consumed by |
|-------|------|-------------|-------------|
| `turn_number` | int | 0-indexed turn | all scripts |
| `question` | str | Interviewer question | transcript |
| `response` | str | Respondent answer | transcript |
| `persona` | str | Persona ID | — |
| `persona_name` | str | Persona display name | — |
| `strategy_selected` | str | Winning strategy ID | all scripts |
| `should_continue` | bool | Interview continues | extract |
| `termination_reason` | str\|null | Why it stopped | extract |
| `latency_ms` | int | Pipeline latency | — |
| `focus_node_id` | str\|null | Selected focus node UUID | transcript, backfill |
| `focus_node_label` | str\|null | Focus node label | transcript |
| `signals` | dict | Signal pool values (see below) | reviews, extract, CSV |
| `node_signals` | dict | Per-node signal values | extract |
| `score_decomposition` | list | Scored candidates with contributions | all scoring scripts |
| `strategy_alternatives` | list | Ranked alternatives with scores | reviews, extract |
| `nodes_added` | list | New graph nodes this turn | transcript, mermaid, extract |
| `edges_added` | list | New graph edges this turn | extract |
| `saturation_metrics` | dict | Saturation tracking data | extract |
| `stage_timings` | dict | Per-stage latency (ms) | — |

## Signal Keys (Current Taxonomy)

These are the keys found in `turns[].signals`. Downstream scripts MUST use
these names — the old names (llm.engagement, graph.node_count, etc.) are retired.

### Global Signals (one value per turn)

| Signal Key | Type | Pool | Description |
|-----------|------|------|-------------|
| `meta.interview.phase` | str | meta | "early" / "mid" / "late" |
| `interview.phase.is_late_stage` | bool | session | True when late phase |
| `interview.phase.reason` | str | session | Human-readable phase explanation |
| `interview.strategy.self_count` | dict{str:float} | session | {strategy_name: normalized_count} |
| `interview.strategy.turns_since_change` | float | session | Normalized consecutive turns |
| `response.semantic.llm.engagement` | float | llm | Willingness to participate [0,1] |
| `response.semantic.llm.certainty` | float | llm | Epistemic confidence [0,1] |
| `response.semantic.llm.response_depth` | str | llm | "surface"/"shallow"/"moderate"/"deep" |
| `response.semantic.llm.engagement.trend` | str | llm | "deepening"/"stable"/"shallowing"/"fatigued" |
| `convgraph.state.node.count` | int | graph | Total surface nodes |
| `convgraph.state.edge.count` | int | graph | Total surface edges |
| `convgraph.state.node.orphan_count` | int | graph | Isolated node count |
| `convgraph.state.max_depth` | float | graph | Normalized chain depth [0,1] |
| `convgraph.chain.completion.ratio` | float | graph | Fraction of complete chains [0,1] |
| `convgraph.chain.completion.has_complete` | bool | graph | Any complete chain exists |
| `convgraph.chain.structure.frontier_count` | int | graph | Nodes with gap_above |
| `convgraph.chain.structure.ungrounded_count` | int | graph | Nodes with gap_below |
| `canongraph.state.node.count` | int | graph | Canonical concept count |
| `canongraph.state.edge.density` | float | graph | Canonical edge/concept ratio |
| `canongraph.state.exhaustion` | float | graph | Average canonical exhaustion [0,1] |
| `meta.saturation.conversation` | float | meta | Surface yield ratio [0,1] |
| `meta.saturation.canonical` | float | meta | Canonical novelty ratio [0,1] |

### Per-Node Signals (in `turns[].node_signals[node_id]`)

| Signal Key | Type | Description |
|-----------|------|-------------|
| `convgraph.node.exhaustion` | float | Exhaustion score [0,1] |
| `convgraph.node.yield_stagnation` | bool | No yield for 3+ turns |
| `convgraph.node.focus.streak` | str | "none"/"low"/"medium"/"high" |
| `convgraph.node.focus.count` | str | "none"/"low"/"medium"/"high" |
| `convgraph.node.is_current_focus` | bool | Currently focused node |
| `convgraph.node.recency` | float | Time-decay score [0,1] |
| `convgraph.node.is_orphan` | bool | No edges connected |
| `convgraph.node.edge_count` | int | Total edges |
| `convgraph.node.has_outgoing` | bool | Has outgoing edges |
| `convgraph.node.novelty` | str | "high"/"medium"/"low" |
| `convgraph.node.chain.gap.above` | bool | Chain frontier |
| `convgraph.node.chain.gap.below` | bool | Ungrounded |
| `convgraph.node.chain.level.skip` | bool | Skips ontology level |
| `convgraph.node.chain.branching_deficit` | float | Deficit from expected siblings [0,1] |
| `convgraph.node.chain.fan_in` | int | Paths from origin nodes |
| `convgraph.node.llm.elaboration.low` | bool | Per-concept elaboration |
| `convgraph.node.llm.elaboration.mid` | bool | Per-concept elaboration |
| `convgraph.node.llm.elaboration.high` | bool | Per-concept elaboration |
| `convgraph.node.llm.charge.negative` | bool | Per-concept emotional tone |
| `convgraph.node.llm.charge.neutral` | bool | Per-concept emotional tone |
| `convgraph.node.llm.charge.positive` | bool | Per-concept emotional tone |
| `canongraph.node.novelty` | str | "new"/"confirming"/"orphan" |

## CSV Schema (`_scoring.csv`)

One row per (turn × candidate × active_signal). Generated from `score_decomposition`.

| Column | Type | Description |
|--------|------|-------------|
| `turn_number` | int | Turn number |
| `phase` | str | From `meta.interview.phase` |
| `strategy` | str | Strategy name |
| `node_id` | str | UUID or "" for strategy-level |
| `node_label` | str | Human-readable label |
| `signal_name` | str | Signal that contributed to score |
| `signal_value` | str | Raw signal value |
| `signal_weight` | float | Weight from methodology YAML |
| `weighted_contribution` | float | value × weight |
| `phase_multiplier` | float | Phase adjustment factor |
| `phase_bonus` | float | Phase bonus |
| `base_score` | float | Pre-phase score |
| `final_score` | float | Final score after phase |
| `rank` | int | Ranking among candidates |
| `selected` | bool | Whether this candidate won |
| `gated` | bool | Whether valid_when gate blocked |
| `gate_signal` | str | Which gate signal applied |

## Consuming Scripts

| Script | Reads | Signal keys used |
|--------|-------|-----------------|
| `generate_scoring_csv.py` | JSON → CSV | `meta.interview.phase` only |
| `generate_reviews.py` | JSON + CSV | `meta.interview.phase`, `response.semantic.llm.*`, `convgraph.state.*` |
| `generate_transcript.py` | JSON | No signal keys (structural only) |
| `generate_mermaid_graph.py` | JSON | No signal keys (structural only) |
| `extract_simulation_data.py` | JSON | All global signals listed above |
| `analyze_signal_redundancy.py` | JSON or Parquet | `meta.interview.phase` + score_decomposition |
| `backfill_focus_nodes.py` | JSON | No signal keys (structural only) |

## Known Failure Modes

_No entries yet. Add failure patterns as they are discovered in this subsystem — each entry should describe the incorrect behavior, its consequence, and the correct approach._

## Change Protocol

When adding/renaming/removing a signal:
1. Update detection code in `src/signals/`
2. Add weights in methodology YAML (if scoring-relevant)
3. Update this doc's signal tables
4. Update `extract_simulation_data.py` and `generate_reviews.py` if the signal is used there
5. Run `ruff check .` and verify scripts work on a recent simulation JSON
