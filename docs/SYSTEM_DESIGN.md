# Interview System v2 - System Design

> **Purpose**: Narrative documentation of the interview system architecture, written for technical articles and comprehensive understanding.
> **Related**: [Pipeline Contracts](./pipeline_contracts.md) | [Data Flow Paths](./data_flow_paths.md)

## Table of Contents

- [Overview](#overview)
- [Core Architecture](#core-architecture)
- [The Turn Pipeline](#the-turn-pipeline)
- [Signal Pools Architecture](#signal-pools-architecture)
- [Concept-Driven Coverage](#concept-driven-coverage)
- [Methodology-Centric Design](#methodology-centric-design)
- [Knowledge Graph State](#knowledge-graph-state)
- [Policy-Driven Follow-Up Question Generation](#policy-driven-follow-up-question-generation)
- [LLM Integration](#llm-integration)

---

## Overview

The Interview System v2 is a knowledge-graph-based conversational research system that conducts semi-structured interviews through adaptive questioning. At its core, the system uses a **12-stage turn processing pipeline** that transforms user input into follow-up questions while building a knowledge graph of the conversation.

### Key Design Principles

1. **Pipeline Pattern**: Each turn flows through 12 stages with well-defined contracts between stages
2. **Dual-Graph Architecture**: Surface graph preserves extraction fidelity while canonical graph provides stable, deduplicated signals
3. **Signal Pools**: Strategy selection uses namespaced signals from multiple data sources (graph.*, llm.*, temporal.*, meta.*, graph.node.*)
4. **Methodology-Centric**: Interview behavior driven by pluggable YAML methodology configurations
5. **Knowledge Graph**: All extracted concepts and relationships stored as graph structure with traceability to source utterances
6. **Feature Flags**: Optional features (SRL preprocessing, canonical slots, question self-selection) use `enable_*` flags for graceful skip
7. **Fail-Fast**: Errors raise immediately rather than degrading silently

### High-Level Architecture

```
User Input -> Turn Pipeline (12 stages) -> Knowledge Graph -> Strategy Selection -> Question Generation -> User Response
                |
         [SRL Preprocessing] -> [Extraction] -> [Graph Update] -> [Slot Discovery]
                |
         [State Computation] -> [Strategy Selection] -> [Continuation Check]
                |
         [Question Generation] -> [Response Saving] -> [Scoring Persistence]
```

### Pipeline Stages

| Stage | Name | Purpose |
|-------|------|---------|
| 1 | ContextLoadingStage | Load session metadata and graph state |
| 2 | UtteranceSavingStage | Persist user utterance to database |
| 2.5 | SRLPreprocessingStage | Linguistic parsing (optional via `enable_srl`) |
| 3 | ExtractionStage | Extract concepts and relationships via LLM |
| 4 | GraphUpdateStage | Update surface knowledge graph with deduplication |
| 4.5 | SlotDiscoveryStage | Map surface nodes to canonical slots (optional via `enable_canonical_slots`) |
| 5 | StateComputationStage | Refresh graph state and compute saturation metrics |
| 6 | StrategySelectionStage | Signal Pools -> ranked strategy selection |
| 7 | ContinuationStage | Determine if interview should continue |
| 8 | QuestionGenerationStage | Generate follow-up question via LLM |
| 9 | ResponseSavingStage | Persist system response to database |
| 10 | ScoringPersistenceStage | Save scoring history and update session state |

### Key Configuration

- **SRL Preprocessing**: `enable_srl: bool = True` - Linguistic analysis via spaCy
- **Canonical Slots**: `enable_canonical_slots: bool = True` - Dual-graph deduplication
- **Similarity Thresholds**: Surface 0.80, Canonical 0.60
- **LLM Providers**: Three-client architecture (extraction: anthropic, scoring: kimi, generation: anthropic)
- **Interview Phases**: Exploratory, Focused, Closing with configurable turn boundaries

---

## Core Architecture

The Interview System v2 uses a **Two-Layer Design** that separates domain concepts from interview methodologies, combined with a **Dual-Graph Architecture** that maintains both surface-level fidelity and canonical abstraction.

### Two-Layer Design

The system separates **what to explore** (concepts) from **how to explore it** (methodologies):

```
+-------------------------------------------------------------+
|  CONCEPT LAYER (Domain Content)                             |
|  +-------------+  +-------------+  +-------------+         |
|  |  coffee     |  |  oat_milk   |  |  electric   |         |
|  |  _jtbd_v2   |  |    _v2      |  |   _vehicle  |         |
|  +-------------+  +-------------+  +-------------+         |
|       Defines domain entities and their attributes          |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  METHODOLOGY LAYER (Interview Logic)                        |
|  +-----------------+  +-----------------+  +-------------+ |
|  | jobs_to_be_done |  | means_end_chain |  |  critical   | |
|  |     (JTBD)      |  |     (MEC)       |  |  _incident  | |
|  +-----------------+  +-----------------+  +-------------+ |
|       Defines node types, strategies, signals, questions    |
+-------------------------------------------------------------+
```

**Key Insight**: The same concept (e.g., "electric vehicle") can be interviewed using different methodologies (JTBD, Means-End Chain, Critical Incident) without changing the concept definition. This enables methodology comparison and A/B testing.

### Dual-Graph Architecture

The system maintains two parallel graph structures:

#### Surface Graph (Conversation Fidelity)
- **KGNode** / **KGEdge**: Raw extracted concepts and relationships
- Preserves respondent language exactly as spoken
- Deduplication via exact label match + semantic similarity (threshold: 0.80)
- Full provenance: every node/edge linked to source utterance IDs

#### Canonical Graph (Stable Concepts)
- **CanonicalSlot** / **CanonicalEdge**: Abstracted latent concepts
- Handles language variation ("fast car" = "quick vehicle" = "speed_performance")
- LLM-proposed groupings with embedding-based merging (threshold: 0.60)
- Promotion lifecycle: candidate -> active (min support: 2 nodes)

```
+-----------------------------------------------------------------+
|                    DUAL-GRAPH ARCHITECTURE                       |
+-----------------------------------------------------------------+
|                                                                  |
|   SURFACE GRAPH (Fidelity)        CANONICAL GRAPH (Stability)   |
|   +---------------------+         +---------------------+       |
|   |  "fast car"         |-------->|  speed_performance  |       |
|   |  "quick vehicle"    |-------->|    (active slot)    |       |
|   |  "rapid automobile" |-------->|  support_count: 3   |       |
|   +---------------------+         +---------------------+       |
|            |                               |                     |
|            v                               v                     |
|   +---------------------+         +---------------------+       |
|   |  Surface Edges      |-------->|  Canonical Edges    |       |
|   |  (utterance-level)  |         |  (aggregated)       |       |
|   +---------------------+         +---------------------+       |
|                                                                  |
|   Purpose: Traceability           Purpose: Signal Stability     |
|   - Every node linked to          - Robust to language          |
|     source utterance                variation                   |
|   - Exact respondent words        - Consistent strategy         |
|     preserved                       targeting                   |
|                                                                  |
+-----------------------------------------------------------------+
```

### Pipeline Context and Contracts

The **PipelineContext** (`src/services/turn_pipeline/context.py`) carries state through all 12 pipeline stages using formal Pydantic contracts:

| Stage | Contract | Purpose |
|-------|----------|---------|
| 1 | ContextLoadingOutput | Session metadata, turn number, history |
| 2 | UtteranceSavingOutput | Persisted user utterance |
| 2.5 | SrlPreprocessingOutput | Discourse relations, SRL frames (optional) |
| 3 | ExtractionOutput | Extracted concepts and relationships |
| 4 | GraphUpdateOutput | Nodes and edges added to surface graph |
| 4.5 | SlotDiscoveryOutput | Canonical slot mappings (dual-graph) |
| 5 | StateComputationOutput | GraphState + CanonicalGraphState |
| 6 | StrategySelectionOutput | Selected strategy, focus, signals |
| 7 | ContinuationOutput | should_continue flag |
| 8 | QuestionGenerationOutput | Generated next question |
| 9 | ResponseSavingOutput | Persisted system utterance |
| 10 | ScoringPersistenceOutput | Scoring metrics |

**Key Design Principle**: Contracts are the single source of truth. Convenience properties on PipelineContext derive from contracts but never duplicate state. Pipeline ordering is enforced through RuntimeError on premature access.

### Key Domain Models

#### Knowledge Graph Models (`src/domain/models/knowledge_graph.py`)

**KGNode**: Surface-level concept with:
- `label`: Exact text as extracted
- `node_type`: Methodology-defined type (e.g., attribute, consequence, value)
- `source_utterance_ids`: Provenance chain
- `stance`: Sentiment polarity (-1/0/+1)
- `embedding`: Serialized vector for semantic dedup

**GraphState**: Session-level aggregated metrics:
- `node_count` / `edge_count`: Basic statistics
- `depth_metrics`: Longest chain analysis (max_depth, longest_chain_path)
- `saturation_metrics`: Termination indicators (consecutive_low_info, is_saturated)
- `current_phase`: exploratory -> focused -> closing progression
- `strategy_history`: deque(maxlen=30) for diversity tracking

#### Canonical Graph Models (`src/domain/models/canonical_graph.py`)

**CanonicalSlot**: Stable latent concept with:
- `slot_name`: LLM-generated canonical name (e.g., "energy_stability")
- `node_type`: Preserved from surface nodes for type-aware processing
- `status`: candidate or active
- `support_count`: Number of surface nodes mapped
- `embedding`: Serialized numpy vector for similarity matching

**CanonicalGraphState**: Parallel to GraphState:
- `concept_count`: Active slots only (candidates excluded)
- `orphan_count`: Active slots with no canonical edges
- `avg_support`: Average surface nodes per slot (richness measure)
- `max_depth`: Longest canonical chain

### Service Responsibilities

#### GraphService (`src/services/graph_service.py`)
- Converts extraction results to graph nodes/edges
- Three-step deduplication: exact match -> semantic similarity -> create new
- Cross-turn edge resolution (links nodes from prior turns)
- **Edge aggregation**: Maps surface edges to canonical edges via slot mappings

#### CanonicalSlotService (`src/services/canonical_slot_service.py`)
- **Slot discovery**: Batched LLM call proposing groupings across all node types
- **Embedding similarity**: Merges near-duplicates and grammatical variants (lemmatization)
- **Promotion logic**: Candidate -> active when support_count >= threshold
- **Batch limiting**: Max 8 nodes per LLM call to avoid timeouts

### Configuration-Driven Behavior

All configurable values live in YAML, not code:

```
config/
├── concepts/              # Domain entities (what to explore)
│   ├── coffee_jtbd_v2.yaml
│   └── oat_milk_v2.yaml
├── methodologies/         # Interview logic (how to explore)
│   ├── jobs_to_be_done.yaml
│   ├── means_end_chain.yaml
│   └── critical_incident.yaml
└── personas/              # Synthetic respondent profiles
    ├── skeptical_analyst.yaml
    └── ...
```

**Feature Flags** (in `src/core/config.py`):
- `enable_srl`: Semantic Role Labeling preprocessing (Stage 2.5)
- `enable_canonical_slots`: Dual-graph architecture (Stage 4.5)
- `surface_similarity_threshold`: 0.80 for surface dedup
- `canonical_similarity_threshold`: 0.60 for slot merging
- `canonical_min_support_nodes`: 2 for slot promotion

---

## The Turn Pipeline

The turn pipeline is the core processing engine that transforms each user input into a system response. It implements a **12-stage pipeline** (10 base stages + 2 optional stages) with formal contracts between stages.

### Pipeline Architecture

```
User Input -> [12 Stages] -> Next Question
                  |
         Knowledge Graph (accumulating)
```

Each stage has a single responsibility and communicates through a shared `PipelineContext`. The pipeline uses **contract-based state accumulation** (ADR-010): each stage produces a typed Pydantic output model that becomes the single source of truth for downstream stages.

### PipelineContext Structure

The `PipelineContext` (in `src/services/turn_pipeline/context.py`) accumulates state through the pipeline:

```python
@dataclass
class PipelineContext:
    # Input parameters (immutable)
    session_id: str
    user_input: str

    # Service references
    node_tracker: Optional[NodeStateTracker]

    # Stage output contracts (accumulated by each stage)
    context_loading_output: Optional[ContextLoadingOutput] = None      # Stage 1
    utterance_saving_output: Optional[UtteranceSavingOutput] = None    # Stage 2
    srl_preprocessing_output: Optional[SrlPreprocessingOutput] = None  # Stage 2.5
    extraction_output: Optional[ExtractionOutput] = None               # Stage 3
    graph_update_output: Optional[GraphUpdateOutput] = None            # Stage 4
    slot_discovery_output: Optional[SlotDiscoveryOutput] = None        # Stage 4.5
    state_computation_output: Optional[StateComputationOutput] = None  # Stage 5
    strategy_selection_output: Optional[StrategySelectionOutput] = None # Stage 6
    continuation_output: Optional[ContinuationOutput] = None           # Stage 7
    question_generation_output: Optional[QuestionGenerationOutput] = None # Stage 8
    response_saving_output: Optional[ResponseSavingOutput] = None      # Stage 9
    scoring_persistence_output: Optional[ScoringPersistenceOutput] = None # Stage 10
```

Convenience properties (e.g., `context.strategy`, `context.graph_state`) derive from these contracts for backward compatibility while maintaining the contract as the source of truth.

### The 12 Stages

| # | Stage | File | Purpose | Type |
|---|-------|------|---------|------|
| 1 | **ContextLoadingStage** | `stages/context_loading_stage.py` | Load session metadata, turn number, conversation history, strategy history | Base |
| 2 | **UtteranceSavingStage** | `stages/utterance_saving_stage.py` | Persist user input to database | Base |
| 2.5 | **SRLPreprocessingStage** | `stages/srl_preprocessing_stage.py` | Extract linguistic structure (discourse relations, SRL frames) | Optional |
| 3 | **ExtractionStage** | `stages/extraction_stage.py` | Extract concepts and relationships from user input | Base |
| 4 | **GraphUpdateStage** | `stages/graph_update_stage.py` | Add extracted data to knowledge graph with deduplication | Base |
| 4.5 | **SlotDiscoveryStage** | `stages/slot_discovery_stage.py` | Map surface nodes to canonical slots (dual-graph architecture) | Optional |
| 5 | **StateComputationStage** | `stages/state_computation_stage.py` | Refresh graph state metrics, compute saturation | Base |
| 6 | **StrategySelectionStage** | `stages/strategy_selection_stage.py` | Select strategy using joint strategy-node scoring | Base |
| 7 | **ContinuationStage** | `stages/continuation_stage.py` | Decide if interview should continue | Base |
| 8 | **QuestionGenerationStage** | `stages/question_generation_stage.py` | Generate follow-up question | Base |
| 9 | **ResponseSavingStage** | `stages/response_saving_stage.py` | Persist system response to database | Base |
| 10 | **ScoringPersistenceStage** | `stages/scoring_persistence_stage.py` | Save scoring, update session state, persist LLM usage | Base |

**Optional Stage Control:**
- Stage 2.5 (SRL): Controlled by `enable_srl` config flag (default: True)
- Stage 4.5 (Slot Discovery): Controlled by `enable_canonical_slots` config flag (default: True)

### Stage Contracts

Each stage validates its dependencies and produces a formal contract output:

**Stage 1: ContextLoadingStage**
- Output: `ContextLoadingOutput` - methodology, concept_id, concept_name, turn_number, mode, max_turns, recent_utterances, strategy_history, recent_node_labels, velocity state, focus_history

**Stage 2: UtteranceSavingStage**
- Output: `UtteranceSavingOutput` - turn_number, user_utterance_id, user_utterance
- Side Effects: INSERT to utterances table

**Stage 2.5: SRLPreprocessingStage** (Optional)
- Output: `SrlPreprocessingOutput` - discourse_relations, srl_frames, discourse_count, frame_count
- Behavior: If disabled, produces empty output gracefully

**Stage 3: ExtractionStage**
- Output: `ExtractionOutput` - extraction (concepts/relationships), methodology, timestamp, concept_count, relationship_count
- Side Effects: LLM API call

**Stage 4: GraphUpdateStage**
- Output: `GraphUpdateOutput` - nodes_added, edges_added, node_count, edge_count
- Side Effects: INSERT/UPDATE to kg_nodes, kg_edges; updates NodeStateTracker

**Stage 4.5: SlotDiscoveryStage** (Optional)
- Output: `SlotDiscoveryOutput` - slots_created, slots_updated, mappings_created
- Side Effects: INSERT canonical_slots, INSERT surface_to_slot_mapping, LLM call for slot proposal

**Stage 5: StateComputationStage**
- Output: `StateComputationOutput` - graph_state, recent_nodes, computed_at, saturation_metrics, canonical_graph_state
- Computes: Fresh graph metrics, saturation indicators (zero yield, shallow responses, depth plateau)

**Stage 6: StrategySelectionStage**
- Output: `StrategySelectionOutput` - strategy, focus, selected_at, signals, node_signals, strategy_alternatives, generates_closing_question, focus_mode, score_decomposition
- Validates: Graph state freshness via `computed_at` timestamp

**Stage 7: ContinuationStage**
- Output: `ContinuationOutput` - should_continue, focus_concept, reason, turns_remaining
- Reads: saturation_metrics from StateComputationOutput

**Stage 8: QuestionGenerationStage**
- Output: `QuestionGenerationOutput` - question, strategy, focus, has_llm_fallback
- Side Effects: LLM API call (for fallback)

**Stage 9: ResponseSavingStage**
- Output: `ResponseSavingOutput` - turn_number, system_utterance_id, system_utterance, question_text
- Side Effects: INSERT to utterances table

**Stage 10: ScoringPersistenceStage**
- Output: `ScoringPersistenceOutput` - turn_number, strategy, depth_score, saturation_score, has_methodology_signals
- Side Effects: INSERT to scoring_history, UPDATE session state (turn_count, velocity, focus_history), persist LLM usage

### TurnResult Output

The pipeline returns a `TurnResult` dataclass (in `src/services/turn_pipeline/result.py`):

```python
@dataclass
class TurnResult:
    turn_number: int
    extracted: dict                    # concepts, relationships
    graph_state: dict                  # node_count, edge_count, depth_achieved
    scoring: dict                      # depth, saturation
    strategy_selected: str
    next_question: str
    should_continue: bool
    latency_ms: int = 0

    # Observability
    signals: Optional[Dict[str, Any]] = None
    strategy_alternatives: Optional[List[Dict[str, Any]]] = None
    termination_reason: Optional[str] = None

    # Dual-graph output
    canonical_graph: Optional[Dict[str, Any]] = None
    graph_comparison: Optional[Dict[str, Any]] = None

    # Per-turn changes
    nodes_added: List[Dict[str, Any]] = field(default_factory=list)
    edges_added: List[Dict[str, Any]] = field(default_factory=list)
    saturation_metrics: Optional[Dict[str, Any]] = None
    node_signals: Optional[Dict[str, Dict[str, Any]]] = None
    score_decomposition: Optional[List[Any]] = None
```

### Continuation and Termination Conditions

The `ContinuationStage` (Stage 7) determines if the interview should continue:

**Hard Stops (always checked):**
- `turn_number >= max_turns` - Maximum turns reached
- `generates_closing_question=True` - Closing strategy selected

**Saturation Checks (after MIN_TURN_FOR_SATURATION=5 or late stage):**
- **graph_saturated**: 5+ consecutive turns with zero yield (no new nodes/edges)
- **quality_degraded**: 6+ consecutive shallow responses
- **depth_plateau**: 6+ turns at same max_depth (only during zero-yield turns)
- **all_nodes_exhausted**: All explored nodes have `turns_since_last_yield >= 3`

**Termination Reasons:**
| Reason | Condition |
|--------|-----------|
| `Maximum turns reached` | `turn_number >= max_turns` |
| `Closing strategy selected` | Strategy with `generates_closing_question=true` |
| `graph_saturated` | `consecutive_low_info >= 5` |
| `quality_degraded` | `consecutive_shallow >= 6` |
| `depth_plateau` | `consecutive_depth_plateau >= 6` |
| `all_nodes_exhausted` | All nodes exhausted |
| `saturated` | Generic saturation fallback |

---

## Signal Pools Architecture

### Signal Pool Overview

The system uses methodology-based signal detection with YAML configuration. Signal pools enable flexible strategy selection by collecting signals from multiple data sources:

```
+-------------------------------------------------------------+
|              GlobalSignalDetectionService                   |
|  - Uses ComposedSignalDetector for global signals           |
|  - Dependency-ordered detection (topological sort)          |
|  - Batches LLM signals into single API call                 |
+-------------------------------------------------------------+
                            |
        +-------------------+-------------------+---------------+
        |                   |                   |               |
        v                   v                   v               v
+--------------+   +--------------+   +--------------+ +--------------+
| Graph Pool   |   |  LLM Pool    |   |Temporal Pool | |Technique Pool|
|              |   |              |   |              | |              |
|Global:       |   | - response_  |   | - strategy_  | |Node-level:   |
| - node_count |   |   depth      |   |   repetition | | - strategy_  |
| - max_depth  |   | - valence    |   | - turns_     | |   repetition |
| - chain_comp |   | - certainty  |   |   since_     | |              |
| - canonical_*|   | - specificity|   |   strategy   | +--------------+
|              |   | - engagement |   |   change     |
|Node-level:   |   | - intellectual|  |              |
| - exhausted  |   |   engagement |   |              |
| - yield_stag |   | - global_    |   |              |
| - focus_     |   |   trend      |   |              |
|   streak     |   |              |   |              |
| - recency_   |   |              |   |              |
|   score      |   |              |   |              |
| - is_orphan  |   |              |   |              |
| - edge_count |   |              |   |              |
| - has_outgoing|  |              |   |              |
+--------------+   +--------------+   +--------------+
        |                   |                   |
        +-------------------+-------------------+
                            |
                            v
                    +--------------+
                    |  Meta Pool   |
                    |              |
                    |Global:       |
                    | - interview_ |
                    |   phase      |
                    | - conversation|
                    |   saturation |
                    | - canonical  |
                    |   saturation |
                    |              |
                    |Node-level:   |
                    | - node.opportunity|
                    +--------------+
```

### Signal Namespacing

All signals use dot-notation namespacing to prevent collisions:

| Pool | Namespace | Example Signals |
|------|-----------|-----------------|
| **Graph (Global)** | `graph.*` | node_count, max_depth, orphan_count, chain_completion.ratio, chain_completion.has_complete, canonical_concept_count, canonical_edge_density, canonical_exhaustion_score |
| **Graph (Node)** | `graph.node.*` | exhausted, exhaustion_score, yield_stagnation, focus_streak, recency_score, is_current_focus, is_orphan, edge_count, has_outgoing |
| **LLM** | `llm.*` | response_depth (categorical: surface/shallow/moderate/deep), valence (float [0,1]), certainty (float [0,1]), specificity (float [0,1]), engagement (float [0,1]), intellectual_engagement (float [0,1]), global_response_trend (deepening/stable/shallowing/fatigued) |
| **Temporal** | `temporal.*` | strategy_repetition_count, turns_since_strategy_change |
| **Meta (Global)** | `meta.*` | interview.phase, conversation.saturation, canonical.saturation |
| **Meta (Node)** | `meta.node.*` | opportunity (exhausted/probe_deeper/fresh) |
| **Technique (Node)** | `technique.node.*` | strategy_repetition (none/low/medium/high) |

### YAML Configuration Flow

Methodology YAML files drive signal detection and strategy selection:

1. **MethodologyRegistry.load()** parses YAML into MethodologyConfig
2. **config.signals** -> GlobalSignalDetectionService creates ComposedSignalDetector
3. **config.strategies** -> rank_strategy_node_pairs for scoring
4. **config.phases** -> Phase weights and bonuses applied during scoring

The flow combines:
- Global signals from ComposedSignalDetector
- Node signals from NodeSignalDetectionService
- Phase modifiers (weights multiplicative, bonuses additive)
- Joint strategy-node scoring for optimal (strategy, node) pair selection

### Fresh LLM Signals

**Critical Design Decision**: LLM signals are **fresh per response** - computed every turn, no cross-response caching. This ensures:
- Signals reflect the current conversation state
- No stale signals from previous responses
- Accurate strategy selection

### Rubric-Based LLM Detection

LLM signals use rubric-based prompts to guide the LLM's assessment. The `LLMBatchDetector` loads rubric definitions from `src/signals/llm/prompts/signals.md` using indentation-based parsing:

**Rubric Structure**:
```markdown
response_depth: How much elaboration does the response provide?
    1 = Minimal or single-word answer, no development
    2 = Brief statement with no supporting detail
    3 = Moderate elaboration with some explanation or context
    4 = Detailed response with reasoning, examples, or multiple facets
    5 = Rich, layered response exploring the topic from multiple angles
```

**Parsing Method**:
- Signal headers: Start at column 0, contain `:`, not a comment
- Content lines: Indented, appended to current signal's rubric
- Example: `response_depth:` header followed by indented scale definitions

**Batch Detection**:
All 6 LLM signals (response_depth, specificity, certainty, valence, engagement, intellectual_engagement) are detected in a single API call via `LLMBatchDetector`. The prompt includes the interviewer's question (for context) and the respondent's answer, with rubrics injected to guide the LLM's scoring. The LLM returns structured JSON:

```json
{
  "response_depth": {"score": 4, "rationale": "Detailed response with examples"},
  "specificity": {"score": 4, "rationale": "Concrete details and named entities"},
  "certainty": {"score": 5, "rationale": "Confident statements with no hedging"},
  "valence": {"score": 4, "rationale": "Positive tone throughout"},
  "engagement": {"score": 5, "rationale": "Volunteered additional context unprompted"},
  "intellectual_engagement": {"score": 4, "rationale": "Causal reasoning with value expression present"}
}
```

**Signal Type Handling**:
- **Categorical** (response_depth): Returns integer 1-5, mapped to string values (surface/shallow/moderate/deep), matched via string equality in strategy weights
- **Continuous** (others): Returns integer 1-5, normalized to float [0,1] via (score-1)/4, matched via threshold binning (.low/.mid/.high) in strategy weights

**LLM Signal Decorator**:
LLM signals are created using the `@llm_signal` decorator pattern for zero-boilerplate signal definition:
```python
@llm_signal(
    signal_name="llm.response_depth",
    rubric_key="response_depth",
    description="Assesses quantity of elaboration on a 1-5 scale",
)
class ResponseDepthSignal(BaseLLMSignal):
    pass  # Everything handled by decorator
```

### Node-Level Signals

Node-level signals enable per-node state tracking and joint strategy-node scoring.

Node-level signals use the `graph.node.*` namespace and are computed by `NodeSignalDetector` subclasses:

| Signal | Description | Type | Detector |
|--------|-------------|------|----------|
| `graph.node.exhausted` | Boolean: is node exhausted | bool | `NodeExhaustedSignal` |
| `graph.node.exhaustion_score` | Continuous: 0.0 (fresh) to 1.0 (exhausted) | float | `NodeExhaustionScoreSignal` |
| `graph.node.yield_stagnation` | Boolean: 3+ turns without yield | bool | `NodeYieldStagnationSignal` |
| `graph.node.focus_streak` | Categorical: none/low/medium/high | str | `NodeFocusStreakSignal` |
| `graph.node.is_current_focus` | Boolean: is this the current focus | bool | `NodeIsCurrentFocusSignal` |
| `graph.node.recency_score` | Continuous: 1.0 (current) to 0.0 (20+ turns ago) | float | `NodeRecencyScoreSignal` |
| `graph.node.is_orphan` | Boolean: node has no edges | bool | `NodeIsOrphanSignal` |
| `graph.node.edge_count` | Integer: total edges (incoming + outgoing) | int | `NodeEdgeCountSignal` |
| `graph.node.has_outgoing` | Boolean: node has outgoing edges | bool | `NodeHasOutgoingSignal` |
| `technique.node.strategy_repetition` | Categorical: none/low/medium/high | str | `NodeStrategyRepetitionSignal` (technique pool) |

**Node Signal Architecture:**

All node signal detectors inherit from `NodeSignalDetector` base class (`src/signals/graph/node_base.py`), which provides:
- Access to `NodeStateTracker` for per-node state
- Automatic iteration over all tracked nodes via `_get_all_node_states()`
- Helper method `_calculate_shallow_ratio()` for response depth analysis
- Consistent return type: `Dict[node_id, signal_value]`

### Meta Signals

Meta signals provide higher-level abstractions by combining multiple lower-level signals:

**Node Opportunity Signal (`meta.node.opportunity`):**

Combines node-level signals to determine what action should be taken for each node:
- **exhausted**: Node is exhausted (no yield, shallow responses, persistent focus)
- **probe_deeper**: Deep responses but no yield (extraction opportunity)
- **fresh**: Node has opportunity for exploration

Computed by `NodeOpportunitySignal` using:
- `graph.node.exhausted`
- `graph.node.focus_streak`
- `llm.response_depth`

**Interview Phase Signal (`meta.interview.phase`):**

Detects the current interview phase based on turn number with automatically calculated proportional boundaries:
- **early**: ~10% of max_turns (minimum 2 turns)
- **mid**: Between early and late phases
- **late**: Final 2 turns reserved for validation

Phase boundaries are calculated proportionally from `max_turns`:
```python
early_max_turns = max(2, round(max_turns * 0.10))
mid_max_turns = max_turns - 2
```

Computed by `InterviewPhaseSignal` using context.turn_number and context.max_turns.

**Conversation Saturation Signal (`meta.conversation.saturation`):**

Measures extraction yield ratio: current surface node yield vs peak. Formula: `saturation = 1.0 - min(current_delta / peak, 1.0)`. Output: 0.0 (matching peak) to 1.0 (zero extraction). Indicates when respondent's answers are yielding fewer new nodes.

**Canonical Saturation Signal (`meta.canonical.saturation`):**

Measures canonical novelty ratio: new canonical slots / new surface nodes. Formula: `saturation = 1.0 - min(canonical_delta / surface_delta, 1.0)`. Output: 0.0 (all new themes) to 1.0 (pure deduplication). Indicates when new surface nodes are thematically redundant.

### Joint Strategy-Node Scoring

The system implements joint strategy-node scoring (D1 architecture) for focus selection.

Instead of selecting a strategy first and then a node, the system scores all (strategy, node) pairs:

```python
def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],
    node_tracker: NodeStateTracker,
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
) -> tuple[List[Tuple[StrategyConfig, str, float]], List[ScoredCandidate]]:
    """
    Rank (strategy, node) pairs by joint score.

    For each (strategy, node) pair:
    1. Merge global + node signals (node signals take precedence)
    2. Score strategy using combined signals (with per-signal decomposition)
    3. Apply phase weight multiplier if available
    4. Apply phase bonus additively if available
    5. Sort all pairs by score descending

    Returns: (ranked_pairs, decomposition) where decomposition contains
    per-signal contribution breakdown for every candidate (simulation observability)
    """
```

**Scoring Formula**:
```python
# Base score from signal weights
base_score = score_strategy(strategy, combined_signals)

# Apply phase weight multiplier if available
multiplier = phase_weights.get(strategy.name, 1.0)

# Apply phase bonus additively if available
bonus = phase_bonuses.get(strategy.name, 0.0)

# Final score: (base score multiplier) + bonus
final_score = (base_score * multiplier) + bonus
```

**Signal Weight Partitioning**:
Signal weights are automatically partitioned into global and node-scoped weights based on namespace prefixes:
- `graph.node.*`, `technique.node.*`, `meta.node.*` -> node_weights
- All others -> strategy_weights

**Benefits:**
- Strategy selection considers node-specific context
- Natural integration with node exhaustion (exhausted nodes get low scores)
- Phase-based weights (multiplicative) and bonuses (additive) adjust strategy preferences per interview phase
- Single scoring pass for both strategy and node selection
- Returns alternatives list for debugging: `[(strategy, node_id, score), ...]`
- Full score decomposition available for simulation observability via `ScoredCandidate` dataclass

---

## Concept-Driven Coverage

Concepts define **what** to explore in an interview—the research topic and objectives—while remaining decoupled from **how** to explore it (the methodology). This separation enables the same concept to be studied using different methodologies (Means-End Chain, Jobs-to-be-Done, Critical Incident, etc.) without changing the core topic definition.

### Concept Structure

Concepts are defined in YAML files located in `config/concepts/` and loaded via `src/core/concept_loader.py`. The Pydantic models in `src/domain/models/concept.py` define the structure:

```python
class Concept(BaseModel):
    id: str                    # Unique identifier (e.g., "coffee_jtbd")
    name: str                  # Human-readable name
    methodology: str           # Which methodology to use
    context: ConceptContext    # Research brief context
    elements: List[ConceptElement]  # Legacy: always empty for exploratory interviews

class ConceptContext(BaseModel):
    objective: Optional[str]   # Primary research objective
```

**Example Concept YAML** (`config/concepts/headphones_mec.yaml`):
```yaml
id: headphones_mec
name: "Wireless Headphones Means-End Chain"
methodology: means_end_chain

objective: "Explore how people evaluate wireless headphones, focusing on which attributes drive their purchase decisions and what values those attributes serve"
```

### Concept Loading and Caching

The `load_concept()` function in `src/core/concept_loader.py` loads concept definitions with module-level caching:

```python
def load_concept(name: str, concepts_dir: Optional[Path] = None) -> Concept:
    """Load concept configuration from YAML file with caching."""
    if name in _cache:
        return _cache[name]
    # ... load and validate from config/concepts/{name}.yaml
```

- Concepts are cached after first load for performance
- The loader validates required fields (`id`, `name`, `methodology`)
- The `objective` field can be at root level or nested under `context`

### How Concepts Drive Interview Coverage

**1. Opening Question Generation**

The concept's `objective` field drives the opening question via `get_opening_question_user_prompt()` in `src/llm/prompts/question.py`:

```python
def get_opening_question_user_prompt(objective: str, methodology: Optional[MethodologySchema] = None) -> str:
    return f"""You are an experienced qualitative moderator starting an in-depth interview.

**Interview objective (for you):**
{objective}

**Methodology (for you):**
{name}: {goal}

**Method-specific opening guidance:**
{opening_bias}"""
```

The objective provides focused guidance to the LLM on what specific aspect of the concept to explore, while the methodology's `opening_bias` (from YAML config) guides the style of questioning.

**2. Extraction Context**

During the extraction stage (`src/services/turn_pipeline/stages/extraction_stage.py`), the concept is loaded and attached to the extraction service:

```python
if hasattr(context, "concept_id") and context.concept_id:
    self.extraction.concept_id = context.concept_id
    self.extraction.concept = load_concept(context.concept_id)
    self.extraction.element_alias_map = get_element_alias_map(self.extraction.concept)
```

The concept provides context for:
- Element linking (legacy feature for evaluative interviews)
- Cross-turn relationship bridging via existing node labels
- Methodology-appropriate extraction guidelines

**3. Question Generation Anchoring**

Throughout the interview, the concept name anchors questions to the research topic (in `src/services/turn_pipeline/stages/question_generation_stage.py`):

```python
next_question = await self.question.generate_question(
    focus_concept=focus_concept,
    recent_utterances=updated_utterances,
    graph_state=context.graph_state,
    recent_nodes=context.recent_nodes,
    strategy=strategy,
    topic=context.concept_name,  # Anchors questions to research topic
)
```

The topic anchoring instruction in `src/llm/prompts/question.py` ensures questions remain connected to the respondent's experience:

```python
if topic:
    topic_instruction = f"""
## Topic Anchoring:
This interview is about **{topic}**. While exploring deeper motivations and values,
ensure questions remain connected to the respondent's experience with {topic}.
"""
```

**4. API Access**

Concepts are exposed via REST API endpoints in `src/api/routes/concepts.py`:

- `GET /concepts` - List all available concepts with summary info
- `GET /concepts/{id}` - Get full concept configuration
- `GET /concepts/{id}/elements` - Get concept elements (legacy)

### Concept-Methodology Decoupling

The same concept can be studied with different methodologies by creating multiple YAML files with different `methodology` values. For example:

| Concept File | Methodology | Objective |
|--------------|-------------|-----------|
| `coffee_jtbd_legacy.yaml` | jobs_to_be_done | Understand the underlying jobs people are trying to accomplish when they consume coffee |
| `headphones_mec.yaml` | means_end_chain | Explore how people evaluate wireless headphones, focusing on attributes and values |

This decoupling allows researchers to:
- Compare insights across methodologies for the same topic
- Reuse concept definitions with different methodological lenses
- Maintain a library of research topics independent of interview techniques

### Legacy: Concept Elements

The `elements` field in `Concept` is a legacy feature from evaluative interviews with predefined topics. The current system is **exploratory only**—the elements list is always empty in practice. The field exists for backward compatibility with old concept formats and potential future evaluative interview support.

---

## Methodology-Centric Design

### Methodology Registry

The system uses a **methodology registry** with lazy-loading and validation:

```python
# src/methodologies/registry.py
class MethodologyRegistry:
    def __init__(self, config_dir: str | Path | None = None):
        # Default: config/methodologies relative to project root
        self.config_dir = Path(config_dir)
        self._cache: dict[str, MethodologyConfig] = {}

    def get_methodology(self, name: str) -> MethodologyConfig:
        """Get methodology configuration by name (loads on-demand)."""
        if name in self._cache:
            return self._cache[name]

        config_path = self.config_dir / f"{name}.yaml"
        with open(config_path) as f:
            data = yaml.safe_load(f)

        config = MethodologyConfig(
            name=method_data["name"],
            description=method_data.get("description", ""),
            signals=data.get("signals", {}),
            strategies=[...],  # StrategyConfig objects
            phases=phases,  # PhaseConfig objects if defined
        )

        self._validate_config(config, config_path)
        self._cache[name] = config
        return config

    def create_signal_detector(
        self, config: MethodologyConfig
    ) -> "ComposedSignalDetector":
        """Create a composed signal detector for a methodology."""
        signal_names = []
        for pool_signals in config.signals.values():
            signal_names.extend(pool_signals)
        return ComposedSignalDetector(signal_names)
```

**Global Access Pattern**:

```python
# src/methodologies/__init__.py
def get_registry() -> MethodologyRegistry:
    """Get the global methodology registry instance."""
    return _registry
```

### MethodologyStrategyService

The `MethodologyStrategyService` implements **two-stage strategy selection** using methodology configs:

1. **Stage 1**: Select strategy using global signals (graph, llm, temporal, meta)
2. **Stage 2**: Conditionally select node for strategies with `node_binding='required'`

```python
# src/services/methodology_strategy_service.py
class MethodologyStrategyService:
    def __init__(
        self,
        global_signal_service: Optional[GlobalSignalDetectionService] = None,
        node_signal_service: Optional[NodeSignalDetectionService] = None,
    ):
        self.methodology_registry = get_registry()
        self.global_signal_service = (
            global_signal_service or GlobalSignalDetectionService()
        )
        self.node_signal_service = node_signal_service or NodeSignalDetectionService()

    async def select_strategy_and_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Tuple[str, Optional[str], ...]:
        # 1. Load methodology config from YAML
        config = self.methodology_registry.get_methodology(methodology_name)

        # 2. Detect global signals
        global_signals = await self.global_signal_service.detect(...)

        # 3. Detect node-level signals
        node_signals = await self.node_signal_service.detect(...)

        # 4. Detect interview phase for phase weights/bonuses
        phase_result = await phase_signal.detect(...)
        current_phase = phase_result.get("meta.interview.phase", "early")

        # 5. Get phase weights and bonuses from config
        phase_weights = config.phases[current_phase].signal_weights
        phase_bonuses = config.phases[current_phase].phase_bonuses

        # 6. Stage 1: Rank strategies using global signals
        ranked_strategies, stage1_decomp = rank_strategies(
            strategy_configs=config.strategies,
            signals=global_signals,
            phase_weights=phase_weights,
            phase_bonuses=phase_bonuses,
            return_decomposition=True,
        )

        best_strategy = ranked_strategies[0][0]

        # 7. Stage 2: Select node if strategy requires node binding
        if best_strategy.node_binding == "required" and node_signals:
            ranked_nodes, stage2_decomp = rank_nodes_for_strategy(
                best_strategy, node_signals
            )
            focus_node_id = ranked_nodes[0][0] if ranked_nodes else None
```

### YAML Configuration Structure

Methodologies are defined in YAML files under `config/methodologies/`:

```yaml
# Example: config/methodologies/means_end_chain.yaml
method:
  name: means_end_chain
  version: "3.0"
  goal: "Explore causal chains from concrete attributes to abstract values"
  opening_bias: "Elicit concrete, experience-based responses..."
  description: "Laddering: attributes -> consequences -> values"

ontology:
  nodes:
    - name: attribute
      level: 1
      terminal: false
      description: "Concrete product feature..."
      examples: ["creamy texture", "plant-based"]

  edges:
    - name: leads_to
      description: "Causal or enabling relationship"
      permitted_connections:
        - [attribute, functional_consequence]

signals:
  graph:
    - graph.node_count
    - graph.max_depth
    - graph.node.exhaustion_score
  llm:
    - llm.response_depth
    - llm.engagement
  temporal:
    - temporal.strategy_repetition_count
  meta:
    - meta.interview.phase

strategies:
  - name: deepen
    description: "Explore why something matters..."
    signal_weights:
      llm.response_depth.low: 0.8
      llm.engagement.high: 0.5
      graph.node.exhaustion_score.low: 1.0
      temporal.strategy_repetition_count: -0.3

  - name: reflect
    node_binding: none          # Optional: "required" (default) or "none"
    focus_mode: summary         # Optional: "recent_node" (default), "summary", "topic"
    generates_closing_question: true  # Optional: marks interview-ending strategy
    signal_weights:
      graph.max_depth: 0.7

phases:
  early:
    description: "Initial exploration..."
    signal_weights:
      explore: 1.5
      deepen: 0.5
    phase_bonuses:
      explore: 0.2

  mid:
    description: "Building depth..."
    signal_weights:
      deepen: 1.3
    phase_bonuses:
      deepen: 0.3

  late:
    description: "Validation..."
    signal_weights:
      reflect: 1.2
    phase_bonuses:
      reflect: 0.2
```

### Strategy Selection Mechanisms

#### Signal Weight Scoring

The `score_strategy()` function in `src/methodologies/scoring.py` computes weighted scores:

```python
def score_strategy(
    strategy_config: StrategyConfig,
    signals: Dict[str, Any],
) -> float:
    score = 0.0
    for signal_key, weight in strategy_config.signal_weights.items():
        signal_value = _get_signal_value(signal_key, signals)
        if signal_value is None:
            continue
        if isinstance(signal_value, bool):
            contribution = weight if signal_value else 0.0
        elif isinstance(signal_value, (int, float)):
            contribution = weight * signal_value  # Already [0,1]
        score += contribution
    return score
```

**Compound Key Handling**: Signal keys support value qualifiers:
- `llm.response_depth.surface` - matches when response_depth == "surface"
- `graph.node.exhaustion_score.low` - matches when score <= 0.25
- `graph.chain_completion.has_complete.false` - boolean matching

#### Node-Scoped Signal Partitioning

Node-scoped signals (prefixes: `graph.node.`, `technique.node.`, `meta.node.`) are partitioned from strategy weights:

```python
def partition_signal_weights(
    signal_weights: Dict[str, float],
) -> tuple[Dict[str, float], Dict[str, float]]:
    """Split into (strategy_weights, node_weights)."""
    for key, weight in signal_weights.items():
        if any(key.startswith(prefix) for prefix in NODE_SIGNAL_PREFIXES):
            node_weights[key] = weight
        else:
            strategy_weights[key] = weight
    return strategy_weights, node_weights
```

### Phase-Based Weights and Bonuses

Phase configuration enables adaptive interview behavior through two mechanisms:

**1. Signal Weights (Multiplicative)**:
```python
# Applied per-strategy: final_score = base_score * multiplier
multiplier = phase_weights.get(strategy.name, 1.0)
```

**2. Phase Bonuses (Additive)**:
```python
# Applied after multiplication: final_score = (base_score * multiplier) + bonus
bonus = phase_bonuses.get(strategy.name, 0.0)
final_score = (base_score * multiplier) + bonus
```

**Phase Detection**: The `InterviewPhaseSignal` detects phase based on turn boundaries:
- `early`: turns 1-4
- `mid`: turns 5-12
- `late`: turns 13+

**Score Decomposition**: The scoring system returns `ScoredCandidate` objects with full breakdown:
```python
@dataclass
class ScoredCandidate:
    strategy: str
    node_id: str
    signal_contributions: list[SignalContribution]
    base_score: float
    phase_multiplier: float
    phase_bonus: float
    final_score: float
    rank: int
    selected: bool
```

### Strategy Configuration Options

Each strategy in YAML supports these configuration options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | str | required | Strategy identifier |
| `description` | str | "" | Human-readable description |
| `signal_weights` | dict | required | Signal-to-weight mappings |
| `node_binding` | str | "required" | "required" or "none" |
| `focus_mode` | str | "recent_node" | "recent_node", "summary", or "topic" |
| `generates_closing_question` | bool | false | Whether strategy ends interview |

### Validation

The registry validates methodology configs at load time:

1. **Signal validation**: All signals in `signals:` sections must be known to `ComposedSignalDetector`
2. **Strategy validation**: Duplicate names, invalid `node_binding`/`focus_mode` values
3. **Phase validation**: Phase weights/bonuses must reference defined strategy names
4. **Signal weight validation**: Weight keys must match known signals or allowed prefixes

---

## Knowledge Graph State

### Session State

The `SessionState` object tracks mutable interview state across conversation turns (Pydantic BaseModel):

```python
class SessionState(BaseModel):
    # Core session metadata
    methodology: str
    concept_id: str
    concept_name: str
    turn_count: int = 0
    last_strategy: Optional[str] = None
    mode: InterviewMode = InterviewMode.EXPLORATORY

    # Velocity tracking for saturation signals
    surface_velocity_peak: float = 0.0
    prev_surface_node_count: int = 0
    canonical_velocity_peak: float = 0.0
    prev_canonical_node_count: int = 0

    # Focus history for tracing strategy-node decisions across turns
    focus_history: List[FocusEntry] = Field(default_factory=list)
```

**FocusEntry Model**:

```python
class FocusEntry(BaseModel):
    """Single entry in focus history tracking strategy-node decisions."""
    turn: int                     # Turn number (1-indexed)
    node_id: str                  # Target node ID (empty if no node focus)
    label: str                    # Human-readable node label
    strategy: str                 # Strategy selected for this turn
```

**Focus Tracing Flow**:
1. **ContextLoadingStage** (Stage 1): Loads `focus_history` from `SessionState` into `TurnContext`
2. **ScoringPersistenceStage** (Stage 10): Appends new `FocusEntry` with current turn's strategy and node focus
3. **API**: `GET /sessions/{id}` returns `focus_history` array from `session.state.focus_history`

**Post-Hoc Analysis**:
- Enables reconstruction of exploration path through knowledge graph
- Turn 1 has empty `node_id`/`label` (graph was empty, no node to target)
- Empty turns are preserved (no gaps in sequence) for accurate trace reading

### Graph Structure

The knowledge graph stores:

- **Nodes** (`KGNode`): Concepts extracted from user responses
  - `id`: Unique node identifier
  - `session_id`: Session identifier
  - `label`: Concept text
  - `node_type`: Type classification (attribute, functional, psychosocial, etc.)
  - `source_utterance_ids`: Source utterances for traceability (supports multiple sources)
  - `confidence`: LLM extraction confidence (0.0-1.0)
  - `properties`: Optional metadata properties
  - `recorded_at`: Timestamp when node was created
  - `superseded_by`: Optional ID of node that supersedes this one (for REVISES)
  - `stance`: Sentiment polarity (-1 negative, 0 neutral, +1 positive)

- **Edges** (`KGEdge`): Relationships between concepts
  - `id`: Unique edge identifier
  - `session_id`: Session identifier
  - `source_node_id`: Source node
  - `target_node_id`: Target node
  - `edge_type`: Type of relationship (leads_to, revises, is_a, etc.)
  - `source_utterance_ids`: Source utterances for traceability
  - `confidence`: Relationship confidence (0.0-1.0)
  - `properties`: Optional metadata properties
  - `recorded_at`: Timestamp when edge was created

### Graph State Metrics

The `GraphState` object tracks session-level aggregated metrics (Pydantic BaseModel):

```python
class GraphState(BaseModel):
    # Basic counts
    node_count: int = 0
    edge_count: int = 0
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    orphan_count: int = 0

    # Structured metrics
    depth_metrics: DepthMetrics          # max_depth, avg_depth, depth_by_element, longest_chain_path
    saturation_metrics: Optional[SaturationMetrics] = None

    # Phase tracking
    current_phase: Literal["exploratory", "focused", "closing"] = "exploratory"
    turn_count: int = 0
    strategy_history: Any = Field(default_factory=lambda: deque(maxlen=30))

    # Extensibility
    extended_properties: Dict[str, Any] = Field(default_factory=dict)
```

**DepthMetrics**:
- `max_depth`: Length of longest reasoning chain
- `avg_depth`: Average depth across all nodes
- `depth_by_element`: Average depth per element ID
- `longest_chain_path`: Node IDs forming the deepest chain

**SaturationMetrics**:
- `chao1_ratio`: Chao1 diversity estimator (0-1)
- `new_info_rate`: Rate of novel concept introduction
- `consecutive_low_info`: Turns since last novel concept
- `consecutive_shallow`: Turns with only shallow/surface responses
- `consecutive_depth_plateau`: Turns at same max_depth (no progress)
- `prev_max_depth`: Previous turn's max_depth for plateau detection
- `is_saturated`: Derived flag indicating topic exhaustion

These metrics drive strategy selection via signal pools.

### Canonical Graph State

The system maintains a parallel canonical graph for deduplicated concepts (Pydantic BaseModel):

```python
class CanonicalGraphState(BaseModel):
    concept_count: int              # Active slots only (candidates excluded)
    edge_count: int                 # Canonical edges
    orphan_count: int               # Active slots with no canonical edges
    max_depth: int                  # Longest canonical chain
    avg_support: float              # Average support_count per active slot
```

**Core Models**:

- **CanonicalSlot**: Stable latent concept abstracted from surface nodes
  - `id`: Unique slot identifier
  - `session_id`: Session identifier
  - `slot_name`: LLM-generated canonical name (e.g., "energy_stability")
  - `description`: LLM-generated concept explanation
  - `node_type`: Preserves methodology hierarchy
  - `status`: "candidate" or "active"
  - `support_count`: Number of surface nodes mapped to this slot
  - `first_seen_turn`: Turn when slot was first created
  - `promoted_turn`: Turn when promoted to active (None if still candidate)
  - `embedding`: Serialized numpy embedding (float32, 300-dim)

- **SlotMapping**: Maps surface node to canonical slot
  - `surface_node_id`: ID of surface KGNode
  - `canonical_slot_id`: ID of canonical slot
  - `similarity_score`: Cosine similarity (0.0-1.0)
  - `assigned_turn`: Turn when mapping was created

- **CanonicalEdge**: Aggregated relationship in canonical graph
  - `id`: Unique edge identifier
  - `source_slot_id`/`target_slot_id`: Connected slot IDs
  - `edge_type`: Relationship type
  - `support_count`: Number of supporting surface edges
  - `surface_edge_ids`: Provenance - IDs of supporting surface edges

**State Computation**:
- Computed by `StateComputationStage` (Stage 5)
- Aggregates surface edges to canonical edges
- Tracks candidate -> active slot lifecycle
- Orphans count only ACTIVE slots with zero canonical edges

### Node State Tracking

The system includes per-node state tracking via `NodeStateTracker` to enable node exhaustion detection and backtracking.

The `NodeState` dataclass tracks for each node:

```python
@dataclass
class NodeState:
    # Basic info
    node_id: str
    label: str
    created_at_turn: int
    depth: int
    node_type: str
    is_terminal: bool = False
    level: int = 0

    # Engagement metrics
    focus_count: int = 0
    last_focus_turn: Optional[int] = None
    turns_since_last_focus: int = 0
    current_focus_streak: int = 0

    # Yield metrics
    last_yield_turn: Optional[int] = None
    turns_since_last_yield: int = 0
    yield_count: int = 0
    yield_rate: float = 0.0

    # Response quality
    all_response_depths: List[str] = field(default_factory=list)

    # Relationships
    connected_node_ids: Set[str] = field(default_factory=set)
    edge_count_outgoing: int = 0
    edge_count_incoming: int = 0

    # Strategy usage
    strategy_usage_count: Dict[str, int] = field(default_factory=dict)
    last_strategy_used: Optional[str] = None
    consecutive_same_strategy: int = 0

    @property
    def is_orphan(self) -> bool:
        """Check if node has no edges."""
        return (self.edge_count_incoming + self.edge_count_outgoing) == 0
```

**NodeStateTracker** manages all node states:

```python
class NodeStateTracker:
    def __init__(self, canonical_slot_repo: Optional["CanonicalSlotRepository"] = None):
        self.states: Dict[str, NodeState] = {}           # node_id -> NodeState
        self.previous_focus: Optional[str] = None        # Last focused node
        self.canonical_slot_repo = canonical_slot_repo   # For dual-graph support

    # Core operations
    async def register_node(self, node: KGNode, turn_number: int) -> NodeState
    async def update_focus(self, node_id: str, turn_number: int, strategy: str) -> None
    async def record_yield(self, node_id: str, turn_number: int, graph_changes: GraphChangeSummary) -> None
    async def append_response_signal(self, focus_node_id: str, response_depth: str) -> None
    async def update_edge_counts(self, node_id: str, outgoing_delta: int, incoming_delta: int) -> None

    # Serialization for persistence
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeStateTracker"
```

**Dual-Graph Support**:
- When `canonical_slot_repo` is provided, surface node IDs resolve to canonical slot IDs for tracking
- Enables aggregation across paraphrases (e.g., "fast car" and "quick vehicle" both map to same slot)
- Falls back to surface node_id if no mapping exists

### Node Tracker Persistence

NodeStateTracker persists across turns via database storage in `sessions.node_tracker_state` column.

**Persistence Flow**:

1. **Load (turn start)**: `SessionRepository.get_node_tracker_state()` retrieves JSON state; `NodeStateTracker.from_dict()` reconstructs tracker
2. **Use (during turn)**: Tracker updated via `update_focus()`, `record_yield()`, `append_response_signal()`
3. **Save (turn end)**: `NodeStateTracker.to_dict()` serializes to JSON; `SessionRepository.update_node_tracker_state()` persists to database

**Schema Versioning**:
- `NODE_TRACKER_SCHEMA_VERSION = 1` for future compatibility
- Includes: `schema_version`, `previous_focus`, `states` dict
- Graceful degradation: NULL state creates fresh tracker

### Node Exhaustion and Backtracking

The node exhaustion system enables intelligent backtracking by detecting when nodes are exhausted.

**Exhaustion Detection Criteria**:

A node signals exhaustion through multiple metrics:
- `turns_since_last_yield`: Turns since node produced graph changes (threshold-based)
- `current_focus_streak`: Consecutive turns focused on this node
- `yield_rate`: Ratio of yields to focus attempts (0.0 = exhausted, 1.0 = high yield)

**Node-Level Signals**:

| Signal | Type | Purpose |
|--------|------|---------|
| `graph.node.exhausted` | boolean | Primary exhaustion flag |
| `graph.node.exhaustion_score` | float (0.0-1.0) | Continuous exhaustion score |
| `graph.node.yield_stagnation` | boolean | Early warning: 3+ turns without yield |
| `graph.node.focus_streak` | categorical | Track persistent focus (none/low/medium/high) |
| `graph.node.recency_score` | float (0.0-1.0) | How recently node was focused |

**Exhaustion Score Calculation**:

```python
exhaustion_score = (
    min(turns_since_last_yield, 10) / 10.0 * 0.4 +  # Yield stagnation (0.0-0.4)
    min(current_focus_streak, 5) / 5.0 * 0.3 +       # Persistent focus (0.0-0.3)
    shallow_response_ratio * 0.3                      # Response quality (0.0-0.3)
)
```

**Score interpretation**:
- `0.0 - 0.3`: Fresh node, high opportunity
- `0.3 - 0.6`: Moderate engagement, some yield
- `0.6 - 1.0`: Exhausted, backtracking recommended

**Backtracking Behavior**:

1. **Negative weights for exhausted nodes**: Strategies targeting exhausted nodes receive `graph.node.exhausted.true` signal with negative weight
2. **Strategy selection deprioritizes exhausted nodes**: During joint strategy-node scoring, exhausted nodes receive lower scores
3. **System backtracks to high-yield nodes**: Focus selection prioritizes nodes with `meta.node.opportunity: "fresh"` or orphan status
4. **Natural oscillation**: Deep dive until exhaustion, then backtrack to fresh nodes

### Focus History Tracking

The `focus_history` field in `SessionState` maintains an ordered sequence of `FocusEntry` records:

```python
class FocusEntry(BaseModel):
    turn: int          # Turn number when focus was selected
    node_id: str       # Target node ID (empty string if no specific node)
    label: str         # Human-readable node label
    strategy: str      # Strategy selected for this turn
```

**Update Flow**:
1. **StrategySelectionStage** (Stage 6): Determines strategy and optional node focus
2. **ScoringPersistenceStage** (Stage 10): Appends `FocusEntry` to `session.state.focus_history`
3. **Next Turn**: `ContextLoadingStage` (Stage 1) loads updated history into `TurnContext`

**Usage**:
- Post-hoc analysis of exploration path through knowledge graph
- Debugging strategy selection decisions
- Understanding interview progression patterns

---

## Policy-Driven Follow-Up Question Generation

### Opening vs Follow-Up Questions

The system uses fundamentally different prompt structures for opening versus follow-up questions:

**Opening Questions** (conversational, low-constraint):
- Goal: Warmly invite the respondent to share initial thoughts
- Style: Friendly, open-ended, narrative-focused
- Context: Methodology (name, goal, opening_bias) + interview objective
- Temperature: 0.9 for creative variety
- Example: "What are your thoughts on oat milk alternatives?"

**Follow-Up Questions** (policy-driven, high-constraint):
- Goal: Execute a specific strategy based on signals
- Style: Focused, strategic, topic-anchored
- Context: Strategy description + graph state + recent conversation + topic anchoring
- Temperature: 0.7 (self-selection mode) or 0.8 (baseline)
- Example: "Why does having that routine matter to you?" (deepen strategy)

### Signal Rationale in Prompts

> **Implementation Note**: Signal rationale in prompts is architected but not currently wired. The prompt templates in `src/llm/prompts/question.py` support signal descriptions and the `QuestionService.generate_question()` method accepts `signals` and `signal_descriptions` parameters. However, `QuestionGenerationStage` does not yet pass these parameters from `StrategySelectionOutput` to `generate_question()`. This feature is designed but not deployed.

Follow-up prompts include active signals with descriptions to explain WHY each strategy was selected:

```
## Active Signals:
- graph.max_depth: 1
  -> "Depth of the longest chain. Low values (<2) indicate surface-level exploration"
- llm.response_depth: moderate
  -> "LLM assessment of response depth. 'moderate' means some elaboration"
- graph.chain_completion.has_complete: false
  -> "Whether any complete chains exist from level 1 to terminal nodes"

## Why This Strategy Was Selected:
- Low depth suggests we're still at surface level
- No complete chains exist - need to reach terminal values
- Strategy: deepen to probe motivations and values

Focus concept: indulgence
Strategy: Deepen Understanding - "Explore why something matters to understand deeper motivations and values"
```

The `_build_strategy_rationale()` function in `src/llm/prompts/question.py` generates explanations based on active signals:
- `graph.max_depth`: Indicates surface vs deep exploration
- `graph.chain_completion.has_complete`: Shows whether terminal values reached
- `llm.response_depth`: Surface-level responses suggest need for deeper probing
- `llm.hedging_language`: Uncertainty levels inform clarification needs

### Strategy Descriptions from YAML

Strategies are loaded from methodology YAML files (`config/methodologies/*.yaml`) with `description` fields that explain WHAT each strategy does:

```yaml
strategies:
  - name: deepen
    description: "Explore why something matters to understand deeper motivations and values"
    signal_weights:
      # ...
  - name: explore
    description: "Discover new attributes or consequences not yet mentioned"
    signal_weights:
      # ...
```

The prompt generation code loads these descriptions dynamically:

```python
registry = get_registry()
config = registry.get_methodology(methodology_name)
strategy_config = next((s for s in config.strategies if s.name == strategy), None)
if strategy_config:
    strat_description = strategy_config.description
```

This makes strategies:
- **Configurable**: Edit YAML without code changes
- **Self-documenting**: Description field explains strategy purpose
- **LLM-ready**: Descriptions formulated for prompt inclusion

### Methodology Context in Prompts

When methodology schema is available, both opening and follow-up prompts include methodology-specific context:

**Follow-up prompts** include:
```
Method: means_end_chain
Goal: Explore causal chains from concrete attributes to abstract values
```

**Opening prompts** include:
```
Methodology: means_end_chain
Method goal: Understand how product attributes link to personal values
Method-specific opening guidance: Start with concrete attributes and elicit the respondent's own associations.
```

The `MethodologySchema.method` field provides:
- `name`: Methodology identifier (e.g., "means_end_chain", "jobs_to_be_done")
- `goal`: High-level description of the methodology's purpose
- `description`: Detailed explanation of the method
- `opening_bias`: Methodology-specific guidance for opening question generation (e.g., "Start with concrete attributes" for MEC, "Start with job context" for JTBD)

### Topic Anchoring

To prevent questions from drifting into abstract philosophy, the system anchors questions to the research topic:

**System prompt** (when topic provided):
```
## Topic Anchoring:
This interview is about **coffee**. While exploring deeper motivations and values,
ensure questions remain connected to the respondent's experience with coffee.
If the conversation drifts too far into abstract philosophy, gently relate back to coffee.
```

**User prompt** (when depth >= 2):
```
Note: We're deep in the conversation. Keep the question connected to coffee -
explore values through the lens of their specific experience, not generic life philosophy.
```

---

## LLM Integration

### Three-Client Architecture

The system uses a three-client architecture with task-optimized LLM selection, implemented in `/home/mikhailarutyunov/projects/interview-system-v2/src/llm/client.py`:

| Client Type | Purpose | Default Provider | Default Model | Temperature | Max Tokens | Timeout |
|-------------|---------|------------------|---------------|-------------|------------|---------|
| `extraction` | Extract nodes/edges from user responses | anthropic | claude-sonnet-4-6 | 0.3 | 2048 | 30s |
| `scoring` | Extract diagnostic signals for strategy scoring | kimi | kimi-k2-0905-preview | 0.3 | 512 | 30s |
| `generation` | Generate interview questions | anthropic | claude-sonnet-4-6 | 0.7 | 1024 | 30s |

**Client Factory Functions**:
- `get_extraction_llm_client()` - Returns LLMClient configured for extraction tasks
- `get_scoring_llm_client()` - Returns LLMClient configured for scoring tasks
- `get_generation_llm_client()` - Returns LLMClient configured for question generation

**Configuration Overrides**: Each client type can be overridden via environment variables:
- `LLM_EXTRACTION_PROVIDER` - Override extraction provider (default: anthropic)
- `LLM_SCORING_PROVIDER` - Override scoring provider (default: kimi)
- `LLM_GENERATION_PROVIDER` - Override generation provider (default: anthropic)

**Sonnet 4.6 Effort Parameter**: Extraction and generation clients support the `effort` parameter for Claude Sonnet 4.6:
- Extraction: `effort="medium"` (complex agentic reasoning for structured output)
- Generation: `effort="low"` (conversational, speed matters)

### Supported Providers

The system supports three LLM providers via the abstract `LLMClient` base class:

1. **AnthropicClient** - Claude models via Messages API
   - Base URL: `https://api.anthropic.com/v1`
   - Supports `effort` parameter for output token budget control
   - API key: `ANTHROPIC_API_KEY`

2. **KimiClient** - Moonshot AI models via OpenAI-compatible API
   - Base URL: `https://api.moonshot.ai/v1`
   - Uses `OpenAICompatibleClient` base class
   - API key: `KIMI_API_KEY`

3. **DeepSeekClient** - DeepSeek models via OpenAI-compatible API
   - Base URL: `https://api.deepseek.com`
   - Uses `OpenAICompatibleClient` base class
   - API key: `DEEPSEEK_API_KEY`

### LLM Timeout and Retry Behavior

All clients implement consistent timeout and retry logic:

**Retry Configuration**:
- Max retries: 1 (2 total attempts)
- Base delay: 1.0 second
- Backoff: Exponential (`delay = base_delay * 2^attempt`)

**Retryable Conditions**:
- `httpx.TimeoutException` - Retry with exponential backoff
- `HTTPStatusError(429)` - Rate limit, retry with exponential backoff

**Non-Retryable Conditions**:
- Other 4xx/5xx errors - Raised immediately without retry

**Error Types** (from `src/core/exceptions`):
- `LLMTimeoutError` - Raised after all retries exhausted on timeout
- `LLMRateLimitError` - Raised after all retries exhausted on rate limit

### Token Usage Tracking

All LLM calls automatically track token usage when a `session_id` is provided:

- Input tokens and output tokens recorded per call
- Usage tracked via `TokenUsageService.record_llm_call()`
- Session ID passed via context variable (`set_llm_session_id()`) or explicit parameter
- Pricing configuration in `src/core/config.py` for cost calculations

**Pricing Configuration** (per million tokens):
- Claude Sonnet: $3.00 input / $15.00 output
- Kimi K2: $0.60 input / $2.50 output
- DeepSeek Chat: $0.14 input / $0.28 output

### Structured Logging

All LLM calls emit structured logs via structlog:

**Log Events**:
- `llm_call_start` - Debug level, includes prompt length, temperature, attempt number
- `llm_call_complete` - Info level, includes latency, input/output tokens
- `llm_timeout` - Warning level on timeout
- `llm_rate_limit` - Warning level on 429
- `llm_retry_after_timeout` / `llm_retry_after_rate_limit` - Info level on retry
- `llm_http_error` - Error level on non-retryable HTTP errors

---

## References

- [Pipeline Contracts](./pipeline_contracts.md) - Stage read/write specifications
- [Data Flow Paths](./data_flow_paths.md) - Critical data flow visualizations
- [API Documentation](./API.md) - Complete API reference
- [DEVELOPMENT](./DEVELOPMENT.md) - Development guide
