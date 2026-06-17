# Domain Fidelity Review - Interview System v2

**Date**: 2026-02-09
**Reviewer**: Claude Opus 4.6 (via 3 parallel sub-agents)
**Scope**: Domain logic validation -- does the code implement structured interviews as claimed?

---

## Executive Summary

**Is this a structured interview system? YES.**

The system implements genuine adaptive structured interviews driven by:
- 4 fully functional YAML-defined research methodologies (+ 1 incomplete stub)
- 20+ graph-derived signals feeding deterministic strategy selection
- 3-phase interview progression (early/mid/late) with distinct strategy preferences
- Joint strategy-node scoring with automatic exhaustion-aware backtracking
- 6 intelligent termination conditions beyond simple turn counting

**Key findings:**
- **4 ghost features** documented but not implemented (coverage, focus_preference, LLM fallback, two-tier scoring)
- **1 dead code area**: Technique classes (`laddering.py`, `probing.py`, etc.) defined but never used
- **Pervasive doc debt**: Wrong YAML config paths, stale signal names, phantom fields in 6+ documentation files
- **All core behavioral claims verified**: exhaustion, backtracking, graph-driven adaptation, intelligent termination, dual-graph deduplication

---

## Section 1: Structured Interview Verification

### 1.1 Methodology Layer

**5 methodology YAML configs** exist in `config/methodologies/`:

| Methodology | Strategies | Techniques | Status |
|-------------|-----------|------------|--------|
| `means_end_chain` | 5 (deepen, clarify, explore, reflect, revitalize) | laddering, probing, elaboration, validation | **COMPLETE** |
| `jobs_to_be_done` | 6 (explore_situation, probe_alternatives, dig_motivation, validate_outcome, revitalize, uncover_obstacles) | probing, elaboration, laddering, validation | **COMPLETE** |
| `critical_incident` | 6 (explore_incident, explore_outcomes, explore_emotions, explore_attributions, explore_learnings, explore_behavior_change) | probing, elaboration, laddering, validation | **COMPLETE** |
| `repertory_grid` | 5 (triadic_elicitation, explore_constructs, ladder_constructs, explore_ideal, explore_similarities) | probing, laddering, elaboration, validation | **COMPLETE** |
| `customer_journey_mapping` | 0 | - | **INCOMPLETE** (ontology only, line 1 warns) |

Each methodology defines:
- Distinct **node types** (e.g., MEC: attribute → functional_consequence → psychosocial_consequence → value)
- Distinct **strategy sets** with unique signal weight vectors
- **Phase-based weight modifiers** (early/mid/late)
- **Signal normalization ranges** for numeric signals

### 1.2 Strategy Selection Is Deterministic

Strategy selection is **strictly rule-based** with zero randomness:

**Scoring formula** (`src/methodologies/scoring.py:29-52, 196-225`):
```
base_score = Σ(signal_weight × signal_value)  for each signal in strategy.signal_weights
final_score = (base_score × phase_multiplier) + phase_bonus
```

All (strategy, node) pairs are scored via Cartesian product and sorted descending. The highest-scoring pair is selected.

**Evidence**: `rank_strategy_node_pairs()` at `src/methodologies/scoring.py:196-225`

### 1.3 Phase-Based Progression

Interview behavior changes across 3 phases detected by node count:

| Phase | Trigger | Strategy Preference (MEC) |
|-------|---------|--------------------------|
| **Early** | node_count < 5 | explore: 1.5x + 0.2 bonus, deepen: 0.5x |
| **Mid** | 5 ≤ node_count < 15 | deepen: 1.3x + 0.3 bonus, clarify: 0.8x |
| **Late** | node_count ≥ 15 | reflect: 1.2x + 0.2 bonus, explore: 0.3x |

**Evidence**: Phase detection at `src/methodologies/signals/meta/interview_phase.py:131-154`; phase weights at `config/methodologies/means_end_chain.yaml:251-283`

