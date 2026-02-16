# Canonical Slot Extraction Guide

**Purpose**: Comprehensive guide to understanding and fine-tuning the canonical slot discovery system (dual-graph architecture).

**Related Beads**: vub0 (Phase 2: Dual-Graph Architecture), gjb5 (threshold tuning), z7gh (threshold testing), 00cw (lemmatization)

---

## Table of Contents

1. [What is Canonical Slot Discovery?](#what-is-canonical-slot-discovery)
2. [How It Works: The Pipeline](#how-it-works-the-pipeline)
3. [Configuration Parameters](#configuration-parameters)
4. [Similarity Threshold Tuning](#similarity-threshold-tuning)
5. [Slot Promotion Mechanics](#slot-promotion-mechanics)
6. [Tools and Scripts](#tools-and-scripts)
7. [Practical Examples](#practical-examples)
8. [Troubleshooting](#troubleshooting)
9. [References](#references)

---

## What is Canonical Slot Discovery?

Canonical slot discovery is a **deduplication system** that maps user's actual language (surface nodes) to abstract, reusable categories (canonical slots).

### Dual-Layer Deduplication Architecture

The system performs deduplication at **two layers**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DUAL-LAYER DEDUPLICATION                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LAYER 1: SURFACE SEMANTIC DEDUP (GraphService)                    │
│  ───────────────────────────────────────────────                   │
│  • Threshold: 0.80 (higher = more conservative)                    │
│  • Purpose: Merge similar verbatim concepts within session         │
│  • Scope: Session-local only                                       │
│  • Requirement: Same node_type required                            │
│  • Pattern: Exact match → Semantic match → Create new             │
│                                                                     │
│  LAYER 2: CANONICAL SLOT DEDUP (CanonicalSlotService)              │
│  ─────────────────────────────────────────────────                 │
│  • Threshold: 0.83 default (configurable)                          │
│  • Purpose: Map surface nodes to abstract, reusable categories     │
│  • Scope: Cross-session (canonical slots are reusable)             │
│  • Pattern: LLM propose → Exact match → Similarity match → Create │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why Two Layers?**
- **Surface layer**: Prevents immediate fragmentation within a session (e.g., "avoid sugar" and "reducing sugar" merged at extraction time)
- **Canonical layer**: Enables cross-session aggregation and analysis (e.g., all sugar-related concepts map to `reduce_sugar` slot)

### The Problem It Solves

Users express the same concept in different ways:

```
User says:                Canonical Slot:
─────────────────────────────────────────────────────
"reducing inflammation"   → reduce_inflammation
"avoid inflammation"      → reduce_inflammation
"less inflammatory"       → reduce_inflammation
```

Without canonical slots, each variation would create a separate node, fragmenting the knowledge graph and making analysis difficult.

### Dual-Graph Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DUAL-GRAPH ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SURFACE GRAPH (User's Actual Language)                            │
│  ─────────────────────────────────────                             │
│  • Contains: kg_nodes table                                        │
│  • What user actually said                                         │
│  • Raw, unnormalized                                               │
│                                                                     │
│              ↕ (mapped via surface_to_slot_mapping)                │
│                                                                     │
│  CANONICAL GRAPH (Abstract Categories)                             │
│  ────────────────────────────────                                  │
│  • Contains: canonical_slots table                                 │
│  • Normalized, abstract concepts                                   │
│  • Reusable across sessions/interviews                             │
│  • Used for aggregation, reporting                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Surface Semantic Deduplication

Surface semantic deduplication prevents the creation of nearly-identical nodes within a session by applying similarity matching at the moment of node creation.

### How It Works

```python
# Three-step deduplication in graph_service.py:_add_or_get_node()

Step 1: Exact label+type match
  - Check: (label.lower(), node_type) in existing_nodes
  - If match: Add source_utterance to existing node, return it
  - Fast path - no embedding computation needed

Step 2: Semantic similarity match (if no exact match)
  - Compute embedding via EmbeddingService (all-MiniLM-L6-v2)
  - Query: find_similar_nodes(session_id, node_type, embedding, threshold=0.80)
  - Return matches sorted by similarity (descending)
  - If match found: Add source_utterance to existing node, return it

Step 3: Create new node
  - No match found (exact or semantic)
  - Create new KGNode with embedding stored for future dedup
  - Return new node
```

### Configuration

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `surface_similarity_threshold` | 0.80 | 0.0-1.0 | Cosine similarity threshold for surface dedup |

**Higher than canonical (0.80 vs 0.83)**: Preserves concept granularity. We want canonical slots to be more aggressive in merging (broader categories) while surface nodes preserve more nuance (specific respondent language).

### Comparison with Canonical Slots

| Aspect | Surface Dedup | Canonical Slots |
|--------|---------------|-----------------|
| **When** | At node creation time | After extraction, in SlotDiscoveryStage |
| **Scope** | Single session | Cross-session |
| **Threshold** | 0.80 | 0.83 (configurable) |
| **Embedding** | Stored on KGNode.embedding | Stored on CanonicalSlot.embedding |
| **Service** | GraphService | CanonicalSlotService |
| **Purpose** | Prevent session fragmentation | Enable cross-session aggregation |
| **Output** | Fewer surface nodes | Abstract canonical categories |

### Database Schema

```sql
-- Surface layer: kg_nodes table
CREATE TABLE kg_nodes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    label TEXT NOT NULL,
    node_type TEXT NOT NULL,
    embedding BLOB,  -- 384-dim float32, nullable for backward compat
    -- ... other fields
);

-- Canonical layer: canonical_slots table
CREATE TABLE canonical_slots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    description TEXT,
    embedding BLOB NOT NULL,  -- Required for canonical slots
    status TEXT DEFAULT 'candidate',  -- 'candidate' or 'active'
    support_count INTEGER DEFAULT 1,
    -- ... other fields
);
```

---

## How It Works: The Pipeline

### Stage 1: Extraction

User responds → LLM extracts concepts as surface nodes:

```python
# Example surface nodes extracted from user response
[
  KGNode(id="n1", label="reducing inflammation", node_type="attribute"),
  KGNode(id="n2", label="sustainability matters", node_type="value"),
  KGNode(id="n3", label="higher cost", node_type="barrier")
]
```

### Stage 2: LLM Proposes Canonical Slots

The `CanonicalSlotService` groups surface nodes by type and asks the LLM to propose abstract canonical slots:

```python
# LLM prompt (simplified)
"""
Group these surface nodes into SPECIFIC, GRANULAR canonical slots:
- reducing inflammation
- avoiding inflammation
- less inflammatory

Existing slots: [none]

Respond with JSON grouping these nodes into canonical categories.
"""

# LLM response
{
  "proposed_slots": [
    {
      "slot_name": "reduce_inflammation",
      "description": "Minimizing inflammatory response in the body",
      "surface_node_ids": ["n1", "n2", "n3"]
    }
  ]
}
```

### Stage 3: Find or Create Slot

For each proposed slot, the system:

1. **Checks for exact match** (after lemmatization):
   - `reduce_inflammation` matches existing slot? → Use it

2. **No exact match? Search by similarity**:
   - Compute embedding for `"reduce_inflammation :: Minimizing inflammatory response"`
   - Find similar existing slots via cosine similarity
   - If `similarity >= canonical_similarity_threshold` → Merge into existing slot
   - Otherwise → Create new candidate slot

### Stage 4: Check Promotion

After mapping surface nodes, check if slot should be promoted:

```python
if slot.status == "candidate" and slot.support_count >= canonical_min_support_nodes:
    promote_slot(slot.id, turn_number)
```

---

## Configuration Parameters

All parameters are in `src/core/config.py` and can be set via environment variables.

### 1. `canonical_similarity_threshold`

**Environment Variable**: `CANONICAL_SIMILARITY_THRESHOLD`

**Default**: `0.83`

**Range**: `0.0` - `1.0`

**Description**: Cosine similarity threshold for merging canonical slots. When a new slot is proposed, it's compared against existing slots via embedding similarity. If similarity >= this threshold, the new slot merges into the existing one.

**How it works**:
- Higher values (0.9+) = More conservative, fewer merges, more distinct slots
- Lower values (0.8-0.85) = More permissive, more merging, fewer slots

**Example**:
```
Proposed: "reduce_inflammation" (similarity 0.89 to existing "anti_inflammatory")

At threshold 0.88: 0.89 >= 0.88 → MERGE (use existing slot)
At threshold 0.90: 0.89 < 0.90 → CREATE NEW (separate slot)
```

---

### 2. `canonical_min_support_nodes`

**Environment Variable**: `CANONICAL_MIN_SUPPORT_NODES`

**Default**: `1`

**Range**: `1` - `∞`

**Description**: Minimum number of surface nodes that must map to a candidate slot before it can be promoted to "active" status. Each time a surface node maps to this slot, `supportCount += 1`. When `supportCount >= this threshold`, the slot is promoted.

**Think of it as "proof of recurrence"** — a slot must be mentioned multiple times before we trust it.

---

#### How Slots Get Reused: Two Paths

There are **two different mechanisms** by which surface nodes map to existing canonical slots. Understanding both is key to understanding how `min_support_nodes` affects behavior.

**Path 1: LLM-Level Reuse (Direct Name Reuse)**

When the LLM proposes new canonical slots, it's given **only "active" slots** as context:

```python
# From canonical_slot_service.py line 125
active_slots = await self.slot_repo.get_active_slots(session_id, node_type)
existing_slot_names = [s.slot_name for s in active_slots]
```

The LLM can directly reuse an existing slot name if it sees it in context:

```
Turn 1: "avoid sugar"
  → LLM proposes "reduce_sugar"
  → Slot created as candidate (supportCount = 1)

Turn 5: "low sugar"
  → LLM sees "reduce_sugar" in context (IF it's active)
  → LLM proposes "reduce_sugar" (exact name reuse)
  → Exact match found → maps to existing slot (supportCount = 2)
```

**Path 2: System-Level Dedup (Similarity Matching)**

Even if the LLM doesn't see an existing slot, the system performs similarity search against **both active AND candidate slots**:

```python
# From canonical_slot_service.py lines 364-369
active_matches = await self.slot_repo.find_similar_slots(
    session_id, node_type, embedding, status="active"
)
candidate_matches = await self.slot_repo.find_similar_slots(
    session_id, node_type, embedding, status="candidate"  # ← Candidates too!
)
```

```
Turn 1: "avoid sugar"
  → LLM proposes "reduce_sugar"
  → Slot created as candidate (supportCount = 1)
  → Embedding stored

Turn 5: "low sugar"
  → LLM proposes "low_sugar_content" (different name!)
  → System checks similarity against ALL existing slots
  → Finds "reduce_sugar" with similarity 0.89
  → If >= threshold: Maps to existing slot
  → If < threshold: Creates NEW candidate slot
```

---

#### The Nuance vs. Clutter Trade-Off

The `min_support_nodes` parameter creates a fundamental trade-off:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MIN_SUPPORT TRADE-OFF                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LOWER (1-2)               │  HIGHER (3-4)                         │
│  ─────────────────────────  │  ───────────────────────────────     │
│  • LLM sees all slots       │  • LLM sees fewer slots              │
│  • Forced to reuse names    │  • More freedom for new names        │
│  • Cleaner canonical space  │  • More granular, nuanced slots     │
│  • May lose nuance          │  • More cluttered, potential dupes  │
│                                                                     │
│  Example:                    │  Example:                            │
│    "avoid sugar"             │    "avoid sugar"                     │
│    + "low sugar"             │    + "low sugar"                     │
│    + "reduce sugar"          │    + "reduce sugar"                  │
│    → All map to single slot  │    → May become 3 separate slots:   │
│      "reduce_sugar"          │      - "avoid_sugar_intent"          │
│    → Clean but loses         │      - "low_sugar_preference"        │
│      distinction             │      - "reduce_sugar_action"         │
│                              │    → Nuanced but cluttered           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Higher min_support = permission to be specific.** The LLM isn't constrained by existing one-off concepts, so it can propose more granular distinctions.

**Lower min_support = early consolidation.** The LLM is constantly reminded of what's already been said, encouraging it to fit new inputs into existing frames.

---

#### How it Works: Step by Step

```
Turn 1: "reducing inflammation"
  → LLM proposes "reduce_inflammation"
  → Slot created as candidate (supportCount = 1)
  → At min_support=1: Promoted to active immediately
  → At min_support=2: Stays candidate (needs 1 more)

Turn 3: "avoid inflammation"
  → LLM proposes slot (sees "reduce_inflammation" IF active)
  → If min_support=1: LLM sees active slot → Reuses exact name
  → If min_support=2: LLM doesn't see candidate → Proposes new name
  → Similarity search checks both active AND candidate slots
  → If similarity >= threshold: Maps to existing slot
  → If similarity < threshold: Creates new candidate slot

Turn 5: "less inflammatory"
  → Process repeats...
  → supportCount increases with each mapping
  → When supportCount >= threshold: Promoted to active
```

---

#### Interview Length Considerations

| Interview Length | Recommended Threshold | Rationale |
|------------------|----------------------|-----------|
| Short (5-10 turns) | 1-2 | Lower threshold needed; concepts have fewer opportunities to recur |
| Medium (10-20 turns) | 2-3 | Balance between discovery and quality |
| Long (20+ turns) | 3-4 | Higher threshold filters out more noise |

---

#### Test Results: min_support Comparison

| Test | Settings | Total Slots | Active | Candidate | Key Finding |
|------|----------|-------------|--------|------------|-------------|
| Test 1 | support=1, threshold=0.8 | 68 | 68 (100%) | 0 | All slots active immediately |
| Test 2 | support=2, threshold=0.83 | 40 | 5 (12.5%) | 35 (87.5%) | Strict filtering in action |

**Key Insight**: With `min_support=2`, only 5 of 40 slots became active—the remaining 35 stayed as candidates because they weren't mentioned enough times. This demonstrates the quality filtering effect.

---

#### During Interview vs. After Interview

**Important distinction**: Setting `min_support` before the interview vs. filtering by `support_count` afterwards have different effects.

| Timing | Setting min_support | Filtering by support_count |
|--------|--------------------|---------------------------|
| **When** | Before interview starts | After interview completes |
| **Affects** | LLM context (which slots shown as reusable) | Reporting only (cosmetic) |
| **Impact on duplicates** | Yes (lower = fewer duplicates) | No (data already created) |
| **How to set** | `CANONICAL_MIN_SUPPORT_NODES=2` | SQL query: `WHERE support_count >= 2` |

**Recommendation**: If you want cleaner canonical graphs with fewer duplicates, set `min_support=2` **before** the interview. Filtering afterwards only affects reporting, not the underlying data (duplicates may already exist).

---

#### Post-Interview Filtering

You can query by `support_count` regardless of promotion status:

```sql
-- Get all slots mentioned 2+ times (even if still "candidate")
SELECT slot_name, status, support_count
FROM canonical_slots
WHERE session_id = ? AND support_count >= 2
ORDER BY support_count DESC;
```

This is useful for reporting, but doesn't change the fact that duplicates may have been created during the interview.

---

### 3. `canonical_min_turns`

**Environment Variable**: `CANONICAL_MIN_TURNS`

**Default**: `2`

**Range**: `1` - `∞`

**Status**: ⚠️ **NOT YET IMPLEMENTED**

**Intended Behavior**: Minimum number of distinct turns in which a slot should have support before promotion. This would prevent slots from earning promotion via multiple mentions in a single long response.

**Current State**: Parameter exists in config but is not used in promotion logic. Currently, promotion only checks `supportCount` regardless of turn distribution.

---

### Parameter Selection Guide

**Quick Reference**:

| Goal | similarity_threshold | min_support_nodes | Rationale |
|------|---------------------|-------------------|-----------|
| **Production default** | 0.83 | 1 | Balanced defaults, maximum discovery |
| **Maximum discovery** | 0.80 | 1 | Most permissive, catch all variations |
| **Clean analysis** | 0.85-0.88 | 2-3 | Minimal duplicates, clear aggregation |
| **Rich nuance** | 0.80-0.83 | 1 | Preserve all distinctions |
| **Short interviews (5-10 turns)** | 0.83 | 1 | Lower support needed |
| **Long interviews (20+ turns)** | 0.83-0.88 | 2-3 | Higher support filters noise |

**By Interview Type**:

| Interview Type | Recommended Settings |
|----------------|---------------------|
| Exploratory research | `threshold=0.83`, `support=1` (default) |
| Validation study | `threshold=0.85`, `support=2` |
| Production interview | `threshold=0.83`, `support=1` (default) |
| Quick poll (5 turns) | `threshold=0.83`, `support=1` (default) |
| Deep dive (20+ turns) | `threshold=0.83`, `support=2` |

**Note**: The new defaults (`threshold=0.83`, `support=1`) prioritize discovery over filtering. For cleaner graphs with fewer duplicates, increase `min_support_nodes` to 2-3.

---

## Similarity Threshold Tuning

### Background

After switching from spaCy word vectors to sentence-transformers (commit 9f402c7), the similarity scoring behavior changed. Threshold testing from previous experiments was invalidated, requiring re-analysis.

### The Analysis Script

**Location**: `scripts/analyze_similarity_distribution.py`

**Purpose**: Analyzes how the sentence-transformers embedding model distributes similarity scores when matching surface concepts to canonical slots.

**Usage**:
```bash
uv run python scripts/analyze_similarity_distribution.py <session_id>
```

**Output**:
1. Total mappings count
2. Histogram of similarity scores in buckets:
   - 0.8-0.85 ← Includes 0.8 test level
   - 0.85-0.88 ← Includes 0.83
   - And other ranges
3. Statistics for non-exact matches (min, max, mean, median, stddev)
4. Recommendation on whether threshold tuning is needed

### Test Results: Threshold Comparison

| Threshold | Mappings | Exact (1.0) | Similarity-Based | Sample Non-Exact Scores |
|-----------|----------|-------------|------------------|------------------------|
| **0.8** (Permissive) | 67 | 65 (97%) | 2 (3%) | 0.8397, 0.8504 (mean 0.845) |
| **0.83** (Balanced) | 65 | 63 (97%) | 2 (3%) | 0.8832, 0.9203 (mean 0.902) |
| **0.88** (Conservative) | 61 | 61 (100%) | 0 (0%) | All exact |

**Key Findings**:
- Lower thresholds (0.8) catch lower-similarity matches (0.84-0.85 range)
- Higher thresholds (0.83) reject low-similarity matches (0.8397 rejected → new slot created)
- Old default 0.88 was very conservative—no similarity-based matches occurred (all exact)
- **Threshold changes only affect ~3% of mappings**—minimal impact
- Most matches are exact (LLM reuses names or creates new slots)

**Recommendation**: New default **0.83** balances precision with recall. Use 0.88 for maximum conservatism.

---

## Slot Promotion Mechanics

### Slot Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CANONICAL SLOT LIFECYCLE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  "candidate" STATUS                                                 │
│  ─────────────────                                                 │
│  • Created when first proposed by LLM                              │
│  • Maps surface nodes, but not yet trusted                         │
│  • Participates in similarity matching (just like active slots)     │
│  • Must EARN promotion through:                                    │
│      1. canonical_min_support_nodes (1) ← "How many mentions?"     │
│      2. canonical_min_turns (2) ← "Across how many turns?" [TODO]   │
│                                                                     │
│                           ↓                                         │
│                 [PROMOTION CHECK]                                  │
│                 if supportCount ≥ 1                                │
│                           ↓                                         │
│  "active" STATUS                                                   │
│  ────────────────                                                  │
│  • Trusted canonical slot                                          │
│  • Used for aggregation, analysis                                  │
│  • Returned to LLM as context for future proposals                 │
│  • Still participates in similarity matching                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Two Paths for Slot Reuse

When a user mentions something related to an existing concept, the system has two ways to map it to the right slot:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TWO SLOT REUSE PATHS                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PATH 1: LLM-LEVEL REUSE                                           │
│  ───────────────────────                                           │
│  1. LLM proposes new slot → Sees "active" slots in context         │
│  2. Recognizes existing concept → Proposes exact same name         │
│  3. System finds exact match → Maps to existing slot               │
│                                                                     │
│  Example:                                                            │
│    Turn 1: "avoid sugar" → "reduce_sugar" (active)                │
│    Turn 5: "low sugar" → LLM sees "reduce_sugar" → Reuses name     │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  PATH 2: SYSTEM-LEVEL SIMILARITY MATCHING                          │
│  ────────────────────────────────────────────                       │
│  1. LLM proposes new slot → Proposes different name                │
│  2. System computes embedding → Searches ALL slots (active+cand)  │
│  3. Finds similar slot → If similarity >= threshold, maps to it    │
│                                                                     │
│  Example:                                                            │
│    Turn 1: "avoid sugar" → "reduce_sugar" (candidate)              │
│    Turn 5: "low sugar" → LLM proposes "low_sugar_content"          │
│    → Similarity search finds "reduce_sugar" (0.89 similarity)      │
│    → If threshold <= 0.89: Maps to existing slot                   │
│    → If threshold > 0.89: Creates new candidate slot              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Insight: Why Status Matters

The "active" vs. "candidate" distinction affects **LLM-level reuse** (Path 1), not similarity matching (Path 2):

- **Active slots**: Shown to LLM as context → Can be directly reused
- **Candidate slots**: NOT shown to LLM → Must rely on similarity matching
- **Both statuses**: Participate in similarity matching

This is why `min_support_nodes` affects duplicate risk:
- **Low values (1-2)**: Slots become active quickly → LLM sees them → Reuses names → Fewer duplicates
- **High values (3+)**: Slots stay candidates longer → LLM doesn't see them → Might propose different names → More potential duplicates

---

## Tools and Scripts

### 1. analyze_similarity_distribution.py

**Purpose**: Analyze similarity score distribution for a completed session.

**Usage**:
```bash
# Basic usage
uv run python scripts/analyze_similarity_distribution.py <session_id>

# Specify custom database path
uv run python scripts/analyze_similarity_distribution.py <session_id> --db /path/to/db
```

**When to use**:
- After switching embedding models
- After changing threshold to assess impact
- When investigating why slots are/aren't merging

### 2. run_simulation.py

**Purpose**: Run a synthetic interview simulation for testing.

**Usage**:
```bash
# Basic usage
uv run python scripts/run_simulation.py <concept_id> <persona_id> [max_turns]

# With custom threshold
CANONICAL_SIMILARITY_THRESHOLD=0.8 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15

# With custom support threshold
CANONICAL_MIN_SUPPORT_NODES=2 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 10
```

**Available concepts**:
- `oat_milk_v2` (means_end_chain methodology)
- `coffee_jtbd_v2` (jobs_to_be_done methodology)

**Available personas**:
- `health_conscious`: Health-Conscious Millennial
- `quality_focused`: Quality Enthusiast
- `convenience_seeker`: Busy Professional
- `sustainability_minded`: Environmentally Conscious Consumer
- `price_sensitive`: Budget-Conscious Shopper

---

## Practical Examples

### Example 1: Testing a Lower Threshold

**Scenario**: You want to test if a lower threshold (0.8) increases slot merging without creating false merges.

```bash
# Run simulation at threshold 0.8
CANONICAL_SIMILARITY_THRESHOLD=0.8 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15

# Note the session_id from output, then analyze
uv run python scripts/analyze_similarity_distribution.py <session_id>
```

**What to look for**:
- Non-exact match percentage: If >10%, threshold is having significant effect
- Histogram distribution: Are scores clustering near your threshold?
- Sample non-exact matches: Are these valid merges or false positives?

### Example 2: Short Interview Optimization

**Scenario**: Running 10-turn interviews, want to ensure concepts get promoted.

```bash
# Lower support threshold for short interviews
CANONICAL_MIN_SUPPORT_NODES=2 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 10
```

**Rationale**: In a 10-turn interview, a concept mentioned 2 times represents 20% of the content—worthy of promotion.

### Example 3: Comparing Thresholds Side-by-Side

**Scenario**: Want to see the difference between thresholds 0.8, 0.83, and 0.88.

```bash
# Run at 0.8
CANONICAL_SIMILARITY_THRESHOLD=0.8 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15 2>&1 | tee run_0.8.log

# Run at 0.83
CANONICAL_SIMILARITY_THRESHOLD=0.83 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15 2>&1 | tee run_0.83.log

# Run at 0.88
CANONICAL_SIMILARITY_THRESHOLD=0.88 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15 2>&1 | tee run_0.88.log
```

Then analyze each session and compare:
- Total canonical slots created
- Percentage of exact vs. similarity-based matches
- Slot names: Are there near-duplicates that should have merged?

### Example 4: Testing min_support_nodes Impact

**Scenario**: Compare how different `min_support_nodes` values affect slot promotion and canonical graph structure.

```bash
# Test 1: Permissive (support=1, threshold=0.8)
CANONICAL_MIN_SUPPORT_NODES=1 CANONICAL_SIMILARITY_THRESHOLD=0.8 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15

# Test 2: Balanced (support=2, threshold=0.83)
CANONICAL_MIN_SUPPORT_NODES=2 CANONICAL_SIMILARITY_THRESHOLD=0.83 uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15
```

**Results Comparison**:

| Metric | Test 1 (support=1) | Test 2 (support=2) |
|--------|-------------------|-------------------|
| Total Mappings | 74 | 46 |
| Total Canonical Slots | 68 | 40 |
| Active Slots | 68 (100%) | 5 (12.5%) |
| Candidate Slots | 0 (0%) | 35 (87.5%) |
| Similarity Matches | 1 (1.4%) | 1 (2.2%) |

**Interpretation**:
- Test 1: All slots promoted immediately—no quality filtering
- Test 2: Only 5 of 40 slots became active—35 stayed as candidates
- The `min_support_nodes` parameter dramatically affects what becomes "active"

**Query to verify**:
```bash
# Check slot status distribution
uv run python -c "
import asyncio, aiosqlite
async def check():
    async with aiosqlite.connect('data/interview.db') as db:
        db.row_factory = aiosqlite.Row
        query = '''
        SELECT status, COUNT(*) as count
        FROM canonical_slots
        WHERE session_id = ?
        GROUP BY status
        '''
        async with db.execute(query, ('<session_id>',)) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                print(f'{row[\"status\"]}: {row[\"count\"]} slots')
asyncio.run(check())
"
```

### Example 5: Production Monitoring

**Scenario**: Monitor how similarity scores are distributed in production.

```bash
# List sessions with mappings
uv run python -c "
import asyncio, aiosqlite
async def list_sessions():
    async with aiosqlite.connect('data/interview.db') as db:
        db.row_factory = aiosqlite.Row
        query = '''
        SELECT DISTINCT n.session_id, COUNT(*) as mapping_count
        FROM surface_to_slot_mapping m
        JOIN kg_nodes n ON m.surface_node_id = n.id
        GROUP BY n.session_id
        ORDER BY mapping_count DESC
        LIMIT 10
        '''
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                print(f\"{row['session_id']} | mappings={row['mapping_count']}\")
asyncio.run(list_sessions())
"

# Analyze recent sessions
uv run python scripts/analyze_similarity_distribution.py <session_id>
```

---

## Troubleshooting

### Problem: All similarity scores are 1.0

**Cause**: LLM is reusing exact canonical slot names, so no similarity-based matching occurs.

**Solutions**:
1. This is normal behavior—LLM learns to reuse names
2. To force similarity matching, use a persona with more varied vocabulary
3. Run longer interviews to increase chance of variations

### Problem: No canonical slots being created

**Cause**: `enable_canonical_slots` feature flag may be disabled.

**Check**:
```python
# In src/core/config.py
enable_canonical_slots: bool = True  # Must be True
```

### Problem: Too many candidate slots, none promoted

**Cause**: `canonical_min_support_nodes` may be too high for interview length.

**Solution**: Lower the threshold:
```bash
CANONICAL_MIN_SUPPORT_NODES=2 uv run python scripts/run_simulation.py ...
```

---

## References

- **Implementation**: `src/services/canonical_slot_service.py`
- **Configuration**: `src/core/config.py`
- **Repository**: `src/persistence/repositories/canonical_slot_repo.py`
- **Domain Models**: `src/domain/models/canonical_graph.py`
- **Related Beads**: vub0 (Phase 2), gjb5 (threshold tuning), z7gh (threshold testing), 00cw (lemmatization)
