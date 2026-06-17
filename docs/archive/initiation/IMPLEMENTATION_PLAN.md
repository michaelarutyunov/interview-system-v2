# Adaptive Interview System v2: Implementation Plan

**Status:** Draft  
**Date:** January 2026  
**Companion Documents:** PRD v2.0, Engineering Guide v1.0

---

## Executive Summary

This plan maps the existing v1 codebase to the v2 architecture, identifying what can be reused, what needs adaptation, and what must be rewritten. The goal is to preserve the substantial domain logic while eliminating the architectural issues that caused v1 to fail.

### v1 → v2 Transformation Summary

| Category | Files | Decision | Effort |
|----------|-------|----------|--------|
| **Reuse as-is** | 8 | Copy with minor imports | ~2 hours |
| **Adapt** | 12 | Refactor for new architecture | ~20 hours |
| **Rewrite** | 6 | New implementation required | ~30 hours |
| **Remove** | 4 | Not needed in v2 | 0 |

**Total estimated effort:** ~52 hours (6-7 working days)

---

## 1. Root Cause Analysis: Why v1 Failed

### The Fatal Error
```
RuntimeError: Task <Task pending name='Task-5'...> got Future <Future pending> 
attached to a different loop

asyncpg.exceptions._base.InterfaceError: cannot perform operation: 
another operation is in progress
```

### Root Cause Chain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Gradio UI (sync callbacks)                                                  │
│      ↓                                                                       │
│  GradioUIAdapter.process_turn() [SYNC method]                               │
│      ↓                                                                       │
│  asyncio.run() OR ThreadPoolExecutor + new_event_loop()                     │
│      ↓                                                                       │
│  SessionOrchestrator.process_turn() [ASYNC]                                 │
│      ↓                                                                       │
│  asyncpg connection (bound to ORIGINAL loop at pool creation time)          │
│      ↓                                                                       │
│  💥 CRASH: Connection belongs to different event loop                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why the Adapter Pattern Failed

The `adapters.py` attempted multiple workarounds:
1. **ThreadPoolExecutor** - Creates new thread with new event loop, but asyncpg pool is bound to original loop
2. **asyncio.run()** - Creates entirely new loop, same problem
3. **Async callbacks in Gradio** - Gradio 6.0 has its own event loop that conflicts

**The fundamental issue:** asyncpg connection pools are bound to the event loop at creation time and cannot be used from a different loop.

### v2 Solution: Single Event Loop Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FastAPI (uvicorn)                                                           │
│      ↓                                                                       │
│  Single async event loop (managed by uvicorn)                               │
│      ↓                                                                       │
│  All async operations run in same loop                                       │
│      ↓                                                                       │
│  aiosqlite (no pool binding issues - connection per request)                │
│      ↓                                                                       │
│  ✅ Works correctly                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. File-by-File Migration Analysis

### 2.1 Models Layer (`src/models/`)

| File | v1 Lines | Decision | Rationale | v2 Changes |
|------|----------|----------|-----------|------------|
| `session.py` | 180 | **ADAPT** | Good models, remove Redis dependencies | Remove `SessionState` Redis fields, simplify |
| `knowledge_graph.py` | 150 | **ADAPT** | Good structure, simplify temporal | Remove bi-temporal fields (`valid_from`, `valid_to`, `superseded_at`), keep `recorded_at` |
| `strategy.py` | 200 | **ADAPT** | Core domain logic, keep | Remove unused strategy types, keep 3-4 |
| `extraction.py` | 100 | **REUSE** | Pure data models | Minor import fixes |
| `concept.py` | 80 | **REUSE** | Pure data models | As-is |
| `computed_state.py` | 120 | **ADAPT** | Simplify state structure | Remove momentum complexity |
| `llm_responses.py` | 60 | **REUSE** | Pure data models | As-is |

### 2.2 Modules Layer (`src/modules/`)

