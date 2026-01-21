# Phase 3: Scoring & Strategy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build multi-dimensional strategy scoring system for adaptive interview behavior

**Architecture:** 5 orthogonal scorers (Coverage, Depth, Saturation, Novelty, Richness) produce multipliers that combine multiplicatively via ArbitrationEngine to select optimal strategy/focus pairs. StrategyService orchestrates selection.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, pytest-asyncio, structlog, aiosqlite

---

## Context Notes for Implementation

### Key Design Principles
1. **Orthogonality**: Each scorer measures ONE dimension - no overlap
2. **Multiplicative Scoring**: final_score = base × ∏(weighted_scores) - creates emergent behavior
3. **Pure Functions**: Scorers are stateless functions of state (no side effects)
4. **Configuration-Driven**: All thresholds from config, never hardcoded

### GraphState Properties Used
Phase 3 scorers read these properties from `graph_state.properties`:
- `turn_count`: Current turn number
- `elements_total`: Total stimulus elements (list)
- `elements_seen`: Set of covered elements
- `new_info_rate`: Ratio of new concepts to total concepts
- `consecutive_low_info_turns`: Count of turns below threshold
- `avg_response_length`: Average user response length
- `recent_nodes`: List of recent node dicts

### File Organization
```
src/services/scoring/
├── __init__.py          # Package exports
├── base.py              # ScorerBase, ScorerOutput
├── coverage.py          # CoverageScorer
├── depth.py             # DepthScorer
├── saturation.py        # SaturationScorer
├── novelty.py           # NoveltyScorer
├── richness.py          # RichnessScorer
└── arbitration.py       # ArbitrationEngine

src/services/
└── strategy_service.py  # StrategyService orchestration

tests/unit/
├── test_scorer_base.py
├── test_coverage_scorer.py
├── test_depth_scorer.py
├── test_saturation_scorer.py
├── test_novelty_scorer.py
├── test_richness_scorer.py
├── test_arbitration.py
└── test_strategy_service.py
```

---

## Task 1: Create Scoring Package Structure

**Files:**
- Create: `src/services/scoring/__init__.py`
- Create: `src/services/scoring/base.py`
- Test: `tests/unit/test_scorer_base.py`

### Step 1: Create package __init__.py

```bash
mkdir -p src/services/scoring
```

Create `src/services/scoring/__init__.py`:
```python
"""Strategy scoring package."""

from src.services.scoring.base import ScorerBase, ScorerOutput

__all__ = ["ScorerBase", "ScorerOutput"]
```

### Step 2: Create ScorerOutput and ScorerBase in base.py

Create `src/services/scoring/base.py` with full content from spec 3.1.

### Step 3: Write failing tests for ScorerOutput

Create `tests/unit/test_scorer_base.py` with tests for:
- `test_create_valid_output`: Normal creation
- `test_raw_score_validation`: Scores must be 0-2
- `test_weight_validation`: Weights must be >= 0.1

Run: `pytest tests/unit/test_scorer_base.py::TestScorerOutput -v`
Expected: FAIL (base.py not yet created)

### Step 4: Implement ScorerOutput

Add ScorerOutput class to `src/services/scoring/base.py`:
```python
class ScorerOutput(BaseModel):
    """Output from a single scorer."""
    scorer_name: str = Field(description="Name of the scorer")
    raw_score: float = Field(default=1.0, ge=0.0, le=2.0, description="Raw score 0-2")
    weight: float = Field(default=1.0, ge=0.1, le=5.0, description="Scorer weight")
    weighted_score: float = Field(description="Score after weighting (raw^weight)")
    signals: Dict[str, Any] = Field(default_factory=dict, description="State signals used")
    reasoning: str = Field(default="", description="Human-readable explanation")

    model_config = {"from_attributes": True}
```

Run: `pytest tests/unit/test_scorer_base.py::TestScorerOutput -v`
Expected: PASS

### Step 5: Write failing tests for ScorerBase

Add tests to `tests/unit/test_scorer_base.py`:
- `test_init_with_defaults`: Default config values
- `test_init_with_config`: Custom config values
- `test_make_output_clamps_high_score`: Scores > 2.0 clamped to 2.0
- `test_make_output_clamps_low_score`: Scores < 0.0 clamped to 0.0
- `test_make_output_applies_weight`: weighted_score = raw_score^weight