### 1.4 Strategy Influences Question Generation

The selected strategy's **name and description** are injected into the LLM prompt:

**System prompt** (`src/llm/prompts/question.py:88-91`):
```
Your current strategy is: **{strat_name}**
Strategy: {strat_description}
```

**User prompt** includes active signals with descriptions explaining WHY the strategy was selected (`src/llm/prompts/question.py:164-179`).

Different strategies produce genuinely different questions because:
1. Strategy description tells the LLM the questioning approach
2. Focus node differs (joint scoring selects different nodes per strategy)
3. Active signals provide context about what to investigate

### 1.5 Graph State Matters

Removing the knowledge graph would break structured behavior. Graph signals directly drive strategy selection:

| Signal | Effect on Strategy | Weight |
|--------|-------------------|--------|
| `graph.node.is_orphan.true` | Boosts clarify (connect isolated concepts) | 1.0 |
| `graph.node.exhausted.false` | Boosts deepen on fresh nodes | 1.0 |
| `graph.max_depth` | Boosts reflect at high depth | 0.7 |
| `graph.chain_completion.has_complete_chain.false` | Boosts deepen for incomplete chains | 1.0 |
| `graph.orphan_count` | Boosts clarify globally | 0.7 |

---

## Section 2: Ghost Features Audit

### Ghost Features Table

| # | Feature | Status | Impact |
|---|---------|--------|--------|
| 1 | **Coverage Tracking** (CoverageState, coverage_breadth, coverage_score) | DEAD | None -- replaced by saturation metrics |
| 2 | **Element-Level Coverage** (concept_elements tracking) | DEAD | API endpoint exists but pipeline never uses it |
| 3 | **Chain Completion** | **FUNCTIONAL** (not a ghost) | Actively used in strategy scoring |
| 4 | **focus_preference** (strategy.focus_preference) | DEAD | Zero references in code/YAML. Replaced by joint strategy-node scoring |
| 5 | **LLM Fallback** (has_llm_fallback) | STUB | Contract field always `False`, no fallback logic exists |
| 6 | **Two-Tier/Veto Scoring** (tier1_results, tier2_results, vetoed_by) | DEAD (schema ghost) | Logic removed; DB schema, API schemas, repo methods remain as dead weight |
| 7 | **Customer Journey Mapping** | STUB | Ontology-only YAML, no signals/strategies/phases. Would fail at runtime |

### Ghost 1: Coverage Tracking (CONFIRMED DEAD)

**Removed from code:**
- `GraphState` model has NO `coverage_state` field (`src/domain/models/knowledge_graph.py:120-212`)
- No coverage signals exist in any signal pool
- No coverage references in any YAML methodology config
- Migration `002_remove_coverage.sql` drops concept_elements table
- Database init cleanup drops `coverage_score` columns (`src/persistence/database.py:89-102`)

**Still in documentation:**
- `CLAUDE.md:132` -- Signal table lists `coverage_breadth`
- `docs/SYSTEM_DESIGN.md:558-597` -- Entire "Coverage State Tracking" section (code examples for non-existent code)
- `docs/SYSTEM_DESIGN.md:666-669` -- GraphState shows `coverage_state: CoverageState` and `coverage_breadth: float`
- `docs/pipeline_contracts.md:550` -- `ScoringPersistenceOutput` lists `coverage_score: float`
- `docs/DEVELOPMENT.md:486` -- YAML example shows `graph.coverage_breadth: 0.6`

**Replacement**: Saturation metrics (consecutive_zero_yield, consecutive_shallow, depth_plateau) and canonical slot deduplication

### Ghost 4: focus_preference (CONFIRMED DEAD)

**Zero matches** in any `.py` or `.yaml` file. FocusSelectionService uses strategy name matching and joint strategy-node scoring, not `focus_preference`.

