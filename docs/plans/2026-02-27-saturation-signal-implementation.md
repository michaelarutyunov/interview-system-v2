# Saturation Signal Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the broken saturation formulas in both `meta.conversation.saturation` and `meta.canonical.saturation` with instantaneous, meaningful metrics, then wire suppression weights into mid-phase deepening strategies.

**Architecture:** Two existing signal classes get rewritten internals (same names, same registration). EWMA fields removed from SessionState/ContextLoadingOutput/ScoringPersistenceStage. Five methodology YAMLs get new negative weights on deepening strategies and recalibrated positive weights on validation strategies.

**Tech Stack:** Python (Pydantic models, async signal detectors), YAML methodology configs, pytest

**Design doc:** `docs/plans/2026-02-27-saturation-signal-redesign.md`

---

### Task 1: Write tests for new ConversationSaturationSignal formula

**Files:**
- Create: `tests/signals/meta/test_conversation_saturation.py`

**Step 1: Write the tests**

```python
"""Tests for ConversationSaturationSignal — extraction yield ratio."""

from unittest.mock import MagicMock

import pytest

from src.signals.meta.conversation_saturation import ConversationSaturationSignal


def _make_context(prev_surface: int, peak: float, turn: int = 5):
    """Build mock context with ContextLoadingOutput and graph_state."""
    clo = MagicMock()
    clo.prev_surface_node_count = prev_surface
    clo.surface_velocity_peak = peak
    ctx = MagicMock()
    ctx.context_loading_output = clo
    ctx.turn_number = turn
    return ctx


def _make_graph_state(node_count: int):
    gs = MagicMock()
    gs.node_count = node_count
    return gs


@pytest.mark.asyncio
async def test_matching_peak_yields_zero():
    """When current extraction matches peak, saturation = 0.0."""
    ctx = _make_context(prev_surface=20, peak=10.0)
    gs = _make_graph_state(node_count=30)  # delta=10, peak=10 → ratio=1.0 → sat=0.0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.0


@pytest.mark.asyncio
async def test_zero_extraction_yields_one():
    """When no new nodes extracted, saturation = 1.0."""
    ctx = _make_context(prev_surface=30, peak=10.0)
    gs = _make_graph_state(node_count=30)  # delta=0 → sat=1.0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 1.0


@pytest.mark.asyncio
async def test_half_peak_yields_half():
    """When extraction is half of peak, saturation = 0.5."""
    ctx = _make_context(prev_surface=25, peak=10.0)
    gs = _make_graph_state(node_count=30)  # delta=5, peak=10 → ratio=0.5 → sat=0.5
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.5


@pytest.mark.asyncio
async def test_exceeds_peak_clamps_to_zero():
    """When extraction exceeds peak, saturation clamps to 0.0."""
    ctx = _make_context(prev_surface=20, peak=5.0)
    gs = _make_graph_state(node_count=30)  # delta=10, peak=5 → ratio=2.0 → clamped → sat=0.0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.0


@pytest.mark.asyncio
async def test_zero_peak_yields_zero():
    """When peak is 0 (first turn), saturation = 0.0 (not saturated)."""
    ctx = _make_context(prev_surface=0, peak=0.0)
    gs = _make_graph_state(node_count=5)  # delta=5, but peak=0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.0


@pytest.mark.asyncio
async def test_no_graph_state_yields_zero():
    """When graph_state is None, saturation = 0.0."""
    ctx = _make_context(prev_surface=10, peak=5.0)
    result = await ConversationSaturationSignal().detect(ctx, None, "")
    assert result["meta.conversation.saturation"] == 1.0  # delta=0 (no graph → node_count=0, prev=10 → clamp to 0)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/signals/meta/test_conversation_saturation.py -v`
Expected: FAIL (old formula returns different values)

**Step 3: Commit failing tests**

```bash
git add tests/signals/meta/test_conversation_saturation.py
git commit -m "test: add failing tests for new conversation saturation formula"
```

---

### Task 2: Write tests for new CanonicalSaturationSignal formula

**Files:**
- Create: `tests/signals/meta/test_canonical_saturation.py`

**Step 1: Write the tests**

