# Top-K Joint Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 2-stage strategy selection (Stage 1: pick strategy, Stage 2: pick node for that strategy) with joint scoring that evaluates all eligible (strategy, node) pairs and selects the globally best pair.

**Architecture:** Wire the existing `rank_strategy_node_pairs()` function from `scoring.py` into `MethodologyStrategyService.select_strategy_and_focus()`, replacing the sequential Stage 1 → Stage 2 flow. Partition strategies by `node_binding` — node-bound strategies go through joint scoring, conversation strategies (node_binding=none) are scored separately. Merge both candidate pools and select the global best.

**Tech Stack:** Python 3.12, pytest, Pydantic v2, structlog

**Spec:** `docs/superpowers/specs/2026-04-13-top-k-joint-scoring-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/services/methodology_strategy_service.py` | Modify | Core scoring refactor: replace 2-stage with joint scoring |
| `src/domain/models/pipeline_contracts.py` | Modify | Update `strategy_alternatives` type annotation |
| `src/services/turn_pipeline/context.py` | Modify | Update `strategy_alternatives` property return type |
| `src/services/turn_pipeline/pipeline.py` | Modify | Simplify alternative serialization (uniform 3-tuples) |
| `tests/services/test_methodology_strategy_service_two_stage.py` | Modify | Update existing tests + add new test |
| `scripts/extract_simulation_data.py` | Modify | Update alternatives parsing for 3-tuple format |

---

### Task 1: Update `StrategySelectionOutput` contract type

**Files:**
- Modify: `src/domain/models/pipeline_contracts.py:241-249`

- [ ] **Step 1: Update `strategy_alternatives` type annotation**

In `src/domain/models/pipeline_contracts.py`, change the `strategy_alternatives` field at line 241 from mixed 2/3-tuple to uniform 3-tuple:

```python
    # Before:
    strategy_alternatives: List[Union[tuple[str, float], tuple[str, str, float]]] = (
        Field(
            default_factory=list,
            description=(
                "Alternative strategies with scores for observability. "
                "Format: [(strategy, score)] or [(strategy, node_id, score)] for joint scoring"
            ),
        )
    )

    # After:
    strategy_alternatives: List[tuple[str, Optional[str], float]] = Field(
        default_factory=list,
        description=(
            "Alternative strategies with scores for observability. "
            "Format: [(strategy, node_id_or_None, score)] — uniform 3-tuples. "
            "node_id is a UUID string for node_binding='required' strategies, "
            "or None for node_binding='none' strategies."
        ),
    )
```

Also update the `score_decomposition` description at line 259 to remove Stage 1 / Stage 2 language:

```python
    # Before:
    score_decomposition: Optional[List[ScoredCandidate]] = Field(
        default=None,
        description=(
            "Per-candidate score decomposition from rank_strategies() and "
            "rank_nodes_for_strategy(). Combines Stage 1 (strategy-level with node_id='') "
            "and Stage 2 (node-level) decompositions. Each entry has strategy, node_id, "
            "signal_contributions (name/value/weight/contribution), base_score, "
            "phase_multiplier, phase_bonus, final_score, rank, selected. "
            "Populated during simulation; None in live API."
        ),
    )

    # After:
    score_decomposition: Optional[List[ScoredCandidate]] = Field(
        default=None,
        description=(
            "Per-candidate score decomposition from joint scoring. Each entry has "
            "strategy, node_id (UUID or None for conversation strategies), "
            "signal_contributions (name/value/weight/contribution), base_score, "
            "phase_multiplier, phase_bonus, final_score, rank, selected. "
            "Populated during simulation; None in live API."
        ),
    )
```

- [ ] **Step 2: Run ruff and pyright**

Run: `ruff check src/domain/models/pipeline_contracts.py`
Expected: No warnings.

Run: `uv run python -c "from src.domain.models.pipeline_contracts import StrategySelectionOutput; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/domain/models/pipeline_contracts.py
git commit -m "refactor(contracts): update StrategySelectionOutput for uniform 3-tuple alternatives"
```

---

