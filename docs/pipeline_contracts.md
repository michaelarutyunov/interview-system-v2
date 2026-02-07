# Pipeline Stage Contracts

> **Context**: This document defines the read/write contracts for each stage in the turn processing pipeline.
> **Related**: [Data Flow Paths](./data_flow_paths.md) | [ADR-008: Internal API Boundaries](./adr/008-internal-api-boundaries-pipeline-pattern.md) | [ADR-010: Pipeline Contracts](./adr/010-formalize-pipeline-contracts-strengthen-data-models.md)

## Overview

The turn pipeline implements a **shared context accumulator pattern** where `PipelineContext` flows through all stages. Each stage has well-defined read/write contracts:

- **Inputs**: Immutable parameters set at pipeline creation
- **Reads**: Context fields consumed by the stage
- **Writes**: Context fields modified or populated by the stage

**ADR-010 Phase 2**: Pipeline contracts have been formalized as Pydantic models in `src/domain/models/pipeline_contracts.py`. Each stage now has typed input/output models with enhanced traceability via `source_utterance_id` fields throughout extraction and scoring data.

## Implementation Status

**Total Stages**: 11 (including optional Stage 2.5: SRLPreprocessingStage)
**Stages with Contracts**: 11 (100%)
**Stages Missing Contracts**: 0 (0%)

**Status**: ✅ All pipeline stages have formal contracts defined

---

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
| `SrlPreprocessingOutput` | Discourse relations and SRL frames | `SRLPreprocessingStage` |
| `StateComputationOutput` | Fresh graph state with timestamp | `StateComputationStage` |
| `StrategySelectionInput` | Validated input for strategy selection | `StrategySelectionStage` |
| `StrategySelectionOutput` | Selected strategy with scoring breakdown | `StrategySelectionStage` |
| `ExtractionOutput` | Concepts and relationships with counts | `ExtractionStage` |
| `GraphUpdateOutput` | Graph updates with counts | `GraphUpdateStage` |
| `QuestionGenerationOutput` | Generated question with LLM fallback flag | `QuestionGenerationStage` |
| `ResponseSavingOutput` | Saved system utterance | `ResponseSavingStage` |
| `ContinuationOutput` | Continuation decision with reason | `ContinuationStage` |
| `ScoringPersistenceOutput` | Scoring data with flag tracking | `ScoringPersistenceStage` |

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

---

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
    strategy_history: deque[str]  # Auto-trimmed to 30 items

    # Graph state (loaded in ContextLoadingStage, updated in StateComputationStage)
    graph_state: Optional[GraphState]
    recent_nodes: List[KGNode]

    # Node state tracking (persisted across turns via SessionService)
    # Phase 9 (2026-02-03): Now persisted to sessions.node_tracker_state
    node_tracker: NodeStateTracker

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
    focus: Optional[Dict[str, Any]]  # Contains focus_node_id when strategy selects a node
    signals: Optional[Dict[str, Any]]  # Phase 4: Methodology signals (namespaced)
    strategy_alternatives: List[tuple[str, float]]  # Phase 4: Scored alternatives

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

---

## Stage Dependencies (Contract Validation)

Each stage validates that its required predecessor stages have completed successfully by checking for the presence of their contract outputs. This ensures pipeline execution order is maintained and prevents silent failures.

