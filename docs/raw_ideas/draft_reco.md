# Implementation Proposal: Enhanced Scoring & Strategy System

## Executive Summary

This document proposes a coherent implementation of the enhanced scorer and strategy system, building on the existing `TwoTierScoringEngine` architecture. The proposal adds 4 new strategies and 3 new Tier-2 scorers while maintaining backward compatibility.

`★ Insight ─────────────────────────────────────`
**The existing two-tier architecture is already well-designed**: Tier-1 provides hard vetoes (boolean), Tier-2 provides weighted additive scoring (0-2 range). The research maps cleanly onto this: the "Tier-1 table" in strategies.md corresponds to veto conditions, while the scoring formulas correspond to Tier-2 weights. We don't need to reinvent the wheel—we extend what exists.
`─────────────────────────────────────────────────`

---

## Final Decisions Summary

### Scoring Formula
The final scoring formula is:
```
scorer_sum = Σ(strategy_weight × raw_score)
final_score = scorer_sum × phase_multiplier
```

Where:
- `strategy_weight`: Per-scorer, per-strategy weight from config (e.g., CoverageGap × deepen = 0.30)
- `raw_score`: Scorer's raw output (0-2 range, 1.0 = neutral)
- `phase_multiplier`: Phase-specific modifier for this strategy (e.g., deepen in exploratory = 0.8)

### Configuration Structure
- **Strategies**: No `priority_base`, no `min_turns` - removed for simplicity
- **Scorers**: No `base_weight` - all use direct `strategy_weights` only
- **Modes**: Three phases - `exploratory`, `focused`, `closing`
- **LLM Usage**: Deterministic scorers preferred; LLM only for keyword/natural language tasks (AmbiguityScorer)
- **Heuristics**: Minimized - use band-based thresholds (e.g., if density > 0.7: score = 1.5)

### New Components
- **Strategies**: `bridge`, `contrast`, `ease`, `synthesis`
- **Scorers**: `PeripheralReadinessScorer`, `ContrastOpportunityScorer`, `ClusterSaturationScorer`
- **Graph Utils**: Cluster analysis utilities for all scorers

---

## Part 1: New Strategies to Add

### Current Strategies (in config/scoring.yaml)
- `deepen` (depth)
- `broaden` (breadth)
- `cover_element` (coverage)
- `closing` (closing)
- `reflection` (reflection)

### New Strategies to Add

| Strategy ID | Name | Type Category |
|-------------|------|---------------|
| `bridge` | Lateral Bridge to Peripheral | peripheral |
| `contrast` | Introduce Counter-Example | contrast |
| `ease` | Ease / Rapport Repair | interaction |
| `synthesis` | Summarise & Invite Extension | transition |

### YAML Configuration Addition

Add to `config/scoring.yaml` strategies section:

```yaml
strategies:
  # ... existing strategies ...

  - id: bridge
    name: Lateral Bridge to Peripheral
    type_category: peripheral
    enabled: true
    prompt_hint: "Explicitly link to what was just said, then gently shift to a related but distinct area."

  - id: contrast
    name: Introduce Counter-Example
    type_category: contrast
    enabled: true
    prompt_hint: "Politely introduce a counter-example or opposite case to test boundaries."

  - id: ease
    name: Ease / Rapport Repair
    type_category: interaction
    enabled: true
    prompt_hint: "Simplify or soften the question, encourage participation."

  - id: synthesis
    name: Summarise & Invite Extension
    type_category: transition
    enabled: true
    prompt_hint: "Briefly summarise what you've heard and invite correction or addition."
```

---

## Part 2: New Tier-2 Scorers

### Current Tier-2 Scorers
- `CoverageGapScorer` (0.20)
- `DepthBreadthBalanceScorer` (0.20)
- `AmbiguityScorer` (0.15)
- `EngagementScorer` (0.15)
- `StrategyDiversityScorer` (0.15)
- `NoveltyScorer` (0.15)

### New Tier-2 Scorers to Add

