# Plan 2: Domain Logic Encapsulation Improvements

**Goal**: Consolidate scattered domain logic into cohesive services, reduce duplication, and improve domain model usage.

**Estimated Steps**: 5
**Total Files Modified**: ~12
**New Files Created**: 2

---

## Step 1: Create FocusSelectionService

**Model**: Opus (architectural change, requires careful design)
**Risk**: Medium
**New File**: `src/services/focus_selection_service.py`
**Modified Files**:
- `src/services/turn_pipeline/stages/continuation_stage.py`
- `src/services/question_service.py`
- `src/services/methodology_strategy_service.py`

### Background

Focus selection logic is currently scattered across:
1. `continuation_stage.py:87-109` - Resolves focus_node_id to label
2. `question_service.py:223-265` - `select_focus_concept()` heuristic selection
3. `methodology_strategy_service.py` - Joint strategy-node selection

This creates confusion about who owns focus selection and leads to duplicated fallback logic.

### Implementation

**1a. Create `src/services/focus_selection_service.py`**:

```python
"""
Focus selection service for interview node targeting.

Consolidates all focus selection logic into a single service that:
1. Resolves node IDs to labels
2. Applies strategy-based focus preferences
3. Provides fallback selection when needed

This service is the single source of truth for "what should we ask about next?"
"""

from typing import Optional, List, Dict, Any
import structlog

from src.domain.models.knowledge_graph import KGNode, GraphState

log = structlog.get_logger(__name__)


class FocusSelectionService:
    """
    Centralized service for selecting interview focus targets.

    All focus selection decisions flow through this service to ensure
    consistent behavior across the pipeline.
    """

    def resolve_focus_from_strategy_output(
        self,
        focus_dict: Optional[Dict[str, Any]],
        recent_nodes: List[KGNode],
        strategy: str,
        graph_state: Optional[GraphState] = None,
    ) -> str:
        """
        Resolve focus from strategy selection output.

        This is the primary entry point after StrategySelectionStage.

        Args:
            focus_dict: Focus dict from StrategySelectionOutput (may contain
                       focus_node_id or focus_description)
            recent_nodes: Recent nodes for fallback resolution
            strategy: Selected strategy (affects fallback behavior)
            graph_state: Current graph state (for advanced selection)

        Returns:
            Focus concept label (human-readable string for prompts)

        Resolution order:
        1. If focus_dict has focus_node_id, resolve to node label
        2. If focus_dict has focus_description, use it
        3. Fall back to strategy-based heuristic selection
        """
        # Try to resolve from focus_node_id
        if focus_dict and "focus_node_id" in focus_dict:
            node_id = focus_dict["focus_node_id"]
            label = self._resolve_node_id_to_label(node_id, recent_nodes)
            if label:
                log.debug(
                    "focus_resolved_from_node_id",
                    node_id=node_id,
                    label=label,
                )
                return label

        # Try to use focus_description
        if focus_dict and "focus_description" in focus_dict:
            description = focus_dict["focus_description"]
            if description:
                log.debug(
                    "focus_resolved_from_description",
                    description=description,
                )
                return description

        # Fall back to strategy-based selection
        return self._select_by_strategy(
            recent_nodes=recent_nodes,
            strategy=strategy,
            graph_state=graph_state,
        )

    def _resolve_node_id_to_label(
        self,
        node_id: str,
        nodes: List[KGNode],
    ) -> Optional[str]:
        """
        Find node label by ID.

        Args:
            node_id: Node ID to look up
            nodes: List of nodes to search

        Returns:
            Node label if found, None otherwise
        """
        for node in nodes:
            if str(node.id) == str(node_id):
                return node.label
        return None

    def _select_by_strategy(
        self,
        recent_nodes: List[KGNode],
        strategy: str,
        graph_state: Optional[GraphState] = None,
    ) -> str:
        """
        Select focus concept using strategy-based heuristics.

        This is the fallback when no explicit focus is provided.

        Args:
            recent_nodes: Recently added nodes
            strategy: Strategy name
            graph_state: Current graph state

        Returns:
            Focus concept label
        """
        log.debug(
            "focus_selecting_by_strategy",
            strategy=strategy,
            recent_node_count=len(recent_nodes),
        )

        if not recent_nodes:
            return "the topic"

        if strategy == "deepen":
            # Focus on most recent concept to ladder up
            return recent_nodes[0].label

        elif strategy == "broaden":
            # Focus on recent concept but will ask for alternatives
            return recent_nodes[0].label

        elif strategy == "cover" or strategy == "cover_element":
            # Would ideally look at uncovered elements
            # For now, use most recent
            return recent_nodes[0].label

        elif strategy == "close":
            # Summarize what we've learned
            return "what we've discussed"

        elif strategy == "reflect":
            # Reflect on a recent concept
            return recent_nodes[0].label

        # Default: most recent node
        return recent_nodes[0].label
```

