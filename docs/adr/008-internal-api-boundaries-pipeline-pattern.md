# ADR-008: Internal API Boundaries + Pipeline Pattern

## Status
Accepted

**Implementation Date**: 2025-01-23
**Implemented By**: Sub-agents (a099603, a40241e, a226329, a88f75f)

## Context

The interview system currently has a layered architecture (API → Services → Repositories → Database), but the boundaries between layers are porous.

### Full Plan Reference

This ADR is derived from the comprehensive implementation plan at:
`/home/mikhailarutyunov/.claude/plans/federated-roaming-abelson.md`

The plan contains detailed analysis including:
- 6 root cause problems with file locations and line numbers
- 4-phase implementation timeline (6-7 weeks)
- Testing strategy with code examples
- Success metrics and verification procedures
- Migration risks and mitigation strategies
- Critical files reference (create/modify lists)

### Current Problems

#### 1. Layer Violations
**Location**: `src/api/routes/sessions.py:277-311`

```python
# ❌ BAD: API route executing raw SQL
async with db.execute("SELECT config FROM sessions WHERE id = ?"):
    config = json.loads(row[0])
```

**Impact**: Database schema changes break API routes directly, bypassing repositories.

#### 2. Direct Database Access in Services
**Location**: `src/services/session_service.py:373, 608`

```python
# ❌ BAD: Service creating inline DB connections
async with aiosqlite.connect(str(self.session_repo.db_path)) as db:
```

**Impact**: Service layer couples to database implementation; can't mock or test easily.

#### 3. Missing Repository Abstraction
**Problem**: No `UtteranceRepository` - utterance SQL scattered across `SessionService` and `SessionRepository`

**Impact**: Duplicate SQL queries, inconsistent error handling, no single source of truth.

#### 4. Implicit Contracts
**Location**: Throughout scoring/strategy services

```python
# ❌ BAD: Generic dict with no validation
focus: Dict[str, Any] = {"type": "depth", "node_id": "123"}

# ✅ GOOD: Typed model
class Focus(BaseModel):
    focus_type: Literal["depth", "breadth", "coverage"]
    node_id: Optional[str] = None
```

**Impact**: No compile-time guarantees; wrong data structures fail at runtime.

#### 5. God Service Anti-Pattern
**Location**: `src/services/session_service.py:120-329`

200-line `process_turn()` method orchestrating 10 steps:
1. Load context
2. Save user utterance
3. Extract concepts
4. Update graph
5. Compute graph state
6. Select strategy
7. Determine continuation
8. Generate question
9. Save system utterance
10. Save scoring data

**Impact**: Hard to test individual steps; changes ripple through entire pipeline.

#### 6. Configuration Scattering

| Config Item | Current Location | Should Be |
|------------|------------------|-----------|
| Scorer weights | `config/scoring.yaml` | ✅ Correct |
| Phase profiles | `config/scoring.yaml` | ✅ Correct |
| Phase thresholds | Hardcoded in `StrategyService.__init__()` | ❌ Move to YAML |
| Max turns | `SessionCreate.config` dict | ❌ Move to YAML |
| Target coverage | Hardcoded `0.8` in multiple places | ❌ Move to YAML |

**Impact**: Configuration spread across 3+ locations; hard to see complete picture.

### Impact Summary

- **Change amplification**: Modifying one component requires touching 4-5 files
- **Fragile testing**: Can't test pipeline stages in isolation
- **Runtime surprises**: Type errors caught at runtime instead of compile-time
- **Difficult onboarding**: New developers struggle to understand turn processing flow

## Decision

**Adopt internal API boundaries + pipeline pattern** for the interview system.

### Why This Approach?

#### ✅ Addresses All Root Causes
- **Repositories** fix layer violations
- **Typed models** prevent implicit contracts
- **Pipeline pattern** breaks up god service
- **Config consolidation** centralizes settings

#### ✅ Proportional to Problem
- Not microservices (overkill)
- Not event-driven (unnecessary complexity)
- Leverages existing layered architecture

#### ✅ Low Risk Migration
- Incremental, backward-compatible changes
- Can keep old code as fallback during transition
- No infrastructure changes required