| Scorer | Weight | Purpose | Signals Needed |
|--------|--------|---------|----------------|
| `PeripheralReadinessScorer` | 0.15 | Detect when lateral bridging is optimal | Cluster density, peripheral candidate count |
| `ContrastOpportunityScorer` | 0.15 | Detect when counter-example is available | Opposite stance nodes, cluster coherence |
| `ClusterSaturationScorer` | 0.10 | Detect when topic is complete | Cluster density, sentiment variance |

**Total Tier-2 Weight After Addition:** 0.95 (5% buffer for future additions)

---

## Part 3: Scorer Implementation Details

### 3.1 PeripheralReadinessScorer

**Purpose:** Score strategies based on readiness for lateral movement to peripheral but related topics.

**Signals:**
- `local_cluster_density`: Density of current focus cluster (0-1)
- `peripheral_candidate_count`: Number of unvisited nodes within 2-3 hops
- `turns_since_last_jump`: How long since we moved to a new cluster

**Scoring Logic (Band-Based):**
```python
if strategy.id == "bridge":
    # High confidence: cluster saturated AND peripherals exist
    if local_cluster_density > 0.7 and peripheral_candidate_count >= 3:
        raw_score = 1.5
    # Moderate boost: one condition met
    elif local_cluster_density > 0.5 or peripheral_candidate_count >= 1:
        raw_score = 1.2
    else:
        raw_score = 1.0
else:
    raw_score = 1.0  # Neutral for non-bridge strategies

return clamp(0.5, 1.8, raw_score)
```

**Implementation Location:** `src/services/scoring/two_tier/tier2/peripheral_readiness.py`

---

### 3.2 ContrastOpportunityScorer

**Purpose:** Score strategies based on availability of opposite-stance nodes and cluster coherence.

**Signals:**
- `has_opposite_stance`: Boolean, exists node with stance = -focus.stance
- `local_cluster_density`: Density of current cluster (0-1)
- `cluster_balance`: Ratio of largest to total clusters (0-1)

**Scoring Logic (Band-Based):**
```python
if strategy.id == "contrast" and has_opposite_stance:
    # High confidence: opposite exists AND cluster is coherent
    if local_cluster_density > 0.6:
        raw_score = 1.5
    # Moderate boost: opposite exists but cluster less coherent
    else:
        raw_score = 1.2
else:
    raw_score = 1.0

return clamp(0.5, 1.5, raw_score)
```

**Requires:** Node `stance` attribute (+1, 0, -1) added at stimulus ingestion.

**Implementation Location:** `src/services/scoring/two_tier/tier2/contrast_opportunity.py`

---

### 3.3 ClusterSaturationScorer

**Purpose:** Score strategies based on how complete the current topical cluster is.

**Signals:**
- `local_cluster_density`: Density of current cluster (0-1)
- `median_cluster_degree`: Median degree within cluster
- `cluster_node_count`: Size of current cluster

**Scoring Logic (Band-Based):**
```python
# Saturation = density * degree (proxy for completeness)
saturation = min(1.0, local_cluster_density * median_cluster_degree / 3)

if strategy.id == "synthesis":
    # Boost when cluster is saturated
    if saturation > 0.7:
        raw_score = 1.5
    elif saturation > 0.4:
        raw_score = 1.2
    else:
        raw_score = 1.0
else:
    raw_score = 1.0

return clamp(0.5, 1.6, raw_score)
```

**Implementation Location:** `src/services/scoring/two_tier/tier2/cluster_saturation.py`

---

## Part 4: Enhanced Existing Scorers

### 4.1 AmbiguityScorer Enhancement (LLM-Based)

**Current:** Returns raw score based on ambiguity signals.

**Enhancement:** Use LLM-based ambiguity detection instead of hardcoded keywords.

