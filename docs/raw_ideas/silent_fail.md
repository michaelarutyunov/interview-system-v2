# Silent Failure Detection - MVP Implementation Plan

**Date**: 2026-01-23
**Context**: Single interview MVP (no concurrent users, ~20-30 turns)
**Goal**: Immediate visibility when something breaks during the interview

---

## Problem Statement

### Current Behavior
```python
# src/services/scoring/two_tier/engine.py:259-267
except Exception as e:
    logger.warning(
        "Tier2 scorer failed",
        scorer=scorer.scorer_id,
        error=str(e),
    )
    reasoning_trace.append(f"{scorer.scorer_id}: ERROR - {str(e)}")
    # Continue with other scorers
```

**Issues for MVP**:
1. Scorer failures are logged but silent - interviewer won't notice
2. If ALL scorers fail, you get 0.0 score (looks like valid low score)
3. No way to distinguish "legitimate bad strategy" from "scoring system is broken"
4. For single interview MVP, you need **immediate feedback**, not post-mortem analysis

---

## MVP Solution: Fail Fast with Clear Errors

For a single interview MVP, the best approach is **fail fast** rather than degrade gracefully.

### Philosophy
- ✅ **MVP**: If scoring breaks → stop interview → show error → fix it
- ❌ **Production**: Keep interview running → log degradation → alert ops team

### Benefits for MVP
1. Immediate feedback during testing
2. Forces you to fix issues before they compound
3. Simpler implementation (no health checks, no degradation tracking)
4. Better debugging experience

---

## Implementation Plan

### Option A: Fail Fast (Recommended for MVP)

**Change**: Don't catch scorer exceptions, let them bubble up

**Implementation**:
```python
# src/services/scoring/two_tier/engine.py

# BEFORE (current):
try:
    output = await scorer.score(...)
    tier2_outputs.append(output)
except Exception as e:
    logger.warning("Tier2 scorer failed", ...)
    # Continue with other scorers

# AFTER (MVP fail-fast):
try:
    output = await scorer.score(...)
    tier2_outputs.append(output)
except Exception as e:
    logger.error(
        "Scorer failed - terminating interview",
        scorer=scorer.scorer_id,
        error=str(e),
        strategy=strategy.get("id"),
        exc_info=True,
    )
    raise ScorerFailureError(
        f"Scorer {scorer.scorer_id} failed: {str(e)}"
    ) from e
```

**Benefits**:
- ✅ Immediate visibility
- ✅ Clear error messages in interview output
- ✅ Stack traces for debugging
- ✅ Zero additional complexity

