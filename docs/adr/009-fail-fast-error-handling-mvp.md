# ADR 009: Fail-Fast Error Handling for MVP

**Date**: 2026-01-23
**Status**: Accepted
**Decision Makers**: Development Team
**Context**: Single interview MVP implementation

---

## Context

The current scoring engine catches exceptions from individual scorers, logs warnings, and continues processing with remaining scorers. This "graceful degradation" approach is appropriate for production systems with multiple concurrent users, but creates visibility problems for MVP testing:

1. **Silent failures**: Scorer errors are logged but not visible to the interviewer
2. **Ambiguous scores**: A 0.0 score from failed scorers is indistinguishable from legitimate low scores
3. **Debugging difficulties**: Issues compound as the interview continues with broken scoring
4. **No immediate feedback**: Developers only discover issues during post-mortem analysis

For a single-interview MVP focused on testing and iteration, we need immediate visibility into failures.

### Current Implementation

```python
# src/services/scoring/two_tier/engine.py:200-208, 259-267
except Exception as e:
    logger.warning(
        "Tier2 scorer failed",
        scorer=scorer.scorer_id,
        error=str(e),
    )
    reasoning_trace.append(f"{scorer.scorer_id}: ERROR - {str(e)}")
    # Continue with other scorers
```

### Requirements

- **MVP Context**: Single interview testing, ~20-30 turns
- **No concurrent users**: Race conditions and resilience are not immediate concerns
- **Testing focus**: Need to identify and fix issues quickly
- **Future scaling**: Must have clear migration path to production resilience

---

## Decision

We will implement **fail-fast error handling** for scorer failures in the MVP:

1. **Remove exception catching** for scorer failures
2. **Raise `ScorerFailureError`** when any scorer fails
3. **Terminate interview immediately** with clear error message
4. **Provide full stack traces** for debugging

### Implementation

```python
# New exception type
class ScorerFailureError(Exception):
    """Raised when a scorer fails and interview should terminate."""
    pass

# Updated scoring logic
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

---

## Consequences

### Positive

1. **Immediate visibility**: Developers know instantly when scoring breaks
2. **Clear error messages**: Exact scorer and error details in interview output
3. **Better debugging**: Full stack traces available immediately
4. **Simple implementation**: Removes exception handling complexity
5. **Forces fixes**: Can't continue with broken scoring system
6. **No ambiguity**: Failures are explicit, not hidden in scores

### Negative

1. **Less resilient**: One scorer failure terminates entire interview
2. **Requires restarts**: Cannot recover from failures without restarting interview
3. **Not production-ready**: Will need upgrade path for multi-user systems

### Migration Path to Production

When scaling beyond MVP (multiple concurrent users):

1. **Phase 1**: Add partial failure tolerance
   - Allow individual scorer failures
   - Fail only if ALL scorers fail
   - Track degradation in results

2. **Phase 2**: Add health monitoring
   - Pre-interview health checks
   - Continuous monitoring
   - Alerting for degradation

3. **Phase 3**: Add compensation logic
   - Transaction management across pipeline
   - Rollback on failures
   - Session error state tracking

(See `docs/raw_ideas/architectural-sense-check.md` for full production requirements)

---

## Alternatives Considered

### Alternative 1: Graceful Degradation (Current)

**Pros**:
- More resilient
- Interview continues despite failures
- Production-ready behavior

**Cons**:
- Silent failures during MVP testing
- Harder to debug
- Issues compound over time
- Over-engineered for single interview

**Verdict**: Rejected for MVP, but appropriate for production

### Alternative 2: Fail Only on Total Failure

**Pros**:
- More resilient than fail-fast
- Still fails when completely broken
- Allows partial scoring

**Cons**:
- More complex than fail-fast
- Might hide issues (e.g., 1 of 3 scorers fails)
- Still harder to debug than fail-fast

**Verdict**: Rejected for MVP, consider for Phase 1 of production migration

### Alternative 3: Health Check Only

**Pros**:
- No behavior change during interview
- Proactive testing before interview
- Easy to implement alongside current system

**Cons**:
- Requires manual execution
- Doesn't catch runtime failures
- No automatic protection

**Verdict**: Rejected as sole solution, but useful addition for pre-interview checks

---

## Implementation Notes

### Files Modified

1. `src/core/exceptions.py` - Add `ScorerFailureError`
2. `src/services/scoring/two_tier/engine.py:200-208` - Fail fast on Tier 1 errors
3. `src/services/scoring/two_tier/engine.py:259-267` - Fail fast on Tier 2 errors

### Testing Strategy

1. Write tests that verify scorer failures raise `ScorerFailureError`
2. Verify error messages include scorer ID and error details
3. Verify interview terminates immediately (no continued processing)
4. Manual testing with intentionally broken scorer configuration

### Rollback Plan

If fail-fast proves too aggressive even for MVP testing:
1. Revert to graceful degradation
2. Add health check endpoint (Alternative 3)
3. Run health check before each interview

---

## References

- `docs/raw_ideas/architectural-sense-check.md` - Production scaling requirements
- `docs/raw_ideas/silent_fail.md` - Detailed options analysis
- ADR-006: Scoring Architecture - Two-tier scoring system design
- ADR-008: Internal API Boundaries - Pipeline pattern

---

## Review and Update

This ADR should be revisited when:
1. Moving from single MVP interview to multiple concurrent users
2. Deploying to production environment
3. Scorer failures become too disruptive even during testing
4. Adding automated testing infrastructure that expects resilience
