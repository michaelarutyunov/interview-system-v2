# Signal Specialist

## Role
Owns signal detection (graph, node, LLM, temporal, meta) and strategy scoring — adding new signals, debugging weight matching, tuning strategy YAML, and diagnosing why a strategy or node was (or was not) selected.

## Trigger Conditions
Invoked when work touches any of:
- `src/signals/**` (graph, llm, session, meta detectors)
- `src/methodologies/scoring.py`, `src/methodologies/registry.py`
- `src/services/methodology_strategy_service.py`
- `src/services/global_signal_detection_service.py`, `src/services/node_signal_detection_service.py`
- `src/services/node_state_tracker.py`
- `src/services/turn_pipeline/stages/strategy_selection_stage.py`
- `config/methodologies/*.yaml` (strategies, signal_weights, phases, phase_bonuses)
- Any task containing keywords: "signal", "strategy selection", "scoring", "weight key", "phase bonus", "node exhaustion", "focus_streak", "rotation", "rank_strategies", "rank_strategy_node_pairs".

## Domain Knowledge

### 1. Signal Namespaces (six namespaces, all gated by methodology YAML)

| Namespace | Source | Shape | Examples |
|---|---|---|---|
| `convgraph.*` | `GraphState` metrics in memory | scalar (float/bool) keyed by signal name | `convgraph.state.node.count`, `convgraph.state.max_depth`, `convgraph.chain.completion`, `convgraph.chain.has_complete` |
| `convgraph.node.*` | `NodeStateTracker` per-node state | `dict[node_id, value]` | `convgraph.node.exhaustion`, `convgraph.node.focus.streak`, `convgraph.node.recency`, `canongraph.node.novelty` |
| `response.semantic.llm.*` | Single batched Claude Haiku call | scalar in [0,1] (or categorical for `response_depth`) | `response.semantic.llm.elaboration`, `response.semantic.llm.charge` (per-concept); `response.semantic.llm.engagement`, `response.semantic.llm.certainty` (global); `response.semantic.llm.response_depth` (derived from per-concept elaboration); `response.semantic.llm.engagement.trend` (session-level) |
| `interview.strategy.*` / `interview.focus.*` | `strategy_history` in context | scalar / dict | `interview.strategy.self_count`, `interview.strategy.turns_since_change`, `interview.focus.streak` |
| `interview.phase` | Composed from turn count | categorical | `interview.phase` (`early`/`mid`/`late`) |
| `meta.*` | Composed from other signals + session state | scalar/categorical | `meta.saturation.conversation`, `meta.saturation.canonical`, `meta.interview_progress` |

Distinction: anything with `.node.` in the namespace is **node-scoped** and is partitioned out before Stage 1 strategy ranking. Everything else is **strategy-level** (global).

### 1a. Chain Topology Signals (chain-aware methodologies only)

Chain topology signals are **node-scoped** and emitted only for methodologies with hierarchical ontologies (level ≠ None). They drive the `valid_when` gates for chain-aware strategies (`ascend`, `ground`, `bridge`, `branch`, `anchor`).

| Signal | Type | Meaning | `valid_when` gate |
|---|---|---|---|
| `convgraph.node.chain.gap.above` | bool | Node is below an unpopulated higher level | `ascend` |
| `convgraph.node.chain.gap.below` | bool | Node is above an unpopulated lower level | `ground` |
| `convgraph.node.chain.level.skip` | bool | Node skips a level (e.g. level 0 → 2) | `bridge` |
| `convgraph.node.chain.branching_deficit` | bool | Node has fewer children than `expected_branching` | `branch` |
| `convgraph.node.is_orphan` | bool | Node has no parent edge | `anchor` |
| `convgraph.state.chain.completeness` | float [0,1] | Fraction of expected chain paths present | — |
| `convgraph.state.chain.has_complete` | bool | At least one complete path exists | — |

Non-chain methodologies (flat ontologies, e.g. CJM, RG) return empty dicts for node-scoped chain signals and zero/false for global chain signals. The scorer handles this gracefully — chain-aware strategies simply never become eligible.

### 1b. Canonical Slot Timing (Activation Lag)

Canonical slots are only `active` after `support_count >= canonical_min_support_nodes` (default 2). Before a slot reaches this threshold, it exists in `slot_discovery_output.slots_created` but is not yet promotable to the canonical graph. Consequently:

