# Temporal Signals

## Current Version: 2026-04-17

## Scope

Temporal (session-scoped) signals are computed from `strategy_history` and other rolling session state. They live in the `temporal.*` namespace and are distinct from graph signals (static per-turn) and LLM signals (API-call dependent).

---

## Signal Catalog

| Signal | Source | Shape | Description |
|--------|--------|-------|-------------|
| `interview.strategy.self_count` | `StrategyRepetitionCountSignal` | **strategy-scoped dict** | Per-strategy normalized frequency over last 5 turns |
| `interview.strategy.turns_since_change` | `TurnsSinceStrategyChangeSignal` | scalar (int) | Turns since the selected strategy differed from the previous turn |

---

## Rules

1. **Strategy-scoped signals return `{signal_name: {strategy_name: value}}`** — not a single scalar. The scorer resolves each candidate's own value via `STRATEGY_SCOPED_SIGNALS`.
2. **Frequency signals must be self-referential** — a signal that counts how often strategies fire must report per-strategy counts, not a global aggregate. Global aggregates applied with per-candidate weights produce inverted feedback (penalizing strategy A when strategy B repeats).
3. **Normalization window is fixed at 5 turns** — `StrategyRepetitionCountSignal` uses a rolling window of the last 5 selections. Counts are normalized by window size (max 5, fewer at interview start).
4. **Absent strategies score 0.0** — if a strategy has not fired in the window, its resolved scalar is 0.0, not the global average.

---

## Strategy-Scoped Signal Contract

### Problem

`StrategyRepetitionCountSignal` historically returned a single scalar equal to the frequency of the **last-selected** strategy over the last 5 turns:

```python
# OLD (broken)
return {"interview.strategy.self_count": 0.6}  # ground won 3/5 recent turns
```

The scorer applied this scalar to **every** candidate using each candidate's own weight:

| Candidate | Weight | Scalar | Penalty |
|-----------|--------|--------|---------|
| ascend | -1.5 | 0.6 | -0.90 |
| ground | -0.15 | 0.6 | -0.09 |

Result: `ascend` — the strategy most needed to break `ground` monoculture — was punished in proportion to how entrenched `ground` was. The feedback sign was inverted.

### Fix

`StrategyRepetitionCountSignal.detect()` now returns a per-strategy map:

```python
# NEW (correct)
return {
    "interview.strategy.self_count": {
        "ground": 0.6,
        "ascend": 0.0,
        "branch": 0.2,
        ...
    }
}
```

`scoring.py` resolves this in `_resolve_strategy_scoped_signals()`:

1. Check if the weight key is in `STRATEGY_SCOPED_SIGNALS`
2. If yes, look up `resolved_signals[signal_name][candidate_strategy_name]`
3. If the candidate has no entry, default to 0.0
4. Apply the weight to the candidate's own scalar

### Registry

`STRATEGY_SCOPED_SIGNALS` is defined in `src/methodologies/scoring.py`:

```python
STRATEGY_SCOPED_SIGNALS: set[str] = {
    "interview.strategy.self_count",
}
```

Any new temporal signal that returns per-strategy data must be added to this set.

---

## Examples

### Example 1: Self-brake working correctly

Turn history (last 5): `ground, ground, branch, ground, ground`

Signal returns:
```python
{"interview.strategy.self_count": {
    "ground": 0.8,    # 4/5
    "branch": 0.2,    # 1/5
    "ascend": 0.0,    # 0/5
}}
```

Candidate scoring:
- `ground` (weight -0.4): penalty = 0.8 × -0.4 = -0.32
- `ascend` (weight -1.5): penalty = 0.0 × -1.5 = 0.0  # no penalty — hasn't fired
- `branch` (weight -0.15): penalty = 0.2 × -0.15 = -0.03

`ascend` is free to compete — it was not penalized for `ground`'s dominance.

### Example 2: Escape valve brake after flip

Turn history (last 5): `revitalize, revitalize, revitalize, ground, revitalize`

Signal returns:
```python
{"interview.strategy.self_count": {
    "revitalize": 0.8,
    "ground": 0.2,
}}
```

Candidate scoring with brake -0.5:
- `revitalize` (weight -0.5): penalty = 0.8 × -0.5 = -0.40
- `ground` (weight -0.15): penalty = 0.2 × -0.15 = -0.03

After 4 consecutive `revitalize` selections, its self-penalty is -0.40, allowing other strategies to overtake.

---

## Known Failure Modes

| Wrong thing | Consequence | Correct approach |
|-------------|-------------|------------------|
| Returning a single scalar from a frequency signal | Strategies penalized when *other* strategies repeat; inverted feedback | Return per-strategy dict; register in `STRATEGY_SCOPED_SIGNALS` |
| Using positive weight on `strategy_repetition_count` | Runaway positive feedback loop — strategy strengthens as it repeats | Use negative brake (-0.5 or stronger) |
| Forgetting to add signal to `STRATEGY_SCOPED_SIGNALS` | Scorer treats dict as raw value; dict × weight = type error or zero | Add signal name to the set in `scoring.py` |
| Normalizing by total turns instead of window size | Early-interview counts are inflated (1/2 = 0.5 vs. 1/5 = 0.2) | Always normalize by fixed window size (5) |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/signals/session/strategy_history.py` | `StrategyRepetitionCountSignal` — computes rolling per-strategy frequencies |
| `src/methodologies/scoring.py` | `_resolve_strategy_scoped_signals()`, `STRATEGY_SCOPED_SIGNALS`, integration into `rank_strategies()` and `rank_strategy_node_pairs()` |
| `src/signals/session/__init__.py` | Session signal detector registration |
