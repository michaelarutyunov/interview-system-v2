# Pipeline Stage Contracts

> **Context**: This document defines the read/write contracts for each stage in the turn processing pipeline.
> **Related**: [Data Flow Paths](./data_flow_paths.md) | [ADR-008: Internal API Boundaries](./adr/008-internal-api-boundaries-pipeline-pattern.md) | [ADR-010: Pipeline Contracts](./adr/010-formalize-pipeline-contracts-strengthen-data-models.md)

## Overview

The turn pipeline implements a **shared context accumulator pattern** where `PipelineContext` flows through all stages. Each stage has well-defined read/write contracts:

- **Inputs**: Immutable parameters set at pipeline creation
- **Reads**: Context fields consumed by the stage
- **Writes**: Context fields modified or populated by the stage

**ADR-010 Phase 2**: Pipeline contracts have been formalized as Pydantic models in `src/domain/models/pipeline_contracts.py`. Each stage now has typed input/output models with enhanced traceability via `source_utterance_id` fields throughout extraction and scoring data.

## Pydantic Contract Models (ADR-010 Phase 2)

ADR-010 Phase 2 introduced typed Pydantic models for all pipeline stage inputs and outputs. These models provide:

- **Type Safety**: Runtime validation ensures data integrity
- **Traceability**: `source_utterance_id` links all extraction and scoring data to specific user utterances
- **Freshness Tracking**: `computed_at` timestamps prevent using stale state
- **Documentation**: Field descriptions serve as inline documentation

### Key Contract Models

| Model | Purpose | Location |
|-------|---------|----------|
| `ContextLoadingOutput` | Session metadata, graph state | `ContextLoadingStage` |
| `UtteranceSavingOutput` | Saved utterance with ID | `UtteranceSavingStage` |
| `StateComputationOutput` | Fresh graph state with timestamp | `StateComputationStage` |
| `StrategySelectionInput` | Validated input for strategy selection | `StrategySelectionStage` |
| `StrategySelectionOutput` | Selected strategy with scoring breakdown | `StrategySelectionStage` |
| `ExtractionResult` | Concepts and relationships with traceability | `ExtractionStage` |
| `QualitativeSignalSet` | LLM-extracted semantic signals | Signal extraction |

### Traceability Pattern

All data extracted from user input now includes `source_utterance_id`:

```python
# ExtractionResult with traceability
concept = ExtractedConcept(
    text="oat milk is creamy",
    node_type="attribute",
    source_utterance_id="utter_123",  # Links to UtteranceSavingOutput.utterance_id
)

# QualitativeSignalSet with metadata
signals = QualitativeSignalSet(
    turn_number=5,
    source_utterance_id="utter_123",  # Same utterance
    generated_at=datetime.now(timezone.utc),
    llm_model="moonshot-v1-8k",
    prompt_version="v2.1",
)
```

This traceability chain enables debugging and analysis:
- Which utterance produced this concept?
- What signals were extracted from this response?
- Why was this strategy selected for this turn?

## Pipeline Context Schema

The `PipelineContext` class (defined in `src/services/turn_pipeline/context.py`) contains all state that flows through the pipeline:

```python
@dataclass
class PipelineContext:
    # Input parameters (immutable after creation)
    session_id: str
    user_input: str

    # Session metadata (loaded in ContextLoadingStage)
    methodology: str
    concept_id: str
    concept_name: str
    turn_number: int
    mode: str
    max_turns: int
    recent_utterances: List[Dict[str, str]]
    strategy_history: List[str]

    # Graph state (loaded in ContextLoadingStage, updated in StateComputationStage)
    graph_state: Optional[GraphState]
    recent_nodes: List[KGNode]

    # Extraction results (computed in ExtractionStage)
    extraction: Optional[ExtractionResult]

    # Utterances (saved in UtteranceSavingStage, ResponseSavingStage)
    user_utterance: Optional[Utterance]
    system_utterance: Optional[Utterance]

    # Graph updates (computed in GraphUpdateStage)
    nodes_added: List[KGNode]
    edges_added: List[Dict[str, Any]]

    # Strategy selection (computed in StrategySelectionStage)
    strategy: str
    selection_result: Optional[Any]
    focus: Optional[Dict[str, Any]]

    # Continuation decision (computed in ContinuationStage)
    should_continue: bool
    focus_concept: str

    # Generated question (computed in QuestionGenerationStage)
    next_question: str

    # Scoring data (computed in ScoringPersistenceStage)
    scoring: Dict[str, Any]

    # Performance tracking
    stage_timings: Dict[str, float]
```

## Stage Contracts

### Stage 1: ContextLoadingStage

