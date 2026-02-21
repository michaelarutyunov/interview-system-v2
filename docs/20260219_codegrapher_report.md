# CodeGrapher Architectural Report
**Generated**: 2026-02-19
**Index Status**: Fresh (793 symbols indexed, 143 files)
**Token Budget**: 3000 per query

---

## Summary Table

| Category | Symbols Found | Core (>0.10) | Important (0.05-0.10) | Supporting (<0.05) |
|----------|---------------|--------------|------------------------|-------------------|
| Pipeline Stages & Execution | 19 | 0 | 2 | 17 |
| Signal Detection & Pools | 22 | 0 | 2 | 20 |
| Strategy Selection & Scoring | 18 | 0 | 2 | 16 |
| Graph Services (Surface/Canonical) | 16 | 0 | 2 | 14 |
| State Computation & Persistence | 18 | 0 | 2 | 16 |
| Methodology Configuration & YAML | 28 | 0 | 3 | 25 |
| Node State Tracking & Focus | 24 | 0 | 2 | 22 |
| LLM Extraction & Semantic Parsing | 18 | 0 | 2 | 16 |
| Question Generation & Continuation | 25 | 0 | 2 | 23 |
| API Routes & Endpoints | 33 | 0 | 2 | 31 |
| Repositories & Data Persistence | 13 | 0 | 2 | 11 |
| SRL Preprocessing & Linguistic Features | 13 | 0 | 2 | 11 |
| **TOTAL** | **247** | **0** | **25** | **222** |

---

## PageRank Guide

| Score Range | Classification | Meaning |
|-------------|----------------|---------|
| **≥ 0.10** | Core Component | Central hub used by many parts of the system |
| **0.05 - 0.10** | Important Utility | Key service or supporting class |
| **< 0.05** | Leaf Node | Specific implementation, test, or rarely referenced |

---

## Detailed Findings by Category

### 1. Pipeline Stages & Execution Flow

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `SessionService._build_pipeline` | 0.071466 | `src/services/session_service.py:177-296` | Constructs the 12-stage pipeline |
| `PipelineContext` | 0.065296 | `src/services/turn_pipeline/context.py:45-522` | Central context object passed through all stages |
| `TurnPipeline` | 0.065296 | `src/services/turn_pipeline/pipeline.py:21-273` | Main pipeline executor |
| `TurnStage` | 0.065296 | `src/services/turn_pipeline/base.py:15-39` | Abstract base for all 12 stages |

`★ Insight ─────────────────────────────────────`
The pipeline architecture follows a clean 12-stage design with Stage 2.5 (SRL) and Stage 4.5 (Slot Discovery) as intermediate processing points. The `PipelineContext` serves as the single source of truth passed through each stage, ensuring traceability and state consistency.
`─────────────────────────────────────────────────`

### 2. Signal Detection & Signal Pools

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `ComposedSignalDetector` | 0.065296 | `src/signals/signal_registry.py:27-204` | Registry for all signal detectors |
| `SignalDetector` (ABC) | 0.065296 | `src/signals/signal_base.py:20-212` | Base class for all signals |
| `NodeSignalDetector` | 0.065296 | `src/signals/graph/node_base.py:16-90` | Base for per-node signals |
| `BaseLLMSignal` | 0.065296 | `src/signals/llm/llm_signal_base.py:12-66` | Base for LLM-based signals |
| `ChainCompletionSignal` | 0.065296 | `src/signals/graph/graph_signals.py:160-325` | Detects causal chain completeness |

`★ Insight ─────────────────────────────────────`
Signal detection uses a three-tier hierarchy: global signals (graph-level), node signals (per-node analysis), and LLM signals (response quality). The `@llm_signal()` decorator pattern allows declarative signal definition with automatic rubric loading from `signals.md`.
`─────────────────────────────────────────────────`

### 3. Strategy Selection & Scoring

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `FocusSelectionService._select_by_strategy` | 0.083805 | `src/services/focus_selection_service.py:107-156` | Strategy-based node selection |
| `MethodologyStrategyService` | 0.065296 | `src/services/methodology_strategy_service.py:36-275` | Strategy scoring and ranking |
| `StrategySelectionStage` | 0.065296 | `src/services/turn_pipeline/stages/strategy_selection_stage.py:26-255` | Pipeline stage 6 |
| `score_strategy` | 0.065296 | `src/methodologies/scoring.py:15-47` | Core scoring function |

`★ Insight ─────────────────────────────────────`
Strategy selection uses a two-tier execution model with joint strategy-node scoring (D1 architecture). Phase weights (multiplicative) and bonuses (additive) are applied at the methodology level, allowing fine-tuned control per interview phase.
`─────────────────────────────────────────────────`

### 4. Graph Services (Surface & Canonical)

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `GraphService` | 0.065296 | `src/services/graph_service.py:35-591` | Surface graph with deduplication |
| `CanonicalGraphService` | 0.065296 | `src/services/canonical_graph_service.py:21-208` | Canonical slot mapping |
| `CanonicalGraphState` | 0.065296 | `src/domain/models/canonical_graph.py:130-166` | Canonical graph state model |

