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
│  │             │  │engagement   │  │             │  │            │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
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

**Source**: LLM analysis of user response
**Cost**: High (1 API call per response, batched)
**Location**: `src/signals/llm/`

| Signal | Type | Scale | Description |
|--------|------|-------|-------------|
| `llm.response_depth` | float | 0.0-1.0 | Elaboration quantity |
| `llm.specificity` | float | 0.0-1.0 | Concreteness of language |
| `llm.certainty` | float | 0.0-1.0 | Epistemic confidence |
| `llm.valence` | float | 0.0-1.0 | Emotional tone (negative-positive) |
| `llm.engagement` | float | 0.0-1.0 | Willingness to engage |

**Scale Interpretation**:
```
0.0 = Very low / minimal / negative (was 1)
0.25 = Low / somewhat vague / uncertain (was 2)
0.5 = Moderate / neutral (was 3)
0.75 = High / fairly concrete / confident (was 4)
1.0 = Very high / detailed / positive / certain (was 5)
```

**Batch Detection**: All LLM signals are detected in a single API call:
```python
# One API call returns all signals:
{
    "llm.response_depth": 0.75,    # Detailed response (was 4)
    "llm.specificity": 0.5,        # Moderately concrete (was 3)
    "llm.certainty": 1.0,          # Very confident (was 5)
    "llm.valence": 0.75,           # Positive tone (was 4)
    "llm.engagement": 1.0          # Highly engaged (was 5)
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
| `meta.interview_progress` | float | 0.0-1.0 progress through interview |
| `meta.interview.phase` | str | `early`, `mid`, or `late` |
| `meta.node.opportunity` | str | `exhausted`, `probe_deeper`, or `fresh` |

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
| `graph.node.*` | Graph-derived per-node signals | exhausted, focus_streak, edge_count |
| `technique.node.*` | Technique-specific signals | strategy_repetition |

### Available Node Signals

| Signal | Type | Description |
|--------|------|-------------|
| `graph.node.exhausted` | bool | Binary exhaustion flag |
| `graph.node.exhaustion_score` | float | Continuous exhaustion 0.0-1.0 |
| `graph.node.yield_stagnation` | bool | No yield for 3+ turns |
| `graph.node.focus_streak` | str | `none`, `low`, `medium`, `high` |
| `graph.node.is_current_focus` | bool | Currently focused node |
| `graph.node.recency_score` | float | 0.0-1.0 recency |
| `graph.node.is_orphan` | bool | No connected edges |
| `graph.node.edge_count` | int | Total edges |
| `graph.node.has_outgoing` | bool | Has outgoing edges |
| `technique.node.strategy_repetition` | int | Times same strategy used on node |

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

#### 3. Threshold Binning
```yaml
signal_weights:
  llm.response_depth.high: 0.8   # True if value >= 0.75
  llm.response_depth.low: 0.3    # True if value <= 0.25
```
- `.high` matches values >= 0.75 (internally derived from Likert 4-5)
- `.low` matches values <= 0.25 (internally derived from Likert 1-2)

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
      llm.response_depth.low: 0.8
      temporal.strategy_repetition_count: -0.5

  - name: deepen
    description: "Explore why something matters (laddering up)"
    signal_weights:
      llm.response_depth.high: 0.8
      graph.max_depth: 0.5
      graph.node.exhausted.false: 1.0
      graph.node.focus_streak.low: 0.5

  - name: clarify
    description: "Get more detail on vague responses"
    signal_weights:
      llm.specificity.low: 1.0
      llm.certainty.low: 0.5

  - name: bridge
    description: "Connect isolated concepts"
    signal_weights:
      graph.node.is_orphan.true: 1.0

  - name: reflect
    description: "Synthesize insights"
    signal_weights:
      meta.interview.phase.late: 1.0
      graph.chain_completion.high: 0.8

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
    - graph.node.exhausted

strategies:
  - name: deepen
    signal_weights:
      graph.node.exhausted.false: 2.0  # High weight for non-exhausted nodes
```

The D1 architecture will score each (deepen, node) pair, preferring nodes where `exhausted=false`.

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
| `signal.name.value` | Signal equals "value" |
| `signal.name.high` | Numeric signal >= 0.75 |
| `signal.name.low` | Numeric signal <= 0.25 |
