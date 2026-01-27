# ADR-010: Formalize Pipeline Contracts and Strengthen GraphState Data Model

## Status
**Proposed** | 2025-01-26

## Context

### Current Problems

**Problem 1: Documentation-Only Contracts**
Pipeline contracts exist only as markdown documentation (`docs/pipeline_contracts.md`). This has led to bugs:

- **Stale state bug**: `coverage_state` computed in Stage 1 (ContextLoadingStage) is used in Stage 6 (StrategySelectionStage), but doesn't include concepts extracted in Stage 3. This causes wrong strategy selection.
- **No type safety**: Stages read from `context.properties` dict with no compile-time checking
- **No runtime validation**: Invalid data can flow between stages undetected

**Problem 2: GraphState Data Model Gaps**

The current `GraphState` model has several weaknesses discovered during pipeline analysis:

1. **Generic `properties: dict` too flexible**
   - Used for: `turn_count`, `strategy_history`, `phase`, `sentiments`
   - No type safety - typos not caught at development time
   - Cannot determine what fields stages actually require

2. **Depth metrics incomplete**
   - Only `max_depth` (single integer)
   - Missing: `avg_depth`, `depth_by_element`, `longest_chain_path`
   - Limits scoring accuracy (DepthBreadthBalanceScorer needs per-element depth)

3. **Coverage state optionality unclear**
   - Sometimes required, sometimes optional
   - No clear contract when it's present vs absent
   - Leads to None-checks scattered through code

4. **Saturation metrics missing**
   - `SaturationScorer` computes: `chao1_ratio`, `new_info_rate`, `consecutive_low_info`
   - These metrics aren't stored in `GraphState`
   - Must be recomputed or lost between turns

### Why This Matters Now

The two-tier scoring system (ADR-004) and adaptive strategy selection (ADR-003) depend heavily on accurate graph state. Weak data contracts directly impact interview quality.

## Decision

We will **formalize all pipeline stage contracts as Pydantic models** and **strengthen the GraphState data model** to address the gaps identified above.

### Part 1: Formalize Pipeline Contracts

**Represent each stage's input and output as explicit Pydantic models:**

```python
# Example: Stage contracts
class ContextLoadingOutput(BaseModel):
    """Contract: ContextLoadingStage MUST provide these outputs."""
    methodology: Methodology
    graph_state: GraphState  # With strengthened data model
    recent_nodes: list[Node]
    turn_number: int
    mode: str
    max_turns: int

class StateComputationOutput(BaseModel):
    """Contract: StateComputationStage MUST provide FRESH state."""
    graph_state: GraphState
    recent_nodes: list[Node]
    computed_at: datetime  # For freshness checking

class StrategySelectionInput(BaseModel):
    """Contract: StrategySelectionStage requirements."""
    graph_state: GraphState
    recent_nodes: list[Node]
    extraction: ExtractionResult
    conversation_history: list[dict]
    turn_number: int

    @model_validator(mode='after')
    def verify_state_freshness(self) -> 'StrategySelectionInput':
        """Ensure state isn't stale relative to extraction."""
        if self.graph_state.computed_at < self.extraction.timestamp:
            raise ValueError(
                f"State is stale! Computed {self.extraction.timestamp - self.graph_state.computed_at} "
                "before extraction. StrategySelection requires fresh state from StateComputation."
            )
        return self
```

**Benefits:**
- Pyright catches contract violations during development
- Runtime validation prevents invalid data flow
- Self-documenting (models = contracts)
- Freshness validation prevents the stale state bug

### Part 2: Strengthen GraphState Data Model

**Replace generic `properties: dict` with typed fields:**

```python
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_validator

class DepthMetrics(BaseModel):
    """Depth analysis of the knowledge graph."""
    max_depth: int = Field(description="Length of longest reasoning chain")
    avg_depth: float = Field(description="Average depth across all nodes")
    depth_by_element: Dict[str, float] = Field(
        description="Average depth per element ID",
        default_factory=dict
    )
    longest_chain_path: List[str] = Field(
        description="Node IDs in the deepest chain",
        default_factory=list
    )

class SaturationMetrics(BaseModel):
    """Information saturation indicators."""
    chao1_ratio: float = Field(description="Chao1 diversity estimator (0-1)")
    new_info_rate: float = Field(description="Rate of novel concept introduction")
    consecutive_low_info: int = Field(description="Turns since last novel concept")
    is_saturated: bool = Field(description="Derived: indicates topic exhaustion")

class GraphState(BaseModel):
    """Complete state of the interview knowledge graph."""

    # === Basic Counts ===
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    orphan_count: int = Field(ge=0, default=0)

    # === Structured Metrics ===
    depth_metrics: DepthMetrics
    saturation_metrics: Optional[SaturationMetrics] = None

    # === Coverage ===
    coverage_state: CoverageState  # Required for coverage-driven mode

    # === Phase Tracking ===
    current_phase: Literal['exploratory', 'focused', 'closing']
    turn_count: int = Field(ge=0, default=0)
    strategy_history: List[str] = Field(default_factory=list)

    # === Extensibility ===
    extended_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Experimental metrics not yet promoted to first-class fields"
    )

    @model_validator(mode='after')
    def validate_consistency(self) -> 'GraphState':
        """Validate internal consistency."""
        # Count consistency
        if sum(self.nodes_by_type.values()) != self.node_count:
            raise ValueError(
                f"node_count ({self.node_count}) must equal sum of nodes_by_type "
                f"({sum(self.nodes_by_type.values())})"
            )

        # Phase-turn sanity check
        if self.current_phase == 'closing' and self.turn_count < 3:
            logger.warning(
                f"Closing phase at turn {self.turn_count} - unusually early",
                extra={'turn_count': self.turn_count, 'phase': self.current_phase}
            )

        return self
```

