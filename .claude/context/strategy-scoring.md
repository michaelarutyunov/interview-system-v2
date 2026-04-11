# Strategy Scoring

## Core Mechanics

Strategy selection runs in two stages, both using the same scoring formula:

```
base_score = Σ(signal_weight × signal_value)
final_score = (base_score × phase_multiplier) + phase_bonus
```

### Stage 1 — Strategy Ranking (`rank_strategies`)

Scores each strategy against global signals only. Node-scoped weight keys
(`graph.node.*`, `technique.node.*`, `meta.node.*`) are stripped before Stage 1
scoring via `partition_signal_weights()`. The top-ranked strategy is selected.

### Stage 2 — Joint Strategy-Node Ranking (`rank_strategy_node_pairs`)

Scores every `(strategy, node_id)` combination. For each pair, global signals
and node-specific signals are merged (`{**global_signals, **node_signals}`);
node-signal keys take precedence on collision. The top-ranked pair determines
both the selected strategy and the target node for question generation.

Strategies with `node_binding: none` are handled by Stage 1 only — they receive
a single score with no node component.

### Signal Value Resolution

| Weight key pattern | Resolved as |
|---|---|
| `graph.max_depth` | Raw signal value (float in [0,1] or bool) |
| `llm.response_depth.deep` | `True` (→1.0) if `response_depth == "deep"`, else `False` (→0.0) |
| `llm.specificity.high` | `True` if value >= 0.75 |
| `llm.specificity.mid` | `True` if 0.25 < value < 0.75 |
| `llm.specificity.low` | `True` if value <= 0.25 |
| `graph.node.exhausted.true` | `True` if node signal `exhausted == True` |

Threshold binning (`.low`/`.mid`/`.high`) applies only to float signals
normalized to [0, 1]. Categorical signals use exact string equality.

### Phase Multiplier and Bonus

Phase multipliers and bonuses are keyed by **strategy name** in the YAML
`phases:` block. Both are retrieved from `config.phases[current_phase]`:

- `signal_weights` → multiplicative (default `1.0` when absent)
- `phase_bonuses` → additive (default `0.0` when absent)

The same phase values are applied in both Stage 1 (strategy ranking) and
Stage 2 (node ranking for the winning strategy).

**Example**:
```
Base explore score: 2.5
Early phase multiplier: 1.5
Early phase bonus: 0.2
Final score = (2.5 × 1.5) + 0.2 = 3.95
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

## Correctness Requirements

1. **Phase multiplier and bonus are applied after base scoring** — never fold
   them into `signal_weights`.

2. **Node-scoped weight key namespace**: keys that should influence node ranking
   must start with `graph.node.*`, `technique.node.*`, or `meta.node.*`.
   Any other prefix routes the weight to strategy-level scoring only.

3. **Negative weights are valid** — use them for diversity penalties
   (e.g., `temporal.strategy_repetition_count: -0.5`).

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
    detected, `revitalize` is selected instead. Set `score_threshold: 0.0` (Phase 2 default)
    to disable fallback during cross-strategy comparison.

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

---

## Key Files

| File | Purpose |
|---|---|
| `src/methodologies/scoring.py` | `rank_strategy_node_pairs()`, `rank_strategies()`, `partition_signal_weights()`, `ScoredCandidate`, `SignalContribution` |
| `src/methodologies/registry.py` | `MethodologyRegistry`, `StrategyConfig`, `PhaseConfig` — YAML loading and validation |
| `src/services/methodology_strategy_service.py` | Orchestrates Stage 1 + Stage 2; retrieves phase weights/bonuses from loaded config |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Pipeline stage that calls `MethodologyStrategyService` |
| `config/methodologies/means_end_chain.yaml` | Reference methodology YAML with strategies, signal_weights, and phases |
| `config/methodologies/jobs_to_be_done.yaml` | Alternative methodology for comparison |