Run: `pytest tests/unit/test_scorer_base.py::TestScorerBase -v`
Expected: FAIL (ScorerBase not implemented)

### Step 6: Implement ScorerBase

Add ScorerBase to `src/services/scoring/base.py` (full implementation from spec 3.1).

Run: `pytest tests/unit/test_scorer_base.py::TestScorerBase -v`
Expected: PASS

### Step 7: Verify imports

Run: `python3 -c "from src.services.scoring import ScorerBase, ScorerOutput; print('OK')"`
Expected: OK

### Step 8: Commit

```bash
git add src/services/scoring/ tests/unit/test_scorer_base.py
git commit -m "feat(scorers): add ScorerBase and ScorerOutput"
```

---

## Task 2: Implement CoverageScorer

**Files:**
- Create: `src/services/scoring/coverage.py`
- Test: `tests/unit/test_coverage_scorer.py`

### Step 1: Write failing tests

Create `tests/unit/test_coverage_scorer.py`:
```python
import pytest
from src.services.scoring.coverage import CoverageScorer
from src.domain.models.knowledge_graph import GraphState

@pytest.mark.asyncio
async def test_coverage_complete_no_boost():
    scorer = CoverageScorer()
    graph_state = GraphState(
        properties={
            "elements_total": 5,
            "elements_seen": {"a", "b", "c", "d", "e"},
        }
    )
    output = await scorer.score(
        strategy={"id": "cover", "type_category": "coverage"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.0

@pytest.mark.asyncio
async def test_coverage_gap_boosts_coverage_strategy():
    scorer = CoverageScorer()
    graph_state = GraphState(
        properties={"elements_total": 5, "elements_seen": {"a", "b", "c"}}
    )
    output = await scorer.score(
        strategy={"id": "cover", "type_category": "coverage"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 2.0  # gap_boost
```

Run: `pytest tests/unit/test_coverage_scorer.py -v`
Expected: FAIL (coverage.py not created)

### Step 2: Implement CoverageScorer

Create `src/services/scoring/coverage.py` with full implementation from spec 3.2.

Run: `pytest tests/unit/test_coverage_scorer.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/scoring/coverage.py tests/unit/test_coverage_scorer.py
git commit -m "feat(scorers): add CoverageScorer for element coverage tracking"
```

---

## Task 3: Implement DepthScorer

**Files:**
- Create: `src/services/scoring/depth.py`
- Test: `tests/unit/test_depth_scorer.py`

### Step 1: Write failing tests

Create `tests/unit/test_depth_scorer.py`:
```python
@pytest.mark.asyncio
async def test_early_phase_boosts_breadth():
    scorer = DepthScorer()
    graph_state = GraphState(properties={"turn_count": 3}, max_depth=1)
    output = await scorer.score(
        strategy={"id": "broaden", "type_category": "breadth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.5  # early_breadth_boost
```

Run: `pytest tests/unit/test_depth_scorer.py -v`
Expected: FAIL

### Step 2: Implement DepthScorer

Create `src/services/scoring/depth.py` from spec 3.3.

Run: `pytest tests/unit/test_depth_scorer.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/scoring/depth.py tests/unit/test_depth_scorer.py
git commit -m "feat(scorers): add DepthScorer for phase-based depth/breadth balance"
```

---

## Task 4: Implement SaturationScorer

**Files:**
- Create: `src/services/scoring/saturation.py`
- Test: `tests/unit/test_saturation_scorer.py`

### Step 1: Write failing tests

Create `tests/unit/test_saturation_scorer.py`:
```python
@pytest.mark.asyncio
async def test_saturated_penalizes_depth():
    scorer = SaturationScorer()
    graph_state = GraphState(
        properties={"new_info_rate": 0.02, "consecutive_low_info_turns": 3}
    )
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 0.3  # saturated_penalty
```

Run: `pytest tests/unit/test_saturation_scorer.py -v`
Expected: FAIL

### Step 2: Implement SaturationScorer

Create `src/services/scoring/saturation.py` from spec 3.4.

