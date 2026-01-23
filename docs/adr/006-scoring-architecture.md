# ADR-006: Enhanced Scoring and Strategy Architecture

## Status
Proposed

## Context
**Supersedes**: Extends ADR-004 (Two-Tier Hybrid Scoring System)

The current two-tier scoring system (ADR-004) provides a solid foundation with:
- **Tier 1**: Hard constraint vetoes (KnowledgeCeiling, ElementExhausted, RecentRedundancy)
- **Tier 2**: Weighted additive scoring with 6 scorers (CoverageGap, Ambiguity, DepthBreadthBalance, Engagement, StrategyDiversity, Novelty)
- **5 strategies**: deepen, broaden, cover_element, closing, reflection

However, after analyzing qualitative research interview methodologies and testing the system, several limitations have emerged:

### Current Limitations

1. **Insufficient Strategy Variety**: The system lacks strategies for:
   - Lateral bridging to peripheral but related topics
   - Contrastive questioning (testing boundaries with counter-examples)
   - Rapport repair when engagement drops
   - Synthesis and summarization transitions

2. **Uniform Scoring Across Contexts**: All scorers apply the same weight regardless of:
   - Interview phase (early exploration vs. deep dive vs. closing)
   - Strategy-specific needs (e.g., CoverageGap matters more for deepen than for ease)
   - Respondent state (confused vs. engaged vs. fatigued)

3. **Heuristic Complexity**: Many scorers use arbitrary coefficients (e.g., `0.3 * density + 0.2 * peripheral_count`) that:
   - Are difficult to justify or explain
   - Require extensive tuning
   - Don't align with qualitative research principles

4. **No Phase Awareness**: The system doesn't modulate behavior based on:
   - Interview progression (exploratory → focused → closing)
   - Turn count thresholds
   - Coverage completion ratios

### Research Findings

Analysis of qualitative research methodology (as documented in `docs/raw_ideas/draft_reco.md`) reveals:

1. **Peripheral Readiness**: Effective interviews detect when current topic clusters are saturated and bridge to related but unexplored areas
2. **Contrast Opportunities**: Introducing counter-examples tests boundaries and reveals depth of understanding
3. **Cluster Saturation**: Synthesis works best when topical clusters are complete (high density + high degree)
4. **Phase Modulation**: Early interviews prioritize breadth; later interviews prioritize depth
5. **Ambiguity Detection**: Hedge words and uncertainty markers signal need for clarification strategies

## Decision
**Adopt an enhanced scoring and strategy architecture** with:

1. **4 New Strategies**: bridge, contrast, ease, synthesis
2. **3 New Tier-2 Scorers**: PeripheralReadiness, ContrastOpportunity, ClusterSaturation
3. **Strategy-Scorer Weight Matrix**: Per-strategy scorer weights (not uniform across all strategies)
4. **Phase-Based Modulation**: Three interview phases (exploratory, focused, closing) with strategy multipliers
5. **Simplified Scoring Formula**: `final_score = Σ(strategy_weight × raw_score) × phase_multiplier`
6. **LLM-Based Ambiguity Detection**: Replace keyword heuristics with LLM-based linguistic analysis

### Technical Architecture

```
Enhanced Two-Tier Scoring System
│
├── Tier 1: Hard Constraints (Boolean Vetoes) - UNCHANGED
│   ├── KnowledgeCeilingScorer
│   ├── ElementExhaustedScorer
│   └── RecentRedundancyScorer
│
├── Tier 2: Weighted Additive Scoring - ENHANCED
│   ├── Existing Scorers:
│   │   ├── CoverageGapScorer
│   │   ├── AmbiguityScorer (enhanced with LLM)
│   │   ├── DepthBreadthBalanceScorer
│   │   ├── EngagementScorer
│   │   ├── StrategyDiversityScorer
│   │   └── NoveltyScorer
│   │
│   └── New Scorers:
│       ├── PeripheralReadinessScorer (weight: 0.15)
│       ├── ContrastOpportunityScorer (weight: 0.15)
│       └── ClusterSaturationScorer (weight: 0.10)
│
├── Strategies (9 total)
│   ├── Existing: deepen, broaden, cover_element, closing, reflection
│   └── New: bridge, contrast, ease, synthesis
│
└── Phase Profiles (3 phases)
    ├── exploratory: {broaden: 1.2, deepen: 0.8, bridge: 0.2, ...}
    ├── focused: {deepen: 1.3, broaden: 0.4, contrast: 1.2, ...}
    └── closing: {closing: 1.5, synthesis: 1.3, deepen: 0.3, ...}
```

