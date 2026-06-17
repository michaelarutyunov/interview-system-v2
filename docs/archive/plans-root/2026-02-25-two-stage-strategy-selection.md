# Two-Stage Strategy Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace joint (strategy × node) scoring with a two-stage approach: select strategy from global signals, then conditionally select node for that strategy.

**Architecture:** Strategy selection uses only global signals (no `graph.node.*`). Node selection uses only node signals, scoped to the chosen strategy's `node_weights`. Strategies declare `node_binding: required | preferred | none` to control whether node selection runs. Auto-partition by namespace: `graph.node.*` and `technique.node.*` keys in `signal_weights` are automatically routed to node scoring.

**Tech Stack:** Python 3.12, pytest, YAML configs, Pydantic, structlog

---

## Background

### Current Architecture (Joint Scoring)
`rank_strategy_node_pairs()` in `scoring.py` scores every (strategy, node) combination using merged global + node signals. This creates O(S×N) candidates where 21/29 signals are identical across all candidates, drowning out node-specific differentiation.

### New Architecture (Two-Stage)
1. **Stage 1 — Strategy Selection:** Score strategies using only global signals → pick best strategy
2. **Stage 2 — Node Selection (conditional):** If strategy has `node_binding: required|preferred`, score nodes using node signals scoped to that strategy → pick best node

### Key Files
- `src/methodologies/scoring.py` — scoring functions (main changes)
- `src/methodologies/registry.py` — `StrategyConfig` dataclass + YAML loader
- `src/services/methodology_strategy_service.py` — orchestrator (calls scoring)
- `src/services/turn_pipeline/stages/strategy_selection_stage.py` — pipeline stage (caller)
- `config/methodologies/means_end_chain.yaml` — MEC methodology config
- `config/methodologies/jobs_to_be_done.yaml` — JTBD methodology config
- `config/methodologies/critical_incident.yaml` — CIT methodology config
- `tests/methodologies/test_scoring.py` — scoring tests

### Auto-Partition Rule
Signal weight keys are partitioned by namespace at scoring time:
- Keys starting with `graph.node.` or `technique.node.` → **node weights** (used in stage 2)
- All other keys → **strategy weights** (used in stage 1)

This means **zero YAML changes required** for the partition itself. The YAML `signal_weights` section stays as-is.

### Node Binding Classification
Each strategy declares how it relates to nodes:
- `node_binding: required` — Must select a node (deepen, clarify, explore)
- `node_binding: none` — No node needed (reflect, revitalize)

Default is `required` (backward compatible — all current strategies target nodes).

---

## Task 1: Add `node_binding` Field to StrategyConfig

**Files:**
- Modify: `src/methodologies/registry.py:76-84` (StrategyConfig dataclass)
- Modify: `src/methodologies/registry.py:152-165` (YAML loader)
- Test: `tests/methodologies/test_scoring.py`

**Step 1: Write the failing test**

Add to `tests/methodologies/test_scoring.py`:

```python
class TestStrategyConfigNodeBinding:
    """Tests for StrategyConfig node_binding field."""

    def test_default_node_binding_is_required(self):
        """New strategies default to node_binding='required'."""
        config = StrategyConfig(
            name="test",
            description="Test",
            signal_weights={"llm.engagement.high": 0.5},
        )
        assert config.node_binding == "required"

    def test_node_binding_none(self):
        """Strategies can declare node_binding='none'."""
        config = StrategyConfig(
            name="reflect",
            description="Reflect",
            signal_weights={"meta.interview_progress": 0.5},
            node_binding="none",
        )
        assert config.node_binding == "none"

    def test_invalid_node_binding_raises(self):
        """Invalid node_binding value raises ValueError during YAML validation."""
        # This is tested via registry validation, not StrategyConfig directly
        pass
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestStrategyConfigNodeBinding -v`
Expected: FAIL — `StrategyConfig.__init__() got an unexpected keyword argument 'node_binding'`

**Step 3: Implement the change**

In `src/methodologies/registry.py`, add to `StrategyConfig` (line ~84):

```python
VALID_NODE_BINDINGS = frozenset({"required", "none"})

@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    description: str
    signal_weights: dict[str, float]
    generates_closing_question: bool = False
    focus_mode: str = "recent_node"
    node_binding: str = "required"  # NEW: "required" or "none"
```