**Still in documentation:**
- `CLAUDE.md:141` -- "based on strategy.focus_preference"
- `docs/SYSTEM_DESIGN.md:631` -- "Select focus using strategy.focus_preference"
- `docs/DEVELOPMENT.md:480,487` -- Shows `focus_preference: shallow` and `focus_preference: recent`
- `README.md:434` -- Shows `focus_preference: deep`

### Ghost 5: LLM Fallback (STUB)

- Contract field defined: `has_llm_fallback: bool = Field(default=False)` (`src/domain/models/pipeline_contracts.py:319-321`)
- Two TODOs in `question_generation_stage.py:85,90`: "Track has_llm_fallback when QuestionService supports it"
- No actual fallback logic in QuestionService or any LLM client
- `docs/SYSTEM_DESIGN.md:1090-1094` falsely claims: "The system implements LLM fallback for reliability"

### Ghost 6: Two-Tier Scoring (SCHEMA GHOST)

**Logic removed** but infrastructure remains:
- `src/api/schemas.py:273-306` -- `Tier1ResultSchema`, `Tier2ResultSchema`, `ScoringCandidateSchema`
- `src/persistence/repositories/session_repo.py:163-255` -- `save_scoring_candidate()`, `get_turn_scoring()`, `get_all_scoring_candidates()`
- `src/persistence/migrations/001_initial.sql:161-195` -- `scoring_candidates` table with indexes
- `src/services/session_service.py:651-656` -- Reads tier results from DB
- `src/services/export_service.py:233-238` -- Exports tier results

`save_scoring_candidate()` is never called by any active pipeline code. New sessions never populate the `scoring_candidates` table.

---

## Section 3: Behavioral Claims Verification

### Claim 1: Adaptive Strategy Selection - VERIFIED

| Sub-claim | Status | Evidence |
|-----------|--------|----------|
| Graph state affects strategy scores | ✅ | 7 global + 3 canonical + 10 node-level graph signals in YAML weights |
| Response quality affects strategy | ✅ | `llm.response_depth.surface: 0.8` triggers deepen; `llm.hedging_language.high: 1.0` triggers reflect |
| Interview phases change preferences | ✅ | 3 phases with distinct multipliers + bonuses per methodology |

### Claim 2: Node Exhaustion & Backtracking - VERIFIED

**Exhaustion criteria** (ALL must be met, `src/methodologies/signals/graph/node_exhaustion.py:46-72`):
1. `focus_count >= 1` (engaged at least once)
2. `turns_since_last_yield >= 3` (no new info for 3+ turns)
3. `current_focus_streak >= 2` (persistent focus without yield)
4. Shallow ratio >= 0.66 (2/3 recent responses are shallow)

**Continuous score** (`node_exhaustion.py:107-131`):
```
exhaustion_score = (turns_since_yield/10)*0.4 + (focus_streak/5)*0.3 + shallow_ratio*0.3
```

**Backtracking mechanism**: Exhausted nodes get 0.0 for `graph.node.exhausted.false: 1.0` signal, while fresh nodes get +1.0. Joint scoring naturally selects (strategy, fresh_node) over (strategy, exhausted_node). The `revitalize` strategy has `meta.node.opportunity.exhausted: 0.3` to approach exhausted nodes from a new angle.

### Claim 3: Intelligent Termination - VERIFIED

**6 termination conditions** (`src/services/turn_pipeline/stages/continuation_stage.py`):

| Condition | Trigger | Evidence |
|-----------|---------|----------|
| `max_turns_reached` | `turn_number >= max_turns` | `continuation_stage.py:145-153` |
| `close_strategy` | `strategy == "close"` | `continuation_stage.py:155-161` |
| `graph_saturated` | `consecutive_zero_yield >= 5` | `continuation_stage.py:178-181` |
| `quality_degraded` | `consecutive_shallow >= 4` | `continuation_stage.py:226-233` |
| `depth_plateau` | `consecutive_depth_plateau >= 6` | `continuation_stage.py:235-242` |
| `all_nodes_exhausted` | All explored nodes have `turns_since_last_yield >= 3` | `continuation_stage.py:252-265` |