```python
"""Tests for CanonicalSaturationSignal — canonical novelty ratio."""

from unittest.mock import MagicMock

import pytest

from src.signals.meta.canonical_saturation import CanonicalSaturationSignal


def _make_context(prev_surface: int, prev_canonical: int):
    clo = MagicMock()
    clo.prev_surface_node_count = prev_surface
    clo.prev_canonical_node_count = prev_canonical
    ctx = MagicMock()
    ctx.context_loading_output = clo
    return ctx


def _make_graph_state(node_count: int):
    gs = MagicMock()
    gs.node_count = node_count
    return gs


def _make_canonical_state(concept_count: int):
    cgs = MagicMock()
    cgs.concept_count = concept_count
    return cgs


@pytest.mark.asyncio
async def test_pure_dedup_yields_one():
    """When 8 new surface nodes map to 0 new canonical → saturation = 1.0."""
    ctx = _make_context(prev_surface=22, prev_canonical=2)
    ctx.graph_state = _make_graph_state(node_count=30)  # delta_surface=8
    ctx.canonical_graph_state = _make_canonical_state(concept_count=2)  # delta_canonical=0
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 1.0


@pytest.mark.asyncio
async def test_all_novel_yields_zero():
    """When every new surface node creates a new canonical slot → saturation = 0.0."""
    ctx = _make_context(prev_surface=10, prev_canonical=5)
    ctx.graph_state = _make_graph_state(node_count=15)  # delta_surface=5
    ctx.canonical_graph_state = _make_canonical_state(concept_count=10)  # delta_canonical=5
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.0


@pytest.mark.asyncio
async def test_partial_novelty():
    """2 new canonical from 8 new surface → novelty=0.25, saturation=0.75."""
    ctx = _make_context(prev_surface=22, prev_canonical=4)
    ctx.graph_state = _make_graph_state(node_count=30)  # delta_surface=8
    ctx.canonical_graph_state = _make_canonical_state(concept_count=6)  # delta_canonical=2
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.75


@pytest.mark.asyncio
async def test_no_surface_extraction_yields_zero():
    """When no surface nodes extracted, saturation = 0.0 (not saturated — nothing to judge)."""
    ctx = _make_context(prev_surface=30, prev_canonical=10)
    ctx.graph_state = _make_graph_state(node_count=30)  # delta_surface=0
    ctx.canonical_graph_state = _make_canonical_state(concept_count=10)
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.0


@pytest.mark.asyncio
async def test_canonical_disabled_returns_empty():
    """When canonical graph is None (feature disabled), return empty dict."""
    ctx = _make_context(prev_surface=10, prev_canonical=0)
    ctx.graph_state = _make_graph_state(node_count=15)
    ctx.canonical_graph_state = None
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result == {}


@pytest.mark.asyncio
async def test_canonical_exceeds_surface_clamps():
    """Edge case: more canonical than surface (shouldn't happen, but clamp)."""
    ctx = _make_context(prev_surface=10, prev_canonical=5)
    ctx.graph_state = _make_graph_state(node_count=12)  # delta_surface=2
    ctx.canonical_graph_state = _make_canonical_state(concept_count=10)  # delta_canonical=5
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    # novelty_ratio = min(5/2, 1.0) = 1.0 → saturation = 0.0
    assert result["meta.canonical.saturation"] == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/signals/meta/test_canonical_saturation.py -v`
Expected: FAIL (old formula returns different values)

**Step 3: Commit failing tests**

```bash
git add tests/signals/meta/test_canonical_saturation.py
git commit -m "test: add failing tests for new canonical saturation formula"
```

---

### Task 3: Rewrite ConversationSaturationSignal

**Files:**
- Modify: `src/signals/meta/conversation_saturation.py` (entire file)

**Step 1: Replace the implementation**

