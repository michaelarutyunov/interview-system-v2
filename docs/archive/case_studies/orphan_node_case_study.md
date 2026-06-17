# Case Study: Orphan Node Selection in Knowledge Graph Interviews

**Date**: 2026-03-09
**Interview**: Meal Planning JTBD v2 (Baseline Cooperative)
**Node**: "avoid cooking something too complex when tired"
**Turns**: Created in Turn 8, Selected for focus in Turn 10

---

## Executive Summary

A knowledge graph node was extracted with **zero semantic connections** to other concepts, yet was still selected for focus by the strategy selection system. This case study examines the root cause (LLM extraction failure), the system's self-awareness (orphan detection), and why selection still occurred (freshness + strategy fit).

---

## Phenomenon

During a synthetic interview simulation, a node representing the user's constraint ("avoid cooking something too complex when tired") was:

1. **Extracted** in Turn 8 alongside 7 other related concepts
2. **Connected to nothing** - 0 edges in, 0 edges out
3. **Detected as orphan** by the system (`graph.node.is_orphan: True`)
4. **Selected for questioning** in Turn 10 (score: 2.33)

### Visual Evidence

In the generated mermaid diagram, this node appears in the Turn 8 column but has no edge lines connecting it to any other nodes. It displays "F10" indicating focus selection in Turn 10.

---

## Root Cause Analysis

### Why Was It Not Connected?

**LLM Extraction Service Failure**

The extraction stage (`extraction_stage.py`) extracted 8 concepts and created 10 edges in Turn 8, but our target node received **zero relationships**.

```python
# Turn 8 extraction results:
nodes_added: 8
edges_added: 10
edges_involving_target: 0  # ← The problem
```

**Evidence that extraction was working otherwise:**

Other nodes from the same turn WERE successfully connected:
- `tension between meal effort level` → `ordering takeout as fallback` (triggers)
- `cascade of small decisions` → `negotiating meal preferences` (enables)
- `avoid low-effort fallbacks` → `tension between effort level` (conflicts_with)

**Hypothesis**: The LLM prompt did not encourage cross-linking between the concept "avoid cooking something too complex when tired" and semantically related nodes like "tension between meal effort level and post-work energy" or "cascade of small simultaneous dinner decisions."

---

## System Behavior

### Self-Awareness: Orphan Detection

The system correctly detected the isolation:

```python
# Turn 9 node_signals for target:
{
  "graph.node.is_orphan": True,
  "graph.node.edge_count": 0,
  "graph.node.has_outgoing": False,
  "graph.node.exhaustion_score": 0.0
}
```

The `graph.node.is_orphan` signal (from `node_signal_detection_service.py`) uses `node_state.out_degree + node_state.in_degree == 0` to flag disconnected nodes.

### Selection Despite Isolation

**Turn 9**: Not selected (other concepts ranked higher)
**Turn 10**: Selected with `uncover_obstacles` strategy (Score: 2.33)

**Why it scored high:**
1. **Freshness bonus**: `exhaustion_score: 0.0` (never explored)
2. **Strategy fit**: `uncover_obstacles` looks for constraints/barriers
3. **Node-level scoring**: Fresh nodes get priority in Stage 2 joint scoring

---

## Implications

### 1. LLM Extraction Limitations

Semantic relationship detection is not guaranteed, even for clearly related concepts. The same extraction call that successfully linked 7 other concepts failed to link our target node.

**Mitigation strategies:**
- Improve extraction prompts to explicitly check for relationships with all newly extracted concepts
- Add post-extraction "relationship inference" using embedding similarity
- Implement a "connection suggestion" mechanism for low-degree nodes

### 2. Robustness of Strategy Selection

The system can still surface important concepts even when they're not integrated into the knowledge graph. This is **feature, not bug** - the interview can explore orphaned concepts that may represent unique user constraints or preferences.

### 3. Signal Pool Architecture

The `graph.node.is_orphan` signal provides self-awareness that enables the system to understand graph topology limitations. Future strategies could:
- Prioritize orphan nodes for connection-building questions
- Use orphan status as a signal for "unique/unexplored territory"
- Track orphan resolution over time (did later questions successfully integrate the node?)

---

## Related Files

| File | Relevance |
|------|-----------|
| `src/services/extraction_service.py` | LLM-based concept and relationship extraction |
| `src/signals/graph/node_signals.py` | `is_orphan`, `edge_count`, `exhaustion_score` detection |
| `src/methodologies/scoring.py` | Strategy→node joint scoring with phase multipliers |
| `docs/data_flow_paths.md` | Path 5: Traceability chain (utterance → node → edge) |
| `scripts/generate_mermaid_graph.py` | Visualization showing orphan node isolation |

---

## Recommended Actions

1. **Improve extraction prompts**: Add explicit instruction to cross-reference newly extracted concepts for semantic relationships
2. **Add orphan tracking metric**: Track orphan node lifecycle (created → selected → integrated or remained orphan)
3. **Consider connection-focused strategy**: A strategy that specifically targets orphan nodes for "bridge-building" questions
4. **Embedding-based fallback**: When LLM extraction produces no relationships for a concept, use embedding similarity to suggest potential connections

---

## Conclusion

This orphan node case demonstrates both a limitation (LLM extraction can miss semantic links) and a robustness (strategy selection works despite graph gaps). The system's self-awareness via `graph.node.is_orphan` enables it to understand and work around these extraction failures.

**Key insight**: Knowledge graph connectivity is **necessary but not sufficient** for interview quality. Orphan nodes can represent valuable user constraints that deserve exploration even if the extraction stage failed to link them to the broader graph.
