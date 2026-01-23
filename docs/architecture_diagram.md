# Complete Architecture Diagram (Mermaid)

**Adaptive Interview System v2** - Full Module Dependency Graph

> This diagram shows every Python module in the codebase with arrows indicating data flow and dependencies. Render with [Mermaid Live Editor](https://mermaid.live) or any Mermaid-compatible viewer.

---

## Mermaid Diagram

```mermaid
graph TD
    %% Styles
    classDef api fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef service fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef pipeline fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef repository fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef domain fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef llm fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef scoring fill:#e0f2f1,stroke:#004d40,stroke-width:2px

    %% ============================================================
    %% API LAYER
    %% ============================================================
    subgraph API ["API Layer (FastAPI)"]
        API_ROUTES["api/routes/sessions.py<br/>POST /sessions/{id}/turns"]:::api
        API_SCHEMAS["api/schemas.py<br/>Request/Response Models"]:::api
        API_DEPS["api/dependencies.py<br/>Dependency Injection"]:::api
    end

    %% ============================================================
    %% SERVICE LAYER - Core Services
    %% ============================================================
    subgraph SERVICES ["Service Layer"]
        SESSION_SVC["services/session_service.py<br/>SessionService"]:::service
        EXTRACTION_SVC["services/extraction_service.py<br/>ExtractionService"]:::service
        GRAPH_SVC["services/graph_service.py<br/>GraphService"]:::service
        QUESTION_SVC["services/question_service.py<br/>QuestionService"]:::service
        STRATEGY_SVC["services/strategy_service.py<br/>StrategyService"]:::service
        EXPORT_SVC["services/export_service.py<br/>ExportService"]:::service
    end

    %% ============================================================
    %% PIPELINE LAYER - Turn Processing Pipeline
    %% ============================================================
    subgraph PIPELINE ["Pipeline Layer (ADR-008)"]
        PIPELINE_MAIN["turn_pipeline/pipeline.py<br/>TurnPipeline"]:::pipeline
        PIPELINE_CTX["turn_pipeline/context.py<br/>PipelineContext"]:::pipeline
        PIPELINE_RESULT["turn_pipeline/result.py<br/>TurnResult"]:::pipeline
        PIPELINE_BASE["turn_pipeline/base.py<br/>TurnStage"]:::pipeline
    end

    subgraph STAGES ["Pipeline Stages (10)"]
        STAGE1["stages/context_loading_stage.py<br/>1. Load metadata"]:::pipeline
        STAGE2["stages/utterance_saving_stage.py<br/>2. Save user input"]:::pipeline
        STAGE3["stages/extraction_stage.py<br/>3. Extract concepts"]:::pipeline
        STAGE4["stages/graph_update_stage.py<br/>4. Update graph"]:::pipeline
        STAGE5["stages/state_computation_stage.py<br/>5. Refresh state"]:::pipeline
        STAGE6["stages/strategy_selection_stage.py<br/>6. Select strategy"]:::pipeline
        STAGE7["stages/continuation_stage.py<br/>7. Decide continuation"]:::pipeline
        STAGE8["stages/question_generation_stage.py<br/>8. Generate question"]:::pipeline
        STAGE9["stages/response_saving_stage.py<br/>9. Save response"]:::pipeline
        STAGE10["stages/scoring_persistence_stage.py<br/>10. Save scoring"]:::pipeline
    end

    %% ============================================================
    %% SCORING LAYER - Two-Tier Scoring System
    %% ============================================================
    subgraph SCORING ["Scoring System (ADR-006)"]
        SCORING_ENGINE["scoring/two_tier/engine.py<br/>TwoTierScoringEngine"]:::scoring

        subgraph TIER1 ["Tier 1: Filters"]
            T1_APPLICABILITY["scoring/tier1/applicability.py<br/>ApplicabilityFilter"]:::scoring
            T1_COVERAGE["scoring/tier1/coverage.py<br/>CoverageThresholdFilter"]:::scoring
        end

        subgraph TIER2 ["Tier 2: Scorers"]
            T2_COVERAGE["scoring/tier2/coverage_gap.py<br/>CoverageGapScorer"]:::scoring
            T2_DEPTH["scoring/tier2/depth_breadth_balance.py<br/>DepthBreadthScorer"]:::scoring
            T2_DIVERSITY["scoring/tier2/strategy_diversity.py<br/>StrategyDiversityScorer"]:::scoring
            T2_AMBIGUITY["scoring/tier2/ambiguity.py<br/>AmbiguityScorer"]:::scoring
            T2_BASE["scoring/base.py<br/>ScorerBase"]:::scoring
        end
    end

    %% ============================================================
    %% REPOSITORY LAYER - Data Access
    %% ============================================================
    subgraph REPOS ["Repository Layer"]
        SESSION_REPO["persistence/repositories/session_repo.py<br/>SessionRepository"]:::repository
        GRAPH_REPO["persistence/repositories/graph_repo.py<br/>GraphRepository"]:::repository
        UTTERANCE_REPO["persistence/repositories/utterance_repo.py<br/>UtteranceRepository"]:::repository
    end

    subgraph DB ["Database"]
        SQLITE [("data/interview.db<br/>SQLite Database")]
    end

    %% ============================================================
    %% DOMAIN LAYER - Business Entities
    %% ============================================================
    subgraph DOMAIN ["Domain Models"]
        DOMAIN_TURN["domain/models/turn.py<br/>TurnContext, TurnResult, Focus"]:::domain
        DOMAIN_KG["domain/models/knowledge_graph.py<br/>KGNode, KGEdge, GraphState"]:::domain
        DOMAIN_EXTRACTION["domain/models/extraction.py<br/>ExtractionResult"]:::domain
        DOMAIN_UTTERANCE["domain/models/utterance.py<br/>Utterance"]:::domain
        DOMAIN_INTERVIEW["domain/models/interview_state.py<br/>InterviewMode, Phase"]:::domain
        DOMAIN_METHODS["core/schema_loader.py<br/>MethodologySchema"]:::domain
    end

    %% ============================================================
    %% LLM LAYER - Language Model Integration
    %% ============================================================
    subgraph LLM ["LLM Layer"]
        LLM_CLIENT["llm/client.py<br/>AnthropicClient"]:::llm
        LLM_PROMPTS["llm/prompts/<br/>extraction.py, question.py"]:::llm
    end

    %% ============================================================
    %% CONFIG LAYER
    %% ============================================================
    subgraph CONFIG ["Configuration"]
        CONFIG_MAIN["core/config.py<br/>Settings"]:::domain
        CONFIG_INTERVIEW["config/interview_config.yaml<br/>Interview Config"]:::domain
        CONFIG_SCORING["config/scoring.yaml<br/>Scoring Config"]:::domain
        CONFIG_METHODS["config/methodologies/<br/>*.yaml"]:::domain
    end

    %% ============================================================
    %% DATA FLOW ARROWS
    %% ============================================================

    %% API → SessionService
    API_ROUTES -->|"POST /sessions/{id}/turns<br/>{session_id, user_input}"| SESSION_SVC
    API_SCHEMAS -.->|"Validates"| API_ROUTES
    API_DEPS -.->|"Injects repos & services"| API_ROUTES

    %% SessionService → Pipeline
    SESSION_SVC -->|"Creates<br/>PipelineContext"| PIPELINE_CTX
    SESSION_SVC -->|"Delegates to"| PIPELINE_MAIN
    PIPELINE_MAIN -->|"Returns"| PIPELINE_RESULT

    %% Pipeline → Stages (Sequential Flow)
    PIPELINE_MAIN -->|"1. Execute"| STAGE1
    STAGE1 -->|"2. Execute"| STAGE2
    STAGE2 -->|"3. Execute"| STAGE3
    STAGE3 -->|"4. Execute"| STAGE4
    STAGE4 -->|"5. Execute"| STAGE5
    STAGE5 -->|"6. Execute"| STAGE6
    STAGE6 -->|"7. Execute"| STAGE7
    STAGE7 -->|"8. Execute"| STAGE8
    STAGE8 -->|"9. Execute"| STAGE9
    STAGE9 -->|"10. Execute"| STAGE10

    %% PipelineContext flows through all stages
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE1
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE2
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE3
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE4
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE5
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE6
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE7
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE8
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE9
    PIPELINE_CTX -.->|"Reads/Writes"| STAGE10

    %% Stages → Services
    STAGE1 -->|"Uses"| SESSION_REPO
    STAGE1 -->|"Uses"| GRAPH_REPO
    STAGE1 -->|"Uses"| UTTERANCE_REPO

    STAGE2 -->|"Uses"| UTTERANCE_REPO

    STAGE3 -->|"Uses"| EXTRACTION_SVC

    STAGE4 -->|"Uses"| GRAPH_SVC

    STAGE5 -->|"Uses"| GRAPH_SVC

    STAGE6 -->|"Uses"| STRATEGY_SVC

    STAGE7 -->|"Uses"| QUESTION_SVC

    STAGE8 -->|"Uses"| QUESTION_SVC

    STAGE9 -->|"Uses"| UTTERANCE_REPO

    STAGE10 -->|"Uses"| SESSION_REPO

    %% Services → LLM
    EXTRACTION_SVC -->|"Calls"| LLM_CLIENT
    QUESTION_SVC -->|"Calls"| LLM_CLIENT
    LLM_CLIENT -->|"Uses prompts from"| LLM_PROMPTS

    %% Services → Repositories
    SESSION_SVC -->|"Uses"| SESSION_REPO
    SESSION_SVC -->|"Uses"| GRAPH_REPO
    GRAPH_SVC -->|"Uses"| GRAPH_REPO
    EXPORT_SVC -->|"Uses"| SESSION_REPO
    EXPORT_SVC -->|"Uses"| GRAPH_REPO

    %% StrategyService → Scoring
    STRATEGY_SVC -->|"Uses"| SCORING_ENGINE

    %% Scoring Engine → Tiers
    SCORING_ENGINE -->|"1. Filter candidates"| TIER1
    SCORING_ENGINE -->|"2. Score candidates"| TIER2

    %% Tier1 filters
    TIER1 -->|"Uses"| T1_APPLICABILITY
    TIER1 -->|"Uses"| T1_COVERAGE

    %% Tier2 scorers
    TIER2 -->|"Uses"| T2_COVERAGE
    TIER2 -->|"Uses"| T2_DEPTH
    TIER2 -->|"Uses"| T2_DIVERSITY
    TIER2 -->|"Uses"| T2_AMBIGUITY
    T2_COVERAGE -->|"Extends"| T2_BASE
    T2_DEPTH -->|"Extends"| T2_BASE
    T2_DIVERSITY -->|"Extends"| T2_BASE
    T2_AMBIGUITY -->|"Extends"| T2_BASE

    %% Repositories → Database
    SESSION_REPO -->|"CRUD"| SQLITE
    GRAPH_REPO -->|"CRUD"| SQLITE
    UTTERANCE_REPO -->|"CRUD"| SQLITE

    %% Domain Models (used by all layers)
    DOMAIN_TURN -.->|"Used by"| PIPELINE_CTX
    DOMAIN_KG -.->|"Used by"| GRAPH_SVC
    DOMAIN_EXTRACTION -.->|"Used by"| EXTRACTION_SVC
    DOMAIN_UTTERANCE -.->|"Used by"| UTTERANCE_REPO
    DOMAIN_INTERVIEW -.->|"Used by"| SESSION_SVC

    %% Configuration
    CONFIG_MAIN -->|"Loads"| CONFIG_INTERVIEW
    CONFIG_MAIN -->|"Loads"| CONFIG_SCORING
    DOMAIN_METHODS -->|"Loads"| CONFIG_METHODS

    %% Services use config
    SESSION_SVC -.->|"Reads"| CONFIG_INTERVIEW
    STRATEGY_SVC -.->|"Reads"| CONFIG_SCORING
    EXTRACTION_SVC -.->|"Reads"| DOMAIN_METHODS
```

---

## Legend

| Layer | Color | Description |
|-------|-------|-------------|
| **API Layer** | 🔵 Blue | HTTP endpoints and request/response handling |
| **Service Layer** | 🟣 Purple | Core business logic and orchestration |
| **Pipeline Layer** | 🟠 Orange | Turn processing pipeline (ADR-008) |
| **Repository Layer** | 🟢 Green | Database access abstraction |
| **Domain Models** | 🔴 Pink | Business entities and data structures |
| **LLM Layer** | 🟡 Lime | Language model integration |
| **Scoring Layer** | 🔵 Teal | Two-tier scoring system (ADR-006) |

---

## Module Count by Layer

| Layer | Modules |
|-------|---------|
| API | 3 (routes, schemas, dependencies) |
| Services | 6 (session, extraction, graph, question, strategy, export) |
| Pipeline | 14 (pipeline, context, result, base, 10 stages) |
| Scoring | ~10 (engine, tier1 filters, tier2 scorers, base) |
| Repositories | 3 (session, graph, utterance) |
| Domain | 5+ (turn, knowledge_graph, extraction, utterance, interview_state) |
| LLM | 2 (client, prompts) |
| **Total** | **~43 modules** |

---

## Data Flow Summary

### 1. Request Flow
```
User Input → API Routes → SessionService → TurnPipeline → 10 Stages → TurnResult → API Response
```

### 2. PipelineContext Accumulation
```
Initial: {session_id, user_input}
  ↓ ContextLoadingStage
Add: {methodology, graph_state, recent_utterances}
  ↓ ExtractionStage
Add: {extraction (concepts, relationships)}
  ↓ GraphUpdateStage
Add: {nodes_added, edges_added}
  ↓ StateComputationStage
Update: {graph_state}
  ↓ StrategySelectionStage
Add: {strategy, focus, scoring}
  ↓ ContinuationStage
Add: {should_continue}
  ↓ QuestionGenerationStage
Add: {next_question}
  ↓ ResponseSavingStage
Add: {system_utterance}
  ↓ ScoringPersistenceStage
Add: {scoring}
```

### 3. Service Dependencies
```
SessionService
  ├─→ ExtractionService ──→ LLM Client
  ├─→ GraphService ──────→ GraphRepository
  ├─→ QuestionService ────→ LLM Client
  └─→ StrategyService ────→ TwoTierScoringEngine
                            ├─→ Tier1 Filters
                            └─→ Tier2 Scorers
```

---

## References

- **ADR-006**: Two-tier scoring architecture
- **ADR-008**: Pipeline pattern + internal API boundaries
- **ADR-007**: YAML-based methodology schema
- **Data Flow Diagram**: `docs/data_flow_diagram.md` - Detailed stage breakdown