### Scoring Formula

**Before (ADR-004)**:
```python
final_score = strategy.priority_base + Σ(base_weight × raw_score)
```

**After (This Decision)**:
```python
# Step 1: Sum weighted scorer outputs for this strategy
scorer_sum = Σ(strategy_weight × raw_score)

# Step 2: Apply phase multiplier
final_score = scorer_sum × phase_multiplier
```

**Example Calculation**:
```
Strategy: deepen
Phase: exploratory (phase_multiplier = 0.8)

Scorers:
  CoverageGap:     strategy_weight=0.30, raw_score=1.5 → 0.45
  Ambiguity:       strategy_weight=0.20, raw_score=1.2 → 0.24
  Novelty:         strategy_weight=0.15, raw_score=0.8 → 0.12
  ─────────────────────────────────────────────────────
  scorer_sum = 0.81

final_score = 0.81 × 0.8 = 0.648
```

### New Strategies

| Strategy ID | Type Category | Purpose | Prompt Hint |
|-------------|---------------|---------|-------------|
| `bridge` | peripheral | Lateral bridge to peripheral topics | "Explicitly link to what was just said, then gently shift to a related but distinct area." |
| `contrast` | contrast | Introduce counter-example | "Politely introduce a counter-example or opposite case to test boundaries." |
| `ease` | interaction | Rapport repair | "Simplify or soften the question, encourage participation." |
| `synthesis` | transition | Summarize and invite extension | "Briefly summarise what you've heard and invite correction or addition." |

### New Tier-2 Scorers

#### 1. PeripheralReadinessScorer (weight: 0.15)
**Purpose**: Detect when lateral bridging is optimal

**Signals**:
- `local_cluster_density`: Density of current focus cluster (0-1)
- `peripheral_candidate_count`: Number of unvisited nodes within 2-3 hops
- `turns_since_last_jump`: How long since we moved to a new cluster

**Scoring Logic** (simplified band-based):
```python
if strategy.id == "bridge":
    if local_cluster_density > 0.7 and peripheral_candidate_count >= 3:
        raw_score = 1.5  # High confidence: cluster saturated + peripherals exist
    elif local_cluster_density > 0.5 or peripheral_candidate_count >= 1:
        raw_score = 1.2  # Moderate boost
    else:
        raw_score = 1.0  # Neutral
else:
    raw_score = 1.0  # Neutral for non-bridge strategies

return clamp(0.5, 1.8, raw_score)
```

**Implementation**: `src/services/scoring/tier2/peripheral_readiness.py`

#### 2. ContrastOpportunityScorer (weight: 0.15)
**Purpose**: Detect when counter-example is available

**Signals**:
- `has_opposite_stance`: Boolean, exists node with stance = -focus.stance
- `local_cluster_density`: Density of current cluster (0-1)

**Scoring Logic**:
```python
if strategy.id == "contrast" and has_opposite_stance:
    if local_cluster_density > 0.6:
        raw_score = 1.5  # High confidence: opposite + coherent cluster
    else:
        raw_score = 1.2  # Moderate boost
else:
    raw_score = 1.0

return clamp(0.5, 1.5, raw_score)
```

**Implementation**: `src/services/scoring/tier2/contrast_opportunity.py`

