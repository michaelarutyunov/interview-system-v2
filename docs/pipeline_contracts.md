# Pipeline Stage Contracts

> **Context**: This document defines the read/write contracts for each stage in the turn processing pipeline.
> **Related**: [Data Flow Paths](./data_flow_paths.md) | [ADR-008: Internal API Boundaries](./adr/008-internal-api-boundaries-pipeline-pattern.md) | [ADR-010: Pipeline Contracts](./adr/010-formalize-pipeline-contracts-strengthen-data-models.md)

## Overview

The turn pipeline implements a **shared context accumulator pattern** where `PipelineContext` flows through all stages. Each stage has well-defined read/write contracts:

- **Inputs**: Immutable parameters set at pipeline creation
- **Reads**: Context fields consumed by the stage
- **Writes**: Context fields modified or populated by the stage

**ADR-010 Phase 2**: Pipeline contracts have been formalized as Pydantic models in `src/domain/models/pipeline_contracts.py`. Each stage now has typed input/output models with enhanced traceability via `source_utterance_id` fields throughout extraction and scoring data.

**Total Pipeline Stages**: 12 (10 base stages + 2 optional stages)

## Implementation Status

**Total Stages**: 12 (including optional Stage 2.5: SRLPreprocessingStage and Stage 4.5: SlotDiscoveryStage)

**Stage Configuration**:
- **Base stages**: 10 (always run)
- **Optional stages**: 2 (controlled by feature flags)
  - Stage 2.5 (SRLPreprocessingStage): `enable_srl=True` (default: True)
  - Stage 4.5 (SlotDiscoveryStage): `enable_canonical_slots=True` (default: True)
- **Total when both enabled**: 12 stages
- **Total when both disabled**: 10 stages

**Stages with Contracts**: 12 (100%)
- **Stages Missing Contracts**: 0 (0%)

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
| `ExtractionOutput` | Concepts and relationships with counts | `ExtractionStage` |
| `GraphUpdateOutput` | Graph updates with counts | `GraphUpdateStage` |
| `SlotDiscoveryOutput` | Canonical slot discovery counts | `SlotDiscoveryStage` (Stage 4.5) |
| `StateComputationOutput` | Fresh graph state with timestamp | `StateComputationStage` |
| `StrategySelectionInput` | Validated input for strategy selection | `StrategySelectionStage` |
| `StrategySelectionOutput` | Selected strategy with scoring breakdown | `StrategySelectionStage` |
| `ContinuationOutput` | Continuation decision with reason | `ContinuationStage` |
| `QuestionGenerationOutput` | Generated question with LLM fallback flag | `QuestionGenerationStage` |
| `ResponseSavingOutput` | Saved system utterance | `ResponseSavingStage` |
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

The `PipelineContext` class (defined in `src/services/turn_pipeline/context.py`) contains all state that flows through the pipeline using a **contract-based architecture** (ADR-010 Phase 2).

### Architecture Pattern

Instead of direct fields, `PipelineContext` stores:
1. **Stage output contracts** - Optional Pydantic models from each stage
2. **Convenience properties** - Read from contract outputs for easy access
3. **Service references** - Injected dependencies (node_tracker, etc.)

### Schema Structure

```python
@dataclass
class PipelineContext:
    # Input parameters (immutable after creation)
    session_id: str
    user_input: str

    # Service references
    node_tracker: Optional["NodeStateTracker"] = None

    # Stage output contracts (accumulated by each stage)
    # The single source of truth for pipeline state

    # Stage 1: ContextLoadingStage
    context_loading_output: Optional[ContextLoadingOutput] = None

    # Stage 2: UtteranceSavingStage
    utterance_saving_output: Optional[UtteranceSavingOutput] = None

    # Stage 2.5: SRLPreprocessingStage (optional)
    srl_preprocessing_output: Optional[SrlPreprocessingOutput] = None

    # Stage 3: ExtractionStage
    extraction_output: Optional[ExtractionOutput] = None

    # Stage 4: GraphUpdateStage
    graph_update_output: Optional[GraphUpdateOutput] = None

    # Stage 4.5: SlotDiscoveryStage (optional)
    slot_discovery_output: Optional[SlotDiscoveryOutput] = None

    # Stage 5: StateComputationStage
    state_computation_output: Optional[StateComputationOutput] = None

    # Stage 6: StrategySelectionStage
    strategy_selection_output: Optional[StrategySelectionOutput] = None

    # Stage 7: ContinuationStage
    continuation_output: Optional[ContinuationOutput] = None

    # Stage 8: QuestionGenerationStage
    question_generation_output: Optional[QuestionGenerationOutput] = None

    # Stage 9: ResponseSavingStage
    response_saving_output: Optional[ResponseSavingOutput] = None

    # Stage 10: ScoringPersistenceStage
    scoring_persistence_output: Optional[ScoringPersistenceOutput] = None
```