| File | v1 Lines | Decision | Rationale | v2 Changes |
|------|----------|----------|-----------|------------|
| `session_orchestrator.py` | 650 | **REWRITE** | Event loop issues, PostgreSQL/Redis coupling | New FastAPI-native implementation with SQLite |
| `arbitration_engine.py` | 150 | **ADAPT** | Clean logic, reduce scorers | Keep multiplicative scoring, reduce to 5 scorers |
| `strategy_selector.py` | 200 | **ADAPT** | Good logic, simplify | Remove unused strategies |
| `question_generator.py` | 180 | **ADAPT** | Good prompts, update LLM client | Switch to new LLM client abstraction |
| `language_understanding.py` | 250 | **ADAPT** | Good extraction logic | Update LLM calls, simplify coreference |
| `knowledge_graph_manager.py` | 450 | **REWRITE** | asyncpg + bi-temporal complexity | New SQLite + single-temporal version |
| `conversational_graph_manager.py` | 200 | **ADAPT** | Redis dependency | Convert to in-memory + SQLite backup |
| `input_processor.py` | 100 | **REUSE** | Pure text processing | Minor cleanup |
| `state_computer.py` | 300 | **ADAPT** | Reduce complexity | Simplify to 3 core scores |
| `response_assembler.py` | 150 | **ADAPT** | Good structure | Update LLM client calls |
| `concept_parser.py` | 120 | **REUSE** | YAML parsing logic | As-is |
| `opening_question_generator.py` | 80 | **REUSE** | Simple LLM call | Update client |

### 2.3 Scorers (`src/modules/scorers/`)

| File | v1 Lines | Decision | Rationale | v2 Status |
|------|----------|----------|-----------|-----------|
| `base.py` | 100 | **REUSE** | Clean abstraction | As-is |
| `element_coverage_scorer.py` | 80 | **REUSE** | Core scorer | Keep |
| `saturation_scorer.py` | 90 | **REUSE** | Core scorer | Keep |
| `depth_breadth_phase_scorer.py` | 100 | **ADAPT** | Combine into depth scorer | Merge with novelty |
| `novelty_scorer.py` | 70 | **REUSE** | Core scorer | Keep |
| `response_richness_scorer.py` | 80 | **ADAPT** | Simplify | Keep, simplify |
| `connectivity_scorer.py` | 70 | **REMOVE** | Redundant with graph stats | Remove |
| `confidence_gap_scorer.py` | 60 | **REMOVE** | Rarely triggered | Remove |
| `topic_relevance_scorer.py` | 70 | **REMOVE** | LLM-based, slow | Remove |
| `schema_conformance_scorer.py` | 80 | **REMOVE** | Rarely triggered | Remove |
| `cross_link_scorer.py` | 70 | **REMOVE** | Complex, low value | Remove |
| `ambiguity_scorer.py` | 60 | **REMOVE** | Rarely triggered | Remove |
| `contradiction_scorer.py` | 70 | **REMOVE** | Edge case | Remove |
| `strategy_diversity_scorer.py` | 60 | **REMOVE** | Adds complexity | Remove |
| `completion_readiness_scorer.py` | 70 | **ADAPT** | Merge into saturation | Merge |

**v2 Scorer Set (5 total):**
1. `coverage_scorer.py` - Element coverage tracking
2. `depth_scorer.py` - Ladder depth measurement  
3. `saturation_scorer.py` - New information rate (includes completion)
4. `novelty_scorer.py` - Recent question deduplication
5. `richness_scorer.py` - Response quality assessment

### 2.4 Utils Layer (`src/utils/`)

| File | v1 Lines | Decision | Rationale | v2 Changes |
|------|----------|----------|-----------|------------|
| `llm_integration.py` | 300 | **REWRITE** | Provider abstraction overkill | Simple Anthropic client per Engineering Guide |
| `redis_client.py` | 150 | **REMOVE** | No Redis in v2 | Delete |
| `embeddings.py` | 100 | **REMOVE** | Semantic dedup not MVP | Delete (add later if needed) |
| `text_processing.py` | 80 | **REUSE** | Pure functions | As-is |
| `history.py` | 60 | **ADAPT** | Remove Redis dependency | SQLite-based |
| `logging_config.py` | 50 | **REWRITE** | Update to structlog pattern | Per Engineering Guide |

### 2.5 UI Layer (`src/ui/`)

| File | v1 Lines | Decision | Rationale | v2 Changes |
|------|----------|----------|-----------|------------|
| `adapters.py` | 200 | **REMOVE** | Root cause of failure | Delete entirely |
| `gradio_app.py` | 300 | **REWRITE** | Complete redesign | Separate demo UI, API-first |
| `components/*.py` | 400 | **ADAPT** | Good visualizations | Update for new data structures |

### 2.6 Error Handling (`src/error_handling/`)

| File | v1 Lines | Decision | Rationale | v2 Changes |
|------|----------|----------|-----------|------------|
| `recovery_manager.py` | 150 | **ADAPT** | Good patterns | Simplify, remove fallback chains |
| `degradation_manager.py` | 100 | **ADAPT** | Good concept | Simplify levels |

---

## 3. Phased Implementation

### Phase 1: Foundation (Days 1-2)
**Goal:** Bootable FastAPI app with SQLite, health endpoint, basic session CRUD

#### Tasks

