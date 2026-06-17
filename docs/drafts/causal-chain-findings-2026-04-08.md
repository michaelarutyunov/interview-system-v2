# Causal Chain Extraction Analysis — 2026-04-08

## Executive Summary

Analysis of the first causal chain extraction run (20260325_111835_glp1_food_mec_strict_glp1_user.json) revealed two significant bugs affecting chain counts and conformance metrics:

1. **xvih (P1):** `superseded_by` field is never populated despite 5 `revises` edges existing — **FIXED**
2. **ep8i (P2):** Maximal path filter is **NOT buggy** — 896 violating chains are real, caused by LLM ignoring MEC ladder ordering

---

## Bug 1: Revises Edges Without Supersession (xvih)

### Finding
- **Revises edges (surface):** 5
- **Superseded nodes excluded:** 0
- **Expected:** 5 nodes should have `superseded_by != null`

### Root Cause
The `handle_contradiction()` method in `src/services/graph_service.py` (line 421) is **never called** by the extraction pipeline. The method exists but is orphaned — it's not integrated into the graph update flow.

### Current Flow
1. LLM extracts `revises` relationships (edge type defined in methodology YAML)
2. `add_extraction_to_graph()` calls `_add_edge_from_relationship()`
3. Edge is created normally via `repo.create_edge()`
4. `supersede_node()` is **never called**
5. `superseded_by` remains `NULL` for all nodes

### Code Evidence
**src/services/graph_service.py:421-463**
```python
async def handle_contradiction(
    self,
    session_id: str,
    old_node_id: str,
    new_concept: ExtractedConcept,
    utterance_id: str,
) -> Tuple[KGNode, KGEdge]:
    """
    Handle a contradiction between old and new beliefs.

    Creates new node and REVISES edge, marks old node as superseded.
    """
    # Create new node for the new belief
    new_node = await self.repo.create_node(...)

    # Mark old node as superseded
    await self.repo.supersede_node(old_node_id, new_node.id)

    # Create REVISES edge
    edge = await self.repo.create_edge(
        session_id=session_id,
        source_node_id=new_node.id,
        target_node_id=old_node_id,
        edge_type="revises",
        ...
    )
```

This method is **not referenced anywhere** in the codebase:
```bash
$ rg -n "handle_contradiction" src/ --type py
src/services/graph_service.py:421:    async def handle_contradiction(
```

### Impact
1. **Causal chain skill bug:** The skill filters on `superseded_by` to exclude retracted chains. With this field always `NULL`, superseded nodes are incorrectly included in chain extraction.
2. **Retracted chain count:** Always reports 0 even when 5 `revises` edges exist.
3. **Data integrity:** Graph state claims contradictions exist (via `revises` edges) but doesn't mark which nodes are superseded.

### Fix Options

**Option A: Call `handle_contradiction()` when `revises` is extracted**
- Modify `_add_edge_from_relationship()` to detect `relationship_type == "revises"`
- Parse the source and target texts
- Find existing nodes
- Call `handle_contradiction()` instead of normal edge creation
- **Pros:** Uses existing implementation, maintains consistency
- **Cons:** Requires restructuring of `_add_edge_from_relationship()`

**Option B: Integrate contradiction handling into `_add_edge_from_relationship()`**
- Add special case for `revises` edge type
- Call `repo.supersede_node()` before creating the edge
- **Pros:** Minimal code change, keeps logic local
- **Cons:** Duplicates some logic from `handle_contradiction()`

**Recommended:** Option A for cleaner separation of concerns.

---

## Non-Bug: Maximal Path Filter (ep8i) — NOT INFLATED

### Finding
- **Surface chains:** 32 conforming / 896 violating = **3.4% conformance** (not 16% as originally reported — 16% included permissive-only paths)
- **Graph size:** 104 nodes, 165 `leads_to` edges, 5 roots
- **Total maximal paths:** 928 (all survive the prefix filter — no inflation)

### Investigation Results

**The prefix-only maximal filter is correct for this domain.**

Measured:
- 928 total paths enumerated by DFS (cycle-guarded, length ≥ 2)
- Prefix filter removed: **0 paths** — all 928 are genuinely maximal
- 658 paths contain shortcut edges (direct A→C alongside A→B→C), but these are structurally distinct routes through the DAG
- 270 paths have no shortcut edges at all

**Applying subsequence-based filtering would be a bug.** It would collapse structurally distinct chains that share start/end nodes but take different routes through the graph — exactly the structural diversity that causal chain analysis should preserve. Two different attribute→value ladders via different consequence chains would be incorrectly merged.

### Real Finding: LLM Extraction Quality

The 896 violating chains are a **real validation finding**, not a filter artifact. Top violating edge types:

| Violation | Count | Description |
|-----------|-------|-------------|
| psychosocial_consequence → functional_consequence | 1236 | L3→L2 (backwards hop) |
| functional_consequence → instrumental_value | 458 | L2→L4 (skipping L3) |
| terminal_value → functional_consequence | 388 | L5→L2 (backwards hop) |
| instrumental_value → psychosocial_consequence | 370 | L4→L3 (backwards hop) |

Permitted MEC ladder ordering: attribute(L1) → functional_consequence(L2) → psychosocial_consequence(L3) → instrumental_value(L4) → terminal_value(L5).

The LLM extractor creates edges that violate this ordering. The `permitted_connections` validation in `extraction_service.py` is **commented out** (lines 479-495), so violations pass through unchecked.

### Recommendation
- **Do NOT modify the maximal path filter** — it's working correctly
- **Close ep8i as not-a-bug** with finding documented
- **Create follow-up bead** for re-enabling permitted_connections validation in extraction

---

## Related Issues

### bp6t: Surface Conformance Ratio (3.4%)
Confirmed as a **real validation finding**. The LLM extractor does not respect MEC ladder ordering at the surface level. 896 of 928 chains violate `permitted_connections`. Canonical slots achieve 100% by collapsing surface variance — this is expected, not a bug.

Root cause: `permitted_connections` validation is commented out in `extraction_service.py:479-495`.

### 7g7s: Retracted Chain Count
Fix implemented (xvih). Now that `supersede_node()` is called for revises edges, `superseded_by` will be populated. Update the skill's retracted count logic:
```python
retracted_count = len([n for n in nodes if n.get('superseded_by')])
```

---

## Updated Next Steps

1. ~~**Fix xvih (P1):** Integrate revises handling into pipeline~~ **DONE**
2. ~~**Fix ep8i (P2):** Tighten maximal path filter~~ **NOT A BUG** — filter is correct
3. **Fix 7g7s (P2):** Update retracted count in skill (now unblocked)
4. **Re-run extraction:** After xvih fix, validate superseded_by is populated
5. **Follow-up:** Re-enable `permitted_connections` validation in extraction
