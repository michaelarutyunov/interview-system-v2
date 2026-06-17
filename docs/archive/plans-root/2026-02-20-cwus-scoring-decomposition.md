# cwus: Live Scoring Decomposition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Capture per-signal score contributions live inside `rank_strategy_node_pairs()` and serialize them into the simulation JSON, replacing the inaccurate post-hoc recomputation in `generate_scoring_csv.py`.

**Architecture:** A new `ScoringDecomposition` dataclass captures signal-level contributions, phase adjustments, and final scores for every (strategy, node) candidate during joint scoring. This flows through the existing pipeline chain (StrategySelectionOutput → TurnResult → SimulationTurn → JSON). The CSV generator is updated to read from the JSON decomposition rather than recomputing.

**Tech Stack:** Python dataclasses, Pydantic (existing), pytest, ruff

---

## Background — The Problem

`rank_strategy_node_pairs()` in `src/methodologies/scoring.py` produces a list of `(strategy, node_id, score)` tuples. The score is a single float — there is no record of which signals fired, what their weights were, or how the phase multiplier/bonus affected the result.

`generate_scoring_csv.py` attempts to recover this information post-hoc by re-running `_get_signal_value()` against the global signals stored in the JSON. This misses everything from node-level signals (merged inside `rank_strategy_node_pairs` per node). Result: completely different scores, making the CSV useless for calibration.

The fix captures decomposition at compute time, where all information is available.

---

## Files Involved

| File | Change type |
|------|-------------|
| `src/methodologies/scoring.py` | Modify — add decomposition capture to `rank_strategy_node_pairs` |
| `src/domain/models/pipeline_contracts.py` | Modify — add `score_decomposition` field to `StrategySelectionOutput` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Modify — pass decomposition through |
| `src/services/turn_pipeline/result.py` | Modify — add `score_decomposition` field to `TurnResult` |
| `src/services/turn_pipeline/pipeline.py` | Modify — pass `score_decomposition` to `TurnResult` |
| `src/services/simulation_service.py` | Modify — add `score_decomposition` to `SimulationTurn`, serialize to JSON |
| `scripts/generate_scoring_csv.py` | Modify — read from JSON `score_decomposition` instead of recomputing |
| `tests/methodologies/test_scoring.py` | Modify/create — test decomposition output |

---

## Data Structure

```python
# One signal contribution within a scored candidate
@dataclass
class SignalContribution:
    name: str          # e.g. "llm.valence.low"
    value: Any         # resolved value (True/False/float)
    weight: float      # from YAML signal_weights
    contribution: float  # weight * value (or weight if bool True, 0 if False)

# Full decomposition for one (strategy, node) candidate
@dataclass
class ScoredCandidate:
    strategy: str
    node_id: str
    signal_contributions: list[SignalContribution]
    base_score: float         # sum of contributions
    phase_multiplier: float   # from phase config (default 1.0)
    phase_bonus: float        # from phase config (default 0.0)
    final_score: float        # (base_score * phase_multiplier) + phase_bonus
    rank: int                 # 1 = best
    selected: bool            # True for the winning candidate
```

The `score_decomposition` field in the JSON turn is a list of `ScoredCandidate` dicts, one per (strategy, node) pair evaluated.

---

## Task 1: Add decomposition dataclasses to scoring.py

**Files:**
- Modify: `src/methodologies/scoring.py`

**Step 1: Add dataclasses at top of file (after imports)**

```python
from dataclasses import dataclass, field

@dataclass
class SignalContribution:
    name: str
    value: Any
    weight: float
    contribution: float

@dataclass
class ScoredCandidate:
    strategy: str
    node_id: str
    signal_contributions: list[SignalContribution] = field(default_factory=list)
    base_score: float = 0.0
    phase_multiplier: float = 1.0
    phase_bonus: float = 0.0
    final_score: float = 0.0
    rank: int = 0
    selected: bool = False
```

**Step 2: Add `score_strategy_with_decomposition()` helper**

This is a variant of `score_strategy()` that also returns the per-signal breakdown:

```python
def score_strategy_with_decomposition(
    strategy_config: StrategyConfig,
    signals: Dict[str, Any],
) -> tuple[float, list[SignalContribution]]:
    """Score a strategy and return (score, signal_contributions)."""
    weights = strategy_config.signal_weights
    score = 0.0
    contributions = []

    for signal_key, weight in weights.items():
        signal_value = _get_signal_value(signal_key, signals)

        if signal_value is None:
            continue

        if isinstance(signal_value, bool):
            contribution = weight if signal_value else 0.0
        elif isinstance(signal_value, (int, float)):
            contribution = weight * signal_value
        else:
            contribution = 0.0

        score += contribution
        contributions.append(SignalContribution(
            name=signal_key,
            value=signal_value,
            weight=weight,
            contribution=contribution,
        ))

    return score, contributions
```

**Step 3: Run existing tests to confirm nothing broken**

```bash
uv run pytest tests/ -q -x 2>&1 | tail -10
```

Expected: same pass/fail as before (90 pass, 8 pre-existing SRL failures)

**Step 4: Commit**

```bash
git add src/methodologies/scoring.py
git commit -m "feat(scoring): add SignalContribution/ScoredCandidate dataclasses and score_strategy_with_decomposition"
```

---

## Task 2: Update rank_strategy_node_pairs to return decomposition

**Files:**
- Modify: `src/methodologies/scoring.py`

**Step 1: Write a failing test**

Create or extend `tests/methodologies/test_scoring.py`:

```python
def test_rank_strategy_node_pairs_returns_decomposition():
    """rank_strategy_node_pairs should return ScoredCandidate list alongside ranked pairs."""
    from src.methodologies.scoring import rank_strategy_node_pairs
    from src.methodologies.registry import StrategyConfig

    strategy = StrategyConfig(name="dig_motivation", signal_weights={
        "llm.engagement.high": 0.5,
        "llm.response_depth.deep": 0.3,
    })
    global_signals = {
        "llm.engagement": 0.75,     # >= 0.75 → "high" → True
        "llm.response_depth": "deep",
    }
    node_signals = {"node-1": {}}

    ranked, decomposition = rank_strategy_node_pairs(
        strategies=[strategy],
        global_signals=global_signals,
        node_signals=node_signals,
    )

    assert len(decomposition) == 1
    candidate = decomposition[0]
    assert candidate.strategy == "dig_motivation"
    assert candidate.node_id == "node-1"
    assert candidate.selected is True
    assert candidate.rank == 1
    # engagement.high fired: 0.5 contribution; response_depth.deep fired: 0.3
    assert abs(candidate.base_score - 0.8) < 0.001
    assert len(candidate.signal_contributions) == 2
```

**Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/methodologies/test_scoring.py::test_rank_strategy_node_pairs_returns_decomposition -v
```

Expected: FAIL — `rank_strategy_node_pairs` returns a list, not a tuple.

**Step 3: Update `rank_strategy_node_pairs` signature and body**

Change return type and body to also return `list[ScoredCandidate]`:

```python
def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],
    node_tracker=None,
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
) -> tuple[List[Tuple[StrategyConfig, str, float]], List[ScoredCandidate]]:
    """
    Rank (strategy, node) pairs by joint score.
    Returns (ranked_pairs, decomposition) where decomposition is a list of
    ScoredCandidate with per-signal contribution breakdown.
    """
    current_phase = global_signals.get("meta.interview.phase", "unknown")
    scored_pairs: List[Tuple[StrategyConfig, str, float]] = []
    candidates: List[ScoredCandidate] = []

    for strategy in strategies:
        for node_id, node_signal_dict in node_signals.items():
            combined_signals = {**global_signals, **node_signal_dict}

            # Use decomposition variant
            base_score, contributions = score_strategy_with_decomposition(
                strategy, combined_signals
            )

            multiplier = 1.0
            if phase_weights and strategy.name in phase_weights:
                multiplier = phase_weights[strategy.name]

            bonus = 0.0
            if phase_bonuses and strategy.name in phase_bonuses:
                bonus = phase_bonuses[strategy.name]

            final_score = (base_score * multiplier) + bonus

            scored_pairs.append((strategy, node_id, final_score))
            candidates.append(ScoredCandidate(
                strategy=strategy.name,
                node_id=node_id,
                signal_contributions=contributions,
                base_score=base_score,
                phase_multiplier=multiplier,
                phase_bonus=bonus,
                final_score=final_score,
            ))

            log.debug(
                "strategy_node_pair_scored",
                strategy=strategy.name,
                node_id=node_id,
                base_score=round(base_score, 4),
                phase_multiplier=multiplier,
                phase_bonus=bonus,
                final_score=round(final_score, 4),
                phase=current_phase,
            )

    # Sort by score descending
    ranked = sorted(scored_pairs, key=lambda x: x[2], reverse=True)

    # Build ordered index for rank/selected assignment
    ranked_order = {(s.name, nid): i for i, (s, nid, _) in enumerate(ranked)}
    for candidate in candidates:
        rank = ranked_order.get((candidate.strategy, candidate.node_id), len(ranked))
        candidate.rank = rank + 1  # 1-indexed
        candidate.selected = (rank == 0)

    log.info(
        "joint_scoring_top5",
        phase=current_phase,
        phase_weights=phase_weights,
        phase_bonuses=phase_bonuses,
        top5=[
            {"strategy": s.name, "node_id": nid, "score": round(sc, 4)}
            for s, nid, sc in ranked[:5]
        ],
    )

    return ranked, candidates
```

**Step 4: Run test to confirm it passes**

```bash
uv run pytest tests/methodologies/test_scoring.py::test_rank_strategy_node_pairs_returns_decomposition -v
```

Expected: PASS

**Step 5: Run full suite to check for regressions**

```bash
uv run pytest tests/ -q 2>&1 | tail -15
```

Expected: 90 pass (same as before). If `rank_strategy_node_pairs` callers break, fix them — they all go through `methodology_strategy_service.py` which is the next task.

**Step 6: Commit**

```bash
git add src/methodologies/scoring.py tests/methodologies/test_scoring.py
git commit -m "feat(scoring): rank_strategy_node_pairs returns (ranked_pairs, decomposition) tuple"
```

---

## Task 3: Update MethodologyStrategyService to propagate decomposition

**Files:**
- Modify: `src/services/methodology_strategy_service.py`
- Modify: `src/domain/models/pipeline_contracts.py`

**Step 1: Add `score_decomposition` to `StrategySelectionOutput` in pipeline_contracts.py**

Find the `StrategySelectionOutput` class (around line 212) and add one field:

```python
# Import at top of file (add to existing imports)
from src.methodologies.scoring import ScoredCandidate

# Inside StrategySelectionOutput:
score_decomposition: Optional[List[ScoredCandidate]] = Field(
    default=None,
    description=(
        "Per-candidate score decomposition from joint scoring. "
        "Each entry has strategy, node_id, signal_contributions (name/value/weight/contribution), "
        "base_score, phase_multiplier, phase_bonus, final_score, rank, selected."
    ),
)
```

Note: `ScoredCandidate` is a dataclass (not Pydantic), so Pydantic will serialize it as a dict via `arbitrary_types_allowed`. Add to model config if not already present:

```python
model_config = {"arbitrary_types_allowed": True}
```

**Step 2: Update `select_strategy_and_focus` return type and value**

In `methodology_strategy_service.py`, the function calls `rank_strategy_node_pairs` and unpacks `scored_pairs`. Update:

```python
# Before:
scored_pairs = rank_strategy_node_pairs(...)

# After:
scored_pairs, score_decomposition = rank_strategy_node_pairs(...)
```

Add `score_decomposition` to the return tuple (it's the 6th element now):

```python
# Update return type annotation to include 6th element:
) -> Tuple[
    str,
    Optional[str],
    Sequence[Union[Tuple[str, float], Tuple[str, str, float]]],
    Optional[Dict[str, Any]],
    Dict[str, Dict[str, Any]],
    List["ScoredCandidate"],   # NEW
]:

# Update return statement:
return (
    best_strategy_config.name,
    best_node_id,
    alternatives,
    global_signals,
    node_signals,
    score_decomposition,       # NEW
)
```

**Step 3: Update StrategySelectionStage to unpack and pass through**

In `src/services/turn_pipeline/stages/strategy_selection_stage.py`, the stage calls `select_strategy_and_focus` and unpacks 5 values. Update to unpack 6:

```python
# Before:
strategy_name, focus_node_id, alternatives, global_signals, node_signals = (
    await self.strategy_service.select_strategy_and_focus(...)
)

# After:
strategy_name, focus_node_id, alternatives, global_signals, node_signals, score_decomposition = (
    await self.strategy_service.select_strategy_and_focus(...)
)
```

Pass `score_decomposition` to `StrategySelectionOutput`:

```python
output = StrategySelectionOutput(
    strategy=strategy_name,
    focus=focus_dict,
    signals=global_signals,
    node_signals=node_signals,
    strategy_alternatives=...,
    score_decomposition=score_decomposition,   # NEW
)
```

**Step 4: Add `score_decomposition` to PipelineContext property**

In `src/services/turn_pipeline/context.py`, add a property alongside `node_signals`:

```python
@property
def score_decomposition(self):
    """Per-candidate score decomposition from joint scoring."""
    if self.strategy_selection_output is None:
        return None
    return self.strategy_selection_output.score_decomposition
```

**Step 5: Run full test suite**

```bash
uv run pytest tests/ -q 2>&1 | tail -15
```

Expected: 90 pass. If tuple unpacking fails anywhere, fix the caller.

**Step 6: Commit**

```bash
git add src/methodologies/scoring.py src/domain/models/pipeline_contracts.py \
        src/services/methodology_strategy_service.py \
        src/services/turn_pipeline/stages/strategy_selection_stage.py \
        src/services/turn_pipeline/context.py
git commit -m "feat(pipeline): propagate score_decomposition from joint scoring through StrategySelectionOutput"
```

---

## Task 4: Propagate decomposition to TurnResult and SimulationTurn

**Files:**
- Modify: `src/services/turn_pipeline/result.py`
- Modify: `src/services/turn_pipeline/pipeline.py`
- Modify: `src/services/simulation_service.py`

**Step 1: Add `score_decomposition` to `TurnResult`**

In `src/services/turn_pipeline/result.py`, add field:

```python
from src.methodologies.scoring import ScoredCandidate

# Inside TurnResult dataclass:
score_decomposition: Optional[List[ScoredCandidate]] = None
```

**Step 2: Pass `score_decomposition` in pipeline.py**

In `src/services/turn_pipeline/pipeline.py`, where `TurnResult(...)` is constructed, add:

```python
TurnResult(
    ...
    node_signals=context.node_signals,
    score_decomposition=context.score_decomposition,   # NEW
)
```

**Step 3: Add `score_decomposition` to `SimulationTurn`**

In `src/services/simulation_service.py`, add to the `SimulationTurn` dataclass:

```python
score_decomposition: Optional[List[Dict[str, Any]]] = None
```

Note: `SimulationTurn` stores plain dicts (for JSON serialization), not `ScoredCandidate` objects. Serialize on the way in.

**Step 4: Pass decomposition in simulation main loop**

Find where `SimulationTurn` is constructed from `turn_result_session` (around line 244) and add:

```python
score_decomposition=_serialize_decomposition(turn_result_session.score_decomposition),
```

Add the serializer helper near top of file (after imports):

```python
def _serialize_decomposition(
    decomposition: Optional[List["ScoredCandidate"]],
) -> Optional[List[Dict[str, Any]]]:
    """Convert ScoredCandidate list to JSON-serializable dicts."""
    if decomposition is None:
        return None
    result = []
    for c in decomposition:
        result.append({
            "strategy": c.strategy,
            "node_id": c.node_id,
            "signal_contributions": [
                {
                    "name": sc.name,
                    "value": sc.value,
                    "weight": sc.weight,
                    "contribution": sc.contribution,
                }
                for sc in c.signal_contributions
            ],
            "base_score": round(c.base_score, 6),
            "phase_multiplier": c.phase_multiplier,
            "phase_bonus": c.phase_bonus,
            "final_score": round(c.final_score, 6),
            "rank": c.rank,
            "selected": c.selected,
        })
    return result