**1b. Update `continuation_stage.py` to use the service**:

```python
# In __init__:
def __init__(self, question_service, focus_selection_service: FocusSelectionService):
    self.question = question_service
    self.focus_selection = focus_selection_service
    self._tracking: Dict[str, _SessionSaturationState] = {}

# Replace lines 86-109 with:
if should_continue:
    focus_concept = self.focus_selection.resolve_focus_from_strategy_output(
        focus_dict=context.focus,
        recent_nodes=context.recent_nodes,
        strategy=context.strategy,
        graph_state=context.graph_state,
    )
else:
    focus_concept = ""
```

**1c. Remove `select_focus_concept()` from `question_service.py`**:

After verifying all callers now use `FocusSelectionService`, delete the method.

**1d. Update pipeline factory to inject the service**:

In wherever stages are constructed (likely `api/routes/sessions.py` or a factory):

```python
focus_selection_service = FocusSelectionService()
continuation_stage = ContinuationStage(
    question_service=question_service,
    focus_selection_service=focus_selection_service,
)
```

### Acceptance Criteria
- [ ] All focus selection flows through `FocusSelectionService`
- [ ] `QuestionService.select_focus_concept()` is deleted
- [ ] `ContinuationStage` uses injected service
- [ ] Fallback chain is clearly documented in one place
- [ ] Tests verify resolution order (node_id -> description -> heuristic)

---

## Step 2: Unify Phase Detection Logic

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/methodologies/signals/meta/interview_phase.py`
- `src/services/turn_pipeline/stages/continuation_stage.py`

### Background

Phase detection exists in two places:
1. `InterviewPhaseSignal` in `interview_phase.py` - Uses node count + orphan count
2. Saturation tracking in `continuation_stage.py` - Uses different turn-based metrics

These should be unified so there's one source of truth for "what phase is this interview in?"

### Implementation

**2a. Extend `InterviewPhaseSignal` to include saturation-based phase indicators**:

```python
# Add to InterviewPhaseSignal.detect() return value:
return {
    "meta.interview.phase": phase,  # existing
    "meta.interview.phase_reason": reason,  # NEW: why this phase
    "meta.interview.is_late_stage": phase == "late",  # NEW: convenience flag
}
```

**2b. Update `continuation_stage.py` to consume the phase signal**:

```python
# In _should_continue(), after basic checks:

# Get phase from signal (if available in context)
current_phase = None
if context.signals:
    current_phase = context.signals.get("meta.interview.phase")

# Late stage enables saturation checks
if current_phase == "late" or turn_number >= MIN_TURN_FOR_SATURATION:
    # ... existing saturation checks ...
```

**2c. Add phase to continuation decision logging**:

```python
log.info(
    "continuation_determined",
    session_id=context.session_id,
    should_continue=should_continue,
    phase=current_phase,  # NEW
    reason=reason,
)
```

### Acceptance Criteria
- [ ] Phase detection uses single signal as source of truth
- [ ] Continuation stage consumes phase from signals
- [ ] No duplicate phase calculation logic
- [ ] Logging includes phase information

---

## Step 3: Move Saturation Tracking to StateComputationStage

**Model**: Opus (significant refactoring)
**Risk**: Medium
**Files**:
- `src/services/turn_pipeline/stages/state_computation_stage.py`
- `src/services/turn_pipeline/stages/continuation_stage.py`
- `src/domain/models/knowledge_graph.py`
- `src/domain/models/pipeline_contracts.py`

### Background

The `SaturationMetrics` model exists in `knowledge_graph.py` but is never populated. Meanwhile, `continuation_stage.py` maintains its own `_SessionSaturationState` for saturation tracking.

This violates the principle that `StateComputationStage` is the source of truth for graph state.

### Implementation

**3a. Update `StateComputationOutput` contract to include saturation**:

```python
# In pipeline_contracts.py, add to StateComputationOutput:

