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
| `convgraph.state.max_depth` | Raw signal value (float in [0,1] or bool) |
| `response.semantic.llm.elaboration` | Raw float [0,1]: mean per-concept elaboration score; depth categories derived from this |
| `convgraph.node.llm.elaboration.high` | `True` (→1.0) if node-level mean elaboration ≥ 0.67, else `False` (→0.0) |
| `convgraph.node.llm.elaboration.low` | `True` (→1.0) if node-level mean elaboration < 0.34, else `False` (→0.0) |
| `convgraph.node.exhaustion.high` | `True` if node exhaustion score ≥ 0.67 |
| `convgraph.node.chain.gap.above.true` | `True` if node has no outgoing edge to a higher ontology level |
| `convgraph.node.chain.gap.below.true` | `True` if node has no incoming edge from a lower ontology level |
| `convgraph.node.chain.level.skip.true` | `True` if node has a direct leads_to edge skipping >1 ontology level |
| `convgraph.node.chain.branching_deficit` | Float in [0,1]: 1 - (actual_siblings / expected_siblings) |
| `convgraph.node.chain.fan_in` | Int: count of distinct origin-level nodes with paths to this node |
| `convgraph.node.chain.level.gap_size` | Int: ontology levels between this node and terminal/origin |
| `convgraph.node.chain.has_attribute_foundation.true` | `True` if a downward path reaches an attribute-level node |
| `convgraph.node.chain.has_terminal_apex.true` | `True` if an upward path reaches a terminal-value node |
| `convgraph.node.is_orphan.true` | `True` if node has no edges at all (isolated) |
| `convgraph.node.recency` | Float in [0,1]: how recently the node was last discussed |
| `convgraph.node.llm.elaboration.low` / `.mid` / `.high` | `True` if per-concept elaboration score falls in bin |
| `convgraph.node.llm.charge.positive` / `.negative` | `True` if per-concept charge (emotional tone) is positive/negative |
| `convgraph.node.llm.has_quality_data.true` | `True` if node has at least one per-concept LLM rating history entry |

Threshold binning (`.low`/`.mid`/`.high`) applies only to float signals
normalized to [0, 1]. Categorical signals use exact string equality.
Bool signals use `.true`/`.false` suffix. Integer signals (e.g., `fan_in`,
`level_gap_size`) are multiplied directly by weight — use small weights to
avoid dominance.

### Per-Concept LLM Rating Propagation

The LLM signal detector produces **per-concept ratings** (`elaboration`, `charge`)
for each extracted concept, plus **global ratings** (`certainty`, `engagement`).
Per-concept ratings are routed from concepts to graph nodes in a dedicated
pipeline stage:

- **LLMPrefetchStage (Stage 3.1)** fires the LLM batch call as an `asyncio.Task`
  (non-blocking, overlapped with Stages 3–4.5).
- **LLMSignalBridgeStage (Stage 4.7)** awaits the prefetch task, maps per-concept
  ratings to graph nodes via `concept_to_node_id`, and appends them to
  `NodeState.quality_history` via `NodeStateTracker.append_quality()`.
  The stage emits an `LLMSignalBridgeOutput` contract on `PipelineContext`.

Stage 4.7 is the earliest point where all bridge dependencies are satisfied:
concept_to_node_id (from GraphUpdateStage, Stage 4), NodeStateTracker keys
(from Stages 4 + 4.5), and LLM results (from Stage 3.1).

**MethodologyStrategyService** reads global LLM signals from
`context.llm_signal_bridge_output.global_signals` (the Stage 4.7 contract)
and passes them to `GlobalSignalDetectionService.detect()` via the
`llm_global_signals` parameter, which merges them into the non-LLM global
signals. The old `detect_with_per_concept()` method has been removed.

Node-level signal detectors consume the quality history appended by Stage 4.7:

| Signal key | Source | Description |
|---|---|---|
| `convgraph.node.llm.elaboration` | `NodeElaborationSignal` | Avg per-concept elaboration for this node, binned to low/mid/high |
| `convgraph.node.llm.charge` | `NodeChargeSignal` | Dominant emotional charge for this node, mapped to positive/negative |
| `convgraph.node.llm.has_quality_data` | `NodeHasQualityDataSignal` | `True` if node has any quality history entries |