```python
class AmbiguityScorer(Tier2Scorer):
    async def score(self, strategy, focus, graph_state, recent_nodes, conversation_history):
        # Get recent respondent text
        recent_text = self._get_recent_respondent_text(conversation_history, turns=2)

        if not recent_text:
            return self.make_output(raw_score=1.0, reasoning="No recent text to analyze")

        prompt = f"""Analyze this interview response for linguistic ambiguity and uncertainty.

Response text: "{recent_text}"

Evaluate:
1. **Hedge words**: Does the respondent use qualifying language (maybe, sort of, might)?
2. **Uncertainty markers**: Explicit expressions of not knowing (not sure, unclear)?
3. **Extraction confidence**: Would you be confident extracting a clear claim from this?

Rate AMBIGUITY from 0.0 (crystal clear) to 1.0 (very ambiguous).

Return JSON: {{"ambiguity": float, "reasoning": str}}
"""

        try:
            response = await self.llm_light.call(prompt, response_format="json")
            ambiguity = response['ambiguity']

            # Convert to score: higher ambiguity = boost for clarify strategy
            if ambiguity < 0.2:
                raw_score = 0.9  # Clear, no clarification needed
            elif ambiguity < 0.5:
                raw_score = 1.2  # Mild ambiguity
            else:
                raw_score = 1.5  # High ambiguity

            signals = {'ambiguity': ambiguity}
            return self.make_output(
                raw_score=raw_score,
                signals=signals,
                reasoning=response['reasoning']
            )

        except Exception as e:
            logger.warning(f"LLM ambiguity detection failed: {e}")
            return self.make_output(raw_score=1.0, reasoning="LLM call failed, using neutral")
```

**Benefits:**
- No hardcoded keyword lists to maintain
- Handles edge cases like sarcasm, complex phrasing
- Provides explainable reasoning

**Configuration:** Requires two LLM clients in config.yaml:
```yaml
llm:
  main: {provider: "anthropic", model: "claude-sonnet-4-20250514"}
  light: {provider: "anthropic", model: "claude-haiku-4-20250514"}
```

AmbiguityScorer uses `llm_light` for scoring tasks.

---

### 4.2 CoverageGapScorer Enhancement

**Current:** Returns score based on gap count.

**Enhancement:** Distinguish gap types per research:

```python
# Gap types:
# - unmentioned: Element never referenced
# - no_reaction: Element mentioned but no respondent elaboration
# - no_comprehension: Low clarity on element discussion
# - unconnected: Element has degree 0 in respondent subgraph

# Track which elements have which gap types
gaps_by_element = self._analyze_coverage_gaps(graph_state, conversation_history)

# For the focus element, count its active gaps
focus_gaps = gaps_by_element.get(focus_element_id, [])

# Score based on gap count (same bands as current)
gap_count = len(focus_gaps)
if gap_count == 0:
    raw_score = 0.8
elif gap_count <= 2:
    raw_score = 1.2
else:
    raw_score = 1.5

signals = {
    'gap_count': gap_count,
    'gap_types': focus_gaps
}
```

---

## Part 5: Graph Utilities Module

Create `src/services/scoring/graph_utils.py`:

```python
"""Graph analysis utilities for Tier-2 scorers.

These functions provide O(1) or O(log n) lookups for cluster-level metrics.
Clusters are computed via Louvain algorithm and cached per turn.
"""

from typing import Dict, Optional, Tuple
import networkx as nx
from collections import defaultdict

# Cache for cluster assignments
_cluster_cache: Dict[int, Dict[str, int]] = {}  # turn -> node_id -> cluster_id


def get_clusters(graph: nx.Graph, turn_number: int) -> Dict[str, int]:
    """Get Louvain cluster assignments for all nodes.

    Results are cached per turn. Cache invalidates on turn change.
    """
    if turn_number in _cluster_cache:
        return _cluster_cache[turn_number]

    # Use python-louvain for community detection
    import community as community_louvain
    partition = community_louvain.best_partition(graph)

    _cluster_cache[turn_number] = partition
    return partition


def get_cluster_nodes(
    focus_node: str,
    clusters: Dict[str, int]
) -> set:
    """Get all nodes in the same cluster as focus_node."""
    focus_cluster = clusters.get(focus_node)
    if focus_cluster is None:
        return {focus_node}
    return {node for node, cid in clusters.items() if cid == focus_cluster}


def local_cluster_density(
    focus_node: str,
    graph: nx.Graph,
    clusters: Optional[Dict[str, int]] = None
) -> float:
    """Density of the cluster containing focus_node.

    Returns: 2 * |E| / (|V| * (|V| - 1))
    Returns 0.0 for single-node clusters.
    """
    if clusters is None:
        clusters = get_clusters(graph, -1)  # No caching

    nodes = get_cluster_nodes(focus_node, clusters)
    n = len(nodes)

    if n <= 1:
        return 0.0

    # Count internal edges
    subgraph = graph.subgraph(nodes)
    e = subgraph.number_of_edges()

    return 2 * e / (n * (n - 1))


def cluster_size(
    focus_node: str,
    clusters: Dict[str, int]
) -> int:
    """Number of nodes in the cluster containing focus_node."""
    return len(get_cluster_nodes(focus_node, clusters))


def largest_cluster_ratio(
    graph: nx.Graph,
    clusters: Dict[str, int]
) -> float:
    """Size of largest cluster / total nodes."""
    if not clusters:
        return 1.0

    cluster_sizes = defaultdict(int)
    for node, cid in clusters.items():
        cluster_sizes[cid] += 1

    max_size = max(cluster_sizes.values()) if cluster_sizes else 0
    return max_size / len(clusters)


def has_peripheral_candidates(
    focus_node: str,
    graph: nx.Graph,
    clusters: Dict[str, int],
    max_hops: int = 2
) -> Tuple[int, float]:
    """Count unvisited nodes within max_hops of focus_node's cluster.

    Returns: (candidate_count, max_relevance)
    """
    focus_cluster = clusters.get(focus_node)
    cluster_nodes = get_cluster_nodes(focus_node, clusters)

    # Find nodes within max_hops
    candidates = set()
    for node in cluster_nodes:
        # BFS outward
        for _, neighbor, data in graph.edges(node, data=True):
            if clusters.get(neighbor) != focus_cluster:
                # Add relevance score if available
                relevance = data.get('relevance', 0.5)
                candidates.add((neighbor, relevance))

    # Filter by relevance threshold
    min_relevance = 0.3
    valid = [(n, r) for n, r in candidates if r >= min_relevance]

    return len(valid), max([r for _, r in valid], default=0.0)


def has_opposite_stance_node(
    focus_node: str,
    graph: nx.Graph,
    clusters: Optional[Dict[str, int]] = None
) -> bool:
    """Check if any node has opposite stance to focus_node.

    Returns True if exists node where stance == -focus.stance
    Neutral nodes (stance == 0) are ignored.
    """
    focus_stance = graph.nodes.get(focus_node, {}).get('stance', 0)

    # Neutral focus has no opposite
    if focus_stance == 0:
        return False

    target_stance = -focus_stance

    for node, data in graph.nodes(data=True):
        node_stance = data.get('stance', 0)
        if node_stance == target_stance:
            return True

    return False


def median_cluster_degree(
    focus_node: str,
    graph: nx.Graph,
    clusters: Dict[str, int]
) -> float:
    """Median degree of nodes in focus_node's cluster."""
    nodes = get_cluster_nodes(focus_node, clusters)

    degrees = [graph.degree(n) for n in nodes]
    if not degrees:
        return 0.0

    degrees.sort()
    n = len(degrees)
    if n % 2 == 0:
        return (degrees[n//2 - 1] + degrees[n//2]) / 2
    else:
        return degrees[n//2]


def clear_cluster_cache():
    """Clear the cluster cache (call at start of new turn)."""
    _cluster_cache.clear()
```

---

## Part 6: Strategy-Scorer Weight Matrix

Per the research (strat-scoring.md), each scorer has different importance per strategy. Implement as configuration:

### YAML Structure (Clean, No base_weight)