#### 3. ClusterSaturationScorer (weight: 0.10)
**Purpose**: Detect when topic is complete

**Signals**:
- `local_cluster_density`: Density of current cluster (0-1)
- `median_cluster_degree`: Median degree within cluster
- `cluster_node_count`: Size of current cluster

**Scoring Logic**:
```python
saturation = min(1.0, local_cluster_density * median_cluster_degree / 3)

if strategy.id == "synthesis":
    if saturation > 0.7:
        raw_score = 1.5  # Cluster is saturated
    elif saturation > 0.4:
        raw_score = 1.2  # Moderately saturated
    else:
        raw_score = 1.0  # Not saturated
else:
    raw_score = 1.0

return clamp(0.5, 1.6, raw_score)
```

**Implementation**: `src/services/scoring/tier2/cluster_saturation.py`

### Enhanced AmbiguityScorer

**Current**: Keyword-based heuristics (hedge words, uncertainty markers)

**Enhanced**: LLM-based linguistic analysis

**Prompt**:
```
Analyze this interview response for linguistic ambiguity and uncertainty.

Response text: "{recent_text}"

Evaluate:
1. Hedge words: Does the respondent use qualifying language (maybe, sort of, might)?
2. Uncertainty markers: Explicit expressions of not knowing (not sure, unclear)?
3. Extraction confidence: Would you be confident extracting a clear claim from this?

Rate AMBIGUITY from 0.0 (crystal clear) to 1.0 (very ambiguous).

Return JSON: {{"ambiguity": float, "reasoning": str}}
```

**Scoring Logic**:
```python
ambiguity = response['ambiguity']

if ambiguity < 0.2:
    raw_score = 0.9  # Clear, no clarification needed
elif ambiguity < 0.5:
    raw_score = 1.2  # Mild ambiguity
else:
    raw_score = 1.5  # High ambiguity
```

**Implementation**: Enhance `src/services/scoring/tier2/ambiguity.py` with LLM client

### Graph Utilities Module

Create `src/services/scoring/graph_utils.py` for cluster analysis:

```python
def get_clusters(graph: nx.Graph, turn_number: int) -> Dict[str, int]:
    """Get Louvain cluster assignments for all nodes (cached per turn)."""

def local_cluster_density(focus_node: str, graph: nx.Graph) -> float:
    """Density of the cluster containing focus_node."""

def has_peripheral_candidates(focus_node: str, graph: nx.Graph, max_hops: int = 2) -> Tuple[int, float]:
    """Count unvisited nodes within max_hops of focus_node's cluster."""

def has_opposite_stance_node(focus_node: str, graph: nx.Graph) -> bool:
    """Check if any node has opposite stance to focus_node."""

def median_cluster_degree(focus_node: str, graph: nx.Graph) -> float:
    """Median degree of nodes in focus_node's cluster."""
```

### Configuration Structure

**Updated YAML** (`config/scoring.yaml`):

```yaml
strategies:
  - id: deepen
    name: Deepen existing branches
    type_category: depth
    enabled: true
    prompt_hint: "Explore deeper into why this is important."

  - id: bridge
    name: Lateral Bridge to Peripheral
    type_category: peripheral
    enabled: true
    prompt_hint: "Explicitly link to what was just said, then gently shift to a related but distinct area."

  # ... other strategies ...

tier2_scorers:
  coverage_gap:
    enabled: true
    strategy_weights:
      deepen: 0.30
      broaden: 0.24
      cover_element: 0.30
      synthesis: 0.20
      default: 0.20

  ambiguity:
    enabled: true
    strategy_weights:
      deepen: 0.20
      clarify: 0.30
      bridge: 0.10  # Don't bridge while ambiguous
      synthesis: 0.10
      default: 0.15

  peripheral_readiness:
    enabled: true
    strategy_weights:
      bridge: 0.30
      broaden: 0.20
      default: 0.05

  # ... other scorers ...

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
    closing: 0.5
    ease: 1.0
    reflection: 0.7

  closing:
    deepen: 0.3
    broaden: 0.2
    cover_element: 0.5
    bridge: 0.3
    contrast: 0.5
    synthesis: 1.3
    closing: 1.5
    ease: 1.0
    reflection: 0.3

phase_config:
  exploratory:
    min_turns: 8
    max_turns: 20

  focused:
    min_turns: 5
    max_turns: null

  closing:
    min_turns: 15
    trigger_coverage: 0.95
```

