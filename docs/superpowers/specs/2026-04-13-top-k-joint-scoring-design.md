# Top-K Joint Scoring Design

**Date**: 2026-04-13
**Status**: Approved
**Epic**: scoring_system_review_top_k_joint_scoring (bead bbnc)

## Context

`MethodologyStrategyService.select_strategy_and_focus()` uses a 2-stage architecture:

1. **Stage 1**: `rank_strategies()` scores all strategies using global signals only, picks the #1 strategy
2. **Stage 2**: `rank_nodes_for_strategy()` scores nodes only for the Stage 1 winner

This creates a blind spot: if `ascend` wins Stage 1 but a `(bridge, node_with_level_skip)` pair would have scored higher jointly, that pair is never evaluated. The joint scoring function `rank_strategy_node_pairs()` already exists in `scoring.py` but is dead code — the service layer never calls it.

## Decision

Replace the 2-stage scoring with **joint scoring** using the existing `rank_strategy_node_pairs()` function. No K parameter is needed — with `valid_when` gates, MEC typically filters 6 strategies to 2-3 eligible ones. "All eligible" is simpler and more correct.

## Architecture

### New scoring flow

```
1. Partition strategies:
   - node_bound: strategies with node_binding='required'
   - conversation: strategies with node_binding='none'

2. Score node-bound strategies:
   rank_strategy_node_pairs(node_bound, global_signals, node_signals)
   → List of (strategy_config, node_id, score) + ScoredCandidate decomposition

3. Score conversation strategies:
   rank_strategies(conversation, global_signals, phase_weights, phase_bonuses)
   → Convert to (strategy_config, None, score) format + ScoredCandidate decomposition

4. Merge into single candidate pool, sort by score descending

5. Apply threshold fallback on best candidate's score:
   if best_score < threshold AND (fatigue OR low_engagement):
     override to revitalize

6. Return best (strategy, node_id) pair
```

### What changes

| File | Change |
|------|--------|
| `src/services/methodology_strategy_service.py` | Rewrite `select_strategy_and_focus()` to use joint scoring |
| `src/domain/models/pipeline_contracts.py` | `strategy_alternatives` type → `List[tuple[str, Optional[str], float]]` |
| `tests/services/test_methodology_strategy_service_two_stage.py` | Update for 3-tuple alternatives and unified decomposition |
| `scripts/extract_simulation_data.py` | Add `stage1_rank` / `final_rank` fields to CSV |

### What does NOT change

- `src/methodologies/scoring.py` — `rank_strategy_node_pairs()` works as-is
- Signal detection services — no changes
- `ScoredCandidate` / `SignalContribution` — no changes
- Phase weights/bonuses — applied identically inside scoring functions
- `StrategySelectionStage` — just passes through the new output format
- `ContinuationStage`, `QuestionGenerationStage` — read from context, already handle None focus

### `StrategySelectionOutput` contract changes

**Before**:
```python
strategy_alternatives: List[Union[tuple[str, float], tuple[str, str, float]]]
# Mixed 2-tuples (strategy, score) and 3-tuples (strategy, node_id, score)
```

**After**:
```python
strategy_alternatives: List[tuple[str, Optional[str], float]]
# Uniform 3-tuples: (strategy, node_id_or_None, score)
```

### `score_decomposition` format

**Before**: Combined Stage 1 (node_id="") + Stage 2 (node_id=uuid) entries.

**After**: All entries from joint scoring. Node-bound strategies have real node_ids. Conversation strategies have `node_id=None`.

### Threshold fallback behavior

Threshold continues to apply to the best candidate's final_score. If the best pair's score is below `chain_completion.score_threshold` AND fatigue/engagement signals indicate problems, override to revitalize. This preserves the existing safety behavior.

## Testing

### Updated existing tests

- `test_node_binding_none_skips_node_selection` → conversation strategy gets node_id=None
- `test_node_binding_required_selects_best_node` → still passes (best joint pair wins)
- `test_alternatives_are_strategy_level` → alternatives are now 3-tuples
- `test_stage1_decomposition_captured_in_output` → unified decomposition, no Stage 1/2 split
- `test_node_binding_none_has_only_strategy_decomposition` → node_id=None instead of ""

### New tests

1. **Strategy B beats Strategy A on joint score**: When ascend scores highest globally but bridge has a better node score on a level_skip node, the joint scorer selects (bridge, node_with_level_skip). This is the bead-mandated test.
2. **All valid_when gates filter out all strategies**: Raises `ScoringError`.
3. **Only conversation strategies eligible**: Returns (revitalize, None, score).
4. **Single node, single strategy**: Basic path correctness.

### Validation (bead c1hx)

Run before/after on 5+ simulation JSONs comparing:
- Strategy selected per turn
- Focus node per turn
- % of turns where joint scoring changes the pair
- Bridge/ground firing rate change

## Consequences

**Positive**:
- Eliminates the Stage 1 blind spot — all eligible (strategy, node) pairs are evaluated
- No new parameters — uses existing `rank_strategy_node_pairs()` as-is
- More explainable: one scoring pass, one ranking, one winner

**Negative**:
- Slightly more CPU when many nodes exist (scoring all pairs vs. just one strategy's nodes). In practice, `valid_when` gates keep the candidate pool small (2-3 strategies × N nodes).
- `alternatives` format changes from mixed 2/3-tuples to uniform 3-tuples — downstream consumers need updating

## Alternatives Considered

1. **Top-K 2-stage expansion**: Keep Stage 1/Stage 2 split, take top K strategies. Rejected — introduces arbitrary K parameter, more complex, and analyst feedback says K is unnecessary given valid_when filtering.

2. **Hybrid with phase decomposition**: Same joint scoring but add explicit global_score and node_score components to each pair. Rejected — `SignalContribution` already provides per-signal breakdown, so the namespace is recoverable without new fields.