### Task 2: Update `PipelineContext.strategy_alternatives` return type

**Files:**
- Modify: `src/services/turn_pipeline/context.py:464-479`

- [ ] **Step 1: Update return type annotation**

In `src/services/turn_pipeline/context.py`, update the `strategy_alternatives` property at line 464:

```python
    # Before:
    @property
    def strategy_alternatives(self) -> List[tuple[str, float] | tuple[str, str, float]]:
        """Get ranked alternative strategies with scores for observability.

        Returns:
            List of tuples from StrategySelectionOutput (Stage 6):
            - [(strategy, score)] for strategy-only scoring
            - [(strategy, node_id, score)] for joint strategy-node scoring
            Returns empty list if stage not yet completed.

        Note:
            Used for debugging and understanding why a strategy was selected.
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy_alternatives
        return []

    # After:
    @property
    def strategy_alternatives(self) -> List[tuple[str, Optional[str], float]]:
        """Get ranked alternative strategies with scores for observability.

        Returns:
            List of 3-tuples from StrategySelectionOutput (Stage 6):
            [(strategy, node_id_or_None, score)] — uniform format.
            node_id is a UUID string for node_binding='required' strategies,
            or None for node_binding='none' strategies.
            Returns empty list if stage not yet completed.
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy_alternatives
        return []
```

Add `Optional` to the imports at the top of the file if not already present.

- [ ] **Step 2: Run ruff**

Run: `ruff check src/services/turn_pipeline/context.py`
Expected: No warnings.

- [ ] **Step 3: Commit**

```bash
git add src/services/turn_pipeline/context.py
git commit -m "refactor(context): update strategy_alternatives return type to uniform 3-tuple"
```

---

### Task 3: Simplify alternative serialization in pipeline.py

**Files:**
- Modify: `src/services/turn_pipeline/pipeline.py:196-210`

- [ ] **Step 1: Simplify the 2-tuple / 3-tuple branching**

In `src/services/turn_pipeline/pipeline.py`, replace the alternative serialization block at lines 196-210:

```python
    # Before:
    if alternatives:
        strategy_alternatives = []
        for alt in alternatives:
            if len(alt) == 2:
                strategy, score = alt
                strategy_alternatives.append(
                    {"strategy": strategy, "score": score}
                )
            elif len(alt) == 3:
                strategy, node_id, score = alt
                strategy_alternatives.append(
                    {"strategy": strategy, "node_id": node_id, "score": score}
                )

    # After:
    if alternatives:
        strategy_alternatives = []
        for alt in alternatives:
            strategy, node_id, score = alt  # Uniform 3-tuple
            strategy_alternatives.append(
                {"strategy": strategy, "node_id": node_id, "score": score}
            )
```

- [ ] **Step 2: Run ruff**

Run: `ruff check src/services/turn_pipeline/pipeline.py`
Expected: No warnings.

- [ ] **Step 3: Commit**

```bash
git add src/services/turn_pipeline/pipeline.py
git commit -m "refactor(pipeline): simplify alternative serialization for uniform 3-tuples"
```

---

### Task 4: Refactor `MethodologyStrategyService.select_strategy_and_focus()`

This is the core change. The current method runs Stage 1 → Stage 2. The new method partitions strategies by node_binding, runs joint scoring for node-bound strategies and global scoring for conversation strategies, merges results, and selects the best pair.

**Files:**
- Modify: `src/services/methodology_strategy_service.py:85-393`

- [ ] **Step 1: Update imports**

At the top of `src/services/methodology_strategy_service.py`, add `rank_strategy_node_pairs` to the import from `scoring`:

```python
from src.methodologies.scoring import (
    rank_strategies,
    rank_nodes_for_strategy,
    rank_strategy_node_pairs,
    ScoredCandidate,
)
```

- [ ] **Step 2: Replace `select_strategy_and_focus()` method body**

Replace the method body from the `# --- Stage 1:` comment (line 245) through the return statement (line 393) with the joint scoring implementation. Keep everything before that (methodology config loading, node_tracker check, signal detection, phase detection) unchanged.