In the YAML loader (line ~153), add `node_binding`:

```python
StrategyConfig(
    name=s["name"],
    description=s.get("description", ""),
    signal_weights=s["signal_weights"],
    generates_closing_question=s.get("generates_closing_question", False),
    focus_mode=s.get("focus_mode", "recent_node"),
    node_binding=s.get("node_binding", "required"),  # NEW
)
```

In `_validate_config`, add validation for `node_binding` (after the `focus_mode` check around line 202):

```python
if strategy.node_binding not in VALID_NODE_BINDINGS:
    errors.append(
        f"strategies[{i}] '{strategy.name}': "
        f"invalid node_binding '{strategy.node_binding}' "
        f"(valid: {sorted(VALID_NODE_BINDINGS)})"
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestStrategyConfigNodeBinding -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/methodologies/registry.py tests/methodologies/test_scoring.py
git commit -m "feat: add node_binding field to StrategyConfig"
```

---

## Task 2: Add `partition_signal_weights()` Helper to Scoring

**Files:**
- Modify: `src/methodologies/scoring.py` (add new function)
- Test: `tests/methodologies/test_scoring.py`

**Step 1: Write the failing test**

```python
from src.methodologies.scoring import partition_signal_weights

class TestPartitionSignalWeights:
    """Tests for auto-partitioning signal weights by namespace."""

    def test_separates_node_signals(self):
        """graph.node.* and technique.node.* go to node_weights."""
        weights = {
            "llm.response_depth.low": 0.8,
            "llm.engagement.high": 0.7,
            "graph.node.exhaustion_score.low": 1.0,
            "graph.node.focus_streak.high": -0.8,
            "technique.node.strategy_repetition.low": 0.3,
        }
        strategy_weights, node_weights = partition_signal_weights(weights)

        assert strategy_weights == {
            "llm.response_depth.low": 0.8,
            "llm.engagement.high": 0.7,
        }
        assert node_weights == {
            "graph.node.exhaustion_score.low": 1.0,
            "graph.node.focus_streak.high": -0.8,
            "technique.node.strategy_repetition.low": 0.3,
        }

    def test_all_global(self):
        """Weights with no node signals return empty node_weights."""
        weights = {"llm.engagement.high": 0.5, "meta.interview_progress": 0.3}
        strategy_weights, node_weights = partition_signal_weights(weights)

        assert strategy_weights == weights
        assert node_weights == {}

    def test_all_node(self):
        """Weights with only node signals return empty strategy_weights."""
        weights = {"graph.node.exhaustion_score.low": 1.0}
        strategy_weights, node_weights = partition_signal_weights(weights)

        assert strategy_weights == {}
        assert node_weights == weights

    def test_empty_weights(self):
        """Empty dict returns two empty dicts."""
        strategy_weights, node_weights = partition_signal_weights({})
        assert strategy_weights == {}
        assert node_weights == {}

    def test_meta_node_goes_to_node_weights(self):
        """meta.node.* signals are node-scoped too."""
        weights = {"meta.node.opportunity.fresh": 0.6}
        strategy_weights, node_weights = partition_signal_weights(weights)
        assert strategy_weights == {}
        assert node_weights == {"meta.node.opportunity.fresh": 0.6}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestPartitionSignalWeights -v`
Expected: FAIL — `ImportError: cannot import name 'partition_signal_weights'`

**Step 3: Implement**

Add to `src/methodologies/scoring.py`:

```python
# Prefixes that indicate node-scoped signals
NODE_SIGNAL_PREFIXES = ("graph.node.", "technique.node.", "meta.node.")


def partition_signal_weights(
    signal_weights: Dict[str, float],
) -> tuple[Dict[str, float], Dict[str, float]]:
    """Split signal_weights into strategy weights and node weights by namespace.

    Keys starting with graph.node.*, technique.node.*, or meta.node.* are
    routed to node_weights. Everything else goes to strategy_weights.

    Args:
        signal_weights: Combined signal weights from YAML config

    Returns:
        Tuple of (strategy_weights, node_weights)
    """
    strategy_weights: Dict[str, float] = {}
    node_weights: Dict[str, float] = {}

    for key, weight in signal_weights.items():
        if any(key.startswith(prefix) for prefix in NODE_SIGNAL_PREFIXES):
            node_weights[key] = weight
        else:
            strategy_weights[key] = weight

    return strategy_weights, node_weights
```

