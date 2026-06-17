# Extraction Quality Discussion

> **Date**: 2026-02-04
> **Participants**: User + Claude
> **Status**: Exploratory discussion, no implementation yet

---

## Context

The interview system's extraction pipeline produces significantly fewer edges than expected:

| Metric | Actual | Target | Gap |
|--------|--------|--------|-----|
| Nodes | 62 | ~30-40 | 55% over |
| Edges | 33 | 120-180 | 80% under |
| Edge/Node ratio | 0.53 | 2-3 | 6x below |
| Orphan nodes | 16 (26%) | <5% | 5x over |

An initial investigation was documented in `docs/plans/extraction_issues.md`. This discussion goes deeper into root causes and potential solutions.

---

## Part 1: Initial Analysis

### JSON Evidence - Semantic Duplication

The JSON reveals rampant semantic duplication. Examples from same interview:

**Vitamin/Calcium cluster (4 nodes for ~1 concept):**
- `"fortified with vitamin D and calcium"` (attribute)
- `"fortified with calcium and vitamin D"` (attribute)
- `"getting enough vitamin D and calcium"` (functional_consequence)
- `"getting calcium and vitamin D"` (functional_consequence)

**Energy cluster (5+ nodes for ~1 concept):**
- `"more energy throughout the day"` (psychosocial)
- `"more energy"` (functional)
- `"energy"` (psychosocial)
- `"sustained energy throughout the day"` (functional)
- `"maintaining baseline energy"` (functional)

**Digestion cluster (4 nodes):**
- `"easier to digest"` (functional)
- `"better digestion"` (functional)
- `"easier on my digestion"` (functional)
- `"body doesn't have to work as hard to process it"` (functional)

### Key Finding

**The system is OVER-EXTRACTING NODES, not under-extracting edges.**

