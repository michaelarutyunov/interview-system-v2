# Remove Coverage-Driven Mode Infrastructure

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all dead coverage-driven mode infrastructure (~500 lines) since the system is purely exploratory.

**Architecture:** The coverage-driven mode was an alternative interview strategy that was never completed. It left dead code across domain models, persistence, API schemas, configuration, and services. We remove it bottom-up: dead code first, then simplify the InterviewMode enum, then remove GraphState.coverage_state (high-impact), then clean persistence/API/config layers.

**Tech Stack:** Python, Pydantic, FastAPI, SQLite (aiosqlite), pytest

**Decisions:**
- Remove everything including DB columns, concept_elements table, API fields
- Remove depth_calculator.py (only used by coverage state building)
- Keep InterviewMode enum with only EXPLORATORY value
- Do NOT touch `src/methodologies/signals/graph/coverage.py` (tracked by bead 6xa separately)

---

## Phase 1: Dead Code Removal (no external dependencies)

### Task 1: Remove duplicate coverage classes from concept.py

**Files:**
- Modify: `src/domain/models/concept.py:107-123`

**Step 1: Verify classes are unused**

Run: `grep -rn "from src.domain.models.concept import.*ElementCoverage\|from src.domain.models.concept import.*CoverageState" src/ tests/`
Expected: No output (unused)

**Step 2: Remove duplicate ElementCoverage and CoverageState from concept.py**

Remove lines 107-123 (the `ElementCoverage` and `CoverageState` dataclasses).

**Step 3: Run tests to verify nothing breaks**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -20`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/domain/models/concept.py
git commit -m "refactor: remove duplicate ElementCoverage/CoverageState from concept.py

Dead code - these classes were never imported anywhere.

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

### Task 2: Remove dead coverage classes from interview_state.py

**Files:**
- Modify: `src/domain/models/interview_state.py:98-353, 555-597`

**Step 1: Verify classes are unused**

Run: `grep -rn "TopicPriority\|TopicState\|create_interview_state\|_depth_for_priority" src/ tests/ --include="*.py" | grep -v "interview_state.py"`
Expected: No output (all unused outside their own file)

**Step 2: Remove dead code**

Remove these blocks from `interview_state.py`:
- Lines 98-108: Section header comment + `TopicPriority` enum
- Lines 111-186: `TopicState` dataclass
- Lines 188-353: `CoverageState(InterviewState)` dataclass
- Lines 555-584: `create_interview_state()` factory function
- Lines 590-597: `_depth_for_priority()` helper

Keep `InterviewMode` enum (will be simplified in Phase 2) and `ExploratoryState` class.

**Step 3: Run tests**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -20`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/domain/models/interview_state.py
git commit -m "refactor: remove dead TopicPriority, TopicState, CoverageState from interview_state.py

These classes were never imported outside their own file. Also removes
create_interview_state() factory and _depth_for_priority() helper.

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 2: Simplify InterviewMode Enum

### Task 3: Simplify InterviewMode to EXPLORATORY only and update all defaults

**Files:**
- Modify: `src/domain/models/interview_state.py` (InterviewMode enum)
- Modify: `src/domain/models/session.py` (mode defaults)
- Modify: `src/domain/models/turn.py` (mode default)
- Modify: `src/api/schemas.py` (mode defaults)
- Modify: `src/services/turn_pipeline/context.py` (default mode string)
- Modify: `src/domain/models/pipeline_contracts.py` (mode field)
- Modify: `src/services/simulation_service.py` (mode assignment)

**Step 1: Simplify InterviewMode enum**

In `interview_state.py`, change InterviewMode to only have EXPLORATORY:
```python
class InterviewMode(str, Enum):
    """Interview mode."""
    EXPLORATORY = "exploratory"
```

**Step 2: Update all defaults to EXPLORATORY**

In `session.py`:
- Line 19: `mode: InterviewMode = InterviewMode.EXPLORATORY`
- Line 33: `mode: InterviewMode = InterviewMode.EXPLORATORY`

In `turn.py`:
- Line 33: `mode: InterviewMode = InterviewMode.EXPLORATORY`