Replace the block starting at line 245 (`# --- Stage 1: Select strategy using global signals only ---`) through line 393 (the return statement) with:

```python
        # --- Joint scoring: evaluate all eligible (strategy, node) pairs ---

        # Partition strategies by node_binding
        node_bound_strategies = [s for s in strategies if s.node_binding == "required"]
        conversation_strategies = [s for s in strategies if s.node_binding == "none"]

        all_ranked: list[tuple[Any, Optional[str], float]] = []
        all_decomposition: list[ScoredCandidate] = []

        # Score node-bound strategies via joint scoring
        if node_bound_strategies:
            ranked_pairs, pair_decomposition = rank_strategy_node_pairs(
                node_bound_strategies,
                global_signals,
                node_signals,
                node_tracker=node_tracker,
                phase_weights=phase_weights,
                phase_bonuses=phase_bonuses,
            )
            # Convert (StrategyConfig, node_id, score) → (StrategyConfig, node_id, score)
            all_ranked.extend(ranked_pairs)
            all_decomposition.extend(pair_decomposition)

            log.info(
                "joint_scoring_complete",
                methodology=methodology_name,
                node_bound_count=len(node_bound_strategies),
                pairs_scored=len(ranked_pairs),
            )

        # Score conversation strategies via global-only scoring
        if conversation_strategies:
            ranked_conv, conv_decomposition = rank_strategies(
                conversation_strategies,
                global_signals,
                phase_weights=phase_weights,
                phase_bonuses=phase_bonuses,
                return_decomposition=True,
            )
            # Convert (StrategyConfig, score) → (StrategyConfig, None, score)
            for strat, score in ranked_conv:
                all_ranked.append((strat, None, score))
            all_decomposition.extend(conv_decomposition)

            log.info(
                "conversation_scoring_complete",
                methodology=methodology_name,
                conversation_count=len(conversation_strategies),
            )

        # Sort merged candidates by score descending
        all_ranked.sort(key=lambda x: x[2], reverse=True)

        if not all_ranked:
            log.error(
                "no_ranked_candidates",
                methodology=methodology_name,
                node_bound_count=len(node_bound_strategies),
                conversation_count=len(conversation_strategies),
                exc_info=True,
            )
            raise ScoringError(
                f"No valid (strategy, node) pairs could be scored for "
                f"methodology '{methodology_name}'. "
                f"Node-bound strategies: {len(node_bound_strategies)}, "
                f"Conversation strategies: {len(conversation_strategies)}."
            )

        best_strategy_config, best_node_id, best_score = all_ranked[0]

        # --- Threshold fallback check ---
        score_threshold = 0.0
        if config.chain_completion and isinstance(config.chain_completion, dict):
            score_threshold = float(
                config.chain_completion.get("score_threshold", 0.0)
            )

        if best_score < score_threshold:
            global_fatigue = global_signals.get("llm.global_response_trend") == "fatigued"
            engagement = global_signals.get("llm.engagement", 1.0)
            low_engagement = isinstance(engagement, (int, float)) and engagement < 0.3

            fallback_strategy_name: str | None = None
            if global_fatigue or low_engagement:
                fallback_strategy_name = "revitalize"

            if fallback_strategy_name:
                # Find the fallback in the ranked list or strategy configs
                fallback_pair = next(
                    (
                        (s, nid, sc)
                        for s, nid, sc in all_ranked
                        if s.name == fallback_strategy_name
                    ),
                    None,
                )
                if fallback_pair:
                    log.info(
                        "strategy_threshold_fallback",
                        methodology=methodology_name,
                        best_score=best_score,
                        threshold=score_threshold,
                        fallback_strategy=fallback_strategy_name,
                        reason="global_fatigue_or_low_engagement",
                    )
                    best_strategy_config, best_node_id, best_score = fallback_pair
                else:
                    log.debug(
                        "strategy_threshold_below_but_no_fallback",
                        methodology=methodology_name,
                        best_score=best_score,
                        threshold=score_threshold,
                    )

        # Assign rank and selected flags to decomposition
        ranked_order = {
            (s.name, nid): i
            for i, (s, nid, _) in enumerate(all_ranked)
        }
        for candidate in all_decomposition:
            key = (candidate.strategy, candidate.node_id if candidate.node_id else None)
            rank = ranked_order.get(key, len(all_ranked))
            candidate.rank = rank + 1
            candidate.selected = rank == 0

        # Build alternatives as uniform 3-tuples
        alternatives = [(s.name, nid, score) for s, nid, score in all_ranked]

        focus_node_id = best_node_id

        log.info(
            "strategy_selected",
            methodology=methodology_name,
            strategy=best_strategy_config.name,
            node_id=focus_node_id,
            score=best_score,
            node_binding=best_strategy_config.node_binding,
            alternatives_count=len(alternatives),
            top_3_alternatives=alternatives[:3],
            decomposition_count=len(all_decomposition),
        )

        return (
            best_strategy_config.name,
            focus_node_id,
            alternatives,
            global_signals,
            node_signals,
            all_decomposition,
        )
```

