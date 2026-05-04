# Edge Extraction — Decisions Doc

Companion to `docs/drafts/edge-extraction-spec.md`. Pins decisions resolved during the pre-implementation investigation pass (branch `feature/edge-extraction-stage-4-5b`).

This doc supersedes the spec wherever they conflict. Beads should cite this doc, not the spec, for contract decisions.

**Status: COMPLETE** (May 2026). All beads B1–B11 closed. Stage 4.5B is mandatory for all 6 methodologies. Feature flag deleted. Stage 3 is concept-only. See `reports/edge_extraction_rollout/` for per-methodology validation reports.

---

## D1 — Full separation of node and edge extraction

**Decision:** Stage 3 produces nodes only. A new Stage 4.5B produces ALL edges (both within-turn and cross-turn). The spec's "incremental" framing (Stage 3 keeps within-turn edges) is rejected.

**Rationale:** Within-turn edges share the same circular-evidence and frame-contamination risks as cross-turn edges. Mixed ownership creates a debugging boundary that adds no value. Within-turn edges piggyback on a Sonnet call we are already making in parallel — marginal latency cost is near zero.

**Consequence:**
- Delete `ExtractedRelationship` and `ExtractionResult.relationships` (`src/domain/models/extraction.py:73-100, 121`).
- Delete `_parse_relationships` (`src/services/extraction_service.py:432-510`) and all relationships handling at lines 30, 34, 192-200, 206-207, 213.
- Strip relationship sections from the Stage 3 prompt: bridge instructions (`src/llm/prompts/extraction.py:171-194`), level-aware section (128-146), relationship example loop (108-120), relationships JSON schema block (208-217), and the `parse_extraction_response` relationships branch at line 317.
- Delete bridge logic in `extraction_stage.py:31-46, 207-341` (`_format_context_for_extraction`, `_get_previous_focus`, `_get_bridge_config`, `_BRIDGE_TARGET_DESCRIPTIONS`).
- `GraphService.add_extraction_to_graph` returns `(nodes, [])`. Edge writing moves entirely to the Stage 4.5B persistence path.
- Methodology YAMLs: `relationship_examples` and `extraction_guidelines` keys referenced by the deleted prompt sections become dead config — to be removed in a follow-up cleanup bead, not in B2.

---

## D2 — Pipeline mechanism: prefetch + bridge pair

**Decision:** Stage 4.5B is implemented as two stages following the existing `LLMPrefetchStage` / `LLMSignalBridgeStage` pattern. No generic N-stream merger.

**Rationale:** Investigation confirmed there is no merge coordinator today — "parallel" work is hand-wired via a single `asyncio.create_task` stored on `PipelineContext`. Adding a generic merger is out of scope; the established pattern is sufficient and consistent with the codebase.

**Consequence:**
- `EdgeExtractionPrefetchStage` fires `context._edge_extraction_task = asyncio.create_task(...)`.
- `EdgeExtractionBridgeStage` awaits the task and performs edge persistence.
- No changes to `TurnPipeline.execute` — both stages plug into the existing flat sequential list.

---

## D3 — Stage placement and ordering

**Decision:** Pipeline ordering inside the Stage 4–5 window is:

```
Stage 4   GraphUpdateStage              (writes nodes, runs node dedup, assigns node IDs)
Stage 4.5 SlotDiscoveryStage            (canonical slot mapping)
Stage 4.5B-prefetch  EdgeExtractionPrefetchStage   (fires asyncio.Task)
Stage 4.6 EdgeExtractionBridgeStage     (awaits task, writes edges, updates tracker edge counts)
Stage 4.7 LLMSignalBridgeStage          (existing — seals tracker)
Stage 5   StateComputationStage         (existing)
```

**Rationale:**
- EdgeExtractionPrefetch must run AFTER Stage 4 because it needs post-dedup node IDs from `GraphUpdateOutput.concept_to_node_id`.
- EdgeExtractionBridge must run BEFORE Stage 4.7 because `LLMSignalBridgeStage` seals `_evolving_node_tracker` (`src/services/turn_pipeline/stages/llm_signal_bridge_stage.py:115-123`). Stage 4.5B mutates edge counts on that tracker and cannot run after sealing.
- EdgeExtractionPrefetch can run in parallel with the existing LLM prefetch task fired at Stage 3.1 — both Sonnet calls overlap.

**Consequence:**
- The latency-hiding window for edge extraction is narrower than the spec implied: it overlaps with `SlotDiscoveryStage` and the tail of the existing LLM prefetch, not with `GraphUpdateStage`.
- B5 (pipeline wiring) must include an inline comment documenting this ordering rationale at the call site.

---

## D4 — Tracker edge-count update and `record_yield` ownership