**Key design decisions:**

1. **`extended_properties` escape hatch** - Allows future metrics without breaking changes
2. **`saturation_metrics: Optional[...]`** - Expensive to compute, not always needed
3. **`current_phase: Literal[...]`** - Type-safe enum alternatives
4. **`coverage_state` required** - Makes contract explicit for coverage-driven mode
5. **Validation in `@model_validator`** - Catches inconsistencies early

### Part 3: Migration Strategy

**Phase 1: Create models alongside existing code (Week 1)**
```python
# Create new models file
# src/domain/models/pipeline_contracts.py

# Keep existing PipelineContext working
class PipelineContext:
    # Existing implementation
    properties: Dict[str, Any]  # Still works

# Add new Pydantic models
class GraphState(BaseModel):
    # New implementation
    turn_count: int  # Typed field
```

**Phase 2: Update stages incrementally (Weeks 2-3)**
1. Start with stages that have known bugs (StateComputation, StrategySelection)
2. Update one stage at a time
3. Run tests after each change
4. Keep old fields temporarily with `@deprecated` decorator

**Phase 3: Remove deprecated fields (Week 4)**
1. Verify all stages use new models
2. Remove old `properties` dict access patterns
3. Delete markdown contracts (docs/pipeline_contracts.md)

## Consequences

### Positive

1. **Type safety** - Pyright catches contract violations during development
2. **Runtime validation** - Pydantic validates data at stage boundaries
3. **Self-documenting** - Models are the contracts, no separate documentation needed
4. **Bug prevention** - Freshness validation prevents stale state bugs
5. **Complete metrics** - Depth and saturation metrics improve scoring accuracy
6. **IDE support** - Auto-completion and refactoring tools work better
7. **Testability** - Easier to create valid test fixtures

### Negative

1. **Boilerplate** - ~10 models for 10 pipeline stages
2. **Breaking changes** - All code accessing `properties['turn_count']` must update
3. **Refactoring cost** - Changing contracts affects multiple stages
4. **Migration effort** - ~3-4 weeks of incremental work
5. **Learning curve** - Team must understand Pydantic validation model

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes in production | Incremental migration, keep old fields temporarily |
| Extended_properties abuse | Add lint rule: "Prefer typed fields over extended_properties" |
| Performance overhead from validation | Pydantic validation is fast (<1ms per model) |
| Optional saturation_metrics complexity | Clear documentation: when to compute vs skip |

## Alternatives Considered

### Alternative 1: Type stubs (.pyi files) only
**Description:** Add type hints without runtime validation

**Rejected because:**
- No runtime validation (bugs still slip through)
- Requires maintaining separate .pyi files
- Less discoverable than inline models

### Alternative 2: Keep markdown contracts, add assertions
**Description:** Keep current approach, add manual validation in stages

**Rejected because:**
- Already failed (stale state bug occurred with markdown contracts)
- Manual assertions inconsistent across stages
- No compile-time checking

### Alternative 3: Data model improvements only, no contract formalization
**Description:** Fix GraphState but keep pipeline contracts as-is

**Rejected because:**
- Doesn't prevent contract violation bugs
- Type safety at GraphState level doesn't help stage interfaces
- Misses the core problem: no validation between stages

### Alternative 4: Fully rigid models (no extended_properties)
**Description:** No escape hatch, all fields must be predefined

**Rejected because:**
- Too rigid for experimental features
- Every new metric requires breaking change
- Hinders rapid iteration

## References

- [ADR-004: Two-Tier Scoring System](./004-two-tier-scoring-system.md) - Depends on accurate graph state
- [ADR-008: Concept-Element Coverage System](./008-concept-element-coverage-system.md) - Defines coverage_state
- [docs/pipeline_contracts.md](../pipeline_contracts.md) - Existing markdown contracts (to be replaced)
- [src/services/scoring/two_tier/base.py](../src/services/scoring/two_tier/base.py) - Pydantic pattern to follow

## Implementation Checklist

- [ ] Create `src/domain/models/pipeline_contracts.py` with stage input/output models
- [ ] Create `src/domain/models/graph_state.py` with strengthened GraphState
- [ ] Update StateComputationStage to output StateComputationOutput
- [ ] Update StrategySelectionStage to require StrategySelectionInput
- [ ] Add freshness validation between StateComputation and StrategySelection
- [ ] Update graph repository to compute DepthMetrics and SaturationMetrics
- [ ] Migrate all stages from `properties` dict to typed fields
- [ ] Add tests for contract validation
- [ ] Remove deprecated `properties` dict access patterns
- [ ] Delete `docs/pipeline_contracts.md` (models are now the contracts)
- [ ] Update development documentation to reference models, not markdown