| Stage | Depends On | Validation Check |
|-------|-----------|------------------|
| **Stage 1: ContextLoadingStage** | None (first stage) | N/A |
| **Stage 2: UtteranceSavingStage** | Stage 1: `context_loading_output` | Validates context is loaded |
| **Stage 2.5: SRLPreprocessingStage** | Stage 2: `utterance_saving_output` | Validates utterance is saved |
| **Stage 3: ExtractionStage** | Stage 2: `utterance_saving_output` | Validates utterance is saved (optional SRL hints from Stage 2.5) |
| **Stage 4: GraphUpdateStage** | Stage 2: `utterance_saving_output`, Stage 3: `extraction_output` | Validates both utterance saved and extraction completed |
| **Stage 5: StateComputationStage** | Stage 4: `graph_update_output` | Validates graph was updated |
| **Stage 6: StrategySelectionStage** | Stage 5: `state_computation_output` | Validates state computation completed |
| **Stage 7: ContinuationStage** | Stage 6: `strategy_selection_output` | Validates strategy was selected |
| **Stage 8: QuestionGenerationStage** | Stage 6: `strategy_selection_output`, Stage 7: `continuation_output` | Validates both strategy selected and continuation determined |
| **Stage 9: ResponseSavingStage** | Stage 8: `question_generation_output` | Validates question was generated |
| **Stage 10: ScoringPersistenceStage** | Stage 6: `strategy_selection_output` | Validates strategy was selected |

### Implementation Pattern

Each stage implements contract validation at the start of its `process()` method:

```python
async def process(self, context: "PipelineContext") -> "PipelineContext":
    """Stage-specific docstring..."""
    # Validate Stage N (PredecessorStage) completed first
    if context.predecessor_output is None:
        raise RuntimeError(
            "Pipeline contract violation: CurrentStage (Stage N+1) requires "
            "PredecessorStage (Stage N) to complete first."
        )
    # ... rest of stage logic
```

### Benefits

1. **Fail-fast**: Errors are detected immediately when stages are called out of order
2. **Clear error messages**: Each violation identifies both the current stage and the missing predecessor
3. **Documentation**: The validation checks serve as inline documentation of stage dependencies
4. **Debugging**: Contract violations are easy to trace through the error messages

---

## Stage Contracts

### Stage 1: ContextLoadingStage

**File**: `src/services/turn_pipeline/stages/context_loading_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Load session metadata, conversation history, and current graph state from database |
| **Dependencies** | None (first stage) |
| **Immutable Inputs** | `session_id`, `user_input` |
| **Reads** | Database (Session, Utterance, GraphRepository) |
| **Writes** | `context_loading_output` (ContextLoadingOutput contract) |
| **Side Effects** | None (read-only database operations) |

**Contract Output**: `ContextLoadingOutput`
```python
methodology: str           # Methodology identifier
concept_id: str           # Concept identifier
concept_name: str         # Human-readable concept name
turn_number: int          # Current turn number
mode: str                 # Interview mode
max_turns: int            # Maximum turns
recent_utterances: List[Dict[str, str]]  # Conversation history
strategy_history: deque[str]  # Strategy history (auto-trimmed to 30 items)
graph_state: GraphState    # Knowledge graph state
recent_nodes: List[KGNode] # Recent nodes
```

**Note**: `graph_state` is refreshed by `StateComputationStage` (Stage 5), not this stage.

---

### Stage 2: UtteranceSavingStage

**File**: `src/services/turn_pipeline/stages/utterance_saving_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Persist user input to database for conversation history and provenance |
| **Dependencies** | Stage 1: `context_loading_output` |
| **Immutable Inputs** | `session_id`, `user_input` |
| **Reads** | `turn_number` |
| **Writes** | `utterance_saving_output` (UtteranceSavingOutput contract) |
| **Side Effects** | INSERT to utterances table |

**Contract Output**: `UtteranceSavingOutput`
```python
turn_number: int          # Turn number for this utterance
user_utterance_id: str    # Database ID of saved utterance
user_utterance: Utterance # Full saved utterance record
```

---

### Stage 2.5: SRLPreprocessingStage

