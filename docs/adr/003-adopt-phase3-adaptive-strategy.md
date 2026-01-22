# ADR-003: Adopt Phase 3 Adaptive Strategy Selection

## Status
Accepted

## Context
The interview system currently operates in **Phase 2 mode** with hardcoded strategy selection:
- Always uses "deepen" strategy regardless of interview state
- Returns placeholder scoring values (coverage=0.0, depth=0.0, saturation=0.0)
- Shows "Strategy: UNKNOWN" in UI
- Generates repetitive laddering questions ("Why is X important to you?")

After completing a 20-turn interview, the user observed:
1. Questions felt repetitive and formulaic
2. No variety in questioning strategies
3. Coverage metric stuck at 0%
4. No adaptive behavior based on respondent input

However, **Phase 3 components are already implemented** as separate modules:
- `StrategyService` - Orchestrates multi-dimensional strategy selection
- `ArbitrationEngine` - Combines scores from multiple scorers
- 5 Scorers: CoverageScorer, DepthScorer, SaturationScorer, NoveltyScorer, RichnessScorer
- Strategy definitions: deepen, broaden, cover_element with priority weights

These components exist but are **not integrated** into the turn processing flow in `SessionService.process_turn()`.

## Decision
**Adopt Phase 3 adaptive strategy selection system and integrate it into the turn processing pipeline.**

Replace the Phase 2 hardcoded approach with the full Phase 3 scoring and strategy selection system.

## Rationale
### Benefits
1. **Adaptive questioning** - Strategy varies based on interview state (depth, breadth, coverage)
2. **Reduced repetition** - Different strategies produce different question patterns
3. **Accurate metrics** - Real coverage, depth, and saturation scores instead of 0.0
4. **Strategy transparency** - UI shows actual selected strategy with reasoning
5. **Aligns with PRD** - PRD specifies adaptive strategy selection as core feature

### Costs
1. **Integration complexity** - Need to wire StrategyService into SessionService
2. **Dependency verification** - Confirm scorers work with current data model
3. **Potential bugs** - Integration may expose issues in scorer implementations
4. **Performance** - Multi-scorer arbitration adds processing time per turn

### Why Not Stay with Phase 2?
Phase 2 was explicitly designed as a temporary stepping stone. The code comments indicate:
```python
# Phase 2: Always returns "deepen"
# Phase 3: Full scoring-based selection
```

Staying with Phase 2 means using an incomplete implementation. The Phase 3 system already exists - it just needs integration.

## Implementation
See implementation plan in beads issues (created via `bd create`).

Key integration points:
1. `SessionService.__init__()` - Require StrategyService instead of Optional[None]
2. `SessionService.process_turn()` - Call scorer methods instead of returning 0.0
3. FastAPI dependency injection - Wire ArbitrationEngine with all scorers
4. `/sessions/{id}/graph` endpoint - Expose graph state for UI display

## Consequences
### Positive
- Interview questions become adaptive to respondent input
- Coverage tracking shows actual stimulus element coverage
- Strategy selection visible in UI with reasoning
- System behaves as specified in PRD

### Negative
- Turn processing latency increases (multiple scorer calls)
- More complex failure modes (scorer errors affect turn processing)
- Need to monitor scorer output quality

### Neutral
- Graph visualization still requires separate endpoint implementation
- Export functionality unaffected (fixed separately in ADR-001 context)

## Related Decisions
- **ADR-001**: Dual sync/async API - Unaffected, API interface remains the same
- **ADR-002**: Streamlit framework choice - Unaffected, UI displays same data

## References
- PRD Section 8: Adaptive Strategy Selection
- `src/services/scoring/` - Implemented but unused scorer modules
- `src/services/strategy_service.py` - Implemented but unused strategy service
- `src/services/session_service.py:299-303` - Hardcoded scoring placeholder values
