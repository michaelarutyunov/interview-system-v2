# Phase 5: Global Response Tracking and Validation Triggers Implementation Plan

**Status:** Ready for Implementation
**Date:** 2026-01-29
**Parent Bead:** interview-system-v2-w61

## Overview

Implement global response tracking signals and validation strategy triggers. This enables the system to detect user engagement levels, fatigue, and uncertainty — triggering appropriate responses like validation/clarification.

## Tasks

### Task 1: Implement Global Response Trend Signal

**File:** `src/methodologies/signals/llm/global_response_trend.py` (new)

**Signal:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `llm.global_response_trend` | categorical | `deepening` / `stable` / `shallowing` / `fatigued` | Track response quality over time |

**Logic:**
```python
# Track last N response depths
recent = self.response_history[-5:]

if not recent:
    return "stable"

deep_count = sum(1 for d in recent if d == "deep")
shallow_count = sum(1 for d in recent if d in ["surface", "shallow"])

if shallow_count >= 4:
    return "fatigued"
elif shallow_count > deep_count:
    return "shallowing"
elif deep_count > shallow_count:
    return "deepening"
else:
    return "stable"
```

**Implementation:**
```python
class GlobalResponseTrendSignal(BaseLLMSignal):
    """Track if responses are getting shallower globally (fatigue?)."""

    signal_name = "llm.global_response_trend"
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    def __init__(self, history_size=10):
        self.response_history = []  # Track response depths across turns

    async def detect(self, context, graph_state, response_text) -> str:
        # Get current response depth from LLM
        # Add to history
        # Calculate trend
        pass
```

### Task 2: Implement Hedging Language Signal

**File:** `src/methodologies/signals/llm/hedging_language.py` (new)

**Signal:**

| Signal Name | Type | Values | Purpose |
|-------------|------|--------|---------|
| `llm.hedging_language` | categorical | `none` / `low` / `medium` / `high` | Detect uncertainty in responses |

**LLM Prompt:**
```
Analyze this response for hedging and uncertainty:

"{response_text}"

Look for:
- Hedging words: maybe, I think, sort of, kind of, I guess, probably
- Uncertain phrasing: not sure, it depends, might be, could be
- Tentative statements: qualifiers, hesitations

Rate the level of hedging/uncertainty:
- none: No hedging, confident statements
- low: Minimal hedging, mostly confident
- medium: Moderate hedging, some uncertainty
- high: Significant hedging, very uncertain
```

**Implementation:**
```python
class HedgingLanguageSignal(BaseLLMSignal):
    """Detect hedging, uncertainty, tentative language in responses."""

    signal_name = "llm.hedging_language"
    cost_tier = SignalCostTier.HIGH  # LLM call
    refresh_trigger = RefreshTrigger.PER_RESPONSE

    async def _analyze_with_llm(self, response_text: str) -> dict:
        # Use LLM to detect hedging/uncertainty
        pass
```

### Task 3: Update Validation Strategy with Uncertainty Triggers

**Files:**
- `src/methodologies/config/means_end_chain.yaml` (modify)
- `src/methodologies/config/jobs_to_be_done.yaml` (modify)

**Add hedging/uncertainty signal weights:**

```yaml
strategies:
  - name: reflect  # validation
    technique: validation
    signal_weights:
      # Existing weights...
      llm.hedging_language.high: 1.0  # Trigger on high uncertainty
      llm.hedging_language.medium: 0.7
      meta.node.opportunity.probe_deeper: 0.6  # Or extraction opportunity
```

### Task 4: Create Revitalization Strategy (Optional)

**File:** `src/methodologies/config/means_end_chain.yaml` (modify)

**Purpose:** When user shows fatigue (shallow responses), revitalize engagement.

```yaml
strategies:
  - name: revitalize
    technique: elaboration  # Or custom revitalization technique
    signal_weights:
      llm.global_response_trend.fatigued: 1.0
      llm.global_response_trend.shallowing: 0.5
      meta.node.opportunity.exhausted: 0.3  # Try exhausted nodes with new angle
```

### Task 5: Integrate Global Response Tracking into Pipeline

**File:** `src/services/methodology_strategy_service.py` (modify)

**Requirements:**
- Initialize GlobalResponseTrendSignal with session-scoped history
- Update history with each response
- Detect trend before strategy selection

**Implementation:**
```python
class MethodologyStrategyService:
    def __init__(self):
        # ... existing ...
        self.global_trend_signal = GlobalResponseTrendSignal()

    async def select_strategy_and_focus(...):
        # ... existing signal detection ...

        # Update and detect global response trend
        current_depth = global_signals.get("llm.response_depth", "surface")
        trend = await self.global_trend_signal.detect(context, graph_state, response_text)

        # Add trend to global_signals
        global_signals["llm.global_response_trend"] = trend
```

### Task 6: Add Unit Tests

**File:** `tests/methodologies/signals/test_llm_signals.py` (new)

**Test cases:**
- Test global response trend with various history patterns
- Test hedging language detection (with mocked LLM)
- Test fatigue detection
- Test uncertainty levels

### Task 7: Add Integration Tests

**File:** `tests/integration/test_global_response_tracking.py` (new)

**Test cases:**
- Test validation triggered by high hedging
- Test revitalization triggered by fatigue
- Test trend tracking across multiple turns
- Test end-to-end with uncertain responses

## Success Criteria

- [ ] Global response trend signal implemented
- [ ] Hedging language signal implemented
- [ ] Validation strategy updated with uncertainty triggers
- [ ] Global tracking integrated into pipeline
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] No ruff linting errors
- [ ] No pyright type errors

## Dependencies

- Phase 1: NodeStateTracker ✅
- Phase 2: Node-Level Signals ✅
- Phase 3: Joint Strategy-Node Scoring ✅
- Phase 4: Meta Signals and Phasing ✅
- LLM infrastructure setup (interview-system-v2-1xx) - ⚠️ May need to be addressed

## Signal Hierarchy

```
llm.global_response_trend (global, temporal)
└── Aggregates: llm.response_depth over N turns

llm.hedging_language (global, per-response)
└── LLM analysis of current response

Used by:
├── reflect/validate strategy (uncertainty → validate)
└── revitalize strategy (fatigue → re-engage)
```

## Design Patterns

**Session-Scoped Signal Tracking:**
- GlobalResponseTrendSignal maintains history across session
- Needs to be initialized once per session
- State persists across turns

**LLM Signal Pattern:**
- HedgingLanguageSignal extends BaseLLMSignal
- Fresh LLM analysis per response
- No caching across responses (per ADR-014)

## Next Phase

After Phase 5 completion, Phase 6 will focus on testing, calibration, and signal weight tuning using synthetic interviews.

## Notes on LLM Infrastructure

This phase requires LLM infrastructure for:
1. HedgingLanguageSignal (LLM-based)
2. Response depth detection (may already exist)

If LLM infrastructure is not fully wired up (see bead interview-system-v2-1xx), implement with:
- Mock LLM responses for testing
- Placeholder LLM integration
- Document where real LLM calls should be added
