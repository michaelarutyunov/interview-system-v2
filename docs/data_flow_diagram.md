# Data Flow Diagram

**Adaptive Interview System v2** - Single Turn Processing (Post-ADR-008)

> **Note**: This document reflects the new pipeline architecture implemented in ADR-008. The previous monolithic `SessionService.process_turn()` has been refactored into a composable pipeline pattern.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                     │
│                        "I like the creamy texture"                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                                 │
│                     POST /sessions/{id}/turns                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Validate request                                                  │  │
│  │ 2. Delegate to SessionService                                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Service Layer: SessionService                          │
│                    process_turn(session_id, user_input)                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Create TurnContext (data transfer object)                          │  │
│  │ 2. Delegate to TurnPipeline.execute(context)                           │  │
│  │ 3. Return TurnResult                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Pipeline Layer: TurnPipeline                               │
│                     execute(context) → 10 sequential stages                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  │                                                                       │  │
│  │  ▼  TurnContext (data bucket) flows through stages:                     │  │
│  │  │                                                                       │  │
│  │  ├─→ ContextLoadingStage     → adds: methodology, graph_state            │  │
│  │  ├─→ UtteranceSavingStage    → adds: user_utterance                  │  │
│  │  ├─→ ExtractionStage          → adds: extraction                     │  │
│  │  ├─→ GraphUpdateStage        → adds: nodes_added, edges_added        │  │
│  │  ├─→ StateComputationStage   → adds: updated graph_state         │  │
│  │ ├─→ StrategySelectionStage  → adds: strategy, focus, scoring     │  │
│  │ ├─→ ContinuationStage       → adds: should_continue              │  │
│  │ ├─→ QuestionGenerationStage → adds: next_question                 │  │
│  │ ├─→ ResponseSavingStage     → adds: system_utterance             │  │
│  │ └─→ ScoringPersistenceStage → adds: scoring                        │  │
│  │                                                                       │  │
│  │  Each stage is independent - only reads/writes TurnContext           │  │
│  │  No stage calls another stage directly                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────────┴───────────────────┐
                    ▼                   ▼                   ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │ Repository Layer    │ │   Service Layer    │ │   Service Layer    │
        │ (Database Access)   │ │ (Business Logic)   │ │ (Business Logic)   │
        └───────────────────┘ └───────────────────┘ └───────────────────┘

        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │ SessionRepository  │ │ ExtractionService │ │  GraphService     │
        │ GraphRepository    │ │ QuestionService  │ │ StrategyService   │
        │ UtteranceRepository│ │                   │ │                   │
        └───────────────────┘ └───────────────────┘ └───────────────────┘
```

---

## Pipeline Stage Details

### Stage 1: ContextLoadingStage

**Purpose**: Load session metadata and current state

**Reads from**:
- `TurnContext.session_id`

**Interacts with**:
- `SessionRepository.get_session()` - session config
- `GraphRepository.get_graph_state()` - current graph state
- `UtteranceRepository.get_recent()` - conversation history

**Writes to TurnContext**:
- `methodology`, `concept_id`, `concept_name`, `max_turns`
- `graph_state` (GraphState object)
- `recent_utterances` (list)
- `mode` (interview mode: coverage_driven/synthetic)

---

### Stage 2: UtteranceSavingStage

**Purpose**: Persist user input to database

**Reads from**:
- `TurnContext.session_id`, `user_input`, `turn_number`

**Interacts with**:
- `UtteranceRepository.save()` - save user utterance

**Writes to TurnContext**:
- `user_utterance` (Utterance object)

---

### Stage 3: ExtractionStage

**Purpose**: Extract concepts and relationships from user input

**Reads from**:
- `TurnContext.user_input`, `graph_state`, `recent_utterances`

**Interacts with**:
- `ExtractionService.extract()` - LLM-based extraction

**Writes to TurnContext**:
- `extraction` (ExtractionResult with concepts/relationships)

---

### Stage 4: GraphUpdateStage

**Purpose**: Update knowledge graph with extracted data

**Reads from**:
- `TurnContext.extraction`, `session_id`

**Interacts with**:
- `GraphService.add_extraction_to_graph()` - add nodes/edges

**Writes to TurnContext**:
- `nodes_added` (list of KGNode)
- `edges_added` (list of edges)

---

### Stage 5: StateComputationStage

**Purpose**: Recompute graph state after updates

**Reads from**:
- `TurnContext.session_id`

**Interacts with**:
- `GraphService.get_graph_state()` - get updated state

**Writes to TurnContext**:
- `graph_state` (refreshed GraphState object)

---

### Stage 6: StrategySelectionStage

**Purpose**: Select questioning strategy using two-tier scoring

**Reads from**:
- `TurnContext.graph_state`, `recent_nodes`, `extraction`

**Interacts with**:
- `StrategyService.select_strategy()` - scoring + selection

**Writes to TurnContext**:
- `strategy` (strategy_id string)
- `focus` (dict with node_id/element_id)
- `selection_result` (full selection data)
- `scoring` (scoring breakdown)

---

### Stage 7: ContinuationStage

**Purpose**: Determine if interview should continue

**Reads from**:
- `TurnContext.turn_number`, `graph_state`, `strategy`

**Interacts with**:
- Business logic to check coverage, max_turns, etc.

**Writes to TurnContext**:
- `should_continue` (boolean)
- `focus_concept` (string)

---

### Stage 8: QuestionGenerationStage

**Purpose**: Generate follow-up question based on strategy

**Reads from**:
- `TurnContext.strategy`, `focus`, `recent_utterances`

**Interacts with**:
- `QuestionService.generate_question()` - LLM-based generation

**Writes to TurnContext**:
- `next_question` (question text)

---

### Stage 9: ResponseSavingStage

**Purpose**: Persist system utterance to database

**Reads from**:
- `TurnContext.session_id`, `next_question`, `turn_number`

**Interacts with**:
- `UtteranceRepository.save()` - save system utterance

**Writes to TurnContext**:
- `system_utterance` (Utterance object)

---

### Stage 10: ScoringPersistenceStage

**Purpose**: Save scoring data for analysis

**Reads from**:
- `TurnContext.session_id`, `turn_number`, `scoring`, `strategy`

**Interacts with**:
- `SessionRepository.save_scoring_candidate()` - save scoring details
- `SessionRepository.save_scoring_history()` - save scoring summary

**Writes to TurnContext**:
- (updates turn tracking in session)

---

## Data Flow Summary

| Stage | Input from TurnContext | Output to TurnContext | External Dependencies |
|-------|------------------------|----------------------|----------------------|
| **1. ContextLoading** | session_id | methodology, graph_state, recent_utterances | SessionRepository, GraphRepository, UtteranceRepository |
| **2. UtteranceSaving** | user_input, session_id | user_utterance | UtteranceRepository |
| **3. Extraction** | user_input, graph_state, recent_utterances | extraction | ExtractionService (LLM) |
| **4. GraphUpdate** | extraction, session_id | nodes_added, edges_added | GraphService |
| **5. StateComputation** | session_id | graph_state (updated) | GraphService |
| **6. StrategySelection** | graph_state, extraction | strategy, focus, scoring | StrategyService, Scoring modules |
| **7. Continuation** | turn_number, graph_state | should_continue | (business logic) |
| **8. QuestionGeneration** | strategy, focus, recent_utterances | next_question | QuestionService (LLM) |
| **9. ResponseSaving** | next_question, session_id | system_utterance | UtteranceRepository |
| **10. ScoringPersistence** | scoring, strategy, turn_number | (tracking only) | SessionRepository |

---

## Key Data Structures

```python
# TurnContext (data bucket passed between stages)
@dataclass
class TurnContext:
    # Input (immutable)
    session_id: str
    user_input: str
    turn_number: int

    # Accumulated state
    methodology: str
    concept_id: str
    graph_state: Optional[GraphState]
    extraction: Optional[ExtractionResult]
    strategy: str
    next_question: str
    should_continue: bool
    # ... and more