class StateComputationOutput(BaseModel):
    """Contract: StateComputationStage output (Stage 5)."""

    graph_state: GraphState = Field(...)
    recent_nodes: List[KGNode] = Field(...)
    computed_at: datetime = Field(...)

    # NEW: Saturation metrics computed at Stage 5
    saturation_metrics: Optional[SaturationMetrics] = Field(
        default=None,
        description="Saturation indicators computed from graph state",
    )
```

**3b. Implement saturation computation in `state_computation_stage.py`**:

```python
async def process(self, context: "PipelineContext") -> "PipelineContext":
    graph_state = await self.graph.get_graph_state(context.session_id)
    recent_nodes = await self.graph.get_recent_nodes(context.session_id, limit=5)

    # Update turn count and strategy history (existing)
    if graph_state:
        graph_state.turn_count = context.turn_number
        graph_state.strategy_history = context.strategy_history

    # NEW: Compute saturation metrics
    saturation = self._compute_saturation_metrics(
        context=context,
        graph_state=graph_state,
        nodes_added_this_turn=len(context.nodes_added),
        edges_added_this_turn=len(context.edges_added),
    )

    computed_at = datetime.now(timezone.utc)

    context.state_computation_output = StateComputationOutput(
        graph_state=graph_state,
        recent_nodes=recent_nodes,
        computed_at=computed_at,
        saturation_metrics=saturation,  # NEW
    )

    return context

def _compute_saturation_metrics(
    self,
    context: "PipelineContext",
    graph_state: GraphState,
    nodes_added_this_turn: int,
    edges_added_this_turn: int,
) -> SaturationMetrics:
    """
    Compute saturation metrics for the current turn.

    Uses simplified metrics for POC:
    - new_info_rate: ratio of new nodes this turn to total nodes
    - consecutive_low_info: turns since meaningful graph growth
    - is_saturated: derived from consecutive_low_info threshold
    """
    total_nodes = graph_state.node_count if graph_state else 0
    new_info = nodes_added_this_turn + edges_added_this_turn

    # Calculate new_info_rate
    if total_nodes > 0:
        new_info_rate = min(1.0, new_info / max(total_nodes * 0.1, 1))
    else:
        new_info_rate = 1.0 if new_info > 0 else 0.0

    # Track consecutive low info turns (simplified)
    # In production, this would use session-scoped state
    consecutive_low_info = 0
    if new_info == 0:
        # Would increment from previous state
        consecutive_low_info = 1  # Simplified for now

    is_saturated = consecutive_low_info >= 5

    return SaturationMetrics(
        chao1_ratio=0.0,  # Placeholder for future Chao1 estimator
        new_info_rate=new_info_rate,
        consecutive_low_info=consecutive_low_info,
        is_saturated=is_saturated,
    )
```

**3c. Simplify `continuation_stage.py` to use saturation from context**:

```python
def _should_continue(self, context: "PipelineContext") -> tuple[bool, str]:
    # ... existing hard stops ...

    # Use saturation from StateComputationOutput
    saturation = None
    if context.state_computation_output:
        saturation = context.state_computation_output.saturation_metrics

    if saturation and saturation.is_saturated:
        return False, "graph_saturated"

    # ... other checks ...
```

**3d. Remove `_SessionSaturationState` and `_tracking` from continuation_stage.py**

### Acceptance Criteria
- [ ] `SaturationMetrics` is populated by `StateComputationStage`
- [ ] `ContinuationStage` reads saturation from context
- [ ] `_SessionSaturationState` is removed
- [ ] All saturation logic is in one place
- [ ] Tests verify saturation detection works

---

## Step 4: Consolidate LLM Client Construction

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/llm/client.py`
- `src/services/extraction_service.py`
- `src/services/question_service.py`
- `src/api/dependencies.py`

### Background

Currently, each service that uses LLM does:
```python
def __init__(self, llm_client: Optional[LLMClient] = None):
    self.llm = llm_client or get_xxx_llm_client()
```

This spreads LLM client construction and makes it hard to:
1. Switch LLM providers globally
2. Share client instances
3. Configure timeouts/retries consistently

### Implementation

**4a. Create a centralized LLM client factory in `api/dependencies.py`**:

```python
from functools import lru_cache
from src.llm.client import LLMClient, get_extraction_llm_client, get_generation_llm_client


@lru_cache(maxsize=1)
def get_shared_extraction_client() -> LLMClient:
    """Get or create the shared extraction LLM client."""
    return get_extraction_llm_client()


@lru_cache(maxsize=1)
def get_shared_generation_client() -> LLMClient:
    """Get or create the shared generation LLM client."""
    return get_generation_llm_client()
```

**4b. Update service constructors to require LLM client (no default)**:

```python
# In extraction_service.py:
class ExtractionService:
    def __init__(
        self,
        llm_client: LLMClient,  # Now required
        skip_extractability_check: bool = False,
        min_word_count: int = 3,
        concept_id: Optional[str] = None,
    ):
        self.llm = llm_client
        # ... rest unchanged ...

# In question_service.py:
class QuestionService:
    def __init__(
        self,
        llm_client: LLMClient,  # Now required
        default_strategy: str = "deepen",
        methodology: str = "means_end_chain",
    ):
        self.llm = llm_client
        # ... rest unchanged ...
```

**4c. Update service construction in routes/dependencies**:

```python
# In the route handler or dependency provider:
extraction_service = ExtractionService(
    llm_client=get_shared_extraction_client(),
    concept_id=concept_id,
)
question_service = QuestionService(
    llm_client=get_shared_generation_client(),
    methodology=methodology,
)
```

### Acceptance Criteria
- [ ] LLM clients are constructed in one place
- [ ] Services receive clients via dependency injection
- [ ] No service constructs its own LLM client
- [ ] Clients are cached/reused via `@lru_cache`

---

## Step 5: Add Type Annotations to Stage Constructors

**Model**: Sonnet
**Risk**: Low
**Files**:
- All files in `src/services/turn_pipeline/stages/`

### Background

Stage constructors accept services but don't type-annotate them:
```python
def __init__(self, extraction_service):  # No type hint
```

This makes it hard to understand dependencies at a glance.

### Implementation

**For each stage, add type annotations to constructor**:

```python
# context_loading_stage.py
from src.persistence.repositories.session_repo import SessionRepository
from src.services.graph_service import GraphService

class ContextLoadingStage(TurnStage):
    def __init__(
        self,
        session_repo: SessionRepository,
        graph_service: GraphService,
    ):
        self.session_repo = session_repo
        self.graph = graph_service

# extraction_stage.py
from src.services.extraction_service import ExtractionService

class ExtractionStage(TurnStage):
    def __init__(self, extraction_service: ExtractionService):
        self.extraction = extraction_service

# graph_update_stage.py
from src.services.graph_service import GraphService

class GraphUpdateStage(TurnStage):
    def __init__(self, graph_service: GraphService):
        self.graph = graph_service

# state_computation_stage.py
from src.services.graph_service import GraphService

class StateComputationStage(TurnStage):
    def __init__(self, graph_service: GraphService):
        self.graph = graph_service

# question_generation_stage.py
from src.services.question_service import QuestionService

class QuestionGenerationStage(TurnStage):
    def __init__(self, question_service: QuestionService):
        self.question = question_service

# continuation_stage.py
from src.services.question_service import QuestionService
from src.services.focus_selection_service import FocusSelectionService

class ContinuationStage(TurnStage):
    def __init__(
        self,
        question_service: QuestionService,
        focus_selection_service: FocusSelectionService,
    ):
        self.question = question_service
        self.focus_selection = focus_selection_service
        self._tracking: Dict[str, _SessionSaturationState] = {}
```

### Acceptance Criteria
- [ ] All stage constructors have type annotations
- [ ] Imports are added for type hints
- [ ] `pyright` reports no type errors
- [ ] Dependencies are clear from constructor signatures

---

## Testing Strategy

After each step:
1. Run `pyright src/` - ensure no type errors
2. Run `ruff check src/` - ensure no lint errors
3. Run `pytest tests/` - ensure no test regressions

After all steps:
1. Run full test suite
2. Verify all domain logic is consolidated per the plan
3. Code review to confirm no scattered logic remains

---

## Dependency Order

Steps should be executed in order:
1. **Step 1** (FocusSelectionService) - No dependencies
2. **Step 2** (Phase Detection) - No dependencies
3. **Step 3** (Saturation) - Depends on pipeline being stable
4. **Step 4** (LLM Clients) - No dependencies
5. **Step 5** (Type Annotations) - Should be done last as it touches all stages

Steps 1, 2, and 4 can be done in parallel if needed.