```yaml
# In config/scoring.yaml

tier2_scorers:
  coverage_gap:
    enabled: true
    strategy_weights:
      deepen: 0.30      # Direct weight
      broaden: 0.24
      cover_element: 0.30
      synthesis: 0.22
      closing: 0.26
      bridge: 0.16
      contrast: 0.18
      ease: 0.14
      reflection: 0.12
      default: 0.20

  ambiguity:
    enabled: true
    strategy_weights:
      clarify: 0.30
      deepen: 0.28
      bridge: 0.14
      synthesis: 0.14
      default: 0.15

  # ... similar for other scorers
```

### Engine Implementation

**`src/services/scoring/two_tier/engine.py` — `TwoTierScoringEngine.score_candidate()`**

```python
# In TwoTierScoringEngine

async def score_candidate(self, strategy, focus, graph_state, recent_nodes, conversation_history, phase="exploratory"):
    # 1. Run all Tier-1 vetoes
    tier1_results = await self._run_tier1_scorers(...)
    if any(r.is_veto for r in tier1_results):
        return ScoringResult(vetoed=True, tier1_results=tier1_results)

    # 2. Run all Tier-2 scorers (each returns raw_score 0-2)
    tier2_results = []
    scorer_sum = 0.0

    for scorer in self.tier2_scorers:
        # Get strategy-specific weight (no base_weight, all start at 1.0)
        strategy_weight = scorer.config.get('strategy_weights', {}).get(
            strategy['id'],
            scorer.config.get('strategy_weights', {}).get('default', 0.1)
        )

        # Scorer returns raw score (independent of weights)
        result = await scorer.score(strategy, focus, graph_state, recent_nodes, conversation_history)

        # Apply only strategy_weight
        contribution = strategy_weight * result.raw_score
        scorer_sum += contribution

        # Store for debugging/analysis
        result.strategy_weight = strategy_weight
        result.weighted_contribution = contribution
        tier2_results.append(result)

    # 3. Apply phase multiplier AFTER summing all scorers
    phase_multiplier = self.phase_profiles.get(phase, {}).get(strategy['id'], 1.0)
    final_score = scorer_sum * phase_multiplier

    return ScoringResult(
        total_score=final_score,
        scorer_sum=scorer_sum,
        phase_multiplier=phase_multiplier,
        tier1_results=tier1_results,
        tier2_results=tier2_results
    )
```

**Example Calculation:**

```
Strategy: deepen
Phase: exploratory (phase_multiplier = 0.8)

Scorers:
- CoverageGap: strategy_weight=0.30, raw_score=1.5 → contribution=0.45
- Ambiguity:   strategy_weight=0.28, raw_score=1.2 → contribution=0.34
- Novelty:     strategy_weight=0.15, raw_score=0.8 → contribution=0.12

scorer_sum = 0.45 + 0.34 + 0.12 = 0.91
final_score = 0.91 × 0.8 = 0.73
```

---

## Part 7: Phase Profiles (Three Modes)

### Phase Configuration

```yaml
phase_config:
  exploratory:
    min_turns: 8      # Stay in exploratory for at least 8 turns
    max_turns: 20     # Force transition to focused after 20 turns

  focused:
    min_turns: 5      # Stay in focused for at least 5 turns
    max_turns: null   # No max, can stay focused indefinitely

  closing:
    min_turns: 15     # Can start closing after turn 15
    trigger_coverage: 0.95  # Or when 95% coverage achieved

phase_profiles:
  exploratory:
    deepen: 0.8
    broaden: 1.2
    cover_element: 1.1
    bridge: 0.2
    contrast: 0.0
    synthesis: 0.3
    closing: 0.0
    ease: 1.0
    reflection: 0.3

  focused:
    deepen: 1.3
    broaden: 0.4
    cover_element: 1.1
    bridge: 1.0
    contrast: 1.2
    synthesis: 0.7
    closing: 0.3
    ease: 1.0
    reflection: 0.7

  closing:
    deepen: 0.3
    broaden: 0.2
    cover_element: 0.5
    bridge: 0.3
    contrast: 0.5
    synthesis: 1.2
    closing: 1.5
    ease: 1.0
    reflection: 0.3
```

### Implementation

**1. Data Model Addition (in GraphState):**