### Data Model Changes

1. **Add `stance` to Nodes**:
   ```python
   node_data = {
       'id': element_id,
       'text': element_text,
       'stance': element_data.get('stance', 0),  # +1, 0, or -1
   }
   ```

2. **Add `turn_count` to GraphState**:
   ```python
   @property
   def turn_count(self) -> int:
       return self.properties.get('turn_count', 0)

   def increment_turn(self):
       self.properties['turn_count'] = self.turn_count + 1
   ```

3. **Add `phase` to GraphState**:
   ```python
   @property
   def phase(self) -> str:
       return self.properties.get('phase', 'exploratory')

   def set_phase(self, phase: str):
       self.properties['phase'] = phase
   ```

4. **Add `sentiment` to Turns**:
   ```python
   turn_data = {
       'speaker': 'respondent',
       'text': utterance,
       'sentiment': sentiment_score,  # -1 to +1 from API
   }
   ```

### LLM Configuration

Add dual LLM clients to `config.yaml`:

```yaml
llm:
  main:  # For question generation
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
    api_key: ${ANTHROPIC_API_KEY}

  light:  # For scoring tasks (AmbiguityScorer)
    provider: "anthropic"
    model: "claude-hiku-4-20250514"
    api_key: ${ANTHROPIC_API_KEY}
```

## Rationale

### Benefits

1. **Richer Interview Dynamics**: 4 new strategies enable more nuanced conversation flows (bridging, contrasting, rapport repair, synthesis)

2. **Context-Aware Scoring**: Strategy-scorer weight matrix ensures each strategy is scored on relevant dimensions (e.g., PeripheralReadiness matters for bridge, not deepen)

3. **Phase-Based Adaptation**: Interview naturally progresses from breadth → depth → closure without manual intervention

4. **Reduced Heuristics**: Band-based scoring (0.5/1.0/1.5) replaces arbitrary coefficients, making behavior more predictable and explainable

5. **LLM-Based Ambiguity**: No hardcoded keyword lists; handles edge cases like sarcasm and complex phrasing

6. **Explainable Decisions**: LLM reasoning provides justification for ambiguity scores

7. **Backward Compatible**: Existing scorers and strategies continue to work; new components are additive

### Costs

1. **Implementation Complexity**: 3 new scorers, 4 new strategies, phase system, graph utilities (~5-7 days)

2. **Configuration Overhead**: Strategy-scorer weight matrix requires careful tuning (~50+ weight values)

3. **LLM Dependency**: AmbiguityScorer requires LLM API calls, adding latency and cost

4. **Data Model Changes**: Requires adding `stance` to nodes, `sentiment` to turns, phase tracking

5. **Testing Burden**: More components = more integration test cases

6. **Graph Computation**: Louvain clustering adds per-turn overhead (mitigated by caching)

### Why Not Alternatives?

| Alternative | Rejected Because |
|-------------|------------------|
| **Status quo (ADR-004)** | Limited strategy variety; no phase awareness; uniform scoring doesn't match qualitative research practices |
| **LLM-based scoring for all scorers** | Too slow, expensive, non-deterministic; graph-structural scorers (CoverageGap, PeripheralReadiness) work fine with deterministic logic |
| **Keyword-based ambiguity detection** | Hardcoded keyword lists don't handle edge cases; requires ongoing maintenance; less robust than LLM |
| **Multiplicative phase modulation** (`final = Σ(weights) × phase`) | Can cause score explosion if phase multipliers compound; additive approach is more predictable |
| **Single phase instead of three** | Doesn't match interview progression; early interviews need breadth, late interviews need depth; closing needs special handling |