```python
"""Conversation saturation signal from extraction yield ratio.

Measures how much extractable content the respondent is producing compared
to their peak turn. High saturation means the respondent's answers are
yielding fewer new surface nodes than their best turn — responses are
drying up regardless of engagement quality.
"""

from src.signals.signal_base import SignalDetector


class ConversationSaturationSignal(SignalDetector):
    """Extraction yield ratio: current surface node yield vs peak.

    Formula: saturation = 1.0 - min(current_delta / peak, 1.0)

    Output: 0.0 (matching or exceeding peak extraction) to 1.0 (zero extraction).
    Instantaneous per-turn, no smoothing.

    Namespaced signal: meta.conversation.saturation
    Cost: low (reads from ContextLoadingOutput and graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.conversation.saturation"
    description = "Extraction yield ratio: 0=extracting at peak rate, 1=zero extraction. Compares this turn's new surface nodes to the session's peak extraction turn."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        clo = context.context_loading_output
        peak = clo.surface_velocity_peak

        # Current turn's surface node delta
        prev_surface = clo.prev_surface_node_count
        current_surface = graph_state.node_count if graph_state else 0
        surface_delta = max(current_surface - prev_surface, 0)

        if peak > 0:
            yield_ratio = surface_delta / peak
        else:
            yield_ratio = 1.0  # first turn, no peak yet → not saturated

        saturation = 1.0 - min(yield_ratio, 1.0)
        return {self.signal_name: round(saturation, 4)}
```

**Step 2: Run tests**

Run: `uv run pytest tests/signals/meta/test_conversation_saturation.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/signals/meta/conversation_saturation.py
git commit -m "refactor: replace conversation saturation formula with extraction yield ratio"
```

---

### Task 4: Rewrite CanonicalSaturationSignal

**Files:**
- Modify: `src/signals/meta/canonical_saturation.py` (entire file)

**Step 1: Replace the implementation**

```python
"""Canonical saturation signal from novelty ratio.

Measures what fraction of this turn's surface extraction was thematically
redundant at the canonical level. High saturation means new surface nodes
are deduplicating into existing canonical slots — the respondent is
elaborating on known themes rather than introducing new ones.
"""

from src.signals.signal_base import SignalDetector


class CanonicalSaturationSignal(SignalDetector):
    """Canonical novelty ratio: new canonical slots / new surface nodes.

    Formula: saturation = 1.0 - min(canonical_delta / surface_delta, 1.0)

    Output: 0.0 (all new themes) to 1.0 (pure deduplication).
    Returns empty dict if canonical slots are disabled.
    Instantaneous per-turn, no smoothing.

    Namespaced signal: meta.canonical.saturation
    Cost: low (reads from ContextLoadingOutput, graph_state, canonical_graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.canonical.saturation"
    description = "Canonical novelty ratio: 0=all extraction is thematically new, 1=pure deduplication into existing canonical slots."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        clo = context.context_loading_output

        # Check if canonical graph is available
        cg_state = context.canonical_graph_state
        if cg_state is None:
            return {}

        # Surface delta this turn
        prev_surface = clo.prev_surface_node_count
        current_surface = graph_state.node_count if graph_state else 0
        surface_delta = max(current_surface - prev_surface, 0)

        # Canonical delta this turn
        prev_canonical = clo.prev_canonical_node_count
        current_canonical = cg_state.concept_count
        canonical_delta = max(current_canonical - prev_canonical, 0)

        if surface_delta > 0:
            novelty_ratio = min(canonical_delta / surface_delta, 1.0)
        else:
            novelty_ratio = 1.0  # no extraction → not saturated

        saturation = 1.0 - novelty_ratio
        return {self.signal_name: round(saturation, 4)}
```

**Step 2: Run tests**

Run: `uv run pytest tests/signals/meta/test_canonical_saturation.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/signals/meta/canonical_saturation.py
git commit -m "refactor: replace canonical saturation formula with novelty ratio"
```

---

### Task 5: Remove EWMA fields from SessionState, ContextLoadingOutput, and ScoringPersistenceStage

**Files:**
- Modify: `src/domain/models/session.py:66-67,75-76` — remove `surface_velocity_ewma`, `canonical_velocity_ewma`
- Modify: `src/domain/models/pipeline_contracts.py:55,58` — remove same fields
- Modify: `src/services/turn_pipeline/stages/scoring_persistence_stage.py:290,299,342,345` — remove EWMA computation
- Modify: `src/services/turn_pipeline/stages/context_loading_stage.py:124,127` — remove EWMA loading

**Step 1: Remove `surface_velocity_ewma` and `canonical_velocity_ewma` from `SessionState`**

In `src/domain/models/session.py`, delete lines 66-67 (`surface_velocity_ewma` field) and lines 75-76 (`canonical_velocity_ewma` field). Keep `surface_velocity_peak`, `canonical_velocity_peak`, `prev_surface_node_count`, `prev_canonical_node_count`.

**Step 2: Remove same fields from `ContextLoadingOutput`**