- [ ] **Step 3: Update docstring**

Update the class docstring at line 42 to remove "Two-stage" language:

```python
    """Strategy selection service using joint scoring architecture.

    Evaluates all eligible (strategy, node) pairs simultaneously and selects
    the globally highest-scoring pair. Node-bound strategies (node_binding='required')
    are scored via rank_strategy_node_pairs(); conversation strategies
    (node_binding='none') are scored via rank_strategies() with node_id=None.

    Signal detection is delegated to specialized services:
    - GlobalSignalDetectionService: graph.*, llm.*, temporal.*, meta.* signals
    - NodeSignalDetectionService: graph.node.*, technique.node.* signals per node
    """
```

Update the method docstring at line 98 to reflect joint scoring:

```python
        """Select best (strategy, node) pair using joint scoring with phase weights.

        Evaluates all eligible (strategy, node) pairs by combining global signals
        with node-level signals. Selects the globally highest-scoring pair.

        Detection flow:
        1. Detect global signals (llm.response_depth, graph.*, temporal.*)
        2. Detect node-level signals (graph.node.exhausted, meta.node.opportunity)
        3. Detect interview phase (early/mid/late) for phase weights/bonuses
        4. Score all eligible (strategy, node) pairs using combined signals
        5. Select highest-scoring pair

        Args:
            context: Pipeline context with methodology, node_tracker, recent_utterances
            graph_state: Current knowledge graph state with node/edge counts
            response_text: User's response text for LLM signal analysis

        Returns:
            Tuple of (strategy_name, focus_node_id, alternatives, global_signals,
            node_signals, decomposition):
            - strategy_name: Name of selected strategy
            - focus_node_id: UUID of selected focus node, or None for conversation strategies
            - alternatives: List of (strategy, node_id_or_None, score) tuples sorted by score
            - global_signals: Dict of detected global signals
            - node_signals: Dict mapping node_id to per-node signal dict
            - decomposition: List of ScoredCandidate with per-signal breakdown

        Raises:
            ConfigurationError: If methodology not found or has no strategies defined
            ValueError: If node_tracker is not available in context
            ScoringError: If no valid (strategy, node) pairs can be scored
        """
```

Also update the module docstring at line 1:

```python
"""Strategy selection service using joint scoring architecture.

Implements joint strategy-node selection where all eligible (strategy, node)
pairs are scored simultaneously using combined global and node signals.

Key concepts:
- Joint scoring: All (strategy, node) pairs scored together, best pair wins
- Phase weights: Multiplicative signal weights per interview phase (early/mid/late)
- Phase bonuses: Additive strategy bonuses per interview phase
- Node exhaustion: Penalty for over-probing the same node
- Signal pools: Shared signal detectors (graph, llm, temporal, meta)
"""
```

- [ ] **Step 4: Run ruff check**

Run: `ruff check src/services/methodology_strategy_service.py`
Expected: No warnings.

- [ ] **Step 5: Commit**

```bash
git add src/services/methodology_strategy_service.py
git commit -m "feat(scoring): replace 2-stage selection with joint (strategy, node) scoring"
```