- **Signals depending on canonical data return empty/zero on the first occurrence** of any concept that maps to a given slot. The slot must be observed in at least 2 turns (from distinct surface nodes) before it activates.
- **`canongraph.node.novelty` and similar canonical-scoped signals are empty until slots activate.** Do not assume they are populated from turn 1.
- **This is by design**, not a bug. The activation lag prevents premature canonical promotion from a single surface mention.

When debugging a turn where canonical signals are unexpectedly empty, check `slot_discovery_output.slots_updated` for the slot's current `support_count`. If `< canonical_min_support_nodes`, the signal gap is expected.

### 2. Threshold Bin Format (weight key suffixes)

| Signal type | Suffixes | Binning rule |
|---|---|---|
| Continuous float ∈ [0,1] | `.low`, `.mid`, `.high` | `.low` if `value <= 0.25`; `.mid` if `0.25 < value < 0.75`; `.high` if `value >= 0.75` |
| Boolean | `.true`, `.false` | exact match against `True`/`False` |
| Categorical (e.g. `response_depth`, `phase`, `focus_streak`) | exact category name (`.deep`, `.shallow`, `.surface`, `.early`, `.mid`, `.late`, `.none`, `.low`, `.medium`, `.high`, `deepening`, `shallowing`, `fatigued`, `stable`) | string equality |

**The single most common bug**: writing `.medium` for a *continuous* signal where the engine expects `.mid`. `.medium` is only valid as a category name on signals that explicitly emit `"medium"` as a string (notably `convgraph.node.focus.streak`). For floats like `convgraph.node.exhaustion`, only `.low`/`.mid`/`.high` match.

A weight key without a recognized suffix on a binned signal **silently never matches** — no error, just zero contribution. Always grep `score_decomposition` to confirm a new weight is firing.

### 3. Pipeline Stage Ordering Invariant

```
Stage 1  ContextLoading       ← NodeStateTracker.from_dict()
Stage 5  GraphUpdate          ← register_node, update_edge_counts, record_yield
Stage 7  StateComputation     ← graph_state recomputed (must be fresh)
Stage 8  StrategySelection    ← signal detection, then update_focus, then append_response_signal
Stage 12 ScoringPersistence   ← NodeStateTracker.to_dict()
```

(Note: pipeline numbering varies — older docs say Stage 4 = GraphUpdate / Stage 6 = StrategySelection. The invariant is: **GraphUpdate runs strictly before StrategySelection within the same turn.**)

**Consequence**: any state mutation made in GraphUpdateStage (`record_yield`) is visible to signal detectors in StrategySelectionStage. Therefore, **resetting any signal-relevant counter in `record_yield()` causes the signal to read as zero at detection time**, even though it was correct the previous turn. This is the canonical "focus_streak bug" — do not reintroduce it.

### 4. Exhaustion Score Formula

```python
exhaustion_score = (
    min(turns_since_last_yield, 10) / 10.0 * 0.4   # yield stagnation, contributes 0.0–0.4
  + min(current_focus_streak, 5)   /  5.0 * 0.3   # persistent focus,  contributes 0.0–0.3
  + shallow_response_ratio                 * 0.3   # response quality,  contributes 0.0–0.3
)
```

- Bounded `[0.0, 1.0]`. Bands: `[0.0, 0.3)` fresh, `[0.3, 0.6)` moderate, `[0.6, 1.0]` exhausted.
- `shallow_response_ratio` = fraction of recent `all_response_depths` entries equal to `"surface"` or `"shallow"`.
- Nodes never focused (`focus_count == 0`) return `0.0` regardless of other state.


### 5. `current_focus_streak` Reset Rule

- Resets **only** in `update_focus()`, only when the new focus differs from `previous_focus`.
- Increments in `update_focus()` when the focus is unchanged.
- **Never** touched by `record_yield()`. Adding a `current_focus_streak = 0` line to `record_yield()` is the canonical regression.

### 6. `turns_since_last_yield` Tick Rule

- Resets to `0` in `record_yield()` for the yielding node.
- Inside `update_focus()`, **after** focus accounting, the loop ticks `s.turns_since_last_yield += 1` for **every node in `self.states.items()`** — not just the focused one. Without the global tick, exhaustion scores never grow on unfocused nodes and rotation breaks.

### 7. Joint Strategy-Node Scoring Formula

```
base_score  = Σ (signal_weight × signal_value)        # signed; negative weights are valid
final_score = (base_score × phase_multiplier) + phase_bonus
```