The LLM:
1. Creates new nodes for every paraphrase
2. Doesn't know existing nodes exist
3. Can't link back to previously extracted concepts
4. Creates orphans because edges reference non-existent (this turn's) labels

---

## Part 2: Root Causes Identified

### Cause 1: LLM Blindness to Graph State (CRITICAL)

The extraction LLM receives:
- Last 5 conversation turns
- Methodology guidelines
- Element definitions for linking
- **NO existing graph nodes**
- **NO information about what was already extracted**

The LLM is asked to extract concepts **as if no graph exists**.

**Impact**: Every turn creates fresh nodes, leading to semantic duplicates and orphans.

### Cause 2: Exact-Match-Only Deduplication

Deduplication uses case-insensitive **exact match only**:
- `"more energy"` ≠ `"energy"` (different nodes)
- `"feel healthier"` ≠ `"feeling healthier"` (different nodes)
- `"vitamin D and calcium"` ≠ `"calcium and vitamin D"` (different nodes)

### Cause 3: Abstract MEC Node Type Definitions

The MEC hierarchy creates inherent ambiguity:

| Level | Type | Problem |
|-------|------|---------|
| 2 | functional_consequence | vs. 3? |
| 3 | psychosocial_consequence | vs. 4? |
| 4 | instrumental_value | vs. 3? |

Definitions lack differentiation criteria and boundary case examples.

### Cause 4: Prompt Structure Buries Relationship Instructions

The extraction prompt is ~180 lines. Relationship extraction guidance is sandwiched between element linking and methodology examples - it gets "lost in the noise."

### Cause 5: Edge Loss from Cross-Turn References

If the LLM creates a relationship like `"nice sensation" → "feel good"` but only extracted `"pleasant sensation"` this turn (not `"nice sensation"`), the edge is silently discarded.

---

## Part 3: Hypothesis Evaluation

| Hypothesis | Assessment |
|------------|------------|
| Bad model choice | UNLIKELY - model is capable, just blind to context |
| Prompt issues | CONFIRMED - relationships buried, no quota enforcement |
| Incomplete context | **PRIMARY CAUSE** - LLM doesn't see existing nodes |
| NLP augmentation needed | Revisited - see Part 5 |
| Schema definitions | PARTIAL - MEC hierarchy is abstract, but not root cause |

---

## Part 4: The Node Grouping Idea

### Proposal

Add a "node grouping" step in the pipeline:
1. After extraction, cluster nodes semantically (e.g., "energy" group)
2. Pass grouped nodes to next turn's extraction context
3. LLM sees "buckets" to map new concepts into

### User's Concerns (Valid)

1. **Early stage dominance**: 3 initial nodes become 3 groups → everything funnels into them
2. **Late stage over-grouping**: 15 groups create "gravity wells" → LLM avoids creating truly novel concepts

### Analysis

This is a classic **explore vs. exploit tradeoff**. Prompting cannot reliably solve it because:

1. **LLMs are pattern matchers**: When shown 15 groups, they naturally classify into existing categories
2. **Confidence asymmetry**: Matching to existing group feels "safe," creating new feels "risky"
3. **Context priming**: Showing groups primes the LLM to think in those terms

### Conclusion

> **Showing groups biases extraction. The bias cannot be reliably removed through prompting.**

Better approach: **Separate extraction from deduplication**
- Extract WITHOUT showing groups (unbiased)
- Deduplicate AFTER extraction (separate decision with tunable threshold)

---

## Part 5: Revisiting NLP Augmentation

### Initial Dismissal

"LLMs already do implicit linguistic analysis" - so NLP preprocessing adds little value.

### User's Reframe

The argument isn't about replacement, but **making implicit structure explicit BEFORE the LLM sees it**.

The LLM is juggling many tasks during extraction:
- Node type classification
- Confidence scoring
- Stance detection
- Element linking
- JSON formatting
- Relationship extraction

By the time it gets to relationships, attention is already "spent." Relationships get deprioritized.

### How SRL Could Help

**Example utterance:**
> "I switched to oat milk because it's easier to digest and that helps me feel more energetic"

**With SRL annotation:**
```
PREDICATE: switched
  AGENT: I
  THEME: oat milk
  CAUSE: easier to digest

PREDICATE: helps
  CAUSER: that [=easier to digest]
  EXPERIENCER: me
  RESULT: feel more energetic

CAUSAL_CLAUSE: "because it's easier to digest"
  ANTECEDENT: switched to oat milk
  CONSEQUENT: easier to digest
```

**Enhanced extraction context:**
```
STRUCTURAL ANALYSIS (use this to guide relationship extraction):
- Causal link detected: "oat milk" CAUSES "easier to digest"
- Causal link detected: "easier to digest" ENABLES "feel more energetic"
- Coreference: "that" refers to "easier to digest"
```

This **pre-computes the hard part** and hands it to the LLM.

### Problem-to-Solution Mapping

| Problem | NLP Solution |
|---------|--------------|
| Implicit relationships | Dependencies make them explicit (subject→verb→object chains) |
| Orphaned nodes | SRL binds arguments to predicates even when distant in text |
| Missing causal links | Constituency parsing identifies "because X, Y" clause structures |
| Over-extraction of entities | POS constraints filter to content words (nouns, verbs) |

### What SRL Doesn't Solve

- **Semantic duplication**: SRL won't know "more energy" = "sustained energy"
- **Node type classification**: SRL tells WHAT relates to WHAT, not ontological type
- **Cross-turn relationships**: SRL operates within utterances

### Practical Considerations

**Speed**: SRL on 3-4 sentences is ~50-100ms with spaCy or Stanza. Not an LLM call.

**Risk**: SRL models trained on written text may struggle with conversational speech (fragments, hedging, run-ons).

**Integration point**: Context enrichment - LLM sees both raw text AND structural analysis.

### Revised Assessment

> **NLP provides STRUCTURAL scaffolding that reduces cognitive load on the extraction LLM.**

It's not about replacing LLM intelligence - it's about presenting information in a form that's easier for the LLM to act on.

---

## Part 6: Key Reframes from Discussion

### On the Graph's Purpose

> "This is not a proper knowledge graph. It's a conversation graph that emulates what accumulates in a moderator's head."

The graph is a **working memory structure**, not a knowledge base. Quality means usefulness for conversation steering, not ontological correctness.

### On Perfection vs. Incrementalism

> "The task is not to make it perfect, but to correct surface issues like node duplication."

Incremental improvements are acceptable. Longer pipeline with extra LLM calls is OK for demonstrating working flow. Parallelization is a future optimization.

### On Context for Extraction

> "The definition of what constitutes a node + recent conversations is insufficient."

Current context (node type definitions + conversation history) isn't enough. Need MORE structure. NLP could provide that structure.

---

## Part 7: Open Questions

1. **Relationship extraction without node awareness**: Can you extract edges without knowing existing nodes? Or is this fundamentally a two-pass problem?

2. **Canonical labels**: Should they drive new extraction, or should new extractions be independent and then deduplicated?

3. **Deduplication granularity**: Match on label only? Label + type? Label + type + connected edges? Utterance context?

4. **SRL accuracy on conversational text**: Need to test whether off-the-shelf tools handle interview transcripts well.

5. **Psychosocial node type confusion**: Could a dedicated technique be triggered when graph growth stagnates on psychosocial nodes? (Parked for separate bead)

---

## Part 8: Proposed Next Steps

1. **Small SRL experiment**: Take 5-10 utterances, run SRL, add structural analysis to extraction prompt, compare results

2. **Post-extraction deduplication**: Implement semantic similarity check (embeddings or lightweight LLM call)

3. **Phase-aware thresholds**: Early stage = favor novelty, late stage = favor consolidation

4. **Prompt restructuring**: Move relationship instructions to prominent position, add explicit quota

---

## Appendix: Files Referenced

| File | Purpose |
|------|---------|
| `src/services/turn_pipeline/stages/extraction_stage.py` | Context formatting, LLM call |
| `src/llm/prompts/extraction.py` | Extraction prompt construction |
| `src/services/graph_service.py` | Node/edge deduplication |
| `config/methodologies/means_end_chain.yaml` | MEC schema, extraction guidelines |
| `docs/plans/extraction_issues.md` | Initial investigation |
| `synthetic_interviews/20260204_015548_oat_milk_v2_health_conscious.json` | Example output |