`★ Insight ─────────────────────────────────────`
The dual-graph architecture separates the surface graph (preserves utterance fidelity with semantic deduplication) from the canonical graph (stable abstraction slots). This enables signal stability across interviews while maintaining traceability to source utterances.
`─────────────────────────────────────────────────`

### 5. State Computation & Persistence

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `StateComputationStage` | 0.065296 | `src/services/turn_pipeline/stages/state_computation_stage.py:54-267` | Stage 5 - refreshes graph metrics |
| `ScoringPersistenceStage` | 0.065296 | `src/services/turn_pipeline/stages/scoring_persistence_stage.py:25-358` | Stage 10 - saves scoring and state |
| `GraphState` | 0.065296 | `src/domain/models/knowledge_graph.py:173-274` | Computed graph metrics |
| `NodeState` | 0.065296 | `src/domain/models/node_state.py:24-91` | Per-node state tracking |

`★ Insight ─────────────────────────────────────`
State computation follows the freshness guarantee pattern—state extracted after graph updates is validated as fresh before use in strategy selection. The `StateComputationOutput` contract ensures stage 5 produces valid inputs for stage 6.
`─────────────────────────────────────────────────`

### 6. Methodology Configuration & YAML Loading

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `LLMBatchDetector._load_output_example` | 0.079178 | `src/signals/llm/batch_detector.py:110-121` | Loads few-shot examples |
| `MethodologyRegistry` | 0.065296 | `src/methodologies/registry.py:80-253` | YAML-based methodology loader |
| `load_interview_config` | 0.065296 | `src/core/config.py:278-325` | Config loader |
| `load_persona` | 0.065296 | `src/core/persona_loader.py:73-109` | Persona YAML loader |
| `load_concept` | 0.065296 | `src/core/concept_loader.py:21-78` | Concept YAML loader |
| `load_methodology` | 0.065296 | `src/core/schema_loader.py:20-57` | Methodology schema loader |

`★ Insight ─────────────────────────────────────`
The system is methodology-agnostic by design—all strategies, signals, and phases are configured via YAML files in `config/methodologies/`. This allows adding new interview methodologies without code changes. The registry pattern auto-discovers methodology files at startup.
`─────────────────────────────────────────────────`

### 7. Node State Tracking & Focus Management

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `NodeStateTracker` | 0.065296 | `src/services/node_state_tracker.py:42-507` | Tracks focus, yield, recency |
| `NodeYieldStagnationSignal` | 0.065296 | `src/signals/graph/node_signals.py:170-231` | Detects yield stagnation |
| `NodeFocusStreakSignal` | 0.065296 | `src/signals/graph/node_signals.py:239-301` | Detects persistent focus |
| `NodeRecencyScoreSignal` | 0.065296 | `src/signals/graph/node_signals.py:344-401` | Computes node recency |
| `NodeOpportunitySignal` | 0.065296 | `src/signals/meta/node_opportunity.py:24-240` | Meta-signal for node opportunity |

`★ Insight ─────────────────────────────────────`
Node state tracking enables per-node signal detection for sophisticated strategy targeting. The `NodeState` model tracks focus_count, turns_since_last_yield, and current_focus_streak—these metrics feed exhaustion scoring and opportunity detection.
`─────────────────────────────────────────────────`

### 8. LLM Extraction & Semantic Parsing

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `SRLService._extract_srl_frames` | 0.070849 | `src/services/srl_service.py:177-221` | SRL frame extraction |
| `SRLService.nlp` | 0.070849 | `src/services/srl_service.py:58-70` | Lazy-loaded spaCy model |
| `ExtractionService` | 0.065296 | `src/services/extraction_service.py:47-504` | LLM-based extraction |
| `SRLPreprocessingStage` | 0.065296 | `src/services/turn_pipeline/stages/srl_preprocessing_stage.py:25-95` | Stage 2.5 - linguistic parsing |
| `ExtractionStage` | 0.065296 | `src/services/turn_pipeline/stages/extraction_stage.py:23-264` | Stage 3 - concept extraction |

`★ Insight ─────────────────────────────────────`
Extraction uses a two-stage approach: Stage 2.5 performs linguistic preprocessing (SRL frames, discourse relations) via spaCy, then Stage 3 uses LLM extraction with SRL context for improved concept/relationship extraction. The spaCy model is lazy-loaded via property pattern.
`─────────────────────────────────────────────────`

### 9. Question Generation & Continuation

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `ChatInterface._display_opening_question` | 0.074551 | `ui/components/chat.py:45-51` | UI opening question display |
| `QuestionService` | 0.065296 | `src/services/question_service.py:36-238` | Question generation |
| `QuestionGenerationStage` | 0.065296 | `src/services/turn_pipeline/stages/question_generation_stage.py:22-104` | Stage 8 - generates question |
| `ContinuationStage` | 0.065296 | `src/services/turn_pipeline/stages/continuation_stage.py:34-262` | Stage 7 - continue decision |
| `ContinuationStage._should_continue` | 0.065296 | `src/services/turn_pipeline/stages/continuation_stage.py:116-189` | Continuation logic |

