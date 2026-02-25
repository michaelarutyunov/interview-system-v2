# Stage 1 Score Decomposition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Stage 1 (strategy selection) score decomposition to simulation JSON and CSV output, providing full visibility into why strategies were selected—without breaking existing consumers.

**Architecture:** Two-stage selection already implemented. Stage 1 (`rank_strategies`) computes strategy scores with phase weights but currently returns only `(strategy, score)` tuples. Stage 2 (`rank_nodes_for_strategy`) already returns `ScoredCandidate` decomposition. This plan extends Stage 1 to return decomposition alongside the existing format.

**Tech Stack:** Python 3.12, pytest, YAML configs, Pydantic, structlog

---

## Background

### Current State
- **Stage 1**: `rank_strategies()` returns `List[Tuple[StrategyConfig, float]]` — no per-signal breakdown
- **Stage 2**: `rank_nodes_for_strategy()` returns `(ranked_nodes, List[ScoredCandidate])` — has decomposition
- **JSON output**: Has `alternatives` (strategy name + final score) and `score_decomposition` (node only)
- **CSV output**: Generated from `score_decomposition` → shows only node-level scores

### Problem
When analyzing interviews, you can see **which node** was selected and why, but you **cannot** see:
1. Why `explore` was chosen over `deepen` at the strategy level
2. How phase multipliers affected the strategy decision
3. The per-signal contribution breakdown for strategy selection

### Solution
Extend `rank_strategies()` to optionally return `ScoredCandidate` decomposition (same structure as Stage 2), capture it at the service layer, and add it to JSON/CSV outputs.

### Key Files
- `src/methodologies/scoring.py` — `rank_strategies()` function (main changes)
- `src/services/methodology_strategy_service.py` — orchestrator (capture decomposition)
- `src/services/turn_pipeline/stages/strategy_selection_stage.py` — pipeline stage
- `src/domain/models/pipeline_contracts.py` — `StrategySelectionOutput` model
- `src/services/simulation_service.py` — JSON serialization
- `scripts/generate_scoring_csv.py` — CSV generation
- `tests/methodologies/test_scoring.py` — unit tests

---

## Non-Breaking Design Principles

### 1. Additive Changes Only
- **Do NOT** modify the return type of `rank_strategies()` in a breaking way
- **Do ADD** an optional second return value (tuple expansion)
- Existing callers continue to work: `ranked = rank_strategies(...)`

### 2. Coexistence Period
- Keep existing `alternatives` and `score_decomposition` fields in JSON
- Add NEW fields alongside: `strategy_selection_decomposition`
- CSV: Add new section at the top, keep existing node rows