In `src/domain/models/pipeline_contracts.py`, delete line 55 (`surface_velocity_ewma`) and line 58 (`canonical_velocity_ewma`).

**Step 3: Remove EWMA computation from ScoringPersistenceStage**

In `src/services/turn_pipeline/stages/scoring_persistence_stage.py`:
- Line 290: delete `new_surface_ewma = alpha * surface_delta + ...`
- Line 299: delete `new_canonical_ewma = alpha * canonical_delta + ...`
- Line 304: delete `new_canonical_ewma = 0.0`
- Line 342: delete `surface_velocity_ewma=new_surface_ewma,`
- Line 345: delete `canonical_velocity_ewma=new_canonical_ewma,`
- If `alpha` variable is no longer used, remove it too.

**Step 4: Remove EWMA loading from ContextLoadingStage**

In `src/services/turn_pipeline/stages/context_loading_stage.py`:
- Line 124: delete `surface_velocity_ewma=session.state.surface_velocity_ewma,`
- Line 127: delete `canonical_velocity_ewma=session.state.canonical_velocity_ewma,`

**Step 5: Run all saturation tests + ruff check**

Run: `uv run pytest tests/signals/meta/ -v && ruff check src/domain/models/session.py src/domain/models/pipeline_contracts.py src/services/turn_pipeline/stages/scoring_persistence_stage.py src/services/turn_pipeline/stages/context_loading_stage.py`
Expected: PASS, no lint errors

**Step 6: Commit**

```bash
git add src/domain/models/session.py src/domain/models/pipeline_contracts.py src/services/turn_pipeline/stages/scoring_persistence_stage.py src/services/turn_pipeline/stages/context_loading_stage.py
git commit -m "refactor: remove unused EWMA velocity fields from session state and pipeline"
```

---

### Task 6: Add suppression weights to mid-phase deepening strategies (all 5 YAMLs)

**Files:**
- Modify: `config/methodologies/jobs_to_be_done.yaml` — `dig_motivation` signal_weights (after line ~310)
- Modify: `config/methodologies/means_end_chain.yaml` — `deepen` signal_weights (after line ~184)
- Modify: `config/methodologies/critical_incident.yaml` — `probe_attributions` signal_weights (after line ~335)
- Modify: `config/methodologies/repertory_grid.yaml` — `ladder_constructs` signal_weights (after line ~313)
- Modify: `config/methodologies/customer_journey_mapping.yaml` — `compare_expectations` signal_weights (after line ~395)

**Step 1: Add to each deepening strategy's `signal_weights` block**

Append these two lines to each strategy's signal_weights:

For CJM `compare_expectations`:
```yaml
      # Saturation suppression — pivot when themes/yield exhausted
      meta.canonical.saturation.high: -0.6
      meta.conversation.saturation.high: -0.4
```

For JTBD `dig_motivation`, MEC `deepen`, CIT `probe_attributions`, RG `ladder_constructs`:
```yaml
      # Saturation suppression — pivot when themes/yield exhausted
      meta.canonical.saturation.high: -0.5
      meta.conversation.saturation.high: -0.4
```

**Step 2: Recalibrate late-phase validation strategy weights**

In each of the 5 YAMLs, change the validation/reflect strategy's saturation weights from:
```yaml
      meta.conversation.saturation: 0.5
      meta.canonical.saturation: 0.3
```
to:
```yaml
      meta.conversation.saturation: 0.3
      meta.canonical.saturation: 0.2
```

These strategies are: `validate_outcome` (JTBD), `reflect` (MEC), `validate` (CIT, RG), `reflect_on_journey` (CJM).

**Step 3: Commit**

```bash
git add config/methodologies/
git commit -m "feat: add saturation suppression weights to mid-phase deepening strategies"
```

---

### Task 7: Run full test suite and lint

**Files:** None (verification only)

**Step 1: Run full signal tests**

Run: `uv run pytest tests/signals/ -v`
Expected: All PASS

**Step 2: Run ruff on all changed files**

Run: `ruff check . --fix && ruff format .`
Expected: Clean

**Step 3: Run full test suite**

Run: `uv run pytest -x`
Expected: All PASS

**Step 4: Commit any formatting fixes**

```bash
git add -A && git commit -m "style: formatting fixes" || echo "nothing to commit"
```