**File**: `src/services/turn_pipeline/stages/srl_preprocessing_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Extract linguistic structure (discourse relations, SRL frames) to guide extraction with structural hints |
| **Dependencies** | Stage 2: `utterance_saving_output` |
| **Immutable Inputs** | `user_input` |
| **Reads** | `recent_utterances` (to extract interviewer question) |
| **Writes** | `srl_preprocessing_output` (SrlPreprocessingOutput contract) |
| **Side Effects** | None (read-only spaCy analysis) |
| **Feature Flag** | `enable_srl` in Settings (if disabled or srl_service=None, stage outputs empty contract) |

**Contract Output**: `SrlPreprocessingOutput`
```python
discourse_relations: List[Dict[str, str]]  # {marker, antecedent, consequent}
srl_frames: List[Dict[str, Any]]          # {predicate, arguments}
discourse_count: int                      # Number of discourse relations found
frame_count: int                          # Number of SRL frames found
timestamp: datetime                       # When SRL analysis was performed
```

**Input Requirements:**
- `PipelineContext.user_input` (from pipeline creation)
- `PipelineContext.context_loading_output.recent_utterances` (from Stage 1)
- `PipelineContext.utterance_saving_output` (from Stage 2) - validates Stage 2 completed

**Behavior:**
- If `srl_service is None` (feature disabled): Set empty `SrlPreprocessingOutput` and return
- Extract interviewer question from `recent_utterances` (last system utterance)
- Call `srl_service.analyze(user_utterance, interviewer_question)`
- Build `SrlPreprocessingOutput` from results
- Log `srl_analysis_complete` with `discourse_count`, `frame_count`

**Error Handling:**
- If `srl_service` is None (feature disabled): Set empty output, return (do not crash pipeline)
- If spaCy model load fails: Log error, set empty output, return (graceful degradation)
- SRLService handles all spaCy errors internally and returns empty structures

**Note**: This stage is optional and can be disabled via `enable_srl=False` config flag. When disabled, the stage still runs but produces an empty contract output for consistency.

---

### Stage 3: ExtractionStage

**File**: `src/services/turn_pipeline/stages/extraction_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Extract concepts and relationships from user text using AI/ML |
| **Dependencies** | Stage 2: `utterance_saving_output` |
| **Immutable Inputs** | `user_input` |
| **Reads** | `recent_utterances`, `concept_id`, `srl_preprocessing_output` (optional, from Stage 2.5) |
| **Writes** | `extraction_output` (ExtractionOutput contract) |
| **Side Effects** | LLM API call |

**Contract Output**: `ExtractionOutput`
```python
extraction: ExtractionResult  # Extracted concepts and relationships
methodology: str               # Methodology used for extraction
timestamp: datetime           # When extraction was performed (auto-set)
concept_count: int           # Number of concepts extracted (auto-calculated)
relationship_count: int       # Number of relationships extracted (auto-calculated)
```

**Behavior:**
- If `srl_preprocessing_output` has data (from Stage 2.5): Inject structural analysis section into extraction context
- Format: `## STRUCTURAL ANALYSIS (use to guide relationship extraction):`
  - Causal/temporal markers: `[marker]: "antecedent" → "consequent"`
  - Predicate-argument structures: `predicate: nsubj=X, dobj=Y, ...` (limited to top 5 frames)
- Log `srl_context_added` with approximate token count of added section
- If `srl_preprocessing_output` is None or empty: Extraction works identically (backward compatible)

**Features**:
- Auto-calculates counts from extraction result
- Auto-sets timestamp
- Optional SRL structural hints injection (Phase 1: SRL Preprocessing Infrastructure)

---

### Stage 4: GraphUpdateStage