Run: `pytest tests/unit/test_saturation_scorer.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/scoring/saturation.py tests/unit/test_saturation_scorer.py
git commit -m "feat(scorers): add SaturationScorer for topic exhaustion detection"
```

---

## Task 5: Implement NoveltyScorer

**Files:**
- Create: `src/services/scoring/novelty.py`
- Test: `tests/unit/test_novelty_scorer.py`

### Step 1: Write failing tests

Create `tests/unit/test_novelty_scorer.py`:
```python
@pytest.mark.asyncio
async def test_recent_focus_penalized():
    scorer = NoveltyScorer()
    recent_nodes = [{"id": "node-1"}, {"id": "node-2"}]
    output = await scorer.score(
        strategy={"id": "deepen"},
        focus={"node_id": "node-1"},
        graph_state=GraphState(),
        recent_nodes=recent_nodes,
    )
    assert output.raw_score == 0.3  # recency_penalty
```

Run: `pytest tests/unit/test_novelty_scorer.py -v`
Expected: FAIL

### Step 2: Implement NoveltyScorer

Create `src/services/scoring/novelty.py` from spec 3.5.

Run: `pytest tests/unit/test_novelty_scorer.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/scoring/novelty.py tests/unit/test_novelty_scorer.py
git commit -m "feat(scorers): add NoveltyScorer for repetitive exploration prevention"
```

---

## Task 6: Implement RichnessScorer

**Files:**
- Create: `src/services/scoring/richness.py`
- Test: `tests/unit/test_richness_scorer.py`

### Step 1: Write failing tests

Create `tests/unit/test_richness_scorer.py`:
```python
@pytest.mark.asyncio
async def test_low_engagement_penalizes_depth():
    scorer = RichnessScorer()
    graph_state = GraphState(properties={"avg_response_length": 30})
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 0.6  # low_penalty
```

Run: `pytest tests/unit/test_richness_scorer.py -v`
Expected: FAIL

### Step 2: Implement RichnessScorer

Create `src/services/scoring/richness.py` from spec 3.6.

Run: `pytest tests/unit/test_richness_scorer.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/scoring/richness.py tests/unit/test_richness_scorer.py
git commit -m "feat(scorers): add RichnessScorer for engagement-based adaptation"
```

---

## Task 7: Implement ArbitrationEngine

**Files:**
- Create: `src/services/scoring/arbitration.py`
- Test: `tests/unit/test_arbitration.py`

### Step 1: Write failing tests

Create `tests/unit/test_arbitration.py`:
```python
@pytest.mark.asyncio
async def test_multiplies_scores():
    from src.services.scoring.arbitration import ArbitrationEngine
    from src.services.scoring.coverage import CoverageScorer
    from src.services.scoring.depth import DepthScorer

    scorers = [CoverageScorer(config={"weight": 1.0}), DepthScorer(config={"weight": 1.0})]
    engine = ArbitrationEngine(scorers)

    graph_state = GraphState(
        properties={"turn_count": 3, "elements_total": 5, "elements_seen": {"a", "b"}}
    )

    score, outputs, reasoning = await engine.score(
        strategy={"id": "broaden", "type_category": "breadth", "priority_base": 1.0},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )

    assert score > 1.0  # Both boost breadth
    assert len(outputs) == 2
```

Run: `pytest tests/unit/test_arbitration.py -v`
Expected: FAIL

### Step 2: Implement ArbitrationEngine

Create `src/services/scoring/arbitration.py` from spec 3.7.

Run: `pytest tests/unit/test_arbitration.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/scoring/arbitration.py tests/unit/test_arbitration.py
git commit -m "feat(scorers): add ArbitrationEngine for multi-dimensional scoring"
```

---

## Task 8: Implement StrategyService

**Files:**
- Create: `src/services/strategy_service.py`
- Test: `tests/unit/test_strategy_service.py`

### Step 1: Write failing tests

Create `tests/unit/test_strategy_service.py`:
```python
@pytest.mark.asyncio
async def test_selects_strategy():
    from src.services.strategy_service import StrategyService
    from src.services.scoring.arbitration import ArbitrationEngine
    from src.services.scoring.coverage import CoverageScorer

    engine = ArbitrationEngine([CoverageScorer()])
    service = StrategyService(engine, config={"veto_threshold": 0.1})

    graph_state = GraphState(
        properties={"turn_count": 5, "elements_total": ["a", "b", "c"], "elements_seen": {"a"}}
    )

    result = await service.select(graph_state, [])

    assert result.selected_strategy["id"] in ["deepen", "broaden", "cover_element"]
```

