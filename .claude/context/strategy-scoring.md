# Strategy Scoring

## Core Mechanics

Strategy selection uses joint scoring — all eligible (strategy, node) pairs are
scored simultaneously and the globally highest-scoring pair is selected.

```
base_score = Σ(signal_weight × signal_value)
final_score = (base_score × phase_multiplier) + phase_bonus
```

### Joint Strategy-Node Scoring

`MethodologyStrategyService.select_strategy_and_focus()` partitions strategies
by `node_binding`:

- **node_binding='required'**: scored via `rank_strategy_node_pairs()` — each
  (strategy, node) pair gets merged global+node signals, valid_when gates filter
  ineligible pairs, and the pair is scored.
- **node_binding='none'**: scored via `rank_strategies()` — global signals only,
  node_id is None in the output.

Both candidate pools are merged and sorted by score. The highest-scoring pair
determines both the selected strategy and the target node for question generation.

### Signal Value Resolution

| Weight key pattern | Resolved as |
|---|---|
| `graph.max_depth` | Raw signal value (float in [0,1] or bool) |
| `llm.response_depth.deep` | `True` (→1.0) if `response_depth == "deep"`, else `False` (→0.0) |
| `llm.specificity.high` | `True` if value >= 0.75 |
| `llm.specificity.mid` | `True` if 0.25 < value < 0.75 |
| `llm.specificity.low` | `True` if value <= 0.25 |
| `graph.node.exhausted.true` | `True` if node signal `exhausted == True` |
| `graph.node.gap_above.true` | `True` if node has no outgoing edge to a higher ontology level |
| `graph.node.gap_below.true` | `True` if node has no incoming edge from a lower ontology level |
| `graph.node.level_skip.true` | `True` if node has a direct leads_to edge skipping >1 ontology level |
| `graph.node.branching_deficit` | Float in [0,1]: 1 - (actual_siblings / expected_siblings) |
| `graph.node.fan_in` | Int: count of distinct origin-level nodes with paths to this node |
| `graph.node.level_gap_size` | Int: ontology levels between this node and terminal/origin |
| `graph.node.is_orphan.true` | `True` if node has no edges at all (isolated) |
| `graph.node.recency_score` | Float in [0,1]: how recently the node was last discussed |

Threshold binning (`.low`/`.mid`/`.high`) applies only to float signals
normalized to [0, 1]. Categorical signals use exact string equality.
Bool signals use `.true`/`.false` suffix. Integer signals (e.g., `fan_in`,
`level_gap_size`) are multiplied directly by weight — use small weights to
avoid dominance.

### Phase Multiplier and Bonus

Phase multipliers and bonuses are keyed by **strategy name** in the YAML
`phases:` block. Both are retrieved from `config.phases[current_phase]`:

- `signal_weights` → multiplicative (default `1.0` when absent)
- `phase_bonuses` → additive (default `0.0` when absent)

The same phase values are applied in both Stage 1 (strategy ranking) and
Stage 2 (node ranking for the winning strategy).

**Example**:
```
Base ascend score: 2.5
Early phase multiplier: 0.8
Early phase bonus: 0.0
Final score = (2.5 × 0.8) + 0.0 = 2.0
```

### `ScoredCandidate` Decomposition

Every scored pair produces a `ScoredCandidate` dataclass with:

| Field | Type | Contents |
|---|---|---|
| `strategy` | `str` | Strategy name |
| `node_id` | `str` | Node UUID; `""` for Stage 1 strategy-level entries |
| `signal_contributions` | `list[SignalContribution]` | Per-signal breakdown |
| `base_score` | `float` | Score before phase adjustment |
| `phase_multiplier` | `float` | Applied multiplier |
| `phase_bonus` | `float` | Applied bonus |
| `final_score` | `float` | `(base_score × phase_multiplier) + phase_bonus` |
| `rank` | `int` | 1-indexed rank among all candidates |
| `selected` | `bool` | `True` for rank == 1 |

`SignalContribution` records `name`, `value`, `weight`, and `contribution`
(the actual product added to `base_score`).

---

## Chain-Aware Strategy Selection (MEC)

### Overview

The Means-End Chain methodology uses 6 chain-aware strategies that exploit
graph topology to drive interview flow. Each strategy targets a specific
structural gap or opportunity in the knowledge graph.

Legacy strategies (`deepen`, `explore`, `clarify`, `reflect`) have been removed
from MEC YAMLs. The default fallback strategy in code is now `ascend` (was
`deepen`).

### The 6 MEC Strategies

| Strategy | `node_binding` | `valid_when` | Purpose |
|---|---|---|---|
| `ascend` | `required` | `graph.node.gap_above` | Extend an incomplete chain upward toward terminal values |
| `ground` | `required` | `graph.node.gap_below` | Establish causal antecedents for ungrounded high-level nodes |
| `bridge` | `required` | `graph.node.level_skip` | Fill missing intermediate levels in a chain with skipped ontology levels |
| `branch` | `required` | `graph.node.branching_deficit` | Expand breadth where methodology expects more siblings |
| `anchor` | `required` | `graph.node.is_orphan` | Connect isolated nodes to existing graph structure |
| `revitalize` | `none` | *(none)* | Conversation-level fallback for fatigue/disengagement |