**Step 4: Run tests**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestPartitionSignalWeights -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/methodologies/scoring.py tests/methodologies/test_scoring.py
git commit -m "feat: add partition_signal_weights() for auto namespace routing"
```

---

## Task 3: Add `rank_nodes_for_strategy()` to Scoring

**Files:**
- Modify: `src/methodologies/scoring.py` (add new function)
- Test: `tests/methodologies/test_scoring.py`

**Step 1: Write the failing test**

```python
from src.methodologies.scoring import rank_nodes_for_strategy, ScoredCandidate

class TestRankNodesForStrategy:
    """Tests for node ranking within a selected strategy."""

    def test_ranks_nodes_by_node_signal_score(self):
        """Nodes ranked by node_weights applied to node signals."""
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,           # global (ignored here)
                "graph.node.exhaustion_score.low": 1.0,   # node weight
                "graph.node.focus_streak.high": -0.8,     # node weight
            },
        )
        node_signals = {
            "node_a": {"graph.node.exhaustion_score": 0.1, "graph.node.focus_streak": 0.9},  # low exh, high streak
            "node_b": {"graph.node.exhaustion_score": 0.1, "graph.node.focus_streak": 0.1},  # low exh, low streak
        }

        ranked, candidates = rank_nodes_for_strategy(strategy, node_signals)

        assert len(ranked) == 2
        # node_b should win: exhaustion_score.low=True (+1.0), focus_streak.high=False (no penalty)
        # node_a: exhaustion_score.low=True (+1.0), focus_streak.high=True (-0.8) = 0.2
        assert ranked[0][0] == "node_b"
        assert ranked[1][0] == "node_a"
        assert ranked[0][1] > ranked[1][1]

    def test_returns_empty_for_no_nodes(self):
        """Returns empty lists when no node signals provided."""
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={"graph.node.exhaustion_score.low": 1.0},
        )

        ranked, candidates = rank_nodes_for_strategy(strategy, {})
        assert ranked == []
        assert candidates == []

    def test_only_uses_node_weights(self):
        """Global signal weights in strategy config are ignored."""
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,           # global — must be ignored
                "graph.node.exhaustion_score.low": 1.0,   # node weight
            },
        )
        node_signals = {
            "node_a": {"graph.node.exhaustion_score": 0.1},
        }

        ranked, _ = rank_nodes_for_strategy(strategy, node_signals)

        # Score should only reflect node weight (1.0), not global weight (0.8)
        assert ranked[0][1] == pytest.approx(1.0)

    def test_returns_scored_candidates(self):
        """Decomposition includes signal contributions for each node."""
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={"graph.node.exhaustion_score.low": 1.0},
        )
        node_signals = {
            "node_a": {"graph.node.exhaustion_score": 0.1},
        }

        _, candidates = rank_nodes_for_strategy(strategy, node_signals)

        assert len(candidates) == 1
        assert candidates[0].strategy == "deepen"
        assert candidates[0].node_id == "node_a"
        assert len(candidates[0].signal_contributions) == 1
        assert candidates[0].signal_contributions[0].name == "graph.node.exhaustion_score.low"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestRankNodesForStrategy -v`
Expected: FAIL — `ImportError: cannot import name 'rank_nodes_for_strategy'`

**Step 3: Implement**

Add to `src/methodologies/scoring.py`:

```python
def rank_nodes_for_strategy(
    strategy_config: StrategyConfig,
    node_signals: Dict[str, Dict[str, Any]],
) -> tuple[List[Tuple[str, float]], List[ScoredCandidate]]:
    """Rank nodes for a specific strategy using only node-scoped signal weights.

    Auto-partitions the strategy's signal_weights to extract only node-scoped
    weights (graph.node.*, technique.node.*, meta.node.*), then scores each
    node against those weights.

    Args:
        strategy_config: Strategy config (node weights extracted automatically)
        node_signals: Dict mapping node_id to per-node signal dict

    Returns:
        Tuple of (ranked_nodes, candidates) where:
        - ranked_nodes: List of (node_id, score) sorted descending
        - candidates: List of ScoredCandidate with per-signal breakdown
    """
    _, node_weights = partition_signal_weights(strategy_config.signal_weights)

    if not node_signals or not node_weights:
        return [], []

    # Create a temporary StrategyConfig with only node weights for scoring
    node_strategy = StrategyConfig(
        name=strategy_config.name,
        description=strategy_config.description,
        signal_weights=node_weights,
    )

    scored: List[Tuple[str, float]] = []
    candidates: List[ScoredCandidate] = []

    for node_id, signals in node_signals.items():
        score, contributions = score_strategy_with_decomposition(node_strategy, signals)

        scored.append((node_id, score))
        candidates.append(
            ScoredCandidate(
                strategy=strategy_config.name,
                node_id=node_id,
                signal_contributions=contributions,
                base_score=score,
                final_score=score,
            )
        )

    # Sort by score descending
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)

    # Assign ranks
    ranked_order = {node_id: i for i, (node_id, _) in enumerate(ranked)}
    for candidate in candidates:
        rank = ranked_order.get(candidate.node_id, len(ranked))
        candidate.rank = rank + 1
        candidate.selected = rank == 0

    log.debug(
        "nodes_ranked_for_strategy",
        strategy=strategy_config.name,
        top3=[(nid, round(sc, 4)) for nid, sc in ranked[:3]],
    )

    return ranked, candidates