Run: `pytest tests/unit/test_strategy_service.py -v`
Expected: FAIL

### Step 2: Implement StrategyService

Create `src/services/strategy_service.py` from spec 3.8.

Run: `pytest tests/unit/test_strategy_service.py -v`
Expected: PASS

### Step 3: Commit

```bash
git add src/services/strategy_service.py tests/unit/test_strategy_service.py
git commit -m "feat(scorers): add StrategyService for adaptive strategy selection"
```

---

## Task 9: Integrate StrategyService into SessionService

**Files:**
- Modify: `src/services/session_service.py`

### Step 1: Update SessionService.__init__ signature

Read current `src/services/session_service.py` and update `__init__` to accept `strategy_service`:

```python
def __init__(
    self,
    session_repo: SessionRepository,
    graph_repo: GraphRepository,
    extraction_service: Optional[ExtractionService] = None,
    graph_service: Optional[GraphService] = None,
    question_service: Optional[QuestionService] = None,
    strategy_service: Optional[StrategyService] = None,  # NEW
    max_turns: int = 20,
    target_coverage: float = 0.8,
):
    # ... existing code ...
    self.strategy = strategy_service  # NEW
```

### Step 2: Update TurnResult dataclass

Add scoring dict with strategy info:
```python
@dataclass
class TurnResult:
    turn_number: int
    extracted: Dict[str, Any]
    graph_state: Dict[str, Any]
    scoring: Dict[str, Any]  # Now includes strategy_id, score, reasoning
    strategy_selected: str
    next_question: str
    should_continue: bool
    latency_ms: int = 0
```

### Step 3: Replace _select_strategy with strategy_service.select

Update process_turn method (around line 174):
```python
# OLD: strategy = self._select_strategy(...)
# NEW:
selection = await self.strategy.select(
    graph_state=graph_state,
    recent_nodes=[n.dict() for n in recent_nodes],
)
strategy = selection.selected_strategy["id"]
focus = selection.selected_focus
```

### Step 4: Update question generation

Pass strategy and focus to question generation:
```python
next_question = await self.question.generate_question(
    focus_concept=focus.get("node_id") or focus.get("element_id"),
    recent_utterances=updated_utterances,
    graph_state=graph_state,
    recent_nodes=recent_nodes,
    strategy=strategy,
)
```

### Step 5: Update TurnResult with scoring info

```python
return TurnResult(
    # ... existing fields ...
    scoring={
        "strategy_id": selection.selected_strategy["id"],
        "strategy_name": selection.selected_strategy["name"],
        "focus_type": selection.selected_focus.get("focus_type"),
        "final_score": selection.final_score,
        "reasoning": selection.scoring_reasoning[-3:] if selection.scoring_reasoning else [],
    },
    strategy_selected=strategy,
    # ...
)
```

### Step 6: Run integration tests

Run: `pytest tests/integration/test_session_flow.py -v`
Expected: PASS

### Step 7: Commit

```bash
git add src/services/session_service.py
git commit -m "feat(session): integrate StrategyService for adaptive strategy selection"
```

---

## Task 10: Update Package Exports

**Files:**
- Modify: `src/services/scoring/__init__.py`

### Step 1: Add all scorer exports

Update `src/services/scoring/__init__.py`:
```python
"""Strategy scoring package."""

from src.services.scoring.base import ScorerBase, ScorerOutput
from src.services.scoring.coverage import CoverageScorer
from src.services.scoring.depth import DepthScorer
from src.services.scoring.saturation import SaturationScorer
from src.services.scoring.novelty import NoveltyScorer
from src.services.scoring.richness import RichnessScorer
from src.services.scoring.arbitration import ArbitrationEngine

__all__ = [
    "ScorerBase",
    "ScorerOutput",
    "CoverageScorer",
    "DepthScorer",
    "SaturationScorer",
    "NoveltyScorer",
    "RichnessScorer",
    "ArbitrationEngine",
]
```

### Step 2: Verify imports

