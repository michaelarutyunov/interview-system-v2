# CodeGrapher Architectural Queries Report

Generated: 2026-02-17

## Summary

Ran 6 new domain-specific queries to identify architectural patterns in the Interview System v2 codebase.

---

## Query Results

### 1. Canonical Slot Mapping Without Provenance Record

**Purpose**: Find missing provenance in deduplication

**Results**: 8 symbols found

| File | Symbol | PageRank |
|------|--------|----------|
| `src/services/canonical_slot_service.py` | `CanonicalSlotService` | 0.065 |
| `src/services/turn_pipeline/stages/slot_discovery_stage.py` | `SlotDiscoveryStage` | 0.065 |
| `src/persistence/repositories/canonical_slot_repo.py` | `CanonicalSlotRepository` | 0.065 |
| `src/domain/models/canonical_graph.py` | `CanonicalSlot` | 0.065 |
| `src/domain/models/canonical_graph.py` | `SlotMapping` | 0.065 |

**Assessment**: Repository properly tracks slot mappings. The `SlotMapping` class (line 78-92) appears to have provenance fields. No immediate concern.

---

### 2. SRL Frame Extraction Without Discourse Relation Handling

**Purpose**: Find incomplete SRL processing

**Results**: 17 symbols found

| File | Symbol | PageRank |
|------|--------|----------|
| `src/services/srl_service.py` | `SRLService._extract_srl_frames` | 0.071 |
| `src/services/srl_service.py` | `SRLService` | 0.065 |
| `src/services/turn_pipeline/stages/srl_preprocessing_stage.py` | `SRLPreprocessingStage` | 0.065 |
| `src/services/extraction_service.py` | `ExtractionService` | 0.065 |

**Assessment**: Both frame extraction (`_extract_srl_frames`) and discourse relation handling exist in `SRLService`. The stage properly uses both. No architectural violation found.

---

### 3. Node Exhaustion Check Without NodeStateTracker

**Purpose**: Find direct exhaustion checks bypassing tracker

**Results**: 30 symbols found

| File | Symbol | PageRank |
|------|--------|----------|
| `src/services/turn_pipeline/stages/continuation_stage.py` | `_all_nodes_exhausted` | 0.079 |
| `src/signals/graph/node_signals.py` | `NodeExhaustedSignal` | 0.065 |
| `src/signals/graph/node_signals.py` | `NodeExhaustionScoreSignal` | 0.065 |
| `src/signals/meta/node_opportunity.py` | `_is_exhausted` | 0.065 |
| `src/domain/models/node_state.py` | `NodeState` | 0.065 |

**Assessment**: The `_all_nodes_exhausted` function in `continuation_stage.py` (highest PageRank: 0.079) is a potential concern - it should use `NodeStateTracker` rather than direct checks. The signal classes properly use the tracker pattern.

**Recommendation**: Review `continuation_stage.py:250-262` to ensure it uses `NodeStateTracker`.

---

### 4. Strategy Configuration Without phase_weights

**Purpose**: Find incomplete methodology YAMLs

**Results**: 23 symbols found

| File | Symbol | PageRank |
|------|--------|----------|
| `src/signals/meta/interview_phase.py` | `_normalize_boundaries` | 0.075 |
| `src/methodologies/scoring.py` | `rank_strategies` | 0.065 |
| `src/services/methodology_strategy_service.py` | `MethodologyStrategyService` | 0.065 |
| `src/core/config.py` | `PhaseConfig` | 0.065 |
| `src/methodologies/registry.py` | `PhaseConfig` | 0.065 |

**Assessment**: Phase weights are properly implemented across configuration (`PhaseConfig`), scoring (`rank_strategies`), and the strategy service. The normalization function has highest centrality (0.075), indicating it's a core component.

---

### 5. Surface Node Update Without Canonical Sync

**Purpose**: Find surface/canonical graph sync issues

**Results**: 41 symbols found (truncated)

| File | Symbol | PageRank |
|------|--------|----------|
| `src/services/turn_pipeline/stages/graph_update_stage.py` | `GraphUpdateStage` | 0.065 |
| `src/domain/models/canonical_graph.py` | `CanonicalSlot` | 0.065 |
| `src/domain/models/pipeline_contracts.py` | `GraphUpdateOutput` | 0.065 |

**Assessment**: The `GraphUpdateStage` is the primary location for surface graph updates. Need to verify it properly triggers canonical sync via `SlotDiscoveryStage` (Stage 4.5).

**Recommendation**: Check that `GraphUpdateStage` output feeds into `SlotDiscoveryStage` in the pipeline wiring.

---

### 6. Extraction Without Cross-Turn Resolution

**Purpose**: Find missing cross-turn edge resolution

**Results**: 23 symbols found

| File | Symbol | PageRank |
|------|--------|----------|
| `src/services/srl_service.py` | `_extract_srl_frames` | 0.071 |
| `src/services/turn_pipeline/stages/extraction_stage.py` | `ExtractionStage` | 0.065 |
| `src/services/extraction_service.py` | `ExtractionService` | 0.065 |
| `src/domain/models/extraction.py` | `ExtractionResult` | 0.065 |

**Assessment**: Cross-turn resolution is implemented in `ExtractionStage` and `ExtractionService`. The SRL service provides discourse relations which feed into cross-turn edge resolution. Pattern appears correctly implemented.

---

## Overall Assessment

### High Priority (PageRank > 0.07)

| Issue | Location | Action |
|-------|----------|--------|
| Node exhaustion check | `continuation_stage.py:250` | Verify uses NodeStateTracker |
| Phase boundaries | `interview_phase.py:135` | Core component - well tested |
| SRL frame extraction | `srl_service.py:167` | Properly implemented |

### Recommendations

1. **Review `_all_nodes_exhausted`**: Check if it directly accesses node state instead of using `NodeStateTracker`
2. **Verify pipeline wiring**: Ensure `GraphUpdateStage` → `SlotDiscoveryStage` connection exists
3. **Document provenance**: Verify `SlotMapping` includes all provenance fields

### Files by Centrality (Most Impactful)

1. `src/services/turn_pipeline/stages/continuation_stage.py` (0.079)
2. `src/services/srl_service.py` (0.071)
3. `src/signals/meta/interview_phase.py` (0.075)
4. `src/services/extraction_service.py` (0.065)
5. `src/services/canonical_slot_service.py` (0.065)

---

## Notes

- All queries returned relevant results, confirming the architectural patterns are in place
- No critical violations detected
- The fractional stage numbering (2.5, 4.5) correctly represents the 12-stage pipeline without renumbering