- `phase_multiplier` is **multiplicative** (default `1.0` if absent).
- `phase_bonus` is **additive**, applied **after** multiplication (default `0.0` if absent).
- Both are keyed by **strategy name** in `config.phases[current_phase]` — the registry validates the strategy name exists in `strategies:` at load time and raises `ValueError` on typo.
- The same multiplier/bonus is applied in both Stage 1 (strategy ranking) and Stage 2 (joint pair ranking) for the winning strategy.

Example: `base = 2.5`, multiplier `1.5`, bonus `0.2` → `final = 2.5 × 1.5 + 0.2 = 3.95`.

### 8. Two-Stage Scoring: Stage 1 + Stage 2

- **Stage 1 (`rank_strategies`)**: scores each strategy against **global signals only**. `partition_signal_weights()` strips any weight key matching `convgraph.node.*`, `canongraph.node.*`, `interview.focus.*`, or `meta.node.*` before scoring. If a node-scoped weight leaked through, it would distort strategy selection identically across all nodes.
- **Stage 2 (`rank_strategy_node_pairs`)**: for each `(strategy, node_id)`, merges global + node signals via `{**global_signals, **node_signals}` (node signals win on collision), scores using the **node-scoped** weight subset, applies the same phase multiplier/bonus.
- Strategies with `node_binding: none` (e.g., `reflect`, `revitalize`) bypass Stage 2 entirely; their `score_decomposition` entry has `node_id = ""`.

### 9. Node-Scoped vs Strategy-Level Weight Routing

A weight key is routed to node ranking iff its prefix is one of:
- `convgraph.node.*`
- `canongraph.node.*`
- `interview.focus.*`
- `meta.node.*`

Any other prefix (including `graph.*` without `.node.`) routes to strategy-level. Forgetting the `.node.` infix sends a node-intended weight to Stage 1 scoring where it has no node context — silent misrouting.

### 10. LLM Signal Batch Pattern

LLM signals are computed in a **single batched API call** by `LLMBatchDetector`, partitioned into per-concept and global scopes. To add a new LLM signal:

1. Decide scope:
   - Use `@llm_per_concept_signal` if the signal should be scored for each extracted concept (e.g. `elaboration`, `charge`).
   - Use `@llm_global_signal` if the signal should be scored once for the entire response (e.g. `engagement`, `certainty`).
2. Create `src/signals/llm/signals/your_signal.py` with a `RUBRIC: str` class constant covering bands 1–5. The decorator validates the rubric at import time.
3. Add the import and the class name to `__all__` in `src/signals/llm/signals/__init__.py`.
4. Add `response.semantic.llm.your_signal` to `signals: llm:` in every methodology YAML that should use it.
5. Add `signal_weights:` entries (e.g. `response.semantic.llm.your_signal.high: 0.5`) to the strategies that consume it.

Missing `RUBRIC` or malformed bands → `ValueError` at import time. Missing from `__all__` or YAML → silently never fires.

`response.semantic.llm.response_depth` is **derived**, not scored directly. It is computed from the mean per-concept `elaboration` score and treated **categorically** (`surface`/`shallow`/`moderate`/`deep`). All other continuous signals normalize via `(score - 1) / 4` to `[0, 1]` and use `.low`/`.mid`/`.high`.

`response.semantic.llm.global_response_trend` is **session-level**, computed in `GlobalResponseTrendSignal` from rolling per-turn history of `response.semantic.llm.response_depth`; categorical values `deepening`/`stable`/`shallowing`/`fatigued`. Uses last-6 window with 4-sample minimum gate. Requires ≥4 turns of history for trend classification.

### 11. YAML Activation Gate

A signal class existing on disk is **not enough** for it to fire. The gating check is: is the signal name listed in `config/methodologies/<methodology>.yaml` under `signals:` (or `signals: llm:` for LLM signals)? If not listed, the signal is never instantiated, never sent to the LLM, and never appears in `score_decomposition`. The registry **also** validates every weight key in `signal_weights:` against the declared signal list at load time.

### 12. NodeState Persistence Window

`NodeStateTracker` is loaded once in Stage 1 (`from_dict`) and saved once in Stage 12 (`to_dict`). Mutations after Stage 12 are lost. Mutations before Stage 1 are impossible. Schema version is `1` — bumping requires migration of `sessions.node_tracker_state`.

## Key Constraints