### Convenience Properties

Each commonly-accessed field is exposed via a `@property` that derives from the appropriate contract:

```python
# Examples (not exhaustive):
@property
def methodology(self) -> str:
    """From context_loading_output.methodology"""
    return self.context_loading_output.methodology

@property
def turn_number(self) -> int:
    """From context_loading_output.turn_number"""
    return self.context_loading_output.turn_number

@property
def graph_state(self) -> GraphState:
    """From state_computation_output.graph_state"""
    return self.state_computation_output.graph_state

@property
def strategy_history(self) -> List[str]:
    """From context_loading_output.strategy_history"""
    return self.context_loading_output.strategy_history
```

This pattern ensures:
- **Single source of truth**: Stage contracts contain the data
- **Type safety**: Pydantic models validate all data
- **Traceability**: Each field can be traced to its producing stage
- **Testability**: Contracts can be inspected and tested independently

Each stage **reads** from the context and **writes** new information. This pattern ensures:
- Clear data flow contracts between stages
- Easy debugging (trace state evolution)
- Testability (each stage is isolated)
- Parallel development (stages have clear boundaries)

---

## Stage Dependencies (Contract Validation)

Each stage validates that its required predecessor stages have completed successfully by checking for the presence of their contract outputs. This ensures pipeline execution order is maintained and prevents silent failures.

| Stage | Depends On | Validates | Notes |
|-------|-----------|-----------|-------|
| **Stage 1: ContextLoadingStage** | None (first stage) | N/A | First stage in pipeline |
| **Stage 2: UtteranceSavingStage** | Stage 1: `context_loading_output` | No | Assumes context loaded |
| **Stage 2.5: SRLPreprocessingStage** | Stage 2: `utterance_saving_output` | Yes | Validates utterance saved |
| **Stage 3: ExtractionStage** | Stage 2: `utterance_saving_output` | Yes | Validates utterance saved |
| **Stage 4: GraphUpdateStage** | Stage 2: `utterance_saving_output`, Stage 3: `extraction_output` | Yes | Validates both utterance saved and extraction completed |
| **Stage 4.5: SlotDiscoveryStage** | Stage 4: `graph_update_output` | Yes | Validates graph was updated |
| **Stage 5: StateComputationStage** | Stage 4: `graph_update_output` | No | Assumes graph updated |
| **Stage 6: StrategySelectionStage** | Stage 5: `state_computation_output` | Yes | Validates graph_state set |
| **Stage 7: ContinuationStage** | Stage 6: `strategy_selection_output` | Yes | Validates strategy selected |
| **Stage 8: QuestionGenerationStage** | Stage 6: `strategy_selection_output`, Stage 7: `continuation_output` | Yes | Validates both strategy selected and continuation determined |
| **Stage 9: ResponseSavingStage** | Stage 8: `question_generation_output` | No | Assumes question generated |
| **Stage 10: ScoringPersistenceStage** | Stage 6: `strategy_selection_output` | No | Assumes strategy selected |

### Implementation Pattern

Each stage implements contract validation at the start of its `process()` method:

```python
async def process(self, context: "PipelineContext") -> "PipelineContext":
    """Stage-specific docstring..."""
    # Validate Stage N (PredecessorStage) completed first
    if context.predecessor_output is None:
        raise RuntimeError(
            f"Pipeline contract violation: {self.__class__.__name__} (Stage {current_stage_number + 1}) requires "
            f"{PredecessorStage.__class__.__name__} (Stage N) to complete first. "
        )

    # ... rest of stage logic
```

