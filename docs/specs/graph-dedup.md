# Graph Deduplication

## Core Mechanics

`GraphService.add_extraction_to_graph()` (Stage 4 — `graph_update_stage.py`) integrates extracted concepts and relationships into the surface knowledge graph with deduplication.

**Node deduplication pipeline (per extracted concept):**
1. **Exact label + node_type match** (case-insensitive, fast path) — calls `repo.find_node_by_label_and_type()`. If found, adds `utterance_id` to provenance and returns the existing node.
2. **Semantic similarity match** — only runs when `embedding_service` is configured. Computes embedding for the concept text, then calls `repo.find_similar_nodes()` filtering by same `node_type` and `threshold = surface_similarity_threshold` (default **0.80**). If a match is found, the new concept merges into the best-scoring existing node.
3. **Create new node** — if neither match succeeds, a new `KGNode` is created with the computed embedding (if available).

**Cross-turn edge resolution:**
After processing the current turn's concepts, the full session node map is loaded (`get_nodes_by_session`) and merged into `label_to_node`. This allows edges extracted this turn to reference nodes created in prior turns. When a relationship's source or target resolves to a deduplicated existing node, the edge is created between those node IDs (not the original extracted text).

**Edge deduplication:** duplicate edges (same source, target, and `edge_type`) are merged — the utterance is added to the existing edge's provenance rather than creating a new edge.

**Scope:** deduplication is session-scoped. The same concept text in different sessions creates independent nodes.

## Correctness Requirements

1. **Embedding required for semantic dedup** — if `embedding_service` is `None`, only exact-match dedup runs. Nodes without embeddings silently skip Step 2 and always create new nodes on re-extraction.
2. **`surface_similarity_threshold = 0.80` is intentionally high** — the surface graph preserves language variation. A lower threshold would collapse distinct phrasings into one node prematurely.
3. **Same `node_type` required for semantic merge** — two concepts of different types (e.g., `attribute` vs. `functional_consequence`) will never merge even if text is similar.
4. **Cross-turn edge resolution loads all session nodes** — edges referencing prior-turn concepts are correctly wired only because the full session graph is loaded at Step 1.5. If this load fails or returns stale data, cross-turn edges will be silently dropped (`edge_skipped_missing_node`).
5. **Dedup is session-scoped** — no global or cross-session merging occurs.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Same concept creates multiple surface nodes | `embedding_service` not configured (semantic dedup skipped), or `surface_similarity_threshold` too high for the concept pair | Verify `embedding_service` is injected; lower threshold if intentional merging is desired |
| Semantically different concepts merged | `surface_similarity_threshold` too low | Raise threshold toward 0.85–0.90 and re-test |
| Cross-turn edges silently dropped | Source or target node not found in `label_to_node` — concept text varies turn-over-turn and exact match fails | Check `edge_skipped_missing_node` log; lower threshold or verify embedding pipeline |
| Edges lost after dedup | Edge dedup merge not adding utterance to provenance | Check `edge_deduplicated` log and `repo.add_edge_source_utterance()` path |
| Nodes created without embeddings | `embedding_service` unavailable or encoding failed | Check `embedding_service` initialization; verify spaCy model (`en_core_web_md`) is installed |
| `aggregate_surface_edges_to_canonical` raises `AttributeError` | `canonical_slot_repo` is `None` but `enable_canonical_slots=True` | Verify `GraphService` is constructed with `canonical_slot_repo` when dual-graph mode is enabled |

## Key Files

- `src/services/graph_service.py` — `GraphService` (dedup logic in `_add_or_get_node`, edge resolution in `_add_edge_from_relationship`)
- `src/services/turn_pipeline/stages/graph_update_stage.py` — Stage 4 wiring
- `src/persistence/repositories/graph_repo.py` — `find_node_by_label_and_type`, `find_similar_nodes`, `create_node`
- `src/domain/models/knowledge_graph.py` — `KGNode`, `KGEdge`, `GraphState`
- `src/core/config.py` — `deduplication.surface_similarity_threshold` (default 0.80)