Saturation metrics computed in `StateComputationStage._compute_saturation_metrics()` (`state_computation_stage.py:180-271`).

### Claim 4: Knowledge Graph Guides Questioning - VERIFIED

**20 graph-derived signals** drive strategy selection:
- 7 global graph signals (node_count, edge_count, orphan_count, max_depth, avg_depth, depth_by_element, chain_completion)
- 3 canonical graph signals (concept_count, edge_density, exhaustion_score)
- 10 node-level signals (exhausted, exhaustion_score, yield_stagnation, focus_streak, is_current_focus, recency_score, is_orphan, edge_count, has_outgoing, strategy_repetition)

### Claim 5: Dual-Graph Deduplication - VERIFIED

- **SlotDiscoveryStage**: Wired conditionally via `enable_canonical_slots` flag (`session_service.py:248-253`)
- **LLM proposal**: Structured JSON extraction via scoring LLM (`canonical_slot_service.py:148-261`)
- **Embedding similarity**: all-MiniLM-L6-v2 (384-dim) with threshold 0.83 (`canonical_slot_service.py:357-395`)
- **Promotion**: candidate → active when `support_count >= canonical_min_support_nodes` (default: 1)
- **TurnResult output**: `canonical_graph` and `graph_comparison` fields populated

---

## Section 4: Code Issues Found

### Issue 1: Technique Classes Are Dead Code

- **Severity**: Low (unused infrastructure)
- **Files**: `src/methodologies/techniques/laddering.py`, `probing.py`, `elaboration.py`, `validation.py`, `common.py`
- **Problem**: These classes define `generate_questions()` methods but `QuestionService` never imports or calls any technique. Strategy influence works entirely through LLM prompt injection (strategy description), not template questions.
- **Impact**: Dead code confuses developers into thinking techniques are used
- **Recommendation**: Either integrate technique-generated questions as LLM prompt examples, or remove the unused classes

### Issue 2: Saturation Tracking Is In-Memory Only

- **Severity**: Medium (data loss on restart)
- **File**: `src/services/turn_pipeline/stages/state_computation_stage.py:89`
- **Problem**: `_SaturationTrackingState` stored in an in-memory dict keyed by `session_id`. Server restart mid-session resets `consecutive_zero_yield`, `consecutive_shallow`, and `consecutive_depth_plateau` to zero.
- **Impact**: Saturation-based termination won't trigger correctly if server restarts during an interview
- **Recommendation**: Persist saturation counters to `sessions` table (similar to NodeStateTracker pattern)

### Issue 3: orphan_improvement_pct Is a Placeholder

- **Severity**: Low (cosmetic)
- **File**: `src/services/turn_pipeline/pipeline.py:232`
- **Problem**: `orphan_improvement_pct` hardcoded to `0.0` in graph_comparison output
- **Impact**: TurnResult reports 0% orphan improvement regardless of actual improvement
- **Recommendation**: Implement or remove the field

### Issue 4: canonical_min_turns Not Implemented

- **Severity**: Low (config exists but not enforced)
- **File**: `src/core/config.py:150-159`
- **Problem**: Documented as "NOT YET IMPLEMENTED" -- promotion only checks `support_count`, not temporal spread
- **Impact**: Slots promoted immediately (support=1) regardless of how many turns have passed
- **Recommendation**: Implement or remove the config field

### Issue 5: Phase Detection Ignores orphan_count Parameter

- **Severity**: Low (unused parameter)
- **File**: `src/methodologies/signals/meta/interview_phase.py:131-154`
- **Problem**: `_determine_phase()` accepts `orphan_count` parameter but only uses `node_count` for phase transitions. Comment says "could be added."
- **Impact**: Phase detection is simpler than it could be
- **Recommendation**: Remove the unused parameter or implement orphan-based transitions

