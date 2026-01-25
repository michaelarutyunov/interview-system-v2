# Scoring System Architecture

Two-tier hybrid scoring for adaptive strategy selection in interviews.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Complete Selection Pipeline                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Load strategies from config/scoring.yaml                     │
│     ↓                                                             │
│  2. Determine phase (exploratory/focused/closing)                │
│     ↓                                                             │
│  3. Generate focus targets for each strategy                     │
│     - deepen → [recent_node]                                     │
│     - broaden → [open]                                           │
│     - bridge → [peripheral_node]                                 │
│     - cover_element → [uncovered_element_1, ...]                 │
│     ↓                                                             │
│  4. Create (strategy, focus) candidate pairs                      │
│     ↓                                                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  TIER 1: Hard Constraints (Veto Checks)                   │  │
│  │  - KnowledgeCeilingScorer: User lacks knowledge           │  │
│  │  - ElementExhaustedScorer: Element overmentioned          │  │
│  │  - RecentRedundancyScorer: Question repeated              │  │
│  │                                                            │  │
│  │  Output: is_veto (bool)                                    │  │
│  │  Rule: Any veto = candidate rejected (early exit)         │  │
│  │                                                            │  │
│  │  Key: Each scorer receives strategy/focus and can         │  │
│  │       conditionally veto based on strategy_id              │  │
│  └───────────────────────────────────────────────────────────┘  │
│         │                                                         │
│         ▼ (only if NO veto)                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  TIER 2: Weighted Additive Scoring                        │  │
│  │                                                            │  │
│  │  Each scorer returns raw_score in [0, 2]:                  │  │
│  │    0.0 = strongly discourage                               │  │
│  │    1.0 = neutral                                           │  │
│  │    2.0 = strongly encourage                                │  │
│  │                                                            │  │
│  │  scorer_sum = Σ(scorer_i.weight × scorer_i.raw_score)     │  │
│  └───────────────────────────────────────────────────────────┘  │
│         ↓                                                         │
│  final_score = scorer_sum × phase_multiplier                    │
│         ↓                                                         │
│  Select highest-scored non-vetoed candidate                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Candidate Generation

Before scoring, the system generates (strategy, focus) candidate pairs.

### Strategy Definitions

Strategies are defined in `config/scoring.yaml`:

```yaml
strategies:
  - id: deepen
    name: "Deepen Understanding"
    type_category: "depth"
    enabled: true
    prompt_hint: "Explore deeper into why this is important."
    priority_base: 1.0

  - id: broaden
    name: "Explore Breadth"
    type_category: "breadth"
    enabled: true
    prompt_hint: "Expand to related areas or perspectives."
    priority_base: 1.0

  - id: bridge
    name: "Lateral Bridge to Peripheral"
    type_category: "peripheral"
    enabled: true
    prompt_hint: "Link to what was just said, then shift to related area."
    priority_base: 0.8

  - id: synthesis
    name: "Summarise & Invite Extension"
    type_category: "transition"
    enabled: true
    prompt_hint: "Summarise what you've heard and invite correction."
    priority_base: 0.7

  - id: contrast
    name: "Counter-Example Exploration"
    type_category: "depth"
    enabled: true
    prompt_hint: "Consider the opposite case or a different perspective."
    priority_base: 0.8

  - id: ease
    name: "Simplify Question"
    type_category: "rapport"
    enabled: true
    prompt_hint: "Simplify the question and make it more conversational."
    priority_base: 0.5
```

### Focus Generation

For each strategy, the system generates 1+ focus targets:

| Strategy | Focus Generation | Example Output |
|----------|------------------|----------------|
| `deepen` | Most recent node | `[(focus_type="depth", node_id="node_123")]` |
| `broaden` | Open exploration | `[(focus_type="breadth", node_id=None)]` |
| `bridge` | Peripheral node (low degree) | `[(focus_type="lateral_bridge", node_id="node_45")]` |
| `synthesis` | Recent 2-3 nodes | `[(focus_type="synthesis", nodes=[...])]` |
| `cover_element` | Uncovered elements | `[(element="taste"), (element="texture")]` |
| `contrast` | Opposite stance node | `[(focus_type="counter_example", node_id="node_78")]` |

**Focus Schema:**
```python
Focus(
    focus_type: Literal[
        "depth_exploration",
        "breadth_exploration",
        "coverage_gap",
        "closing",
        "reflection",
        "lateral_bridge",      # NEW: For bridge strategy
        "counter_example",     # NEW: For contrast strategy
        "rapport_repair",      # NEW: For ease strategy
        "synthesis",           # NEW: For synthesis strategy
    ],
    node_id: Optional[str],
    element_id: Optional[str],
    focus_description: str,
    confidence: float,
)
```

