# Plan 3: Pipeline Flow Clarity Improvements

**Goal**: Improve clarity of data flow through the pipeline, eliminate confusing placeholder patterns, and make stage dependencies explicit.

**Estimated Steps**: 4
**Total Files Modified**: ~8

---

## Step 1: Eliminate Placeholder GraphState Pattern

**Model**: Opus (architectural change with ripple effects)
**Risk**: Medium
**Files**:
- `src/services/turn_pipeline/stages/context_loading_stage.py`
- `src/domain/models/pipeline_contracts.py`
- `src/services/turn_pipeline/context.py`

### Background

Currently, `ContextLoadingStage` (Stage 1) creates a placeholder `GraphState`:

```python
placeholder_graph_state = context.graph_state or GraphState(
    node_count=0,
    edge_count=0,
    depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
    current_phase="exploratory",
    turn_count=session.state.turn_count or 0,
)
```

This is confusing because:
1. The "real" `GraphState` comes from `StateComputationStage` (Stage 5)
2. Early stages might accidentally use the placeholder thinking it's real
3. The contract includes `graph_state` even though it's not actually loaded here

### Implementation

**1a. Remove `graph_state` from `ContextLoadingOutput`**:

```python
# In pipeline_contracts.py, update ContextLoadingOutput:

class ContextLoadingOutput(BaseModel):
    """Contract: ContextLoadingStage output (Stage 1).

    Stage 1 loads session metadata and conversation history.

    Note: graph_state is NOT loaded here - it comes from StateComputationStage
    (Stage 5) after graph updates. Stages 2-4 should not access graph_state.
    """

    # Session metadata
    methodology: str = Field(...)
    concept_id: str = Field(...)
    concept_name: str = Field(...)
    turn_number: int = Field(ge=0, ...)
    mode: str = Field(...)
    max_turns: int = Field(ge=1, ...)

    # Conversation history
    recent_utterances: List[Dict[str, Any]] = Field(...)
    strategy_history: List[str] = Field(...)

    # REMOVED: graph_state and recent_nodes (they come from Stage 5)
```

**1b. Update `ContextLoadingStage` to not create placeholder**:

```python
# In context_loading_stage.py:

context.context_loading_output = ContextLoadingOutput(
    methodology=session.methodology,
    concept_id=session.concept_id,
    concept_name=session.concept_name,
    turn_number=(session.state.turn_count or 0) + 1,
    mode=session.mode.value,
    max_turns=max_turns,
    recent_utterances=recent_utterances,
    strategy_history=strategy_history,
    # REMOVED: recent_nodes and graph_state
)
```

**1c. Update `PipelineContext` properties**:

```python
# In context.py:

@property
def graph_state(self) -> Optional[GraphState]:
    """Get graph_state from StateComputationOutput.

    Returns None if StateComputationStage hasn't run yet.
    Stages before Stage 5 should NOT access this property.
    """
    if self.state_computation_output:
        return self.state_computation_output.graph_state
    return None  # Explicitly None before Stage 5

@property
def recent_nodes(self) -> List[KGNode]:
    """Get recent_nodes from StateComputationOutput.

    Returns empty list if StateComputationStage hasn't run yet.
    """
    if self.state_computation_output:
        return self.state_computation_output.recent_nodes
    return []
```

**1d. Add stage-order validation in StrategySelectionStage**:

```python
# In strategy_selection_stage.py, at the start of process():

if context.state_computation_output is None:
    raise RuntimeError(
        "Pipeline stage order violation: StrategySelectionStage (Stage 6) "
        "requires StateComputationStage (Stage 5) to have run first. "
        "state_computation_output is None."
    )
```

### Acceptance Criteria
- [ ] `ContextLoadingOutput` no longer includes `graph_state`
- [ ] `graph_state` property returns `None` before Stage 5
- [ ] Stages 2-4 don't access `graph_state` (verify with grep)
- [ ] Stage 6 validates that Stage 5 has run
- [ ] Tests verify stage order is enforced

---

