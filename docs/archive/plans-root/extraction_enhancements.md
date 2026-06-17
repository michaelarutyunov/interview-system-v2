# Extraction Enhancement Integration Analysis

> **Date**: 2026-02-05
> **Status**: Deep evaluation complete - Requires decisions on ambiguities
> **Scope**: SRL Preprocessing + Semantic Deduplication (Canonical Slots)

---

## Executive Summary

Two Colab-tested enhancements are candidates for pipeline integration:

1. **SRL Preprocessing** (`docs/srl/`) - Discourse + predicate-argument structures injected into extraction prompt
2. **Streaming Canonical Slot Discovery** (`docs/dedup2/`) - LLM-assisted concept abstraction with embedding-based slot merging

After deep analysis of both implementations against the current 10-stage pipeline, the key finding is:

**These two enhancements solve different problems and have vastly different integration costs.**

- SRL is a **prompt enhancement** - low risk, incremental, reversible
- Canonical Slots are an **architectural transformation** - high risk, introduces a two-layer graph model, touches 6+ files, changes what the knowledge graph fundamentally represents

The analysis below provides honest assessment of robustness, weaknesses, integration paths, and ambiguities that must be resolved before implementation.

---

## Part 1: SRL Preprocessing

### What It Does

Uses spaCy's dependency parser to extract:
1. **Discourse relations** via MARK/ADVCL dependencies (subordinating conjunctions: "because", "since", "so")
2. **SRL frames** via dependency tree walking (predicate-argument structures: who does what to whom)

These are injected as structural hints into the extraction LLM prompt alongside the original (unmodified) text.

### Integration Point

**File**: `src/services/turn_pipeline/stages/extraction_stage.py` (lines 111-145)

The change targets `_format_context_for_extraction()`, which currently builds context from recent utterances. SRL analysis would be added as an additional section in the context string.

```
Current flow:
  ExtractionStage.process()
    → _format_context_for_extraction(context) → context string
    → extraction_service.extract(text, context=context_string)

Enhanced flow:
  ExtractionStage.process()
    → _run_srl_analysis(context.user_input) → structural_hints  [NEW]
    → _format_context_for_extraction(context, structural_hints) → context string
    → extraction_service.extract(text, context=context_string)
```

Alternative: Create a new `SRLPreprocessingStage` between Stage 2 and Stage 3. This is cleaner architecturally but adds pipeline complexity for what is essentially a prompt enhancement.

**Recommendation**: Keep it inside ExtractionStage as a private method. It's a preprocessing step for extraction, not a separate pipeline concern.

### Strengths

| Strength | Evidence |
|----------|----------|
| Lightweight dependency | Only spaCy + en_core_web_sm (~45MB total) |
| Fast | ~100-150ms per utterance (tested) |
| Language-agnostic | Uses Universal Dependencies, not hardcoded markers |
| No text corruption | Original text preserved, analysis is supplementary |
| Addresses root cause | Extraction LLM lacks structural hints for WHERE relationships exist |
| Reversible | Can be toggled off without side effects |

### Weaknesses and Robustness Concerns

#### 1. Unproven Integration Benefit

The SRL analysis has only been tested standalone in Colab. There is **no evidence** that adding structural hints to the extraction prompt actually improves edge/node ratio. The LLM may already detect the same causal links, or may ignore the hints entirely.

**Mitigation**: Must run A/B test with synthetic interviews before committing.

#### 2. High Noise Rate (~40%)

From the test data: 91 predicate frames extracted, but ~40% are noise from conversational hedging:
- `mean (agent=I)` - 6 occurrences
- `know (agent=you)` - 8 occurrences
- `think (agent=I)` - 3 occurrences

These generate SRL frames that provide zero extraction value and may confuse the LLM.

**Mitigation**: Filter noise predicates. Maintain a stoplist of conversational verbs: `{"mean", "know", "think", "guess", "say", "tell", "ask", "like"}`. Or filter frames where the only argument is a pronoun.

#### 3. Pronoun Arguments Limit SRL Value

Many SRL frames have pronouns as arguments:
```
helps: ARG0=it  → useless without knowing "it" = "oat milk"
gives: ARG0=it, ARG1=me  → both pronouns
```

The LLM resolves these implicitly, but the structural hint `helps: ARG0=it` adds no information that the LLM doesn't already have from reading the text.