# TurnResult (final output)
class TurnResult:
    turn_number: int
    extracted: dict  # concepts, relationships
    graph_state: dict  # node_count, coverage, depth
    scoring: dict     # coverage, depth, etc.
    strategy_selected: str
    next_question: str
    should_continue: bool
    latency_ms: int
```

---

## How Changes Are Isolated (ADR-008 Benefit)

### Before: Monolithic Process

```
SessionService.process_turn() - 200 lines
├─ Load context
├─ Save utterance (inline SQL)
├─ Extract concepts
├─ Update graph
├─ Compute state
├─ Select strategy (complex scoring logic)
├─ Determine continuation
├─ Generate question
├─ Save response (inline SQL)
└─ Save scoring (inline SQL)

PROBLEM: Changing "Select strategy" requires:
  1. Finding the code in 200 lines
  2. Understanding how it affects "Extract concepts"
  3. Risking breaking "Save response"
```

### After: Pipeline Stages

```
TurnPipeline.execute(context)
├─ ContextLoadingStage     (only loads metadata)
├─ UtteranceSavingStage    (only saves utterance)
├─ ExtractionStage          (only extracts)
├─ GraphUpdateStage        (only updates graph)
├─ StateComputationStage   (only recomputes state)
├─ StrategySelectionStage  (only selects strategy) ← CHANGE THIS
├─ ContinuationStage       (only decides continuation)
├─ QuestionGenerationStage (only generates question)
├─ ResponseSavingStage     (only saves response)
└─ ScoringPersistenceStage (only saves scoring)

BENEFIT: Changing StrategySelectionStage requires:
  1. Open src/services/turn_pipeline/stages/strategy_selection_stage.py
  2. Modify process() method
  3. No impact on other stages!
```

---

## Adding a New Scorer (Example)

### Step 1: Create scorer file

```python
# src/services/scoring/tier2/sentiment.py
class SentimentScorer(ScorerBase):
    """Boost strategies based on respondent sentiment."""

    async def score(self, candidate, context):
        # Read from context (doesn't touch database)
        sentiment = await self._get_sentiment(context.recent_utterances)

        # Return score (doesn't affect other stages)
        if sentiment > 0.5:
            return self.make_output(raw_score=1.3)
        return self.make_output(raw_score=1.0)
```

### Step 2: Register scorer

```python
# src/services/scoring/tier2/__init__.py
from .sentiment import SentimentScorer

def get_tier2_scorers(config):
    return [
        CoverageGapScorer(config["coverage_gap"]),
        SentimentScorer(config["sentiment"]),  # ← ADD THIS
        # ... other scorers
    ]
```

### Step 3: Add configuration

```yaml
# config/scoring.yaml
tier2_scorers:
  sentiment:
    enabled: true
    weight: 0.15
    threshold: 0.5
```

**Files modified**: 2 files (one line + 5 lines)
**Files NOT touched**: API, Pipeline, SessionService, Database

---

## References

- **ADR-008**: Internal API Boundaries + Pipeline Pattern - Full architectural decision
- **Pipeline Visualization**: `docs/raw_ideas/pipeline_architecture_visualization.md` - Detailed explanation with examples
- **Pipeline Diagram**: `docs/raw_ideas/pipeline_dependencies.dot` - Graphviz visualization