### Candidate Pair Creation

```
For each strategy:
    For each focus:
        Create candidate(strategy, focus)
        Score through two-tier engine

Example:
    deepen + [recent_node] → 1 candidate
    broaden + [open] → 1 candidate
    cover_element + [taste, texture, packaging] → 3 candidates
    bridge + [peripheral_node] → 1 candidate
    synthesis + [recent_nodes] → 1 candidate

Total: 7 candidates to score
```

---

## Tier 1: Hard Constraints

**Purpose:** Reject candidates that MUST NOT be used.

**Characteristics:**
- Boolean output: `is_veto` (True/False)
- No weights, all vetoes equal
- Early exit on first veto
- Independent scorers, no cross-dependencies
- Each scorer receives `(strategy, focus)` and can veto selectively

**Existing Scorers:**

| Scorer | Veto Condition |
|--------|----------------|
| `KnowledgeCeilingScorer` | User signals "I don't know" |
| `ElementExhaustedScorer` | Element mentioned >N times |
| `RecentRedundancyScorer` | **Focus description** too similar to **recent actual questions** |

> **Important:** RecentRedundancyScorer compares the proposed `focus_description` (e.g., "Explore new aspects about oat milk") against **actual previously asked questions** from `conversation_history`. This prevents selecting a focus that would result in asking essentially the same question again. The actual question is generated later by the LLM based on the selected focus.

### Conditional Veto Example

A Tier 1 scorer can veto some strategies but not others:

```python
class HypotheticalExhaustionScorer(Tier1Scorer):
    async def evaluate(self, strategy, focus, ...) -> Tier1Output:
        is_exhausted = self._check_exhaustion(conversation_history)

        if is_exhausted:
            # Allow these strategies during exhaustion
            if strategy["id"] in ["reflection", "synthesis", "ease"]:
                return Tier1Output(is_veto=False, ...)

            # Veto other strategies
            return Tier1Output(is_veto=True, ...)

        return Tier1Output(is_veto=False, ...)
```

This means:
- `(broaden, open)` → **VETOED**
- `(synthesis, open)` → **PASSES**

---

## Tier 2: Weighted Additive Scoring

**Purpose:** Rank candidates by quality along multiple dimensions.

**Characteristics:**
- Score range: [0, 2] where 1.0 = neutral
- Weighted sum: each scorer has configurable weight
- Orthogonal dimensions (each scorer measures one thing)
- Phase multipliers adjust strategy preference by interview phase

**Formula:**

```
scorer_sum = Σ(weight_i × raw_score_i)  for all Tier 2 scorers

final_score = scorer_sum × phase_multiplier
```

**Existing Scorers:**

| Scorer | Dimension | Weight | Description |
|--------|-----------|--------|-------------|
| `CoverageGapScorer` | Uncovered elements | 0.20 | Boosts strategies covering unexplored elements |
| `AmbiguityScorer` | Response clarity | 0.15 | Boosts clarify strategy when responses are vague |
| `DepthBreadthBalanceScorer` | Depth vs breadth balance | 0.20 | Maintains exploration/exploitation balance |
| `EngagementScorer` | User momentum | 0.10 | Adapts strategy complexity to engagement level |
| `StrategyDiversityScorer` | Strategy variety | 0.15 | Penalizes repetitive strategy use |
| `NoveltyScorer` | Information freshness | 0.15 | Boosts strategies targeting newer nodes |
| `ClusterSaturationScorer` | Topic saturation | 0.15 | **NEW** Boosts synthesis when topics are saturated |
| `ContrastOpportunityScorer` | Opposite stance detection | 0.12 | **NEW** Boosts contrast when opposite stances exist |
| `PeripheralReadinessScorer` | Peripheral node availability | 0.12 | **NEW** Boosts bridge when peripheral nodes exist |

### Tier 2 Scorer Details

#### ClusterSaturationScorer (P1)
**Purpose:** Boosts synthesis strategy based on topic saturation level.

**Scoring Logic:**
- Uses Chao1 estimator to predict species richness
- `synthesis` + `saturation > 0.7` → score = 1.5 (strong boost)
- `synthesis` + `saturation > 0.4` → score = 1.2 (moderate boost)
- Otherwise → score = 1.0 (neutral)

**Signals:** `saturation_pct`, `predicted_species`, `is_saturated`

#### ContrastOpportunityScorer (P1)
**Purpose:** Boosts contrast strategy when opposite stance nodes exist.

