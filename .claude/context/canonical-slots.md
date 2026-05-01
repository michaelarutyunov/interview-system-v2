# Canonical Slots
## Current Version: 1.0

## Core Mechanics

`CanonicalSlotService` (Stage 4.5 — `slot_discovery_stage.py`, optional) abstracts surface `KGNode`s into stable canonical slots to handle respondent language variation. Disabled entirely when `enable_canonical_slots: false`.

**Slot discovery pipeline (per turn):**
1. **Batch surface nodes by `node_type`** — groups nodes extracted this turn. Capped at `MAX_SLOT_DISCOVERY_BATCH_SIZE = 8` nodes per turn; excess nodes are processed in subsequent turns.
2. **Single batched LLM call** — `_llm_propose_slots_batched()` sends one request covering all node types. The prompt includes existing active slot names per type (to encourage reuse) and requests `slot_name` (snake_case), `description`, and `surface_node_ids` per proposed grouping.
3. **Find or create per proposal** (`_find_or_create_slot`):
   - **Lemmatize** proposed name (word-by-word via spaCy) to normalize grammatical variants (e.g. `reduced` → `reduce`).
   - **Exact name match** — if a slot with this lemmatized name and `node_type` already exists, use it.
   - **Embedding similarity search** — encode `"{slot_name} :: {description}"` and search both `active` and `candidate` slots within the same `node_type` and session against `canonical_similarity_threshold` (default **0.60**).
   - **Merge or create** — merge into best similarity match, or create a new `candidate` slot.
4. **Map surface nodes** — each surface node ID is mapped to the resolved slot via `slot_repo.map_surface_to_slot()`.
5. **Promotion check** — after mapping, re-read the slot's `support_count`. If `status == "candidate"` and `support_count >= canonical_min_support_nodes` (default **2**), promote to `active`.

**Only `active` slots appear in canonical graph signals.** Candidate slots exist in the DB but are invisible to signal detection.

## Correctness Requirements

1. **`active` slots only in signals** — first occurrence of any concept → `candidate` slot → zero contribution to canonical signals. This is expected behavior, not a bug.
2. **`canonical_min_support_nodes = 2` (default)** — a surface concept must appear in at least 2 surface nodes (across any turns) before its slot is promoted and canonical signals fire.
3. **Stage 4.5 runs after Stage 4** — surface nodes must exist in the DB before slot discovery. Stage ordering guarantees this; do not reorder.
4. **`enable_canonical_slots: false` skips Stage 4.5 entirely** — canonical signals return empty collections, not errors. `GraphService` must not be constructed with `canonical_slot_repo` when the flag is off, or `aggregate_surface_edges_to_canonical()` will raise.
5. **Embedding encodes `name :: description`** — richer semantic signal than name alone. Changes to description format affect similarity matching.
6. **Lemmatization uses spaCy `en_core_web_md`** — must be installed. Lemmatizes word-by-word (not phrase) to avoid context-sensitive POS tagging artifacts.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Canonical signals always zero early in the interview | Slots still `candidate` — `support_count` below `canonical_min_support_nodes` | Expected behavior; no fix needed. If promotion is desired earlier, lower `canonical_min_support_nodes` in config |
| Slot not promoted despite multiple mentions | `support_count` not reaching threshold, or concept resolves to different slots each turn | Check `slot_promoted` / `slot_found_exact` / `slot_merged` logs; inspect `canonical_similarity_threshold` — may be too low, causing fragmentation |
| Excessive slot fragmentation | `canonical_similarity_threshold` too high — similar concepts don't merge | Lower threshold (e.g. 0.55) or check that embedding model is loaded correctly |
| Stage 4.5 errors on missing embeddings | Surface nodes created without embeddings (embedding service unavailable in Stage 4) | Verify `embedding_service` is injected into `GraphService`; check Stage 4 logs for embedding failures |
| LLM assigns node IDs from wrong type | Batched LLM response cross-contaminates node IDs across types | `_find_or_create_slot` guards against this with `valid_node_ids` filter; check `slot_discovery_batch_limited` logs if many nodes/turn |
| `slot_discovery_batch_limited` warning | More than 8 nodes extracted in a single turn | Expected for information-dense responses; remaining nodes processed next turn. Raise `MAX_SLOT_DISCOVERY_BATCH_SIZE` if needed |
| `focus_update_failed_node_not_found` / `append_quality_failed_node_not_found` warnings in NodeStateTracker | `register_node()` stores under surface UUID but lookups resolve via `_resolve_canonical_slot_id()` to canonical slot ID. Stage 4.5 creates mappings AFTER registration. | `remap_to_canonical_slots()` called at end of SlotDiscoveryStage re-keys tracker from UUID → canonical_slot_id. If warnings persist, check `canonical_slot_remap_complete` logs |

## Canonical Chains

Canonical chains (reported in `02_causal_chains.md`) are constructed by aggregating surface edges through canonical slot mappings. Because canonical slots merge semantically similar surface nodes into "big themes," the edge aggregation between slots is inherently lossy — multiple surface edges with different relationship types and directions get collapsed into aggregate counts.

**Canonical chains are expected to be sparse and incomplete.** This is not a bug. Surface chains are the primary analysis target. Canonical chains become useful only in cross-persona or multi-run analysis, where the same canonical slots recur across different interviews and reveal stable patterns.

**When reviewing an interview:**
- Focus chain quality assessment on **surface chains** — these preserve the respondent's actual language and edge semantics
- Do NOT flag low canonical chain counts as `over_aggressive_dedup` or a configuration problem
- Only reference canonical chains when comparing across multiple runs (same slot appearing across different personas/concepts)

## Known Failure Modes

- **Flagging canonical chain sparsity as a bug**: Reviewers unfamiliar with the dual-graph architecture sometimes treat zero canonical full chains as a dedup failure. This is expected behavior — see "Canonical Chains" above.


## Key Files

- `src/services/canonical_slot_service.py` — `CanonicalSlotService` (full discovery pipeline)
- `src/services/turn_pipeline/stages/slot_discovery_stage.py` — Stage 4.5 wiring
- `src/persistence/repositories/canonical_slot_repo.py` — slot CRUD, `map_surface_to_slot`, `promote_slot`, `find_similar_slots`
- `src/domain/models/canonical_graph.py` — `CanonicalSlot`, `CanonicalEdge`
- `src/core/config.py` — `deduplication.canonical_similarity_threshold` (default 0.60), `deduplication.canonical_min_support_nodes` (default 2)
- `src/services/graph_service.py` — `aggregate_surface_edges_to_canonical()` (canonical edge aggregation using slot mappings)
