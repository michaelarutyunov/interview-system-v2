# Extraction Pipeline Extensions Summary

> **Date**: 2026-02-04
> **Status**: Proposal for discussion
> **Related**: [extraction_discussion.md](extraction_discussion.md)

---

## Current Pipeline (Baseline)

```
Stage 1:  ContextLoadingStage      - Load session, graph state
Stage 2:  UtteranceSavingStage     - Save user input
Stage 3:  ExtractionStage          - LLM extracts concepts + relationships
Stage 4:  GraphUpdateStage         - Add nodes/edges to graph (exact-match dedup)
Stage 5:  StateComputationStage    - Refresh graph metrics
Stage 6:  StrategySelectionStage   - Select next strategy
Stage 7:  ContinuationStage        - Decide if interview continues
Stage 8:  QuestionGenerationStage  - Generate next question
Stage 9:  ResponseSavingStage      - Save system response
Stage 10: ScoringPersistenceStage  - Save scoring data
```

**Current extraction latency**: ~3-4s (single LLM call)
**Current edge/node ratio**: 0.53 (target: 2-3)

---

## Proposed Extensions

### Extension 1: SRL Preprocessing Stage

**Insert between**: Stage 2 (UtteranceSaving) → Stage 3 (Extraction)

```
Stage 2:   UtteranceSavingStage
Stage 2.5: SRLPreprocessingStage  ← NEW
Stage 3:   ExtractionStage (receives SRL context)
```

**Purpose**:
- Run Semantic Role Labeling on the current utterance (and optionally last 2-3 utterances)
- Extract predicate-argument structures, causal clauses, coreference
- Pass structural analysis as additional context to extraction LLM

**What it provides to extraction**:
```
STRUCTURAL ANALYSIS:
- Predicate "switched": AGENT=I, THEME=oat milk, CAUSE=easier to digest
- Predicate "helps": CAUSER=easier to digest, RESULT=feel energetic
- Causal clause detected: "because it's easier to digest"
- Coreference: "that" → "easier to digest"
```

**Latency added**: 50-150ms (local NLP model, no LLM call)