In `schemas.py`:
- Lines 23-26: `mode: InterviewMode = InterviewMode.EXPLORATORY`
- Line 40: `mode: InterviewMode = InterviewMode.EXPLORATORY`

In `context.py`:
- Line 114: change `return "coverage_driven"` to `return "exploratory"`

In `pipeline_contracts.py`:
- Line 33: update description to remove "coverage" mention

**Step 3: Run tests**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -20`
Expected: Some tests may fail if they assert `mode == "coverage_driven"`. Fix those tests.

**Step 4: Fix any failing tests**

Tests likely referencing COVERAGE_DRIVEN:
- `tests/pipeline/test_strategy_selection_new_schema.py`: Uses `mode="coverage_driven"`
- `tests/pipeline/test_context_loading_stage_contract.py`: Sets mock `mode.value = "coverage"`

Update these to use `"exploratory"`.

**Step 5: Run tests again**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -20`
Expected: All pass

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: simplify InterviewMode to EXPLORATORY only

Remove COVERAGE_DRIVEN enum value and update all defaults across
domain models, API schemas, pipeline context, and tests.

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 3: Remove CoverageState from GraphState (high-impact)

### Task 4: Remove CoverageState from knowledge_graph.py and all GraphState consumers

**Files:**
- Modify: `src/domain/models/knowledge_graph.py` (remove ElementCoverage, CoverageState, coverage_state field)
- Modify: `src/persistence/repositories/graph_repo.py` (remove _build_coverage_state and related)
- Modify: `src/services/turn_pipeline/stages/context_loading_stage.py` (remove CoverageState import/usage)
- Delete: `src/services/depth_calculator.py`
- Modify: ALL test files that construct GraphState with coverage_state parameter

**Step 1: Remove ElementCoverage, CoverageState classes from knowledge_graph.py**

Remove lines 79-96 (`ElementCoverage` and `CoverageState` models).

**Step 2: Remove coverage_state field from GraphState**

Remove lines 157-159 (`coverage_state: CoverageState` field) from `GraphState`.

**Step 3: Remove _build_coverage_state() and related from graph_repo.py**

Remove:
- Import of `CoverageState`, `ElementCoverage` (lines 24-25)
- Import of `DepthCalculator` (line 29)
- The `_build_coverage_state()` method (lines 541-633)
- The `_map_nodes_to_elements()` method (lines 635+)
- The `_load_concept_elements()` method (lines 764+)
- In `get_graph_state()`: remove the call to `_build_coverage_state()` and `coverage_state` assignment (lines 514-538)

**Step 4: Remove CoverageState from context_loading_stage.py**

Remove import (lines 114-118) and the `coverage_state=CoverageState()` from placeholder GraphState (line 124).

**Step 5: Delete depth_calculator.py**

```bash
rm src/services/depth_calculator.py
```

**Step 6: Update ALL test files constructing GraphState**

Remove `coverage_state=CoverageState()` from GraphState construction in:
- `tests/unit/test_models.py`
- `tests/unit/test_graph_service.py`
- `tests/unit/test_session_service.py`
- `tests/unit/test_question_service.py`
- `tests/domain/test_graph_state.py` (also remove coverage_state test cases)
- `tests/pipeline/test_strategy_selection_new_schema.py`
- `tests/methodologies/signals/test_all_signal_pools.py`
- `tests/methodologies/signals/test_graph_signals_poc.py`

Remove imports of `CoverageState`, `ElementCoverage` from all these files.

**Step 7: Run tests**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -30`
Expected: All pass

**Step 8: Commit**

```bash
git add -A
git commit -m "refactor: remove CoverageState from GraphState and all consumers

Remove ElementCoverage, CoverageState from knowledge_graph.py.
Remove coverage_state field from GraphState model.
Remove _build_coverage_state(), _map_nodes_to_elements(), _load_concept_elements()
from graph_repo.py. Delete depth_calculator.py (only consumer removed).
Update all tests constructing GraphState.

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 4: Clean Persistence Layer

### Task 5: Remove coverage_score from session_repo.py and scoring_persistence_stage.py

