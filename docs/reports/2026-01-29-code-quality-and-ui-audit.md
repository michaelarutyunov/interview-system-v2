# Code Quality and UI Audit Report

**Date:** 2026-01-29
**Branch:** feature/node-exhaustion-backtracking

## Summary

- **Ruff**: 1 error fixed (1 auto-fixed)
- **Pyright**: 38 errors found
- **UI**: 5 issues identified (3 critical, 2 minor)

---

## 1. Code Quality Results

### Ruff Linting
```
✅ 1 error auto-fixed
✅ All files formatted
```

**Issue fixed:** Unused import in `src/methodologies/signals/registry.py`

### Pyright Type Checking (38 errors)

#### Critical Errors (9)

**1. Dataclass isinstance pattern** (6 errors)
- Files: All technique files + focus_selection_service.py
- Issue: `isinstance(x, @dataclass)` pattern - incorrect first parameter
- Location: `src/methodologies/techniques/*.py`, `src/services/focus_selection_service.py:26`

```python
# ❌ Wrong
if isinstance(items, @dataclass):
    ...

# ✅ Correct
if hasattr(items, "__dataclass_fields__"):
    ...
```

**2. Strategy alternatives type mismatch** (1 error)
- File: `src/services/turn_pipeline/stages/strategy_selection_stage.py:122`
- Issue: `strategy_alternatives` type is `Sequence[tuple[str, float] | tuple[str, str, float]]` but expected `List[tuple[str, float]]`
- This is a **Phase 3 regression** - the pipeline contract needs updating

```python
# Current contract (WRONG):
strategy_alternatives: List[tuple[str, float]]  # (strategy, score)

# Should be (to match Phase 3 joint scoring):
strategy_alternatives: List[tuple[str, float]] | List[tuple[str, str, float]]  # Mixed
```

**3. Optional member access** (2 errors)
- File: `src/services/focus_selection_service.py:138, 183`
- Issue: Accessing `.label` on potentially None objects

#### Test/Performance Errors (29)

**4. Performance test issues** (26 errors)
- File: `tests/performance/test_node_exhaustion_performance.py`
- Issues:
  - `pytest.stash` doesn't exist
  - Missing required parameters for KGNode
  - Missing `passed` parameter
  - Optional member access on NodeState

**5. Test runner issues** (3 errors)
- File: `tests/synthetic/runner/node_exhaustion_test_runner.py`
- Issue: `record_yield` gets `Optional[str]` but expects `str`

---

## 2. UI Issues

### Critical Issues (3)

**UI-1: Strategy ranking component incompatible with Phase 3**
- File: `ui/components/scoring.py:202-212`
- Issue: `_render_strategy_ranking()` expects dictionaries but receives tuples
- Impact: **Scoring tab will crash** when displaying alternatives

```python
# Current code (WRONG):
def _render_strategy_ranking(self, alternatives: List[Dict[str, Any]]):
    for i, alt in enumerate(alternatives[:5]):
        score = alt.get("score", 0)      # ❌ tuples don't have .get()
        name = alt.get("strategy", "unknown")  # ❌ tuples don't have .get()

# After Phase 3, alternatives is:
# List[tuple[str, str, float]] or List[tuple[str, float]]
# e.g., [("deepen", "node_1", 1.5), ("clarify", "node_2", 0.8)]
```

**Fix needed:** Handle both dict and tuple formats for backward compatibility

---

**UI-2: "Phase" not exposed in API response**
- File: `ui/streamlit_app.py:198`
- Issue: Phase is displayed but not actually returned by `/sessions/{id}/status` endpoint
- Impact: Phase always shows "UNKNOWN"

```python
# Streamlit app displays:
phase = status_data.get("phase", "unknown")  # Always "unknown" - not in response

# But phase IS calculated in MethodologyStrategyService
# Just not exposed through the API
```

**Fix needed:** Add `phase` to session status response

---

**UI-3: Legacy signals displayed for MEC**
- File: `ui/components/scoring.py:106-131`
- Issue: Lists MEC-specific signals like `ladder_depth`, `edge_density` which don't exist in Phase 4 methodology-centric architecture
- Impact: Empty signal sections in UI

