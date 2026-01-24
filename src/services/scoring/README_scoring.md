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

  - id: broaden
    name: "Explore Breadth"
    type_category: "breadth"
    enabled: true
    prompt_hint: "Expand to related areas or perspectives."

  - id: bridge
    name: "Lateral Bridge to Peripheral"
    type_category: "peripheral"
    enabled: true
    prompt_hint: "Link to what was just said, then shift to related area."

  - id: synthesis
    name: "Summarise & Invite Extension"
    type_category: "transition"
    enabled: true
    prompt_hint: "Summarise what you've heard and invite correction."
```

### Focus Generation

For each strategy, the system generates 1+ focus targets:

| Strategy | Focus Generation | Example Output |
|----------|------------------|----------------|
| `deepen` | Most recent node | `[(focus_type="depth", node_id="node_123")]` |
| `broaden` | Open exploration | `[(focus_type="breadth", node_id=None)]` |
| `bridge` | Peripheral node (low degree) | `[(focus_type="peripheral", node_id="node_45")]` |
| `synthesis` | Recent 2-3 nodes | `[(focus_type="summary", nodes=[...])]` |
| `cover_element` | Uncovered elements | `[(element="taste"), (element="texture")]` |

**Focus Schema:**
```python
Focus(
    focus_type: str,           # Type of focus (depth, breadth, coverage, etc.)
    node_id: Optional[str],    # Target node (if applicable)
    element_id: Optional[str], # Target element (for coverage)
    focus_description: str,    # Human-readable description
    confidence: float,         # Confidence in this focus [0-1]
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
    synthesis + [recent_nodes] → 1 candidate

Total: 6 candidates to score
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

### How RecentRedundancyScorer Works

A common point of confusion: **it evaluates the focus_description, not a generated question.**

```
Timeline:
1. Focus generation creates: focus = {focus_description: "Explore new aspects about oat milk"}
2. RecentRedundancyScorer compares this to recent ACTUAL questions
3. If too similar → veto this candidate
4. If distinct → allow candidate to proceed to scoring
5. Later: LLM generates actual question based on selected focus
```

**Example:**

| focus_description | Compared to (actual recent questions) | Similarity | Result |
|-------------------|--------------------------------------|------------|--------|
| "Explore new aspects about oat milk" | "What else do you notice about oat milk?" | 0.92 | **VETO** |
| "Deepen: why coffee helps you focus" | "What else do you notice about oat milk?" | 0.15 | Pass |
| "Tell me more about the taste" | "What does oat milk taste like?" | 0.88 | **VETO** |

The scorer prevents selecting a focus that would result in asking essentially the same thing again, even if worded differently.

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

| Scorer | Dimension | Weight |
|--------|-----------|--------|
| `CoverageGapScorer` | Uncovered elements | 0.20 |
| `AmbiguityScorer` | Response clarity | 0.15 |
| `DepthBreadthBalanceScorer` | Depth vs breadth balance | 0.20 |
| `EngagementScorer` | User momentum | 0.15 |
| `StrategyDiversityScorer` | Strategy variety | 0.15 |
| `NoveltyScorer` | Information freshness | 0.15 |

---

## Phase Multipliers

Phase profiles boost/suppress strategies based on interview stage:

```yaml
# config/scoring.yaml
phase_profiles:
  exploratory:
    broaden: 1.2    # Boost breadth exploration
    deepen: 0.8     # Reduce deep diving
    closing: 0.0    # Disable closing

  focused:
    deepen: 1.3     # Boost deep exploration
    contrast: 1.2   # Introduce counter-examples
    closing: 0.5    # Allow some closing

  closing:
    closing: 1.5    # Strongly boost closing
    synthesis: 1.2  # Summarize findings
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
3. `(cover_element, taste)` - cover taste element
4. `(cover_element, texture)` - cover texture element
5. `(synthesis, recent_nodes)` - summarize and extend

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
CoverageGapScorer    → raw=1.2, weight=0.20 → contrib=0.24
AmbiguityScorer      → raw=1.0, weight=0.15 → contrib=0.15
DepthBreadthBalance  → raw=0.6, weight=0.20 → contrib=0.12  (low breadth)
EngagementScorer     → raw=1.2, weight=0.15 → contrib=0.18
StrategyDiversityScorer → raw=0.4, weight=0.15 → contrib=0.06  (broaden overused)
NoveltyScorer        → raw=1.0, weight=0.15 → contrib=0.15

scorer_sum = 0.90
```

**Phase Multiplier:**
```
phase_multiplier = phase_profiles["exploratory"]["broaden"] = 1.2

final_score = 0.90 × 1.2 = 1.08
```

---

### Comparing All Candidates

| Strategy | Focus | Tier 1 | scorer_sum | phase_mult | final_score |
|----------|-------|--------|------------|------------|-------------|
| deepen | node_coffee | Pass | 0.85 | 0.8 | 0.68 |
| broaden | open | Pass | 0.90 | 1.2 | **1.08** ← Selected |
| cover_element | taste | Pass | 1.10 | 1.1 | 1.21 |
| cover_element | texture | Pass | 1.10 | 1.1 | 1.21 |
| synthesis | recent_nodes | Pass | 0.95 | 0.3 | 0.29 |

**Winner:** `cover_element` + `taste` (highest final_score)

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

## LLM Qualitative Signal Extraction (Layer 3)

Layer 3 of the signal architecture uses LLM semantic understanding to extract
qualitative signals that complement rule-based heuristics. This provides deeper
insight into respondent engagement, reasoning quality, and knowledge state.

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
│  Layer 3: LLM Semantic Extraction (llm_signals.py) ★ NEW ★       │
│    → QualitativeSignalExtractor with 6 signal types              │
│    → Nuanced understanding beyond pattern matching               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Qualitative Signal Types

| Signal | Description | Use Case |
|--------|-------------|----------|
| `UncertaintySignal` | Distinguishes productive vs terminal uncertainty | KnowledgeCeilingScorer nuance |
| `ReasoningSignal` | Causal, counterfactual, metacognitive detection | EngagementScorer enhancement |
| `EmotionalSignal` | Engagement intensity and trajectory | Phase transitions |
| `ContradictionSignal` | Stance shifts and inconsistencies | Depth strategy adjustment |
| `KnowledgeCeilingSignal` | Terminal vs exploratory "don't know" | Selective deepen veto |
| `ConceptDepthSignal` | Abstraction level measurement | Deepen vs broaden selection |

### Integration Pattern

Scorers can opt-in to use LLM signals:

```python
class MyScorer(Tier1Scorer):
    def __init__(self, config):
        super().__init__(config)
        self.use_llm_signals = self.params.get("use_llm_signals", False)

    async def evaluate(self, strategy, focus, graph_state, ...):
        # Check for LLM signals in graph_state.properties
        if self.use_llm_signals:
            qualitative_signals = graph_state.properties.get("qualitative_signals")
            if qualitative_signals:
                # Use LLM signal for enhanced decision
                kc_signal = qualitative_signals.get("knowledge_ceiling")
                if kc_signal and kc_signal.get("is_terminal"):
                    return Tier1Output(is_veto=True, ...)

        # Fall back to rule-based logic
        return self._evaluate_rule_based(...)
```

### Enabling LLM Signals

1. **Configure StrategyService** to extract signals (future enhancement):

```python
# In StrategyService.__init__
from src.services.scoring.llm_signals import QualitativeSignalExtractor

self.signal_extractor = QualitativeSignalExtractor() if config.get(
    "use_llm_signals", False
) else None

# In StrategyService.select (before scoring loop)
if self.signal_extractor:
    signals = await self.signal_extractor.extract(
        conversation_history=conversation_history,
        turn_number=graph_state.turn_count,
    )
    # Store in graph_state for scorers to access
    graph_state.properties["qualitative_signals"] = signals.to_dict()
```

2. **Enable in scorer config** (`config/scoring.yaml`):

```yaml
tier1_scorers:
  - id: knowledge_ceiling
    class: KnowledgeCeilingScorer
    enabled: true
    params:
      use_llm_signals: true  # Enable LLM enhancement
      # ... other params
```

### Cost Considerations

- **LLM Model**: Uses light client (Haiku/GPT-4o-mini) for cost efficiency
- **Frequency**: Extract once per turn, consume across all scorers
- **Tokens**: ~1500 max output, ~1000 input (recent 10 turns)
- **Fallback**: Graceful degradation to rule-based if LLM fails

### Example: KnowledgeCeilingScorer Enhancement

The `KnowledgeCeilingScorer` demonstrates LLM integration:

```python
# Without LLM: Veto any "don't know" response
"I don't know about oat milk" → VETO deepen

# With LLM: Nuanced detection
"I don't know about oat milk, but I'm curious about..." → ALLOW deepen (exploratory)
"I don't know and I don't really care about milk" → VETO deepen (terminal)
```

---

## Current Implementation Issues

> ⚠️ **Known Issues** (as of 2025-01-24)

1. **Strategies Not Loaded from YAML**
   - YAML defines 9 strategies, but only 5 are used in code
   - `bridge`, `contrast`, `ease`, `synthesis` are configured but never evaluated
   - Must update both `config/scoring.yaml` AND `strategy_service.py` to add strategies

2. **Focus Generation Hardcoded**
   - `_get_possible_focuses()` is a big if-elif chain
   - Not configurable via YAML
   - No focus logic for the 4 unused strategies

3. **Redundant min_turns Gate**
   - `closing` strategy has `min_turns=8` check
   - But phase system already controls when closing is available
   - Creates inconsistency (phase says turn 10, min_turns says turn 8)

4. **Phase Profile Dead Code**
   - YAML sets multipliers for `bridge`, `contrast`, `ease`, `synthesis`
   - These are never applied because those strategies are never candidates

5. **LLM Signal Integration Incomplete** (as of 2025-01-24)
   - `QualitativeSignalExtractor` implemented and tested
   - `KnowledgeCeilingScorer` enhanced with opt-in LLM support
   - **Missing**: StrategyService integration to extract signals before scoring
   - **Missing**: Config flag to enable LLM signals globally
   - **Current**: Scorers can use signals but no pipeline step extracts them

**Integration TODO:**
```python
# In StrategyService.select() before scoring loop:
if self.signal_extractor:
    signals = await self.signal_extractor.extract(
        conversation_history=conversation_history,
        turn_number=graph_state.turn_count,
    )
    graph_state.properties["qualitative_signals"] = signals.to_dict()
```
   - These are never applied because those strategies are never candidates

**Ideal State:**
- Strategies loaded from YAML only
- Focus generation declarative (config-driven) or extensible
- Phase system as single source for strategy availability
- Adding strategy = YAML entry only (for simple cases)

---

## Key Design Principles

1. **Tier 1 = Safety:** When in doubt, veto. Better to be conservative.
2. **Tier 2 = Quality:** Each scorer measures ONE dimension independently.
3. **Neutrality = 1.0:** Tier 2 scores around 1.0 indicate "no strong opinion"
4. **Phases = Strategy Modulation:** Phase multipliers adapt behavior per interview stage
5. **Debuggability:** Every score includes reasoning and signals for inspection
6. **Conditional Vetoes:** Tier 1 scorers can veto selectively based on strategy_id