**Tradeoffs**:
- ⚠️ One scorer failure kills entire interview
- ⚠️ Less resilient (but that's OK for MVP testing)

---

### Option B: Fail Fast on Total Failure Only

**Change**: Allow individual scorer failures, but fail if ALL scorers fail

**Implementation**:
```python
# src/services/scoring/two_tier/engine.py

# Track failures
tier2_failures = 0
tier2_total = len(self.tier2_scorers)

for scorer in self.tier2_scorers:
    try:
        output = await scorer.score(...)
        tier2_outputs.append(output)
        # ... existing logic ...
    except Exception as e:
        tier2_failures += 1
        logger.warning("Tier2 scorer failed", ...)
        reasoning_trace.append(f"{scorer.scorer_id}: ERROR - {str(e)}")

        # Check if ALL scorers failed
        if tier2_failures == tier2_total:
            logger.error(
                "All Tier2 scorers failed - terminating interview",
                strategy=strategy.get("id"),
            )
            raise AllScorersFailedError(
                f"All {tier2_total} Tier2 scorers failed for strategy {strategy.get('id')}"
            )
```

**Benefits**:
- ✅ More resilient than Option A
- ✅ Still fails fast when scoring completely broken
- ✅ Allows partial scoring failures

**Tradeoffs**:
- ⚠️ More complex than Option A
- ⚠️ Might hide issues if only 1 of 3 scorers fails

---

### Option C: Add Health Check Only (Minimal Change)

**Change**: Add single endpoint to verify scoring works

**Implementation**:
```python
# src/services/scoring/two_tier/engine.py

async def health_check(self) -> dict[str, Any]:
    """Test all scorers with dummy data to verify they work."""

    dummy_strategy = {"id": "test", "name": "Test Strategy"}
    dummy_focus = {"focus_type": "test"}

    results = {
        "tier1": {},
        "tier2": {},
        "healthy": True,
    }

    # Test Tier 1
    for scorer in self.tier1_scorers:
        try:
            await scorer.score(
                strategy=dummy_strategy,
                focus=dummy_focus,
                graph_state={},
                recent_nodes=[],
                conversation_history=[],
            )
            results["tier1"][scorer.scorer_id] = "✅ OK"
        except Exception as e:
            results["tier1"][scorer.scorer_id] = f"❌ FAILED: {str(e)}"
            results["healthy"] = False

    # Test Tier 2
    for scorer in self.tier2_scorers:
        try:
            await scorer.score(
                strategy=dummy_strategy,
                focus=dummy_focus,
                graph_state={},
                recent_nodes=[],
                conversation_history=[],
            )
            results["tier2"][scorer.scorer_id] = "✅ OK"
        except Exception as e:
            results["tier2"][scorer.scorer_id] = f"❌ FAILED: {str(e)}"
            results["healthy"] = False

    return results
```

**Usage**: Run before starting interview
```bash
# CLI or API endpoint
$ interview-system health-check

Scoring System Health:
  Tier 1 Scorers:
    ✅ coverage_gap_detector: OK
    ✅ depth_breadth_balance: OK
  Tier 2 Scorers:
    ✅ semantic_similarity: OK
    ✅ coverage_analysis: OK
    ❌ novelty_scorer: FAILED - API key missing

  Status: UNHEALTHY - 1 of 5 scorers failed
```

**Benefits**:
- ✅ No behavior change during interview
- ✅ Proactive testing before interview starts
- ✅ Easy to run manually

**Tradeoffs**:
- ⚠️ Requires manual execution
- ⚠️ Doesn't catch runtime failures during interview

---

## Recommendation for MVP

**Use Option A: Fail Fast**

**Rationale**:
1. You're testing with single interviews - you WANT it to break loudly
2. Simpler than tracking partial failures
3. Forces fixing issues immediately
4. Easy to change later if you need resilience

**When to switch**:
- Move to Option B when you have real users (graceful degradation)
- Move to production health checks (from architectural doc) when scaling

---

## Implementation Steps

### Step 1: Create Custom Exceptions
```python
# src/core/exceptions.py (create if doesn't exist)

class ScorerFailureError(Exception):
    """Raised when a scorer fails and interview should terminate."""
    pass

class AllScorersFailedError(Exception):
    """Raised when all scorers fail for a strategy."""
    pass
```

### Step 2: Update Scoring Engine

**File**: `src/services/scoring/two_tier/engine.py`

**Changes**:
- Line 200-208: Replace `logger.warning` with `logger.error` + raise exception (Tier 1)
- Line 259-267: Replace `logger.warning` with `logger.error` + raise exception (Tier 2)

### Step 3: Update Pipeline Error Handling

**File**: `src/services/turn_pipeline/pipeline.py`

**Changes**:
- Line 78-85: Already propagates exceptions correctly ✅
- Just verify that `ScorerFailureError` is caught and logged at API level

### Step 4: Test Failure Scenarios

**Manual Testing**:
1. Break a scorer configuration (wrong API key, etc.)
2. Start interview
3. Verify clear error message appears
4. Verify no orphaned data in database

---

## Validation Checklist

- [ ] Scorer failure terminates interview immediately
- [ ] Error message clearly identifies which scorer failed
- [ ] Stack trace available in logs for debugging
- [ ] No orphaned data in database after failure
- [ ] Easy to identify and fix the broken scorer

---

## Future Enhancements (Post-MVP)

When scaling beyond single interview MVP:

1. **Graceful Degradation** (from architectural doc P0-3)
   - Track failed scorer counts
   - Continue with partial scoring
   - Mark results as "degraded"

2. **Health Monitoring** (from architectural doc P0-3)
   - Continuous health checks
   - Alerting for scoring degradation
   - Metrics dashboard

3. **Compensation Logic** (from architectural doc P0-4)
   - Saga pattern for pipeline failures
   - Rollback on errors
   - Session error state tracking

---

## Files to Modify

1. `src/core/exceptions.py` - Add custom exceptions
2. `src/services/scoring/two_tier/engine.py:200-208, 259-267` - Fail fast on scorer errors
3. `src/services/turn_pipeline/pipeline.py:78-85` - Verify error propagation (already correct)

**Estimated Effort**: 30-60 minutes
**Testing Time**: 15-30 minutes

---

## Comparison: MVP vs Production

| Aspect | MVP (Fail Fast) | Production (Resilient) |
|--------|-----------------|------------------------|
| Scorer failure | ❌ Interview terminates | ⚠️ Mark as degraded, continue |
| Error visibility | ✅ Immediate, clear | 📊 Metrics dashboard |
| Recovery | 🔄 Restart interview | ♻️ Auto-compensation |
| Complexity | 🟢 Minimal | 🔴 High (saga pattern, health checks) |
| Best for | Testing, iteration | Multiple concurrent users |

---

## Summary

**For your single interview MVP**: Implement **Option A (Fail Fast)** - it's simple, gives immediate feedback, and appropriate for testing phase. You can always add resilience later when you scale.

The architectural review document describes the **production solution** you'll need eventually, but for MVP testing, failing fast is the right choice.
