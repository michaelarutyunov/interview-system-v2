# Architectural Sense Check - Interview System v2

**Date**: 2026-01-23
**Reviewer**: Claude (Architect Review Agent)
**Overall Grade**: B+ (Good architecture with critical gaps)

---

## Executive Summary

The codebase demonstrates solid foundations with clean pipeline separation and a well-designed two-tier scoring system. However, there are critical gaps around transaction management, race conditions, and error handling that could cause data inconsistency in production.

**Strengths**: Clean pipeline architecture, two-tier scoring, proper async/usage of Pydantic
**Critical Gaps**: No transaction management, turn count race conditions, silent scoring failures

---

## Critical Issues (P0 - Must Fix)

### 1. No Transaction Management Across Pipeline Stages

**Purpose**: Ensure atomicity of turn processing - either all stages succeed or none do, preventing orphaned or inconsistent state.

**Current Behavior**:
- Each pipeline stage creates its own database connection
- If stage 5 of 10 fails, stages 1-4 have already committed changes
- Example: Graph update succeeds → scoring persistence fails → orphaned graph state

**After Implementation**:
- Single transaction spans entire pipeline
- Any stage failure triggers rollback of all previous stage changes
- No orphaned utterances, nodes, or scores
- User sees either complete turn or error (no partial state)

**Files Affected**:
- `src/services/turn_pipeline/stages/context_loading_stage.py:62-71`
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py:121-171`
- `src/services/turn_pipeline/pipeline.py`

**Implementation Approach**:
- Implement Unit of Work pattern
- Pass single transaction context through pipeline stages
- Use `session.begin()` pattern with rollback on failure

---

### 2. Turn Count Race Condition

**Purpose**: Prevent concurrent turn requests from corrupting the turn counter.

**Current Behavior**:
```python
# src/services/turn_pipeline/stages/scoring_persistence_stage.py:241-252
turn_count=context.turn_number + 1,  # Read-modify-write without lock
```
- `context.turn_number` is loaded at pipeline start
- Multiple concurrent requests could read same value
- Results in duplicate or skipped turn numbers

**After Implementation**:
- Database-level atomic increment: `UPDATE sessions SET turn_count = turn_count + 1`
- Turn count is always consistent regardless of concurrency
- Or add version column with optimistic concurrency control

**Files Affected**:
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py:241-252`

**Implementation Approach**:
- Move turn count increment to database with atomic operation
- Return new turn count from database query

---

### 3. Silent Scoring Failures

**Purpose**: Detect and alert when scoring system degrades or fails, preventing silent quality degradation.

**Current Behavior**:
```python
# src/services/scoring/two_tier/engine.py:200-267
except Exception as e:
    logger.warning(...)  # Logged but continues
    # Continues with 0.0 score - indistinguishable from valid low score
```
- Scorers can fail silently
- No mechanism to detect if ALL scorers failed
- 0.0 scores look like valid data (legitimate low scores)

**After Implementation**:
- Track failed scorer count per candidate
- If >50% of Tier 2 scorers fail, mark candidate as "degraded"
- Health check endpoint reports scoring system status
- Alerts when scoring system is degraded

**Files Affected**:
- `src/services/scoring/two_tier/engine.py:200-267`

**Implementation Approach**:
- Add failure counter to scoring context
- Implement health check endpoint
- Add degraded status to candidate scoring results

---

### 4. No Pipeline Compensation Logic

**Purpose**: Enable recovery from mid-pipeline failures with proper cleanup and user notification.

**Current Behavior**:
- If any stage fails, exception is raised
- Previous stages have already modified persisted state
- User utterance is saved but no system response generated
- No mechanism to recover or clean up

**After Implementation**:
- Saga pattern with compensation actions for each stage
- On failure, execute compensation to undo previous stage effects
- Mark session as "error" state on pipeline failure
- User can see what went wrong and potentially retry

**Files Affected**:
- `src/services/turn_pipeline/pipeline.py:78-85`