**File**: `src/services/turn_pipeline/stages/context_loading_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Load session metadata, conversation history, and current graph state from database |
| **Immutable Inputs** | `session_id`, `user_input` |
| **Reads** | Database (Session, Utterance, GraphRepository) |
| **Writes** | `methodology`, `concept_id`, `concept_name`, `turn_number`, `mode`, `max_turns`, `recent_utterances`, `strategy_history`, `graph_state`, `recent_nodes` |
| **Side Effects** | None (read-only database operations) |

### Stage 2: UtteranceSavingStage

**File**: `src/services/turn_pipeline/stages/utterance_saving_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Persist user input to database for conversation history and provenance |
| **Immutable Inputs** | `session_id`, `user_input` |
| **Reads** | `turn_number` |
| **Writes** | `user_utterance` |
| **Side Effects** | INSERT to utterances table |

### Stage 3: ExtractionStage

**File**: `src/services/turn_pipeline/stages/extraction_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Extract concepts and relationships from user text using AI/ML |
| **Immutable Inputs** | `user_input` |
| **Reads** | `recent_utterances`, `concept_id` |
| **Writes** | `extraction` (ExtractionResult with concepts and relationships) |
| **Side Effects** | LLM API call |

### Stage 4: GraphUpdateStage

**File**: `src/services/turn_pipeline/stages/graph_update_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Add extracted concepts and relationships to knowledge graph |
| **Immutable Inputs** | None |
| **Reads** | `extraction`, `user_utterance` |
| **Writes** | `nodes_added`, `edges_added` |
| **Side Effects** | INSERT/UPDATE to nodes and edges in graph database |

### Stage 5: StateComputationStage

**File**: `src/services/turn_pipeline/stages/state_computation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Refresh graph state metrics after updates (node count, coverage, depth, etc.) |
| **Immutable Inputs** | `session_id` |
| **Reads** | None (re-queries from database) |
| **Writes** | `graph_state` (refreshed), `recent_nodes` (refreshed) |
| **Side Effects** | None (read-only database operations) |

### Stage 6: StrategySelectionStage

**File**: `src/services/turn_pipeline/stages/strategy_selection_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Select questioning strategy using two-tier adaptive scoring system |
| **Immutable Inputs** | `user_input`, `mode` |
| **Reads** | `graph_state`, `recent_nodes`, `recent_utterances`, `extraction`, `strategy_history` |
| **Writes** | `strategy`, `selection_result`, `focus` |
| **Side Effects** | None (pure computation) |

**Implementation Note**: Uses `.model_dump()` for Pydantic v2 compatibility when passing node data to strategy selector.

### Stage 7: ContinuationStage

**File**: `src/services/turn_pipeline/stages/continuation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Determine if interview should continue and select focus concept |
| **Immutable Inputs** | `turn_number`, `max_turns` |
| **Reads** | `graph_state`, `strategy`, `selection_result`, `focus` |
| **Writes** | `should_continue`, `focus_concept` |
| **Side Effects** | None (pure computation) |

### Stage 8: QuestionGenerationStage

**File**: `src/services/turn_pipeline/stages/question_generation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Generate follow-up question or closing message |
| **Immutable Inputs** | None |
| **Reads** | `should_continue`, `focus_concept`, `recent_utterances`, `graph_state`, `strategy` |
| **Writes** | `next_question` |
| **Side Effects** | LLM API call |

### Stage 9: ResponseSavingStage

**File**: `src/services/turn_pipeline/stages/response_saving_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Persist system response to database |
| **Immutable Inputs** | `session_id`, `turn_number` |
| **Reads** | `next_question` |
| **Writes** | `system_utterance` |
| **Side Effects** | INSERT to utterances table |

### Stage 10: ScoringPersistenceStage

**File**: `src/services/turn_pipeline/stages/scoring_persistence_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Save scoring results to database and update session state |
| **Immutable Inputs** | `turn_number` |
| **Reads** | `strategy`, `selection_result` |
| **Writes** | `scoring` (detailed breakdown) |
| **Side Effects** | UPDATE session state (turn_count, strategy_history), INSERT scoring records |

## Contract Verification

When modifying pipeline stages, ensure:

1. **Read-before-write**: A stage should never write to a context field it hasn't first read (unless it's the sole producer)
2. **No side-channel communication**: All data must flow through PipelineContext
3. **Immutability**: Input parameters (`session_id`, `user_input`) must never be modified
4. **Traceability**: Every write should have a corresponding database operation or computation trace

## Related Documentation

- [Data Flow Paths](./data_flow_paths.md) - Visual diagrams of critical data flows
- [ADR-008: Internal API Boundaries](./adr/008-internal-api-boundaries-pipeline-pattern.md) - Architecture rationale
- [ADR-010: Three-Client LLM Architecture](./adr/010-three-client-llm-architecture.md) - LLM service architecture