**Scoring Logic:**
- `contrast` + `has_opposite` + `density > 0.6` → score = 1.5
- `contrast` + `has_opposite` → score = 1.2
- Otherwise → score = 1.0

**Signals:** `has_opposite_stance`, `local_cluster_density`, `opportunity_checked`

#### PeripheralReadinessScorer (P1)
**Purpose:** Boosts bridge strategy when peripheral nodes are available.

**Scoring Logic:**
- `bridge` + `peripheral_count >= 3` + `density > 0.5` → score = 1.5
- `bridge` + `peripheral_count >= 2` → score = 1.2
- Otherwise → score = 1.0

**Signals:** `peripheral_count`, `local_cluster_density`, `peripheral_checked`

---

## Phase Multipliers

Phase profiles boost/suppress strategies based on interview stage:

```yaml
# config/scoring.yaml
phase_profiles:
  exploratory:
    broaden: 1.2    # Boost breadth exploration
    deepen: 0.8     # Reduce deep diving
    bridge: 0.7     # Some bridging allowed
    closing: 0.0    # Disable closing

  focused:
    deepen: 1.3     # Boost deep exploration
    contrast: 1.2   # Introduce counter-examples
    bridge: 1.0     # Allow bridging
    closing: 0.5    # Allow some closing

  closing:
    closing: 1.5    # Strongly boost closing
    synthesis: 1.3  # Summarize findings
    broaden: 0.2    # Suppress breadth
```

---

## Phase System

Phases are determined by turn count (deterministic model):

```yaml
# config/interview_config.yaml
phases:
  exploratory:
    n_turns: 4   # Turns 0-3
  focused:
    n_turns: 6   # Turns 4-9
  closing:
    n_turns: 1   # Turn 10+
```

```python
def _determine_phase(turn_count: int) -> str:
    if turn_count < 4:
        return "exploratory"
    elif turn_count < 10:
        return "focused"
    else:
        return "closing"
```

**Key Point:** The phase system controls when strategies are preferred. No per-strategy `min_turns` gates needed.

---

## Complete Example

### Scenario

**Interview state:**
- Phase: `exploratory` (turn 3)
- Recent user responses: "I like coffee", "It helps me focus"
- Strategy history: ["broaden", "broaden", "broaden"]
- Current node count: 5
- Uncovered elements: ["taste", "texture"]

**Generated Candidates:**
1. `(deepen, node_coffee)` - deepen on most recent node
2. `(broaden, open)` - explore new aspects
3. `(bridge, peripheral_node)` - bridge to peripheral topic
4. `(cover_element, taste)` - cover taste element
5. `(cover_element, texture)` - cover texture element
6. `(synthesis, recent_nodes)` - summarize and extend

---

### Evaluating Candidate #2: `(broaden, open)`

**Tier 1:**
```
KnowledgeCeilingScorer → is_veto=False
ElementExhaustedScorer → is_veto=False
RecentRedundancyScorer → is_veto=False
```
✓ Passes Tier 1

**Tier 2:**
```
CoverageGapScorer        → raw=1.2, weight=0.20 → contrib=0.24
AmbiguityScorer          → raw=1.0, weight=0.15 → contrib=0.15
DepthBreadthBalance      → raw=0.6, weight=0.20 → contrib=0.12  (low breadth)
EngagementScorer         → raw=1.2, weight=0.10 → contrib=0.12
StrategyDiversityScorer  → raw=0.4, weight=0.15 → contrib=0.06  (broaden overused)
NoveltyScorer            → raw=1.0, weight=0.15 → contrib=0.15
ClusterSaturationScorer  → raw=1.0, weight=0.15 → contrib=0.15  (low saturation)
ContrastOpportunityScorer → raw=1.0, weight=0.12 → contrib=0.12  (no contrast)
PeripheralReadinessScorer → raw=1.0, weight=0.12 → contrib=0.12  (bridge not checked)

scorer_sum = 1.19
```

**Phase Multiplier:**
```
phase_multiplier = phase_profiles["exploratory"]["broaden"] = 1.2

final_score = 1.19 × 1.2 = 1.43
```

---

### Comparing All Candidates

| Strategy | Focus | Tier 1 | scorer_sum | phase_mult | final_score |
|----------|-------|--------|------------|------------|-------------|
| deepen | node_coffee | Pass | 0.85 | 0.8 | 0.68 |
| broaden | open | Pass | 1.19 | 1.2 | **1.43** ← Selected |
| bridge | peripheral_node | Pass | 0.95 | 0.7 | 0.67 |
| cover_element | taste | Pass | 1.10 | 1.1 | 1.21 |
| cover_element | texture | Pass | 1.10 | 1.1 | 1.21 |
| synthesis | recent_nodes | Pass | 0.95 | 0.3 | 0.29 |

