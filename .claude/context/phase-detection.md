# Phase Detection Specification
## Current Version: 1.0

How interview phases (early/mid/late) are determined and how they affect strategy selection weights.

## Source of Truth

Phase boundaries come from **three sources in priority order**:

| Priority | Source | How it works |
|----------|--------|--------------|
| 1 (highest) | `--phase-turns` CLI flag | Explicit `[early, mid, late]` turn counts. Stored in session config JSON as `phase_turns`. |
| 2 | `interview_config.yaml` → `phases.{exploratory,focused,closing}.n_turns` | Proportional turn counts (default: 6/7/2 = 15 total). Scaled to `max_turns`. |
| 3 (fallback) | Heuristic in `InterviewPhaseSignal.calculate_phase_boundaries()` | 10% early, last 2 turns late. Used when config is unavailable. |

**Dead config warning:** The `phase_boundaries: {early_max_turns, mid_max_turns}` key in methodology YAML is **never read** by any Python code. Removed from JTBD YAML April 2026. Do not add it to new methodologies.

## Architecture

### Implementation: `src/signals/meta/interview_phase.py`

`InterviewPhaseSignal._get_phase_boundaries(context)` returns `{early_max_turns, mid_max_turns}`. It tries each priority tier in order and returns the first that succeeds.

### Phase Multipliers: Methodology YAML

While boundaries are global, **phase-specific strategy multipliers** are methodology-specific and defined in `config/methodologies/{m}.yaml` under `phases.{early,mid,late}.signal_weights`:

```yaml
phases:
  early:
    signal_weights:
      elaborate: 1.2
      ground: 1.2
      anchor: 1.2
      ascend: 1.0
      validate: 0.2    # heavily suppressed
  mid:
    signal_weights:
      ascend: 1.3
      ground: 1.3
      validate: 0.5
  late:
    signal_weights:
      validate: 1.5
      revitalize: 1.2
    phase_bonuses:
      validate: 0.2
```

These multipliers are applied by the strategy scorer (`src/methodologies/scoring.py`) based on the phase detected by `InterviewPhaseSignal`.

## --phase-turns Flag

### CLI

```bash
uv run python scripts/run_simulation.py \
  --concept zerofizz_beverage_jtbd \
  --persona baseline_cooperative \
  --phase-turns 4-4-2
```

- `4-4-2` = 4 early turns, 4 mid turns, 2 late turns
- `max_turns` is derived as the sum (10)
- If `--max-turns` is also provided, it must equal the sum (validation error otherwise)

### Data Flow

```
--phase-turns "4-4-2"
  → run_simulation.py parses → [4, 4, 2], max_turns=10
  → SimulationService.simulate_interview(phase_turns=[4,4,2], max_turns=10)
  → _create_simulation_session stores in config: {"max_turns": 10, "phase_turns": [4,4,2]}
  → ContextLoadingStage reads config, sets ContextLoadingOutput.phase_turns
  → InterviewPhaseSignal._get_phase_boundaries() checks context.context_loading_output.phase_turns
  → Returns {early_max_turns: 4, mid_max_turns: 8}
```

### Phase Determination

```python
def _determine_phase(turn_number, early_max_turns, mid_max_turns):
    if turn_number < early_max_turns:     # turns 0-3
        return "early"
    elif turn_number < mid_max_turns:     # turns 4-7
        return "mid"
    else:                                 # turns 8-9
        return "late"
```

Turn numbers are 0-indexed. A phase boundary of `early_max_turns=4` means turns 0,1,2,3 are "early."

## Proportional Scaling (Priority 2)

When `--phase-turns` is not used, `interview_config.yaml` proportions are scaled:

```python
# interview_config.yaml: exploratory=6, focused=7, closing=2 (total=15)
# For max_turns=10:
early_max = max(1, round(10 * 6/15))  = 4
mid_max   = max(5, round(10 * 13/15)) = 9
# Result: early=0-3, mid=4-8, late=9
```

The `interview_config.phases` section:
```yaml
phases:
  exploratory:
    n_turns: 6
  focused:
    n_turns: 7
  closing:
    n_turns: 2
```

## Pipeline Integration

- **Stage 6** (StrategySelectionStage): Phase signal is detected and passed to the scorer
- **Scorer**: Applies `phases.{phase}.signal_weights` as multipliers to strategy scores
- **Phase bonuses**: `phases.{phase}.phase_bonuses` are additive bonuses applied after multiplication

## Signals Produced

```python
{
    "interview.phase": "early" | "mid" | "late",
    "interview.phase.reason": "turn_number=3, phase=early, boundaries=early<4, mid<8",
    "interview.phase.is_late_stage": True | False,
}
```

## Source Files

- `src/signals/meta/interview_phase.py` — `InterviewPhaseSignal`, boundary calculation, phase determination
- `src/core/config.py` — `interview_config` (reads `config/interview_config.yaml`)
- `config/interview_config.yaml` — `phases.exploratory/focused/closing.n_turns`
- `scripts/run_simulation.py` — `--phase-turns` flag parsing
- `src/services/simulation_service.py` — passes `phase_turns` to session config
- `src/services/turn_pipeline/stages/context_loading_stage.py` — reads `phase_turns` from session config
- `src/domain/models/pipeline_contracts.py` — `ContextLoadingOutput.phase_turns: Optional[list[int]]`
- `src/methodologies/scoring.py` — applies phase multipliers from methodology YAML
