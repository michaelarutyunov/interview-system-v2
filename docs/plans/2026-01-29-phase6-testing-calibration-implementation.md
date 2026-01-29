# Phase 6: Testing, Calibration, and Signal Weight Tuning Implementation Plan

**Status:** Ready for Implementation
**Date:** 2026-01-29
**Parent Bead:** interview-system-v2-dlm

## Overview

Comprehensive testing, calibration, and signal weight tuning for the node exhaustion system. This phase ensures all components work together correctly and signal weights are calibrated for optimal interview behavior.

## Tasks

### Task 1: Create Synthetic Interview Scenarios

**File:** `tests/synthetic/scenarios/node_exhaustion_scenarios.py` (new)

**Scenarios to test:**

1. **Exhaustion Detection**: Interview that exhausts a node, then backtracks
2. **Multi-Branch Exploration**: Interview that explores multiple branches
3. **Uncertainty Response**: Interview with hedging/uncertain responses
4. **Fatigue Recovery**: Interview with shallow responses, then revitalization
5. **Phase Transitions**: Interview that progresses through early → mid → late
6. **Orphan Node Priority**: Interview that prioritizes orphan nodes
7. **Probe Deeper Opportunity**: Deep responses without yield
8. **Strategy Repetition**: Same strategy used repeatedly on same node

**Format:**
```python
@dataclass
class InterviewScenario:
    """Test scenario for synthetic interviews."""
    name: str
    description: str
    user_responses: List[str]  # Simulated user responses
    expected_behaviors: List[str]  # Expected system behaviors
    turn_count: int
```

### Task 2: Implement Synthetic Interview Runner

**File:** `tests/synthetic/runner/node_exhaustion_test_runner.py` (new)

**Purpose:** Run synthetic interviews through the full pipeline and capture results.

**Implementation:**
```python
class NodeExhaustionTestRunner:
    """Run synthetic interviews to validate node exhaustion behavior."""

    async def run_scenario(
        self, scenario: InterviewScenario
    ) -> InterviewResult:
        """Run a scenario and capture results."""
        pass

    def validate_exhaustion_detection(
        self, result: InterviewResult
    ) -> bool:
        """Verify exhausted nodes are deprioritized."""
        pass

    def validate_backtracking(
        self, result: InterviewResult
    ) -> bool:
        """Verify system backtracks to non-exhausted nodes."""
        pass
```

### Task 3: Add End-to-End Pipeline Tests

**File:** `tests/integration/test_node_exhaustion_e2e.py` (new)

**Test cases:**
- Full interview with node exhaustion
- Full interview with uncertainty triggers
- Full interview with phase transitions
- Full interview with fatigue detection
- Validate node state tracking accuracy
- Validate signal detection accuracy
- Validate strategy selection behavior

### Task 4: Signal Weight Calibration Suite

**File:** `tests/calibration/test_signal_weights.py` (new)

**Purpose:** Test various signal weight configurations to find optimal values.

**Approach:**
```python
@dataclass
class WeightConfiguration:
    """Configuration for signal weight testing."""
    name: str
    weights: Dict[str, float]  # Signal weight modifications
    expected_behavior: str

# Test different weight combinations
test_configurations = [
    WeightConfiguration(
        name="high_exhaustion_penalty",
        weights={"graph.node.exhausted.true": -2.0},
        expected_behavior="aggressive_backtracking"
    ),
    WeightConfiguration(
        name="low_exhaustion_penalty",
        weights={"graph.node.exhausted.true": -0.5},
        expected_behavior="conservative_backtracking"
    ),
    # ... more configurations
]
```

### Task 5: Performance Testing

**File:** `tests/performance/test_node_exhaustion_performance.py` (new)

**Metrics:**
- Signal detection latency
- Joint scoring performance with N nodes
- Memory usage of NodeStateTracker
- Total turn processing time

**Benchmarks:**
- 10 nodes, 4 strategies
- 50 nodes, 4 strategies
- 100 nodes, 4 strategies

### Task 6: Documentation Updates

**Files to update:**
- `docs/SYSTEM_DESIGN.md` - Update architecture diagrams
- `docs/ADR/ADR-014-signal-pools-architecture.md` - Add node signals section
- `README.md` - Add overview of new features
- `docs/plans/2026-01-29-node-exhaustion-backtracking-design.md` - Mark as implemented

**Content:**
- Architecture overview of node exhaustion system
- Signal reference documentation
- YAML configuration guide
- Phase-based configuration guide
- Troubleshooting guide

### Task 7: Create Calibration Report

**File:** `docs/reports/2026-01-29-calibration-report.md` (new)

**Contents:**
- Summary of test results
- Signal weight recommendations
- Known issues and limitations
- Performance characteristics
- Future improvements

## Success Criteria

- [ ] All synthetic interview scenarios pass
- [ ] End-to-end pipeline tests pass
- [ ] Performance benchmarks acceptable (< 1s per turn)
- [ ] Signal weight calibration completed
- [ ] Documentation updated
- [ ] Calibration report created
- [ ] No critical bugs
- [ ] Code quality checks pass

## Dependencies

- Phase 1-5: All previous phases ✅

## Test Coverage Goals

- Unit tests: > 80% coverage
- Integration tests: All major flows covered
- E2E tests: All scenarios covered
- Performance tests: Key metrics validated

## Calibration Process

1. **Baseline Testing**: Run all tests with initial weights
2. **Issue Identification**: Identify behaviors that need adjustment
3. **Weight Tuning**: Adjust signal weights in YAML configs
4. **Validation**: Re-run tests to verify improvements
5. **Iteration**: Repeat until behaviors are acceptable

## Known Issues to Address

1. **LLM Infrastructure**: HedgingLanguageSignal uses heuristics; real LLM integration pending (bead interview-system-v2-1xx)
2. **Exhaustion Threshold**: May need tuning based on interview length
3. **Phase Boundaries**: Early/mid/late thresholds may need calibration
4. **Recency Decay**: 20-turn decay may need adjustment

## Performance Targets

| Metric | Target | Acceptable |
|--------|--------|------------|
| Signal detection (all) | < 100ms | < 200ms |
| Joint scoring (10 nodes) | < 50ms | < 100ms |
| Joint scoring (50 nodes) | < 150ms | < 300ms |
| Total turn processing | < 500ms | < 1s |

## Documentation Requirements

- Update system architecture diagrams
- Add signal reference guide
- Document phase configuration
- Create troubleshooting guide
- Add calibration report

## Final Deliverables

1. All tests passing (unit, integration, e2e, performance)
2. Calibrated signal weights in YAML configs
3. Updated documentation
4. Calibration report
5. Performance benchmark results
6. Known issues and future work documented

## Next Steps After Phase 6

- Merge feature branch to main
- Deploy to staging/production
- Monitor interview quality metrics
- Collect feedback for further calibration
- Plan Phase 7 improvements (if needed)