**Mitigation**: Filter frames where ARG0 is a pronoun and no other meaningful arguments exist.

#### 4. Small spaCy Model Accuracy

`en_core_web_sm` is the smallest English model. Its dependency parsing accuracy is lower than `en_core_web_md` or `en_core_web_lg`:
- sm: ~90% UAS (unlabeled attachment score)
- md: ~92% UAS
- lg: ~93% UAS

For discourse relations (MARK/ADVCL), this means ~10% of markers may be missed or misclassified.

**Mitigation**: Use `en_core_web_md` (50MB) for better accuracy. The latency difference is minimal (~20ms).

#### 5. Prompt Length Increase

Adding discourse relations + SRL frames to the extraction prompt increases token count by ~200-400 tokens per turn. With 5 turns of context already included, this pushes toward extraction LLM's useful context window.

**Mitigation**: Limit SRL output to top 5 most informative frames (filter pronouns, hedging first).

### Estimated Impact

| Metric | Current | With SRL | Confidence |
|--------|---------|----------|------------|
| Edge/node ratio | 0.53 | 0.7-1.0 | LOW - unproven |
| Orphan nodes | 26% | 18-22% | MEDIUM |
| Latency per turn | ~2s | ~2.15s | HIGH |
| Memory overhead | baseline | +50MB | HIGH |

The impact confidence is LOW because we have no integration test data yet.

### Files to Modify

| File | Change | Complexity |
|------|--------|------------|
| `pyproject.toml` | Add `spacy` dependency | Trivial |
| `extraction_stage.py` | Add `_run_srl_analysis()` method | Low |
| `extraction_stage.py` | Modify `_format_context_for_extraction()` | Low |
| New: `src/services/srl_service.py` | Extract spaCy logic from Colab script | Medium |

### Open Questions (SRL)

1. **Should SRL run on just the current utterance or also interviewer's question?**
   - Current utterance only: simpler, less noise
   - Both: captures Q→A causal structure better
   - Recommendation: Current utterance + interviewer's last question

2. **What prompt format works best for structural hints?**
   - Tested format from Colab may not be optimal for Claude extraction
   - Need to experiment with different formatting: bullet points vs. natural language vs. JSON

3. **Is spaCy the right tool?**
   - Alternative: Use the LLM itself to identify structural elements (no new dependency)
   - But: adds latency and cost vs. ~100ms for spaCy

---

## Part 2: Semantic Deduplication (Canonical Slot Discovery)

### What It Actually Does

**This is NOT simple deduplication.** The `dedup2.py` implementation is a **Streaming Canonical Slot Discovery System** that:

1. Receives batches of surface nodes (simulating per-turn extraction)
2. Calls an external LLM (KIMI) to propose abstract "canonical slots" (categories like `energy_stability`, `gut_digestion`)
3. Merges proposed slots with existing ones using embedding cosine similarity
4. Promotes slots to "canonical" status after meeting evidence thresholds
5. Maintains a `surface_id → slot_id` mapping

This creates a **two-layer concept architecture**:

```
Layer 1 (Surface): "more energy throughout the day"
                   "sustained energy throughout the day"
                   "affect my energy levels"
                   "difference in energy levels"
                         ↓ maps to
Layer 2 (Canonical): energy_stability
                     "day-to-day energy level stability and variations"
```

### The Fundamental Question

**Does this project need a two-layer concept architecture, or does it need better deduplication?**

These are fundamentally different:

| Aspect | Simple Dedup | Canonical Slots |
|--------|-------------|-----------------|
| Node labels | Respondent's words (longest) | Abstract category names |
| Node types | Preserved | Potentially crossed |
| Graph semantics | Same as current | Different abstraction level |
| Edge handling | Preserved naturally | Requires remapping |
| Architecture change | Minimal (GraphService only) | Major (new service, new stage, new DB table) |
| Latency | +50-100ms | +2-3s (LLM call) |
| Determinism | Deterministic | Non-deterministic (LLM) |
| Reversibility | Easy to revert | Very hard to revert |

### Strengths