**Implementation Approach**:
- Define compensation action for each stage (undo operation)
- Execute compensations in reverse order on failure
- Add session error state tracking

---

## High Priority Issues (P1)

### 5. N+1 Query in Recent Nodes

**Purpose**: Fix performance degradation as graph size increases.

**Current Behavior**:
```python
# src/services/graph_service.py:278-293
nodes = await self.repo.get_nodes_by_session(session_id)  # Fetches ALL nodes
sorted_nodes = sorted(nodes, key=lambda n: n.recorded_at, reverse=True)
return sorted_nodes[:limit]  # Then filters in Python
```
- Loads all nodes into memory, sorts, then filters
- Performance degrades linearly with total node count

**After Implementation**:
- Single SQL query with `ORDER BY recorded_at DESC LIMIT ?`
- Constant time regardless of total node count
- Significantly reduced memory usage

**Files Affected**:
- `src/services/graph_service.py:278-293`
- `src/persistence/repositories/graph_repo.py`

---

### 6. Double Context Loading

**Purpose**: Eliminate redundant database queries per turn.

**Current Behavior**:
- Session config queried twice: once in ContextLoadingStage, once in SessionService
- Wasted database round trip

**After Implementation**:
- Session config loaded once, cached in PipelineContext
- Reused across stages without re-querying

**Files Affected**:
- `src/services/turn_pipeline/stages/context_loading_stage.py:56-71`
- `src/services/session_service.py:428-430`

---

### 7. Weak Type Safety with Dict[str, Any]

**Purpose**: Improve type safety and catch errors at compile time rather than runtime.

**Current Behavior**:
- Mix of typed `Focus` models and `Dict[str, Any]`
- `focus: Optional[Dict[str, Any]]` in PipelineContext
- 148 `Optional` uses suggests many nullable fields without clear invariants

**After Implementation**:
- Standardize on typed models (Focus, etc.)
- Use `Optional` only when truly nullable with documented invariants
- Better IDE support and compile-time error detection

**Files Affected**:
- `src/services/turn_pipeline/context.py:54`
- `src/services/strategy_service.py:223`

---

### 8. Assertions in Production Code

**Purpose**: Prevent crashes when Python runs with optimizations enabled.

**Current Behavior**:
```python
# src/persistence/repositories/graph_repo.py:98-99
assert node is not None, "Node should exist just after creation"
```
- Assertions can be disabled with `python -O`
- Production could crash or have undefined behavior

**After Implementation**:
- Proper exceptions that cannot be disabled
- Clear error messages for debugging
- Consistent error handling

**Files Affected**:
- `src/persistence/repositories/graph_repo.py:98-99, 314-315`

---

## Medium Priority Issues (P2)

### 9. Inconsistent Error Handling Patterns

**Purpose**: Standardize error handling for predictable error propagation.

**Current Behavior**:
- SessionService raises `ValueError`
- API routes raise `SessionCompletedError`
- No consistent pattern across codebase

**After Implementation**:
- Domain-specific exceptions from `core/exceptions.py` used consistently
- Predictable error handling and user-facing error messages

---

### 10. Hardcoded Limits Scattered Across Code

**Purpose**: Centralize configuration for easier tuning.

**Current Behavior**:
- `limit=10` in ContextLoadingStage
- `limit=5` in recent nodes query
- `[:500]` truncation in scoring persistence

**After Implementation**:
- All limits in `interview_config.yaml`
- Easy to tune without code changes
- Different configs per environment

---

### 11. Missing Validation on Focus Object

**Purpose**: Prevent invalid database records from malformed focus data.

**Current Behavior**:
```python
# src/services/turn_pipeline/stages/scoring_persistence_stage.py:180-239
focus: dict,  # No validation
focus.get("focus_type", "")  # Returns empty string if missing
```
- Empty focus creates invalid database record
- No validation before DB insertion

**After Implementation**:
- Pydantic model validation before DB insertion
- Clear error messages for invalid focus data
- Type-safe focus handling