```

**Step 5: Add `score_decomposition` to JSON serialization**

In `_save_simulation_result`, add alongside `node_signals`:

```python
"node_signals": t.node_signals,
"score_decomposition": t.score_decomposition,   # NEW
```

**Step 6: Run full test suite**

```bash
uv run pytest tests/ -q 2>&1 | tail -15
```

Expected: 90 pass.

**Step 7: Commit**

```bash
git add src/services/turn_pipeline/result.py \
        src/services/turn_pipeline/pipeline.py \
        src/services/simulation_service.py
git commit -m "feat(simulation): serialize score_decomposition into JSON output per turn"
```

---

## Task 5: Update generate_scoring_csv.py to use JSON decomposition

**Files:**
- Modify: `scripts/generate_scoring_csv.py`

**Step 1: Read the existing script to understand current structure**

```bash
head -80 scripts/generate_scoring_csv.py
```

**Step 2: Replace recomputation logic with decomposition reader**

The new logic:

```python
def generate_scoring_csv(json_path: Path) -> Path:
    """Generate scoring CSV from simulation JSON score_decomposition."""
    with open(json_path) as f:
        data = json.load(f)

    csv_path = json_path.with_name(json_path.stem + "_scoring.csv")

    fieldnames = [
        "turn_number", "phase", "strategy", "node_id",
        "signal_name", "signal_value", "signal_weight", "weighted_contribution",
        "phase_multiplier", "phase_bonus", "base_score", "final_score",
        "rank", "selected",
    ]

    rows = []
    for turn in data.get("turns", []):
        turn_number = turn["turn_number"]
        phase = (turn.get("signals") or {}).get("meta.interview.phase", "unknown")
        decomposition = turn.get("score_decomposition")

        if not decomposition:
            # Old JSON without decomposition — emit placeholder row
            if turn.get("strategy_selected"):
                rows.append({
                    "turn_number": turn_number, "phase": phase,
                    "strategy": turn["strategy_selected"], "node_id": "",
                    "signal_name": "N/A (no decomposition in this JSON)",
                    "signal_value": "", "signal_weight": "", "weighted_contribution": "",
                    "phase_multiplier": "", "phase_bonus": "",
                    "base_score": "", "final_score": "",
                    "rank": 1, "selected": True,
                })
            continue

        for candidate in decomposition:
            contribs = candidate.get("signal_contributions") or []
            if not contribs:
                # No signals fired — emit one placeholder row for this candidate
                rows.append({
                    "turn_number": turn_number, "phase": phase,
                    "strategy": candidate["strategy"],
                    "node_id": candidate.get("node_id", ""),
                    "signal_name": "(no signals fired)",
                    "signal_value": "", "signal_weight": "", "weighted_contribution": 0,
                    "phase_multiplier": candidate.get("phase_multiplier", 1.0),
                    "phase_bonus": candidate.get("phase_bonus", 0.0),
                    "base_score": candidate.get("base_score", 0.0),
                    "final_score": candidate.get("final_score", 0.0),
                    "rank": candidate.get("rank", ""),
                    "selected": candidate.get("selected", False),
                })
            else:
                for sc in contribs:
                    rows.append({
                        "turn_number": turn_number, "phase": phase,
                        "strategy": candidate["strategy"],
                        "node_id": candidate.get("node_id", ""),
                        "signal_name": sc["name"],
                        "signal_value": sc["value"],
                        "signal_weight": sc["weight"],
                        "weighted_contribution": sc["contribution"],
                        "phase_multiplier": candidate.get("phase_multiplier", 1.0),
                        "phase_bonus": candidate.get("phase_bonus", 0.0),
                        "base_score": candidate.get("base_score", 0.0),
                        "final_score": candidate.get("final_score", 0.0),
                        "rank": candidate.get("rank", ""),
                        "selected": candidate.get("selected", False),
                    })

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path
```

**Step 3: Verify on a new simulation (3 turns)**

```bash
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 3 2>&1 | tail -10
```

Then check CSV scores match the JSON strategy_alternatives:

```python
import json, csv, glob

