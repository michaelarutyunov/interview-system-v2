# Stage Data Dependencies & Parallelization Analysis

Latency audit dependency map for the 12-stage interview pipeline.
Based on steady-state metrics from 13 sessions, 117 turns, 610 LLM calls.

**Audience**: Engineers evaluating parallelization, extraction atomization, and model migration.
**Source data**: `reports/latency_audit/` (timestamped reports + CSVs).

---

## Pipeline Overview

```
Turn N:
  [1] ContextLoading ──► [2] UtteranceSaving ──► [2.5] SRLPreprocessing
       ~5ms                    ~5ms                    ~13ms (steady)
  ──► [3] Extraction ──► [4] GraphUpdate ──► [4.5] SlotDiscovery
        ~13s (Sonnet)       ~77ms              ~3.3s (Haiku)
  ──► [5] StateComputation ──► [6] StrategySelection ──► [7] Continuation
        ~4ms                     ~4.7s (Haiku)             ~0ms
  ──► [8] QuestionGeneration ──► [9] ResponseSaving ──► [10] ScoringPersistence
        ~1.2s (Haiku)               ~5ms                    ~11ms
```

Steady-state median total: **~22.6s** per turn. Cold start (turn 1): **~41.5s** (spaCy model load adds ~2s to SRL).

---

## Stage I/O on PipelineContext

### Stage 1: ContextLoadingStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `session_id` | |
| **WRITE** | `context_loading_output` | Session metadata, turn_number, methodology, conversation history, strategy_history, recent_node_labels, focus_history |

External I/O: 4-5 sequential DB reads (session, config, strategies, nodes, utterances).
Latency: ~5ms. Driver: multiple sequential SQLite queries.

### Stage 2: UtteranceSavingStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `session_id`, `turn_number`, `user_input` | |
| **WRITE** | `utterance_saving_output` | Persisted user utterance record with ID |

External I/O: 1 DB write (INSERT utterance).
Latency: ~5ms. Driver: single SQLite INSERT.

### Stage 2.5: SRLPreprocessingStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `utterance_saving_output`, `recent_utterances` (last system Q), `user_input` | |
| **WRITE** | `srl_preprocessing_output` | Discourse relations, SRL frames |

External I/O: spaCy NLP pipeline (in-process, no LLM).
Latency: ~2s cold (model load), ~13ms steady. Driver: spaCy model loading on first use.

### Stage 3: ExtractionStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `utterance_saving_output` (utterance ID), `user_input`, `concept_id`, `methodology`, `recent_utterances` (-5), `srl_preprocessing_output` (optional hints), `context_loading_output.recent_node_labels` (-30), `context_loading_output.focus_history` (last) | |
| **WRITE** | `extraction_output` | Extracted concepts + relationships |

External I/O: 1 Sonnet LLM call (~3300 input tokens, ~1100 output tokens).
Latency: **~13s mean, ~19.8s p95**. **Dominant bottleneck — 57% of steady-state time.**

### Stage 4: GraphUpdateStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `utterance_saving_output` (utterance ID), `extraction_output`, `methodology`, `node_tracker` | |
| **WRITE** | `graph_update_output` (nodes_added, edges_added), `concept_to_node_id` (reset) | |

External I/O: Batch DB writes (nodes + edges), node_tracker register/update/record_yield per node.
Latency: ~77ms steady (183ms cold start for first graph build). Driver: batch SQLite writes.

### Stage 4.5: SlotDiscoveryStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `graph_update_output` (nodes_added, edges_added), `session_id`, `turn_number`, `methodology`, `node_tracker` | |
| **WRITE** | `slot_discovery_output`, `node_tracker` (via remap_to_canonical_slots) | Canonical slots + surface→canonical mappings |

External I/O: 1 Haiku LLM call (slot_scoring, ~1500 input / ~520 output tokens), multiple DB writes (slots, mappings, edge aggregation).
Latency: ~3.3s mean, ~5.0s p95. Driver: Haiku LLM call (~3.2s) + sequential DB writes.