**Impact on quality**:
| Metric | Expected Change |
|--------|-----------------|
| Edge/node ratio | +30-50% (relationships made explicit) |
| Orphan nodes | -20-30% (arguments bound to predicates) |
| Node count | Neutral (doesn't affect node extraction) |

**Risks**:
- SRL accuracy on conversational text may be lower than on formal text
- Requires additional dependency (spaCy/Stanza)

---

### Extension 2: Semantic Deduplication Stage

**Insert between**: Stage 3 (Extraction) → Stage 4 (GraphUpdate)

```
Stage 3:   ExtractionStage
Stage 3.5: SemanticDeduplicationStage  ← NEW
Stage 4:   GraphUpdateStage (receives deduplicated concepts)
```

**Purpose**:
- Compare each extracted concept against existing graph nodes
- Use semantic similarity (embeddings or lightweight LLM) to detect near-duplicates
- Map duplicates to canonical labels before graph update

**What it does**:
```
Extracted: "sustained energy throughout the day"
Existing:  "more energy throughout the day" (similarity: 0.91)
Action:    Reuse existing label → no new node created
```

**Latency added**:
- Embedding-based: 100-200ms (local model)
- LLM-based: 500-1000ms (lightweight prompt per concept)

**Impact on quality**:
| Metric | Expected Change |
|--------|-----------------|
| Edge/node ratio | +50-100% (fewer duplicate nodes) |
| Orphan nodes | -40-60% (edges connect to existing nodes) |
| Node count | -30-50% (duplicates consolidated) |

**Configuration**:
- Similarity threshold (e.g., 0.85)
- Phase-aware thresholds: early=0.95 (favor novelty), late=0.80 (favor consolidation)

**Risks**:
- Over-merging distinct concepts (e.g., "mental energy" vs "physical energy")
- Requires embedding model or additional LLM calls

---

### Extension 3: Two-Pass Extraction

**Replace**: Stage 3 (Extraction) with two sub-stages

```
Stage 3a: ConceptExtractionStage     ← NEW (Pass 1)
Stage 3b: RelationshipExtractionStage ← NEW (Pass 2)
```

**Purpose**:
- Pass 1: Extract concepts only (focused task, no relationship burden)
- Pass 2: Given extracted concepts, extract relationships between them (focused task)

**What it does**:
```
Pass 1 prompt: "Extract concepts from this utterance"
Pass 1 output: [concept1, concept2, concept3]

Pass 2 prompt: "Given these concepts, identify relationships between them"
Pass 2 input:  [concept1, concept2, concept3] + utterance
Pass 2 output: [concept1 → concept2, concept2 → concept3]
```

**Latency added**: +2-3s (additional LLM call)

**Impact on quality**:
| Metric | Expected Change |
|--------|-----------------|
| Edge/node ratio | +50-100% (dedicated relationship focus) |
| Orphan nodes | -30-50% (explicit relationship pass) |
| Node count | Neutral |

**Risks**:
- Doubles extraction latency
- Pass 2 may miss implicit relationships not tied to Pass 1 concepts

---

### Extension 4: Cross-Turn Relationship Stage

**Insert between**: Stage 3 (Extraction) → Stage 4 (GraphUpdate)

```
Stage 3:   ExtractionStage
Stage 3.6: CrossTurnRelationshipStage  ← NEW
Stage 4:   GraphUpdateStage
```

**Purpose**:
- Identify relationships between current turn's concepts and previous turns' concepts
- Specifically handle Q→A relationships (interviewer question → respondent answer)
- Connect concepts that span turns but weren't linked during single-turn extraction

**What it does**:
```
Previous turn question: "Why does that sustained energy matter?"
Current turn answer: "It helps me stay productive"

Cross-turn relationship: "sustained energy" → "stay productive"
```

**Latency added**: 500-1500ms (LLM call with limited context)

**Impact on quality**:
| Metric | Expected Change |
|--------|-----------------|
| Edge/node ratio | +20-40% (cross-turn links captured) |
| Orphan nodes | -20-30% (previous concepts connected) |
| Node count | Neutral |

**Risks**:
- May create spurious connections
- Requires careful prompt design to avoid over-linking

---

### Extension 5: Node Type Refinement Stage

**Insert between**: Stage 3 (Extraction) → Stage 4 (GraphUpdate)

```
Stage 3:   ExtractionStage
Stage 3.7: NodeTypeRefinementStage  ← NEW
Stage 4:   GraphUpdateStage
```

**Purpose**:
- Review extracted node types against existing graph's type distribution
- Apply stricter differentiation rules (especially psychosocial vs instrumental)
- Optionally reclassify ambiguous nodes

**What it does**:
```
Extracted: "being responsible" (psychosocial_consequence)
Rule check: Contains "being [adjective]" → likely instrumental_value
Refinement: Reclassify to instrumental_value
```

**Latency added**:
- Rule-based: <50ms
- LLM-based: 500-1000ms

**Impact on quality**:
| Metric | Expected Change |
|--------|-----------------|
| Edge/node ratio | +10-20% (correct types enable valid edges) |
| Type accuracy | +20-40% (targeted refinement) |
| Schema rejections | -30-50% (fewer invalid connections) |

**Risks**:
- Over-correction may lose nuance
- Rules may not generalize across methodologies

---

## Combined Pipeline Options

### Option A: Minimal Extension (Low Latency)

```
Stage 2:   UtteranceSavingStage
Stage 2.5: SRLPreprocessingStage        ← +100ms
Stage 3:   ExtractionStage (with SRL)
Stage 3.5: SemanticDeduplicationStage   ← +150ms (embeddings)
Stage 4:   GraphUpdateStage
```

**Total added latency**: ~250ms
**Expected edge/node improvement**: 1.5-2x current

### Option B: Balanced Extension (Medium Latency)

```
Stage 2:   UtteranceSavingStage
Stage 2.5: SRLPreprocessingStage        ← +100ms
Stage 3:   ExtractionStage (with SRL)
Stage 3.5: SemanticDeduplicationStage   ← +150ms (embeddings)
Stage 3.6: CrossTurnRelationshipStage   ← +1000ms (LLM)
Stage 4:   GraphUpdateStage
```

**Total added latency**: ~1.25s
**Expected edge/node improvement**: 2-2.5x current

### Option C: Maximum Quality (High Latency)

```
Stage 2:   UtteranceSavingStage
Stage 2.5: SRLPreprocessingStage        ← +100ms
Stage 3a:  ConceptExtractionStage       ← existing ~2s
Stage 3b:  RelationshipExtractionStage  ← +2s (LLM)
Stage 3.5: SemanticDeduplicationStage   ← +800ms (LLM-based)
Stage 3.6: CrossTurnRelationshipStage   ← +1000ms (LLM)
Stage 3.7: NodeTypeRefinementStage      ← +500ms (LLM)
Stage 4:   GraphUpdateStage
```

**Total added latency**: ~4.4s (doubles current turn time)
**Expected edge/node improvement**: 2.5-3x current (reaches target)

---

## Summary Table

| Extension | Latency | Edge/Node Impact | Main Benefit |
|-----------|---------|------------------|--------------|
| 1. SRL Preprocessing | +100ms | +30-50% | Makes relationships explicit |
| 2. Semantic Dedup | +150-800ms | +50-100% | Eliminates duplicate nodes |
| 3. Two-Pass Extraction | +2-3s | +50-100% | Focused relationship extraction |
| 4. Cross-Turn Relations | +1s | +20-40% | Connects Q→A across turns |
| 5. Node Type Refinement | +50-500ms | +10-20% | Reduces schema rejections |

---

## Recommended Starting Point

**Option A (Minimal)** provides best value-for-latency:
1. SRL Preprocessing - low latency, structural scaffolding
2. Semantic Deduplication (embeddings) - addresses primary issue (duplicates)

Test this combination first. If edge/node ratio still below 1.5, add Cross-Turn Relationships (Option B).

---

## Next Steps

1. Prototype SRL preprocessing with spaCy/Stanza on sample utterances
2. Implement embedding-based semantic deduplication
3. Measure impact on synthetic interviews
4. Iterate based on results