### Benefits

1. **Fail-fast**: Errors are detected immediately when stages are called out of order
2. **Clear error messages**: Each violation identifies both the current stage and the missing predecessor
3. **Documentation**: The validation checks serve as inline documentation
4. **Debugging**: Contract violations are easy to trace through the error messages

---

## Stage Contracts

### Stage 1: ContextLoadingStage

**File**: `src/services/turn_pipeline/stages/context_loading_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Load session metadata and conversation history from database |
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
strategy_history: List[str]  # History of strategies used (not deque)
recent_node_labels: List[str]  # Labels of existing nodes for cross-turn edge bridging

# Velocity state loaded from SessionState (used by saturation signals)
surface_velocity_ewma: float
surface_velocity_peak: float
prev_surface_node_count: int
canonical_velocity_ewma: float
canonical_velocity_peak: float
prev_canonical_node_count: int

# Focus history for tracing strategy-node decisions across turns
focus_history: List[FocusEntry]  # Loaded from SessionState.focus_history
```

**Note**: `graph_state` and `recent_nodes` are NOT loaded here - they come from `StateComputationStage` (Stage 5) after graph updates.

**FocusEntry Model**:
```python
class FocusEntry(BaseModel):
    turn: int        # Turn number (1-indexed)
    node_id: str     # Target node ID (empty if no node focus)
    label: str       # Human-readable node label
    strategy: str    # Strategy selected for this turn
```

**Cross-Turn Edge Resolution (Phase 4)**:
- Loads all session nodes via `get_nodes_by_session()`
- Extracts node labels into `recent_node_labels`
- These labels are injected into extraction context to enable cross-turn relationship detection

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
user_utterance: Utterance  # Full saved utterance record
```

---

### Stage 2.5: SRLPreprocessingStage (Optional)

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
srl_frames: List[Dict[str, Any]]         # {predicate, arguments}
discourse_count: int                      # Number of discourse relations found
frame_count: int                         # Number of SRL frames found
timestamp: datetime                        # When SRL analysis was performed
```

**Input Requirements:**
- `PipelineContext.user_input` (from pipeline creation)
- `PipelineContext.context_loading_output.recent_utterances` (from Stage 1) - validates Stage 2 completed
- `PipelineContext.utterance_saving_output` (from Stage 2)

**Behavior:**
- If `srl_service` is None (feature disabled): Set empty `SrlPreprocessingOutput` and return
- Extract interviewer question from `recent_utterances` (last system utterance)
- Call `srl_service.analyze(user_utterance, interviewer_question)`
- Build `SrlPreprocessingOutput` from results
- Log `srl_analysis_complete` with `discourse_count`, `frame_count`

**Error Handling** (fail-fast per ADR-009):
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
timestamp: datetime           # When extraction was performed
concept_count: int           # Number of concepts extracted (auto-calculated)
relationship_count: int       # Number of relationships extracted (auto-calculated)
```

**Input Requirements:**
- `PipelineContext.user_input` (from pipeline creation)
- `PipelineContext.context_loading_output.recent_utterances` (from Stage 1) - validates Stage 2 completed
- `PipelineContext.utterance_saving_output.user_utterance` (from Stage 2)

**Features**:
- Auto-calculates counts from extraction result
- Auto-sets timestamp
- Optional SRL structural hints injection (Phase 1: SRL Preprocessing Infrastructure):
  - Format: `## STRUCTURAL ANALYSIS (use to guide relationship extraction):`
  - Causal/temporal markers: `[marker]: "antecedent" → "consequent"`
  - Predicate-argument structures: `predicate: subj=X, dobj=Y, ...` (limited to top 5 frames)
  - Log `srl_context_added` with approximate token count of added section

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
- **Surface Semantic Deduplication (Phase 3)**:
  - 3-step dedup: exact match → semantic similarity (0.80) → create new
  - Embeddings stored in `kg_nodes.embedding` for similarity search
  - Same node_type required for semantic matches
  - Reduces over-extraction, improves NodeStateTracker accuracy
