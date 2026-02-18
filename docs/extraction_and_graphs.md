# Extraction & Dual-Graph Architecture Guide

**Purpose**: Comprehensive guide to the extraction pipeline and dual-graph architecture (Stages 3 → 4 → 4.5 → 5), from user text to dual-graph state.

**Related Beads**: vub0 (Phase 2: Dual-Graph Architecture), gjb5 (threshold tuning), z7gh (threshold testing), 00cw (lemmatization)

---

## Table of Contents

1. [Overview: The Extraction Pipeline](#overview-the-extraction-pipeline)
2. [Stage 3: Concept & Relationship Extraction](#stage-3-concept--relationship-extraction)
3. [Stage 4: Graph Update & Surface Deduplication](#stage-4-graph-update--surface-deduplication)
4. [Stage 4.5: Canonical Slot Discovery](#stage-45-canonical-slot-discovery)
5. [Slot Promotion Mechanics](#slot-promotion-mechanics)
6. [Stage 5: Dual-Graph State Computation](#stage-5-dual-graph-state-computation)
7. [Configuration Reference](#configuration-reference)
8. [Tools and Scripts](#tools-and-scripts)
9. [Practical Examples](#practical-examples)
10. [Troubleshooting](#troubleshooting)
11. [Bug Fixes & Historical Context](#bug-fixes--historical-context)
12. [References](#references)

---

## Overview: The Extraction Pipeline

The extraction pipeline transforms user responses into a dual-layer knowledge graph through four stages:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION PIPELINE FLOW                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STAGE 3: EXTRACTION                                               │
│  ───────────────────────                                           │
│  User text → LLM extraction → Concepts & Relationships             │
│  • Methodology-aware prompts                                       │
│  • Schema validation (node types, edge types)                      │
│  • Cross-turn relationship bridging                                │
│  Output: ExtractionResult with concepts[] and relationships[]      │
│                                                                     │
│                           ↓                                         │
│                                                                     │
│  STAGE 4: GRAPH UPDATE (Surface Layer)                             │
│  ───────────────────────────────────────                           │
│  Concepts → Surface nodes (with semantic dedup)                    │
│  Relationships → Surface edges                                     │
│  • 3-step dedup: exact → semantic (0.80) → create                  │
│  • Cross-turn edge resolution                                      │
│  • NodeStateTracker integration                                    │
│  Output: GraphUpdateOutput with nodes_added[] and edges_added[]   │
│                                                                     │
│                           ↓                                         │
│                                                                     │
│  STAGE 4.5: CANONICAL SLOT DISCOVERY                               │
│  ────────────────────────────────────────                          │
│  Surface nodes → Canonical slots (LLM-proposed)                    │
│  Surface edges → Canonical edges (aggregated)                      │
│  • LLM grouping with similarity dedup (0.60)                       │
│  • Slot promotion via min_support threshold                        │
│  • Abstract, reusable categories                                   │
│  Output: SlotDiscoveryOutput with slots[] and mappings[]           │
│                                                                     │
│                           ↓                                         │
│                                                                     │
│  STAGE 5: STATE COMPUTATION                                        │
│  ───────────────────────────                                       │
│  Compute dual-graph states in parallel:                            │
│  • Surface GraphState (node/edge counts, depth, orphans)           │
│  • Canonical CanonicalGraphState (slot counts, reduction %)        │
│  • Saturation metrics for continuation decisions                   │
│  Output: StateComputationOutput with both graph states             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### What Each Stage Does

**Stage 3 (Extraction)**: LLM analyzes user response to extract concepts (nodes) and relationships (edges) according to methodology schema. Validates against node types and edge types. Enables cross-turn relationships by injecting existing node labels into prompt.

**Stage 4 (Graph Update)**: Adds extracted concepts to surface graph with 3-step semantic deduplication (exact label match → cosine similarity 0.80 → create new). Resolves edges to nodes from previous turns. Updates NodeStateTracker for exhaustion/focus tracking.

**Stage 4.5 (Slot Discovery)**: LLM groups surface nodes into canonical slots (abstract categories). Similarity matching at 0.60 threshold prevents duplicates. Slots earn "active" status when min_support threshold (2) met. Maps surface edges to canonical edges.

**Stage 5 (State Computation)**: Computes surface and canonical graph states in parallel. Surface state provides node/edge counts, depth metrics, orphan detection. Canonical state shows reduction percentage and aggregated structure. Saturation metrics inform continuation decisions.

---

## Stage 3: Concept & Relationship Extraction

**File**: `src/services/turn_pipeline/stages/extraction_stage.py`

**Service**: `src/services/extraction_service.py`

**Prompts**: `src/llm/prompts/extraction.py`

### 2.1 Extractability Pre-Filter

Before calling the LLM, a fast heuristic check filters out non-extractable responses:

```python
# From ExtractionService._fast_extractability_check()

Conditions that skip extraction:
1. Word count < min_word_count (default: 3)
2. Yes/no responses ("yes", "no", "yeah", "nope", "sure", "okay", etc.)
3. Single word responses
```

**Configuration**:
- `min_word_count`: Default 3, configurable at service initialization
- `skip_extractability_check`: Debug flag to bypass filter (testing only)

**Example**:
```
User: "Yes"         → Skipped (yes/no response)
User: "Good"        → Skipped (single word)
User: "Not really"  → Skipped (2 words, below threshold)
User: "I prefer it" → Extracted (3 words, passes threshold)
```

### 2.2 LLM Extraction

**Temperature**: 0.4 (balanced for relationship inference)

**Max tokens**: 4000 (handles long responses with many concepts)

**Context provided to LLM**:
1. **Conversation history** (last 5 turns): Provides conversational context for implicit relationships
2. **SRL hints** (if available): Discourse relations and predicate-argument structures from SRLPreprocessingStage
3. **Existing node labels** (up to 30 recent): Enables cross-turn relationship bridging
4. **Most recent interviewer question**: Highlighted for Q→A relationship creation

```python
# From ExtractionStage._format_context_for_extraction()

Example context:
"""
Respondent: I drink coffee every morning
Interviewer: Why does that morning routine matter?
Respondent: It helps me focus at work

[Most recent question] Interviewer: Why does that morning routine matter?
[Task] Extract concepts from the Respondent's answer AND create a relationship
from the question's topic to the answer concept.

## STRUCTURAL ANALYSIS (use to guide relationship extraction):
Causal/temporal markers detected:
  - [because]: "morning routine" → "helps me focus"

[Existing graph concepts from previous turns]
  - "morning coffee"
  - "daily routine"
  - "workplace productivity"
[Task] When creating relationships, you may reference these exact labels as
source_text or target_text to connect new concepts to existing ones.
"""
```

### 2.3 Methodology-Aware Features

The extraction system is **schema-driven** rather than hardcoded for specific methodologies.

#### Schema-Driven Node Types and Edge Types

```python
# Loaded from methodology YAML (e.g., config/methodologies/jobs_to_be_done.yaml)

Valid node types (JTBD example):
  - job: Functional task the respondent is trying to accomplish
  - pain_point: Obstacle or frustration preventing job completion
  - desired_outcome: What success looks like for the job
  - solution: Product/service that helps achieve the job
  - context: Situational factors affecting job execution

Valid edge types (JTBD example):
  - hinders: pain_point prevents job completion
  - enables: solution facilitates job completion
  - leads_to: job accomplishment results in desired_outcome
  - requires: job depends on context or resource
```

#### Concept Naming Conventions

Loaded from `ontology.concept_naming_convention` in YAML:

```yaml
# config/methodologies/jobs_to_be_done.yaml
ontology:
  concept_naming_convention: >
    Name jobs as infinitive verb phrases (e.g., "prepare breakfast", "track expenses").
    Name pain_points as obstacles (e.g., "inconsistent results", "takes too long").
    Name desired_outcomes as goal states (e.g., "consistent quality", "save time").
```

**Bug fix history**: This field was originally read at top level instead of under `ontology:`, causing naming conventions to always be `None`. Fixed in commit `6bdbef4`.

#### Extraction Guidelines and Relationship Examples

Also loaded from YAML `ontology` section:

```yaml
ontology:
  extraction_guidelines:
    - "Focus on the functional job, not product features"
    - "Capture pain points as obstacles to job completion"
    - "Extract desired outcomes as measurable success criteria"

  relationship_examples:
    job_to_outcome:
      description: "Jobs lead to desired outcomes when successful"
      example: "User says: 'I want my coffee to taste consistent every morning'"
      extraction: "Job: 'make morning coffee' leads_to Outcome: 'consistent taste'"
```

#### Dynamic Primary Edge Type Selection

**Critical fix** for methodology portability (commit `344120c`):

```python
# From get_extraction_system_prompt() in extraction.py

# OLD (hardcoded for Means-End Chain):
primary_edge_type = "leads_to"  # WRONG - doesn't exist in JTBD

# NEW (dynamic selection):
valid_edge_types = schema.get_valid_edge_types()
primary_edge_type = next(
    (et for et in valid_edge_types if et != "revises"),
    valid_edge_types[0] if valid_edge_types else "leads_to",
)
```

**Impact**: Before this fix, JTBD interviews had 99% relationship rejection rate because the LLM was instructed to use "leads_to" edge type which didn't exist in the JTBD schema. After fix: 19x improvement in edge/node ratio.

### 2.4 Cross-Turn Relationship Bridging

**Problem**: Without cross-turn awareness, each turn's extraction is isolated, creating graph fragmentation.

**Solution**: Inject existing node labels into extraction prompt so LLM can reference them in `source_text`/`target_text` fields.

```python
# From ExtractionStage._format_node_labels()

Labels injected:
  - Up to 30 most recent node labels from session
  - Current-turn concepts NOT included (to avoid re-extraction)
  - Exact label match required for edge resolution

Prompt instruction:
"When creating relationships, you may reference these exact labels as source_text
or target_text to connect new concepts to existing ones. Do NOT re-extract these
as new concepts."
```

**Example**:

```
Turn 3: Extract concept "morning routine"
Turn 7: Context includes "morning routine" in existing labels
User: "That routine helps me stay focused at work"

LLM extracts:
  - Concept: "stay focused at work" (NEW)
  - Relationship: "morning routine" → "stay focused at work" (CROSS-TURN EDGE)
    (references existing concept without re-extracting it)
```

**Impact**: Increased edge/node ratio from 0.54 to 1.18 (+118%) by enabling edges between turns.

### 2.5 Schema Validation

After LLM extraction, concepts and relationships are validated against methodology schema:

```python
# From ExtractionService._parse_concepts()

For each concept:
  1. Validate node_type via schema.is_valid_node_type()
  2. If invalid: Log warning, skip concept
  3. If valid: Set is_terminal and level from schema metadata

For each relationship:
  1. Validate edge_type via schema.is_valid_edge_type()
  2. Validate permitted_connections via schema.is_valid_connection(edge_type, source_type, target_type)
  3. If invalid: Log warning, skip relationship
  4. If valid: Create ExtractedRelationship
```

**Validation patterns**:

```python
# Node type validation
schema.is_valid_node_type("job")         # True if "job" in YAML node_types
schema.is_valid_node_type("attribute")   # False if not in schema

# Edge type validation
schema.is_valid_edge_type("hinders")     # True if "hinders" in YAML edge_types

# Connection validation (source_type → target_type permitted?)
schema.is_valid_connection("hinders", "pain_point", "job")  # True if permitted
schema.is_valid_connection("hinders", "job", "pain_point")  # False if not in permitted_connections
```

**Logs to watch**:
- `invalid_node_type`: Concept skipped due to schema mismatch
- `invalid_edge_type`: Relationship skipped due to unknown edge type
- `invalid_connection`: Relationship skipped due to unpermitted node type pairing

### 2.6 JSON Repair

LLMs occasionally generate malformed JSON. Three repair strategies are applied automatically:

```python
# From _repair_json() in extraction.py

Fix 1: Missing commas between properties/elements
  Pattern: "value" "key" or number "key" (missing comma)
  Example: "confidence": 0.9 "source_quote": "..."
  Repair:  "confidence": 0.9, "source_quote": "..."

Fix 2: Trailing commas before closing brackets
  Pattern: [...,] or {...,}
  Example: "concepts": ["job", "pain_point",]
  Repair:  "concepts": ["job", "pain_point"]

Fix 3: Truncated JSON (incomplete closing brackets/braces)
  Pattern: Unbalanced { or [ count
  Example: {"concepts": [{"text": "job"
  Repair:  {"concepts": [{"text": "job"}]}
```

**Log entry**: `extraction_json_repaired` (warning level) indicates repair was needed.

### 2.7 Traceability

Every extracted concept and relationship is linked to its source utterance for provenance tracking:

```python
# Traceability chain: user_input → utterance → concept → node → edge

Stage 2 (UtteranceSaving):
  user_input → Utterance(id=utterance_id, text=user_input)

Stage 3 (Extraction):
  ExtractedConcept(source_utterance_id=utterance_id)
  ExtractedRelationship(source_utterance_id=utterance_id)

Stage 4 (GraphUpdate):
  KGNode(source_utterance_ids=[utterance_id])
  KGEdge(source_utterance_ids=[utterance_id])
```

**Use cases**:
- Auditing: Trace back from node to exact user text
- Multi-source nodes: Deduped nodes accumulate multiple `source_utterance_ids`
- Provenance queries: "Which user statements support this concept?"

---

## Stage 4: Graph Update & Surface Deduplication

**File**: `src/services/turn_pipeline/stages/graph_update_stage.py`

**Service**: `src/services/graph_service.py`

### 3.1 Three-Step Surface Deduplication

Surface deduplication prevents nearly-identical nodes within a session by applying similarity matching at node creation time.

```python
# From GraphService._add_or_get_node()

Step 1: Exact label+type match
  - Check: (label.lower(), node_type) in existing_nodes
  - If match: Add source_utterance to existing node, return it
  - Fast path - no embedding computation needed

Step 2: Semantic similarity match (if no exact match)
  - Compute embedding via EmbeddingService (all-MiniLM-L6-v2, 384-dim)
  - Query: find_similar_nodes(session_id, node_type, embedding, threshold=0.80)
  - Return matches sorted by similarity (descending)
  - If match found: Add source_utterance to existing node, return it

Step 3: Create new node
  - No match found (exact or semantic)
  - Create new KGNode with embedding stored for future dedup
  - Return new node
```

**Embedding model**: `sentence-transformers/all-MiniLM-L6-v2`
- Dimensionality: 384 (float32)
- Storage: BLOB column in `kg_nodes.embedding` (nullable for backward compat)
- Cosine similarity range: 0.0 (orthogonal) to 1.0 (identical)

**Same node_type requirement**: Semantic dedup only matches nodes with identical `node_type`. This preserves type distinctions (e.g., "reduce sugar" as `desired_outcome` vs. `attribute`).

**Threshold**: 0.80 (surface layer is stricter than canonical layer's 0.60 default)

**Why higher than canonical?** Preserves concept granularity. We want canonical slots to be more aggressive in merging (broader categories) while surface nodes preserve more nuance (specific respondent language).

### 3.2 Cross-Turn Node Resolution

After creating nodes from current turn, the system expands `label_to_node` with all session nodes to enable cross-turn edge resolution:

```python
# From GraphService.add_extraction_to_graph()

Step 1: Process current-turn concepts into nodes
  label_to_node = {concept.text.lower(): node}  # Current turn only

Step 1.5: Expand label_to_node with all session nodes
  all_session_nodes = await self.repo.get_nodes_by_session(session_id)
  for node in all_session_nodes:
    key = node.label.lower()
    if key not in label_to_node:  # Current-turn concepts take precedence
      label_to_node[key] = node
      cross_turn_count += 1

Step 2: Process relationships into edges (using expanded label_to_node)
  source_node = label_to_node.get(relationship.source_text.lower())
  target_node = label_to_node.get(relationship.target_text.lower())
  if source_node and target_node:
    create_edge(source_node.id, target_node.id)
```

**Example**:

```
Turn 3: Create node "morning routine" (id=n1)
Turn 7: Extract relationship "morning routine" → "stay focused"

label_to_node expansion:
  {"stay focused": n7, "morning routine": n1, ...}  # n1 from turn 3

Edge creation:
  create_edge(source_node_id=n1, target_node_id=n7)  # Cross-turn edge
```

**Log entry**: `cross_turn_nodes_loaded` shows count of previous-turn nodes made available for edge resolution.

### 3.3 NodeStateTracker Integration

After graph updates, NodeStateTracker is updated to track per-node state for exhaustion/focus signals:

```python
# From GraphUpdateStage._update_node_state_tracker()

1. Register new nodes:
     await node_tracker.register_node(node=node, turn_number=turn_number)

2. Update edge counts for affected nodes:
     For each edge:
       - source node: outgoing_delta += 1
       - target node: incoming_delta += 1
     await node_tracker.update_edge_counts(node_id, outgoing_delta, incoming_delta)

3. Record yield (if graph changes occurred):
     graph_changes = GraphChangeSummary(nodes_added=N, edges_added=M)
     await node_tracker.record_yield(node_id=previous_focus, graph_changes=graph_changes)
```

**Purpose**: Enables `graph.node.exhausted` and `graph.node.focus_streak` signals for strategy selection (prevents monotonous probing of same node).

### Comparison with Canonical Slots

| Aspect | Surface Dedup | Canonical Slots |
|--------|---------------|-----------------|
| **When** | At node creation time | After extraction, in SlotDiscoveryStage |
| **Scope** | Single session | Cross-session |
| **Threshold** | 0.80 | 0.60 (configurable) |
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
    confidence REAL,
    source_utterance_ids TEXT,  -- JSON array
    stance INTEGER DEFAULT 0,
    properties TEXT,  -- JSON
    created_at TEXT,
    -- ... other fields
);

-- Surface layer: kg_edges table
CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    confidence REAL,
    source_utterance_ids TEXT,  -- JSON array
    created_at TEXT,
    FOREIGN KEY (source_node_id) REFERENCES kg_nodes(id),
    FOREIGN KEY (target_node_id) REFERENCES kg_nodes(id)
);
```

---

## Stage 4.5: Canonical Slot Discovery

**File**: `src/services/turn_pipeline/stages/slot_discovery_stage.py`

**Service**: `src/services/canonical_slot_service.py`

### What is Canonical Slot Discovery?

Canonical slot discovery is a **deduplication system** that maps user's actual language (surface nodes) to abstract, reusable categories (canonical slots).

### Dual-Layer Deduplication Architecture

The system performs deduplication at **two layers**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DUAL-LAYER DEDUPLICATION                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LAYER 1: SURFACE SEMANTIC DEDUP (GraphService)                    │
│  ───────────────────────────────────────────────────────────────    │
│  • Threshold: 0.80 (higher = more conservative)                    │
│  • Purpose: Merge similar verbatim concepts within session         │
│  • Scope: Session-local only                                       │
│  • Requirement: Same node_type required                            │
│  • Pattern: Exact match → Semantic match → Create new             │
│                                                                     │
│  LAYER 2: CANONICAL SLOT DEDUP (CanonicalSlotService)              │
│  ─────────────────────────────────────────────────                 │
│  • Threshold: 0.60 default (configurable)                          │
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

### How It Works: The Pipeline

#### Step 1: LLM Proposes Canonical Slots

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

#### Step 2: Find or Create Slot

For each proposed slot, the system:

1. **Checks for exact match** (after lemmatization):
   - `reduce_inflammation` matches existing slot? → Use it

2. **No exact match? Search by similarity**:
   - Compute embedding for `"reduce_inflammation :: Minimizing inflammatory response"`
   - Find similar existing slots via cosine similarity
   - If `similarity >= canonical_similarity_threshold` → Merge into existing slot
   - Otherwise → Create new candidate slot

#### Step 3: Check Promotion

After mapping surface nodes, check if slot should be promoted:

```python
if slot.status == "candidate" and slot.support_count >= canonical_min_support_nodes:
    promote_slot(slot.id, turn_number)
```

### Database Schema

```sql
-- Canonical layer: canonical_slots table
CREATE TABLE canonical_slots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    description TEXT,
    embedding BLOB NOT NULL,  -- Required for canonical slots
    status TEXT DEFAULT 'candidate',  -- 'candidate' or 'active'
    support_count INTEGER DEFAULT 1,
    promoted_at_turn INTEGER,
    created_at TEXT,
    -- ... other fields
);

-- Mapping table: surface nodes → canonical slots
CREATE TABLE surface_to_slot_mapping (
    id TEXT PRIMARY KEY,
    surface_node_id TEXT NOT NULL,
    canonical_slot_id TEXT NOT NULL,
    similarity REAL,
    created_at TEXT,
    FOREIGN KEY (surface_node_id) REFERENCES kg_nodes(id),
    FOREIGN KEY (canonical_slot_id) REFERENCES canonical_slots(id)
);

-- Canonical edges: aggregated from surface edges
CREATE TABLE canonical_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_slot_id TEXT NOT NULL,
    target_slot_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    support_count INTEGER DEFAULT 1,
    surface_edge_ids TEXT,  -- JSON array
    created_at TEXT,
    FOREIGN KEY (source_slot_id) REFERENCES canonical_slots(id),
    FOREIGN KEY (target_slot_id) REFERENCES canonical_slots(id)
);
```

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
│      1. canonical_min_support_nodes (2) ← "How many mentions?"     │
│      2. canonical_min_turns (2) ← "Across how many turns?" [TODO]   │
│                                                                     │
│                           ↓                                         │
│                 [PROMOTION CHECK]                                  │
│                 if supportCount ≥ 2                                │
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

### The Nuance vs. Clutter Trade-Off

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

### Interview Length Considerations

| Interview Length | Recommended Threshold | Rationale |
|------------------|----------------------|-----------|
| Short (5-10 turns) | 1-2 | Lower threshold needed; concepts have fewer opportunities to recur |
| Medium (10-20 turns) | 2-3 | Balance between discovery and quality |
| Long (20+ turns) | 3-4 | Higher threshold filters out more noise |

### Test Results: min_support Comparison

| Test | Settings | Total Slots | Active | Candidate | Key Finding |
|------|----------|-------------|--------|------------|-------------|
| Test 1 | support=1, threshold=0.8 | 68 | 68 (100%) | 0 | All slots active immediately |
| Test 2 | support=2, threshold=0.83 | 40 | 5 (12.5%) | 35 (87.5%) | Strict filtering in action |

**Key Insight**: With `min_support=2`, only 5 of 40 slots became active—the remaining 35 stayed as candidates because they weren't mentioned enough times. This demonstrates the quality filtering effect.

### During Interview vs. After Interview

**Important distinction**: Setting `min_support` before the interview vs. filtering by `support_count` afterwards have different effects.

| Timing | Setting min_support | Filtering by support_count |
|--------|--------------------|---------------------------|
| **When** | Before interview starts | After interview completes |
| **Affects** | LLM context (which slots shown as reusable) | Reporting only (cosmetic) |
| **Impact on duplicates** | Yes (lower = fewer duplicates) | No (data already created) |
| **How to set** | `CANONICAL_MIN_SUPPORT_NODES=2` | SQL query: `WHERE support_count >= 2` |

**Recommendation**: If you want cleaner canonical graphs with fewer duplicates, set `min_support=2` **before** the interview. Filtering afterwards only affects reporting, not the underlying data (duplicates may already exist).

### Post-Interview Filtering

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

## Stage 5: Dual-Graph State Computation

**File**: `src/services/turn_pipeline/stages/state_computation_stage.py`

**Services**: `GraphService`, `CanonicalGraphService`

### Overview

After graph updates, Stage 5 computes graph states for both layers in parallel:

```python
# Compute surface graph state
graph_state = await self.graph.get_graph_state(session_id)

# Compute canonical graph state (if enabled)
if self.canonical_graph_service:
    canonical_graph_state = await self.canonical_graph_service.compute_canonical_state(session_id)
```

### Surface GraphState

**Model**: `src/domain/models/knowledge_graph.py:GraphState`

```python
@dataclass
class GraphState:
    node_count: int
    edge_count: int
    orphan_count: int  # Nodes with no outgoing edges
    max_depth: int     # Longest chain length
    depth_metrics: Optional[DepthMetrics]  # Per-methodology depth analysis
    turn_count: int
    strategy_history: List[str]
    # ... other fields
```

**Metrics provided**:
- Node/edge counts (for graph.node_count, graph.edge_count signals)
- Orphan count (for graph.orphan_count signal)
- Max depth (for graph.max_depth signal)
- Depth metrics (for methodology-specific chain analysis)

### Canonical CanonicalGraphState

**Model**: `src/domain/models/canonical_graph.py:CanonicalGraphState`

```python
@dataclass
class CanonicalGraphState:
    concept_count: int       # Number of canonical slots
    edge_count: int          # Number of canonical edges
    orphan_count: int        # Slots with no outgoing edges
    max_depth: int           # Longest chain in canonical graph
    unmapped_node_count: int # Surface nodes not mapped to any slot
    reduction_percentage: float  # (1 - canonical/surface) * 100
```

**Reduction percentage**: Indicates how much the canonical layer compresses the surface graph.

```python
surface_count = 93
canonical_count = 56
reduction_pct = (1 - 56/93) * 100 = 39.8%
```

### Saturation Metrics

Stage 5 also computes saturation metrics for interview continuation decisions:

```python
@dataclass
class SaturationMetrics:
    consecutive_low_info: int      # Turns with 0 new nodes+edges
    consecutive_shallow: int       # Turns with only shallow responses
    consecutive_depth_plateau: int # Turns at same max_depth
    new_info_rate: float           # New elements / total elements
    is_saturated: bool             # Meets any termination threshold
```

**Thresholds** (from `state_computation_stage.py`):
- `CONSECUTIVE_ZERO_YIELD_THRESHOLD = 5`
- `CONSECUTIVE_SHALLOW_THRESHOLD = 6`
- `DEPTH_PLATEAU_THRESHOLD = 6`

**ContinuationStage** (Stage 7) uses `is_saturated` to terminate interviews when diminishing returns detected.

### Observability via TurnResult

Both graph states are exposed in the `TurnResult` for observability:

```python
# From TurnResult in pipeline_contracts.py
turn_result = TurnResult(
    graph_state=surface_graph_state,         # Surface metrics
    canonical_graph_state=canonical_graph_state,  # Canonical metrics
    saturation_metrics=saturation_metrics,
    # ... other fields
)
```

**Log entry**: `dual_graph_states_computed` with reduction_pct shows compression achieved.

---

## Configuration Reference

All parameters are in `src/core/config.py` and can be set via environment variables.

### Extraction Configuration

| Parameter | Environment Variable | Default | Range | Description |
|-----------|---------------------|---------|-------|-------------|
| `enable_srl` | `ENABLE_SRL` | `True` | bool | Enable SRL preprocessing for discourse hints |
| `enable_canonical_slots` | `ENABLE_CANONICAL_SLOTS` | `True` | bool | Enable dual-graph canonical slot discovery |
| `min_word_count` | N/A | `3` | 1+ | Minimum words for extractability (hardcoded in service init) |

### Surface Deduplication Configuration

| Parameter | Environment Variable | Default | Range | Description |
|-----------|---------------------|---------|-------|-------------|
| `surface_similarity_threshold` | `SURFACE_SIMILARITY_THRESHOLD` | `0.80` | 0.0-1.0 | Cosine similarity threshold for surface node dedup |

**Higher than canonical (0.80 vs 0.60)**: Preserves concept granularity. We want canonical slots to be more aggressive in merging (broader categories) while surface nodes preserve more nuance (specific respondent language).

### Canonical Slot Configuration

| Parameter | Environment Variable | Default | Range | Description |
|-----------|---------------------|---------|-------|-------------|
| `canonical_similarity_threshold` | `CANONICAL_SIMILARITY_THRESHOLD` | `0.60` | 0.0-1.0 | Cosine similarity threshold for merging canonical slots |
| `canonical_min_support_nodes` | `CANONICAL_MIN_SUPPORT_NODES` | `2` | 1+ | Minimum surface nodes required for slot promotion to "active" |
| `canonical_min_turns` | `CANONICAL_MIN_TURNS` | `2` | 1+ | **NOT YET IMPLEMENTED** - Minimum distinct turns for promotion |

### LLM Configuration (Extraction)

| Parameter | Hardcoded Value | Description |
|-----------|-----------------|-------------|
| `temperature` | `0.4` | Balanced for relationship inference (not too deterministic) |
| `max_tokens` | `4000` | Handles long responses with many concepts |

### Threshold Comparison

| Threshold | Layer | Effect |
|-----------|-------|--------|
| 0.80 | Surface | More conservative, preserves nuance within session |
| 0.60 | Canonical | More aggressive, broader cross-session categories |

### Parameter Selection Guide

**Quick Reference**:

| Goal | surface_threshold | canonical_threshold | min_support_nodes | Rationale |
|------|------------------|---------------------|-------------------|-----------|
| **Production default** | 0.80 | 0.60 | 2 | Balanced defaults, broad dedup + confirmation |
| **Maximum discovery** | 0.80 | 0.60 | 1 | Most permissive, catch all variations |
| **Clean analysis** | 0.80 | 0.70-0.80 | 2-3 | Higher precision, clear aggregation |
| **Rich nuance** | 0.80 | 0.60 | 1 | Preserve all distinctions |
| **Short interviews (5-10 turns)** | 0.80 | 0.60 | 1 | Lower support needed |
| **Long interviews (20+ turns)** | 0.80 | 0.60-0.70 | 2-3 | Higher support filters noise |

**By Interview Type**:

| Interview Type | Recommended Settings |
|----------------|---------------------|
| Exploratory research | `surface=0.80`, `canonical=0.60`, `support=2` (default) |
| Validation study | `surface=0.80`, `canonical=0.70`, `support=2` |
| Production interview | `surface=0.80`, `canonical=0.60`, `support=2` (default) |
| Quick poll (5 turns) | `surface=0.80`, `canonical=0.60`, `support=1` |
| Deep dive (20+ turns) | `surface=0.80`, `canonical=0.60`, `support=2-3` |

**Note**: The defaults (`canonical=0.60`, `support=2`) balance broad deduplication with confirmation via second mention. For stricter matching, increase `canonical_similarity_threshold` to 0.70-0.80.

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

**Output**:
1. Total mappings count
2. Histogram of similarity scores in buckets:
   - 0.8-0.85 (includes 0.8 test level)
   - 0.85-0.88 (includes 0.83)
   - And other ranges
3. Statistics for non-exact matches (min, max, mean, median, stddev)
4. Recommendation on whether threshold tuning is needed

### 2. run_simulation.py

**Purpose**: Run a synthetic interview simulation for testing.

**Usage**:
```bash
# Basic usage
uv run python scripts/run_simulation.py <concept_id> <persona_id> [max_turns]

# With custom thresholds
CANONICAL_SIMILARITY_THRESHOLD=0.8 uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 15

CANONICAL_MIN_SUPPORT_NODES=2 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 10

SURFACE_SIMILARITY_THRESHOLD=0.75 uv run python scripts/run_simulation.py coffee_jtbd_v2 quality_focused 12
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
- `skeptical_analyst`: Questions claims, demands evidence
- `social_conscious`: Influenced by peers, follows trends
- `minimalist`: Values simplicity, wants essentials only

---

## Practical Examples

### Example 1: Testing Surface Deduplication Threshold

**Scenario**: You want to see how surface dedup threshold affects node creation.

```bash
# Test 1: Default threshold (0.80)
SURFACE_SIMILARITY_THRESHOLD=0.80 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15

# Test 2: More permissive (0.75)
SURFACE_SIMILARITY_THRESHOLD=0.75 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15

# Test 3: More conservative (0.85)
SURFACE_SIMILARITY_THRESHOLD=0.85 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15
```

**What to compare**:
- Final node count (lower threshold = fewer nodes due to more merges)
- Log entries for `node_deduplicated` with `method="semantic"`
- Check for false merges (semantically different concepts merged)

### Example 2: Testing Canonical Threshold Impact

**Scenario**: You want cleaner canonical graphs with fewer duplicates.

```bash
# Test 1: Permissive (0.80)
CANONICAL_SIMILARITY_THRESHOLD=0.80 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15

# Test 2: Balanced (0.83)
CANONICAL_SIMILARITY_THRESHOLD=0.83 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15

# Test 3: Conservative (0.88)
CANONICAL_SIMILARITY_THRESHOLD=0.88 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15
```

**Then analyze**:
```bash
uv run python scripts/analyze_similarity_distribution.py <session_id>
```

**What to look for**:
- Non-exact match percentage: If >10%, threshold is having significant effect
- Histogram distribution: Are scores clustering near your threshold?
- Sample non-exact matches: Are these valid merges or false positives?

### Example 3: Testing min_support_nodes Impact

**Scenario**: Compare how different `min_support_nodes` values affect slot promotion and canonical graph structure.

```bash
# Test 1: Permissive (support=1)
CANONICAL_MIN_SUPPORT_NODES=1 CANONICAL_SIMILARITY_THRESHOLD=0.83 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15

# Test 2: Balanced (support=2)
CANONICAL_MIN_SUPPORT_NODES=2 CANONICAL_SIMILARITY_THRESHOLD=0.83 uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 15
```

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

### Example 4: Debugging Invalid Edge Type Rejections

**Scenario**: You notice relationships are being rejected due to invalid edge types.

**Check logs**:
```bash
# Look for invalid_edge_type warnings
grep "invalid_edge_type" /tmp/uvicorn_debug.log
```

**Cause**: LLM proposing edge types not in methodology schema.

**Solution**: Check methodology YAML for valid edge types:
```bash
# View edge types for JTBD
cat config/methodologies/jobs_to_be_done.yaml | grep -A 20 "edge_types:"
```

**Verify prompt uses correct primary edge type**:
```python
# In extraction.py:get_extraction_system_prompt()
valid_edge_types = schema.get_valid_edge_types()
primary_edge_type = next(
    (et for et in valid_edge_types if et != "revises"),
    valid_edge_types[0]
)
```

### Example 5: Testing Cross-Turn Edge Resolution

**Scenario**: Verify that edges are being created between nodes from different turns.

**Check logs**:
```bash
# Look for cross_turn_nodes_loaded entries
grep "cross_turn_nodes_loaded" /tmp/uvicorn_debug.log

# Look for cross_turn_node_context_injected entries
grep "cross_turn_node_context_injected" /tmp/uvicorn_debug.log
```

**Expected behavior**:
- Turn 1: Extract concept "morning routine"
- Turn 5: Context includes "morning routine" in `[Existing graph concepts from previous turns]`
- Turn 5: LLM creates relationship: "morning routine" → "stay focused at work"
- Log shows: `cross_turn_edge_created` with `source_turn=1, target_turn=5`

**If no cross-turn edges**:
1. Check node label injection is working (`cross_turn_node_context_injected`)
2. Verify LLM is receiving existing labels in prompt
3. Check relationship validation isn't rejecting cross-turn edges

---

## Troubleshooting

### Problem: All relationships rejected

**Symptoms**:
- `extraction_complete` shows 0 relationships
- Logs show many `invalid_edge_type` warnings

**Cause**: Methodology schema edge types don't match what LLM is proposing.

**Solution**:
1. Check methodology YAML for valid edge types:
   ```bash
   cat config/methodologies/jobs_to_be_done.yaml | grep -A 20 "edge_types:"
   ```
2. Verify prompt is using correct primary edge type (not hardcoded "leads_to")
3. Check if `ontology.relationship_examples` are loaded correctly

**Historical context**: This was the JTBD extraction bug (commit `344120c`) where hardcoded "leads_to" caused 99% rejection rate. Fixed by dynamic primary_edge_type selection.

### Problem: No cross-turn edges

**Symptoms**:
- `cross_turn_nodes_loaded` shows 0 count
- All edges connect nodes from same turn

**Cause**: Node label injection may be disabled or failing.

**Solution**:
1. Check `cross_turn_node_context_injected` log entry
2. Verify `context.context_loading_output.recent_node_labels` is populated
3. Check extraction prompt includes `[Existing graph concepts from previous turns]` section

**Debug**:
```python
# In extraction_stage.py:_format_node_labels()
labels = context.context_loading_output.recent_node_labels
print(f"Labels to inject: {labels}")
```

### Problem: Low edge/node ratio

**Symptoms**:
- Many nodes but few edges
- `graph_state.edge_count / graph_state.node_count < 0.5`

**Cause**: Schema `permitted_connections` may be too restrictive.

**Solution**:
1. Check methodology YAML for `permitted_connections`:
   ```yaml
   edge_types:
     hinders:
       permitted_connections:
         - [pain_point, job]  # Only pain_point → job allowed
   ```
2. Expand permitted_connections to allow more valid pairings
3. Check logs for `invalid_connection` rejections

### Problem: Too many canonical slots, all candidates

**Symptoms**:
- Many candidate slots, none promoted to active
- Low `canonical_graph_state.concept_count` vs. surface count

**Cause**: `canonical_min_support_nodes` too high for interview length.

**Solution**:
```bash
# Lower the threshold
CANONICAL_MIN_SUPPORT_NODES=2 uv run python scripts/run_simulation.py ...
```

**For short interviews (5-10 turns)**: Use `min_support=1` to catch more concepts.

### Problem: All similarity scores are 1.0

**Symptoms**:
- `analyze_similarity_distribution.py` shows 100% exact matches
- No similarity-based deduplication occurring

**Cause**: LLM is perfectly reusing exact canonical slot names.

**Solution**: This is normal behavior—LLM learns to reuse names. Not a problem.

**To force similarity matching** (for testing):
- Use persona with more varied vocabulary (`skeptical_analyst`)
- Run longer interviews to increase variation chance

### Problem: No canonical slots being created

**Symptoms**:
- `canonical_graph_state` is None
- No entries in `canonical_slots` table

**Cause**: `enable_canonical_slots` feature flag may be disabled.

**Check**:
```python
# In src/core/config.py
enable_canonical_slots: bool = True  # Must be True
```

### Problem: Extraction always skipped (not extractable)

**Symptoms**:
- `extraction_skipped_heuristic` in logs
- All responses marked as non-extractable

**Cause**: `min_word_count` threshold too high or yes/no filter too aggressive.

**Solution**:
```python
# In ExtractionService initialization
ExtractionService(
    llm_client=llm,
    skip_extractability_check=True,  # Bypass heuristic check
)
```

**Or adjust threshold**:
```python
ExtractionService(
    llm_client=llm,
    min_word_count=2,  # Lower from default 3
)
```

---

## Bug Fixes & Historical Context

### 1. JTBD Extraction Bug (Commit 344120c)

**Problem**: Jobs-to-be-Done interviews had 99% relationship rejection rate.

**Root cause**: Hardcoded "leads_to" edge type in extraction prompts. JTBD schema doesn't define "leads_to" edge type, so all proposed relationships failed validation.

```python
# OLD (hardcoded for Means-End Chain):
primary_edge_type = "leads_to"  # WRONG - doesn't exist in JTBD

# NEW (dynamic selection):
valid_edge_types = schema.get_valid_edge_types()
primary_edge_type = next(
    (et for et in valid_edge_types if et != "revises"),
    valid_edge_types[0]
)
```

**Impact**: 19x improvement in edge/node ratio after fix (0.05 → 0.95).

**Lesson**: Never hardcode methodology-specific types—always derive from schema.

### 2. YAML Ontology Field Loading Bug (Commit 6bdbef4)

**Problem**: `extraction_guidelines`, `relationship_examples`, and `concept_naming_convention` always None.

**Root cause**: Fields nested under `ontology:` in YAML but read at top level in code.

```yaml
# YAML structure:
ontology:
  concept_naming_convention: "..."
  extraction_guidelines: [...]
  relationship_examples: {...}

# Code was reading:
schema.concept_naming_convention  # None (didn't check ontology.*)
```

**Fix**: Added fields to `OntologySpec` class in `methodology_schema.py`:

```python
@dataclass
class OntologySpec:
    node_types: Dict[str, NodeTypeSpec]
    edge_types: Dict[str, EdgeTypeSpec]
    concept_naming_convention: Optional[str] = None  # NEW
    extraction_guidelines: List[str] = field(default_factory=list)  # NEW
    relationship_examples: Dict[str, RelationshipExampleSpec] = field(default_factory=dict)  # NEW
```

**Impact**: Methodology-specific naming conventions and examples now work correctly.

### 3. Stance Deprecation

**Problem**: `stance` field on concepts was redundant with `llm.valence` signal.

**Decision**: Removed stance extraction from prompts and schema validation.

```python
# OLD: LLM extracted stance (-1, 0, +1)
concept.stance = -1  # Negative stance

# NEW: llm.valence signal covers sentiment
# No stance extraction, field defaults to 0
```

**Rationale**: `llm.valence` (from response depth/specificity analysis) captures sentiment more accurately than explicit stance extraction.

**Status**: `stance` field still exists on `KGNode` for backward compatibility (defaults to 0).

---

## References

### Implementation Files

| File | Purpose |
|------|---------|
| [extraction_service.py](../src/services/extraction_service.py) | Main extraction pipeline |
| [extraction_stage.py](../src/services/turn_pipeline/stages/extraction_stage.py) | Stage 3 orchestration + context formatting |
| [extraction.py](../src/llm/prompts/extraction.py) | Prompt construction + JSON repair |
| [graph_service.py](../src/services/graph_service.py) | Surface dedup + node/edge creation |
| [graph_update_stage.py](../src/services/turn_pipeline/stages/graph_update_stage.py) | Stage 4 orchestration |
| [canonical_slot_service.py](../src/services/canonical_slot_service.py) | Canonical slot discovery |
| [slot_discovery_stage.py](../src/services/turn_pipeline/stages/slot_discovery_stage.py) | Stage 4.5 |
| [state_computation_stage.py](../src/services/turn_pipeline/stages/state_computation_stage.py) | Stage 5 dual-graph state |
| [methodology_schema.py](../src/domain/models/methodology_schema.py) | Schema validation + OntologySpec |
| [config.py](../src/core/config.py) | All configuration parameters |

### Documentation

- **Data Flow Paths**: `docs/data_flow_paths.md` (Paths 3, 5, 10, 11, 12, 13, 14)
- **Pipeline Contracts**: `docs/pipeline_contracts.md`
- **System Design**: `docs/SYSTEM_DESIGN.md`
- **Signals & Strategies**: `docs/signals_and_strategies.md`

### Related Beads

- **vub0** (Phase 2): Dual-Graph Architecture
- **gjb5**: Canonical threshold tuning
- **z7gh**: Threshold testing
- **00cw**: Lemmatization for slot matching