### Stage 5: StateComputationStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `session_id`, `turn_number`, `graph_update_output`, `node_tracker`, `strategy_history` | |
| **WRITE** | `state_computation_output` | graph_state, recent_nodes, computed_at, saturation_metrics, canonical_graph_state |

External I/O: 2 DB reads (graph_state, recent_nodes), 1 optional canonical computation.
Latency: ~4ms. Driver: lightweight DB reads on small graphs.

### Stage 6: StrategySelectionStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `graph_state` (from Stage 5), `graph_state_computed_at`, `recent_nodes`, `extraction`, `recent_utterances`, `turn_number`, `mode`, `session_id`, `user_input`, `methodology`, `node_tracker` | |
| **WRITE** | `strategy_selection_output` (strategy, focus, node_signals, score_decomposition, signals, alternatives), `node_tracker` (update_focus), `graph_state` (add_strategy_used) | |

External I/O: 1 Haiku LLM call (signal_scoring, ~2800 input / ~450 output tokens), CPU-intensive strategy scoring.
Latency: ~4.7s mean, ~7.4s p95. Driver: signal_scoring LLM call (~4.8s) + CPU scoring.

### Stage 7: ContinuationStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `strategy_selection_output`, `max_turns`, `focus`, `recent_nodes`, `strategy`, `graph_state`, `turn_number`, `signals` (phase), `state_computation_output` (saturation), `node_tracker` | |
| **WRITE** | `continuation_output` (should_continue, focus_concept, reason) | |

External I/O: None.
Latency: ~0ms. Pure computation.

### Stage 8: QuestionGenerationStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `strategy_selection_output` (strategy, focus_mode, generates_closing_question), `continuation_output` (focus_concept), `should_continue`, `recent_utterances`, `user_input`, `graph_state`, `recent_nodes`, `concept_name`, `signals`, `session_id` | |
| **WRITE** | `question_generation_output` (question, strategy, focus) | |

External I/O: 1-2 Haiku LLM calls (question_generation, ~1600 input / ~60 output tokens each).
Latency: ~1.2s mean, ~2.3s p95. Driver: Haiku LLM call(s).

### Stage 9: ResponseSavingStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `session_id`, `turn_number`, `next_question` | |
| **WRITE** | `response_saving_output` (system utterance record) | |

External I/O: 1 DB write (INSERT utterance).
Latency: ~5ms.

### Stage 10: ScoringPersistenceStage
| Direction | Field | Notes |
|-----------|-------|-------|
| **READ** | `session_id`, `turn_number`, `strategy`, `graph_state`, `signals`, `context_loading_output` (velocity metrics, focus_history), `strategy_selection_output` (focus), `node_tracker`, `mode`, `methodology`, `concept_id`, `concept_name`, `canonical_graph_state` | |
| **WRITE** | `scoring_persistence_output` | |

External I/O: 3 DB writes (scoring_history INSERT, methodology_signals INSERT, session state/metadata UPDATE).
Latency: ~11ms.

---

## Parallelization Opportunities

### Opportunity 1: Extractability Pre-filter (estimated savings: up to 13s on non-extractable turns)

**Current**: Every turn runs ExtractionStage (~13s Sonnet call) regardless of response content.
**Proposal**: Use the existing `get_extractability_system_prompt()` / `get_extractability_user_prompt()` as a fast pre-filter before full extraction.

The extractability prompt already exists in `src/llm/prompts/extraction.py`. A Haiku call (~50 tokens output) would take ~200-500ms. For brief or non-substantive responses (e.g., "I don't know", "Yeah sure"), this could save the entire 13s extraction cost.

| Factor | Assessment |
|--------|-----------|
| **Estimated latency saved** | 0-13s per turn (0s for substantive responses, 13s for non-extractable) |
| **Implementation complexity** | Low — extractability prompt exists, just wire as Stage 3 pre-check |
| **Quality risk** | Low — the pre-filter is conservative (returns extractable=true when uncertain) |
| **Estimated frequency** | ~10-20% of turns with brief/uncertain personas |