| Strength | Evidence |
|----------|----------|
| Streaming design | Processes nodes per-turn, mirrors real interview flow |
| LLM semantic grouping | More nuanced than embedding-only clustering |
| Evidence-based promotion | Slots need support from multiple nodes before becoming canonical |
| Cross-turn convergence | Later turns can merge into earlier slots |
| Surface provenance | Maintains mapping from original to canonical |

### Weaknesses and Robustness Concerns

#### 1. Loss of Respondent's Language (CRITICAL)

The MEC methodology extraction prompt explicitly requires: *"Use the respondent's own language for concept labels"* (line 133, `extraction.py`).

Canonical slots like `energy_stability` or `ingredient_cleanliness` are researcher abstractions, not respondent language. This changes the fundamental nature of the knowledge graph from "what the respondent said" to "what we think the respondent meant."

**Impact**: Strategy selection, question generation, and the graph visualization all currently rely on respondent language. Canonical slot names would make interview questions feel disconnected from what the respondent actually said.

#### 2. node_type Erasure

The KIMI prompt in `dedup2.py` (line 204-253) strips `node_type` from surface nodes:
```python
nodes_text = "\n".join([
    f"- {n['id']}: {n['label']}"  # <-- no node_type!
    for n in surface_nodes
])
```

This means "better digestion" (functional_consequence) and "digestive health approach" (instrumental_value) could be merged into the same slot. In MEC, these represent different levels of the means-end chain. Merging them destroys the ladder structure.

**Impact**: The MEC hierarchy (attribute → functional → psychosocial → instrumental → terminal) is the core analytical framework. Cross-type merging breaks it.

#### 3. Edge Remapping is Unaddressed

The `dedup2.py` implementation has **no edge handling at all**. In the current system, edges reference specific node IDs. When surface nodes merge into canonical slots:

```
Before: node_A ("more energy") --leads_to--> node_B ("feel better")
After:  slot_X ("energy_stability") --leads_to--> slot_Y ("overall_wellbeing")
```

Every existing edge must be remapped. But:
- What if node_A → node_C, and both A and C map to slot_X? Self-loop.
- What if node_A → node_B, and A and B map to the same slot? Edge disappears.
- What about edge provenance (source_utterance_ids)?

This is a non-trivial graph rewriting problem that the prototype doesn't address.

#### 4. Promotion Thresholds are Trivially Easy

```python
MIN_SUPPORT_NODES = 2  # Just 2 surface nodes
MIN_TURNS = 1          # Seen in just 1 turn
```

With ~7 nodes per turn, nearly every proposed slot with 2+ supporting nodes gets promoted immediately. The promotion mechanism provides almost no filtering.

The original prompt specified `MIN_SUPPORT_NODES=3, MIN_TURNS=2`, which is stricter but still not very selective.

#### 5. External LLM Dependency (KIMI)

The prototype uses Moonshot's KIMI API (`moonshot-v1-8k`). In production:
- Would need to use our existing LLM client (Claude) instead
- Adds a second LLM call per turn (in addition to extraction)
- Cost doubles for LLM usage
- Latency increases by 2-3 seconds per turn

#### 6. Slot Name Drift Across Turns

LLM-generated slot names are non-deterministic. Even with existing slot names passed as context (only "active" ones - see `get_existing_slot_names()` filtering at line 359-364), the LLM may:
- Turn 1: propose `ingredient_quality`
- Turn 3: propose `clean_ingredients`
- Turn 7: propose `food_purity`

The embedding merge layer (threshold 0.88) may or may not catch these as the same concept. Three near-duplicate slots could accumulate.

#### 7. Surface-to-Slot Mapping Overwrites Without Conflict Resolution

```python
# Line 403-404:
for surface_id in surface_ids:
    self.surface_to_slot[surface_id] = existing_id
```

If a surface node is reassigned from slot A to slot B in a later turn, the mapping silently overwrites. No conflict detection, no tracking of reassignment history.

#### 8. No Evaluation Metric

How do we know if the canonical slots are "good"? There is:
- No ground truth to compare against
- No inter-rater reliability measure
- No quantitative quality metric
- No regression test to detect slot quality degradation

The assessment is purely qualitative: "do these groupings look right?"

### NodeStateTracker Interaction

The `NodeStateTracker` (used in `graph_update_stage.py` lines 126-206) tracks per-node state:
- `focus_count`, `turns_since_last_yield`, `current_focus_streak`
- Registered by node ID, updated by edge counts