**Files:**
- Modify: `src/persistence/repositories/session_repo.py`
- Modify: `src/services/turn_pipeline/stages/scoring_persistence_stage.py`
- Modify: `src/services/session_service.py`
- Modify: `src/domain/models/pipeline_contracts.py` (coverage_score field)
- Modify: Tests referencing coverage_score

**Step 1: Remove coverage_score from session_repo.py**

- Lines 32-33: Remove `coverage_score` from INSERT column list
- Line 43: Remove `session.state.coverage_score` from values
- Lines 60-119: Remove `_populate_concept_elements()` method entirely
- Line 49: Remove the call to `_populate_concept_elements()`
- Lines 137-141: Remove `coverage_score` from `update_state()` SQL
- Lines 198-229: Remove `coverage_score` parameter from `save_scoring_history()`
- Lines 333-348: Remove `get_coverage_stats()` method entirely
- Line 536: Remove `coverage_score` from `_row_to_session()`

**Step 2: Remove coverage_score from SessionState model**

In `src/domain/models/session.py`:
- Remove `coverage_score: float = 0.0` field

**Step 3: Remove coverage_score from ScoringPersistenceOutput**

In `src/domain/models/pipeline_contracts.py`:
- Remove `coverage_score: float` field (line 306-307)

**Step 4: Remove coverage references from scoring_persistence_stage.py**

- Line 76: Remove `coverage_score` from output
- Lines 150, 158: Remove `coverage_score` from SQL INSERT
- Line 354: Remove `coverage_score` from `_update_turn_count()`
- Lines 360-391: Remove `coverage_score` extraction from `_extract_legacy_scores()`

**Step 5: Remove coverage references from session_service.py**

- Lines 94, 107, 133-136: Remove `target_coverage` parameter and storage
- Line 145: Remove `target_coverage` from log
- Line 286: Remove `coverage_score` from `_save_scoring()`
- Lines 657-665: Remove `get_coverage_stats()` call and coverage computation from `get_status()`
- Lines 686-687: Remove `coverage` and `target_coverage` from status return

**Step 6: Remove coverage from turn pipeline context**

In `src/services/turn_pipeline/context.py`:
- Line 252: Remove `"coverage"` from scoring dict

**Step 7: Remove coverage from simulation/synthetic services**

In `src/services/simulation_service.py`:
- Remove `coverage_score=0.0` from SessionState construction

In `src/services/synthetic_service.py`:
- Remove `"coverage_achieved": 0.0` from interview_context

**Step 8: Update tests**

- `tests/unit/test_session_repo.py`: Remove all coverage_score assertions
- `tests/unit/test_session_service.py`: Remove target_coverage and coverage_score references
- `tests/integration/test_e2e_system.py`: Remove coverage assertions from scoring response
- `tests/ui/test_smoke.py`: Remove coverage display/emoji tests

**Step 9: Run tests**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -30`
Expected: All pass

**Step 10: Commit**

```bash
git add -A
git commit -m "refactor: remove coverage_score from persistence and services

Remove coverage_score from session_repo, scoring_persistence_stage,
session_service, pipeline context, simulation/synthetic services.
Remove _populate_concept_elements() and get_coverage_stats() methods.
Remove target_coverage config parameter. Update all tests.

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 5: Clean API Schemas and Config

### Task 6: Remove coverage from API schemas, config, and concept route

**Files:**
- Modify: `src/api/schemas.py`
- Modify: `src/api/routes/concepts.py`
- Modify: `src/api/routes/sessions.py`
- Modify: `src/core/config.py`
- Modify: `config/interview_config.yaml`
- Modify: `src/domain/models/turn.py` (focus_type cleanup)

**Step 1: Remove coverage from schemas.py**

- Line 95: Remove `coverage: float = 0.0` from `ScoringSchema`
- Line 140: Remove `"coverage": 0.25` from example JSON
- Line 174: Remove comment mentioning `coverage_achieved`
- Line 255: Remove `coverage: float = 0.0` from `SessionStatusResponse`
- Line 256: Remove `target_coverage: float` from `SessionStatusResponse`

**Step 2: Remove coverage schema from concepts route**