## Consequences

### Positive

1. **More Natural Interviews**: System can bridge topics, test boundaries with contrasts, repair rapport, and synthesize

2. **Adaptive Phases**: Interview automatically shifts from exploration to focus to closure

3. **Better Scoring Alignment**: Each strategy scored on dimensions that matter for that strategy

4. **Explainable Ambiguity**: LLM reasoning provides justification for clarification decisions

5. **Reduced Tuning Burden**: Band-based scoring (0.5/1.0/1.5) more interpretable than continuous coefficients

6. **Research-Aligned**: Matches qualitative research methodology for semi-structured interviews

### Negative

1. **Longer Implementation**: ~5-7 days vs. ~1-2 days for simpler enhancements

2. **Configuration Complexity**: ~50+ weight values to tune in strategy-scorer matrix

3. **LLM Costs**: AmbiguityScorer adds ~1 LLM call per turn (using lighter model mitigates cost)

4. **Per-Turn Overhead**: Louvain clustering + LLM call adds latency (mitigated by caching cluster assignments)

5. **Data Migration**: Need to add `stance` to existing nodes, `sentiment` to historical turns

### Neutral

1. **Backward Compatible**: Existing scorers/strategies work unchanged; new components are additive

2. **Performance**: Louvain clustering cached per turn; LLM uses lighter model (Haiku/Haiku-4)

3. **Testing**: More components but modular design allows unit testing per scorer

4. **Configuration**: YAML structure changes but validation ensures weights sum correctly

## Implementation

See implementation plan in `docs/raw_ideas/draft_reco.md` Part 9.

### Phased Rollout

**Phase 1: Foundation** (Priority 1)
- Create `src/services/scoring/graph_utils.py`
- Add `stance` attribute to stimulus nodes
- Add `turn_count` and `phase` to GraphState
- Add new strategies to `config/scoring.yaml`

**Phase 2: New Scorers** (Priority 1)
- Implement `PeripheralReadinessScorer`
- Implement `ContrastOpportunityScorer`
- Implement `ClusterSaturationScorer`

**Phase 3: Enhanced Scorers** (Priority 2)
- Enhance `AmbiguityScorer` with LLM-based detection
- Add dual LLM client configuration
- Implement turn-level caching for LLM results

**Phase 4: Strategy Profiles** (Priority 3)
- Implement strategy-scorer weight matrix
- Update `TwoTierScoringEngine` to use new formula
- Add phase transition logic to `StrategyService`
- Implement phase profiles configuration

**Phase 5: Integration & Testing** (Priority 4)
- Integration tests for phase transitions
- Unit tests per new scorer
- End-to-end tests for full interview flow
- Performance benchmarking (Louvain + LLM overhead)

## Related Decisions

- **ADR-004**: Two-Tier Hybrid Scoring System - Extended by this decision (adds strategies, scorers, phase modulation)
- **ADR-003**: Adopt Phase 3 Adaptive Strategy - Superseded by ADR-004, this decision further enhances the strategy selection
- **ADR-001**: Dual Sync/Async API - Unaffected
- **ADR-002**: Streamlit Framework Choice - Unaffected

## References

- `docs/raw_ideas/draft_reco.md`: Complete implementation proposal with Q&A
- `docs/theory/two_tier_scoring_system_design.md`: Original two-tier design (extended by this decision)
- `src/services/scoring/two_tier/`: Current two-tier implementation
- `config/scoring.yaml`: Current scoring configuration
- Louvain community detection: `python-louvain` package for cluster analysis
- LLM integration: Anthropic Claude Haiku for lightweight scoring tasks
