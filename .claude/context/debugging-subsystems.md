# Subsystem Debugging Guides

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

## Uvicorn Logging
For debugging API/pipeline issues:
```bash
# Enable uvicorn debug logging
uvicorn src.main:app --reload --log-level debug

# Check specific log files
tail -f /tmp/uvicorn_debug.log
tail -f /tmp/uvicorn_phase_test.log
```