In `src/api/routes/concepts.py`:
- Lines 33-38: Remove `target_coverage` field from `ConceptCompletion` schema

**Step 3: Remove coverage from sessions route**

In `src/api/routes/sessions.py`:
- Line 130: Remove `coverage_score=0.0` from SessionState construction
- Line 417: Remove `coverage=result.scoring["coverage"]` from ScoringSchema construction

**Step 4: Remove coverage from config**

In `config/interview_config.yaml`:
- Line 20: Remove `target_coverage: 0.80`

In `src/core/config.py`:
- Lines 93-94: Remove `default_target_coverage: float = 0.8` from `Settings`
- Lines 131-132: Remove `target_coverage: float = 0.80` from `SessionConfig`

**Step 5: Remove coverage focus types from turn.py**

In `src/domain/models/turn.py`:
- Lines 55-56: Remove `"coverage_gap"` and `"deepen_coverage"` from `Focus.focus_type` Literal
- Line 68: Remove `element_id` field (described as "Element ID for coverage gaps")

**Step 6: Clean up YAML config comments**

In methodology YAML files:
- `config/methodologies/jobs_to_be_done.yaml`: Remove comments about `graph.coverage_breadth`
- `config/methodologies/means_end_chain.yaml`: Remove comments about coverage signals

**Step 7: Clean up misc references**

- `src/methodologies/techniques/probing.py` line 36: Remove comment about `graph.coverage_breadth`
- `src/services/synthetic_service.py` line 66: Remove docstring mention of `coverage_achieved`

**Step 8: Update test_config.py**

- Remove `default_target_coverage` test (line 17, 45)

**Step 9: Run tests**

Run: `uv run pytest tests/ -x -q --tb=short 2>&1 | tail -30`
Expected: All pass

**Step 10: Commit**

```bash
git add -A
git commit -m "refactor: remove coverage from API schemas, config, and routes

Remove coverage fields from ScoringSchema, SessionStatusResponse.
Remove target_coverage from config and ConceptCompletion schema.
Remove coverage focus types from turn model.
Clean up coverage comments in YAML configs and docstrings.

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 6: Database Migration

### Task 7: Write migration to drop coverage columns and concept_elements table

**Files:**
- Create: `src/persistence/migrations/002_remove_coverage.sql`

**Step 1: Write the migration**

```sql
-- Migration 002: Remove coverage-driven mode infrastructure
-- The system is purely exploratory; coverage tracking is dead code.

-- Drop coverage columns from sessions
ALTER TABLE sessions DROP COLUMN coverage_score;

-- Drop coverage_score from scoring_history
ALTER TABLE scoring_history DROP COLUMN coverage_score;

-- Drop concept_elements table entirely
DROP TABLE IF EXISTS concept_elements;
```

Note: SQLite has limited ALTER TABLE support. If using SQLite, the migration approach may need to recreate tables. Check how `001_initial.sql` is applied.

**Step 2: Verify migration approach**

Check how migrations are run in this project:
- Look at `src/persistence/` for migration runner
- Determine if we can use ALTER TABLE DROP COLUMN (SQLite 3.35.0+)

**Step 3: Commit**

```bash
git add src/persistence/migrations/002_remove_coverage.sql
git commit -m "feat: add migration 002 to remove coverage columns and concept_elements table

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Phase 7: Final Verification

### Task 8: Final verification pass

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short 2>&1 | tail -50`
Expected: All pass

**Step 2: Run ruff linter**

Run: `ruff check src/ tests/ --fix`
Expected: Clean (possibly some unused import fixes)

**Step 3: Search for any remaining coverage references**

Run: `grep -rn "coverage" src/ --include="*.py" | grep -v "coverage.py" | grep -v "__pycache__"`
Expected: Only legitimate references (e.g., test coverage, code coverage tools), NOT interview/element/topic coverage

**Step 4: Verify no broken imports**

Run: `uv run python -c "from src.domain.models import interview_state, knowledge_graph, session, turn, concept, pipeline_contracts; print('All imports OK')"`

**Step 5: Close bead and sync**

```bash
bd close qce --reason="Removed all coverage-driven mode infrastructure"
bd sync
git push
```