**Signals that no longer exist:**
- `ladder_depth` (replaced by `graph.max_depth`)
- `edge_density` (replaced by graph metrics)
- `disconnected_nodes` (replaced by `graph.orphan_count`)
- `coverage_breadth` (still exists but in different namespace)
- `missing_terminal_value` (still exists)
- `attributes_explored` (doesn't exist)
- `consequences_explored` (doesn't exist)
- `values_explored` (doesn't exist)

### Minor Issues (2)

**UI-4: Redundant "scoring" field in metrics**
- File: `ui/components/metrics.py:130-151`
- Issue: `_render_scoring()` displays Coverage, Depth, Saturation, Novelty, Richness gauges
- These are from the old two-tier scoring system (removed in Phase 6)
- Impact: Shows empty gauges (no data)

**Fix:** Remove this section or update for Phase 4 signals

---

**UI-5: Hardcoded strategy descriptions**
- File: `ui/components/metrics.py:194-199`
- Issue: Strategy descriptions hardcoded and don't match current strategies

```python
# Current (incomplete):
strategy_descriptions = {
    "deepen": "🔍 Deepen - Explore deeper in current topic chain",
    "broaden": "🌐 Broaden - Find new topic branches",
    "cover_element": "🎯 Cover - Introduce unexplored elements",
    "closing": "✅ Closing - Wrap up the interview",
    "reflection": "🤔 Reflection - Meta-question about the experience",
}

# Missing Phase 4 strategies:
# - clarify (not broaden)
# - explore (not cover_element)
# - reflect (not reflection)
```

**Fix needed:** Update for current strategies (deepen, clarify, explore, reflect, revitalize)

---

## 3. Recommended Fixes

### Priority 1: Fix Phase 3 contract mismatch

**File:** `src/domain/models/pipeline_contracts.py:142-169`

```python
class StrategySelectionOutput(BaseModel):
    # ... existing fields ...

    # Phase 4: Methodology-based selection fields
    signals: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detected signals from methodology-specific signal detector (Phase 4)",
    )
    strategy_alternatives: List[
        Union[tuple[str, float], tuple[str, str, float]]
    ] = Field(  # ← CHANGE THIS
        default_factory=list,
        description=(
            "Alternative strategies with scores for observability (Phase 4). "
            "Format: [(strategy, score)] or [(strategy, node_id, score)] for joint scoring"
        ),
    )
```

### Priority 2: Fix UI strategy ranking component

**File:** `ui/components/scoring.py:202-227`

```python
def _render_strategy_ranking(self, alternatives):
    """Render strategy ranking with scores."""
    for i, alt in enumerate(alternatives[:5]):
        # Handle both dict (legacy) and tuple (Phase 3) formats
        if isinstance(alt, dict):
            score = alt.get("score", 0)
            name = alt.get("strategy", "unknown")
        else:
            # Phase 3 format: tuple[str, float] or tuple[str, str, float]
            if len(alt) == 2:
                name, score = alt
            elif len(alt) == 3:
                name, node_id, score = alt  # node_id available but not displayed
            else:
                continue

        # Highlight selected (first)
        if i == 0:
            st.markdown(f"**→ {name}** `{score:.2f}` ✓")
        else:
            st.markdown(f"  {name} `{score:.2f}`")

        # Progress bar for score
        st.progress(min(max(score, 0.0), 1.0))
```

### Priority 3: Add phase to API response

**File:** `src/services/session_service.py` or wherever status is generated

Add to status response:
```python
{
    "turn_number": ...,
    "phase": "early",  # ← Add this
    "strategy_selected": ...,
}
```

### Priority 4: Fix isinstance dataclass pattern

Replace all:
```python
isinstance(x, @dataclass)
```

With:
```python
hasattr(x, "__dataclass_fields__")
```

Or import `dataclasses` and use:
```python
from dataclasses import is_dataclass
is_dataclass(x)
```

### Priority 5: Update UI signal lists

**File:** `ui/components/scoring.py:103-171`

Replace hardcoded signal lists with Phase 4 signals:
```python
# Node-level signals (Phase 2)
node_signals = {
    k: v
    for k, v in signals.items()
    if k.startswith("graph.node.") or k.startswith("technique.node.")
}

# Global signals
global_signals = {
    k: v
    for k, v in signals.items()
    if not (k.startswith("graph.node.") or k.startswith("technique.node."))
}
```

### Priority 6: Update strategy descriptions

**File:** `ui/components/metrics.py:194-199`

```python
strategy_descriptions = {
    # Phase 4 strategies
    "deepen": "🔍 Deepen - Build depth using laddering technique",
    "clarify": "🔎 Clarify - Probe for relationships and clarity",
    "explore": "🔍 Explore - Expand on recent topics",
    "reflect": "🤔 Reflect - Validate understanding and confirm",
    "revitalize": "⚡ Revitalize - Re-engage when fatigued",
}
```

---

## 4. Files Requiring Updates

### Must Fix (Critical)
1. `src/domain/models/pipeline_contracts.py` - Fix strategy_alternatives type
2. `ui/components/scoring.py` - Handle tuple alternatives
3. `src/services/session_service.py` - Add phase to status response
4. All technique files - Fix @dataclass isinstance pattern

### Should Fix (Important)
5. `ui/components/metrics.py` - Remove/update legacy scoring section
6. `ui/components/metrics.py` - Update strategy descriptions
7. `ui/components/scoring.py` - Update signal lists for Phase 4

### Can Defer (Tests)
8. `tests/performance/test_node_exhaustion_performance.py` - Fix test setup
9. `tests/synthetic/runner/node_exhaustion_test_runner.py` - Fix optional handling

---

## 5. Action Plan

1. **Fix pipeline contract** (5 min)
2. **Fix UI strategy ranking** (10 min)
3. **Add phase to API** (10 min)
4. **Fix isinstance patterns** (15 min)
5. **Update UI signals/strategies** (15 min)
6. **Fix test issues** (30 min)
7. **Re-run checks** (5 min)

**Total estimated time:** ~90 minutes

---

## 6. Beads to Track

- **interview-system-v2-4rz**: Fix ruff and pyright linting issues (already exists)
- **New bead**: Update UI components for Phase 3/4 compatibility
- **New bead**: Fix pipeline contract type mismatches