Run: `python3 -c "from src.services.scoring import *; print('All scorers imported')"`
Expected: All scorers imported

### Step 3: Commit

```bash
git add src/services/scoring/__init__.py
git commit -m "feat(scorers): export all scorers from package"
```

---

## Task 11: Complete Test Coverage

**Files:**
- Modify: All test files in tests/unit/

### Step 1: Add edge case tests to each scorer test file

For each scorer test file, add:
- Disabled scorer test
- Config override test
- Boundary condition tests

### Step 2: Run all scorer tests

Run: `pytest tests/unit/ -k "scorer or arbitration or strategy" -v`
Expected: All PASS

### Step 3: Check coverage

Run: `pytest tests/unit/ -k "scorer or arbitration or strategy" --cov=src/services/scoring --cov=src/services/strategy_service --cov-report=term-missing`
Expected: >80% coverage

### Step 4: Commit any test additions

```bash
git add tests/unit/
git commit -m "test(scorers): add edge case tests for all scorers"
```

---

## Task 12: Final Integration Verification

### Step 1: Run all tests

Run: `pytest tests/ -v`
Expected: All PASS

### Step 2: Verify end-to-end session flow

Run: `pytest tests/integration/test_session_flow.py -v -s`
Expected: Session completes with adaptive strategy selection

### Step 3: Check GraphState properties propagation

Verify that graph_state.properties contains all required fields:
- turn_count
- elements_total, elements_seen
- new_info_rate, consecutive_low_info_turns
- avg_response_length
- recent_nodes

Note: Some properties may need to be added to GraphState or computed dynamically.

### Step 4: Final commit

```bash
git add .
git commit -m "feat(phase-3): complete scoring and strategy selection system"
```

---

## Completion Checklist

- [ ] All 5 scorers implemented and tested
- [ ] ArbitrationEngine implemented with multiplicative scoring
- [ ] StrategyService implemented with focus generation
- [ ] SessionService integration complete
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Test coverage >80%
- [ ] Package exports correct

---

## Testing Commands Reference

```bash
# Test individual scorers
pytest tests/unit/test_scorer_base.py -v
pytest tests/unit/test_coverage_scorer.py -v
pytest tests/unit/test_depth_scorer.py -v
pytest tests/unit/test_saturation_scorer.py -v
pytest tests/unit/test_novelty_scorer.py -v
pytest tests/unit/test_richness_scorer.py -v

# Test orchestration
pytest tests/unit/test_arbitration.py -v
pytest tests/unit/test_strategy_service.py -v

# Test all scoring
pytest tests/unit/ -k "scorer or strategy or arbitration" -v

# Integration tests
pytest tests/integration/test_session_flow.py -v

# Coverage
pytest tests/unit/ -k "scorer" --cov=src/services/scoring --cov-report=term-missing
```

---

## Common Patterns

### Creating a new scorer (template):
1. Extend `ScorerBase`
2. Override `async def score(self, strategy, focus, graph_state, recent_nodes)`
3. Read signals from `graph_state.properties` or `recent_nodes`
4. Apply multipliers based on strategy type
5. Return `self.make_output(raw_score, signals, reasoning)`

### Testing a scorer:
1. Create GraphState with relevant properties
2. Create strategy dict with `type_category`
3. Create focus dict with `node_id` if needed
4. Create recent_nodes list for novelty testing
5. Call `await scorer.score(...)`
6. Assert `output.raw_score` and `output.reasoning`

---

`★ Insight ─────────────────────────────────────`
**Multiplicative Scoring Design**: Phase 3 uses multiplicative (not additive) combination of scorer outputs. This creates powerful emergent behavior: when multiple scorers agree (e.g., "saturation detected" AND "low engagement"), their effects compound exponentially. A veto (<0.1 score) effectively blocks the strategy regardless of other scorers.

**Pure Function Scorers**: Each scorer is designed as a pure function of its inputs - no side effects, no internal state mutation. This makes them trivially testable and composable. The "state" of the interview lives entirely in graph_state.properties.

**Configuration-Driven Thresholds**: All magic numbers (boost amounts, thresholds, weights) are constructor parameters from config dicts. This enables runtime tuning without code changes and supports A/B testing different scoring configurations.
`─────────────────────────────────────────────────`