```

**Step 4: Run tests**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestRankNodesForStrategy -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/methodologies/scoring.py tests/methodologies/test_scoring.py
git commit -m "feat: add rank_nodes_for_strategy() for two-stage node selection"
```

---

## Task 4: Modify `rank_strategies()` to Exclude Node Signals

**Files:**
- Modify: `src/methodologies/scoring.py` (update `rank_strategies`)
- Test: `tests/methodologies/test_scoring.py`

**Step 1: Write the failing test**

```python
class TestRankStrategiesExcludesNodeSignals:
    """Test that rank_strategies only uses global signal weights."""

    def test_node_signals_excluded_from_strategy_scoring(self):
        """graph.node.* weights should not affect strategy ranking."""
        strategy_a = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,           # global → contributes
                "graph.node.exhaustion_score.low": 5.0,   # node → must be excluded
            },
        )
        strategy_b = StrategyConfig(
            name="explore",
            description="Explore",
            signal_weights={
                "llm.response_depth.low": 0.9,           # global → contributes
            },
        )
        signals = {"llm.response_depth": 0.1}  # low

        ranked = rank_strategies([strategy_a, strategy_b], signals)

        # Without node exclusion: deepen would score 0.8 + 5.0 = 5.8 (wrong)
        # With node exclusion: deepen scores 0.8, explore scores 0.9
        assert ranked[0][0].name == "explore"
        assert ranked[0][1] == pytest.approx(0.9)
        assert ranked[1][0].name == "deepen"
        assert ranked[1][1] == pytest.approx(0.8)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/methodologies/test_scoring.py::TestRankStrategiesExcludesNodeSignals -v`
Expected: FAIL — deepen scores 5.8 because node signals are included

**Step 3: Implement**

Modify `rank_strategies()` in `src/methodologies/scoring.py` to partition weights before scoring. Change the scoring loop (around line 188-190):

```python
def rank_strategies(
    strategy_configs: List[StrategyConfig],
    signals: Dict[str, Any],
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
) -> List[Tuple[StrategyConfig, float]]:
    # ... (docstring stays the same, add note about node signal exclusion) ...

    scored = []
    for strategy_config in strategy_configs:
        # Partition to exclude node-scoped signals from strategy scoring
        global_weights, _ = partition_signal_weights(strategy_config.signal_weights)
        global_only_strategy = StrategyConfig(
            name=strategy_config.name,
            description=strategy_config.description,
            signal_weights=global_weights,
        )

        # Score strategy using only global signal weights
        base_score = score_strategy(global_only_strategy, signals)

        # ... rest of phase_weights/bonuses logic stays the same ...
```

**Important:** The existing `score_strategy()` and `score_strategy_with_decomposition()` functions remain unchanged — they score whatever weights they're given. The filtering happens in `rank_strategies()`.