**File**: `src/services/turn_pipeline/stages/graph_update_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Add extracted concepts and relationships to knowledge graph |
| **Dependencies** | Stage 2: `utterance_saving_output`, Stage 3: `extraction_output` |
| **Immutable Inputs** | None |
| **Reads** | `extraction`, `user_utterance` (from contract outputs) |
| **Writes** | `graph_update_output` (GraphUpdateOutput contract) |
| **Side Effects** | INSERT/UPDATE to nodes and edges in graph database; updates NodeStateTracker |

**Contract Output**: `GraphUpdateOutput`
```python
nodes_added: List[KGNode]     # Nodes added to graph
edges_added: List[Dict[str, Any]]  # Edges added to graph
node_count: int               # Number of nodes added (auto-calculated)
edge_count: int               # Number of edges added (auto-calculated)
timestamp: datetime           # When graph update was performed (auto-set)
```

**Features**:
- Auto-calculates counts from lists
- Auto-sets timestamp
- **NodeStateTracker integration**:
  - `register_node()` - Registers new nodes when added
  - `update_edge_counts()` - Updates relationship counts for nodes
  - `record_yield()` - Records yield when graph changes occur

---

### Stage 5: StateComputationStage

**File**: `src/services/turn_pipeline/stages/state_computation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Refresh graph state metrics after updates (node count, coverage, depth, etc.) |
| **Dependencies** | Stage 4: `graph_update_output` |
| **Immutable Inputs** | `session_id` |
| **Reads** | None (re-queries from database) |
| **Writes** | `state_computation_output` (StateComputationOutput contract) |
| **Side Effects** | None (read-only database operations) |

**Contract Output**: `StateComputationOutput`
```python
graph_state: GraphState       # Refreshed knowledge graph state
recent_nodes: List[KGNode]    # Refreshed recent nodes
computed_at: datetime         # When state was computed (freshness tracking)
```

**ADR-010**: Includes freshness validation to prevent stale state bug.

---

### Stage 6: StrategySelectionStage

**File**: `src/services/turn_pipeline/stages/strategy_selection_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Select questioning strategy and focus node using joint strategy-node scoring (D1 Architecture) |
| **Dependencies** | Stage 5: `state_computation_output` |
| **Immutable Inputs** | `user_input`, `mode` |
| **Reads** | `state_computation_output`, `graph_state`, `recent_nodes`, `extraction`, `strategy_history`, `node_tracker` |
| **Writes** | `strategy_selection_output` (StrategySelectionOutput contract) |
| **Side Effects** | None (pure computation) |

**Contract Input**: `StrategySelectionInput`
```python
graph_state: GraphState              # Current knowledge graph state
recent_nodes: List[KGNode]           # Recent nodes
extraction: Any                       # ExtractionResult with timestamp
conversation_history: List[Dict[str, str]]  # Conversation history
turn_number: int                      # Current turn number
mode: str                             # Interview mode
computed_at: datetime                 # When graph_state was computed (freshness validation)
node_tracker: NodeStateTracker        # Node state tracker for node-level signals
```

**Contract Output**: `StrategySelectionOutput`
```python
strategy: str                          # Selected strategy ID
focus: Optional[Dict[str, Any]]        # Focus target with focus_node_id
selected_at: datetime                   # When strategy was selected (auto-set)
signals: Optional[Dict[str, Any]]      # Methodology-specific signals (namespaced)
strategy_alternatives: List[tuple[str, str, float]]  # (strategy, node_id, score) tuples
```

**D1 Architecture Update**: Now uses `MethodologyStrategyService.select_strategy_and_focus()` with joint strategy-node scoring:
- `rank_strategy_node_pairs()` scores all (strategy, node) combinations
- Returns best (strategy, node_id) pair with alternatives for debugging
- Node-level signals enable exhaustion-aware backtracking

---

### Stage 7: ContinuationStage

**File**: `src/services/turn_pipeline/stages/continuation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Determine if interview should continue and select focus concept |
| **Dependencies** | Stage 6: `strategy_selection_output` |
| **Immutable Inputs** | `turn_number`, `max_turns` |
| **Reads** | `graph_state`, `strategy`, `focus` (uses focus_node_id from D1 joint selection) |
| **Writes** | `continuation_output` (ContinuationOutput contract) |
| **Side Effects** | None (pure computation) |

**Contract Output**: `ContinuationOutput`
```python
should_continue: bool     # Whether to continue the interview
focus_concept: str       # Concept to focus on next turn
reason: str              # Reason for continuation decision
turns_remaining: int     # Number of turns remaining
timestamp: datetime      # When continuation decision was made (auto-set)
```

**D1 Architecture**: The `focus` dict contains `focus_node_id` selected jointly with the strategy by `rank_strategy_node_pairs()`.