**Decision:**
- `update_edge_counts_batch` runs twice per turn: once in `GraphUpdateStage` (existing — for nodes) and once in `EdgeExtractionBridgeStage` (new — for edges).
- `record_yield` is called exactly once per turn, by `EdgeExtractionBridgeStage`, against `tracker.previous_focus`. The current `record_yield` call in `GraphUpdateStage:181-197` is REMOVED.

**Rationale:** `record_yield` represents "the focus produced graph change this turn." Until edges are written, that statement is incomplete. Moving the call to after edge writes makes it accurate. Single owner avoids double-credit.

**Consequence:**
- B7 deletes `record_yield` invocation in GraphUpdateStage and adds it to EdgeExtractionBridgeStage.
- B7 verifies tests covering yield credit (search `tests/` for `record_yield`) and updates them if the timing assertions break.

---

## D5 — Edge writer reuse

**Decision:** `GraphService._add_edge_from_relationship` is extended to accept either an `ExtractedRelationship` (legacy callers, none after D1) OR a `ConfirmedEdge` (Stage 4.5B). The post-dedup `is_valid_connection` check at `graph_service.py:342-360` is RETAINED as the single enforcement point for `permitted_connections`.

**Rationale:** Reusing the existing writer keeps dedup, validation, and `add_edge_source_utterance` semantics consistent. `ConfirmedEdge` carries node IDs directly (no `label_to_node` lookup needed for that path), so the extension is a small overload.

**Consequence:**
- B6 implements the overload. Function signature pattern: accept `edge: Union[ExtractedRelationship, ConfirmedEdge]` and branch on type for resolution. Type-pair validation runs identically for both.
- `bd ui0f` remains closed — its fix is preserved.

---

## D6 — Utterance retrieval

**Decision:**
- Add `UtteranceRepository.get_by_ids(ids: List[str]) -> List[Utterance]`.
- Stage 4.5B input construction calls this on demand using `source_utterance_ids` from focus and neighbour nodes.
- Nodes with `source_utterance_ids == ["unknown"]` are EXCLUDED from candidate context (cannot be evidence-grounded).
- The existing `recent_utterances` (window=10) on `ContextLoadingOutput` is NOT used by Stage 4.5B — it's insufficient for cross-turn focus jumps.

**Rationale:** Focus-derived selection (per spec §"Utterance Selection") cannot be served from a recency window. DB read is required. The "unknown" fallback at `extraction_service.py:188, 198` exists in production data; silently including those nodes would produce ungrounded edges.

**Consequence:**
- B3 owns the new repo method and a helper that assembles the focus + neighbours utterance set, deduped by ID.
- Tightening the `"unknown"` fallback itself (e.g. raising on missing `source_utterance_id`) is out of scope — tracked separately if needed.

---

## D7 — Candidate-pair pre-filter: DEFERRED

**Decision:** Stage 4.5B v1 does NOT pre-filter candidate pairs against `permitted_connections`. The LLM receives all candidate pairs from `[CURRENT] × [FOCUS, NEIGHBOR, RECENT]` and rejects type-illegal pairs via `type_constraint_violation` reasoning.

**Rationale:** Only MEC strict has `permitted_connections` defined on chain edges (`means_end_chain_v2_strict.yaml:64, 77`); the other 5 active methodologies enforce nothing at the YAML level. Pre-filter latency win is concentrated on one method. Open Question #2 in the spec called this an optimization — defer until baseline measurement shows the prompt is too large or Sonnet latency is binding.

**Consequence:**
- Bead set drops the pre-filter scope from B4. Add as a follow-up bead post-merge if measurement justifies it.
- Prompt construction (B2) still includes the methodology edge schema with `valid_source_types`/`valid_target_types`, so the LLM has the constraints to apply.

---

## D8 — Methodology uniformity

**Decision:** Stage 4.5B uses a single uniform code path across all 6 active methodologies. Only the prompt content varies, via `MethodologySchema` accessors (`get_edge_descriptions`, `get_chain_relevant_edge_types`, etc.).

**Rationale:** No methodology requires structurally different edge-extraction logic. RG/CJM are documented as "flat" but still have `chain_relevant: true` edges; the same prompt structure works.

**Consequence:** No per-method branching in B4. Prompt template + schema injection only.

---

## D9 — Provider configuration

**Decision:** New `llm.edge_extraction:` block in `config/interview_config.yaml`, defaulting to `provider: anthropic, model: claude-sonnet-4-6, effort: low`. Mirrors the existing `llm.extraction` block.

**Rationale:** Matches spec recommendation. Allows independent tuning vs. extraction. `effort: low` matches the project's pattern of cost-conscious Sonnet calls.

**Consequence:** B1 includes the config block. Loading code is a copy of the existing extraction provider lookup.

---

## D10 — Audit logging: structlog only for v1