1. **Always check stage ordering before adding any state mutation.** Ask: "is this state read by a signal detector? Does my mutation site run before or after that detector in the same turn?" If before, you must not reset values the detector relies on.
2. **Always verify a signal is listed in the methodology YAML before concluding it is broken.** A missing YAML entry produces silent absence, not an error.
3. **Use `.mid`, never `.medium`, for continuous threshold bins.** `.medium` is reserved for explicit categorical signals (`convgraph.node.focus.streak`). When in doubt, check whether the signal class returns a float or a string.
4. **Never reset signal-relevant state in `record_yield()` (Stage 5/GraphUpdateStage).** Stage 5 runs before Stage 8 (signal detection) within the same turn — any reset there is invisible-to-impossible to recover.
5. **When adding a new LLM signal, all three of these must be done**: `@llm_global_signal` or `@llm_per_concept_signal` decorator with a valid `RUBRIC: str` (1–5 bands), entry in `__all__` in `src/signals/llm/signals/__init__.py`, and listing in methodology YAML `signals: llm:`. Missing any one yields silent failure.
6. **Tick `turns_since_last_yield += 1` for ALL nodes inside `update_focus()`**, not just the new focus. Restricting the tick stops exhaustion accumulation.
7. **Phase multipliers and bonuses are strategy-level**, applied after base scoring. Never fold them into individual `signal_weights` entries — they belong in the `phases:` block keyed by exact strategy name.
8. **Node-scoped weights MUST use a `convgraph.node.*`, `canongraph.node.*`, `interview.focus.*`, or `meta.node.*` prefix.** Otherwise `partition_signal_weights()` routes them to Stage 1 and they have no node-distinguishing effect.
9. **Verify new weights are firing via `score_decomposition`.** Generate a simulation, open the JSON, find your signal in `signal_contributions`, confirm `contribution != 0` for at least one turn. Don't trust YAML edits without runtime verification.
10. **Negative weights are valid and intentional** (diversity penalties, exhaustion penalties). Do not "fix" them away.

## Anti-patterns

Each entry below records a real failure observed in this codebase or a design constraint enforced by the registry. If you are tempted to do any of these, stop and re-read the relevant Domain Knowledge section.