---

### Stage 8: QuestionGenerationStage

**File**: `src/services/turn_pipeline/stages/question_generation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Generate follow-up question or closing message |
| **Dependencies** | Stage 6: `strategy_selection_output`, Stage 7: `continuation_output` |
| **Immutable Inputs** | None |
| **Reads** | `should_continue`, `focus_concept`, `recent_utterances`, `graph_state`, `strategy` |
| **Writes** | `question_generation_output` (QuestionGenerationOutput contract) |
| **Side Effects** | LLM API call |

**Contract Output**: `QuestionGenerationOutput`
```python
question: str              # Generated question text
strategy: str               # Strategy used to generate question
focus: Optional[Dict[str, Any]]  # Focus target for question
has_llm_fallback: bool      # Whether LLM fallback was used
timestamp: datetime          # When question was generated (auto-set)
```

---

### Stage 9: ResponseSavingStage

**File**: `src/services/turn_pipeline/stages/response_saving_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Persist system response to database |
| **Dependencies** | Stage 8: `question_generation_output` |
| **Immutable Inputs** | `session_id`, `turn_number` |
| **Reads** | `question_generation_output` |
| **Writes** | `response_saving_output` (ResponseSavingOutput contract) |
| **Side Effects** | INSERT to utterances table |

**Contract Output**: `ResponseSavingOutput`
```python
turn_number: int           # Turn number for this utterance
system_utterance_id: str   # Database ID of saved utterance
system_utterance: Utterance # Full saved utterance record
question_text: str         # Question text that was saved
timestamp: datetime         # When response was saved (auto-set)
```

---

### Stage 10: ScoringPersistenceStage

**File**: `src/services/turn_pipeline/stages/scoring_persistence_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Save scoring results to database and update session state |
| **Dependencies** | Stage 6: `strategy_selection_output` |
| **Immutable Inputs** | `turn_number` |
| **Reads** | `strategy_selection_output` |
| **Writes** | `scoring_persistence_output` (ScoringPersistenceOutput contract) |
| **Side Effects** | UPDATE session state (turn_count, strategy_history), INSERT scoring records |

**Contract Output**: `ScoringPersistenceOutput`
```python
turn_number: int                # Turn number for scoring
strategy: str                  # Strategy that was selected
coverage_score: float           # Coverage metric from graph state
depth_score: float             # Depth metric from graph state
saturation_score: float         # Saturation metric from graph state
has_methodology_signals: bool   # Whether methodology signals were saved
has_legacy_scoring: bool        # Whether legacy two-tier scoring was saved
timestamp: datetime              # When scoring was persisted (auto-set)
```

**Note**: This stage saves both legacy two-tier scoring data (for old sessions) and new methodology-based signals (for new sessions).

---

## Known Issues: Fields Not Set by Stages

The following contract fields exist but are **not currently set** by their respective stages. They have default values or validators that auto-calculate them:

| Stage | Field | Status |
|-------|-------|--------|
| Stage 3 | `timestamp` | Has default factory - works |
| Stage 3 | `concept_count`, `relationship_count` | Has validator - auto-calculates |
| Stage 4 | `timestamp` | Has default factory - works |
| Stage 4 | `node_count`, `edge_count` | Has validator - auto-calculates |
| Stage 6 | `selected_at` | Has default factory - works |
| Stage 7 | `has_llm_fallback` | Has default=False - stage should set this |
| Stage 8 | `timestamp` | Has default factory - works |
| Stage 9 | `timestamp` | Has default factory - works |
| Stage 9 | `reason` | Has default="" - stage should set this |
| Stage 9 | `turns_remaining` | Required field - stage must set this |
| Stage 10 | `timestamp` | Has default factory - works |
| Stage 10 | `has_methodology_signals` | Has default=False - stage should set this |
| Stage 10 | `has_legacy_scoring` | Has default=False - stage should set this |

**Recommendation**: Stages 7, 9, and 10 should be updated to explicitly set their boolean fields for better observability. Stage 9 must set `turns_remaining`.

---

## TurnResult: Pipeline Output

**File**: `src/services/turn_pipeline/result.py`

The `TurnResult` dataclass is the final output returned by the pipeline after all stages complete. It aggregates key information from the turn processing.

```python
@dataclass
class TurnResult:
    turn_number: int
    extracted: dict                    # concepts, relationships
    graph_state: dict                  # node_count, edge_count, depth_achieved
    scoring: dict                      # strategy_id, score, reasoning (Phase 3)
    strategy_selected: Optional[str]   # Selected strategy name
    next_question: str                  # Generated question
    should_continue: bool              # Whether interview continues
    latency_ms: int = 0                # Pipeline execution time
    signals: Optional[Dict[str, Any]] = None           # Raw methodology signals (Phase 6)
    strategy_alternatives: Optional[List[Dict[str, Any]]] = None  # Alternative strategies with scores
    termination_reason: Optional[str] = None  # Reason for termination (e.g., "max_turns_reached", "graph_saturated", "depth_plateau")