If surface nodes merge into canonical slots, tracking state must be consolidated:
- Which slot inherits the focus_count of its merged surface nodes?
- Sum? Max? Average?
- What happens to exhaustion scores?

This is not addressed in the prototype and would require careful design.

### Strategy Selection Impact

Current signal thresholds are calibrated for ~60-70 node graphs:
- `graph.node_count` signals trigger at various thresholds
- `graph.coverage_breadth` depends on node type distribution
- `graph.max_depth` depends on edge chain lengths

With canonical slots, the graph shrinks to ~15-20 nodes. ALL signal thresholds would need recalibration. This is a cascading change that affects every methodology YAML config.

---

## Part 3: Integration Architecture Options

### Option A: SRL Only (Low Risk, Incremental)

```
Pipeline: unchanged stages 1-10
Change: ExtractionStage adds SRL hints to prompt context
```

**Scope**: 2-3 files modified, ~200 lines of new code
**Latency**: +100-150ms per turn
**Dependencies**: spacy + en_core_web_sm
**Risk**: LOW - reversible, no architectural change

### Option B: SRL + Embedding Dedup at GraphService Level (Medium Risk)

```
Pipeline: unchanged stages 1-10
Change 1: ExtractionStage adds SRL hints to prompt
Change 2: GraphService._add_or_get_node() checks cosine similarity
```