**Winner:** `broaden` + `open` (highest final_score)

---

## Signal → Scorer → Score Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Raw Signal      │ ──▶ │ Scorer Logic    │ ──▶ │ Score/Decision   │
│                 │     │                 │     │                  │
│ - "nothing"     │     │ Pattern match   │     │ Tier 1: veto     │
│ - "don't know"  │     │ Counter check   │     │ Tier 2: 0.0-2.0  │
│ - turn_count    │     │ Threshold       │     │                  │
│ - history       │     │ Weighted sum    │     │                  │
└─────────────────┘     └─────────────────┘     └──────────────────┘
```

---

## LLM Qualitative Signal Extraction

The system uses LLM semantic understanding to extract qualitative signals that complement rule-based heuristics. This provides deeper insight into respondent engagement, reasoning quality, and knowledge state.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Three-Layer Signal Architecture               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Database Aggregations (GraphRepository)                │
│    → Node counts, edge patterns, cluster metrics                 │
│    → SQL-based, fast                                             │
│                                                                  │
│  Layer 2: Rule-based Helpers (signal_helpers.py)                 │
│    → get_recent_user_responses(), find_node_by_id()              │
│    → Pure functions, no LLM                                      │
│                                                                  │
│  Layer 3: LLM Semantic Extraction (llm_signals.py) ✓ IMPLEMENTED │
│    → QualitativeSignalExtractor with 6 signal types              │
│    → Nuanced understanding beyond pattern matching               │
│    → Integrated into StrategyService.select() pipeline           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Qualitative Signal Types

| Signal | Description | Use Case |
|--------|-------------|----------|
| `UncertaintySignal` | Distinguishes productive vs terminal uncertainty | KnowledgeCeilingScorer nuance |
| `ReasoningSignal` | Causal, counterfactual, metacognitive detection | EngagementScorer enhancement |
| `EmotionalSignal` | Engagement intensity and trajectory | Sentiment tracking, phase transitions |
| `ContradictionSignal` | Stance shifts and inconsistencies | Depth strategy adjustment |
| `KnowledgeCeilingSignal` | Terminal vs exploratory "don't know" | Selective deepen veto |
| `ConceptDepthSignal` | Abstraction level measurement | Deepen vs broaden selection |

### Sentiment Tracking

Sentiment values are extracted from `EmotionalSignal` intensity and stored in `graph_state.properties["turn_sentiments"]`:

```python
INTENSITY_TO_SENTIMENT = {
    "high_positive": 1.0,
    "moderate_positive": 0.5,
    "neutral": 0.0,
    "moderate_negative": -0.5,
    "high_negative": -1.0,
}
```

**Usage:**
- Sentiment is attached to conversation turns in `ContextLoadingStage`
- Available in conversation history for downstream scorers
- Used for engagement trajectory analysis

### Integration Pattern

Scorers can opt-in to use LLM signals:

```python
class AmbiguityScorer(Tier2Scorer):
    def __init__(self, config):
        super().__init__(config)
        self.use_llm_signals = self.params.get("use_llm_signals", True)

    async def score(self, strategy, focus, graph_state, ...):
        # Check for LLM signals in graph_state.properties
        if self.use_llm_signals:
            qualitative_signals = graph_state.properties.get("qualitative_signals")
            if qualitative_signals:
                # Use LLM signal for enhanced scoring
                reasoning_signal = qualitative_signals.get("reasoning")
                if reasoning_signal and reasoning_signal.get("reasoning_quality") == "causal":
                    # Boost score for causal reasoning
                    raw_score = 1.3
                    return self.make_output(raw_score=raw_score, ...)

        # Fall back to rule-based logic
        return self._score_rule_based(...)
```

### Enabling LLM Signals

LLM signals are automatically extracted by `StrategyService` during candidate scoring. To enable in individual scorers, set `use_llm_signals: true` in scorer config:

```yaml
# config/scoring.yaml
tier2_scorers:
  - id: ambiguity
    class: AmbiguityScorer
    enabled: true
    weight: 0.15
    params:
      use_llm_signals: true  # Enable LLM enhancement
      # ... other params