## Step 2: Make Stage Dependencies Explicit via Contract Checks

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/services/turn_pipeline/stages/extraction_stage.py`
- `src/services/turn_pipeline/stages/graph_update_stage.py`
- `src/services/turn_pipeline/stages/strategy_selection_stage.py`
- `src/services/turn_pipeline/stages/question_generation_stage.py`

### Background

Stages implicitly depend on previous stages having run, but this isn't enforced. Adding explicit contract checks at the start of each stage makes dependencies clear and catches bugs early.

### Implementation

**Add contract validation to each stage**:

```python
# extraction_stage.py - Stage 3 depends on Stage 2
async def process(self, context: "PipelineContext") -> "PipelineContext":
    # Validate Stage 2 completed
    if context.utterance_saving_output is None:
        raise RuntimeError(
            "Pipeline contract violation: ExtractionStage (Stage 3) requires "
            "UtteranceSavingStage (Stage 2) to complete first."
        )
    # ... rest of stage ...

# graph_update_stage.py - Stage 4 depends on Stages 2 and 3
async def process(self, context: "PipelineContext") -> "PipelineContext":
    # Validate Stage 2 completed
    if context.utterance_saving_output is None:
        raise RuntimeError(
            "Pipeline contract violation: GraphUpdateStage (Stage 4) requires "
            "UtteranceSavingStage (Stage 2) to complete first."
        )
    # Validate Stage 3 completed
    if context.extraction_output is None:
        raise RuntimeError(
            "Pipeline contract violation: GraphUpdateStage (Stage 4) requires "
            "ExtractionStage (Stage 3) to complete first."
        )
    # ... rest of stage ...

# strategy_selection_stage.py - Stage 6 depends on Stage 5
async def process(self, context: "PipelineContext") -> "PipelineContext":
    # Validate Stage 5 completed
    if context.state_computation_output is None:
        raise RuntimeError(
            "Pipeline contract violation: StrategySelectionStage (Stage 6) requires "
            "StateComputationStage (Stage 5) to complete first."
        )
    # ... rest of stage ...

# question_generation_stage.py - Stage 8 depends on Stages 6 and 7
async def process(self, context: "PipelineContext") -> "PipelineContext":
    # Validate Stage 6 completed
    if context.strategy_selection_output is None:
        raise RuntimeError(
            "Pipeline contract violation: QuestionGenerationStage (Stage 8) requires "
            "StrategySelectionStage (Stage 6) to complete first."
        )
    # Validate Stage 7 completed
    if context.continuation_output is None:
        raise RuntimeError(
            "Pipeline contract violation: QuestionGenerationStage (Stage 8) requires "
            "ContinuationStage (Stage 7) to complete first."
        )
    # ... rest of stage ...
