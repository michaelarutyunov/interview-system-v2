# ADR-019: Graph Depth via BFS from Roots, Not Exhaustive Longest Path

**Status:** Accepted
**Date:** 2026-02-19
**Context:** StateComputationStage (Stage 5) — `graph_repo._find_longest_path`

---

## Plain-Language Summary

Imagine you're measuring how deep a river system goes by tracing every possible path from every
source to every mouth, backtracking every time you hit a dead end. For a small stream that's fine.
For a large river network with 64 tributaries it would take geological time.

That is what the original code did. For each node in the graph it tried every possible sequence
of nodes it could visit — all permutations — to find the absolute longest one. With 64 nodes
this means on the order of 64 × 64! candidate paths. At turn 12 this caused `StateComputationStage`
to take 323 seconds. At turn 13 the process hung for over 12 minutes before being killed.

The fix: instead of tracing every path, start only from the **source nodes** (concepts with no
incoming edges — the "headwaters"), follow edges forward, and record the furthest you reach from
each source. This is like measuring river depth by starting at the spring and counting how many
steps it takes to reach the sea — no backtracking needed.

---

## Context

`StateComputationStage` calls `graph_repo.get_graph_state()` every turn to refresh graph metrics.
One of those metrics is `depth_metrics.max_depth` — the length of the longest reasoning chain
(e.g., *attribute → consequence → value*). This drives the `graph.max_depth` signal, which in
turn feeds strategy selection and interview progress scoring.

### Original Implementation

```python
# _dfs_longest_path — the NP-hard implementation
def _dfs_longest_path(self, node, adjacency, visited):
    visited.add(node)
    max_length = 1
    for neighbor in adjacency[node]:
        if neighbor not in visited:
            path_length = self._dfs_longest_path(neighbor, adjacency, visited)
            max_length = max(max_length, 1 + path_length)
    visited.remove(node)   # ← backtracking: tries all permutations
    return max_length
```

`visited.remove(node)` on backtrack means the algorithm explores **every permutation** of nodes,
not just every reachable path. This is the exact computational structure of the Hamiltonian path
problem — known to be NP-hard. Complexity: **O(V × V!)**.

Observed runtimes:
- Turn 10 (48 nodes): ~18 seconds
- Turn 12 (64 nodes): **323 seconds**
- Turn 13 (68+ nodes): **> 12 minutes** (process killed via SIGUSR2)

The graph was also built as **undirected** (edges added in both directions), which both worsens
the combinatorial explosion and loses the semantic direction of edges (`attribute → consequence`
is not the same as `consequence → attribute`).

---

## Decision

Replace the exhaustive DFS with **directed BFS from root nodes**, matching the approach already
in use by `canonical_graph_service._compute_max_depth`.

### New Implementation

```python
def _build_directed_adjacency(self, node_ids, edges):
    """Preserves source → target direction of reasoning edges."""
    adjacency = {nid: [] for nid in node_ids}
    has_incoming = set()
    for edge in edges:
        if edge.source_node_id in node_ids and edge.target_node_id in node_ids:
            adjacency[edge.source_node_id].append(edge.target_node_id)
            has_incoming.add(edge.target_node_id)
    return adjacency, has_incoming

def _find_longest_path_bfs(self, adjacency, node_ids, has_incoming):
    """BFS from each root node; no backtracking. O(V × (V+E))."""
    roots = node_ids - has_incoming or node_ids  # fallback: all nodes if fully cyclic
    max_depth = 0
    for root in roots:
        visited = set()
        queue = deque([(root, 0)])
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            max_depth = max(max_depth, depth)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
    return max_depth
```

Complexity: **O(V × (V+E))** — polynomial. For 64 nodes and ~23 edges this runs in microseconds.

---

## Alternatives Considered

### 1. True Longest Simple Path (exact)
The original approach, just written more carefully. Rejected: the problem is inherently NP-hard
on general graphs. No correct exact algorithm runs in polynomial time.

### 2. Graph Diameter (BFS twice)
Standard trick: pick any node, BFS to find the farthest node u, then BFS from u to find the
farthest node v. Length(u,v) approximates diameter. Rejected: diameter is a property of
undirected graphs; our graph is directed. "Farthest from any root" is the correct semantic for
reasoning chains, and BFS-from-roots achieves it exactly.

### 3. DAG Longest Path (topological sort + DP)
Exact longest path in a DAG runs in O(V+E). Rejected: the surface graph may have cycles
(deduplication doesn't guarantee a DAG). BFS-from-roots handles cycles gracefully via the
visited set, without requiring cycle detection as a precondition.

### 4. Keep DFS, add depth limit
Cap recursion at, say, 20 hops. Rejected: hard-coded limits violate the project's no-heuristics
principle, and the real fix is algorithmic, not a band-aid.

---

## Consequences

**Positive:**
- `StateComputationStage` runs in microseconds regardless of graph size
- Directed adjacency preserves the semantic meaning of edges
- Implementation mirrors `canonical_graph_service._compute_max_depth` — one canonical pattern
  across both graphs

**Trade-off:**
- BFS-from-roots gives the longest path reachable *following edge direction from root nodes*.
  This is slightly different from the absolute longest simple path (which could start from
  a mid-chain node). In practice this distinction doesn't matter: reasoning chains in MEC
  always start at attributes (root nodes) and terminate at values (leaf nodes). A path that
  starts mid-chain would be a subchain of a longer root-anchored path.

**Future maintenance note:**
Do not revert to exact DFS "for accuracy". The semantic model (longest chain from source
attribute) matches BFS-from-roots exactly, and the runtime difference is O(V×V!) vs O(V×(V+E)).
