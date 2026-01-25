# ADR 008: Concept-Driven Coverage and Depth Tracking

## Context

The concept-driven interview system has a fundamental architectural gap: concept elements are structurally disconnected from the interview flow.

**Current broken behavior:**
```python
# graph_repo.py compares incompatible namespaces
elements_seen = [row[0] for row in ...]  # Node LABELS like "creamy texture"
elements_total = await self._load_concept_elements()  # Element IDs like "creamy_texture"

# These never match - coverage always shows 0%
if element_id not in elements_seen:  # Always true!
```

**Problems:**
1. Coverage tracking is broken (compares node labels to element IDs)
2. No semantic linking between extracted nodes and concept elements
3. No depth tracking (system doesn't know if user laddered from attribute to value)
4. Concepts contain `type` field, conflating WHAT (concept) with HOW (methodology)

## Decision

Implement a two-layer architecture where:
1. **Concepts** define WHAT to explore (semantic targets via elements)
2. **Methodologies** define HOW to explore (node types, ladder, opening style)
3. **Elements link to nodes** via semantic matching (LLM + alias fallback)
4. **Depth is validated** via chain validation (undirected graph traversal)

### Key Changes

**1. Element IDs are integers**
```yaml
elements:
  - id: 1  # Integer, not string
    label: "Creamy texture"
    aliases: ["silky", "smooth", "foam"]
```

**2. Element linking during extraction**
```python
class ExtractedConcept(BaseModel):
    text: str
    node_type: str
    linked_elements: List[int] = []  # NEW: integer element IDs
```

**3. Depth via chain validation**
- Build subgraph of nodes linked to each element
- Find longest connected path (undirected edges)
- `depth_score = longest_chain_length / methodology_ladder_length`

**4. Coverage state structure**
```python
coverage_state = {
    "elements": {
        1: {
            "covered": True,  # Any linked node
            "linked_node_ids": ["node_123"],
            "types_found": ["attribute"],
            "depth_score": 0.25,  # 1/4 chain
        },
    },
    "elements_covered": 1,
    "elements_total": 6,
    "overall_depth": 0.25,
}
```

## Consequences

### Positive
1. **Concepts become meaningful** - elements drive real coverage tracking
2. **Depth tracking** - validates actual laddering via graph edges, not just type presence
3. **Decoupled design** - concepts portable across methodologies
4. **No new scorers** - repurposes existing CoverageGapScorer and DepthBreadthBalanceScorer

### Negative
1. **LLM token overhead** - +100-200 tokens/turn for element linking in extraction prompt
2. **Chain validation cost** - O(V+E) graph traversal per element (typically <10 nodes)
3. **Concept migration** - existing YAMLs need updates

### Mitigations
1. Token cost is acceptable - piggybacks on existing extraction call (zero new API calls)
2. Graph traversal is cheap - elements have few linked nodes in practice
3. Backward compatibility - old concepts work (empty aliases = label-only matching)

## Alternatives Considered

### Alternative 1: Simple type counting
Count distinct node types per element, ignore connectivity.
- **Rejected:** Doesn't validate laddering (attribute + psychosocial with no functional = 0.5 depth, but not a real chain)

### Alternative 2: Store linking in separate step
Run separate LLM call after extraction for element linking.
- **Rejected:** Doubles API calls; extraction already sees node labels

### Alternative 3: String-based element IDs
Keep using strings like `creamy_texture` for element IDs.
- **Rejected:** Integer IDs simpler; avoids underscore/space mismatch issues

## Implementation

See implementation plan: `~/.claude/plans/playful-questing-pizza.md`

**Phases:**
1. Fix broken coverage comparison
2. Enriched concept format (aliases, context)
3. Element linking during extraction
4. Depth tracking (chain validation)
5. Scorer updates

## References

- Plan: playful-questing-pizza.md
- Related: ADR 006 (Scoring Architecture), ADR 007 (YAML Methodology Schema)