### Issue 6: SRL vs SlotDiscovery Wiring Inconsistency

- **Severity**: Low (design inconsistency)
- **File**: `src/services/session_service.py:229-278`
- **Problem**: SRLPreprocessingStage is always wired (skips internally if service=None). SlotDiscoveryStage is conditionally excluded from the pipeline.
- **Impact**: Different patterns for similar feature-flag behavior
- **Recommendation**: Standardize on one pattern (either always-wire-and-skip or conditionally-exclude)

### Issue 7: Incomplete customer_journey_mapping Would Fail at Runtime

- **Severity**: Medium (potential runtime error)
- **File**: `config/methodologies/customer_journey_mapping.yaml`
- **Problem**: Has ontology only (no signals, strategies, or phases). If a session uses this methodology, `MethodologyStrategyService` would fail because no strategies exist.
- **Impact**: Runtime crash for any session using customer_journey_mapping
- **Recommendation**: Add validation in MethodologyRegistry to reject incomplete configs, or complete the methodology

---

## Section 5: Documentation Debt

### 5.1 CLAUDE.md (Root)

| Line | Issue | Fix |
|------|-------|-----|
| 7 | "10-stage turn processing pipeline" | Change to "12-stage (10 base + 2 optional)" |
| 112-122 | Pipeline stages table shows 10 stages | Add Stage 2.5 (SRLPreprocessing) and Stage 4.5 (SlotDiscovery) |
| 132 | Signal table lists `coverage_breadth` | Replace with: `node_count, max_depth, orphan_count, chain_completion` |
| 133 | LLM signals lists `topics` | Replace with: `response_depth, sentiment, uncertainty, hedging_language, global_response_trend` |
| 134 | Temporal signals lists `turns_since_focus_change` | Replace with: `strategy_repetition_count, turns_since_strategy_change` |
| 135 | Meta signals lists `exploration_score` | Replace with: `interview_progress, interview.phase` |
| 139 | YAML path: `src/methodologies/config/*.yaml` | Change to: `config/methodologies/*.yaml` |
| 141 | "based on strategy.focus_preference" | Change to: "uses joint strategy-node scoring" |
| 202 | YAML path: `src/methodologies/config/` | Change to: `config/methodologies/` |

### 5.2 docs/SYSTEM_DESIGN.md

| Line(s) | Issue | Fix |
|---------|-------|-----|
| 36-37 | ASCII diagram says "10 stages" | Update to "12 stages (10 base + 2 optional)" |
| 53 | "10 sequential stages" | Update to "10 base stages + 2 optional" |
| 539-597 | Entire "Concept-Driven Coverage" section | **REMOVE** or rewrite as canonical slots architecture |
| 550, 614, 925 | YAML path: `src/methodologies/config/` | Change to: `config/methodologies/` |
| 631 | "Select focus using strategy.focus_preference" | Change to: "Joint strategy-node scoring selects optimal pair" |
| 666-669 | GraphState shows `coverage_state` and `coverage_breadth` | Remove these fields; update to match actual model |
| 1090-1094 | "The system implements LLM fallback" | Mark as "planned, not yet implemented" or remove |

### 5.3 docs/pipeline_contracts.md

| Line(s) | Issue | Fix |
|---------|-------|-----|
| 546-556 | `ScoringPersistenceOutput` shows `coverage_score: float` | Remove (field does not exist in actual model) |
| 554 | `has_legacy_scoring` described as potentially True | Update: "Always False -- legacy system removed" |
| 558 | Claims stage saves two-tier scoring data | Remove legacy scoring note |
| 573 | Stage 7 `has_llm_fallback` listed as needing to be set | Note: no fallback logic exists |

### 5.4 docs/DEVELOPMENT.md

