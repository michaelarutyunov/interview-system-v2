# Signals and Strategy Scoring Guide

**Purpose**: Comprehensive guide to understanding the Signal Pools Architecture for adaptive strategy selection.

**Related Beads**: See ADR-014 (Signal Pools Architecture), Phase 6 implementation beads.

---

## Table of Contents

1. [What is Signal-Based Strategy Selection?](#what-is-signal-based-strategy-selection)
2. [How It Works: The Pipeline](#how-it-works-the-pipeline)
3. [Signal Pools Overview](#signal-pools-overview)
4. [Node-Level Signals](#node-level-signals)
5. [Strategy Scoring Mechanics](#strategy-scoring-mechanics)
6. [Configuration Parameters](#configuration-parameters)
7. [YAML Configuration Guide](#yaml-configuration-guide)
8. [Tools and Debugging](#tools-and-debugging)
9. [Practical Examples](#practical-examples)
10. [Troubleshooting](#troubleshooting)
11. [References](#references)

---

## What is Signal-Based Strategy Selection?

Signal-based strategy selection is an **adaptive decision system** that chooses questioning strategies based on real-time signals extracted from the interview context.

### The Problem It Solves

Traditional interview systems use fixed rules or simple heuristics:

```
Traditional: Always ask "Why?" after every answer
Problem: Boring, repetitive, doesn't adapt to user engagement

Signal-Based: Analyze response depth, engagement, graph state
Decision: Choose strategy based on 20+ signals
Result: Dynamic, context-aware conversation flow
```

### Signal Pools Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SIGNAL POOLS ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ GRAPH POOL  │  │  LLM POOL   │  │ TEMPORAL    │  │ META POOL  │ │
│  │  (graph.*)  │  │  (llm.*)    │  │  (temporal.*)│  │  (meta.*)  │ │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├────────────┤ │
│  │ node_count  │  │resp_depth   │  │strategy_rep │  │progress    │ │
│  │ max_depth   │  │specificity  │  │turns_since  │  │phase       │ │
│  │ chain_comp  │  │certainty    │  │last_change  │  │node_opp    │ │
│  │ ...         │  │valence      │  │response_trend│ │            │ │
│  │             │  │engagement   │  │             │  │conv_sat    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
│  │             │  │engagement   │  │             │  │can_sat     │ │
│         └─────────────────┴─────────────────┴──────────────┘       │
│                                    │                                │
│                                    ▼                                │
│                         ┌─────────────────────┐                     │
│                         │  SIGNAL DETECTION   │                     │
│                         │    (Async Batch)    │                     │
│                         └──────────┬──────────┘                     │
│                                    │                                │
│                                    ▼                                │
│                         ┌─────────────────────┐                     │
│                         │ STRATEGY SCORING    │                     │
│                         │  (Weighted Sum)     │                     │
│                         └──────────┬──────────┘                     │
│                                    │                                │
│                                    ▼                                │
│                         ┌─────────────────────┐                     │
│                         │  STRATEGY SELECTED  │                     │
│                         │   (Best Score)      │                     │
│                         └─────────────────────┘                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How It Works: The Pipeline

### Stage 6: Strategy Selection

Located in `src/services/turn_pipeline/stages/strategy_selection_stage.py`.

```python
# Simplified flow
async def execute(self, context: PipelineContext) -> PipelineContext:
    # 1. Load methodology configuration
    methodology = await self.registry.load(context.methodology)

    # 2. Detect global signals (graph, llm, temporal, meta)
    global_signals = await self.global_service.detect(
        config=methodology.signals,
        context=context,
        graph_state=context.graph_state
    )

    # 3. Detect node-level signals for candidate nodes
    node_signals = await self.node_service.detect_for_nodes(
        config=methodology.signals,
        context=context,
        node_ids=candidate_nodes
    )

    # 4. Joint strategy-node scoring
    result = await self.strategy_service.select_strategy(
        methodology=methodology,
        global_signals=global_signals,
        node_signals=node_signals,
        turn_number=context.turn_number
    )

    context.strategy = result.strategy
    context.focus = result.focus
    context.signals = result.signals
    context.strategy_alternatives = result.alternatives
```

### Signal Detection Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SIGNAL DETECTION FLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: YAML Configuration                                         │
│  ───────────────────────                                            │
│  signals:                                                           │
│    graph: [max_depth, chain_completion]                              │
│    llm: [response_depth, valence]                                   │
│    temporal: [strategy_repetition_count]                            │
│    meta: [interview.phase]                                          │
│                                                                     │
│                           ↓                                         │
│                                                                     │
│  Step 2: Dependency Resolution                                      │
│  ─────────────────────────────                                      │
│  Signals declare dependencies:                                      │
│    InterviewPhaseSignal depends on [turn_number]                    │
│                                                                     │
│  ComposedSignalDetector performs topological sort:                  │
│    turn_number → meta.interview.phase                               │
│                                                                     │
│                           ↓                                         │
│                                                                     │
│  Step 3: Parallel Detection by Pool                                 │
│  ─────────────────────────────────                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │GraphSignals │  │ LLMSignals  │  │SessionSignals│                  │
│  │  (async)    │  │  (async)    │  │   (async)    │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│       O(1) cached      Fresh API         O(1) cached                │
│                                                                     │
│  Note: All LLM signals batched into SINGLE API call                 │
│                                                                     │
│                           ↓                                         │
│                                                                     │
│  Step 4: Signal Aggregation                                         │
│  ────────────────────────────                                       │
│  signals = {                                                        │
│    "graph.max_depth": 0.5,                                          │
│    "llm.response_depth": 0.75,                                      │
│    "llm.valence": 0.5,                                              │
│    "temporal.strategy_repetition_count": 0.4,                       │
│    "meta.interview.phase": "mid"                                    │
│  }                                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Signal Pools Overview

### 1. Graph Signals (`graph.*`)

**Source**: Knowledge graph snapshot
**Cost**: O(1) - cached on graph update
**Location**: `src/signals/graph/`

| Signal | Type | Description | Use Case |
|--------|------|-------------|----------|
| `graph.node_count` | int | Total concepts extracted | Interview progress (not used in strategy scoring) |
| `graph.edge_count` | int | Total relationships | Connectivity health (not used in strategy scoring) |
| `graph.orphan_count` | int | Isolated nodes (no edges) | Needs exploration (not used in strategy scoring) |
| `graph.max_depth` | float | Longest chain depth, normalized by ontology levels [0,1] | Laddering progress |
| `graph.avg_depth` | float | Average depth across chains | Overall depth |
| `graph.chain_completion.ratio` | float | Ratio of complete chains [0,1] | Completion metric |
| `graph.chain_completion.has_complete` | bool | Whether any chain is complete | Completion flag |
| `graph.canonical_concept_count` | int | Deduplicated concepts | Canonical coverage |
| `graph.canonical_edge_density` | float | Edge-to-concept ratio | Canonical connectivity |
| `graph.canonical_exhaustion_score` | float | Avg exhaustion (0-1) | Overall exhaustion |

**Example Values**:
```python
{
    "graph.max_depth": 0.5,           # 50% of ontology depth
    "graph.chain_completion.ratio": 0.75,  # 75% chains complete
    "graph.chain_completion.has_complete": True
}
```

---

### 2. LLM Signals (`llm.*`)

**Source**: LLM analysis of user response using rubric-based prompts
**Cost**: High (1 API call per response, batched)
**Location**: `src/signals/llm/`

| Signal | Type | Values | Description |
|--------|------|--------|-------------|
| `llm.response_depth` | categorical | surface, shallow, moderate, deep, comprehensive | Elaboration quantity |
| `llm.specificity` | float | 0.0-1.0 | Concreteness of language |
| `llm.certainty` | float | 0.0-1.0 | Epistemic confidence |
| `llm.valence` | float | 0.0-1.0 | Emotional tone (negative-positive) |
| `llm.engagement` | float | 0.0-1.0 | Willingness to engage |

**Rubric-Based Detection**: The LLM batch detector loads rubric definitions from `src/signals/llm/prompts/signals.md` using indentation-based parsing. Each signal's rubric defines the scoring criteria and scale anchors that guide the LLM's assessment.

**Scale Interpretation (Float Signals)**:
```
0.0 = Very low / minimal / negative
0.25 = Low / somewhat vague / uncertain
0.5 = Moderate / neutral
0.75 = High / fairly concrete / confident
1.0 = Very high / detailed / positive / certain
```

**Categorical Signal (response_depth)**:
```
surface = Minimal or single-word answer
shallow = Brief statement with no supporting detail
moderate = Moderate elaboration with some explanation
deep = Detailed response with reasoning or examples
comprehensive = Rich, layered response exploring multiple angles
```

**Question Context**: The LLM scorer receives both the respondent's answer and the preceding interviewer question for context-aware assessment. The question is extracted from `recent_utterances` (last system utterance) and threaded through the signal detection chain:
```
GlobalSignalDetectionService → ComposedSignalDetector → LLMBatchDetector
```
The prompt template uses `{question}` and `{response}` placeholders. Response text is truncated to 500 characters (~75 words) and question text to 200 characters to balance scoring accuracy with token costs.

**Batch Detection**: All LLM signals are detected in a single API call:
```python
# One API call returns all signals:
{
    "llm.response_depth": "deep",  # Categorical string
    "llm.specificity": 0.5,        # Float [0,1]
    "llm.certainty": 1.0,          # Float [0,1]
    "llm.valence": 0.75,           # Float [0,1]
    "llm.engagement": 1.0          # Float [0,1]
}
```

---

### 3. Temporal Signals (`temporal.*`)

**Source**: Conversation history and session state
**Cost**: O(1) - cached per turn
**Location**: `src/signals/session/`

| Signal | Type | Description |
|--------|------|-------------|
| `temporal.strategy_repetition_count` | float | Times current strategy used in last 5 turns, normalized [0,1] by dividing by window size (5) |
| `temporal.turns_since_strategy_change` | float | Consecutive turns using current strategy, normalized [0,1] by dividing by window size (5) |
| `llm.global_response_trend` | str | Trend: `fatigued`, `shallowing`, `engaged`, `stable` |

**Trend Detection**:
```python
# Analyzes last 3 LLM signals
{
    "llm.global_response_trend": "fatigued"
    # Detected: response_depth decreasing + engagement dropping
}
```

**Usage for Diversity**:
```yaml
# Penalize overused strategies
signal_weights:
  temporal.strategy_repetition_count: -0.5  # Negative weight
```

---

### 4. Meta Signals (`meta.*`)

**Source**: Composite - integrates multiple signal pools
**Cost**: Varies (some O(1), some compute on demand)
**Location**: `src/signals/meta/`

| Signal | Type | Description |
|--------|------|-------------|
| `meta.interview_progress` | float | 0.0-1.0 progress through interview (**DEPRECATED** for JTBD, retained for MEC) |
| `meta.interview.phase` | str | `early`, `mid`, or `late` |
| `meta.node.opportunity` | str | `exhausted`, `probe_deeper`, or `fresh` |
| `meta.conversation.saturation` | float | 0.0-1.0 interview saturation from surface graph velocity (NEW) |
| `meta.canonical.saturation` | float | 0.0-1.0 interview saturation from canonical graph velocity (NEW) |

#### Saturation Signals (New in Phase 6)

**Purpose**: Replace `meta.interview_progress` with methodology-agnostic saturation detection based on information velocity (EWMA of new concept discovery rate).

**Formula**:
```
velocity_decay = 1 - (ewma / max(peak, 1.0))
edge_density_norm = min(edge_count / node_count / 2.0, 1.0)
turn_floor = min(turn_number / 15.0, 1.0)
saturation = 0.60 × velocity_decay + 0.25 × edge_density_norm + 0.15 × turn_floor
```

**Component Weights**:
| Component | Weight | Description |
|-----------|--------|-------------|
| velocity_decay | 60% | Primary indicator — slows as discovery rate decreases |
| edge_density_norm | 25% | Graph richness — edges/nodes normalized to 2.0 |
| turn_floor | 15% | Minimum duration — prevents early saturation on turn 1-2 |

**Usage in validate_outcome strategy**:
```yaml
signal_weights:
  meta.conversation.saturation: 0.5  # High saturation → validate & wrap
  meta.canonical.saturation: 0.3     # Supportive metric
```

**Data Model** (velocity state tracked in SessionState):
- `surface_velocity_ewma`: EWMA of surface node delta per turn (α=0.4)
- `surface_velocity_peak`: Peak surface node delta observed
- `canonical_velocity_ewma`: EWMA of canonical node delta per turn
- `canonical_velocity_peak`: Peak canonical node delta observed

**See Also**: [Path 16: Saturation Signal Computation](./data_flow_paths.md#path-16-saturation-signal-computation-information-velocity)

**Phase Boundaries** (configurable):
```yaml
phase_boundaries:
  early_max_turns: 4    # 0-3 turns = early phase
  mid_max_turns: 12     # 4-11 turns = mid phase
                        # 12+ turns = late phase
```

---

## Node-Level Signals

Node-level signals provide **per-node** assessments for joint strategy-node scoring (D1 Architecture).

### Signal Namespaces

| Namespace | Description | Example Signals |
|-----------|-------------|-----------------|
| `graph.node.*` | Graph-derived per-node signals | exhaustion_score, focus_streak, has_outgoing |
| `technique.node.*` | Technique-specific signals | strategy_repetition |

### NodeState Field Write Timing

**Critical**: All node signals read from `NodeState` fields, which are written by specific pipeline stages. Understanding this timing is essential for avoiding bugs where signals read stale state.

| NodeState Field | Written By | Pipeline Stage | Signal Detection Timing |
|-----------------|------------|-----------------|-------------------------|
| `node_id`, `label`, `created_at_turn`, `depth`, `node_type`, `is_terminal`, `level` | `register_node()` | Stage 4 (GraphUpdateStage) | Fresh at Stage 6 detection |
| `focus_count`, `last_focus_turn` | `update_focus()` | Stage 9 (ContinuationStage) | From PREVIOUS turn at Stage 6 |
| `current_focus_streak` | `update_focus()` | Stage 9 (ContinuationStage) | From PREVIOUS turn at Stage 6 - CRITICAL: Stage 4 `record_yield()` must NOT reset this |
| `turns_since_last_focus` | `update_focus()` | Stage 9 (ContinuationStage) | Ticked for ALL nodes in Stage 9 |
| `turns_since_last_yield` | `record_yield()`, `update_focus()` | Stage 4 (GraphUpdateStage), Stage 9 (ContinuationStage) | Reset by Stage 4 on yield, ticked for all nodes in Stage 9 |
| `last_yield_turn`, `yield_count`, `yield_rate` | `record_yield()` | Stage 4 (GraphUpdateStage) | Fresh at Stage 6 detection |
| `all_response_depths` | `append_response_signal()` | Stage 9 (ContinuationStage) | From PREVIOUS turn at Stage 6 |
| `edge_count_incoming`, `edge_count_outgoing` | `update_edge_counts()` | Stage 4 (GraphUpdateStage) | Fresh at Stage 6 detection |
| `strategy_usage_count`, `last_strategy_used`, `consecutive_same_strategy` | `update_focus()` | Stage 9 (ContinuationStage) | From PREVIOUS turn at Stage 6 |
| `previous_focus` (tracker-level) | `update_focus()` | Stage 9 (ContinuationStage) | From PREVIOUS turn at Stage 6 |

**Key Timing Dependencies**:

1. **Stage 4 → Stage 6**: Signals that read yield metrics (`exhausted`, `exhaustion_score`, `yield_stagnation`) get fresh values because `record_yield()` runs in Stage 4.

2. **Stage 9 (next turn) → Stage 6 (current turn)**: Signals that read focus metrics (`focus_streak`, `recency_score`, `is_current_focus`) are reading values from the PREVIOUS turn's `update_focus()` call in Stage 9 ContinuationStage. This is correct — the focus was selected in the previous turn's Stage 9 and is now being evaluated for signals.

3. **Critical: current_focus_streak timing**: The `current_focus_streak` field is incremented in Stage 9's `update_focus()` call. Signal detection in Stage 6 reads this value, which represents the streak that was set during the previous turn's focus selection. Stage 4's `record_yield()` must NOT reset this value, or signals would always read 0.

4. **Turn counter tick order**: `turns_since_last_yield` is ticked for ALL nodes in Stage 9's `update_focus()` loop, then reset to 0 for the yielding node in Stage 4's `record_yield()`. This means Stage 6 signals see the accumulated value from the previous turn's tick.

### Available Node Signals

| Signal | Type | Reads NodeState Fields | Timing Notes |
|--------|------|------------------------|--------------|
| `graph.node.exhaustion_score` | float | `focus_count`, `turns_since_last_yield`, `current_focus_streak`, `all_response_depths` | Fresh: `turns_since_last_yield` updated Stage 4, `current_focus_streak` from previous turn Stage 9 |
| `graph.node.exhausted` | bool | `focus_count`, `turns_since_last_yield`, `current_focus_streak`, `all_response_depths` | Fresh: `turns_since_last_yield` updated Stage 4, `current_focus_streak` from previous turn Stage 9 |
| `graph.node.yield_stagnation` | bool | `focus_count`, `turns_since_last_yield` | Fresh: both updated Stage 4 or ticked Stage 9 |
| `graph.node.focus_streak` | str | `current_focus_streak` | From previous turn Stage 9 - represents streak selected last turn |
| `graph.node.is_current_focus` | bool | `previous_focus` (tracker-level) | From previous turn Stage 9 - represents focus selected last turn |
| `graph.node.recency_score` | float | `turns_since_last_focus` | Ticked for all nodes in Stage 9 - represents turns since last focus selection |
| `graph.node.is_orphan` | bool | `edge_count_incoming`, `edge_count_outgoing` | Fresh: updated Stage 4 |
| `graph.node.edge_count` | int | `edge_count_incoming`, `edge_count_outgoing` | Fresh: updated Stage 4 |
| `graph.node.has_outgoing` | bool | `edge_count_outgoing` | Fresh: updated Stage 4 |
| `technique.node.strategy_repetition` | int | `consecutive_same_strategy` | From previous turn Stage 9 - represents strategy usage through last turn |

### Node Signal Detection

```python
# Returns dict mapping node_id -> signal_value
{
    "graph.node.exhausted": {
        "node_1": False,
        "node_2": True,   # This node is exhausted
        "node_3": False
    },
    "graph.node.focus_streak": {
        "node_1": "high",    # Focused heavily
        "node_2": "none",    # Not recently focused
        "node_3": "low"
    }
}
```

---

## Strategy Scoring Mechanics

### The Scoring Formula

```
base_score = Σ(signal_weight × signal_value)
final_score = (base_score × phase_multiplier) + phase_bonus
```

> **Note**: All signals are normalized at their source (detector layer) to produce values in [0, 1] or bool. No additional normalization step is needed during scoring.

### Signal Value Resolution

The scoring system supports three signal value patterns:

#### 1. Direct Match
```yaml
signal_weights:
  graph.max_depth: 0.5  # Uses signal value directly
```
- Boolean: `true` = 1.0, `false` = 0.0
- Numeric: already normalized to [0,1] at source

#### 2. Compound Key with String Match
```yaml
signal_weights:
  llm.global_response_trend.fatigued: 1.0  # True if trend == "fatigued"
```
- Value is 1.0 if signal equals the suffix, 0.0 otherwise

#### 3. Threshold Binning (Float Signals Only)
```yaml
signal_weights:
  llm.specificity.high: 0.8   # True if value >= 0.75
  llm.specificity.mid: 0.3    # True if 0.25 < value < 0.75
  llm.specificity.low: 0.3    # True if value <= 0.25
```
- `.high` matches values >= 0.75
- `.mid` matches values in (0.25, 0.75) exclusive
- `.low` matches values <= 0.25
- **Important**: Only use with float signals normalized to [0, 1]. Unbounded signals (e.g., `graph.node.edge_count`, `graph.canonical_concept_count`) will produce incorrect results with threshold binning
- **Categorical signals**: `llm.response_depth` is categorical (surface/shallow/moderate/deep/comprehensive) and uses string equality matching (pattern #2), not threshold binning:
  ```yaml
  signal_weights:
    llm.response_depth.deep: 0.8      # True if response_depth == "deep"
    llm.response_depth.moderate: 0.3  # True if response_depth == "moderate"
    llm.response_depth.shallow: 0.3   # True if response_depth == "shallow"
  ```

### Phase Weights and Bonuses

```yaml
phases:
  early:
    signal_weights:
      explore: 1.5      # 1.5x multiplier
    phase_bonuses:
      explore: 0.2      # +0.2 bonus
  mid:
    signal_weights:
      deepen: 1.3
    phase_bonuses:
      deepen: 0.3
```

**Example Calculation**:
```
Base explore score: 2.5
Early phase multiplier: 1.5
Early phase bonus: 0.2

Final score = (2.5 × 1.5) + 0.2 = 3.95
```

---

## Configuration Parameters

All parameters are defined in methodology YAML files and `src/core/config.py`.

### Methodology YAML Structure

```yaml
method:
  name: means_end_chain
  description: "Laddering: attributes → consequences → values"

# Signal declarations
signals:
  graph:
    - graph.max_depth
    - graph.chain_completion
  llm:
    - llm.response_depth
    - llm.specificity
    - llm.certainty
    - llm.valence
  temporal:
    - temporal.strategy_repetition_count
    - llm.global_response_trend
  meta:
    - meta.interview.phase
    - meta.node.opportunity

# Phase boundaries
phase_boundaries:
  early_max_turns: 4
  mid_max_turns: 12

# Strategy definitions
strategies:
  - name: explore
    description: "Find new attributes/branches"
    signal_weights:
      llm.response_depth.low: 0.8
      temporal.strategy_repetition_count: -0.5

# Phase-based adaptation
phases:
  early:
    signal_weights:
      explore: 1.5
    phase_bonuses:
      explore: 0.2
```

### Parameter Reference

| Parameter | Location | Description |
|-----------|----------|-------------|
| `signals.{pool}` | YAML | List of signals to detect from each pool |
| `phase_boundaries.{phase}_max_turns` | YAML | Turn count thresholds for phase detection |
| `signal_weights.{signal}` | YAML (strategy) | Weight for scoring contribution |
| `signal_weights.{strategy}` | YAML (phase) | Phase-specific multiplier |
| `phase_bonuses.{strategy}` | YAML (phase) | Phase-specific additive bonus |

---

## Methodology-Aware Concept Naming

Methodologies can define their own concept naming conventions via YAML configuration. This guides the LLM to produce consistent, methodology-appropriate concept labels rather than verbatim user language.

### YAML Configuration

```yaml
method:
  name: jobs_to_be_done
  description: "Jobs-to-be-Done interviews"

ontology:
  # ... node type definitions ...

  concept_naming_convention: >
    Name each concept according to its node type role:
    phrase job_statements as jobs to be done,
    pain_points as frustrations or obstacles,
    gain_points as desired outcomes or benefits,
    solution_approaches as methods or actions,
    job_contexts as situations or circumstances,
    emotional_jobs as emotional states sought,
    social_jobs as social outcomes desired,
    job_triggers as initiating events.
    Use the examples in each node type description as naming models.
```

### How It Works

1. **YAML Loading**: `MethodologySchema` includes `concept_naming_convention: Optional[str]` field
2. **Prompt Injection**: ExtractionService loads convention from schema and passes to prompt builder
3. **Dynamic Prompt**: If convention provided, replaces generic naming guidance in system prompt
4. **Output**: LLM produces concepts like "maintain morning focus" instead of "i just need to stay focused in the mornings"

### Benefits

- **Consistency**: Concepts follow methodology conventions (e.g., JTBD uses job-statement phrasing)
- **Clarity**: Abstract labels are easier to connect in the graph
- **Analysis**: Canonical slot mapping works better with normalized language

---

## Cross-Turn Edge Resolution

By default, extracted edges could only reference concepts from the current turn because `label_to_node` only contained nodes extracted from the current response.

### The Problem

```
Turn 1: "I want to avoid sugar"
  → Extracted: ["avoid_sugar"] node

Turn 2: "It helps reduce inflammation"
  → Extracted: ["reduce_inflammation"] node
  → Edge: "avoid_sugar" → "reduce_inflammation"  # ❌ FAILED - "avoid_sugar" not in current turn
```

### The Solution

**Expand label_to_node with all session nodes**:

```python
# In graph_service.py:add_extraction_to_graph()
all_session_nodes = await self.repo.get_nodes_by_session(session_id)
for node in all_session_nodes:
    key = node.label.lower()
    if key not in label_to_node:  # Current-turn concepts take precedence
        label_to_node[key] = node
```

**Inject recent node labels into extraction context**:

```
[Existing graph concepts from previous turns]
  - "avoid_sugar"
  - "maintain_energy"

[Task] When creating relationships, reference these exact labels as source_text
or target_text to connect new concepts to existing ones. Do NOT re-extract these.
```

### Result

```
Turn 1: "I want to avoid sugar"
  → Extracted: ["avoid_sugar"] node

Turn 2: "It helps reduce inflammation"
  → Extracted: ["reduce_inflammation"] node
  → Edge: "avoid_sugar" → "reduce_inflammation"  # ✅ RESOLVED - "avoid_sugar" found in session nodes
```

---

## YAML Configuration Guide

### Minimal Configuration Example

```yaml
method:
  name: simple_methodology
  description: "Basic exploration methodology"

signals:
  graph:
    - graph.max_depth
  llm:
    - llm.engagement

strategies:
  - name: explore
    description: "Explore new topics"
    signal_weights:
      graph.max_depth: 1.0
```

### Complete Configuration Example

```yaml
method:
  name: means_end_chain
  description: "Laddering: attributes → consequences → values"

signals:
  graph:
    - graph.max_depth
    - graph.chain_completion
    - graph.canonical_exhaustion_score
  llm:
    - llm.response_depth
    - llm.specificity
    - llm.certainty
    - llm.valence
    - llm.engagement
  temporal:
    - temporal.strategy_repetition_count
    - llm.global_response_trend
  meta:
    - meta.interview.phase
    - meta.node.opportunity

phase_boundaries:
  early_max_turns: 4
  mid_max_turns: 12

strategies:
  - name: explore
    description: "Find new attributes/branches"
    signal_weights:
      llm.response_depth.shallow: 0.8    # Categorical match (not .low)
      llm.response_depth.surface: 0.5    # Even more brief = boost explore
      temporal.strategy_repetition_count: -0.5

  - name: deepen
    description: "Explore why something matters (laddering up)"
    signal_weights:
      llm.response_depth.shallow: 0.8    # Categorical match
      llm.response_depth.surface: 0.4    # Surface answers = opportunity to deepen
      graph.max_depth: -0.3
      # Engagement & valence safety checks
      llm.engagement.high: 0.7        # Engaged = safe to deepen
      llm.engagement.low: -0.5        # Disengaged = avoid deepening
      llm.valence.high: 0.4           # Positive emotion = safe to probe
      # Diversity
      temporal.strategy_repetition_count: -0.3
      # Node-level signals
      graph.node.exhaustion_score.low: 1.0
      graph.node.focus_streak.low: 0.5

  - name: clarify
    description: "Get more detail on vague responses"
    signal_weights:
      llm.specificity.low: 0.8        # Vague language = clarify
      llm.certainty.low: 0.5          # Uncertainty = clarify
      llm.engagement.mid: 0.3         # Moderate engagement = safe to clarify
      temporal.strategy_repetition_count: -0.3

  - name: bridge
    description: "Connect isolated concepts"
    signal_weights:
      graph.node.is_orphan.true: 1.0

  - name: reflect
    description: "Synthesize insights"
    signal_weights:
      meta.interview.phase.late: 1.0
      graph.chain_completion.high: 0.8
      llm.engagement.low: 0.6         # Low engagement = validate & wrap
      temporal.strategy_repetition_count: -0.2

phases:
  early:
    description: "Initial exploration phase"
    signal_weights:
      explore: 1.5
      clarify: 1.2
    phase_bonuses:
      explore: 0.2

  mid:
    description: "Deep exploration phase"
    signal_weights:
      deepen: 1.3
      bridge: 1.2
    phase_bonuses:
      deepen: 0.3

  late:
    description: "Synthesis phase"
    signal_weights:
      reflect: 1.2
    phase_bonuses:
      reflect: 0.2
```

---

## Tools and Debugging

### Viewing Signal Detection Logs

Signals are logged at `INFO` level during detection:

```python
# Example log output
logger.info(f"signals_detected: {signal_values}")
logger.info(f"interview_phase_detected: {phase}")
logger.info(f"phase_weights_loaded: {phase_weights}")
logger.info(f"phase_bonuses_loaded: {phase_bonuses}")
logger.info(f"strategies_ranked: {ranked}")
logger.info(f"strategy_selected: {strategy_name}")
```

### Enabling Debug Logging

```bash
# Run with debug logging
uvicorn src.main:app --reload --log-level debug
```

### Inspecting Strategy Selection

The `strategy_alternatives` field in `PipelineContext` contains all scored strategies:

```python
# Access in code or logs
context.strategy_alternatives = [
    (strategy_config, node_id, score),
    ...
]
```

### Available Methodologies

```bash
# List available methodology YAML files
ls config/methodologies/

# Example output:
# means_end_chain.yaml
# jobs_to_be_done.yaml
```

---

## Practical Examples

### Example 1: Understanding Strategy Selection

**Scenario**: Debug why `explore` was chosen over `deepen`.

**Check the logs for**:
```
signals_detected: {
    "graph.max_depth": 0.25,
    "llm.response_depth": 0.75,
    "temporal.strategy_repetition_count": 0.0,
    "meta.interview.phase": "early"
}
phase_weights_loaded: {"explore": 1.5, "deepen": 1.0}
strategies_ranked: [
    ("explore", None, 4.2),
    ("deepen", "node_3", 2.8)
]
strategy_selected: explore
```

**Analysis**: Early phase gives `explore` a 1.5x multiplier, boosting its score above `deepen`.

---

### Example 2: Adding a New Strategy

**Step 1**: Edit methodology YAML:
```yaml
strategies:
  - name: my_strategy
    description: "Custom questioning approach"
    signal_weights:
      llm.engagement.high: 1.0
      graph.max_depth: 0.5
```

**Step 2**: Test with simulation:
```bash
uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 10
```

**Step 3**: Check logs for `strategies_ranked` to see your strategy's score.

---

### Example 3: Phase-Based Strategy Promotion

**Goal**: Make `reflect` more likely in late phase.

```yaml
phases:
  late:
    signal_weights:
      reflect: 1.5        # 50% score boost
    phase_bonuses:
      reflect: 0.5        # +0.5 flat bonus

strategies:
  - name: reflect
    signal_weights:
      meta.interview.phase.late: 1.0  # Also activated by late phase
```

---

### Example 4: Penalizing Strategy Repetition

**Goal**: Avoid asking the same way repeatedly.

```yaml
strategies:
  - name: deepen
    signal_weights:
      llm.response_depth: 1.0
      temporal.strategy_repetition_count: -0.3  # Negative weight
```

Each time `deepen` is used consecutively, its score drops. The temporal signal is normalized [0,1] (e.g., 2 repetitions in a window of 5 = 0.4), so the penalty is `0.3 * 0.4 = 0.12`.

---

### Example 5: Node-Level Strategy Targeting

**Goal**: Target non-exhausted nodes with `deepen`.

```yaml
signals:
  graph:
    - graph.node.exhaustion_score

strategies:
  - name: deepen
    signal_weights:
      graph.node.exhaustion_score.low: 1.0  # Boost nodes with low exhaustion (score <= 0.25)
```

The D1 architecture will score each (deepen, node) pair, preferring nodes with low exhaustion scores.

---

## Troubleshooting

### Problem: Strategy never selected

**Symptoms**: Your strategy never appears in `strategies_ranked`.

**Check**:
1. Is the strategy defined in YAML under `strategies:`?
2. Are required signals declared in `signals:` section?
3. Check signal values - maybe conditions never match

**Debug**:
```python
# Add temporary debug logging
logger.info(f"All signals: {signals}")
logger.info(f"Strategy config: {strategy_config}")
```

---

### Problem: All similarity scores are unexpected

**Symptoms**: LLM signals returning unexpected values.

**Check**:
1. Enable debug logging to see raw LLM responses
2. Check `LLMBatchDetector` output in logs
3. Verify signal prompts in `src/signals/llm/`

---

### Problem: Phase detection not working

**Symptoms**: Always in `early` phase regardless of turn count.

**Check**:
1. Verify `phase_boundaries` in YAML:
   ```yaml
   phase_boundaries:
     early_max_turns: 4
     mid_max_turns: 12
   ```
2. Check `meta.interview.phase` signal is declared:
   ```yaml
   signals:
     meta:
       - meta.interview.phase
   ```
3. Check `turn_number` is available in pipeline context (dependency)

---

### Problem: Negative weights not penalizing

**Symptoms**: Strategy still selected despite negative weights.

**Check**:
1. Ensure other positive weights don't outweigh the negative
2. Check if signal value is actually being detected

---

### Problem: Node signals not affecting selection

**Symptoms**: Node-level signals seem ignored.

**Check**:
1. Verify `MethodologyStrategyService.select_strategy()` is using D1 scoring
2. Check `node_signals` are being passed to scoring function
3. Ensure node signal names match exactly (e.g., `graph.node.exhausted`)

---

## References

- **ADR-014**: Signal Pools Architecture (`docs/adr/ADR-014-signal-pools-architecture.md`)
- **Signal Base Class**: `src/signals/signal_base.py`
- **Signal Registry**: `src/signals/signal_registry.py`
- **Scoring Logic**: `src/methodologies/scoring.py`
- **Methodology Registry**: `src/methodologies/registry.py`
- **Strategy Service**: `src/services/methodology_strategy_service.py`
- **Global Signal Detection**: `src/services/global_signal_detection_service.py`
- **Node Signal Detection**: `src/services/node_signal_detection_service.py`
- **Strategy Selection Stage**: `src/services/turn_pipeline/stages/strategy_selection_stage.py`
- **Example Methodologies**: `config/methodologies/*.yaml`

---

## Quick Reference

### Signal Namespaces

| Prefix | Pool | Example |
|--------|------|---------|
| `graph.*` | Graph | `graph.node_count` |
| `llm.*` | LLM | `llm.response_depth` |
| `temporal.*` | Temporal | `temporal.strategy_repetition_count` |
| `meta.*` | Meta | `meta.interview.phase` |
| `graph.node.*` | Node (graph) | `graph.node.exhausted` |
| `technique.node.*` | Node (technique) | `technique.node.strategy_repetition` |

### Compound Key Patterns

| Pattern | Matches When |
|---------|--------------|
| `signal.name` | Signal value (pre-normalized at source [0,1]) |
| `signal.name.value` | Signal equals "value" (string enum match) |
| `signal.name.true` / `signal.name.false` | Boolean signal matches |
| `signal.name.high` | Numeric signal >= 0.75 |
| `signal.name.mid` | Numeric signal in (0.25, 0.75) exclusive |
| `signal.name.low` | Numeric signal <= 0.25 |