```

### Field Details

| Field | Source | Description |
|-------|--------|-------------|
| `turn_number` | PipelineContext | Current turn number (1-indexed) |
| `extracted` | ExtractionOutput | Extracted concepts and relationships |
| `graph_state` | StateComputationOutput | Current graph state metrics |
| `scoring` | ScoringPersistenceOutput | Strategy scoring data |
| `strategy_selected` | StrategySelectionOutput | Selected strategy name |
| `next_question` | QuestionGenerationOutput | Generated follow-up question |
| `should_continue` | ContinuationOutput | Whether to continue interview |
| `latency_ms` | Pipeline | Total execution time in milliseconds |
| `signals` | StrategySelectionOutput | Raw signals from signal pools (Phase 6) |
| `strategy_alternatives` | StrategySelectionOutput | All scored alternatives with scores |
| `termination_reason` | ContinuationOutput.reason | Reason for termination when `should_continue=False` |

### Termination Reasons

The `termination_reason` field is populated by `ContinuationStage` when `should_continue=False`:

| Reason | Description |
|--------|-------------|
| `"max_turns_reached"` | Interview reached configured max_turns limit |
| `"depth_plateau"` | Graph max_depth hasn't increased in 6 consecutive turns |
| `"quality_degraded"` | Consecutive shallow responses detected (saturation) |
| `"close_strategy"` | Closing strategy was selected |

### Usage

`TurnResult` is returned by:
- `SessionService.process_turn()` - API endpoint response
- Simulation endpoints - For testing and diagnostics
- Tests - For validating pipeline behavior

---

## Historical Note: Removed Deprecated Models

The following models were removed as part of the two-tier scoring system cleanup (Phase 6, 2026-01-28):

- `Focus` (old two-tier version - different from `src.domain.models.turn.Focus`)
- `VetoResult`
- `WeightedResult`
- `ScoredStrategy`
- `StrategySelectionResult`

These were kept only for database compatibility but are no longer needed as the system now uses methodology-based signal detection.

---

## Contract Verification

When modifying pipeline stages, ensure:

1. **Read-before-write**: A stage should never write to a context field it hasn't first read (unless it's the sole producer)
2. **No side-channel communication**: All data must flow through PipelineContext
3. **Immutability**: Input parameters (`session_id`, `user_input`) must never be modified
4. **Traceability**: Every write should have a corresponding database operation or computation trace

---

## Related Documentation

- [Data Flow Paths](./data_flow_paths.md) - Visual diagrams of critical data flows
- [ADR-008: Internal API Boundaries](./adr/008-internal-api-boundaries-pipeline-pattern.md) - Architecture rationale
- [ADR-010: Three-Client LLM Architecture](./adr/010-three-client-llm-architecture.md) - LLM service architecture
- [SYSTEM_DESIGN](./SYSTEM_DESIGN.md) - Narrative system architecture for articles