---

### Task 5: Update existing tests

**Files:**
- Modify: `tests/services/test_methodology_strategy_service_two_stage.py`

- [ ] **Step 1: Update `test_alternatives_are_strategy_level`**

The alternatives are now 3-tuples `(strategy, node_id_or_None, score)` instead of mixed 2/3-tuples. Update the assertions:

```python
    async def test_alternatives_are_uniform_3tuples(self):
        """Alternatives should be uniform 3-tuples (strategy, node_id_or_None, score)."""
        s1 = StrategyConfig(
            name="deepen",
            description="D",
            signal_weights={"llm.response_depth.low": 0.8},
        )
        s2 = StrategyConfig(
            name="explore",
            description="E",
            signal_weights={"llm.response_depth.low": 0.5},
        )
        config = MethodologyConfig(
            name="test", description="T", signals={}, strategies=[s1, s2], phases=None
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {"llm.response_depth": 0.1}
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {"node_1": {}}

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        _, _, alternatives, *_ = result
        # Should be 3-tuples (strategy, node_id_or_None, score)
        assert len(alternatives) == 2
        assert len(alternatives[0]) == 3
        assert alternatives[0][0] == "deepen"  # Higher score
        assert alternatives[0][1] is None  # node_binding defaults to "required", no node signals match
```

- [ ] **Step 2: Update `test_stage1_decomposition_captured_in_output`**

Remove Stage 1 / Stage 2 terminology. The decomposition is now unified — no entries with `node_id=""`:

```python
    async def test_decomposition_captured_in_output(self):
        """Service should capture decomposition from joint scoring."""
        deepen = StrategyConfig(
            name="deepen",
            description="D",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "llm.engagement.high": 0.7,
                "graph.node.exhaustion_score.low": 1.0,  # Node-scoped weight
            },
        )
        explore = StrategyConfig(
            name="explore",
            description="E",
            signal_weights={"llm.response_depth.low": 0.5},
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[deepen, explore],
            phases={
                "mid": PhaseConfig(
                    name="mid",
                    description="Mid interview phase",
                    signal_weights={"deepen": 1.3},
                    phase_bonuses={"deepen": 0.2},
                )
            },
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "llm.response_depth": 0.1,  # low -> True
            "llm.engagement": 0.9,  # high -> True
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {"graph.node.exhaustion_score": 0.8},
            "node_b": {"graph.node.exhaustion_score": 0.1},
        }

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )

        # Verify strategy selection
        assert strategy_name == "deepen"
        assert focus_node_id == "node_b"  # Lower exhaustion wins

        # Verify decomposition exists
        assert decomp is not None
        assert len(decomp) > 0

        # All entries have real node_ids (no empty string entries)
        assert all(c.node_id != "" for c in decomp)
```

- [ ] **Step 3: Update `test_node_binding_none_has_only_strategy_decomposition`**

Conversation strategies now have `node_id=None` in decomposition (not `node_id=""`):

```python
    async def test_node_binding_none_has_none_node_id(self):
        """Strategy with node_binding='none' should have node_id=None in decomposition."""
        reflect = StrategyConfig(
            name="reflect",
            description="Reflect",
            signal_weights={"meta.interview_progress": 0.5},
            node_binding="none",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[reflect],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "meta.interview_progress": 0.9
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {}

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "late"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )

        assert strategy_name == "reflect"
        assert focus_node_id is None  # No node selection

        # Should have strategy decomposition with node_id=None
        assert decomp is not None
        assert len(decomp) == 1
        assert decomp[0].strategy == "reflect"
        assert decomp[0].node_id == ""  # rank_strategies uses "" for node_id
        assert len(decomp[0].signal_contributions) == 1
```

Note: `rank_strategies()` in `scoring.py` sets `node_id=""` for strategy-level entries. This is an existing behavior we preserve — the test asserts the actual output.

- [ ] **Step 4: Run all existing tests**

Run: `uv run pytest tests/services/test_methodology_strategy_service_two_stage.py -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/services/test_methodology_strategy_service_two_stage.py
git commit -m "test(scoring): update existing tests for joint scoring output format"
```