### 3. Feature Flag Path
- Implementation can be verified independently
- No changes to scoring logic (only expose what's already computed)
- Each phase is independently revertable

---

## Task 1: Extend `rank_strategies()` to Return Decomposition

**Files:**
- Modify: `src/methodologies/scoring.py:193-255` (`rank_strategies()` function)
- Test: `tests/methodologies/test_scoring.py`

**Current Signature:**
```python
def rank_strategies(
    strategy_configs: List[StrategyConfig],
    signals: Dict[str, Any],
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
) -> List[Tuple[StrategyConfig, float]]:
```

**New Signature:**
```python
def rank_strategies(
    strategy_configs: List[StrategyConfig],
    signals: Dict[str, Any],
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
    return_decomposition: bool = False,
) -> Union[
    List[Tuple[StrategyConfig, float]],
    Tuple[List[Tuple[StrategyConfig, float]], List[ScoredCandidate]]
]:
```

**Step 1: Write failing tests**

Add to `tests/methodologies/test_scoring.py`:

```python
class TestRankStrategiesDecomposition:
    """Tests for Stage 1 strategy score decomposition."""

    def test_returns_decomposition_when_requested(self):
        """rank_strategies should return (ranked, decomposition) when return_decomposition=True."""
        strategies = [
            StrategyConfig(
                name="deepen",
                description="D",
                signal_weights={"llm.response_depth.low": 0.8, "llm.engagement.high": 0.7}
            ),
            StrategyConfig(
                name="explore",
                description="E",
                signal_weights={"llm.response_depth.low": 0.5}
            ),
        ]
        signals = {"llm.response_depth": 0.1, "llm.engagement": 0.9}
        phase_weights = {"deepen": 1.3}
        phase_bonuses = {"deepen": 0.2}

        result = rank_strategies(
            strategies, signals, phase_weights, phase_bonuses, return_decomposition=True
        )

        # Should return tuple of (ranked_strategies, decomposition)
        assert isinstance(result, tuple)
        assert len(result) == 2

        ranked, decomposition = result

        # Verify ranked strategies (existing behavior)
        assert len(ranked) == 2
        assert ranked[0][0].name == "deepen"
        assert ranked[0][1] > 0  # Should have phase-applied score

        # Verify decomposition exists
        assert len(decomposition) == 2
        assert all(isinstance(c, ScoredCandidate) for c in decomposition)

        # Verify deepen has phase multipliers
        deepen_decomp = next(c for c in decomposition if c.strategy == "deepen")
        assert deepen_decomp.phase_multiplier == 1.3
        assert deepen_decomp.phase_bonus == 0.2
        assert deepen_decomp.final_score == deepen_decomp.base_score * 1.3 + 0.2

        # Verify signal contributions are captured
        assert len(deepen_decomp.signal_contributions) == 2
        contrib_names = {c.name for c in deepen_decomp.signal_contributions}
        assert "llm.response_depth.low" in contrib_names
        assert "llm.engagement.high" in contrib_names

    def test_backward_compatible_when_not_requested(self):
        """rank_strategies should return only ranked list when return_decomposition=False (default)."""
        strategies = [
            StrategyConfig(
                name="test",
                description="T",
                signal_weights={"llm.engagement.high": 0.5}
            ),
        ]
        signals = {"llm.engagement": 0.8}

        # Default behavior (return_decomposition=False)
        result = rank_strategies(strategies, signals)

        # Should return list, not tuple
        assert isinstance(result, list)
        assert not isinstance(result, tuple)
        assert len(result) == 1
        assert result[0][0].name == "test"

    def test_decomposition_includes_rank_and_selected(self):
        """Decomposition should mark best strategy as selected with rank=1."""
        strategies = [
            StrategyConfig(name="low", description="L", signal_weights={"x": 0.1}),
            StrategyConfig(name="high", description="H", signal_weights={"x": 1.0}),
        ]
        signals = {"x": 1.0}

        ranked, decomposition = rank_strategies(
            strategies, signals, return_decomposition=True
        )

        # High score strategy should be selected
        high_decomp = next(c for c in decomposition if c.strategy == "high")
        assert high_decomp.selected == True
        assert high_decomp.rank == 1

        # Low score strategy should not be selected
        low_decomp = next(c for c in decomposition if c.strategy == "low")
        assert low_decomp.selected == False
        assert low_decomp.rank == 2
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/methodologies/test_scoring.py::TestRankStrategiesDecomposition -v
```

Expected: FAIL — function doesn't accept `return_decomposition` parameter, doesn't return tuple.

**Step 3: Implement the change**

In `src/methodologies/scoring.py`, modify `rank_strategies()`:

```python
def rank_strategies(
    strategy_configs: List[StrategyConfig],
    signals: Dict[str, Any],
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
    return_decomposition: bool = False,
) -> Union[
    List[Tuple[StrategyConfig, float]],
    Tuple[List[Tuple[StrategyConfig, float]], List[ScoredCandidate]]
]:
    """
    Rank all strategies by score.

    Args:
        strategy_configs: List of strategy configs from YAML
        signals: Dict of detected signals
        phase_weights: Optional dict of phase-based weight multipliers
        phase_bonuses: Optional dict of phase-based additive bonuses
        return_decomposition: If True, return (ranked_strategies, decomposition) tuple

    Returns:
        - If return_decomposition=False: List of (strategy_config, score) sorted descending
        - If return_decomposition=True: Tuple of (ranked_strategies, List[ScoredCandidate])
    """
    import structlog

    log = structlog.get_logger(__name__)

    # Build list of candidates with decomposition
    candidates: List[ScoredCandidate] = []
    scored: List[Tuple[StrategyConfig, float]] = []

    for strategy_config in strategy_configs:
        # Partition to exclude node-scoped signals from strategy scoring
        global_weights, _ = partition_signal_weights(strategy_config.signal_weights)
        global_only_strategy = StrategyConfig(
            name=strategy_config.name,
            description=strategy_config.description,
            signal_weights=global_weights,
        )

        # Score with decomposition
        base_score, contributions = score_strategy_with_decomposition(
            global_only_strategy, signals
        )

        # Apply phase weights
        if phase_weights and strategy_config.name in phase_weights:
            multiplier = phase_weights[strategy_config.name]
        else:
            multiplier = 1.0

        bonus = 0.0
        if phase_bonuses and strategy_config.name in phase_bonuses:
            bonus = phase_bonuses[strategy_config.name]

        final_score = (base_score * multiplier) + bonus

        scored.append((strategy_config, final_score))

        # Build decomposition if requested
        if return_decomposition:
            candidates.append(
                ScoredCandidate(
                    strategy=strategy_config.name,
                    node_id="",  # Stage 1 has no node
                    signal_contributions=contributions,
                    base_score=base_score,
                    phase_multiplier=multiplier,
                    phase_bonus=bonus,
                    final_score=final_score,
                    rank=0,  # Set after sorting
                    selected=False,
                )
            )

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Assign rank and selected flags for decomposition
    if return_decomposition:
        ranked_order = {s.name: i for i, (s, _) in enumerate(scored)}
        for candidate in candidates:
            rank = ranked_order.get(candidate.strategy, len(scored))
            candidate.rank = rank + 1
            candidate.selected = rank == 0

    # Log scores
    log.info(
        "strategies_ranked",
        phase=signals.get("meta.interview.phase", "unknown"),
        phase_weights=phase_weights,
        phase_bonuses=phase_bonuses,
        ranked=[(s.name, score) for s, score in scored],
    )

    if return_decomposition:
        return scored, candidates
    else:
        return scored
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/methodologies/test_scoring.py::TestRankStrategiesDecomposition -v
```

Expected: PASS

**Step 5: Verify existing tests still pass**

```bash
uv run pytest tests/methodologies/test_scoring.py -v
```

Expected: All existing tests still pass (backward compatibility verified)

---

## Task 2: Update Service Layer to Capture Stage 1 Decomposition

**Files:**
- Modify: `src/services/methodology_strategy_service.py:238-288` (Stage 1 section)

**Step 1: Write failing test**

Add to `tests/services/test_methodology_strategy_service_two_stage.py`:

```python
async def test_stage1_decomposition_captured(self):
    """Service should capture Stage 1 decomposition when available."""
    s1 = StrategyConfig(
        name="deepen",
        description="D",
        signal_weights={"llm.response_depth.low": 0.8}
    )
    config = MethodologyConfig(
        name="test",
        description="Test",
        signals={},
        strategies=[s1],
        phases=None,
    )

    service = MethodologyStrategyService()
    service.methodology_registry = MagicMock()
    service.methodology_registry.get_methodology.return_value = config

    service.global_signal_service = AsyncMock()
    service.global_signal_service.detect.return_value = {"llm.response_depth": 0.1}
    service.node_signal_service = AsyncMock()
    service.node_signal_service.detect.return_value = {"node_a": {}}

    with patch(
        "src.services.methodology_strategy_service.InterviewPhaseSignal"
    ) as MockPhase:
        mock_instance = AsyncMock()
        mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
        MockPhase.return_value = mock_instance

        result = await service.select_strategy_and_focus(
            _make_context(), _make_graph_state(), "test"
        )

    # Result should include score_decomposition
    _, _, _, _, _, score_decomp = result

    # Should have strategy-level decomposition (from Stage 1)
    assert score_decomp is not None
    assert len(score_decomp) > 0

    # Should have phase_multiplier captured
    deepen_decomp = next((c for c in score_decomp if c.strategy == "deepen"), None)
    assert deepen_decomp is not None
    # Verify phase_multiplier is captured (not just default 1.0)
    assert hasattr(deepen_decomp, 'phase_multiplier')
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/services/test_methodology_strategy_service_two_stage.py::TestTwoStageMethodologyStrategyService::test_stage1_decomposition_captured -v
```

Expected: FAIL — service doesn't request decomposition from `rank_strategies()`

**Step 3: Implement the change**

In `src/services/methodology_strategy_service.py`, modify Stage 1 section:

```python
# --- Stage 1: Select strategy using global signals only ---
ranked_strategies, strategy_decomposition = rank_strategies(
    strategy_configs=strategies,
    signals=global_signals,
    phase_weights=phase_weights,
    phase_bonuses=phase_bonuses,
    return_decomposition=True,  # NEW: Capture decomposition
)
```

Then update the return value to include strategy decomposition:

```python
# Build combined decomposition
# Note: If node_binding="none", only strategy_decomposition exists
#       If node_binding="required", we have both (merge them)
score_decomposition: list[ScoredCandidate] = []

if strategy_decomposition:
    score_decomposition.extend(strategy_decomposition)

# ... (later in the code)

if best_strategy_config.node_binding == "required" and node_signals:
    ranked_nodes, node_decomposition = rank_nodes_for_strategy(
        best_strategy_config, node_signals
    )
    score_decomposition.extend(node_decomposition)
    # ... rest of node selection code
```

**Step 4: Update return type annotation**

In `select_strategy_and_focus()` return type:

```python
) -> Tuple[
    str,
    Optional[str],
    Sequence[Union[Tuple[str, float], Tuple[str, str, float]]],
    Optional[Dict[str, Any]],
    Dict[str, Dict[str, Any]],
    list[ScoredCandidate],  # This already exists, just ensure it's populated
]:
```

**Step 5: Run tests to verify**

```bash
uv run pytest tests/services/test_methodology_strategy_service_two_stage.py -v
```

---

## Task 3: Add Stage 1 Decomposition to Pipeline Context

**Files:**
- Modify: `src/services/turn_pipeline/stages/strategy_selection_stage.py`

**Step 1: Verify score_decomposition flows through**

The `score_decomposition` should already be flowing from service → stage → context. Verify with existing test:

```bash
uv run pytest tests/services/turn_pipeline/stages/test_strategy_selection_stage.py -v -k decomposition
```

If test doesn't exist, add one:

```python
async def test_score_decomposition_flows_to_context(self):
    """Stage 1 decomposition should be captured in context."""
    # ... setup code similar to existing tests ...

    result = await self.stage.execute(context)

    # Verify score_decomposition is in context
    assert context.score_decomposition is not None
    assert len(context.score_decomposition) > 0

    # Should have strategy-level entries
    strategy_entries = [c for c in context.score_decomposition if c.node_id == ""]
    assert len(strategy_entries) > 0
```

---

## Task 4: Update JSON Output

**Files:**
- Modify: `src/services/simulation_service.py`
- Modify: `src/domain/models/simulation.py` (if needed)

**Step 1: Add new field to SimulationTurn model**

In `src/domain/models/simulation.py`, check if `SimulationTurn` has the field. If `score_decomposition` is already there, we just need to ensure it includes strategy entries.

**Step 2: Update serialization (if needed)**

The `_serialize_decomposition()` method should already handle both strategy and node candidates since they're both `ScoredCandidate`. Verify:

```bash
# Run a simulation and check JSON output
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 3

# Check the JSON includes strategy decomposition
cat synthetic_interviews/*_coffee_jtbd_v2_skeptical_analyst.json | jq '.turns[0].score_decomposition'
```

Expected output should show entries with `node_id: ""` for strategy-level candidates.

**Step 3: Add explicit `strategy_selection` section (optional)**

For clarity, add a dedicated section at the top level:

```python
# In simulation_service.py, when building SimulationTurn
result = SimulationTurn(
    # ... existing fields ...
    score_decomposition=serialized_decomposition,
    strategy_selection={  # NEW: explicit strategy selection section
        "selected_strategy": best_strategy_config.name,
        "strategy_score_with_phase": best_strategy_score,
        "alternatives": [{"strategy": s, "score": sc} for s, sc in ranked_strategies],
    },
)
```

---

## Task 5: Update CSV Generation

**Files:**
- Modify: `scripts/generate_scoring_csv.py`

**Current behavior:** CSV generated from `score_decomposition` shows only node scores.

**New behavior:** Add `stage` column to distinguish strategy vs node scoring.

**Step 1: Modify CSV schema**

```python
# New CSV columns:
# turn | stage | strategy | node_id | rank | selected | base_score | phase_multiplier | phase_bonus | final_score | signal_name | signal_value | signal_weight | signal_contribution

# Where:
# - stage = "strategy" or "node"
# - node_id = empty string for strategy rows
```

**Step 2: Update generate_scoring_csv.py**

```python
def generate_csv_from_simulation(json_file: str, output_csv: str):
    """Generate scoring CSV with both strategy and node decompositions."""

    with open(json_file) as f:
        data = json.load(f)

    rows = []

    for turn in data.get("turns", []):
        turn_number = turn.get("turn", 0)

        # Process score_decomposition
        for candidate in turn.get("score_decomposition", []):
            # Determine stage from node_id
            if candidate.get("node_id") == "" or candidate.get("node_id") is None:
                stage = "strategy"
            else:
                stage = "node"

            # Base row
            base_row = {
                "turn": turn_number,
                "stage": stage,
                "strategy": candidate.get("strategy"),
                "node_id": candidate.get("node_id", ""),
                "rank": candidate.get("rank"),
                "selected": candidate.get("selected"),
                "base_score": candidate.get("base_score"),
                "phase_multiplier": candidate.get("phase_multiplier", 1.0),
                "phase_bonus": candidate.get("phase_bonus", 0.0),
                "final_score": candidate.get("final_score"),
            }

            # Signal contribution rows
            for sig in candidate.get("signal_contributions", []):
                row = {
                    **base_row,
                    "signal_name": sig.get("name"),
                    "signal_value": sig.get("value"),
                    "signal_weight": sig.get("weight"),
                    "signal_contribution": sig.get("contribution"),
                }
                rows.append(row)

    # Write CSV
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
```

**Step 3: Test CSV generation**

```bash
# Generate CSV from existing simulation
uv run python scripts/generate_scoring_csv.py synthetic_interviews/<file>.json

# Verify output has both stages
head -20 <output_csv>.csv | grep -E "stage|strategy|node"
```

Expected: CSV should show `stage,strategy` column with both "strategy" and "node" values.

---

## Task 6: Documentation Updates

**Files:**
- Update: `docs/data_flow_paths.md` — Path 18
- Update: `docs/signals_and_strategies.md` — Score decomposition section

**Changes:**

1. Update Path 18 to reflect that `score_decomposition` now includes both stages
2. Add example showing strategy-level decomposition in JSON
3. Add example showing CSV with `stage` column

---

## Rollback Plan

Each task is independently revertable:

```bash
# To rollback any single task
git revert <commit-hash>

# To rollback entire feature
git revert <start-commit>..<end-commit>
```

---

## Verification Checklist

- [ ] All existing tests pass (no regressions)
- [ ] New decomposition tests pass
- [ ] Simulation JSON includes strategy decomposition
- [ ] CSV includes `stage` column with both values
- [ ] Manual inspection of sample interview looks correct
- [ ] Documentation updated
- [ ] Golden file comparison shows expected additions only

---

## Success Criteria

1. **Can answer "why was this strategy chosen?"**
   - JSON shows strategy-level signal contributions
   - JSON shows phase multiplier applied
   - CSV shows strategy vs node scoring clearly

2. **No breaking changes**
   - All existing tests pass
   - Old JSON fields still present
   - CSV is additive (new column, new rows)

3. **Performance**
   - No significant slowdown in simulation
   - JSON size increase is acceptable (< 20%)
