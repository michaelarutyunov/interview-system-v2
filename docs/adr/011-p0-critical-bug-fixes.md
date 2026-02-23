# ADR-011: P0 Critical Bug Fixes - Methodology, Coverage, and Depth

## Status
**Implemented** | 2026-01-27

## Context

Session diagnostic analysis (session f8eda94b) revealed three P0 critical bugs that prevented the interview system from functioning correctly:

### Problem 1: Methodology Mismatch
**Symptom**: Sessions configured as `jobs_to_be_done` were extracting `means_end_chain` node types (attribute, functional_consequence) instead of JTBD types (job_statement, pain_point, gain_point).

**Root Cause**:
- `ExtractionService.__init__()` had hardcoded default: `methodology="means_end_chain"`
- `ExtractionStage.process()` only updated `concept_id` from session context, never `methodology`
- When SessionService created ExtractionService without args, it defaulted to MEC

**Impact**: All JTBD sessions produced invalid graph structures with wrong node types.

### Problem 2: Coverage State NULL
**Symptom**: `graph_state.coverage_state` was NULL throughout session, causing:
- `CoverageGapScorer` showed "Addresses 0 coverage gap(s)" for all strategies
- `cover_element` strategy generated zero focuses (element_id=None)
- Coverage plateaued at 50% - system had zero capability to push toward uncovered elements

**Root Cause**: Silent failure in `GraphRepository._build_coverage_state()`:
- Concept file loading failed silently
- No diagnostic logging to trace where loading failed
- No fallback when coverage_state is NULL

**Impact**: Coverage-driven interview mode was completely non-functional.

### Problem 3: Depth Metric Regression
**Symptom**: Depth declined 0.20 → 0.16 during "deepen" phase (turns 5-9), opposite of expected behavior.

**Root Causes** (three interconnected):
1. **Conversational implicit extraction missing**: Laddering Q&A didn't create edges
   - Interviewer: "Why does X matter?"
   - User: "Because Y"
   - Expected: Create X→Y edge
   - Actual: No edge created, only extracted Y as isolated node

2. **Average depth dilution**: New shallow nodes lowered average despite deep chains existing

3. **Chain depth not computed**: StateComputationStage didn't compute MEC chain metrics

**Impact**: "Deepen" strategy failed to achieve its outcome - depth decreased instead of increased.

## Decision

Implement emergency fixes for all three P0 bugs with defensive programming and diagnostic improvements.

### Fix 1: Methodology Mismatch (30 min)

**File**: `src/services/turn_pipeline/stages/extraction_stage.py`
```python
# Added methodology update from session context before extraction
if context.methodology and context.methodology != self.extraction.methodology:
    log.info("extraction_methodology_updated",
             old_methodology=self.extraction.methodology,
             new_methodology=context.methodology)
    self.extraction.methodology = context.methodology
    self.extraction.schema = load_methodology(context.methodology)
```

**File**: `src/services/extraction_service.py`
```python
# Changed from hardcoded default to Optional with warning
def __init__(self, methodology: Optional[str] = None, ...):
    if methodology is None:
        log.warning("extraction_service_no_methodology",
                   message="No methodology provided - will be set from session context")
        methodology = "means_end_chain"  # Temporary default for backward compatibility
```

### Fix 2: Coverage State Loading (2.5 hours)

**Phase 2A: Diagnostic Logging**

**File**: `src/persistence/repositories/graph_repo.py`
- Added info-level logging to `_build_coverage_state()` (start/success/failure paths)
- Added logging to `_load_concept_elements()` (file path, existence check)
- Upgraded "coverage_state_built" from debug to info with coverage percentage

**Phase 2B: Fallback Logic**

**File**: `src/services/strategy_service.py`
```python
# Enhanced three-tier fallback for cover_element strategy
if coverage_state:
    # Primary: Use coverage_state object (new format)
    ...
else:
    # Secondary: Use properties["coverage_state"] (old format)
    coverage_state_old = graph_state.properties.get("coverage_state", {})
    ...

    # Tertiary: Load concept directly when both fail
    if not uncovered:
        log.warning("coverage_state_missing_using_concept_fallback")
        concept = load_concept(concept_id)
        for element in concept.elements:
            uncovered.append(element.id)
```

### Fix 3: Depth Metrics (3.5 hours)

**Phase 3A: Conversational Implicit Extraction**

**File**: `src/llm/prompts/extraction.py`
```python
# Added explicit section on conversational implicit relationships
## Conversational Implicit Relationships (CRITICAL for laddering interviews):
When the interviewer asks a question and the respondent answers:
- **Identify the topic in the interviewer's question** (e.g., "Why does X matter?")
- **Extract the concept from the respondent's answer** (e.g., "Because it Y")
- **Create a relationship from question topic → answer concept** (X leads_to Y)
- Set confidence slightly lower (0.7-0.8) since it's implicit, not explicit

Examples:
- Interviewer: "Why does that nice sensation matter?"
  Respondent: "It feels like a good start of the day"
  → Extract relationship: "nice sensation" leads_to "good start of the day"
```

**File**: `src/services/turn_pipeline/stages/extraction_stage.py`
```python
# Enhanced _format_context_for_extraction() to highlight Q→A structure
if len(recent) >= 1 and recent[-1]["speaker"] == "system":
    interviewer_question = recent[-1]["text"]
    lines.append("")
    lines.append(f"[Most recent question] Interviewer: {interviewer_question}")
    lines.append("[Task] Extract concepts from the Respondent's answer AND create a relationship from the question's topic to the answer concept.")
```

**Phase 3B: Max Depth Metric**

**File**: `src/services/depth_calculator.py`
```python
def get_max_depth(self, element_depths: Dict[int, Dict[str, Any]]) -> float:
    """
    Calculate maximum depth across all elements (monotonically increasing).
    Use this to track deepening progress, as average depth can regress.
    """
    return max((data["depth_score"] for data in element_depths.values()), default=0.0)
```