```

### Acceptance Criteria
- [ ] Each stage validates its required upstream contracts
- [ ] Error messages clearly identify the missing dependency
- [ ] Tests verify validation catches out-of-order execution
- [ ] No stage silently proceeds with missing dependencies

---

## Step 3: Decompose MethodologyStrategyService

**Model**: Opus (significant refactoring)
**Risk**: Medium
**Files**:
- `src/services/methodology_strategy_service.py`
- Create: `src/services/signal_detection_service.py`

### Background

`MethodologyStrategyService.select_strategy_and_focus()` does too much:
1. Loads methodology config
2. Validates node_tracker
3. Detects global signals
4. Detects global response trend
5. Detects node-level signals
6. Detects interview phase
7. Gets phase weights/bonuses
8. Scores all (strategy, node) pairs
9. Returns best pair

This violates single responsibility and makes the method hard to test.

### Implementation

**3a. Create `src/services/signal_detection_service.py`**:

```python
"""
Signal detection service for interview strategy selection.

Separates signal detection from strategy scoring, making each
independently testable.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
import structlog

from src.methodologies import get_registry
from src.methodologies.signals.llm.global_response_trend import GlobalResponseTrendSignal
from src.methodologies.signals.meta.interview_phase import InterviewPhaseSignal

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext
    from src.services.node_state_tracker import NodeStateTracker
    from src.methodologies.registry import MethodologyConfig

log = structlog.get_logger(__name__)


class SignalDetectionService:
    """
    Detects all signals needed for strategy selection.

    Separates signal detection from scoring to improve testability
    and clarify responsibilities.
    """

    def __init__(self):
        self.methodology_registry = get_registry()
        self.global_trend_signal = GlobalResponseTrendSignal()

    async def detect_all_signals(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        config: "MethodologyConfig",
        node_tracker: "NodeStateTracker",
    ) -> Dict[str, Any]:
        """
        Detect all signals for strategy selection.

        Returns a unified dict containing:
        - Global signals (graph, llm, temporal)
        - Global response trend
        - Interview phase

        Node signals are NOT included here - they're detected per-node
        by the scoring layer.

        Args:
            context: Pipeline context
            graph_state: Current graph state
            response_text: User's response
            config: Methodology config
            node_tracker: Node state tracker

        Returns:
            Dict of signal_name -> value
        """
        # Detect global signals via composed detector
        signal_detector = self.methodology_registry.create_signal_detector(config)
        global_signals = await signal_detector.detect(
            context, graph_state, response_text
        )

        # Add global response trend
        current_depth = global_signals.get("llm.response_depth", "surface")
        trend_result = await self.global_trend_signal.detect(
            context, graph_state, response_text, current_depth=current_depth
        )
        global_signals["llm.global_response_trend"] = trend_result.get(
            "llm.global_response_trend", "stable"
        )

        # Add interview phase
        phase_signal = InterviewPhaseSignal()
        phase_result = await phase_signal.detect(context, graph_state, response_text)
        global_signals["meta.interview.phase"] = phase_result.get(
            "meta.interview.phase", "early"
        )

        log.debug(
            "all_signals_detected",
            signal_count=len(global_signals),
            phase=global_signals.get("meta.interview.phase"),
        )

        return global_signals

    async def detect_node_signals(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        node_tracker: "NodeStateTracker",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect signals for each tracked node.

        Args:
            context: Pipeline context
            graph_state: Current graph state
            response_text: User's response
            node_tracker: Node state tracker

        Returns:
            Dict mapping node_id -> signal_dict
        """
        # Import node signal detectors
        from src.methodologies.signals.graph.node_exhaustion import (
            NodeExhaustedSignal,
            NodeExhaustionScoreSignal,
            NodeYieldStagnationSignal,
        )
        from src.methodologies.signals.graph.node_engagement import (
            NodeFocusStreakSignal,
            NodeIsCurrentFocusSignal,
            NodeRecencyScoreSignal,
        )
        from src.methodologies.signals.graph.node_relationships import (
            NodeIsOrphanSignal,
            NodeEdgeCountSignal,
            NodeHasOutgoingSignal,
        )
        from src.methodologies.signals.technique.node_strategy_repetition import (
            NodeStrategyRepetitionSignal,
        )

        all_states = node_tracker.get_all_states()
        if not all_states:
            return {}

        node_signals: Dict[str, Dict[str, Any]] = {
            node_id: {} for node_id in all_states.keys()
        }

        signal_detectors = [
            NodeExhaustedSignal(node_tracker),
            NodeExhaustionScoreSignal(node_tracker),
            NodeYieldStagnationSignal(node_tracker),
            NodeFocusStreakSignal(node_tracker),
            NodeIsCurrentFocusSignal(node_tracker),
            NodeRecencyScoreSignal(node_tracker),
            NodeIsOrphanSignal(node_tracker),
            NodeEdgeCountSignal(node_tracker),
            NodeHasOutgoingSignal(node_tracker),
            NodeStrategyRepetitionSignal(node_tracker),
        ]

        for detector in signal_detectors:
            detected = await detector.detect(context, graph_state, response_text)
            for node_id, signal_value in detected.items():
                if node_id in node_signals:
                    node_signals[node_id][detector.signal_name] = signal_value

        return node_signals
