# Pipeline Stage Contracts Status

This document tracks the contract status for all pipeline stages in the interview system.

## Overview

**Total Stages**: 10
**Stages with Contracts**: 10 (100%)
**Stages Missing Contracts**: 0 (0%)

**Contracts Location**: `src/domain/models/pipeline_contracts.py`

---

## All Contracts (Complete)

### Stage 1: ContextLoadingStage ✓

**Contract**: `ContextLoadingOutput`

**Status**: Complete

**Fields**:
- `methodology: str` - Methodology identifier
- `concept_id: str` - Concept identifier
- `concept_name: str` - Human-readable concept name
- `turn_number: int` - Current turn number
- `mode: str` - Interview mode
- `max_turns: int` - Maximum turns
- `recent_utterances: List[Dict[str, str]]` - Conversation history
- `strategy_history: List[str]` - Strategy history
- `graph_state: GraphState` - Knowledge graph state
- `recent_nodes: List[KGNode]` - Recent nodes

**Note**: `graph_state` is populated by `StateComputationStage` (Stage 5), not this stage.

---

### Stage 2: UtteranceSavingStage ✓

**Contract**: `UtteranceSavingOutput`

**Status**: Complete

**Fields**:
- `turn_number: int` - Turn number for this utterance
- `user_utterance_id: str` - Database ID of saved utterance
- `user_utterance: Utterance` - Full saved utterance record

---

### Stage 3: ExtractionStage ✓

**Contract**: `ExtractionOutput`

**Status**: Complete

**Fields**:
- `extraction: ExtractionResult` - Extracted concepts and relationships
- `methodology: str` - Methodology used for extraction
- `timestamp: datetime` - When extraction was performed (auto-set)
- `concept_count: int` - Number of concepts extracted (auto-calculated)
- `relationship_count: int` - Number of relationships extracted (auto-calculated)

**Features**:
- Auto-calculates counts from extraction result
- Auto-sets timestamp

---

### Stage 4: GraphUpdateStage ✓

**Contract**: `GraphUpdateOutput`

**Status**: Complete

**Fields**:
- `nodes_added: List[KGNode]` - Nodes added to graph
- `edges_added: List[Dict[str, Any]]` - Edges added to graph
- `node_count: int` - Number of nodes added (auto-calculated)
- `edge_count: int` - Number of edges added (auto-calculated)
- `timestamp: datetime` - When graph update was performed (auto-set)

**Features**:
- Auto-calculates counts from lists
- Auto-sets timestamp

---

### Stage 5: StateComputationStage ✓

**Contract**: `StateComputationOutput`

**Status**: Complete

**Fields**:
- `graph_state: GraphState` - Refreshed knowledge graph state
- `recent_nodes: List[KGNode]` - Refreshed recent nodes
- `computed_at: datetime` - When state was computed (freshness tracking)

**ADR-010**: Includes freshness validation to prevent stale state bug.

---

### Stage 6: StrategySelectionStage ✓

**Contracts**:
- `StrategySelectionInput` - Input contract with freshness validation
- `StrategySelectionOutput` - Output contract with Phase 4 fields

**Status**: Complete

**Input Fields**:
- `graph_state: GraphState` - Current knowledge graph state
- `recent_nodes: List[KGNode]` - Recent nodes
- `extraction: Any` - ExtractionResult with timestamp
- `conversation_history: List[Dict[str, str]]` - Conversation history
- `turn_number: int` - Current turn number
- `mode: str` - Interview mode
- `computed_at: datetime` - When graph_state was computed

**Output Fields**:
- `strategy: str` - Selected strategy ID
- `focus: Optional[Dict[str, Any]]` - Focus target
- `selected_at: datetime` - When strategy was selected (auto-set)
- `signals: Optional[Dict[str, Any]]` - Methodology-specific signals (Phase 4)
- `strategy_alternatives: List[tuple[str, float]]` - Alternatives with scores (Phase 4)

---

### Stage 7: QuestionGenerationStage ✓

**Contract**: `QuestionGenerationOutput`

**Status**: Complete

**Fields**:
- `question: str` - Generated question text
- `strategy: str` - Strategy used to generate question
- `focus: Optional[Dict[str, Any]]` - Focus target for question
- `has_llm_fallback: bool` - Whether LLM fallback was used
- `timestamp: datetime` - When question was generated (auto-set)

---

### Stage 8: ResponseSavingStage ✓

**Contract**: `ResponseSavingOutput`

**Status**: Complete

**Fields**:
- `turn_number: int` - Turn number for this utterance
- `system_utterance_id: str` - Database ID of saved utterance
- `system_utterance: Utterance` - Full saved utterance record
- `question_text: str` - Question text that was saved
- `timestamp: datetime` - When response was saved (auto-set)

---

### Stage 9: ContinuationStage ✓

**Contract**: `ContinuationOutput`

**Status**: Complete

**Fields**:
- `should_continue: bool` - Whether to continue the interview
- `focus_concept: str` - Concept to focus on next turn
- `reason: str` - Reason for continuation decision
- `turns_remaining: int` - Number of turns remaining
- `timestamp: datetime` - When continuation decision was made (auto-set)

---

### Stage 10: ScoringPersistenceStage ✓

**Contract**: `ScoringPersistenceOutput`

**Status**: Complete

**Fields**:
- `turn_number: int` - Turn number for scoring
- `strategy: str` - Strategy that was selected
- `coverage_score: float` - Coverage metric from graph state
- `depth_score: float` - Depth metric from graph state
- `saturation_score: float` - Saturation metric from graph state
- `has_methodology_signals: bool` - Whether methodology signals were saved
- `has_legacy_scoring: bool` - Whether legacy two-tier scoring was saved
- `timestamp: datetime` - When scoring was persisted (auto-set)

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
| Stage 7 | `timestamp` | Has default factory - works |
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

## Historical Note: Removed Deprecated Models

The following models were removed as part of the two-tier scoring system cleanup (Phase 6, 2026-01-28):

- `Focus` (old two-tier version - different from `src.domain.models.turn.Focus`)
- `VetoResult`
- `WeightedResult`
- `ScoredStrategy`
- `StrategySelectionResult`

These were kept only for database compatibility but are no longer needed as the system now uses methodology-based signal detection.

---

## Implementation Complete

All 10 pipeline stages have formal contracts defined. The contracts provide:

1. **Type Safety**: Pydantic models with runtime validation
2. **Traceability**: IDs and timestamps for debugging
3. **Freshness Tracking**: State freshness validation where applicable
4. **Auto-calculation**: Count fields that auto-calculate from data
5. **Auto-defaults**: Timestamps with default factories

---

## References

- **ADR-008**: Internal API Boundaries & Pipeline Pattern
- **ADR-010**: Pipeline Contracts Formalization (Phase 1 & 2)
- **ADR-013**: Methodology-Centric Architecture (Phase 4)
- **docs/data_flow_analysis.md**: Complete data flow documentation