- **Cross-Turn Edge Resolution (Phase 4)**:
  - Expands `label_to_node` with all session nodes (not just current turn)
  - Enables edges to reference nodes from previous turns
  - Dramatically improves graph connectivity (+72% edges in testing)
- **NodeStateTracker integration**:
  - `register_node()` - Registers new nodes when added
  - `update_edge_counts()` - Updates relationship counts for nodes
  - `record_yield()` - Records yield when graph changes occur

---

### Stage 4.5: SlotDiscoveryStage (Optional)

**File**: `src/services/turn_pipeline/stages/slot_discovery_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Discover or update canonical slots for newly added surface nodes (dual-graph architecture) |
| **Dependencies** | Stage 4: `graph_update_output` |
| **Immutable Inputs** | `session_id` |
| **Reads** | `graph_update_output.nodes_added`, `turn_number`, `methodology` |
| **Writes** | `slot_discovery_output` (SlotDiscoveryOutput contract) |
| **Side Effects** | INSERT canonical_slots, INSERT surface_to_slot_mapping, UPDATE canonical_slots.support_count, LLM call for slot proposal |
| **Feature Flag** | `enable_canonical_slots` in Settings (if disabled, stage is skipped entirely) |

**Contract Output**: `SlotDiscoveryOutput`

```python
slots_created: int           # New canonical slots created this turn
slots_updated: int           # Existing slots that received new mappings
mappings_created: int        # Surface nodes mapped to canonical slots
timestamp: datetime           # When slot discovery was performed (auto-set)
```

**Input Requirements:**
- `PipelineContext.graph_update_output.nodes_added` (from Stage 4) - validates Stage 4 completed
- `PipelineContext.turn_number`, `methodology` - for logging

**Error Handling** (fail-fast per ADR-009):
- No `nodes_added`: skip LLM call, return `SlotDiscoveryOutput` with zeros (only graceful skip)
- `graph_update_output` is None: raise `RuntimeError` (pipeline contract violation)
- LLM failure: exception propagates, pipeline fails for this turn

**Reference**: Phase 2 (Dual-Graph Architecture), bead yuhv

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
saturation_metrics: Optional[SaturationMetrics]  # Saturation indicators (yield, quality signals)
canonical_graph_state: Optional[CanonicalGraphState]  # Canonical graph state (deduplicated concepts)
```

**Note**: `graph_state` is refreshed by querying the database for current metrics. `saturation_metrics` are computed from graph yield and quality signals for ContinuationStage. `canonical_graph_state` provides dual-graph architecture metrics.

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
node_tracker: NodeStateTracker        # Node state tracking for node-level signals
```

**Contract Output**: `StrategySelectionOutput`

```python
strategy: str                          # Selected strategy
focus: Optional[Dict[str, Any]]        # Focus target with focus_node_id when strategy selects a node
selected_at: datetime                # When strategy was selected (auto-set)
signals: Optional[Dict[str, Any]]      # Methodology-specific signals (namespaced)
strategy_alternatives: List[tuple[str, str, float]]  # (strategy, node_id, score) tuples
```

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
should_continue: bool     # Whether to continue interview
focus_concept: str       # Concept to focus on next turn
reason: str              # Reason for continuation decision
turns_remaining: int     # Number of turns remaining
timestamp: datetime        # When continuation decision was made (auto-set)
```

---

### Stage 8: QuestionGenerationStage

**File**: `src/services/turn_pipeline/stages/question_generation_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Generate follow-up question or closing message |
| **Dependencies** | Stage 6: `strategy_selection_output`, Stage 7: `continuation_output` |
| **Immutable Inputs** | None |
| **Reads** | `should_continue`, `focus_concept`, `recent_utterances`, `graph_state`, `strategy` |
| **Side Effects** | LLM API call |

**Contract Output**: `QuestionGenerationOutput`

```python
question: str              # Generated question
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
system_utterance: Utterance  # Full saved utterance record
question_text: str         # Question text that was saved
timestamp: datetime         # When response was saved (auto-set)
```

---

### Stage 10: ScoringPersistenceStage

**File**: `src/services/turn_pipeline/stages/scoring_persistence_stage.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Save scoring results to database and update session state (including focus history) |
| **Dependencies** | Stage 6: `strategy_selection_output` |
| **Immutable Inputs** | `turn_number` |
| **Reads** | `strategy_selection_output`, `context_loading_output` (for focus_history), `node_tracker` |
| **Writes** | `scoring_persistence_output` (ScoringPersistenceOutput contract) |
| **Side Effects** | UPDATE session state (turn_count, velocity, focus_history), INSERT scoring records |