# Load the new JSON
f = sorted(glob.glob("synthetic_interviews/*.json"))[-1]
data = json.load(open(f))

# Turn 1: compare CSV final_score of selected strategy vs strategy_alternatives[0].score
t1 = data["turns"][1]
print("JSON top alternative:", t1["strategy_alternatives"][0])
print("JSON selected:", t1["strategy_selected"])

# Load CSV
csv_file = f.replace(".json", "_scoring.csv")
rows = list(csv.DictReader(open(csv_file)))
t1_selected = [r for r in rows if r["turn_number"] == "1" and r["selected"] == "True"]
# Get unique final_score for selected strategy
scores = {r["strategy"]: r["final_score"] for r in t1_selected}
print("CSV selected strategy scores:", scores)
```

Expected: CSV final_score for selected strategy matches JSON strategy_alternatives[0].score (within floating point).

**Step 4: Lint**

```bash
uv run ruff check scripts/generate_scoring_csv.py --fix
uv run ruff format scripts/generate_scoring_csv.py
```

**Step 5: Commit**

```bash
git add scripts/generate_scoring_csv.py
git commit -m "fix(csv): read score_decomposition from JSON instead of post-hoc recomputation"
```

---

## Task 6: End-to-end verification and close bead

**Step 1: Run full test suite**

```bash
uv run pytest tests/ -q 2>&1 | tail -10
```

Expected: 90 pass, 8 pre-existing SRL failures unchanged.

**Step 2: Run 5-turn simulation and verify CSV accuracy**

```bash
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 5 2>&1 | tail -15
```

Then run the validation script from Task 5 Step 3. Verify that for each turn, the selected strategy's final_score in the CSV matches the corresponding score in `strategy_alternatives` in the JSON (within 0.001).

**Step 3: Lint and format all changed files**

```bash
uv run ruff check src/ scripts/generate_scoring_csv.py --fix
uv run ruff format src/ scripts/generate_scoring_csv.py
```

**Step 4: Final commit and push**

```bash
git add -u
git commit -m "feat(cwus): live scoring decomposition — closes cwus bead

Surface per-signal score breakdown from rank_strategy_node_pairs into
simulation JSON (score_decomposition per turn). CSV now reads live
decomposition instead of inaccurate post-hoc recomputation.

Fixes: CSV scores now match actual pipeline scores exactly."
git push
```

**Step 5: Close bead**

```bash
bd close interview-system-v2-cwus --reason="score_decomposition serialized live from joint scoring; CSV reads from JSON decomposition; scores now accurate"
bd sync
```

---

## Key Invariants — Do Not Break

1. **Non-simulation pipeline**: `TurnResult.score_decomposition` is Optional and defaults to None. The live API pipeline does not use `SimulationTurn` or `_save_simulation_result` — these are simulation-only paths. The live pipeline must continue working unchanged.

2. **Backward-compatible JSON**: Old JSON files without `score_decomposition` still work in `generate_scoring_csv.py` — they get a placeholder "N/A" row instead of failing.

3. **`rank_strategy_node_pairs` return type change**: This function is called in exactly one place — `MethodologyStrategyService.select_strategy_and_focus`. Verify no other callers exist: `grep -rn "rank_strategy_node_pairs" src/`.

4. **`ScoredCandidate` in Pydantic**: Since `ScoredCandidate` is a dataclass (not a BaseModel), Pydantic needs `model_config = {"arbitrary_types_allowed": True}` on `StrategySelectionOutput`. Check if this is already set before adding.

5. **Do not modify `score_strategy()`**: The existing function remains unchanged. Only `score_strategy_with_decomposition()` is new — it calls `_get_signal_value()` with the same logic.