This bridges the gap between extraction-time concepts and strategy-time node
scoring. `response.semantic.llm.elaboration` (mean per-concept) drives response depth
categories (via `_score_to_category()` in `batch_detector.py`) for backward
compatibility with `response.semantic.llm.engagement.trend` and `meta.node.opportunity` signals.

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

## Methodology Architecture (v2)

### Active Methodology Family

All active methodologies live in `config/methodologies/`. Retired configs are in
`config/methodologies/legacy/` for reference only.

| File | Strategies | valid_when gates | chain_threshold | Structure |
|---|---|---|---|---|
| `means_end_chain_v2_strict.yaml` | 7 | ascend, ground, bridge, branch, anchor | 0.15 | 5-level hierarchy |
| `means_end_chain_v2_flex.yaml` | 7 | Same as strict | 0.15 | Same hierarchy, no permitted_connections |
| `jobs_to_be_done_v2.yaml` | 7 | ascend, ground, probe_pain, anchor | 0.05 | 2-level (functional → emotional/social) |
| `critical_incident_v2.yaml` | 7 | ascend, ground, bridge, anchor | 0.10 | 5-level narrative hierarchy |
| `customer_journey_mapping_v2.yaml` | 8 | anchor only | 0.05 | Flat (no chain topology signals) |
| `repertory_grid_v2.yaml` | 8 | explore_construct, anchor | 0.03 | Flat dimensional (no chain topology) |

**Design principle**: Each methodology defines its own strategy names (Option B
from refitting doc), but shares the same scoring engine. The strategy name is UI;
the `valid_when` gate is the contract. Chain topology signals (gap_above, gap_below,
level_skip, branching_deficit) only fire for methodologies with ontology levels.

---

## Chain-Aware Strategy Selection (MEC)

### Overview

The Means-End Chain methodology uses 6 chain-aware strategies that exploit
graph topology to drive interview flow. Each strategy targets a specific
structural gap or opportunity in the knowledge graph.

Legacy strategies (`deepen`, `explore`, `clarify`, `reflect`) have been removed
from MEC YAMLs. The default fallback strategy in code is now `ascend` (was
`deepen`). `validate` was added as a late-phase closing strategy in v3.1.

### The 7 MEC Strategies

| Strategy | `node_binding` | `valid_when` | Purpose |
|---|---|---|---|
| `ascend` | `required` | `convgraph.node.chain.gap.above` | Extend an incomplete chain upward toward terminal values |
| `ground` | `required` | `convgraph.node.chain.gap.below` | Establish causal antecedents for ungrounded high-level nodes |
| `bridge` | `required` | `convgraph.node.chain.level.skip` | Fill missing intermediate levels in a chain with skipped ontology levels |
| `branch` | `required` | `convgraph.node.chain.branching_deficit` | Expand breadth where methodology expects more siblings |
| `anchor` | `required` | `convgraph.node.is_orphan` | Connect isolated nodes to existing graph structure |
| `revitalize` | `none` | *(none)* | Conversation-level fallback for fatigue/disengagement |
| `validate` | `none` | *(none)* | Late-phase closing strategy — generates closing question |

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