---

### Task 6: Add new test — strategy B beats strategy A on joint score

This is the bead-mandated test: when strategy A has the highest global score but strategy B has a better combined (strategy, node) pair, the joint scorer selects strategy B.

**Files:**
- Modify: `tests/services/test_methodology_strategy_service_two_stage.py`

- [ ] **Step 1: Write the failing test**

Add a new test class at the end of the file:

```python
@pytest.mark.asyncio
class TestJointScoringOverride:
    """Tests verifying that joint scoring can override the Stage 1 strategy winner."""

    async def test_better_node_overrides_higher_global_strategy(self):
        """When ascend wins globally but bridge has a better node, joint scoring selects bridge.

        This is the core motivation for joint scoring: the 2-stage architecture
        would pick ascend because it has the highest global score, but the
        (bridge, node_with_level_skip) pair has a higher combined score.
        """
        ascend = StrategyConfig(
            name="ascend",
            description="Ascend",
            signal_weights={
                "graph.node.gap_above.true": 0.5,
                "graph.node.exhaustion_score": -0.3,
            },
            node_binding="required",
            valid_when="graph.node.gap_above",
        )
        bridge = StrategyConfig(
            name="bridge",
            description="Bridge",
            signal_weights={
                "graph.node.level_skip.true": 0.8,
                "graph.node.exhaustion_score": -0.3,
            },
            node_binding="required",
            valid_when="graph.node.level_skip",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[ascend, bridge],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {}  # No global signals

        # Node A: has gap_above=True, NOT level_skip → only ascend is eligible
        # Node B: has level_skip=True, NOT gap_above → only bridge is eligible
        # Node A has high exhaustion (penalty), Node B has low exhaustion
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {
                "graph.node.gap_above": True,
                "graph.node.level_skip": False,
                "graph.node.exhaustion_score": 0.9,  # High exhaustion → big penalty
            },
            "node_b": {
                "graph.node.gap_above": False,
                "graph.node.level_skip": True,
                "graph.node.exhaustion_score": 0.1,  # Low exhaustion → small penalty
            },
        }

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )

        # Bridge on node_b should win because:
        # bridge score on node_b = 0.8 * 1.0 + (-0.3) * 0.1 = 0.77
        # ascend score on node_a = 0.5 * 1.0 + (-0.3) * 0.9 = 0.23
        assert strategy_name == "bridge"
        assert focus_node_id == "node_b"

    async def test_all_gates_filtered_raises_error(self):
        """When all valid_when gates filter out all strategies, raise ScoringError."""
        ascend = StrategyConfig(
            name="ascend",
            description="Ascend",
            signal_weights={"graph.node.gap_above.true": 0.5},
            node_binding="required",
            valid_when="graph.node.gap_above",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[ascend],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {}

        # No nodes pass the gap_above gate
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {
                "graph.node.gap_above": False,
            },
        }

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            with pytest.raises(ScoringError, match="No valid"):
                await service.select_strategy_and_focus(
                    _make_context(), _make_graph_state(), "test"
                )

    async def test_conversation_only_strategy_selected(self):
        """When only conversation strategies are eligible, returns (strategy, None, score)."""
        revitalize = StrategyConfig(
            name="revitalize",
            description="Revitalize",
            signal_weights={"llm.engagement.low": 0.8},
            node_binding="none",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[revitalize],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "llm.engagement": 0.1,  # low → True
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {"node_1": {}}

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )

        assert strategy_name == "revitalize"
        assert focus_node_id is None
```

- [ ] **Step 2: Add missing imports**

Ensure the test file imports `ScoringError`:

```python
from src.core.exceptions import ConfigurationError, ScoringError
```

- [ ] **Step 3: Run the new tests**

Run: `uv run pytest tests/services/test_methodology_strategy_service_two_stage.py::TestJointScoringOverride -v`
Expected: All 3 new tests pass.

- [ ] **Step 4: Run all tests in the file**

Run: `uv run pytest tests/services/test_methodology_strategy_service_two_stage.py -v`
Expected: All tests pass (existing + new).