```

**3b. Simplify `MethodologyStrategyService`**:

```python
class MethodologyStrategyService:
    """Strategy selection using YAML methodology configs."""

    def __init__(self):
        self.methodology_registry = get_registry()
        self.signal_detection = SignalDetectionService()

    async def select_strategy_and_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
    ) -> Tuple[str, Optional[str], Sequence[...], Optional[Dict[str, Any]]]:
        """Select best (strategy, node) pair."""

        methodology_name = context.methodology or "means_end_chain"
        config = self._get_validated_config(methodology_name)
        node_tracker = self._get_validated_tracker(context)

        # Step 1: Detect all signals (delegated)
        global_signals = await self.signal_detection.detect_all_signals(
            context, graph_state, response_text, config, node_tracker
        )

        # Step 2: Detect node signals (delegated)
        node_signals = await self.signal_detection.detect_node_signals(
            context, graph_state, response_text, node_tracker
        )

        # Step 3: Get phase-based adjustments
        current_phase = global_signals.get("meta.interview.phase", "early")
        phase_weights, phase_bonuses = self._get_phase_adjustments(config, current_phase)

        # Step 4: Score all pairs
        scored_pairs = rank_strategy_node_pairs(
            strategies=config.strategies,
            global_signals=global_signals,
            node_signals=node_signals,
            node_tracker=node_tracker,
            phase_weights=phase_weights,
            phase_bonuses=phase_bonuses,
            signal_norms=config.signal_norms,
        )

        if not scored_pairs:
            raise ScoringError(
                f"No valid (strategy, node) pairs for methodology '{methodology_name}'"
            )

        best_strategy, best_node_id, best_score = scored_pairs[0]
        alternatives = [(s.name, nid, score) for s, nid, score in scored_pairs]

        return best_strategy.name, best_node_id, alternatives, global_signals

    def _get_validated_config(self, methodology_name: str) -> "MethodologyConfig":
        """Get and validate methodology config."""
        config = self.methodology_registry.get_methodology(methodology_name)
        if not config:
            raise ConfigurationError(
                f"Methodology '{methodology_name}' not found."
            )
        if not config.strategies:
            raise ConfigurationError(
                f"Methodology '{methodology_name}' has no strategies."
            )
        return config

    def _get_validated_tracker(self, context: "PipelineContext") -> "NodeStateTracker":
        """Get and validate node tracker."""
        if not context.node_tracker:
            raise ValueError("NodeStateTracker required for strategy selection.")
        return context.node_tracker

    def _get_phase_adjustments(
        self,
        config: "MethodologyConfig",
        phase: str,
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Get phase weights and bonuses from config."""
        if config.phases and phase in config.phases:
            return (
                config.phases[phase].signal_weights,
                config.phases[phase].phase_bonuses,
            )
        return None, None
```

### Acceptance Criteria
- [ ] `SignalDetectionService` handles all signal detection
- [ ] `MethodologyStrategyService` focuses on orchestration and scoring
- [ ] Each class has single responsibility
- [ ] Both classes are independently testable
- [ ] Total behavior unchanged (integration tests pass)

---

## Step 4: Add Pipeline Stage Dependency Documentation

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/services/turn_pipeline/stages/__init__.py`
- `src/services/turn_pipeline/pipeline.py`

### Background

The 10-stage pipeline has implicit ordering and dependencies. Making these explicit in code and documentation improves maintainability.

### Implementation

**4a. Add dependency documentation to `stages/__init__.py`**:

```python
"""
Pipeline stages for turn processing.

ADR-008 Phase 3: Each stage encapsulates one logical step of turn processing.

Stage Order and Dependencies:
============================

Stage 1: ContextLoadingStage
  - Loads: Session metadata, conversation history, strategy history
  - Requires: session_id
  - Produces: ContextLoadingOutput

Stage 2: UtteranceSavingStage
  - Saves: User input as utterance
  - Requires: session_id, user_input
  - Produces: UtteranceSavingOutput

Stage 3: ExtractionStage
  - Extracts: Concepts and relationships from user_input
  - Requires: ContextLoadingOutput (for methodology), UtteranceSavingOutput (for traceability)
  - Produces: ExtractionOutput

Stage 4: GraphUpdateStage
  - Updates: Knowledge graph with extracted data
  - Requires: ExtractionOutput, UtteranceSavingOutput
  - Produces: GraphUpdateOutput

Stage 5: StateComputationStage
  - Computes: Fresh graph state after updates
  - Requires: GraphUpdateOutput (implicitly, graph has been updated)
  - Produces: StateComputationOutput (including graph_state!)

Stage 6: StrategySelectionStage
  - Selects: Next questioning strategy and focus node
  - Requires: StateComputationOutput (for fresh graph_state)
  - Produces: StrategySelectionOutput

Stage 7: ContinuationStage
  - Decides: Whether interview should continue
  - Requires: StrategySelectionOutput
  - Produces: ContinuationOutput

Stage 8: QuestionGenerationStage
  - Generates: Next interview question
  - Requires: ContinuationOutput, StrategySelectionOutput, StateComputationOutput
  - Produces: QuestionGenerationOutput

Stage 9: ResponseSavingStage
  - Saves: System response as utterance
  - Requires: QuestionGenerationOutput
  - Produces: ResponseSavingOutput

Stage 10: ScoringPersistenceStage
  - Persists: Scoring metrics and signals
  - Requires: All previous outputs for comprehensive logging
  - Produces: ScoringPersistenceOutput

Critical Data Flow Paths:
========================

1. Graph State: ContextLoading (placeholder) -> StateComputation (real) -> Strategy/Question
2. Traceability: UtteranceSaving (utterance_id) -> Extraction -> GraphUpdate (node provenance)
3. Strategy: StateComputation -> StrategySelection -> Continuation -> QuestionGeneration
"""

from .context_loading_stage import ContextLoadingStage
# ... rest of imports ...
```

**4b. Add stage order assertion to `pipeline.py`**:

```python
class TurnPipeline:
    """Orchestrates execution of pipeline stages."""

    # Define expected stage order for validation
    EXPECTED_STAGE_ORDER = [
        "ContextLoadingStage",
        "UtteranceSavingStage",
        "ExtractionStage",
        "GraphUpdateStage",
        "StateComputationStage",
        "StrategySelectionStage",
        "ContinuationStage",
        "QuestionGenerationStage",
        "ResponseSavingStage",
        "ScoringPersistenceStage",
    ]

    def __init__(self, stages: List[TurnStage]):
        self.stages = stages
        self.logger = log
        self._validate_stage_order()

    def _validate_stage_order(self) -> None:
        """Validate that stages are in expected order."""
        actual_names = [stage.stage_name for stage in self.stages]

        if actual_names != self.EXPECTED_STAGE_ORDER:
            raise ValueError(
                f"Pipeline stages in unexpected order.\n"
                f"Expected: {self.EXPECTED_STAGE_ORDER}\n"
                f"Actual: {actual_names}"
            )
```

### Acceptance Criteria
- [ ] Stage dependencies documented in `__init__.py`
- [ ] Pipeline validates stage order at construction
- [ ] Documentation matches actual implementation
- [ ] New developers can understand flow from documentation

---

## Testing Strategy

After each step:
1. Run `ruff check src/` - ensure no lint errors
2. Run `pyright src/` - ensure no type errors
3. Run `pytest tests/` - ensure no test regressions

After all steps:
1. Run full test suite
2. Run 3 synthetic interviews to verify pipeline flow
3. Verify error messages are clear when stages are misconfigured
4. Code review documentation for accuracy

---

## Dependency Order

Steps can be executed in order, with Step 1 being the most impactful:

1. **Step 1** (Placeholder GraphState) - Most architectural impact, do first
2. **Step 2** (Contract Checks) - Depends on Step 1 being stable
3. **Step 3** (Decompose Service) - Independent of 1-2
4. **Step 4** (Documentation) - Do last to capture final state

Steps 3 and 4 can be done in parallel after Steps 1-2 are complete.