---

### 12. Large SessionService File

**Purpose**: Improve maintainability through better separation of concerns.

**Current Behavior**:
- `session_service.py` is 706 lines
- Multiple responsibilities mixed together

**After Implementation**:
- Extract scoring persistence logic to separate service
- Each service has single responsibility
- Easier to test and maintain

---

## Low Priority Issues (P3)

### 13. TODO Comments in Production Code

**Purpose**: Complete incomplete features.

**Current Behavior**:
- `TODO: Implement actual chain length calculation` in `depth_breadth_balance.py`

**After Implementation**:
- Feature fully implemented
- No technical debt markers

---

### 14. Inconsistent Naming Conventions

**Purpose**: Improve code readability and reduce confusion.

**Current Behavior**:
- `SessionContext` vs `PipelineContext` (similar purposes)
- Inconsistent naming across services

**After Implementation**:
- Consistent naming conventions
- Clear purpose for each component

---

## Data Flow Analysis

### Critical Path (Current):
```
User Input
  → UtteranceSavingStage (persists user utterance) ⚠️ Committed immediately
  → ExtractionStage (LLM call)
  → GraphUpdateStage (persists nodes/edges) ⚠️ Separate transaction
  → StateComputationStage (queries graph state)
  → StrategySelectionStage (scores candidates)
  → QuestionGenerationStage (LLM call)
  → ResponseSavingStage (persists system utterance) ⚠️ Separate transaction
  → ScoringPersistenceStage (persists scoring) ⚠️ Separate transaction
  → Turn count update ⚠️ Separate transaction
```

### Issues:
1. No atomic transaction spanning the turn
2. Utterance can be saved but question generation fails → orphaned utterance
3. Graph updates can succeed but scoring fails → inconsistent state
4. Turn count updated separately → race condition risk

### After P0 Fixes:
```
[Begin Transaction]
  → UtteranceSavingStage
  → ExtractionStage
  → GraphUpdateStage
  → StateComputationStage
  → StrategySelectionStage
  → QuestionGenerationStage
  → ResponseSavingStage
  → ScoringPersistenceStage
  → Turn count (atomic increment)
[Commit Transaction] OR [Rollback + Compensate]
```

---

## Summary Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Total Python Files | ~60 | ✅ |
| Total Lines of Code | ~12,843 | ✅ Good size |
| Optional Type Hints | 148 | ⚠️ High - reduce |
| TODO Comments | 1 | ✅ Good |
| Assertions in production | 2 | ⚠️ Remove |
| Largest File | 706 lines | ⚠️ Consider refactoring |

---

## Prioritized Action Plan

### Phase 1: Critical (Do First)
1. Implement transaction management across pipeline
2. Fix turn count race condition with atomic increment
3. Add saga compensation for pipeline failures
4. Replace assertions with proper exceptions

### Phase 2: High Priority
5. Fix N+1 query in get_recent_nodes
6. Eliminate double context loading
7. Standardize on typed models (Focus, etc.)
8. Add scorer health checks and failure tracking

### Phase 3: Medium Priority
9. Centralize configuration (remove hardcoded limits)
10. Refactor SessionService (extract scoring logic)
11. Standardize error handling patterns
12. Add validation before DB insertion

### Phase 4: Polish
13. Address TODO comments
14. Consistent naming conventions
15. Add connection pooling

---

## What's Working Well ✅

| Aspect | Details |
|--------|---------|
| Pipeline architecture | Clean separation, each stage has single responsibility |
| Two-tier scoring | Well-designed hybrid approach with clear veto/ranking |
| Repository pattern | Clean separation of business logic and persistence |
| Domain models | Pydantic models with proper typing |
| Observability | Structured logging with timings |
| Documentation | ADR process in place |

---

## References

- ADR-005: Dual Mode Interview Architecture
- `docs/raw_ideas/scorers.md`
- `docs/raw_ideas/strat-scoring.md`
- `docs/raw_ideas/strategies.md`