- [ ] **Step 5: Commit**

```bash
git add tests/services/test_methodology_strategy_service_two_stage.py
git commit -m "test(scoring): add joint scoring override and edge case tests"
```

---

### Task 7: Update simulation extraction script

**Files:**
- Modify: `scripts/extract_simulation_data.py:61-65`

- [ ] **Step 1: Update alternatives parsing**

The alternatives are now serialized as `{"strategy": ..., "node_id": ..., "score": ...}` uniformly (no more `{"strategy": ..., "score": ...}` 2-field format). The extraction script already handles 3-field format via the `score` key, but let's verify and add `node_id` to the turns records:

At line 61-65, add node_id extraction from alternatives:

```python
        alts = t.get("strategy_alternatives") or []

        # Score margin: difference between rank 1 and rank 2
        alt_scores = sorted([a["score"] for a in alts], reverse=True) if alts else []
        score_margin = (alt_scores[0] - alt_scores[1]) if len(alt_scores) >= 2 else None

        # Best alternative node_id (may be None for conversation strategies)
        best_alt_node_id = alts[0].get("node_id") if alts else None
```

Then in the `turn_row` dict, add:

```python
            "best_alt_node_id": best_alt_node_id,
```

- [ ] **Step 2: Run ruff**

Run: `ruff check scripts/extract_simulation_data.py`
Expected: No warnings.

- [ ] **Step 3: Commit**

```bash
git add scripts/extract_simulation_data.py
git commit -m "feat(extraction): capture node_id from uniform 3-tuple alternatives"
```

---

### Task 8: Run full test suite and lint

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run ruff on the whole project**

Run: `ruff check .`
Expected: No new warnings.

Run: `ruff format .`
Expected: No formatting changes.

- [ ] **Step 3: Run doc drift check**

Run: `uv run python scripts/check_doc_drift.py`
Expected: No drift warnings related to strategy scoring changes.

---

### Task 9: Update context documentation

**Files:**
- Modify: `.claude/context/strategy-scoring.md`
- Modify: `.claude/context/strategy-selection.md`

- [ ] **Step 1: Update strategy-scoring.md**

In `.claude/context/strategy-scoring.md`, update the "Core Mechanics" section to remove Stage 1 / Stage 2 language and describe joint scoring:

Replace the first section (lines 1-30) with:

```markdown
# Strategy Scoring

## Core Mechanics

Strategy selection uses joint scoring — all eligible (strategy, node) pairs are
scored simultaneously and the globally highest-scoring pair is selected.

```
base_score = Σ(signal_weight × signal_value)
final_score = (base_score × phase_multiplier) + phase_bonus
```

### Joint Strategy-Node Scoring

`MethodologyStrategyService.select_strategy_and_focus()` partitions strategies
by `node_binding`:

- **node_binding='required'**: scored via `rank_strategy_node_pairs()` — each
  (strategy, node) pair gets merged global+node signals, valid_when gates filter
  ineligible pairs, and the pair is scored.
- **node_binding='none'**: scored via `rank_strategies()` — global signals only,
  node_id is None in the output.

Both candidate pools are merged and sorted by score. The highest-scoring pair
determines both the selected strategy and the target node for question generation.
```

Also update the `ScoredCandidate` section to remove Stage 1 / Stage 2 language.

- [ ] **Step 2: Update CLAUDE.md known failure modes**

In the project `CLAUDE.md`, update the "Known Failure Modes" section:

Replace:
```
- **`select_strategy_and_focus()` is D2:** The current architecture uses `rank_strategy_node_pairs()` for joint strategy-node scoring. Any doc or code referencing the old single-strategy D1 flow is outdated.
```

With:
```
- **`select_strategy_and_focus()` uses joint scoring:** All eligible (strategy, node) pairs are scored simultaneously via `rank_strategy_node_pairs()`. The old 2-stage (strategy-first, then node) architecture has been removed.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/context/strategy-scoring.md CLAUDE.md
git commit -m "docs: update strategy scoring docs for joint scoring architecture"
```