**Step 4: Run ALL scoring tests to ensure no regressions**

Run: `uv run pytest tests/methodologies/test_scoring.py -v`
Expected: ALL PASS (existing tests don't use `graph.node.*` weights in `rank_strategies`)

**Step 5: Commit**

```bash
git add src/methodologies/scoring.py tests/methodologies/test_scoring.py
git commit -m "feat: exclude node signals from strategy ranking (two-stage prep)"
```

---

## Task 5: Update `MethodologyStrategyService` for Two-Stage Flow

**Files:**
- Modify: `src/services/methodology_strategy_service.py` (main orchestration change)
- Test: `tests/methodologies/test_scoring.py` (integration-level test)

This is the core change. The service currently calls `rank_strategy_node_pairs()`. It must now:
1. Call `rank_strategies()` with global signals only
2. Check the winning strategy's `node_binding`
3. If `required`: call `rank_nodes_for_strategy()` with node signals
4. If `none`: skip node selection, return `focus_node_id = None`

**Step 1: Write the failing test**

Create new file `tests/services/test_methodology_strategy_service_two_stage.py`:

```python
"""Tests for two-stage strategy selection in MethodologyStrategyService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.methodologies.registry import StrategyConfig, MethodologyConfig, PhaseConfig
from src.services.methodology_strategy_service import MethodologyStrategyService


def _make_context(methodology="means_end_chain", turn_number=5, max_turns=20):
    """Create a minimal mock PipelineContext."""
    ctx = MagicMock()
    ctx.methodology = methodology
    ctx.turn_number = turn_number
    ctx.max_turns = max_turns
    ctx.user_input = "I like oat milk because it's creamy"
    ctx.signals = {}
    ctx.node_tracker = MagicMock()
    ctx.node_tracker.previous_focus = None
    ctx.recent_utterances = []
    return ctx


def _make_graph_state():
    ctx = MagicMock()
    ctx.node_count = 5
    ctx.edge_count = 3
    return ctx


@pytest.mark.asyncio
class TestTwoStageSelection:
    """Test the two-stage strategy→node selection flow."""

    async def test_node_binding_none_skips_node_selection(self):
        """Strategy with node_binding='none' should return focus_node_id=None."""
        reflect_strategy = StrategyConfig(
            name="reflect",
            description="Reflect",
            signal_weights={"meta.interview_progress": 0.5},
            node_binding="none",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[reflect_strategy],
            phases=None,
        )

        service = MethodologyStrategyService()

        # Mock the registry to return our test config
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        # Mock signal detection
        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "meta.interview_progress": 0.9,
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_1": {"graph.node.exhaustion_score": 0.5},
        }

        context = _make_context()
        graph_state = _make_graph_state()

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_phase_instance = AsyncMock()
            mock_phase_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_phase_instance

            result = await service.select_strategy_and_focus(
                context, graph_state, "test response"
            )

        strategy_name, focus_node_id, *_ = result
        assert strategy_name == "reflect"
        assert focus_node_id is None  # No node for node_binding="none"

    async def test_node_binding_required_selects_node(self):
        """Strategy with node_binding='required' should select best node."""
        deepen_strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "graph.node.exhaustion_score.low": 1.0,
            },
            node_binding="required",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[deepen_strategy],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "llm.response_depth": 0.1,  # low
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {"graph.node.exhaustion_score": 0.8},  # high → exhaustion_score.low=False
            "node_b": {"graph.node.exhaustion_score": 0.1},  # low → exhaustion_score.low=True
        }

        context = _make_context()
        graph_state = _make_graph_state()

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_phase_instance = AsyncMock()
            mock_phase_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_phase_instance

            result = await service.select_strategy_and_focus(
                context, graph_state, "test response"
            )

        strategy_name, focus_node_id, *_ = result
        assert strategy_name == "deepen"
        assert focus_node_id == "node_b"  # Lower exhaustion wins
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_methodology_strategy_service_two_stage.py -v`
Expected: FAIL — current code uses joint scoring, not two-stage

**Step 3: Implement**

Rewrite `select_strategy_and_focus()` in `src/services/methodology_strategy_service.py`. Replace the joint scoring block (lines 233-256) with:

```python
        from src.methodologies.scoring import (
            rank_strategies,
            rank_nodes_for_strategy,
            ScoredCandidate,
        )

        # --- Stage 1: Select strategy using global signals only ---
        ranked_strategies = rank_strategies(
            strategy_configs=strategies,
            signals=global_signals,
            phase_weights=phase_weights,
            phase_bonuses=phase_bonuses,
        )

        if not ranked_strategies:
            raise ScoringError(
                f"No strategies could be scored for methodology '{methodology_name}'. "
                f"Strategies available: {len(strategies)}."
            )

        best_strategy_config, best_strategy_score = ranked_strategies[0]

        # --- Stage 2: Select node (conditional on node_binding) ---
        focus_node_id = None
        score_decomposition: list[ScoredCandidate] = []

        if best_strategy_config.node_binding == "required" and node_signals:
            ranked_nodes, score_decomposition = rank_nodes_for_strategy(
                best_strategy_config, node_signals
            )
            if ranked_nodes:
                focus_node_id = ranked_nodes[0][0]

            log.info(
                "node_selected_for_strategy",
                strategy=best_strategy_config.name,
                node_id=focus_node_id,
                node_count=len(ranked_nodes),
                top3=[(nid, round(sc, 4)) for nid, sc in ranked_nodes[:3]],
            )
        else:
            log.info(
                "node_selection_skipped",
                strategy=best_strategy_config.name,
                node_binding=best_strategy_config.node_binding,
            )

        # Build alternatives for observability
        alternatives = [(s.name, score) for s, score in ranked_strategies]
```

Also update the import at the top of the file (line 24):
```python
from src.methodologies.scoring import rank_strategies, rank_nodes_for_strategy, ScoredCandidate
```

And remove the old import of `rank_strategy_node_pairs`.

**Important watch-outs:**
- The return type changes slightly: `alternatives` is now `List[Tuple[str, float]]` (no node_id in alternatives). The caller in `strategy_selection_stage.py` already handles both 2-tuple and 3-tuple formats (line 249), so this is backward compatible.
- `score_decomposition` now only contains node candidates for the winning strategy, not all S×N pairs. This is actually better for observability.
- If `node_binding="required"` but `node_signals` is empty (no tracked nodes yet), `focus_node_id` will be `None`. The caller already handles this.

**Step 4: Run tests**

Run: `uv run pytest tests/services/test_methodology_strategy_service_two_stage.py tests/methodologies/test_scoring.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/services/methodology_strategy_service.py tests/services/test_methodology_strategy_service_two_stage.py
git commit -m "feat: implement two-stage strategy→node selection in service"
```

---

## Task 6: Add `node_binding: none` to YAML Configs

**Files:**
- Modify: `config/methodologies/means_end_chain.yaml`
- Modify: `config/methodologies/jobs_to_be_done.yaml`
- Modify: `config/methodologies/critical_incident.yaml`

**Step 1: Review which strategies should have `node_binding: none`**

For MEC (`means_end_chain.yaml`):
- `deepen` → `required` (default, no change needed)
- `clarify` → `required` (default, no change needed)
- `explore` → `required` (default, no change needed)
- `reflect` → `none` (summarizes across nodes)
- `revitalize` → `none` (re-engages at interview level)

For JTBD (`jobs_to_be_done.yaml`): Read the file to check strategy names, then apply same logic.

For CIT (`critical_incident.yaml`): Read the file to check strategy names, then apply same logic.

**Step 2: Add `node_binding: none` to reflect and revitalize strategies**

In `config/methodologies/means_end_chain.yaml`, add `node_binding: none` to the reflect strategy (around line 219) and revitalize strategy (around line 242):

```yaml
  # Strategy 4: Reflect and validate (validation)
  - name: reflect
    node_binding: none     # NEW — operates on interview level, not specific nodes
    description: "Summarize what you've heard..."
    # ... rest stays the same

  # Strategy 5: Revitalize engagement
  - name: revitalize
    node_binding: none     # NEW — re-engagement is interview-level
    description: "Shift to fresh topics..."
    # ... rest stays the same
```

Do the same for equivalent strategies in JTBD and CIT YAMLs. Check each file to identify which strategies are node-independent (typically: reflect, synthesize, revitalize, wrap_up, and any `focus_mode: summary` strategies).

**Step 3: Run validation**

Run: `uv run pytest tests/methodologies/test_scoring.py -v`
Also run: `uv run python -c "from src.methodologies.registry import MethodologyRegistry; r = MethodologyRegistry(); [r.get_methodology(m) for m in r.list_methodologies()]; print('All configs valid')"`

Expected: All pass, no validation errors

**Step 4: Commit**

```bash
git add config/methodologies/means_end_chain.yaml config/methodologies/jobs_to_be_done.yaml config/methodologies/critical_incident.yaml
git commit -m "feat: add node_binding to reflect/revitalize strategies in all YAMLs"
```

---

## Task 7: Update `strategy_selection_stage.py` for New Return Format

**Files:**
- Modify: `src/services/turn_pipeline/stages/strategy_selection_stage.py`

The stage's `_select_strategy_and_node()` method currently expects 6-element tuple from the service. After Task 5, the alternatives format changed (2-tuple instead of 3-tuple). The stage already handles both formats (line 249 checks `len(alt)`), but we should simplify and remove the legacy 3-tuple handling.

**Step 1: Review current `_select_strategy_and_node` method**

The method at line 170 calls `self.methodology_strategy.select_strategy_and_focus()` and then simplifies alternatives. After the service change, alternatives are already 2-tuples, so the simplification loop (lines 245-257) can be simplified.

**Step 2: Simplify the alternatives handling**

Replace lines 242-257 with:

```python
        # Alternatives are already (strategy_name, score) tuples from two-stage selection
        simplified_alternatives = alternatives
```

Keep the rest of the method unchanged.

**Step 3: Run full test suite to check nothing breaks**

Run: `uv run pytest tests/ -v --timeout=60 -x`
Expected: PASS

**Step 4: Commit**

```bash
git add src/services/turn_pipeline/stages/strategy_selection_stage.py
git commit -m "refactor: simplify alternatives handling for two-stage selection"
```

---

## Task 8: Run Full Simulation and Verify

**Files:** No code changes — verification only.

**Step 1: Run a simulation with MEC**

```bash
uv run python scripts/run_simulation.py oat_milk_v2 convenience_seeker 10
```

Expected: Completes without errors. Check the output JSON for:
- `strategy` field varies (not 100% deepen)
- `focus_node_id` is `null` for reflect/revitalize turns
- `score_decomposition` contains only node candidates (not S×N)

**Step 2: Verify scoring CSV**

```bash
uv run python scripts/generate_scoring_csv.py synthetic_interviews/<latest>.json
```

Review the CSV to confirm decomposition looks correct.

**Step 3: Run full test suite**

```bash
uv run pytest tests/ -v --timeout=120
```

Expected: ALL PASS

**Step 4: Run linting**

```bash
ruff check . --fix
ruff format .
```

**Step 5: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: post-simulation cleanup and formatting"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/methodologies/registry.py` | Add `node_binding` field to `StrategyConfig`, validation |
| `src/methodologies/scoring.py` | Add `partition_signal_weights()`, `rank_nodes_for_strategy()`, update `rank_strategies()` to exclude node signals |
| `src/services/methodology_strategy_service.py` | Replace joint scoring with two-stage: `rank_strategies()` then `rank_nodes_for_strategy()` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Simplify alternatives handling |
| `config/methodologies/means_end_chain.yaml` | Add `node_binding: none` to reflect, revitalize |
| `config/methodologies/jobs_to_be_done.yaml` | Add `node_binding: none` to applicable strategies |
| `config/methodologies/critical_incident.yaml` | Add `node_binding: none` to applicable strategies |
| `tests/methodologies/test_scoring.py` | Tests for partition, node ranking, strategy exclusion |
| `tests/services/test_methodology_strategy_service_two_stage.py` | Integration tests for two-stage flow |

**What does NOT change:**
- Signal detectors (all `src/signals/` files)
- YAML `signal_weights` keys (auto-partitioned)
- `score_strategy()` and `score_strategy_with_decomposition()` (still score whatever weights given)
- `_get_signal_value()` (threshold binning unchanged)
- Pipeline stage order and contracts
- `rank_strategy_node_pairs()` — **kept but unused** (available as fallback during transition; can be removed in a follow-up)