| # | Task | Input | Output | Est. |
|---|------|-------|--------|------|
| 1.1 | Project scaffolding | Engineering Guide | Directory structure, pyproject.toml | 1h |
| 1.2 | SQLite schema | PRD Section 7 | migrations/001_initial.sql | 2h |
| 1.3 | Database module | Engineering Guide | persistence/database.py | 2h |
| 1.4 | Settings & logging | Engineering Guide | core/config.py, core/logging.py | 1h |
| 1.5 | FastAPI app shell | PRD API spec | main.py, health endpoint | 1h |
| 1.6 | Session repository | v1 session.py | persistence/repositories/session_repo.py | 2h |
| 1.7 | Session API endpoints | PRD API spec | api/routes/sessions.py | 2h |
| 1.8 | Integration test | - | tests/integration/test_api.py | 1h |

**Phase 1 Deliverable:** `POST /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}` working

---

### Phase 2: Core Pipeline (Days 3-5)
**Goal:** Single turn processing without scoring/strategy (hardcoded "deepen" strategy)

#### Tasks

| # | Task | Input | Output | Est. |
|---|------|-------|--------|------|
| 2.1 | Adapt models | v1 models/*.py | domain/models/*.py | 3h |
| 2.2 | LLM client | Engineering Guide | llm/client.py | 2h |
| 2.3 | Extraction prompts | v1 language_understanding.py | llm/prompts/extraction.py | 2h |
| 2.4 | Extraction service | v1 language_understanding.py | services/extraction_service.py | 3h |
| 2.5 | Graph repository | v1 knowledge_graph_manager.py | persistence/repositories/graph_repo.py | 4h |
| 2.6 | Graph service | v1 knowledge_graph_manager.py | services/graph_service.py | 3h |
| 2.7 | Question prompts | v1 question_generator.py | llm/prompts/question.py | 1h |
| 2.8 | Question service | v1 question_generator.py | services/question_service.py | 2h |
| 2.9 | Session service | v1 session_orchestrator.py | services/session_service.py | 4h |
| 2.10 | Turn endpoint | PRD API spec | POST /sessions/{id}/turns | 2h |
| 2.11 | Pipeline test | - | tests/integration/test_session_flow.py | 2h |

**Phase 2 Deliverable:** Full turn processing with extraction and question generation (hardcoded strategy)

---

### Phase 3: Scoring & Strategy (Days 6-7)
**Goal:** Adaptive strategy selection with 5 scorers

#### Tasks

| # | Task | Input | Output | Est. |
|---|------|-------|--------|------|
| 3.1 | Scorer base | v1 scorers/base.py | services/scoring/base.py | 1h |
| 3.2 | Coverage scorer | v1 element_coverage_scorer.py | services/scoring/coverage.py | 2h |
| 3.3 | Depth scorer | v1 depth_breadth_phase_scorer.py | services/scoring/depth.py | 2h |
| 3.4 | Saturation scorer | v1 saturation_scorer.py | services/scoring/saturation.py | 2h |
| 3.5 | Novelty scorer | v1 novelty_scorer.py | services/scoring/novelty.py | 1h |
| 3.6 | Richness scorer | v1 response_richness_scorer.py | services/scoring/richness.py | 2h |
| 3.7 | Arbitration engine | v1 arbitration_engine.py | services/scoring/arbitration.py | 2h |
| 3.8 | Strategy selector | v1 strategy_selector.py | services/strategy_service.py | 3h |
| 3.9 | Integrate into session | - | Update session_service.py | 2h |
| 3.10 | Scorer unit tests | - | tests/unit/test_scoring.py | 2h |

**Phase 3 Deliverable:** Adaptive strategy selection working end-to-end

---

### Phase 4: Synthetic Respondent (Day 8)
**Goal:** Automated testing capability

#### Tasks

| # | Task | Input | Output | Est. |
|---|------|-------|--------|------|
| 4.1 | Synthetic prompts | PRD Section 6.2 | llm/prompts/synthetic.py | 1h |
| 4.2 | Synthetic service | PRD Section 6.2 | services/synthetic_service.py | 3h |
| 4.3 | Synthetic endpoint | PRD API spec | api/routes/synthetic.py | 1h |
| 4.4 | Test script | - | scripts/run_synthetic_interview.py | 2h |
| 4.5 | Regression tests | - | tests/integration/test_synthetic.py | 2h |

**Phase 4 Deliverable:** Automated interview testing capability

---

### Phase 5: Demo UI (Days 9-10)
**Goal:** Demo interface with diagnostics panel

#### Tasks

| # | Task | Input | Output | Est. |
|---|------|-------|--------|------|
| 5.1 | UI framework decision | - | Streamlit/Gradio/htmx choice | 1h |
| 5.2 | Chat interface | v1 chat_interface.py | ui/components/chat.py | 3h |
| 5.3 | Graph visualizer | v1 graph_visualizer.py | ui/components/graph.py | 4h |
| 5.4 | Metrics panel | v1 diagnostics_panel.py | ui/components/metrics.py | 3h |
| 5.5 | Session controls | v1 session_manager.py | ui/components/controls.py | 2h |
| 5.6 | Main app | v1 gradio_app.py | ui/app.py | 3h |
| 5.7 | UI integration test | - | Manual testing | 2h |

**Phase 5 Deliverable:** Working demo UI for testing and demonstration

---

### Phase 6: Export & Polish (Days 11-12)
**Goal:** Production-ready MVP

#### Tasks

| # | Task | Input | Output | Est. |
|---|------|-------|--------|------|
| 6.1 | Export service | v1 exporters.py | services/export_service.py | 2h |
| 6.2 | Export endpoints | PRD API spec | GET /sessions/{id}/export | 1h |
| 6.3 | Concept endpoints | PRD API spec | api/routes/concepts.py | 2h |
| 6.4 | Error handling | Engineering Guide | Comprehensive error handling | 3h |
| 6.5 | Logging review | Engineering Guide | Consistent logging throughout | 2h |
| 6.6 | Documentation | - | README.md, API docs | 2h |
| 6.7 | End-to-end testing | - | Full system validation | 3h |
| 6.8 | Performance check | PRD constraints | Verify <5s latency | 2h |

**Phase 6 Deliverable:** Production-ready MVP

---

## 4. Code Migration Patterns

### 4.1 asyncpg → aiosqlite

**Before (v1):**
```python
async with self.db_pool.acquire() as conn:
    row = await conn.fetchrow(
        "SELECT * FROM sessions WHERE id = $1",
        session_id
    )
```

**After (v2):**
```python
async with aiosqlite.connect(self.db_path) as db:
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (str(session_id),)
    )
    row = await cursor.fetchone()
```

### 4.2 Redis Session State → SQLite

**Before (v1):**
```python
await self.redis.set_state(session_id, state, ttl=3600)
state = await self.redis.get_state(session_id, SessionState)
```

**After (v2):**
```python
# State computed on-demand from SQLite, no caching
async def get_session_state(self, session_id: str) -> SessionState:
    session = await self.session_repo.get(session_id)
    graph = await self.graph_repo.get_session_graph(session_id)
    return self._compute_state(session, graph)
```

### 4.3 Bi-temporal → Single-temporal

**Before (v1):**
```python
class KnowledgeNode:
    valid_from: datetime
    valid_to: datetime
    recorded_at: datetime
    superseded_at: datetime
    version: int
```

**After (v2):**
```python
class KGNode:
    recorded_at: datetime  # Single timestamp
    superseded_by: Optional[str] = None  # For contradictions (REVISES edge)
```

### 4.4 14 Scorers → 5 Scorers

**v1 Multiplicative Formula:**
```
score = base × novelty × coverage × depth × saturation × richness 
        × connectivity × confidence × relevance × conformance 
        × crosslink × ambiguity × contradiction × diversity × completion
```

**v2 Multiplicative Formula:**
```
score = base × coverage × depth × saturation × novelty × richness
```

Same multiplicative principle, fewer dimensions.

### 4.5 Sync Wrapper Elimination

**Before (v1):**
```python
def process_turn(self, session_id: str, user_input: str) -> TurnResult:
    try:
        loop = asyncio.get_running_loop()
        # Complex ThreadPoolExecutor workaround...
    except RuntimeError:
        return asyncio.run(self.process_turn_async(...))
```

**After (v2):**
```python
# Just async - FastAPI handles the event loop
async def process_turn(self, session_id: str, user_input: str) -> TurnResult:
    # Direct async implementation
    ...
```

---

## 5. Validation Criteria

### Phase Gate Criteria

| Phase | Gate Criteria |
|-------|---------------|
| **1** | Health endpoint returns 200, session CRUD works, SQLite persists |
| **2** | Turn processing completes, extraction returns concepts, question generated |
| **3** | Strategy changes based on graph state, scores logged correctly |
| **4** | Synthetic interview completes 10 turns without error |
| **5** | UI displays chat, graph updates in real-time, metrics show |
| **6** | Export produces valid JSON/Markdown, all tests pass, <5s p95 latency |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Turn latency p95 | <5s | Logged in TurnResult |
| Extraction accuracy | ≥80% | Manual review of 20 turns |
| Coverage achievement | ≥80% | Synthetic tests with known concepts |
| Session completion | ≥90% | No crashes in 50 synthetic interviews |
| Graph coherence | <10% orphans | Automated check |

---

## 6. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM latency spikes | Delay | Timeout handling, graceful degradation |
| SQLite contention | Corruption | Single-writer pattern, WAL mode |
| Extraction quality | Bad graphs | Confidence thresholds, human review |
| Scorer tuning | Bad strategies | Start with equal weights, tune empirically |
| UI framework issues | Delay | API-first design, UI is separate concern |

---

## 7. File Mapping Reference

### Complete v1 → v2 Mapping

```
v1: src/models/session.py          → v2: src/domain/models/session.py (ADAPT)
v1: src/models/knowledge_graph.py  → v2: src/domain/models/knowledge_graph.py (ADAPT)
v1: src/models/strategy.py         → v2: src/domain/models/strategy.py (ADAPT)
v1: src/models/extraction.py       → v2: src/domain/models/extraction.py (REUSE)
v1: src/models/concept.py          → v2: src/domain/models/concept.py (REUSE)
v1: src/models/computed_state.py   → v2: src/domain/models/computed_state.py (ADAPT)

v1: src/modules/session_orchestrator.py → v2: src/services/session_service.py (REWRITE)
v1: src/modules/knowledge_graph_manager.py → v2: src/persistence/repositories/graph_repo.py + src/services/graph_service.py (REWRITE)
v1: src/modules/language_understanding.py → v2: src/services/extraction_service.py (ADAPT)
v1: src/modules/question_generator.py → v2: src/services/question_service.py (ADAPT)
v1: src/modules/strategy_selector.py → v2: src/services/strategy_service.py (ADAPT)
v1: src/modules/arbitration_engine.py → v2: src/services/scoring/arbitration.py (ADAPT)
v1: src/modules/state_computer.py → v2: src/services/scoring_service.py (ADAPT)
v1: src/modules/input_processor.py → v2: src/utils/text.py (REUSE)
v1: src/modules/concept_parser.py → v2: src/services/concept_service.py (REUSE)

v1: src/modules/scorers/base.py → v2: src/services/scoring/base.py (REUSE)
v1: src/modules/scorers/element_coverage_scorer.py → v2: src/services/scoring/coverage.py (REUSE)
v1: src/modules/scorers/saturation_scorer.py → v2: src/services/scoring/saturation.py (REUSE)
v1: src/modules/scorers/depth_breadth_phase_scorer.py → v2: src/services/scoring/depth.py (ADAPT)
v1: src/modules/scorers/novelty_scorer.py → v2: src/services/scoring/novelty.py (REUSE)
v1: src/modules/scorers/response_richness_scorer.py → v2: src/services/scoring/richness.py (ADAPT)
v1: src/modules/scorers/[8 others] → REMOVE

v1: src/utils/llm_integration.py → v2: src/llm/client.py (REWRITE)
v1: src/utils/redis_client.py → REMOVE
v1: src/utils/embeddings.py → REMOVE (future)
v1: src/utils/text_processing.py → v2: src/utils/text.py (REUSE)

v1: src/ui/adapters.py → REMOVE
v1: src/ui/gradio_app.py → v2: src/ui/app.py (REWRITE)
v1: src/ui/components/*.py → v2: src/ui/components/*.py (ADAPT)

v1: src/error_handling/*.py → v2: src/core/exceptions.py (ADAPT)
```

---

## Appendix: Quick Start Commands

```bash
# Phase 1: Foundation
mkdir -p src/{api/routes,core,domain/models,services,persistence/repositories,llm/prompts,utils,ui/components}
touch src/__init__.py src/main.py

# Create initial migration
cat > src/persistence/migrations/001_initial.sql << 'EOF'
-- See Engineering Guide Section 9.1
EOF

# Run tests after each phase
pytest tests/ -v

# Start dev server
uvicorn src.main:app --reload --port 8000
```

---

## Appendix: Decision Log

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Database | PostgreSQL, SQLite | SQLite | Single-user, zero config |
| Async | sync-first, async-native | async-native (FastAPI) | Future coordinator pattern |
| Scorers | Keep 14, reduce | Reduce to 5 | Tuning complexity |
| Temporal | Bi-temporal, single | Single + REVISES | MVP simplicity |
| UI | Gradio, Streamlit, htmx | TBD (Phase 5) | API-first anyway |
| Caching | Redis, in-memory | In-memory | Single-user, SQLite fast enough |