1. Reads `response.semantic.llm.engagement.trend` — if `"fatigued"`, triggers fallback
2. Reads `response.semantic.llm.engagement` — if `< 0.3` (float), triggers fallback
3. Fallback selects `revitalize` (if defined in the methodology's strategies)

The production threshold in MEC YAMLs is `score_threshold: 0.15`. Set to `0.0`
to disable fallback (used during cross-strategy comparison testing).

If no fatigue/engagement condition is met despite the low score, the best-scoring
strategy is used regardless — the fallback is conservative, not mandatory.

Late-phase closing is handled by `validate` (node_binding: none,
generates_closing_question: true), which uses heavy early/mid phase gates
(`interview.phase.early: -3.0`, `mid: -3.0`) to prevent premature
termination. `validate` is the preferred late-phase strategy across all v2
methodologies.

### Chain Topology Signals

Chain topology signals are computed by `ChainTopologySignalDetector`
(`src/signals/graph/chain_topology_signals.py`). They are pure graph topology —
no LLM calls.

**Source architecture**:
- `ChainTopologySignalDetector` (extends `NodeSignalDetector`) computes a nested
  dict per node under the key `convgraph.node.chain.role`
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
| `convgraph.node.chain.gap.above` | bool | Node has no outgoing edge to a higher ontology level AND is non-terminal |
| `convgraph.node.chain.gap.below` | bool | Node has no incoming edge from a lower ontology level AND is above origin level |
| `convgraph.node.chain.level.skip` | bool | Node has a direct `leads_to` edge that skips >1 ontology level |
| `convgraph.node.chain.branching_deficit` | float [0,1] | 1 - (actual_siblings / expected_siblings); 1.0 = full deficit |
| `convgraph.node.chain.fan_in` | int | Count of distinct origin-level nodes with paths to this node |
| `convgraph.node.chain.level.gap_size` | int | Ontology levels between this node and terminal/origin |
| `convgraph.node.chain.has_attribute_foundation` | bool | Downward path (reverse edges) reaches an attribute-level node |
| `convgraph.node.chain.has_terminal_apex` | bool | Upward path (forward edges) reaches a terminal-value node |

**Non-chain methodologies**: `ChainTopologySignalDetector` returns an empty dict
for methodologies with fewer than 2 distinct ontology levels (e.g., JTBD, CJM,
Repertory Grid, Critical Incident). Signal absence means zero contribution to
scoring.

**Additional per-node signals used by chain-aware strategies**:

| Signal key | Type | Description |
|---|---|---|
| `convgraph.node.is_orphan` | bool | Node has no edges at all (used by `anchor` strategy's `valid_when`) |
| `convgraph.node.recency` | float [0,1] | How recently the node was last discussed (higher = more recent) |
| `convgraph.node.exhaustion` | float [0,1] | How exhausted the node is from repeated probing (negative weight in strategies) |

### Chain Lifecycle Matrix

The `has_attribute_foundation` and `has_terminal_apex` signals encode where a node sits in its chain's lifecycle. MEC scoring uses them to steer strategy selection:

| foundation | apex | Best strategy | Why |
|---|---|---|---|
| False | False | `ground` | Chain is floating — no attribute root and no terminal goal |
| True | False | `ascend` | Chain is grounded — extend upward toward terminal |
| False | True | `ground` | Terminal reached, but chain lacks an attribute below |
| True | True | `branch` | Chain is complete — add breadth from new attributes |

**Weight design in `means_end_chain_v2_strict.yaml`** (N7 + Tier 2 calibration):
- `ascend`: `has_attribute_foundation.true +0.200`, `has_attribute_foundation.false -0.5`; `convgraph.node.exhaustion: -0.8`, `convgraph.node.focus.count.high: -0.8`, `convgraph.node.focus.count.medium: -0.4`, `interview.strategy.self_count: -1.5`
- `ground`: `has_attribute_foundation.false +0.250`, `has_attribute_foundation.true -0.2`
- `branch`: `has_attribute_foundation.true +0.3`, `has_terminal_apex.true +0.5`
- `anchor`: `is_orphan.true: +0.50`
- `validate`: heavy early/mid phase gates (`interview.phase.early: -3.0`, `mid: -3.0`), closing question generator

The old `convgraph.chain.completion.has_complete: -0.2` suppressor on `ascend` was removed — the chain-lifecycle signals provide a more principled replacement.

**f965 migration (per-concept LLM signals)** — legacy LLM signals (`response_depth`, `specificity`, `valence`, `intellectual_engagement`) were replaced by per-concept `elaboration`/`charge` plus global `certainty`/`engagement`. Weight equivalents:
- `llm.response_depth.deep` → `convgraph.node.llm.elaboration.high`
- `llm.specificity.low` → `convgraph.node.llm.elaboration.low`
- `llm.valence.low` → `convgraph.node.llm.charge.negative`
- `llm.valence.high` → `convgraph.node.llm.charge.positive`

**N7 calibration changes** (from N6 baseline — targeting 15-turn interview):
- Ascend `exhaustion_score` strengthened: -0.6 → -0.8
- Ascend `focus_count.high` strengthened: -0.4 → -0.8; `focus_count.medium: -0.4`
- Ascend `repetition_count` strengthened: -0.5 → -1.5
- Ascend added `elaboration.high: +0.4` (triggers laddering on deep content)
- Ground `has_attribute_foundation.false` reduced: 0.400 → 0.250
- Validate added `elaboration.high: +0.3`, `elaboration.mid: +0.2`
- Anchor `is_orphan.true` boosted: +0.35 → +0.50 (orphan rate grew to 12.8%, above 10% threshold)
- Branch `has_terminal_apex.true` boosted: +0.4 → +0.5 (better compete once chain is complete)
- Late phase `branch` multiplier: 0.8 → 1.1 + phase_bonus 0.30
- Late phase `validate` added as primary strategy (1.5x + 0.2 bonus)

**N6 calibration changes** (from N5 baseline):
- Ground `has_attribute_foundation.false` reduced from +0.6 → +0.4 (was causing 10-turn ground streaks; ground now competes rather than dominates in F+F state)
- Revitalize `interview.strategy.self_count` restored to +0.15 (was removed in N5; phase-gated via multipliers to prevent early bursts)
- Early phase: `ground` multiplier boosted to 1.4 (was 1.1) to establish attribute foundation before ascending
- Mid phase: `ascend` reduced 1.4→1.3, `ground` increased 1.2→1.3 — equalized to let node signals decide
- Mid phase: `ascend` `phase_bonus` 0.15 removed — was pushing ascend past all competition structurally

**Emergent behavior from additive weights** (N7):
- F+F: ground gets +0.4, ascend gets -0.5 → ground dominates
- T+F: ground gets -0.2, ascend gets +0.4, but exhaustion/focus_count brakes prevent circular re-visits
- F+T: ground gets +0.4, ascend gets -0.5 → ground dominates
- T+T: branch gets +0.8 (foundation+apex), late phase 1.1x+0.10 → branch fires once chain complete

These weights are calibrated via simulation. The key validation signal is **attribute node count by turn 4** — if still 0–1 attributes, ground weights need strengthening. For 15-turn interviews, also check **orphan rate < 10%** and **branch fires at least once in late phase**.

---

## Calibration Learnings (Phase 4)

Phase 4 (2026-04-15 through 2026-04-17) was a multi-tier calibration exercise across all five methodologies. The process exposed three architectural issues and produced quantified guidance for future tuning.

### 1. Strategy-Scoped Repetition Signals

`interview.strategy.self_count` previously returned a single scalar equal to the frequency of the **last-selected** strategy over the last 5 turns. The scorer applied this scalar to **every** candidate using each candidate's own weight. This meant:
- `ascend` with weight `-1.5` was penalized whenever `ground` (weight `-0.15`) repeated, because the shared scalar (~0.6) × `-1.5` = `-0.90` penalty.
- The feedback sign was inverted: the strategy most needing to fire (to break monoculture) was punished in proportion to how entrenched the dominant strategy was.

**Fix (2026-04-17)**: `StrategyRepetitionCountSignal.detect()` now returns `{signal_name: {strategy_name: normalized_count}}` — a per-strategy map. `scoring.py` gained `_resolve_strategy_scoped_signals()` + `STRATEGY_SCOPED_SIGNALS` registry. Called once per candidate before weight application, flattening the dict to the candidate's own scalar (0.0 if the strategy hasn't fired in the window).

**Implication**: All repetition brakes now behave as genuine self-brakes. Do not reintroduce the old scalar pattern.

### 2. Base Score Asymmetry vs. Repetition Brake Strength

When a strategy's typical base score exceeds its repetition brake magnitude by >3×, the brake cannot prevent monoculture within a 10-turn interview.

| Strategy | Typical Base | Repetition Brake | Ratio | Outcome |
|----------|-------------|------------------|-------|---------|
| CJM `deepen_stage` | 2.3 | -0.6 | 3.8× | Won 8/10 turns despite "brake" |
| RG `explore_construct` | 1.4 | -0.4 | 3.5× | Won 3/10; runner-up never competitive |
| MEC `ascend` (pre-fix) | ~0.8 | -1.5 | 0.5× | Never fired — over-braked |

**Rule of thumb**: repetition brake magnitude should be ≥50% of the strategy's typical base score when that strategy is intended to fire 2–3× per interview. For dominant structural strategies (base >1.5), either:
- Reduce structural positive mass (audit which signals contribute >0.5)
- Strengthen brake to ≥1.0
- Add a `convgraph.node.focus.count.high` penalty (-0.8 to -1.0) that compounds with repetition

### 3. Node Binding Mismatch Silently Strips Weights

`partition_signal_weights()` routes all `convgraph.node.*` / `interview.focus.*` / `meta.node.*` weights to Stage 2 (joint strategy-node scoring). If a strategy is `node_binding: none`, it never enters Stage 2 — all node-scoped weights are silently discarded.

**Example from RG**:
```yaml
node_binding: none
signal_weights:
  convgraph.node.is_orphan.true: 0.7      # stripped — never scored
  convgraph.node.focus.streak.none: 0.5    # stripped — never scored
  convgraph.node.llm.elaboration.low: 0.4      # stripped — never scored
  response.semantic.llm.engagement: 0.5                   # retained — only ~1.0 of positive mass
```

Result: `triadic_elicit` competed on ~1.0 positive mass vs. `explore_construct` at ~2.7. Never selected across 10 turns.

**Fix**: Strategies with `convgraph.node.*` weights must use `node_binding: required`. The registry does NOT validate this alignment — it is a semantic contract.

**Fixed (Phase 4.3)**: RG `triadic_elicit` and `explore_ideal` flipped to `node_binding: required`. Remaining `node_binding: none` strategies in RG (`revitalize`, `validate`) have no `convgraph.node.*` weights that affect selection — their node-scoped weights are secondary (revitalize's fresh-territory seeking) or decorative (validate's summary mode), and both strategies function correctly on global signals alone.

### 4. Escape Valve Positive Feedback

Using a *positive* weight on `interview.strategy.self_count` (e.g., `revitalize: +0.15`) creates a self-reinforcing loop:
1. Structural strategies are suppressed (brakes, valid_when gates)
2. `revitalize` wins as path of least resistance
3. `+0.15` makes it stronger each turn it fires
4. It fires more → it gets stronger → monoculture

Observed in CIT (70% revitalize), RG, and CJM.

**Fix**: Flip to a negative brake. JTBD was fixed first (`+0.15 → -0.5`) and validated; the same flip was applied to CIT, RG, and CJM.

### 5. Per-Concept Signal Weight Guidance

Phase C wiring (per-concept LLM ratings → `NodeStateTracker` → node signals) is functional but underutilized. Per-concept signals (`convgraph.node.llm.elaboration.*`, `convgraph.node.llm.charge.*`) typically carry weights of 0.1–0.2, while structural graph signals carry 0.25–0.40. The result: per-concept signals rarely determine the winner.

**Guideline**: At least one strategy per methodology should use per-concept signals at weight ≥0.3 to ensure they can compete with structural signals. Good pairings:
- `ascend` / `elaborate` → `convgraph.node.llm.elaboration.high` (deep content → ladder up)
- `triadic_elicit` → `convgraph.node.llm.elaboration.low` (shallow content → needs triadic probing)
- `track_emotions` → `convgraph.node.llm.charge.positive` / `.negative` (emotional content → trace it)
- `elicit_narrative` → `convgraph.node.llm.charge.*` (emotional charge → narrate it)

### 6. Persona-Driven Graph Starvation

Sparse-response personas (`brief_responder`) produce few extracted concepts → small graph → node-bound strategies have few nodes to score against. Conversation-level strategies (`revitalize`, `validate`) win by elimination, even with correct brakes.

This is a **methodology-agnostic dynamic**, not a YAML-tunable issue. The correct response is NOT to boost node-bound strategies artificially — it's to accept that some persona/methodology combinations produce degraded interviews by design, or to add an active-probing strategy (new-topic-seeder) that fires when `convgraph.state.node.count.low` is true.

### 7. Calibration Workflow Principle

Phase 4 demonstrated that weight tuning must follow a strict order:
1. **Validate scoring architecture first** — confirm repetition signals, node binding, and valid_when gates behave correctly before touching weights.
2. **Measure base score distributions** — extract `base_score` from `ScoredCandidate` for every strategy before applying brakes. If one strategy's base is >2× the next, no amount of braking will produce diversity.
3. **Tune brakes, not just positive mass** — a strategy with strong positive signals needs an equally strong brake to prevent monoculture.
4. **Re-test with personas that stress the brake** — `single_topic_fixator` tests rotation; `brief_responder` tests starvation; `verbose_tangential` tests valid_when gate discipline.

---

## Correctness Requirements

1. **Phase multiplier and bonus are applied after base scoring** — never fold
   them into `signal_weights`.

2. **Node-scoped weight key namespace**: keys that should influence node ranking
   must start with `convgraph.node.*`, `interview.focus.*`, or `meta.node.*`.
   Any other prefix routes the weight to strategy-level scoring only.

3. **Negative weights are valid** — use them for diversity penalties
   (e.g., `interview.strategy.self_count: -0.5`, `convgraph.node.exhaustion: -0.4`).

4. **Strategy names in `phases:` must match names in `strategies:`** — the
   registry validates this at load time and raises `ValueError` on mismatch.

5. **`node_binding` controls Stage 2 inclusion**:
   - `required` (default): strategy participates in joint strategy-node ranking
   - `none`: strategy receives one score in Stage 1 only; no node is targeted

6. **All signals must be declared in `signals:`** — the registry validates every
   `signal_weights` key against known signal names at load time.

7. **Unbounded count signals are rejected in `signal_weights`** — `convgraph.state.node.count`,
   `convgraph.state.edge.count`, and `convgraph.state.node.orphan_count` return raw integers that can't be
   safely multiplied by weights. The registry raises `ValueError` at load time if
   any of these appear in a strategy's `signal_weights`. Use normalized or
   threshold-binned variants instead (e.g., `convgraph.state.node.count.low`).

8. **`valid_when` gates strategy-node pairs** — a strategy with `valid_when: convgraph.node.chain.gap.above`
   is only scored for nodes where that signal is `True`. Invalid pairs are skipped entirely
   (no score, no contribution). This is a hard gate, not a weight.
   - `valid_when` must reference a known signal name (validated at load time)
   - Only valid for `node_binding: required` strategies (not `node_binding: none`)
   - **Gate signals can be bool OR float.** `gap_above`, `gap_below`, `is_orphan`, `level_skip`
     return `bool`. `branching_deficit` returns `float` in [0,1]. The gate check uses truthiness
     (`not gate_value`), not identity (`is not True`). Never write `gate_value is True` — it
     silently excludes all float signals because `1.0 is True` is `False` in Python.

9. **Chain topology signals are flat per-node** — `ChainTopologySignalDetector` returns a
   nested dict per node. `NodeSignalDetectionService` flattens it into individual signal keys:
   - `convgraph.node.chain.gap.above`, `convgraph.node.chain.gap.below`, `convgraph.node.chain.level.skip`
   - `convgraph.node.chain.branching_deficit`, `convgraph.node.chain.fan_in`, `convgraph.node.chain.level.gap_size`
   - `convgraph.node.chain.has_attribute_foundation`, `convgraph.node.chain.has_terminal_apex`
   Use these flat keys in `signal_weights` and `valid_when`. The parent key
   `convgraph.node.chain.role` also remains available but holds the full dict.

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
| Node-level signal weight treated as strategy-level (ignored in node ranking) | Weight key missing `convgraph.node.*` / `interview.focus.*` / `meta.node.*` prefix | Rename key to correct namespace |
| All strategies scoring equally (≈ 0) | No `signal_weights` defined, or no declared signals are firing | Verify `signal_weights` in YAML and check that signals listed under `signals:` are detected at runtime |
| `strategies_ranked` log shows unexpected order | `node_binding: none` strategy competing against node-binding strategies in Stage 2 | `node_binding: none` strategies are Stage 1 only; ensure the consuming code picks from the right ranking list |
| `ValueError` at startup: unknown strategy in phases | Strategy renamed in `strategies:` but not updated in `phases:` | Sync both sections; registry enforces referential integrity |
| `ValueError` at startup: unbounded count signal in signal_weights | `convgraph.state.node.count`, `convgraph.state.edge.count`, or `convgraph.state.node.orphan_count` used as weight key | Remove the raw count key; use a normalized or binned variant |
| `valid_when` strategy never fires | `valid_when` references a known signal but the signal is never True for any node | Check that chain topology signals are computed (methodology must be chain-based, graph must have nodes) |
| `valid_when` strategy never fires despite signal returning truthy float | `gate_value is not True` identity check rejects floats (e.g. `branching_deficit=1.0` is truthy but `1.0 is True` is `False` in Python) | Use truthiness check: `if not gate_value` — handles bool, float, and None correctly. Fixed in `scoring.py` 2026-04-14. |
| New strategy scores near zero despite valid_when passing | Chain topology signal sub-keys not resolving | Ensure flat sentinel classes are imported via `src/signals/__init__.py`; check flattening in `NodeSignalDetectionService` |
| Legacy strategy name (`deepen`, `explore`, `clarify`, `reflect`) in YAML or code | These strategies were removed from MEC methodologies | Replace with the appropriate chain-aware strategy (see 7 MEC Strategies table above) |
| Old LLM signal key (`llm.specificity`, `llm.valence`, `llm.intellectual_engagement`) in YAML weights or tests | Pre-taxonomy names removed during e4030c4 rename | Use: `specificity` → `convgraph.node.llm.elaboration.*`; `valence` → `convgraph.node.llm.charge.*`; `intellectual_engagement` → split across `elaboration` and `charge` |
| Revitalize selected too aggressively | `score_threshold` too high, causing low-scoring but valid strategies to be bypassed | Lower `chain_completion.score_threshold` in YAML (production: 0.15) |

---

## Key Files

| File | Purpose |
|---|---|
| `src/methodologies/scoring.py` | `rank_strategy_node_pairs()`, `rank_strategies()`, `partition_signal_weights()`, `ScoredCandidate`, `SignalContribution` |
| `src/methodologies/registry.py` | `MethodologyRegistry`, `StrategyConfig` (with `valid_when` field), `PhaseConfig` — YAML loading and validation |
| `src/services/methodology_strategy_service.py` | Orchestrates joint strategy-node scoring via `select_strategy_and_focus()`; reads LLM global signals from `context.llm_signal_bridge_output`; threshold fallback logic; retrieves phase weights/bonuses from loaded config |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Pipeline stage that calls `MethodologyStrategyService` |
| `src/services/turn_pipeline/stages/llm_signal_bridge_stage.py` | Stage 4.7: awaits LLM prefetch task, routes per-concept ratings to `NodeStateTracker.append_quality()`, emits `LLMSignalBridgeOutput` contract |
| `src/services/global_signal_detection_service.py` | Detects non-LLM global signals; merges pre-fetched LLM global signals from Stage 4.7 contract via `llm_global_signals` parameter |
| `src/signals/graph/chain_topology_signals.py` | `ChainTopologySignalDetector` — computes per-node chain topology signals (gap_above, gap_below, level_skip, branching_deficit, fan_in, level_gap_size, chain.has_attribute_foundation, chain.has_terminal_apex); flat sentinel classes for registry |
| `src/signals/graph/graph_traversal.py` | Shared graph traversal utilities — `build_adjacency_list`, `build_reverse_adjacency_list`, `get_node_type_map`, `bfs_reachable`, `bfs_to_target` |
| `config/methodologies/means_end_chain_v2_strict.yaml` | Reference MEC methodology YAML with 6 chain-aware strategies, valid_when gates, signal_weights, score_threshold, and phases |
| `config/methodologies/jobs_to_be_done_v2.yaml` | JTBD methodology — 2-level hierarchy with ascend/ground gates, chain_threshold 0.05 |
| `config/methodologies/critical_incident_v2.yaml` | CIT methodology — narrative hierarchy with ascend/ground/bridge gates |
| `config/methodologies/customer_journey_mapping_v2.yaml` | CJM methodology — flat ontology, no chain topology signals |
| `config/methodologies/repertory_grid_v2.yaml` | RG methodology — dimensional/comparative, no chain topology signals |