**Decision:** Rejected edge candidates and low-confidence edges are logged via structlog with structured fields (rejection_reason, source_node_id, target_node_id, reasoning_summary, confidence). No new DB table.

**Rationale:** Production training-signal capture is premature. structlog output is queryable in development logs and sufficient for audit. A DB table can be added later without breaking the Pydantic contract.

**Consequence:** B8 owns structured logging only. `EdgeExtractionOutput.rejected_candidates` is preserved in memory through the bridge stage and serialized into structlog at the bridge boundary.

---

## D11 — Latency: empirical baseline, no hard budget

**Decision:** No hard latency budget assertion. Stage 4.5B latency is reported via `TurnResult.stage_timings` (existing mechanism at `pipeline.py:82-83`). Acceptance criterion is empirical: post-change p50 turn latency does not regress more than +X% on baseline persona seeds (X to be set when baseline is measured).

**Rationale:** The spec's "800ms budget" is not present in any config file. Treating it as binding would over-constrain implementation against an unanchored number.

**Consequence:** B9 (diff harness) measures and reports stage_timings. The acceptance threshold is set by the human after seeing baseline numbers, not pre-committed.

---

## D12 — Feature flag and rollout

**Decision:**
- New flag `enable_edge_extraction_stage` in interview config, defaulting to `false` on master.
- When OFF: Stage 4.5B prefetch and bridge are no-ops; pipeline behaves identically to today (modulo the Stage 3 relationship deletion in D1, which is a permanent change). To preserve backward compatibility while the flag is OFF, Stage 3 retains relationship extraction UNTIL B10 enables the flag for the first methodology.
- When ON: full edge extraction pipeline runs.
- Rollout sequence: JTBD → MEC strict → MEC flex → CIT → CJM → RG. Validate strategy distribution diff at each step before enabling the next.

**Rationale:** The full Stage 3 deletion in D1 is irreversible mid-rollout — if we delete relationships from Stage 3 immediately, every methodology MUST use Stage 4.5B from that moment. To allow per-methodology rollout with safe rollback, Stage 3's relationship code stays in place during B1–B9 and is deleted in a final cleanup bead AFTER all methodologies are running on Stage 4.5B successfully.

**Consequence:**
- D1's deletions are RESCHEDULED: implemented in a final cleanup bead (B11), not in B1/B2.
- B1/B2 ADD the new path behind the flag without removing the old path.
- B10 enables per-methodology and validates.
- B11 (new) deletes the Stage 3 relationship code path once all methodologies are confirmed on the new path.

This is a meaningful refinement of D1 — D1's end-state is correct, but the path to it is gated for rollback safety.

---

## Bead set (final, ordered)

- **E0 (epic)** — `feature/edge-extraction-stage-4-5b`
- **B1** — `EdgeExtractionOutput` Pydantic contract + `enable_edge_extraction_stage` feature flag (default OFF) + `llm.edge_extraction` config block
- **B2** — Stage 4.5B prompt (universal + methodology-specific via `MethodologySchema` accessors); new prompt module under `src/llm/prompts/`
- **B3** — `UtteranceRepository.get_by_ids` + focus-derived utterance set helper (excludes `"unknown"` source ids)
- **B4** — `EdgeExtractionPrefetchStage` (fires asyncio.Task; flag-gated no-op when OFF)
- **B5** — `EdgeExtractionBridgeStage` (awaits task, persists confirmed edges via D5 reuse, second `update_edge_counts_batch`); pipeline wiring per D3 with inline ordering rationale
- **B6** — Extend `GraphService._add_edge_from_relationship` to accept `ConfirmedEdge` (D5)
- **B7** — Move `record_yield` ownership from `GraphUpdateStage` to `EdgeExtractionBridgeStage` (D4); update affected tests
- **B8** — Structured logging for rejected/low-confidence edges (D10)
- **B9** — Baseline-vs-new diff harness: 1 persona × 6 methodologies, comparing strategy distribution, chain density, stage_timings; flag both OFF and ON
- **B10** — Enable flag per methodology in rollout order (D12); validate at each step
- **B11** — Cleanup: delete Stage 3 relationship code (D1 deletions) after all methodologies confirmed on new path

Each bead is single-session-sized and references this doc by section ID.

---

## Open items NOT decided here (deliberately)

- **`"unknown"` source_utterance_id tightening.** Tracked as a separate hygiene concern; not a blocker for B1–B11.
- **Per-edge training signal capture (DB table for rejected candidates).** Spec Open Q #3 — defer until training pipeline exists.
- **Within-turn edge schema in the prompt.** B2 owns the prompt design; spec section "Output Design" is the starting point but exact XML/JSON shape is a B2 implementation detail.
- **Latency regression threshold.** Set after B9 baseline measurement, not pre-committed.
