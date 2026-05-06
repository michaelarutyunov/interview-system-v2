# Subsystem Debugging Guides
## Current Version: 1.0

## Logging
Logs are saved to `./logs/`

## Strategy Selection Issues
When investigating why a strategy was selected:
1. Check logs for `strategy_selected` or `strategies_ranked` entries
2. Look for phase weight and bonus application in logs
3. Verify signals detected match YAML config expectations
4. Check `src/methodologies/scoring.py` for scoring logic
5. Use synthetic interviews to reproduce patterns

## Joint Strategy-Node Scoring Debugging (D2 Architecture)
When debugging joint scoring:
- Check `rank_strategy_node_pairs()` output for score breakdown
- Look at `strategy_alternatives` list in logs: `[(strategy, node_id, score), ...]`
- Verify global and node signals are merged correctly (node signals take precedence)
- Check for negative weights from `convgraph.node.exhaustion.high` signals
- Verify phase weights (multiplicative) and bonuses (additive) are applied

## Signal Detection Debugging
- Enable debug logging: Check `signals_detected` log entries
- Verify signal namespacing: `graph.*`, `llm.*`, `temporal.*`, `meta.*`, `convgraph.node.*`, `convgraph.node.*, canongraph.node.*, interview.focus.*, meta.node.**`
- Check YAML config for signal_weights definitions
- Look for phase weight and bonus application in scoring logs

## Phase Weights and Bonuses Debugging
- Phase detection happens in `InterviewPhaseSignal` → `interview.phase`
- Phase weights retrieved from `config.phases[phase].signal_weights` (multiplicative)
- Phase bonuses retrieved from `config.phases[phase].phase_bonuses` (additive)
- Applied in `rank_strategies()` and `rank_strategy_node_pairs()` as:
  ```python
  multiplier = phase_weights.get(strategy.name, 1.0)
  bonus = phase_bonuses.get(strategy.name, 0.0)
  final_score = (base_score * multiplier) + bonus
  ```
- Check logs for `interview_phase_detected`, `phase_weights_loaded`, `phase_bonuses_loaded`

## Node Exhaustion Debugging
- Check `convgraph.node.exhaustion` for continuous exhaustion score (0.0-1.0)
- Check `convgraph.node.focus.streak` for persistent focus patterns
- Verify NodeStateTracker state for focus_count, turns_since_last_yield, current_focus_streak

## Known Failure Signatures

### Strategy monoculture (same strategy wins every turn)
1. Check repetition brakes: `interview.strategy.self_count` weight should be negative (e.g., `-0.5`), never positive
2. Compare base scores: `grep "base_score" logs/` — if one strategy's base is >2× the next, brakes can't compensate
3. Verify `node_binding` alignment: strategies with `convgraph.node.*` weights must use `node_binding: required`
4. Check `valid_when` gates aren't filtering out all alternatives for every node

### Per-concept LLM signals always zero
1. Verify `response.semantic.llm.elaboration` and `response.semantic.llm.charge` are in the methodology's `signals: llm:` list
2. Check `bridged_count` in Stage 4.7 logs — if always 0, `concept_to_node_id` mapping is failing
3. Verify `concept.text` (not `.name`) is used when building the concept→node map

### NodeStateTracker state lost between turns
1. Verify Stage 10 calls `node_state_tracker.to_dict()` and saves to `sessions.node_tracker_state`
2. Verify Stage 1 loads it via `from_dict()`
3. Check for `ValueError: Incompatible node_tracker_state schema version` — DB may have stale serialized state

### Tracked metrics split across paraphrase nodes (dual-graph mode)
1. `register_slot_memberships()` must run after Stage 4.5 creates surface-to-slot mappings
2. Check `slot_memberships_registered` log for registered counts
3. If `NodeNotTrackedError` appears in Stage 4.5, a surface node wasn't registered in Stage 4

### Graph dedup fragmentation (same concept creates multiple nodes)
1. Verify `embedding_service` is configured and spaCy model is installed
2. Check `surface_similarity_threshold` — if concepts are inconsistently named, threshold may need lowering
3. Verify `concept_naming_convention` is being followed in the methodology YAML

## Uvicorn Logging
For debugging API/pipeline issues:
```bash
# Enable uvicorn debug logging
uvicorn src.main:app --reload --log-level debug

# Check specific log files
tail -f /tmp/uvicorn_debug.log
tail -f /tmp/uvicorn_phase_test.log
```

## Known Failure Modes

_No entries yet. Add failure patterns as they are discovered in this subsystem — each entry should describe the incorrect behavior, its consequence, and the correct approach._