### Opportunity 2: Signal Scoring LLM Call Parallel with SlotDiscovery (estimated savings: 2-3s)

**Current**: Stages run strictly sequentially: 4.5 (SlotDiscovery, ~3.3s) → 5 (StateComputation, ~4ms) → 6 (StrategySelection, ~4.7s). Total: ~8s.

**Proposal**: The signal_scoring LLM call inside StrategySelection depends on `response_text`, `methodology`, and `graph_state` — all available after Stage 5. The LLM call itself can fire in parallel with SlotDiscovery, but the **bridge step** (routing per-concept ratings into `node_tracker.append_quality()`) must wait for SlotDiscovery to complete, because `append_quality()` resolves surface node IDs to canonical slot IDs via `_resolve_canonical_slot_id()`, which queries the surface→canonical mappings that SlotDiscovery creates.

```
CURRENT:   [4.5 SlotDiscovery 3.3s] → [5 State 4ms] → [6 StrategySelection 4.7s]  = 8.0s
PROPOSED:  [4.5 SlotDiscovery 3.3s] ─┐
            [6 LLM signal_scoring 4.8s]─┤→ [await SlotDiscovery] → [bridge + CPU scoring] = 5.0s
```

The LLM call (the latency bottleneck at ~4.8s) overlaps with SlotDiscovery. After both complete, the bridge step routes per-concept `elaboration` and `charge` ratings into node_tracker via `concept_to_node_id` → `_resolve_canonical_slot_id()` → `append_quality()`. This bridge must run after SlotDiscovery because canonical slot mappings don't exist until Stage 4.5 writes them to the DB.

**Dependency detail**: The LLM produces both global signals (engagement, valence, certainty, response_depth) and per-concept ratings (elaboration, charge). The global signals feed directly into CPU scoring. The per-concept ratings need `concept_to_node_id` (from Stage 4) and canonical slot mappings (from Stage 4.5) to land correctly in the tracker. Running the LLM call early and deferring only the bridge step preserves correctness while gaining the overlap.

| Factor | Assessment |
|--------|-----------|
| **Estimated latency saved** | 2-3s per turn (overlap of signal_scoring LLM with SlotDiscovery) |
| **Implementation complexity** | Medium — split `detect_with_per_concept()` into (a) fire LLM call, (b) await + bridge; defer bridge until SlotDiscovery completes |
| **Quality risk** | Low — LLM signals are response-level; the bridge step is deterministic once mappings exist |
| **Prerequisite** | Refactor `MethodologyStrategyService.select_strategy_and_focus()` to separate LLM dispatch from node_tracker write-back |

### Opportunity 3: Speculative Question Generation (estimated savings: ~1.2s)

**Current**: ContinuationStage (~0ms) → QuestionGenerationStage (~1.2s). Total: ~1.2s.
**Proposal**: Fire QuestionGeneration immediately after StrategySelection (before ContinuationStage). If Continuation decides to stop, discard the generated question.

The probability of stopping is low (~10% of turns, and only on the final turn). The cost of a wasted Haiku call is ~60 output tokens × $0.000001/Token ≈ $0.00006.

```
CURRENT:  [7 Continuation 0ms] → [8 QuestionGen 1.2s] = 1.2s
PROPOSED: [7 Continuation 0ms] ─┐
           [8 QuestionGen 1.2s]─┘ (started earlier)   = 0ms effective
```

| Factor | Assessment |
|--------|-----------|
| **Estimated latency saved** | ~1.2s per turn (on the continue path, which is ~90% of turns) |
| **Implementation complexity** | Low — move QG LLM call to overlap with Continuation's conditional checks |
| **Quality risk** | None (on stop path, question is discarded; on continue path, identical behavior) |
| **Cost of waste** | ~$0.00006 per discarded turn (negligible) |

---

## Extraction Atomization Assessment

**Question**: Can the single Extraction Sonnet call (~13s, ~1100 output tokens) be split into parallel sub-tasks?

**Answer**: Partially feasible, but with significant constraints.