This is **NOT** canonical slots. This is simple embedding-based dedup that:
- Finds existing nodes with cosine similarity > threshold
- Reuses the existing node instead of creating a duplicate
- Preserves respondent language (keeps the existing node's label)
- Respects node_type constraint (only matches same type)
- No LLM call needed

**Scope**: 4-5 files modified, ~300 lines of new code
**Latency**: +200-300ms per turn
**Dependencies**: spacy + sentence-transformers (or spaCy vectors as lighter alternative)
**Risk**: MEDIUM - new ML dependencies, but no architectural change

### Option C: SRL + Full Canonical Slot Discovery (High Risk)

```
Pipeline: stages 1-2, [NEW: SRL], 3, [NEW: SlotDiscovery], 4-10
Change 1: New SRL preprocessing
Change 2: New SlotDiscoveryService as pipeline stage
Change 3: GraphService stores canonical labels
Change 4: Edge creation uses canonical node lookup
Change 5: NodeStateTracker consolidation
Change 6: Signal threshold recalibration
```

**Scope**: 8-12 files modified, 600+ lines of new code, new DB table
**Latency**: +2-3s per turn (LLM call for slot discovery)
**Dependencies**: spacy + sentence-transformers + additional LLM call
**Risk**: HIGH - fundamental architectural change, hard to revert

### Option D: SRL + Embedding Dedup + Offline Canonical Analysis (Pragmatic)

```
Pipeline: stages 1-10 (with Option B changes)
Background: Periodic canonical slot analysis on graph snapshots
```

This combines the benefits:
1. **Immediate**: Embedding dedup in GraphService (no LLM, fast)
2. **Immediate**: SRL hints in extraction prompt
3. **Background**: Canonical slot analysis runs offline after interview completes
4. **Background**: Slot information used for research insights, not for live graph

**Scope**: Option B scope + offline analysis script
**Latency**: +200-300ms per turn (no LLM overhead)
**Risk**: LOW-MEDIUM - keeps canonical slots as analysis tool, not architectural dependency

---

## Part 4: Dependency Impact Assessment

### Current State

The project has **zero ML dependencies**. All intelligence comes from LLM API calls and heuristics.

### With SRL Only

| Dependency | Size | Purpose |
|-----------|------|---------|
| spacy | ~20MB | NLP framework |
| en_core_web_sm | ~25MB | English model |
| **Total** | **~45MB** | |

Startup impact: +2-3s (model load, lazy-loadable)
Memory impact: +30-50MB RAM

### With SRL + Embedding Dedup

| Dependency | Size | Purpose |
|-----------|------|---------|
| spacy | ~20MB | NLP framework |
| en_core_web_md | ~50MB | English model (with vectors) |
| sentence-transformers | ~5MB | Embedding framework |
| torch (CPU) | ~500-800MB | ML runtime |
| all-MiniLM-L6-v2 | ~80MB | Embedding model |
| **Total** | **~650-950MB** | |

Startup impact: +5-8s (two model loads)
Memory impact: +130-200MB RAM

### Lighter Alternative: spaCy Vectors Instead of sentence-transformers

If we use `en_core_web_md` (which includes 300-dim word vectors), we can compute approximate semantic similarity WITHOUT sentence-transformers or torch:

```python
# Using spaCy's built-in vectors
doc1 = nlp("more energy throughout the day")
doc2 = nlp("sustained energy throughout the day")
similarity = doc1.similarity(doc2)  # Uses word2vec-style averaging
```

| Dependency | Size | Purpose |
|-----------|------|---------|
| spacy | ~20MB | NLP framework |
| en_core_web_md | ~50MB | English model with vectors |
| **Total** | **~70MB** | |

**Trade-off**: spaCy's bag-of-vectors similarity is less accurate than sentence-transformers for short phrases. But it avoids the ~800MB torch dependency entirely.

This should be tested: if spaCy vectors can distinguish "more energy" from "better digestion" with sufficient margin, they're good enough for dedup.

---

## Part 5: Specific Integration Design (Option B)

This section details the recommended first step: SRL + Embedding Dedup without canonical slots.

### 5.1 New Service: SRLService

```
Location: src/services/srl_service.py
```

Responsibilities:
- Load and cache spaCy model
- Extract discourse relations from text
- Extract SRL frames from text
- Filter noise predicates
- Format structural hints for prompt injection

Key design decisions:
- Model loaded lazily on first use (avoid startup cost if SRL disabled)
- Noise predicate filter configurable
- Output format matches extraction prompt expectations

### 5.2 Modified: ExtractionStage

```
Location: src/services/turn_pipeline/stages/extraction_stage.py
```

Changes:
- Accept optional `SRLService` in constructor
- Call SRL analysis before extraction
- Inject structural hints into context string
- Feature-flaggable: if SRLService is None, skip (backward compatible)

### 5.3 Modified: GraphService

```
Location: src/services/graph_service.py
```

Changes to `_add_or_get_node()`:

```python
# Current: exact match only
existing = await self.repo.find_node_by_label_and_type(
    session_id, concept.text, concept.node_type
)

# Enhanced: exact match first, then semantic similarity
existing = await self.repo.find_node_by_label_and_type(
    session_id, concept.text, concept.node_type
)
if not existing:
    existing = await self._find_semantically_similar_node(
        session_id, concept.text, concept.node_type, threshold=0.85
    )
```

The `_find_semantically_similar_node()` method:
1. Gets all nodes of same type for session
2. Computes embedding for new label
3. Computes cosine similarity against each existing node
4. Returns best match if above threshold

**Performance concern**: Computing embeddings for all existing nodes every time is O(n). For a session with 60 nodes of which 20 are same type, that's 20 embedding computations per concept.

**Mitigation options**:
- Cache embeddings in memory (dict keyed by node_id)
- Store embeddings in database (new column or separate table)
- Pre-compute embeddings when nodes are created
- Use approximate nearest neighbor for large sessions (FAISS) - overkill for <100 nodes

### 5.4 Modified: SessionService (DI Wiring)

```
Location: src/services/session_service.py
```

Changes:
- Create SRLService instance (or None if disabled)
- Pass to ExtractionStage constructor
- Create EmbeddingService (or similar) for GraphService

### 5.5 New: EmbeddingCache

```
Location: src/services/embedding_cache.py
```

In-memory cache for node embeddings:
- `encode(text) -> np.ndarray` - compute or return cached
- `invalidate(node_id)` - remove on node update
- Scoped per session to prevent cross-session pollution
- TTL-based or size-limited to prevent memory growth

### 5.6 Edge Lookup Enhancement

Currently, edges are created by matching `relationship.source_text` against `label_to_node` (line 189-190 in `graph_service.py`). This exact-match lookup causes edge loss when the LLM uses slightly different labels.

With semantic dedup, the same similarity check should apply to edge endpoint matching:

```python
# Current:
source_node = label_to_node.get(relationship.source_text.lower())

# Enhanced:
source_node = label_to_node.get(relationship.source_text.lower())
if not source_node:
    source_node = self._find_best_label_match(
        relationship.source_text, label_to_node
    )
```

This is a separate improvement but synergistic with dedup.

---

## Part 6: What Canonical Slots Could Look Like (Option C, Future)

If canonical slots are pursued later, here's what the integration would require:

### New Database Table

```sql
CREATE TABLE canonical_slots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'candidate',  -- 'candidate' or 'active'
    embedding BLOB,  -- stored as numpy bytes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    promoted_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE surface_to_slot (
    surface_node_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    similarity_score REAL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (surface_node_id) REFERENCES kg_nodes(id),
    FOREIGN KEY (slot_id) REFERENCES canonical_slots(id),
    PRIMARY KEY (surface_node_id, slot_id)
);
```

### New Pipeline Stage

```
Stage 3.5: SlotDiscoveryStage
  Input: ExtractionOutput (concepts)
  Output: SlotDiscoveryOutput (mapped concepts with canonical labels)

  Dependencies: LLMClient, EmbeddingService, SlotRepository
```

### Modified Stages

| Stage | Change |
|-------|--------|
| Stage 4 (GraphUpdate) | Use canonical label for node creation |
| Stage 5 (StateComputation) | Compute state over canonical nodes |
| Stage 6 (StrategySelection) | All signals recalibrated for canonical graph |
| Stage 8 (QuestionGeneration) | Questions reference canonical or surface labels? |

### The Label Problem

When generating questions, should we use:
- Canonical label: "Tell me more about energy_stability" - unnatural
- Surface label: "Tell me more about sustained energy" - but which surface label?
- Most recent surface label: pragmatic but complex to track

This is a UX problem that canonical slots create and simple dedup doesn't.

---

## Part 7: Ambiguities Requiring Decision

### Decision 1: Which dedup approach?

| Option | For | Against |
|--------|-----|---------|
| **Embedding dedup only** | Simple, fast, no LLM, preserves labels | Less intelligent grouping |
| **Canonical slots** | More nuanced grouping | Loss of respondent language, 2-3s latency, architectural change |
| **Embedding dedup now + canonical later** | Incremental, low risk | Defers hard decisions |

**Recommendation**: Embedding dedup first. Measure impact. Only pursue canonical slots if dedup is insufficient.

### Decision 2: Should dedup respect node_type?

The original dedup experiment enforced same-type-only matching. The dedup2 canonical slots ignore node_type entirely.

- **Same-type only**: Prevents cross-hierarchy merging (MEC-safe). But "being mindful" (instrumental_value) and "being mindful about what I put into my body" (instrumental_value) only merge if same type.
- **Cross-type**: More aggressive reduction but risks destroying MEC structure.

**Recommendation**: Same-type only. The MEC hierarchy is the analytical backbone.

### Decision 3: What embedding model?

| Model | Size | Accuracy | Dependency Weight |
|-------|------|----------|-------------------|
| spaCy en_core_web_md vectors | 50MB | Good for word-level | ~70MB total (light) |
| all-MiniLM-L6-v2 | 80MB | Best for phrases | ~900MB total (heavy, needs torch) |
| spaCy + onnxruntime MiniLM | 80MB | Best for phrases | ~200MB total (medium) |

**Recommendation**: Start with spaCy vectors (en_core_web_md). If similarity quality is insufficient for short phrases, upgrade to sentence-transformers with onnxruntime backend to avoid torch.

### Decision 4: Where to cache embeddings?

- **In-memory only**: Simple, fast, lost on restart. Recomputed per session.
- **In database**: Persistent, but adds column/table. Requires migration.
- **In node properties JSON**: No schema change, but JSON blob queries are slow.

**Recommendation**: In-memory cache first. If sessions are long-running or resume across restarts, add database storage later.

### Decision 5: What happens to existing graph nodes when dedup finds a match?

When a new concept "sustained energy" is extracted and existing node "more energy throughout the day" is found as a semantic match:

- **Option A**: Return existing node, ignore new label (current behavior for exact match)
- **Option B**: Return existing node, update label to new one if it's more specific
- **Option C**: Return existing node, add new label as alias
- **Option D**: Create provenance link (new_label --aliased_by--> existing_node)

**Recommendation**: Option A (return existing, ignore new label). Simplest, matches current exact-match behavior. Alias tracking can be added later if needed.

### Decision 6: Threshold value?

The batch dedup experiment tested thresholds 0.75-0.95:
- 0.75: 8 clusters, 13.2% reduction - too aggressive
- 0.85: 3 clusters, 4.4% reduction - too conservative for batch (but this was with greedy, not connected components)
- 0.95: 2 clusters, 2.9% reduction - barely any merging

For streaming per-node dedup (not batch), the threshold behavior is different: we're comparing ONE new node against ALL existing, not all-vs-all. This means:
- Higher threshold needed (0.88-0.92) to prevent false merges
- Lower threshold (0.82-0.85) catches more paraphrases but risks merging distinct concepts

**Recommendation**: Start at 0.88. Tune based on logged merge decisions.

### Decision 7: How to measure success?

Proposed metrics for evaluation:
1. **Node reduction %**: Target 20-35% (from ~65 to ~42-52 nodes)
2. **False merge rate**: Manual review of merged pairs. Target <5% false positives.
3. **Edge/node ratio improvement**: Target >1.0 (from 0.53)
4. **Orphan node reduction**: Target <15% (from 26%)

**Method**: Run 3 synthetic interviews with current system, then with enhancements. Compare metrics.

---

## Part 8: Recommended Implementation Order

### Phase 1: SRL Preprocessing (1-2 sessions)

1. Create `src/services/srl_service.py` adapting Colab script
2. Add spaCy dependency, model download to setup
3. Modify `ExtractionStage._format_context_for_extraction()`
4. Add feature flag to enable/disable
5. Run synthetic interview, compare extraction quality
6. Measure edge/node ratio change

### Phase 2: Embedding Dedup (1-2 sessions)

1. Decide on embedding model (spaCy vectors vs sentence-transformers)
2. Create `src/services/embedding_service.py` with caching
3. Modify `GraphService._add_or_get_node()` with similarity check
4. Add negation filter (from dedup experiment)
5. Add logging for all merge decisions (critical for tuning)
6. Run synthetic interview, compare node reduction

### Phase 3: Edge Lookup Enhancement (1 session)

1. Modify edge creation to use fuzzy label matching
2. When edge source/target not found in `label_to_node`, try semantic match
3. This reduces edge loss from label mismatch

### Phase 4: Evaluate and Decide (1 session)

1. Run full evaluation with metrics from Decision 7
2. Decide if canonical slots are needed based on results
3. If embedding dedup achieves >25% node reduction with <5% false merges, canonical slots may be unnecessary

### Phase 5: Canonical Slot Discovery (Optional, 3-5 sessions)

Only if Phase 4 shows embedding dedup is insufficient:
1. Design database schema for canonical slots
2. Create SlotDiscoveryService
3. Add as pipeline stage
4. Recalibrate all signal thresholds
5. Handle edge remapping
6. Handle NodeStateTracker consolidation

---

## Part 9: Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SRL hints ignored by extraction LLM | MEDIUM | LOW | A/B test, iterate on prompt format |
| Embedding model too slow | LOW | MEDIUM | Profile, use lighter model |
| False merges in dedup | MEDIUM | HIGH | Conservative threshold, logging, manual review |
| torch dependency too heavy | HIGH | MEDIUM | Use spaCy vectors or onnxruntime |
| Canonical slots break MEC hierarchy | HIGH | HIGH | Don't implement unless embedding dedup insufficient |
| Cold start latency from model loading | MEDIUM | LOW | Lazy loading, warm-up endpoint |
| Signal threshold miscalibration | HIGH (for canonical slots) | HIGH | Full recalibration run needed |

---

## Part 10: Summary

| Enhancement | Status | Risk | Recommendation |
|-------------|--------|------|----------------|
| SRL Preprocessing | Colab-tested, ready to port | LOW | Implement in Phase 1 |
| Embedding Dedup (GraphService) | Colab-tested, proven concept | MEDIUM | Implement in Phase 2 |
| Edge Lookup Enhancement | Not tested, logical extension | LOW | Implement in Phase 3 |
| Canonical Slot Discovery | Colab-tested, unproven in pipeline | HIGH | Defer to Phase 5, only if needed |

The canonical slot system from `dedup2.py` is an interesting research prototype, but integrating it into the live pipeline raises fundamental questions about what the knowledge graph represents. The embedding dedup approach provides 80% of the benefit with 20% of the risk. Start there.