```python
@dataclass
class GraphState:
    # ... existing fields ...
    properties: Dict[str, Any]

    @property
    def phase(self) -> str:
        """Get current interview phase."""
        return self.properties.get('phase', 'exploratory')

    def set_phase(self, phase: str):
        """Transition to a new phase."""
        self.properties['phase'] = phase
        logger.info(f"Phase transition: {self.phase} -> {phase}")
```

**2. Phase Transition Logic (in StrategyService):**

```python
class StrategyService:
    def _determine_phase(self, graph_state: GraphState) -> str:
        """Determine interview phase based on state."""
        turn_count = graph_state.properties.get('turn_count', 0)
        coverage_ratio = self._get_coverage_ratio(graph_state)

        # Phase transition rules
        if turn_count < self.config.get('exploratory_min_turns', 8):
            return 'exploratory'
        elif coverage_ratio > self.config.get('closing_coverage_threshold', 0.95):
            return 'closing'
        elif turn_count >= self.config.get('exploratory_min_turns', 8):
            return 'focused'
        else:
            return 'exploratory'  # Default

    async def select(self, graph_state, ...):
        # Determine phase before scoring
        phase = self._determine_phase(graph_state)
        graph_state.set_phase(phase)

        # Pass phase to scoring engine
        result = await self.scoring_engine.score_candidate(
            strategy=strategy,
            focus=focus,
            graph_state=graph_state,
            phase=phase,
            ...
        )
```

**3. Updated Engine Signature:**

```python
async def score_candidate(
    self,
    strategy,
    focus,
    graph_state,
    recent_nodes,
    conversation_history,
    phase: str = None
):
    if phase is None:
        phase = graph_state.phase  # Default from state

    # Use phase in weight calculation
    phase_multiplier = self.phase_profiles.get(phase, {}).get(strategy['id'], 1.0)
    ...
```

---

## Part 8: Data Model Changes

### 8.1 Add `stance` to Nodes

Stimulus ingestion should add:

```python
# In stimulus/parsing module
node_data = {
    'id': element_id,
    'text': element_text,
    'type': element_type,
    'stance': element_data.get('stance', 0),  # +1, 0, or -1
    # ... other fields
}
```

### 8.2 Add `extraction_confidence` to Nodes

```python
node_data['extraction_confidence'] = confidence_score  # 0-1 from NLP
```

### 8.3 Turn Counting and Phase Transitions

Turn counting happens at the **session level** in SessionService:

**1. Add turn_count to GraphState:**

```python
# In GraphState
@dataclass
class GraphState:
    properties: Dict[str, Any]

    @property
    def turn_count(self) -> int:
        return self.properties.get('turn_count', 0)

    def increment_turn(self):
        self.properties['turn_count'] = self.turn_count + 1
```

**2. Increment in SessionService:**

```python
# In src/services/session_service.py

class SessionService:
    async def process_turn(self, session_id: str, respondent_answer: str) -> str:
        session = await self.get_session(session_id)

        # 1. Add respondent turn to conversation history
        session.conversation_history.append({
            'speaker': 'respondent',
            'text': respondent_answer,
            'sentiment': await self._get_sentiment(respondent_answer),
            'timestamp': datetime.now()
        })

        # 2. Select strategy and generate question
        strategy_result = await self.strategy_service.select(...)
        question = await self.generate_question(strategy_result)

        # 3. Add interviewer turn to history
        session.conversation_history.append({
            'speaker': 'interviewer',
            'text': question,
            'timestamp': datetime.now()
        })

        # 4. Increment turn count AFTER both parts complete
        session.graph_state.increment_turn()

        # 5. Check phase transition
        new_phase = self.strategy_service._determine_phase(session.graph_state)
        if new_phase != session.graph_state.phase:
            session.graph_state.set_phase(new_phase)
            logger.info(f"Turn {session.graph_state.turn_count}: Phase -> {new_phase}")

        return question

    async def start_session(self, session_id: str, stimulus: dict):
        # Initial greeting/intro does NOT count as a turn
        greeting = self._generate_greeting(stimulus)

        session.conversation_history.append({
            'speaker': 'interviewer',
            'text': greeting,
            'timestamp': datetime.now()
        })

        # turn_count starts at 0, will increment to 1 after first respondent answer
        return greeting
```