The extraction prompt produces a single JSON with `concepts` and `relationships` arrays. These are **interdependent** — relationship extraction references concept labels as `source_text`/`target_text`, and the prompt includes cross-turn bridging that connects new concepts to existing graph nodes. A naive split would require:

1. **Pass 1**: Extract concepts only (~7-8s)
2. **Pass 2**: Extract relationships given concepts (~5-6s, simpler prompt)

This 2-pass approach would likely take **~13s sequentially** (same as current) or **~8s with parallel dispatch** (if relationships can be extracted independently). However, the parallel version requires the concept list from Pass 1 before Pass 2 can start, making true parallelism impossible without sacrificing cross-referencing quality.

**Better alternatives for extraction latency reduction**:

| Approach | Est. Savings | Risk | Notes |
|----------|-------------|------|-------|
| Prompt diet | 3-5s | Low | Current prompt ~3.3K input tokens with verbose examples. Trimming methodology guidelines and examples could reduce to ~2K tokens. |
| Extractability pre-filter | 0-13s | Low | Skip extraction for ~10-20% of turns (see Opportunity 1) |
| Model migration (Sonnet → Haiku) | 5-8s | Medium | Haiku is ~3-5× faster but extraction quality untested at Haiku tier. Needs quality baseline (bead x3cm). |
| Two-pass sequential | ~0s | Medium | Similar total time, not recommended. |
| Output schema reduction | 2-3s | Low | Remove `reasoning`, `source_quote` fields from relationships when not needed for dedup. |

---

## Cold Start Analysis

Turn 1 has significantly higher latency (~41.5s median) due to:

1. **SRLPreprocessingStage**: ~2s (spaCy model load, lazy-loaded on first use). Steady-state: ~13ms.
2. **GraphUpdateStage**: ~6.8s (first graph build with initial dedup computation). Steady-state: ~77ms.
3. **SlotDiscoveryStage**: ~4.8s (no existing slots, full discovery). Steady-state: ~3.3s.
4. **StrategySelectionStage**: ~6.3s (larger context, more signals to evaluate). Steady-state: ~4.7s.

Cold start is a one-time cost per session. For interviews with 10+ turns, cold start amortizes to <5% of total time. Not a primary optimization target unless session lengths drop below 5 turns.

---

## Methodology-Specific Hotspots

Based on the audit data, latency distribution varies by methodology:

| Methodology | Turns | p50 Total (ms) | p95 Total (ms) | Notable |
|-------------|-------|----------------|----------------|---------|
| critical_incident_v2 | 18 | 24,061 | 42,233 | Higher extraction p95 |
| customer_journey_mapping_v2 | 20 | 23,098 | 50,799 | Highest p95 variance |
| jobs_to_be_done_v2 | 9 | 23,282 | 34,200 | No cold starts in sample |
| means_end_chain_v2_strict | 43 | 22,063 | 34,680 | Most data, most representative |
| repertory_grid_v2 | 18 | 29,511 | 47,911 | **Highest p50** — StrategySelection p95=21.2s outlier |

**RG outlier**: Repertory Grid shows a 21.2s p95 on StrategySelection (vs 5-9s for others). This likely reflects RG's 8 strategies with complex triadic comparison signals causing longer LLM signal scoring responses. Worth investigating separately.

---

## Summary: Ranked Optimization Priorities

| Priority | Opportunity | Savings | Complexity | Risk |
|----------|------------|---------|------------|------|
| 1 | Extractability pre-filter | 0-13s/turn (10-20% of turns) | Low | Low |
| 2 | Signal scoring LLM parallel with SlotDiscovery | 2-3s/turn | Medium | Low |
| 3 | Extraction prompt diet | 3-5s/turn | Low | Low |
| 4 | Speculative question generation | ~1.2s/turn | Low | None |
| 5 | Model migration (Sonnet→Haiku for extraction) | 5-8s/turn | Medium | Medium |

Combined estimated savings from priorities 1-4: **~6-10s per turn** (reducing steady-state from ~22.6s to ~12-17s).