**Contract Output**: `ScoringPersistenceOutput`

```python
turn_number: int                # Turn number for scoring
strategy: str                  # Strategy that was selected
depth_score: float             # Depth metric from graph state
saturation_score: float         # Saturation metric from graph state
has_methodology_signals: bool   # Whether methodology signals were saved
timestamp: datetime              # When scoring was persisted (auto-set)
```

**Focus History Appending**:

Each turn, `ScoringPersistenceStage._update_turn_count()` appends a `FocusEntry` to the session's `focus_history`:

```python
# Build focus entry for this turn
focus = context.strategy_selection_output.focus  # dict or None
focus_node_id = focus.get("focus_node_id") if focus else None

# Look up node label from node_tracker if node_id is available
node_label = ""
if focus_node_id and context.node_tracker:
    node_state = await context.node_tracker.get_state(focus_node_id)
    if node_state:
        node_label = node_state.label

entry = FocusEntry(
    turn=context.turn_number,
    node_id=focus_node_id or "",
    label=node_label,
    strategy=context.strategy,
)

# Append to existing history loaded at turn start
updated_history = list(context.context_loading_output.focus_history) + [entry]

# Include updated_history in SessionState constructor
updated_state = SessionState(..., focus_history=updated_history)
```

**Important**: Turns with no node focus (empty graph, turn 1) still create an entry with empty `node_id`/`label`. The strategy column alone is informative, and gaps in the sequence make the trace harder to read.

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
    scoring: dict                      # strategy_id, score, reasoning
    strategy_selected: str             # Selected strategy name
    next_question: str                 # Generated question
    should_continue: bool              # Whether interview continues
    latency_ms: int = 0                # Pipeline execution time

    # Observability
    signals: Optional[Dict[str, Any]] = None           # Raw methodology signals
    strategy_alternatives: Optional[List[Dict[str, Any]]] = None # All scored alternatives

    # Termination (optional)
    termination_reason: Optional[str] = None  # Reason for termination

    # Dual-graph output (optional)
    canonical_graph: Optional[Dict[str, Any]] = None  # {slots, edges, metrics}
    graph_comparison: Optional[Dict[str, Any]] = None  # {node_reduction_pct, edge_aggregation_ratio}
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
| `signals` | StrategySelectionOutput | Raw methodology signals from signal pools |
| `strategy_alternatives` | StrategySelectionOutput | All scored strategy alternatives |
| `termination_reason` | ContinuationOutput | Reason for termination when should_continue=False |
| `canonical_graph` | StateComputationOutput | Canonical/deduplicated graph {slots, edges, metrics} |
| `graph_comparison` | Pipeline | Surface vs canonical comparison {node_reduction_pct, edge_aggregation_ratio} |

### Termination Reasons

The `termination_reason` field is populated when `should_continue=False`:

| Reason | Description | Detection |
|--------|-------------|-----------|
| `Maximum turns reached` | Interview reached configured `max_turns` limit | `turn_number >= max_turns` |
| `Closing strategy selected` | Closing strategy was explicitly selected | `strategy == "close"` |
| `graph_saturated` | 6+ consecutive turns with zero yield (no new nodes/edges) | `saturation.consecutive_low_info >= 6` |
| `quality_degraded` | 6+ consecutive shallow responses detected | `saturation.consecutive_shallow >= 6` |
| `depth_plateau` | Graph max_depth hasn't increased in 6 consecutive turns | `saturation.consecutive_depth_plateau >= 6` |
| `all_nodes_exhausted` | All explored nodes have no more content to yield | All nodes have `turns_since_last_yield >= 3` |
| `saturated` | Generic saturation (fallback when is_saturated=True but no specific condition met) | `saturation.is_saturated == True` |

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