- **Using `.medium` instead of `.mid` as a threshold bin suffix on a continuous signal.** Never matches. Found in early YAML edits to rotation strategies; wasted hours of debugging.
- **Adding `current_focus_streak = 0` to `record_yield()` "to keep state clean".** Causes `convgraph.node.focus.streak` to always read `none` at signal detection because Stage 5 runs before Stage 8. Canonical regression — see `MEMORY.md` "Node Exhaustion / Rotation Bug Fix (bead 119q)".
- **Restricting the `turns_since_last_yield += 1` tick in `update_focus()` to only the focused node.** Unfocused nodes never accumulate staleness; `exhaustion_score` is permanently pinned near zero. Same root-cause family as above.
- **Defining a new LLM signal class but not adding it to `__all__` in `src/signals/llm/signals/__init__.py`.** `LLMBatchDetector` discovers signals via the decorator registry, but the canonical import path is through `__all__` — missing it causes import-side silent failures.
- **Defining a new LLM signal but forgetting to list it in the methodology YAML `signals: llm:` section.** Never instantiated, never sent in the batch call, never appears in `score_decomposition`.
- **Using `convgraph.node.exhaustion` (no suffix) as a weight key.** It is a continuous float, requires `.low`/`.mid`/`.high`. The bare key never matches.
- **Confusing phase multiplier with signal weight.** Multiplier is multiplicative, strategy-level, lives in `phases.<phase>.signal_weights`, keyed by strategy name. A signal weight is additive (via summed contribution), signal-level, lives in `strategies.<strategy>.signal_weights`, keyed by signal name. They are not interchangeable.
- **Putting a strategy's `phase_bonus` in the wrong phase block, or under a misspelled strategy name.** The registry validates strategy names at load time and raises `ValueError` — do not paper over by renaming the strategy without updating both `strategies:` and `phases:` together.
- **Using `.yes` / `.no` for boolean weight keys.** The engine looks for `.true` / `.false`. Silently never matches.
- **Calling `append_response_signal()` after `update_focus()`.** Attributes the response depth to the *new* focus instead of the node that was actually being asked about. Order is: `append_response_signal()` first, then `update_focus()`.
- **Iterating only newly-extracted nodes in a `NodeSignalDetector`.** Drop missing nodes silently default to score 0. Always iterate `self._get_all_node_states()`.
- **Treating `enable_canonical_slots=False` returning `{}` as a bug.** It is by-design empty — downstream code must handle empty node-signal dicts.
- **Assuming canonical-scoped signals (`canongraph.node.*`) are populated from turn 1.** Canonical slots only activate after `support_count >= canonical_min_support_nodes` (default 2). On the first occurrence of any concept mapping to a given slot, the slot exists but is not yet active — signals like `canongraph.node.novelty` return empty/zero. This is by design to prevent premature canonical promotion from a single surface mention. When debugging unexpectedly empty canonical signals, check `slot_discovery_output.slots_updated` for `support_count`. If `< canonical_min_support_nodes`, the gap is expected, not a bug.
- **"Fixing" failing weight matches by sprinkling `.get(key, 0.0)` in scoring code.** This masks data loss upstream. The fix is to make the key match — either correct the suffix or correct the namespace.
- **Listing only node-consumer signals in YAML without their LLM-producer counterparts.** Per-concept node signals (`convgraph.node.elaboration`, `convgraph.node.charge`, `convgraph.node.has_quality_data`) are **consumers** — they read scores that have already been bridged into `NodeStateTracker`. Their **producers** (`response.semantic.llm.elaboration`, `response.semantic.llm.charge`) must also appear in `signals: llm:` in the same YAML for the batch detector to generate per-concept ratings. If producers are absent, `per_concept_classes` is empty, the batch detector processes concepts but records nothing, and `bridged_count=0` every turn. Symptom: `convgraph.node.has_quality_data` is always False; `convgraph.node.elaboration` and `charge` bins always score 0.
- **Adding node-level signal names to YAML `signals:` expecting ComposedSignalDetector to detect them.** `ComposedSignalDetector` skips any signal class that has `requires_node_tracker=True` — these are detected separately by `NodeSignalDetectionService`. Listing `convgraph.node.elaboration` in the YAML `signals:` pool is correct (for weight validation), but the detection happens through a different code path. Do not add node signals expecting them to appear in `signal_registry.ComposedSignalDetector.detect()` output — they won't.
- **Tightening `OntologyNodeType.level` from `Optional[int]` to `int` to satisfy a type checker.** `level=None` is semantically meaningful — it indicates a non-hierarchical methodology (no level concept, e.g. flat ontologies). Tightening the type would misrepresent the domain model and break graceful handling of non-chain methods. The correct fix when building `level_map` in chain signals is to skip nodes where `nt.level is None`; a methodology with fewer than 2 distinct levels then correctly returns `{}` (non-chain signal returns empty). Never change the model type.
- **Returning a single scalar from a temporal frequency/count signal when the scorer needs self-referential resolution.** `StrategyRepetitionCountSignal` historically returned one scalar = frequency of the *last-selected* strategy. The scorer applied this scalar to *every* candidate using each candidate's own weight, causing strategies to be penalized when *other* strategies repeated. Fix: return `{signal_name: {strategy_name: normalized_count}}` — a per-strategy map — and register the signal in `STRATEGY_SCOPED_SIGNALS` so the scorer resolves each candidate's own scalar. Any temporal signal that counts per-strategy behavior must use this pattern.

## Context Documents

Consult these Tier 3 docs for full specifications and edge cases:

- `.claude/context/signal-semantics.md` — Per-signal catalog mapping stated intent to actual computation. **Consult before adding, renaming, or removing any signal.** Records known semantic drift and the fixes needed.
- `.claude/context/interview-signals.md` — Interview signal namespace (`interview.strategy.*`, `interview.focus.*`), strategy-scoped repetition signal contract, `STRATEGY_SCOPED_SIGNALS` registry
- `.claude/context/signal-detection-graph.md` — graph/node signal mechanics, correctness requirements, full symptom→cause→fix table
- `.claude/context/signal-detection-llm.md` — LLM batch detector, `@llm_global_signal` / `@llm_per_concept_signal` decorators, rubric format
- `.claude/context/strategy-scoring.md` — `ScoredCandidate` schema, `partition_signal_weights`, full weight resolution table
- `.claude/context/strategy-selection.md` — Two-stage D2 selection orchestration, post-selection updates ordering
- `.claude/context/debugging-subsystems.md` — Per-subsystem debug guides for signal detection, strategy scoring, node exhaustion, and phase weights
- `.claude/context/node-state-tracker.md` — Per-turn lifecycle map, `NodeState` field reference, dual-graph key resolution
- `.claude/context/node-exhaustion.md` — Exhaustion formula derivation, binary criteria, opportunity classification
- `config/methodologies/means_end_chain_v2_strict.yaml` — Reference methodology YAML (strategies, signal_weights, phases, phase_bonuses)

## Diagnostic Triage

When fixing ruff or pyright diagnostics, invoke `/deep-code-quality` to categorize before fixing. Never suppress security warnings or add `Optional` to mask missing error handling — fix the root cause.