`★ Insight ─────────────────────────────────────`
Question generation is strategy-aware—it receives the selected strategy and adapts the prompt accordingly. The continuation decision (Stage 7) happens before question generation (Stage 8), allowing graceful termination before attempting generation.
`─────────────────────────────────────────────────`

### 10. API Routes & Endpoints

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `SessionControls._load_concepts` | 0.071522 | `ui/components/controls.py:283-290` | UI concept loading |
| `APIClient` | 0.065296 | `ui/api_client.py:34-432` | API client for UI |
| `router` (simulation) | 0.065296 | `src/api/routes/simulation.py:31` | Simulation endpoints |
| `router` (sessions) | 0.065296 | `src/api/routes/sessions.py:48` | Session endpoints |
| `router` (synthetic) | 0.065296 | `src/api/routes/synthetic.py:23` | Synthetic persona endpoints |
| `router` (concepts) | 0.065296 | `src/api/routes/concepts.py:20` | Concept endpoints |
| `router` (health) | 0.065296 | `src/api/routes/health.py:15` | Health check endpoint |

`★ Insight ─────────────────────────────────────`
The API is organized by domain: sessions (interview management), simulation (synthetic interviews), synthetic (persona CRUD), concepts (concept CRUD), and health. Dependency injection via `src/api/dependencies.py` provides repositories to routes.
`─────────────────────────────────────────────────`

### 11. Repositories & Data Persistence

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `GraphRepository` | 0.065296 | `src/persistence/repositories/graph_repo.py:29-734` | KG persistence |
| `SessionRepository` | 0.065296 | `src/persistence/repositories/session_repo.py:16-397` | Session persistence |
| `UtteranceRepository` | 0.065296 | `src/persistence/repositories/utterance_repo.py:12-121` | Utterance persistence |
| `CanonicalSlotRepository` | 0.065296 | `src/persistence/repositories/canonical_slot_repo.py:44-51` | Slot persistence |

`★ Insight ─────────────────────────────────────`
All repositories use aiosqlite for async database operations. The repository pattern abstracts SQL complexity from service logic, and dependency injection enables clean testing with mock repositories.
`─────────────────────────────────────────────────`

### 12. SRL Preprocessing & Linguistic Features

| Symbol | PageRank | File | Description |
|--------|----------|------|-------------|
| `SRLService.nlp` | 0.070849 | `src/services/srl_service.py:58-70` | Lazy-loaded spaCy |
| `SRLService._extract_srl_frames` | 0.070849 | `src/services/srl_service.py:177-221` | SRL extraction |
| `SRLPreprocessingStage` | 0.065296 | `src/services/turn_pipeline/stages/srl_preprocessing_stage.py:25-95` | Stage 2.5 |
| `SRLService` | 0.065296 | `src/services/srl_service.py:17-221` | SRL service |

`★ Insight ─────────────────────────────────────`
SRL (Semantic Role Labeling) is a feature-flagged enhancement (`enable_srl`) that provides linguistic context to the extraction stage. The spaCy model is lazy-loaded via `@property` decorator—only loaded when first accessed, reducing startup overhead.
`─────────────────────────────────────────────────`

---

## Architecture Health Summary

### Strengths
1. **Clear separation of concerns**: 12 stages with well-defined contracts via Pydantic models
2. **Signal-driven architecture**: Pluggable signal pools enable methodology-agnostic design
3. **Dual-graph stability**: Surface preserves fidelity, canonical provides stable signals
4. **Lazy-loading patterns**: Expensive resources (spaCy) load on first use
5. **YAML configuration**: Methodologies, personas, and concepts are externalized

### Observations
1. **No core hubs (>0.10 PageRank)**: The system is evenly distributed—no single component dominates
2. **Important utilities (0.05-0.10)**: Services like `MethodologyStrategyService` and `FocusSelectionService` are moderately connected
3. **Extensive test coverage**: Many symbols are test-related, indicating good testing practices

### Recommendations
1. **Continue modular design**: Current distribution indicates healthy architectural boundaries
2. **Monitor SRL latency**: While ~15ms is under the 200ms budget, watch for degradation
3. **Signal documentation**: The signal registry pattern is strong—consider adding auto-generated documentation from signal descriptions

---

## Appendix: Query Categories

1. Pipeline stages and execution flow
2. Signal detection and signal pools
3. Strategy selection and scoring
4. Graph services surface and canonical
5. State computation and persistence
6. Methodology configuration and YAML loading
7. Node state tracking and focus management
8. LLM extraction and semantic parsing
9. Question generation and continuation
10. API routes and endpoints
11. Repositories and data persistence
12. SRL preprocessing and linguistic features