| Line(s) | Issue | Fix |
|---------|-------|-----|
| 418-420, 584 | YAML path: `src/methodologies/config/` | Change to: `config/methodologies/` |
| 480, 487, 760, 766 | `focus_preference` references | Remove |
| 486 | `graph.coverage_breadth: 0.6` | Remove |

### 5.5 docs/data_flow_paths.md

| Line(s) | Issue | Fix |
|---------|-------|-----|
| 135, 777 | YAML path: `src/methodologies/config/` | Change to: `config/methodologies/` |

### 5.6 README.md

| Line | Issue | Fix |
|------|-------|-----|
| 434 | `focus_preference: deep` | Remove |

### 5.7 ADRs

| File | Issue | Fix |
|------|-------|-----|
| `docs/adr/008-concept-element-coverage-system.md` | Entire ADR describes removed system | Mark as SUPERSEDED by canonical slots |
| `docs/adr/ADR-014-signal-pools-architecture.md:183,225,310` | References `focus_preference` | Mark as "not implemented -- replaced by joint scoring" |

---

## Section 6: Priority Summary

### High Priority (Misleading Documentation)

1. **Fix YAML config paths everywhere** -- `src/methodologies/config/` → `config/methodologies/` (CLAUDE.md, SYSTEM_DESIGN.md, DEVELOPMENT.md, data_flow_paths.md). Developers looking for configs will fail.
2. **Fix CLAUDE.md signal pool table** (lines 132-135) -- All 4 signal examples are wrong/stale
3. **Remove "Coverage State Tracking" from SYSTEM_DESIGN.md** (lines 539-597) -- Describes code that does not exist
4. **Remove `focus_preference` references** from CLAUDE.md, SYSTEM_DESIGN.md, DEVELOPMENT.md, README.md

### Medium Priority (Stale but Not Immediately Harmful)

5. **Fix stage count** across docs (10 → 12 with optional stages)
6. **Remove LLM fallback claim** from SYSTEM_DESIGN.md
7. **Fix ScoringPersistenceOutput** in pipeline_contracts.md (remove coverage_score, update has_legacy_scoring)
8. **Add validation** for incomplete methodology configs (customer_journey_mapping)
9. **Persist saturation counters** to database (prevent reset on server restart)

### Low Priority (Cleanup)

10. **Remove dead two-tier scoring infrastructure** (API schemas, repo methods, DB schema)
11. **Remove or integrate unused technique classes**
12. **Fix orphan_improvement_pct placeholder**
13. **Mark ADR-008 (coverage) as superseded**
14. **Standardize stage wiring pattern** (SRL vs SlotDiscovery)

---

## Appendix: Verification Evidence Map

| What Was Verified | Key File(s) | Lines |
|-------------------|-------------|-------|
| Strategy selection is deterministic | `src/methodologies/scoring.py` | 29-52, 196-225 |
| Phase detection works | `src/methodologies/signals/meta/interview_phase.py` | 131-154 |
| Strategy influences LLM prompt | `src/llm/prompts/question.py` | 47-58, 88-91, 164-179 |
| Node exhaustion detection | `src/methodologies/signals/graph/node_exhaustion.py` | 46-72, 107-131 |
| Joint strategy-node scoring | `src/methodologies/scoring.py` | 196-225 |
| Saturation metrics | `src/services/turn_pipeline/stages/state_computation_stage.py` | 180-271 |
| 6 termination conditions | `src/services/turn_pipeline/stages/continuation_stage.py` | 145-265 |
| Canonical slot discovery | `src/services/canonical_slot_service.py` | 148-261, 357-395 |
| Embedding similarity | `src/services/embedding_service.py` | 22-23, 69, 126-128 |
| NodeStateTracker persistence | `src/services/session_service.py` | 695-771 |
| Pipeline wiring | `src/services/session_service.py` | 229-278 |
| Coverage removal | `src/persistence/database.py` | 89-102 |
| Technique classes unused | `src/services/question_service.py` | (no technique imports) |