**File**: `src/domain/models/knowledge_graph.py`
```python
class CoverageState(BaseModel):
    ...
    max_depth: float = 0.0  # P0 Fix: Maximum depth_score (monotonically increasing)
```

**File**: `src/persistence/repositories/graph_repo.py`
```python
# Compute and store max_depth in CoverageState
max_depth = depth_calculator.get_max_depth(element_depths)
coverage_state = CoverageState(
    elements=elements_dict,
    elements_covered=elements_covered,
    elements_total=len(element_ids),
    overall_depth=overall_depth,
    max_depth=max_depth,  # P0 Fix
)
```

**Phase 3C: Chain Depth Computation**

**File**: `src/services/turn_pipeline/stages/state_computation_stage.py`
```python
# Compute chain depth metrics for MEC methodologies
if context.methodology == "means_end_chain":
    nodes_raw = await self.graph.get_nodes_by_session(context.session_id)
    edges_raw = await self.graph.get_edges_by_session(context.session_id)

    nodes_dicts = [{"id": n.id, "node_type": n.node_type} for n in nodes_raw]
    edges_dicts = [{"source_node_id": e.source_node_id, "target_node_id": e.target_node_id}
                   for e in edges_raw]

    chain_depth = calculate_mec_chain_depth(edges=edges_dicts, nodes=nodes_dicts,
                                           methodology=context.methodology)
    graph_state.extended_properties["chain_depth"] = chain_depth
```

## Consequences

### Positive

1. **Methodology integrity**: JTBD sessions now produce correct node types
2. **Coverage recovery**: System can push toward uncovered elements even with NULL coverage_state
3. **Depth tracking works**:
   - Laddering creates proper Q→A edges
   - max_depth provides monotonic progress metric
   - chain_depth enables accurate MEC depth analysis
4. **Diagnostic visibility**: Info-level logging enables rapid bug diagnosis
5. **Defensive programming**: Three-tier fallback prevents total failure

### Negative

1. **Technical debt**: Temporary default "means_end_chain" still exists for backward compatibility
2. **Partial ADR-010 implementation**: Implemented emergency fixes before full contract formalization
3. **Extended_properties usage**: chain_depth stored in escape hatch instead of typed field

### Known Limitations

1. **Methodology validation**: No early validation that methodology matches concept
2. **Coverage state root cause**: Diagnostic logging added, but root cause not yet identified
3. **Max depth persistence**: Not tracked as monotonic across turns (computed fresh each time)

## Relationship to ADR-010

This ADR implements **emergency subsets** of ADR-010 (Formalize Pipeline Contracts):

| ADR-010 Proposal | ADR-011 Implementation |
|------------------|------------------------|
| Strengthen GraphState with typed fields | ✅ Added `max_depth` to CoverageState |
| Add DepthMetrics model | ⚠️ Partial: max_depth only, not full model |
| Formalize StateComputationOutput | ⚠️ Partial: added extended_properties["chain_depth"] |
| Pipeline contract Pydantic models | ❌ Not implemented (still using PipelineContext) |
| Freshness validation | ❌ Not implemented |

**Next Step**: Complete ADR-010 implementation to fully formalize contracts.

## Testing Strategy

### Test 1: Methodology Fix Verification
```bash
# Create JTBD session
curl -X POST /api/sessions -d '{"concept_id": "coffee_jtbd_v2"}'

# Verify extracted node types are JTBD (not MEC)
# Expected: job_statement, pain_point, gain_point
# Not: attribute, functional_consequence, psychosocial_consequence
```

### Test 2: Coverage State Recovery
```bash
# Run coverage_driven mode session
# Check logs for "coverage_state_built_successfully" or fallback warning
# Verify cover_element appears in scoring_candidates
# Monitor coverage progression (should exceed 50%)
```

### Test 3: Depth Metrics Validation
```bash
# Run MEC session with laddering (6-9 turns)
# Turn 6: "Why does X matter?"
# Turn 7: "Why does Y matter?" (Y from turn 6 response)
# Verify:
# - Edges created for Q→A pairs (min 3 edges for 3 laddering turns)
# - max_depth increases monotonically (0.2 → 0.4 → 0.6)
# - chain_depth metrics in graph_state.extended_properties
```

## Implementation

**Commit**: `7ea7f17` - "fix(p0): resolve methodology mismatch, coverage state, and depth metrics"
**Date**: 2026-01-27
**Files Modified**: 8 files, 212 insertions, 7 deletions

All changes passed `ruff check` and were pushed to `master` branch.

## Updates

### 2026-02-03: Technical Debt Resolved (at0)

**Commit**: `413a077` - "fix: make methodology a required parameter for ExtractionService (at0)"

The temporary default "means_end_chain" technical debt has been resolved:
- `ExtractionService.__init__()` now **requires** `methodology: str` parameter
- Removed `Optional[str]` with default and warning logic
- Updated all callers to explicitly pass methodology from session context
- Forces early validation at service creation rather than runtime

**Status**: Technical debt item #1 from "Negative" consequences is now resolved.

## References

- [ADR-007: YAML-based Methodology Schema](./007-yaml-based-methodology-schema.md) - Methodology system
- [ADR-008: Concept-Element Coverage System](./008-concept-element-coverage-system.md) - Coverage state structure
- [ADR-010: Formalize Pipeline Contracts](./010-formalize-pipeline-contracts-strengthen-data-models.md) - Future complete solution
- Session Diagnostic: `session_f8eda94b.json` - Evidence of bugs
- Implementation Plan: `/home/mikhailarutyunov/.claude/plans/swirling-wishing-pizza.md`