#### ✅ Clear Benefits
- **Stops breakage**: Layer violations prevented
- **Compile-time safety**: Typed contracts catch errors early
- **Independent testing**: Each pipeline stage testable in isolation
- **Mode isolation**: Supports dual-mode architecture (ADR-005)

### What NOT to Do (Avoid Over-Engineering)

#### ❌ DON'T: Microservices
- No independent scaling needs (extraction and scoring happen in same request)
- Network overhead would add 100-500ms per hop
- 10x deployment complexity (Docker, orchestration, service discovery)
- Distributed state management nightmare

#### ❌ DON'T: Event-Driven Architecture
- Turn processing must be atomic (can't have eventual consistency)
- Debugging harder (non-linear flow)
- Adds complexity without benefit for synchronous pipeline

#### ❌ DON'T: Extract Every Method into a Service
```python
class FocusSelectionService:  # ❌ Unnecessary service explosion
    async def select_focus(self, strategy: str, nodes: List[KGNode]) -> Focus: ...
```
Keep focus selection as method in `StrategyService`

#### ❌ DON'T: Abstract Factories Everywhere
Python isn't Java; dependency injection works fine with constructors. Use FastAPI's `Depends()` for DI.

#### ❌ DON'T: Create Repository for Every Domain Model
Some models (like `GraphState`) are computed on-demand, not persisted. Only repositories for actual database tables (Session, Graph, Utterance, Concept).

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                │
│  (FastAPI routes - HTTP handling only, no business logic)       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  (Business logic with typed contracts via Pydantic/Protocols)   │
├─────────────────────────────────────────────────────────────────┤
│  SessionService │ ExtractionService │ GraphService │ QuestionSvc │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Layer                               │
│  (Turn processing as composable stages)                         │
├─────────────────────────────────────────────────────────────────┤
│  TurnPipeline orchestrates 10 stages sequentially:              │
│  1. ContextLoading     6. StrategySelection                     │
│  2. UtteranceSaving    7. ContinuationDetermination              │
│  3. Extraction         8. QuestionGeneration                    │
│  4. GraphUpdate        9. ResponseSaving                        │
│  5. StateComputation  10. ScoringPersistence                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Repository Layer                              │
│  (All database access - no SQL outside this layer)              │
├─────────────────────────────────────────────────────────────────┤
│  SessionRepository │ GraphRepository │ UtteranceRepository      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                             │
│  (SQLite with aiosqlite)                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Changes

| Area | Before | After |
|------|--------|-------|
| **API Layer** | Business logic + raw SQL | HTTP handling only, delegates to services |
| **Service Contracts** | `Dict[str, Any]` | Pydantic models (`TurnContext`, `TurnResult`, `Focus`) |
| **Service Interfaces** | Concrete classes | Python `Protocol` (interface definitions) |
| **Turn Processing** | 200-line god method | 10 composable pipeline stages |
| **Configuration** | Scattered across 3+ locations | Single `interview_config.yaml` |
| **Database Access** | Scattered inline connections | Centralized in repositories only |

### New Components

**Domain Models** (`src/domain/models/turn.py`):
```python
from pydantic import BaseModel
from typing import List, Optional, Literal

class TurnContext(BaseModel):
    """Complete context for turn processing"""
    session_id: str
    turn_number: int
    user_input: str
    graph_state: GraphState
    recent_nodes: List[KGNode]
    conversation_history: List[Utterance]
    mode: InterviewMode

    class Config:
        arbitrary_types_allowed = True

class Focus(BaseModel):
    """Typed focus target for strategy"""
    focus_type: Literal["depth_exploration", "breadth_exploration", "coverage_gap", "closing", "reflection"]
    node_id: Optional[str] = None
    element_id: Optional[str] = None
    focus_description: str
    confidence: float = 1.0

class TurnResult(BaseModel):
    """Complete result of turn processing"""
    turn_number: int
    extracted: ExtractionResult
    graph_state: GraphState
    selection: SelectionResult
    next_question: str
    should_continue: bool
    latency_ms: int
```

**Service Protocols** (`src/services/protocols.py`):
```python
from typing import Protocol
from src.domain.models.extraction import ExtractionResult
from src.domain.models.knowledge_graph import KGNode, KGEdge

class IExtractionService(Protocol):
    async def extract(self, text: str, context: str, methodology_schema: dict) -> ExtractionResult:
        """Extract concepts and relationships from text"""
        ...

class IGraphService(Protocol):
    async def add_extraction_to_graph(
        self,
        session_id: str,
        extraction: ExtractionResult,
        utterance_id: str
    ) -> tuple[list[KGNode], list[KGEdge]]:
        """Add extraction results to knowledge graph"""
        ...

class IQuestionService(Protocol):
    async def generate_question(
        self,
        focus: Focus,
        recent_utterances: List[Utterance],
        graph_state: GraphState,
        strategy: str
    ) -> str:
        """Generate follow-up question based on strategy and focus"""
        ...
```

**Pipeline Stages** (`src/services/turn_pipeline/`):
```python
class TurnStage(ABC):
    """Base class for turn processing stages"""

    @abstractmethod
    async def process(self, context: TurnContext) -> TurnContext:
        """Process this stage, update context, return modified context"""
        pass

    @property
    def stage_name(self) -> str:
        """Human-readable stage name for logging"""
        return self.__class__.__name__
```

**New Repository** (`src/persistence/repositories/utterance_repo.py`):
```python
class UtteranceRepository:
    async def save(self, utterance: Utterance) -> Utterance:
        """Save utterance to database"""

    async def get_recent(self, session_id: str, limit: int = 10) -> List[Utterance]:
        """Get recent utterances for session"""

    async def get_by_turn(self, session_id: str, turn_number: int) -> List[Utterance]:
        """Get all utterances (user + system) for a specific turn"""
```

## Rationale

### Benefits

1. **Stops Breakage**: Layer violations prevented by architectural boundaries
2. **Compile-Time Safety**: Typed contracts catch errors at development time
3. **Independent Testing**: Each pipeline stage testable in isolation
4. **Mode Isolation**: Clean separation supports dual-mode architecture (ADR-005)
5. **Reduced Change Amplification**: Single component changes stay localized
6. **Better Observability**: Clear stage boundaries for logging and debugging
7. **Easier Onboarding**: Pipeline stages are self-documenting

### Costs

1. **Implementation Time**: 6-7 weeks for full 4-phase migration
2. **More Files**: ~15 new files (domain models, protocols, 10 stages)
3. **Indirection**: Additional abstraction layers (mitigated by type safety)
4. **Learning Curve**: Team needs to understand pipeline pattern
5. **Testing Burden**: Need comprehensive test suite for each stage

### Performance Impact

**Current Baseline**:
- Turn processing: 1000-2000ms average
  - LLM extraction: ~800ms
  - LLM question generation: ~600ms
  - Database queries: <10ms total
  - Scoring: <50ms

**Expected Overhead**:

| Phase | Change | Overhead | % of Total |
|-------|--------|----------|------------|
| Phase 1 | Repository abstraction | +5ms | 0.3% |
| Phase 2 | Pydantic validation | +1ms | 0.1% |
| Phase 3 | Pipeline orchestration | +10ms | 0.5% |
| Phase 4 | Config loading (cached) | <1ms | 0.0% |
| **Total** | | **<20ms** | **1-2%** |

**Verdict**: Negligible overhead compared to LLM calls (1400ms). Trade-off is acceptable for maintainability gains.

### Why Not Alternatives?

| Alternative | Rejected Because |
|-------------|------------------|
| **Microservices** | Overkill for this scale; no independent scaling needs; 10x deployment complexity; network overhead 100-500ms per hop |
| **Event-Driven Architecture** | Turn processing must be atomic; eventual consistency inappropriate for synchronous pipeline; harder to debug |
| **Service Explosion** | Extracting every method into a service adds unnecessary indirection; keep related logic in existing services |
| **Abstract Factories** | Python isn't Java; FastAPI's `Depends()` provides sufficient DI |
| **Status Quo** | Layer violations actively causing breakage; change amplification makes development slow |

## Consequences

### Positive

1. **Architectural Integrity**: Zero layer violations enforced by contract tests
2. **Type Safety**: `mypy --strict` passes with zero errors
3. **Testability**: Each stage has >80% test coverage
4. **Maintainability**: `SessionService.process_turn()` reduced from 200 to <50 lines
5. **Debugging**: Clear stage boundaries make tracing execution straightforward
6. **Configuration**: Single source of truth in `interview_config.yaml`

### Negative

1. **Migration Effort**: 6-7 weeks of focused development
2. **More Abstraction**: Additional layers to understand
3. **Test Creation**: Need to write comprehensive tests as part of migration
4. **Temporary Complexity**: During migration, old and new code coexist

### Neutral

1. **Performance**: <20ms overhead is negligible for this workload
2. **Dependencies**: No new external dependencies required
3. **Backward Compatibility**: Can maintain old API during transition period
4. **Team Alignment**: Matches existing layered architecture concepts

## Implementation

### Four-Phase Migration

#### Phase 1: Fix Layer Violations (1-2 weeks, Priority: HIGH)

**Goals**: Stop immediate breakage

**Tasks**:

1.1 **Create UtteranceRepository**
   - File: `src/persistence/repositories/utterance_repo.py`
   - Methods: `save()`, `get_recent()`, `get_by_turn()`
   - Files to modify:
     - `src/services/session_service.py` - Remove inline utterance SQL (lines 608-627, 642-658)
     - `src/api/dependencies.py` - Add `get_utterance_repository()`

1.2 **Fix API Layer Violations**
   - File: `src/api/routes/sessions.py`
   - Remove raw SQL from:
     - `get_session_status()` (lines 277-322) - Move to `SessionService.get_status()`
     - `get_turn_scoring()` (lines 375-427) - Move to `ScoringService.get_turn_scoring()`

1.3 **Eliminate Inline Database Connections**
   - File: `src/services/session_service.py`
   - Remove patterns:
     - `async with aiosqlite.connect(str(self.session_repo.db_path)) as db:`
     - `db = await get_db_connection()`
   - Replace with: Repository methods exclusively

**Success Criteria**:
- ✅ Zero `aiosqlite.connect()` calls outside `database.py`
- ✅ Zero `get_db_connection()` calls outside repositories
- ✅ All database access goes through repositories

#### Phase 2: Formalize Contracts (2-3 weeks, Priority: HIGH)

**Goals**: Prevent future breakage

**Tasks**:

2.1 **Define Core Domain Objects**
   - File: `src/domain/models/turn.py`
   - Create: `TurnContext`, `Focus`, `TurnResult`

2.2 **Add Service Interfaces (Protocols)**
   - File: `src/services/protocols.py`
   - Create: `IExtractionService`, `IGraphService`, `IQuestionService`

2.3 **Convert Dict Parameters to Typed Models**
   - Files to modify:
     - `src/services/strategy_service.py` - Replace `Dict[str, Any]` focus with `Focus` model
     - `src/services/question_service.py` - Accept `Focus` instead of generic dict
     - `src/services/session_service.py` - Use `TurnContext` and `TurnResult`

**Success Criteria**:
- ✅ `mypy --strict` passes with zero type errors
- ✅ No `Dict[str, Any]` in service interfaces
- ✅ IDE autocomplete works for all service methods

#### Phase 3: Pipeline Refactoring (2-3 weeks, Priority: MEDIUM)

**Goals**: Improve maintainability

**Tasks**:

3.1 **Extract Turn Stages**
   - Directory: `src/services/turn_pipeline/`
   - Create structure:
     ```
     src/services/turn_pipeline/
     ├── __init__.py
     ├── base.py              # TurnStage base class
     ├── pipeline.py          # TurnPipeline orchestrator
     └── stages/
         ├── __init__.py
         ├── context_loading_stage.py      # Step 1
         ├── utterance_saving_stage.py     # Step 2
         ├── extraction_stage.py           # Step 3
         ├── graph_update_stage.py         # Step 4
         ├── state_computation_stage.py    # Step 5
         ├── strategy_selection_stage.py   # Step 6
         ├── continuation_stage.py         # Step 7
         ├── question_generation_stage.py  # Step 8
         ├── response_saving_stage.py      # Step 9
         └── scoring_persistence_stage.py  # Step 10
     ```

3.2 **Create TurnPipeline Orchestrator**
   - File: `src/services/turn_pipeline/pipeline.py`
   - Implements sequential stage execution with error handling and timing

3.3 **Simplify SessionService**
   - File: `src/services/session_service.py`
   - Replace 200-line `process_turn()` (lines 120-329) with pipeline delegation

**Success Criteria**:
- ✅ `SessionService.process_turn()` < 50 lines
- ✅ Each stage has >80% test coverage
- ✅ Can skip/reorder stages for testing

#### Phase 4: Configuration Consolidation (1 week, Priority: MEDIUM)

**Goals**: Single source of truth

**Tasks**:

4.1 **Centralize Configuration**
   - File: `config/interview_config.yaml`
   - Contents:
     - Session settings (max_turns, target_coverage, min_turns)
     - Phase thresholds (exploratory, focused, closing)
     - Strategy applicability by phase

4.2 **Load Configuration in Services**
   - File: `src/services/strategy_service.py`
   - Remove hardcoded thresholds
   - Load from `settings.interview_config`

**Success Criteria**:
- ✅ Single `interview_config.yaml` with all tunable parameters
- ✅ Zero hardcoded thresholds in service constructors
- ✅ Config changes don't require code changes

### Critical Files Reference

**Files to Create**:
- `src/persistence/repositories/utterance_repo.py` - Utterance data access
- `src/domain/models/turn.py` - Turn contracts (TurnContext, Focus, TurnResult)
- `src/services/protocols.py` - Service interfaces
- `src/services/turn_pipeline/` - Pipeline implementation (10 stage files)
- `config/interview_config.yaml` - Centralized configuration

**Files to Modify**:
- `src/api/routes/sessions.py` - Remove raw SQL (lines 277-322, 375-427)
- `src/services/session_service.py` - Simplify process_turn (lines 120-329)
- `src/services/strategy_service.py` - Use typed Focus, load config from YAML
- `src/services/question_service.py` - Accept typed Focus
- `src/api/dependencies.py` - Add utterance_repo dependency

### Migration Strategy

**Low-Risk Incremental Approach**:
1. Implement changes alongside existing code (not deletion)
2. Add feature flags to toggle between old/new implementation
3. Comprehensive test suite before refactoring
4. Keep old `process_turn()` as `process_turn_legacy()` during transition
5. One phase at a time with full testing between phases

### Testing Strategy

**Unit Tests** (per stage):
```python
# tests/unit/turn_pipeline/test_extraction_stage.py
async def test_extraction_stage_processes_user_input():
    # Arrange
    mock_extraction_service = Mock(spec=IExtractionService)
    mock_extraction_service.extract.return_value = ExtractionResult(...)

    stage = ExtractionStage(extraction_service=mock_extraction_service)
    context = TurnContext(user_input="I love coffee", ...)

    # Act
    result = await stage.process(context)

    # Assert
    assert result.extraction is not None
    assert result.extraction.concepts[0].label == "coffee"
```

**Integration Tests** (full pipeline):
```python
# tests/integration/test_turn_pipeline.py
async def test_complete_turn_pipeline():
    # Arrange
    pipeline = create_turn_pipeline()  # Real services, test DB
    context = TurnContext(
        session_id="test-session",
        user_input="I drink coffee every morning"
    )

    # Act
    result = await pipeline.execute(context)

    # Assert
    assert result.next_question is not None
    assert result.should_continue is True
    assert result.extracted.concepts  # Concepts extracted
    assert result.graph_state.node_count > 0  # Graph updated
```

**Contract Tests** (layer boundaries):
```python
# tests/architecture/test_layer_boundaries.py
def test_api_routes_dont_import_persistence():
    """Enforce: API layer can't import from persistence layer"""
    from src.api.routes import sessions

    # Check module doesn't import aiosqlite
    assert "aiosqlite" not in dir(sessions)

    # Check source code doesn't contain DB imports
    source = inspect.getsource(sessions)
    assert "from src.persistence.database" not in source
```

### Success Metrics

**Objective Metrics** (Must Pass):

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Layer violations | ~5 instances | 0 | `grep -r "aiosqlite.connect" src/api/ src/services/` |
| Type safety | ~20 `Any` types | 0 | `mypy --strict src/` |
| Test coverage | ~60% | >80% | `pytest --cov=src.services.turn_pipeline` |
| Change amplification | 4-5 files | ≤2 files | Manual: Change scorer weight, count files touched |
| God service | 200 lines | <50 lines | Line count of `SessionService.process_turn()` |

**Subjective Metrics** (Validate with Team):

| Metric | How to Assess |
|--------|---------------|
| Developer experience | Survey: "Can you change X without worrying about breaking Y?" |
| Onboarding time | Time for new developer to understand turn pipeline |
| Debugging ease | Can you trace turn execution with clear stage boundaries? |
| Confidence in changes | Do you run full test suite before every commit? |

### Migration Risks & Mitigation

**Risk 1: Breaking Existing Functionality**
- **Likelihood**: Medium
- **Impact**: High (production system)
- **Mitigation**:
  - ✅ Comprehensive test suite before refactoring
  - ✅ Keep old `process_turn()` as `process_turn_legacy()` during transition
  - ✅ Feature flag to toggle between old/new pipeline
  - ✅ Incremental rollout (Phase 1 → test → Phase 2 → test → etc.)

**Risk 2: Performance Regression**
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**:
  - ✅ Benchmark turn latency before/after each phase
  - ✅ Set performance budget: <20ms overhead
  - ✅ Profile pipeline stages to identify bottlenecks

**Risk 3: Scope Creep (Over-Engineering)**
- **Likelihood**: Medium
- **Impact**: Medium (wasted effort)
- **Mitigation**:
  - ✅ Stick to 4-phase plan - no additional "nice to have" features
  - ✅ Review against "What NOT to Do" section before adding abstractions
  - ✅ Stop at Phase 3 if benefits plateau

**Risk 4: Configuration Migration Errors**
- **Likelihood**: Low
- **Impact**: Low (config validation catches errors)
- **Mitigation**:
  - ✅ Pydantic validation on config loading
  - ✅ Config schema tests
  - ✅ Default values for all settings

### Verification Plan

After each phase, verify the system still works:

**1. Start Backend**
```bash
cd interview-system-v2
uvicorn src.main:app --reload
```

**2. Start UI**
```bash
streamlit run ui/streamlit_app.py
```

**3. Run Integration Test**
```bash
# Create session
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "methodology": "mec",
    "concept_id": "coffee",
    "concept_name": "Coffee",
    "max_turns": 10
  }'

# Process turn
curl -X POST http://localhost:8000/sessions/{session_id}/turns \
  -H "Content-Type: application/json" \
  -d '{"text": "I drink coffee every morning"}'

# Verify response
# - extracted.concepts should contain coffee-related concepts
# - next_question should be generated
# - should_continue should be true
```

**4. Run Full Test Suite**
```bash
pytest tests/ -v --cov=src --cov-report=html
```

**5. Check Type Safety**
```bash
mypy --strict src/
```

## Related Decisions

- **ADR-001**: Dual sync/async API - Unaffected (API layer changes are internal)
- **ADR-002**: Streamlit framework choice - Unaffected (UI separate from backend)
- **ADR-005**: Dual-mode interview architecture - **Supported** (clean mode isolation via typed contracts)
- **ADR-006**: Enhanced scoring architecture - Unaffected (scoring service, pipeline stage)
- **ADR-007**: YAML-based methodology schema - **Complementary** (extends YAML consolidation approach)

## References

- **Full Implementation Plan**: `/home/mikhailarutyunov/.claude/plans/federated-roaming-abelson.md`
  - Complete 4-phase breakdown with detailed code examples
  - Testing strategy with unit, integration, and contract test examples
  - Success metrics (objective and subjective)
  - Migration risks and mitigation strategies
  - Verification plan for end-to-end testing
  - Critical files reference (files to create and modify)

- Repository pattern: Martin Fowler's "Patterns of Enterprise Application Architecture"
- Pipeline pattern: "Enterprise Integration Patterns" (Hohpe & Woolf)
- Python Protocols: PEP 544 -- Protocols: Structural subtyping (static duck typing)
