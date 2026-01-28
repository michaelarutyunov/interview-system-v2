# ADR-013: Methodology-Centric Architecture

## Status
Accepted

## Context
The original two-tier scoring system (ADR-004, ADR-006) was generic but complex:
- 15+ scorers with weighted combinations across two tiers
- Hard to understand which signals mattered for each methodology
- Strategies were methodology-agnostic, configured via YAML
- Signal→strategy mapping was indirect and hard to debug

After implementing MEC and JTBD methodologies, we determined:
- Real qualitative methodologies have specific strategies (MEC has laddering, JTBD has dimension exploration)
- Signals are methodology-dependent
- Simpler direct signal→strategy scoring is sufficient
- The two-tier system added unnecessary complexity

## Decision
Refactor to methodology-centric architecture where each methodology is a self-contained module with:
- Methodology-specific signals (~8-10 per methodology)
- Methodology-specific strategies (defined in code, not YAML)
- Direct signal→strategy scoring (no two-tier complexity)

### Architecture Changes

**Before (Two-Tier):**
```
Generic Scorers (15+) → Veto Tier → Weighted Tier → Strategy Selection
├─ Tier 1: Knowledge ceiling, element exhausted, recent redundancy
├─ Tier 2: Coverage gap, ambiguity, depth/breadth, engagement, novelty, etc.
└─ Config: config/interview_config.yaml (strategies + weights)
```

**After (Methodology-Centric):**
```
Methodology Module → Signal Detection → Strategy Scoring → Selection
├─ MEC Module: 8 signals, 4 strategies
│  └─ Signals: missing_terminal_value, ladder_depth, coverage_breadth, etc.
│  └─ Strategies: ladder_deeper, clarify_relationship, explore_new_attribute, reflect_and_validate
└─ JTBD Module: 14 signals, 6 strategies
   └─ Signals: job_identified, situation_depth, motivation_depth, etc.
   └─ Strategies: explore_situation, probe_alternatives, dig_motivation, uncover_obstacles, validate_outcome, balance_coverage
```

### File Structure

```
src/methodologies/
├── __init__.py           # Registry and loader
├── base.py               # Base classes (SignalState, BaseSignalDetector, BaseStrategy)
├── scoring.py            # Generic scoring logic
├── means_end_chain/
│   ├── __init__.py       # MECModule class
│   ├── signals.py        # MECSignalDetector
│   ├── utils.py          # MEC utilities (calculate_mec_chain_depth)
│   └── strategies/
│       ├── ladder_deeper.py
│       ├── clarify_relationship.py
│       ├── explore_new_attribute.py
│       └── reflect_and_validate.py
└── jtbd/
    ├── __init__.py       # JTBDModule class
    ├── signals.py        # JTBDSignalDetector
    └── strategies/
        ├── explore_situation.py
        ├── probe_alternatives.py
        ├── dig_motivation.py
        ├── uncover_obstacles.py
        ├── validate_outcome.py
        └── balance_coverage.py
```

## Implementation

### Phase 1: Base Structure
- Created `src/methodologies/base.py` with base classes
- Created `src/methodologies/scoring.py` with generic scoring logic
- Created `src/methodologies/__init__.py` with registry
- Commit: `3b0c575`

### Phase 2: MEC Module
- Implemented `MECSignalDetector` with 8 MEC-specific signals
- Implemented 4 MEC strategies with signal weights
- Commit: `1861361`

### Phase 3: JTBD Module
- Implemented `JTBDSignalDetector` with 14 JTBD-specific signals
- Implemented 6 JTBD strategies with signal weights
- Commit: `c42b88f`

### Phase 4: Pipeline Integration
- Created `MethodologyStrategyService` for strategy selection
- Updated `StrategySelectionStage` to use methodology service
- Added `signals` and `strategy_alternatives` to PipelineContext
- Updated pipeline contracts
- Commit: `8c0e8fd` (included with Phase 5)

### Phase 5: UI Updates
- Updated scoring panel to display methodology-specific signals
- Added methodology metrics panel
- Integrated signals and strategy alternatives into UI
- Commit: `8c0e8fd`

### Phase 6: Cleanup
- Deleted old two-tier scoring directories (tier1/, tier2/, two_tier/)
- Deleted old scoring utilities (llm_signals.py, signal_helpers.py, graph_utils.py)
- Updated imports and removed old dependencies
- Preserved `calculate_mec_chain_depth` in `src/methodologies/means_end_chain/utils.py`
- Commit: `4d47767`

### Phase 7: Verification
- Created integration tests for both MEC and JTBD
- All 8 integration tests pass
- All 30 pipeline tests pass
- Commit: (pending)

## Consequences

### Positive
- **Clearer mental model**: Methodology is the organizing unit
- **Easier to add methodologies**: Copy module structure, implement signals/strategies
- **Simpler scoring logic**: Direct signal→strategy scoring, no two-tier complexity
- **Better observability**: Signals directly tied to strategies via weights
- **Code reduction**: Removed 6899 lines, added 444 lines (net -6455 lines)
- **Type safety**: Pydantic models for signals and strategies

### Negative
- **Some code duplication**: Each methodology implements similar patterns
- **More files**: Signals and strategies split across multiple files
- **Learning curve**: New structure takes time to understand
- **Migration effort**: Required updating all pipeline stages and UI components

### Neutral
- **YAML config less important**: Strategies defined in code, not config
- **Signal weights in code**: Not editable without deployment (simpler for now)

## Migration Guide

### Adding a New Methodology

1. Create module directory: `src/methodologies/my_methodology/`
2. Implement signal detector extending `BaseSignalDetector`
3. Implement strategies extending `BaseStrategy`
4. Create module class extending `MethodologyModule`
5. Register in `src/methodologies/__init__.py`

Example:
```python
# src/methodologies/my_methodology/__init__.py
class MyMethodologyModule(MethodologyModule):
    name = "my_methodology"
    schema_path = "config/methodologies/my_methodology.yaml"

    def get_strategies(self):
        return [StrategyA, StrategyB]

    def get_signal_detector(self):
        return MySignalDetector()
```

## References

- Plan: `.claude/plans/zany-bubbling-fog.md`
- ADR-004: Two-Tier Scoring System (superseded)
- ADR-006: Enhanced Scoring Architecture (superseded)
- ADR-008: Concept Element Coverage System (preserved)
- ADR-010: Pipeline Contracts (preserved)