### `valid_when` Gate

A strategy with `valid_when` set is only scored for nodes where the named
signal evaluates to `True`. Invalid `(strategy, node)` pairs are skipped
entirely — no score, no contribution. This is a **hard gate**, not a weight.

- `valid_when` must reference a known signal name (validated at load time by the registry)
- Only valid for `node_binding: required` strategies (setting `valid_when` on a
  `node_binding: none` strategy raises `ValueError` at load time)
- `valid_when` is checked in `rank_strategy_node_pairs()` before merging signals
  and computing scores

Implementation: `StrategyConfig.valid_when` (optional `str | None`, default `None`)
in `src/methodologies/registry.py`.

### Score Threshold Fallback

`MethodologyStrategyService` checks `chain_completion.score_threshold` from the
methodology config after Stage 1 scoring. When `best_strategy_score < threshold`,
it evaluates fatigue/engagement signals:

1. Reads `llm.global_response_trend` — if `"fatigued"`, triggers fallback
2. Reads `llm.engagement` — if `< 0.3` (float), triggers fallback
3. Fallback selects `revitalize` (if defined in the methodology's strategies)

The production threshold in MEC YAMLs is `score_threshold: 0.15`. Set to `0.0`
to disable fallback (used during cross-strategy comparison testing).

If no fatigue/engagement condition is met despite the low score, the best-scoring
strategy is used regardless — the fallback is conservative, not mandatory.

### Chain Topology Signals

Chain topology signals are computed by `ChainTopologySignalDetector`
(`src/signals/graph/chain_topology_signals.py`). They are pure graph topology —
no LLM calls.

**Source architecture**:
- `ChainTopologySignalDetector` (extends `NodeSignalDetector`) computes a nested
  dict per node under the key `graph.node.chain_topology`
- `NodeSignalDetectionService` flattens this into individual per-node signal keys
  for use in `signal_weights` and `valid_when`
- Flat sentinel classes (`_GapAboveSentinel`, `_GapBelowSentinel`, etc.) register
  the flat signal names in the `SignalDetector` registry so YAML validation passes
- Shared graph traversal utilities live in `src/signals/graph/graph_traversal.py`
  (`build_adjacency_list`, `build_reverse_adjacency_list`, `get_node_type_map`,
  `bfs_reachable`, `bfs_to_target`)

**Per-node flat signal keys** (use these in `signal_weights` and `valid_when`):

| Signal key | Type | Description |
|---|---|---|
| `graph.node.gap_above` | bool | Node has no outgoing edge to a higher ontology level AND is non-terminal |
| `graph.node.gap_below` | bool | Node has no incoming edge from a lower ontology level AND is above origin level |
| `graph.node.level_skip` | bool | Node has a direct `leads_to` edge that skips >1 ontology level |
| `graph.node.branching_deficit` | float [0,1] | 1 - (actual_siblings / expected_siblings); 1.0 = full deficit |
| `graph.node.fan_in` | int | Count of distinct origin-level nodes with paths to this node |
| `graph.node.level_gap_size` | int | Ontology levels between this node and terminal/origin |

**Non-chain methodologies**: `ChainTopologySignalDetector` returns an empty dict
for methodologies with fewer than 2 distinct ontology levels (e.g., JTBD, CJM,
Repertory Grid, Critical Incident). Signal absence means zero contribution to
scoring.

**Additional per-node signals used by chain-aware strategies**:

| Signal key | Type | Description |
|---|---|---|
| `graph.node.is_orphan` | bool | Node has no edges at all (used by `anchor` strategy's `valid_when`) |
| `graph.node.recency_score` | float [0,1] | How recently the node was last discussed (higher = more recent) |
| `graph.node.exhaustion_score` | float [0,1] | How exhausted the node is from repeated probing (negative weight in strategies) |

---

## Correctness Requirements

1. **Phase multiplier and bonus are applied after base scoring** — never fold
   them into `signal_weights`.

2. **Node-scoped weight key namespace**: keys that should influence node ranking
   must start with `graph.node.*`, `technique.node.*`, or `meta.node.*`.
   Any other prefix routes the weight to strategy-level scoring only.

3. **Negative weights are valid** — use them for diversity penalties
   (e.g., `temporal.strategy_repetition_count: -0.5`, `graph.node.exhaustion_score: -0.4`).

4. **Strategy names in `phases:` must match names in `strategies:`** — the
   registry validates this at load time and raises `ValueError` on mismatch.

5. **`node_binding` controls Stage 2 inclusion**:
   - `required` (default): strategy participates in joint strategy-node ranking
   - `none`: strategy receives one score in Stage 1 only; no node is targeted

6. **All signals must be declared in `signals:`** — the registry validates every
   `signal_weights` key against known signal names at load time.

7. **Unbounded count signals are rejected in `signal_weights`** — `graph.node_count`,
   `graph.edge_count`, and `graph.orphan_count` return raw integers that can't be
   safely multiplied by weights. The registry raises `ValueError` at load time if
   any of these appear in a strategy's `signal_weights`. Use normalized or
   threshold-binned variants instead (e.g., `graph.node_count.low`).

8. **`valid_when` gates strategy-node pairs** — a strategy with `valid_when: graph.node.gap_above`
   is only scored for nodes where that signal is `True`. Invalid pairs are skipped entirely
   (no score, no contribution). This is a hard gate, not a weight.
   - `valid_when` must reference a known signal name (validated at load time)
   - Only valid for `node_binding: required` strategies (not `node_binding: none`)

9. **Chain topology signals are flat per-node** — `ChainTopologySignalDetector` returns a
   nested dict per node. `NodeSignalDetectionService` flattens it into individual signal keys:
   - `graph.node.gap_above`, `graph.node.gap_below`, `graph.node.level_skip`
   - `graph.node.branching_deficit`, `graph.node.fan_in`, `graph.node.level_gap_size`
   Use these flat keys in `signal_weights` and `valid_when`. The parent key
   `graph.node.chain_topology` also remains available but holds the full dict.

10. **Score threshold fallback** — `MethodologyStrategyService` checks `chain_completion.score_threshold`
    from the methodology config. If `best_strategy_score < threshold` AND fatigue/low-engagement
    detected, `revitalize` is selected instead. Production threshold is `0.15` in MEC YAMLs.
    Set `score_threshold: 0.0` to disable fallback.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---|---|---|
| Strategy never selected despite high signal match | Phase multiplier is near zero, suppressing final score | Check `phases.<phase>.signal_weights` for that strategy name |
| Phase bonus not applying | Strategy name typo in `phase_bonuses` | Fix typo; registry will catch it as a `ValueError` on next load |
| Node-level signal weight treated as strategy-level (ignored in node ranking) | Weight key missing `graph.node.*` / `technique.node.*` / `meta.node.*` prefix | Rename key to correct namespace |
| All strategies scoring equally (≈ 0) | No `signal_weights` defined, or no declared signals are firing | Verify `signal_weights` in YAML and check that signals listed under `signals:` are detected at runtime |
| `strategies_ranked` log shows unexpected order | `node_binding: none` strategy competing against node-binding strategies in Stage 2 | `node_binding: none` strategies are Stage 1 only; ensure the consuming code picks from the right ranking list |
| `ValueError` at startup: unknown strategy in phases | Strategy renamed in `strategies:` but not updated in `phases:` | Sync both sections; registry enforces referential integrity |
| `ValueError` at startup: unbounded count signal in signal_weights | `graph.node_count`, `graph.edge_count`, or `graph.orphan_count` used as weight key | Remove the raw count key; use a normalized or binned variant |
| `valid_when` strategy never fires | `valid_when` references a known signal but the signal is never True for any node | Check that chain topology signals are computed (methodology must be chain-based, graph must have nodes) |
| New strategy scores near zero despite valid_when passing | Chain topology signal sub-keys not resolving | Ensure flat sentinel classes are imported via `src/signals/__init__.py`; check flattening in `NodeSignalDetectionService` |
| Legacy strategy name (`deepen`, `explore`, `clarify`, `reflect`) in YAML or code | These strategies were removed from MEC methodologies | Replace with the appropriate chain-aware strategy (see 6 MEC Strategies table above) |
| Revitalize selected too aggressively | `score_threshold` too high, causing low-scoring but valid strategies to be bypassed | Lower `chain_completion.score_threshold` in YAML (production: 0.15) |

---

## Key Files

| File | Purpose |
|---|---|
| `src/methodologies/scoring.py` | `rank_strategy_node_pairs()`, `rank_strategies()`, `partition_signal_weights()`, `ScoredCandidate`, `SignalContribution` |
| `src/methodologies/registry.py` | `MethodologyRegistry`, `StrategyConfig` (with `valid_when` field), `PhaseConfig` — YAML loading and validation |
| `src/services/methodology_strategy_service.py` | Orchestrates Stage 1 + Stage 2; threshold fallback logic; retrieves phase weights/bonuses from loaded config |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Pipeline stage that calls `MethodologyStrategyService` |
| `src/signals/graph/chain_topology_signals.py` | `ChainTopologySignalDetector` — computes per-node chain topology signals (gap_above, gap_below, level_skip, branching_deficit, fan_in, level_gap_size); flat sentinel classes for registry |
| `src/signals/graph/graph_traversal.py` | Shared graph traversal utilities — `build_adjacency_list`, `build_reverse_adjacency_list`, `get_node_type_map`, `bfs_reachable`, `bfs_to_target` |
| `config/methodologies/means_end_chain.yaml` | Reference MEC methodology YAML with 6 chain-aware strategies, valid_when gates, signal_weights, score_threshold, and phases |
| `config/methodologies/jobs_to_be_done.yaml` | Alternative methodology for comparison (non-chain, no chain topology signals) |