```

### Cost Considerations

- **LLM Model**: Uses light client (Haiku) for cost efficiency
- **Frequency**: Extract once per turn, shared across all scorers
- **Tokens**: ~1500 max output, ~1000 input (recent 10 turns)
- **Fallback**: Graceful degradation to rule-based if LLM fails

---

## Depth Measurement: MEC Chain Calculation

The system uses actual BFS traversal for depth measurement instead of edge density heuristics.

### Chain Depth Calculation

```python
def calculate_mec_chain_depth(edges: list, nodes: list, methodology: str) -> dict:
    """
    Performs BFS traversal from root nodes (attributes) to leaf nodes
    (terminal_values) to measure actual chain lengths.

    Returns:
        {
            "max_chain_length": 3.0,      # Longest root-to-leaf path
            "avg_chain_length": 2.1,      # Average of all root-to-leaf paths
            "chain_count": 15,            # Number of distinct chains
            "complete_chains": 12,        # Chains reaching terminal values
        }
    """
```

### Usage in DepthBreadthBalanceScorer

```python
def _calculate_depth(self, graph_state: GraphState, recent_nodes: List) -> float:
    # Try to use pre-computed chain depth from graph_state
    chain_depth = graph_state.properties.get("chain_depth")
    if chain_depth and isinstance(chain_depth, dict):
        avg_chain_length = chain_depth.get("avg_chain_length")
        if avg_chain_length is not None:
            return avg_chain_length

    # Fallback to edge density heuristic
    return self._estimate_depth_from_edges(graph_state)
```

### MEC Node Type Hierarchy

```
attribute → functional_consequence → psychosocial_consequence
         → instrumental_value → terminal_value
```

---

## Graph Utilities

### Simple Helper Functions (Preferred)

These functions work without full NetworkX graph reconstruction:

| Function | Purpose | Used By |
|----------|---------|---------|
| `get_simple_local_density()` | Cluster density approximation | ClusterSaturationScorer, PeripheralReadinessScorer |
| `has_opposite_stance_simple()` | Opposite stance detection | ContrastOpportunityScorer |
| `count_peripheral_nodes_simple()` | Peripheral node counting | PeripheralReadinessScorer |
| `calculate_mec_chain_depth()` | MEC depth via BFS | DepthBreadthBalanceScorer |

### Deprecated NetworkX Functions

> **DEPRECATED** (as of 2025-01-25): The following NetworkX-based functions are NOT currently used by any Tier-2 scorers. They were part of an earlier design phase but the implementation took a different path using simple heuristic functions.

Deprecated functions:
- `get_clusters()`
- `local_cluster_density()`
- `has_opposite_stance_node()`
- `cluster_size()`
- `median_cluster_degree()`
- `has_peripheral_candidates()`
- `largest_cluster_ratio()`
- `median_degree_inside()`
- Compatibility wrappers (`_` prefixed)

These functions are retained for potential future use but emit deprecation warnings if called.

---

## Adding a New Scorer

### Tier 1 (Veto)

```python
# src/services/scoring/tier1/my_scorer.py
class MyScorer(Tier1Scorer):
    async def evaluate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list,
        conversation_history: list[Dict[str, str]],
    ) -> Tier1Output:
        # Check veto condition
        if self._should_veto(strategy, conversation_history):
            return Tier1Output(
                scorer_id="MyScorer",
                is_veto=True,
                reasoning="...",
                signals={...}
            )
        return Tier1Output(is_veto=False, ...)
```

### Tier 2 (Weighted)

```python
# src/services/scoring/tier2/my_scorer.py
class MyScorer(Tier2Scorer):
    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list,
        conversation_history: list[Dict[str, str]],
    ) -> Tier2Output:
        raw_score = self._calculate_score(...)  # 0.0 to 2.0
        return self.make_output(
            raw_score=raw_score,
            signals={...},
            reasoning="..."
        )
```

**Config:**

```yaml
# config/scoring.yaml
tier1_scorers:
  - id: my_scorer
    class: MyScorer
    enabled: true
    params: {...}

tier2_scorers:
  - id: my_scorer
    class: MyScorer
    enabled: true
    weight: 0.10  # Adjust based on importance
    params: {...}
```

---

## Key Design Principles

1. **Tier 1 = Safety:** When in doubt, veto. Better to be conservative.
2. **Tier 2 = Quality:** Each scorer measures ONE dimension independently.
3. **Neutrality = 1.0:** Tier 2 scores around 1.0 indicate "no strong opinion"
4. **Phases = Strategy Modulation:** Phase multipliers adapt behavior per interview stage
5. **Debuggability:** Every score includes reasoning and signals for inspection
6. **Conditional Vetoes:** Tier 1 scorers can veto selectively based on strategy_id
7. **Simple Over Complex:** Prefer heuristic helpers over full graph reconstruction when possible
8. **LLM Enhancement:** Qualitative signals provide nuance but don't replace rule-based logic