**Key Design Decisions:**
- **Turn = complete exchange** (respondent answer + interviewer question)
- **Intro doesn't count** - turn_count increments after first respondent answer
- **Phase transitions happen in SessionService** after each complete turn
- **Three phases**: exploratory → focused → closing

---

## Part 9: Implementation Checklist

### Phase 1: Foundation (Priority 1)
- [ ] Create `src/services/scoring/graph_utils.py`
- [ ] Add `stance` attribute to stimulus nodes
- [ ] Add `extraction_confidence` to nodes (NLP pipeline)
- [ ] Add `sentiment` to turns (API integration)
- [ ] Add new strategies to `config/scoring.yaml`
- [ ] Update `TIER2_SCORER_CLASSES` in `config.py`

### Phase 2: New Scorers (Priority 1)
- [ ] Implement `PeripheralReadinessScorer` (band-based)
- [ ] Implement `ContrastOpportunityScorer` (band-based)
- [ ] Implement `ClusterSaturationScorer` (band-based)
- [ ] Add to configuration with appropriate weights

### Phase 3: Enhanced Scorers (Priority 2)
- [ ] Enhance `AmbiguityScorer` with LLM-based detection
- [ ] Configure `llm_light` client for scoring tasks
- [ ] Enhance `CoverageGapScorer` with gap types
- [ ] Update existing scorer weights if needed

### Phase 4: Strategy Profiles (Priority 3)
- [ ] Implement strategy-scorer weight matrix (no base_weight)
- [ ] Update `TwoTierScoringEngine` to use final formula
- [ ] Add tests for weighted scoring

### Phase 5: Phase System (Priority 4)
- [ ] Define phase transitions in `StrategyService`
- [ ] Add phase profiles to configuration (3 modes)
- [ ] Integrate phase multiplier into scoring
- [ ] Add turn counting to SessionService

---

## Part 10: Testing Strategy

### Unit Tests per Scorer
```python
# tests/scoring/test_peripheral_readiness.py
async def test_high_density_with_peripherals_boosts():
    """Dense cluster + many peripherals = high score."""
    ...

async def test_sparse_cluster_no_peripherals_neutral():
    """Sparse cluster + no peripherals = neutral score."""
    ...

async def test_bridge_strategy_gets_boost():
    """Bridge strategy gets highest boost."""
    ...
```

### Integration Tests
```python
# tests/scoring/test_two_tier_integration.py
async def test_bridge_strategy_selected_when_ripe():
    """When cluster saturated + peripherals exist, bridge is selected."""
    ...

async def test_synthesis_selected_when_saturated():
    """When cluster complete, synthesis is selected."""
    ...

async def test_phase_transitions_work():
    """Test exploratory → focused → closing transitions."""
    ...
```

---

## Part 11: Migration Strategy

### Backward Compatibility
1. All existing scorers remain functional
2. New scorers default to `enabled: false` initially
3. Gradually enable new scorers and monitor behavior
4. Existing strategies work without modification

### Rollout Plan
1. **Week 1:** Implement graph utils and data model changes
2. **Week 2:** Implement new scorers (band-based), keep disabled
3. **Week 3:** Add new strategies, test with existing scorers
4. **Week 4:** Enable new scorers one at a time, monitor
5. **Week 5:** Add strategy-scorer weight matrix (remove base_weight)
6. **Week 6:** Implement three-phase system
7. **Week 7:** Integrate LLM-based AmbiguityScorer with llm_light

---

`★ Insight ─────────────────────────────────────`
**The power of this design is its modularity.** Each component can be implemented and tested independently: graph utils first, then new scorers (with simplified band-based logic), then enhanced scorers (with LLM for specific tasks), then strategy profiles (without base_weight complexity), then the three-phase system. The existing TwoTierScoringEngine doesn't need major modification—it just needs new scorer classes registered and configured. This is how evolutionary software architecture should work.
`─────────────────────────────────────────────────`
