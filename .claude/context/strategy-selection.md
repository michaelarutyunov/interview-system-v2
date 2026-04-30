# Strategy Selection
## Current Version: 1.0

## Core Mechanics

`StrategySelectionStage` (Stage 6) is the decision engine. It orchestrates signal detection and joint scoring to produce a selected strategy and focus node for the current turn.

**Inputs read from context:**
- `graph_state` — must be fresh (StateComputationStage must have run)
- `recent_nodes`, `recent_utterances`, `extraction`
- `strategy_history` — for temporal diversity signals
- `node_tracker` — per-node state for exhaustion signals

**Output:** `StrategySelectionOutput` with `strategy`, `focus_node_id`, `signals`, `node_signals`, `score_decomposition`.

### Joint Scoring Architecture

Strategies and nodes are scored **jointly** — all eligible (strategy, node) pairs are evaluated simultaneously, and the highest-scoring pair wins:

1. **Global signals** are detected via `GlobalSignalDetectionService`
2. **Node signals** are detected via `NodeSignalDetectionService` (initialized from `node_tracker.get_all_states().keys()`)
3. **Joint scoring** via `rank_strategy_node_pairs()` in `src/methodologies/scoring.py`:
   - For each node-bound strategy × each node in `node_signals`, compute a base score from signal weights
   - Apply phase multiplier (multiplicative) and phase bonus (additive)
   - The single highest-scoring (strategy, node) pair determines both the strategy and the focus node
4. **Conversation-level strategies** (with `node_binding: none`) are scored in parallel via `rank_strategies()` using only global signals

**Strategies with `node_binding: none`** (e.g., `revitalize`, `elaborate`, `validate`) operate at conversation level — `focus_node_id` is `None`, and `node_id = ""` appears in `score_decomposition`.

**Strategies with `valid_when` gate** are only scored for nodes where the gate signal evaluates to `True` in the node's signal dict. `node_signal_dict.get(gate_signal)` returns the signal value — `None` (missing) or `False` both exclude the (strategy, node) pair from scoring.

### Signal Detection

`GlobalSignalDetectionService` → detects global signals:
- `graph.*` — graph structure metrics (via `ComposedSignalDetector`)
- `llm.*` — response quality (batch-detected in single API call)
- `temporal.*` — strategy repetition count, turns since strategy change
- `meta.*` — interview progress, phase

`NodeSignalDetectionService` → detects node-level signals:
- Initializes `node_signals` dict from `node_tracker.get_all_states().keys()` — surface UUIDs + canonical slot IDs
- Runs all `NodeSignalDetector` subclasses (tracker-based: exhaustion, focus streak, novelty) and DB-based detectors (`ChainTopologySignalDetector` — gap_above, gap_below, is_orphan, etc.)
- Merge step: detector results are merged into `node_signals` only if their node IDs match entries in the dict (guard: `if node_id in node_signals`)
- See `.claude/context/signal-detection-graph.md` "Key Namespace Divergence" for the tracker-vs-DB key split and merge mechanics

### Phase Weights

Phase is detected via `InterviewPhaseSignal`. Phase weights are loaded from `config.phases[phase]`:

```yaml
phases:
  early:
    signal_weights:      # multiplicative
      ascend: 1.0
      ground: 1.2
    phase_bonuses:       # additive
      elaborate: 0.2
```

Scoring formula: `final_score = (base_score × phase_multiplier) + phase_bonus`

### Post-Selection Updates

After strategy + node selection, before exiting Stage 6:

1. **LLM quality bridge** — `LLMSignalBridgeStage` (Stage 4.7, runs before Stage 6) iterates `per_concept_ratings` from the LLM batch detector and routes `response.semantic.llm.elaboration` / `response.semantic.llm.charge` to each concept's mapped node via `NodeStateTracker.append_quality()`. This runs BEFORE strategy selection, so per-concept quality signals are available during scoring.
2. `update_focus()` — sets new focus as `previous_focus` for next turn, increments streak counters

## Correctness Requirements

1. **StateComputationStage must have run before Stage 6** — `graph_state` is stale if Stage 5 was skipped. Signal detectors that read `graph_state` will produce wrong scores.

2. **Phase must be detected before scoring** — `rank_strategy_node_pairs()` requires `phase_weights` and `phase_bonuses`. Without them, multipliers default to 1.0 and bonuses to 0.0, suppressing phase-based strategy shaping.

3. **`partition_signal_weights()` separates global from node-scoped weights** — strategies with `node_binding: required` have their weights partitioned: node-scoped weights (`convgraph.node.*`) route to stage-2 joint scoring; global weights route to stage-1 base. Strategies with `node_binding: none` use only global weights.

4. **Node signals must not leak into conversation-level strategy scoring** — `partition_signal_weights()` filters them out. A strategy with `node_binding: none` that references `convgraph.node.*` weights loses those weights' contribution.

5. **`strategy_alternatives` is a list of `Dict[str, Any]`** with keys `strategy`, `node_id`, `score` — not 2-tuples. Downstream consumers (`generate_transcript.py`, `generate_scoring_csv.py`) iterate these dicts.

6. **`valid_when` gate is a soft check** — `node_signal_dict.get(gate_signal)` returns `None` (falsy) when the signal key is missing. This means nodes without the gating signal are excluded from that strategy's candidate set. Surface nodes (UUIDs) carry chain topology signals; canonical slot nodes do not (see `signal-detection-graph.md`).

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Wrong strategy always selected regardless of signals | Phase weights not loading (`interview.phase` absent) | Check `InterviewPhaseSignal` detection; verify methodology YAML has `phases` section |
| Strategy with `convgraph.node.*` weights never fires | `node_binding: none` — `partition_signal_weights()` strips node-scoped weights | Change to `node_binding: required` so weights route to joint scoring |
| Phase multipliers applying but not bonuses | `phase_bonuses` key missing from YAML phase config | Add `phase_bonuses:` section under affected phase |
| `focus_node_id` is always `None` for node-bound strategies | `node_signals` dict is empty (NodeSignalDetectionService not running) | Check Stage ordering and NodeSignalDetectionService injection |
| Chain topology signals absent from scoring | Key namespace mismatch — detector returns surface UUIDs, `node_signals` initialized from slot IDs | Verify surface nodes are kept in tracker after remap (see `signal-detection-graph.md`) |
| Ground strategy dominates despite calibration | Phase multiplier asymmetry + `has_attribute_foundation` weight ratio + weak repetition brake | Equalize structural weights, strengthen self_count brake, reduce early phase gap |

## Known Failure Modes

_No entries yet. Add failure patterns as they are discovered in this subsystem — each entry should describe the incorrect behavior, its consequence, and the correct approach._


## Key Files

- `src/services/turn_pipeline/stages/strategy_selection_stage.py` — orchestrates signal detection + joint scoring
- `src/services/methodology_strategy_service.py` — `select_strategy_and_focus()`, routes to `rank_strategy_node_pairs()`
- `src/methodologies/scoring.py` — `rank_strategy_node_pairs()` (joint), `rank_strategies()` (conversation-level), `partition_signal_weights()`
- `src/methodologies/registry.py` — YAML config loader
- `src/services/global_signal_detection_service.py` — global signal orchestration
- `src/services/node_signal_detection_service.py` — per-node signal detection + merge
- `src/services/focus_selection_service.py` — resolves `focus_node_id` to label + node_type
- `src/signals/meta/` — Meta signal implementations (InterviewPhaseSignal, etc.)
- `config/methodologies/*.yaml` — strategy configs, `signal_weights`, `phase_bonuses`, `node_binding`
