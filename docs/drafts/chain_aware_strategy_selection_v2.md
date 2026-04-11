# Chain-Aware Strategy Selection: Revised Proposal

> **Status**: Proposal v2 — simplified architecture, sharper strategy definitions  
> **Date**: 2026-04-10  
> **Supersedes**: v1 proposal (phase-conditional mode switching — rejected as too complex)  
> **Key constraint**: Single selection codepath. No mode switching. One scoring mechanism throughout.

---

## 1. Design Principles

1. **One selection path**: All turns use the same mechanism — score (strategy, node) pairs, pick the best. No phase-conditional branching between "strategy-first" and "node-first" codepaths.

2. **Threshold-based fallback**: If no (strategy, node) pair exceeds a minimum score threshold, conversation-level strategies activate. These are not competing alternatives — they are the fallback when the graph offers nothing actionable.

3. **Strategies are graph operations**: Each strategy produces a structurally distinct change to the knowledge graph. If two strategies would produce the same structural change, they are the same strategy. No vague "explore" or "validate" strategies.

4. **Signals describe structural facts**: Every signal is a deterministic computation on graph topology + methodology ontology. No LLM calls for structural signals.

5. **Methodology YAML is the source of truth**: Growth directions, probe types, level expectations — all methodology-defined, not hardcoded.

---

## 2. Signals

### 2.1 Node-Level Signals

All computed from graph topology + methodology ontology. No LLM needed.

| Signal | Type | Definition |
|---|---|---|
| `graph.node.gap_above` | bool | Node is the highest in its chain AND node type is non-terminal. This is a **chain frontier**. |
| `graph.node.gap_below` | bool | Node has no incoming `leads_to` from a lower abstraction level AND node level is above methodology origin. This node is **ungrounded**. |
| `graph.node.level_skip` | bool | Node has a direct `leads_to` edge that skips one or more intermediate ontology levels. A structural gap exists within an existing chain. |
| `graph.node.branching_deficit` | float [0,1] | `1 - (actual_siblings / expected_siblings)` at this node's ontology level. 0 = fully branched, 1 = no siblings where methodology expects them. Uses `expected_branching` from methodology config. |
| `graph.node.level_gap_size` | int | Number of ontology levels between this node and terminal (if `gap_above`) or origin (if `gap_below`). Proxy for effort-to-complete. |
| `graph.node.fan_in` | int | Number of distinct origin-level nodes that have a path to this node. Higher fan-in means more chains benefit from extending this frontier. |
| `graph.node.recency` | float [0,1] | Normalized turns since last active. Already exists. |
| `graph.node.exhaustion_score` | float [0,1] | Already exists. Retained unchanged. |

**Computation note**: `gap_above`, `gap_below`, `level_skip`, `fan_in`, and `level_gap_size` require walking `leads_to` edges per node. For graphs of 20-30 nodes with depth 3-5, this is O(N×D) — negligible.

### 2.2 Global Signals

| Signal | Type | Definition |
|---|---|---|
| `graph.global.chain_completion_ratio` | float [0,1] | Fraction of origin-level nodes with at least one path to a terminal node. |
| `graph.global.frontier_count` | int | Count of nodes where `gap_above = True`. |
| `graph.global.ungrounded_count` | int | Count of nodes where `gap_below = True`. |

### 2.3 Retained Existing Signals

All existing `llm.*`, `temporal.*`, and `meta.*` signals are retained unchanged. They contribute to (strategy, node) pair scoring through signal weights in the methodology YAML, same as today.

---

## 3. Strategies

Five node-bound strategies. Two conversation-level fallbacks. Nothing else.

### 3.1 Node-Bound Strategies

Each strategy maps to exactly one structural graph operation. Each has a primary trigger signal that makes it a valid candidate for a given node.

#### `ascend`
- **Graph operation**: Add an edge from this node upward to a new node at the next ontology level.
- **When valid**: `graph.node.gap_above = True`
- **Probe selection**: Determined by node's current type → next level up in ontology:
  - `attribute` → functional probe ("What does that do for you?")
  - `functional_consequence` → psychosocial probe ("How does that make you feel?")
  - `psychosocial_consequence` → values probe ("Why does that matter to you?")
  - `instrumental_value` → terminal probe ("What does that ultimately mean for your life?")
- **Scoring affinity**: High weight on `gap_above`, `fan_in` (more chains advanced), negative weight on `exhaustion_score`

#### `ground`
- **Graph operation**: Add an edge from a new lower-level node upward into this node.
- **When valid**: `graph.node.gap_below = True`
- **Probe selection**: "What about [product/context] leads to [node label]?" / "What gives you that sense of [node label]?"
- **Scoring affinity**: High weight on `gap_below`, `recency` (respond to recently-appeared ungrounded nodes), negative weight on `exhaustion_score`
- **Reference**: Reynolds & Gutman (1988) negative laddering

#### `bridge`
- **Graph operation**: Insert a new intermediate node into an existing edge that skips ontology levels.
- **When valid**: `graph.node.level_skip = True`
- **Probe selection**: "You mentioned [lower concept] leads to [higher concept] — what happens in between?"
- **Node binding**: Binds to the lower node of the skipped edge
- **Scoring affinity**: High weight on `level_skip`, moderate weight on `recency`

#### `branch`
- **Graph operation**: Add a new sibling node at the same ontology level, connected to the same parent or child.
- **When valid**: `graph.node.branching_deficit > 0` (methodology expects more siblings at this level)
- **Probe selection**: "Are there other [level-appropriate noun] that also [relate to parent/child]?"
- **Scoring affinity**: High weight on `branching_deficit`, moderate weight on `recency`, negative weight on `exhaustion_score`
- **Methodology-dependent**: `expected_branching` per level defines what "deficit" means

#### `anchor`
- **Graph operation**: Add an edge connecting an isolated node to an existing node in the graph.
- **When valid**: `graph.node.is_orphan = True` (no edges at all)
- **Probe selection**: "How does [concept] relate to [nearest thematic node]?"
- **Scoring affinity**: High weight on `is_orphan`, moderate weight on `recency`
- **Note**: Renamed from `connect_isolate` / `connect_orphan` for brevity

### 3.2 Conversation-Level Strategies (Threshold Fallback)

These activate ONLY when no (strategy, node) pair exceeds the score threshold. They are not scored against node-bound strategies — they exist in a separate tier.

#### `revitalize`
- **When**: Best (strategy, node) pair score < threshold AND (`llm.global_response_trend = "fatigued"` OR `llm.engagement` < 0.3)
- **Action**: Shift conversational energy. Open-ended, low-pressure question. Topic pivot.
- **Node binding**: None

#### `close`
- **When**: Existing termination conditions (saturation, max turns, `chain_completion_ratio` ≥ threshold)
- **Action**: Closing question
- **Node binding**: None

### 3.3 What About `synthesize`?

Synthesis (probing cross-chain connections) is valuable but ambiguous as a strategy. It doesn't produce a single structural graph operation — it potentially creates edges between existing chains. For now, it is **deferred** rather than included. If needed, it can be reintroduced as a late-phase Tier 1 check gated on `chain_completion_ratio ≥ 0.8` and disconnected chain clusters.

---

## 4. Selection Mechanism

### 4.1 Joint (Strategy, Node) Scoring

Single mechanism for all turns. Same codepath regardless of phase.

```
FOR each node N in graph:
    FOR each strategy S where S.is_valid(N) = True:
        score(S, N) = Σ [ signal_value(N, sig) × weight(S, sig) ] × phase_multiplier(S) + phase_bonus(S)
        
candidates = all (S, N, score) triples where S.is_valid(N)
best = max(candidates, key=score)
```

**Validity gating**: A strategy is only scored for a node if the strategy's primary trigger signal is True for that node. `ascend` is never scored for a terminal node. `ground` is never scored for an origin-level node. This keeps the candidate space manageable.

**Phase modulation**: Phase multipliers and bonuses apply to strategies, same as existing architecture. Early phase can boost `branch` (encourage breadth). Late phase can boost `ascend` (complete chains). The mechanism is unchanged — only the strategy names and weights change.

### 4.2 Threshold Fallback

```
IF best.score >= SCORE_THRESHOLD:
    execute(best.strategy, best.node)
ELSE:
    # No structural opportunity is compelling
    IF global_fatigue_detected:
        execute(revitalize)
    ELIF termination_conditions_met:
        execute(close)
    ELSE:
        # Lower threshold and take best available
        execute(best.strategy, best.node)
```

The "lower threshold and take best available" final else-branch is important — it means the system never gets stuck. Even if scores are low, there's always a (strategy, node) pair to execute. The threshold fallback to conversation-level strategies is an opportunity to inject non-structural moves, not a hard gate.

**Threshold value**: Methodology-configurable. Can be tuned per-methodology. Starting heuristic: the threshold at which a human moderator would say "nothing in the graph is calling out to me, let me try something else."

### 4.3 Score Decomposition

Every scored candidate produces a decomposition for observability:

```
(ascend, "feel confident") = 0.82
  gap_above:          0.3  (True × weight 0.3)
  fan_in:             0.2  (3 chains × weight 0.067)  
  recency:            0.16 (0.8 × weight 0.2)
  exhaustion:        -0.04 (0.1 × weight -0.4)
  phase_multiplier:   ×1.2 (mid phase boost for ascend)
  phase_bonus:        +0.0

(ground, "security") = 0.71
  gap_below:          0.3  (True × weight 0.3)
  recency:            0.18 (0.9 × weight 0.2)
  exhaustion:         0.0  (0.0 × weight -0.4)
  phase_multiplier:   ×1.0
  phase_bonus:        +0.0
```

This is the existing `ScoredCandidate` decomposition pattern, applied to the new signals and strategies.

---

## 5. Methodology YAML Extensions

### 5.1 Strategy Definitions

```yaml
strategies:
  - id: "ascend"
    intent: "Extend incomplete chain upward toward terminal values"
    node_binding: "required"
    valid_when: "graph.node.gap_above"
    signal_weights:
      graph.node.gap_above.true: 0.3
      graph.node.fan_in: 0.067        # Per-chain value
      graph.node.recency: 0.2
      graph.node.exhaustion_score: -0.4
      llm.response_depth.deep: 0.1    # Respondent is engaged — keep going
    probe_resolution: "ontology_next_level_up"

  - id: "ground"
    intent: "Establish causal antecedents for ungrounded high-level node"
    node_binding: "required"
    valid_when: "graph.node.gap_below"
    signal_weights:
      graph.node.gap_below.true: 0.3
      graph.node.recency: 0.25        # Higher recency weight — respond to what just appeared
      graph.node.exhaustion_score: -0.4
      llm.response_depth.deep: 0.05
    probe_resolution: "ontology_next_level_down"

  - id: "bridge"
    intent: "Fill missing intermediate level in a skipped chain"
    node_binding: "required"
    valid_when: "graph.node.level_skip"
    signal_weights:
      graph.node.level_skip.true: 0.35
      graph.node.recency: 0.2
      graph.node.exhaustion_score: -0.3
    probe_resolution: "ontology_missing_intermediate"

  - id: "branch"
    intent: "Expand breadth at a level where methodology expects more siblings"
    node_binding: "required"
    valid_when: "graph.node.branching_deficit_gt_0"
    signal_weights:
      graph.node.branching_deficit: 0.25
      graph.node.recency: 0.15
      graph.node.exhaustion_score: -0.3
      llm.engagement: 0.1             # Branch when energy is available
    probe_resolution: "same_level_sibling"

  - id: "anchor"
    intent: "Connect isolated node to existing graph structure"
    node_binding: "required"
    valid_when: "graph.node.is_orphan"
    signal_weights:
      graph.node.is_orphan.true: 0.35
      graph.node.recency: 0.2
      graph.node.exhaustion_score: -0.2
    probe_resolution: "nearest_thematic"
```

### 5.2 Chain Completion Configuration

```yaml
chain_completion:
  score_threshold: 0.15              # Below this, conversation-level strategies may activate
  
  expected_branching:                # Per ontology level
    attribute: 3
    functional_consequence: 2
    psychosocial_consequence: 1
    instrumental_value: 1
    terminal_value: 1
    
  probe_resolution:
    ontology_next_level_up:
      attribute: "why_important"             # "What does that do for you?"
      functional_consequence: "feeling_probe" # "How does that make you feel?"
      psychosocial_consequence: "why_important" # "Why does that matter?"
      instrumental_value: "why_important"     # "What does that ultimately mean?"
      
    ontology_next_level_down:
      terminal_value: "what_enables"          # "What gives you that sense of...?"
      instrumental_value: "what_enables"
      psychosocial_consequence: "what_enables"
      functional_consequence: "concrete_example"
      
    ontology_missing_intermediate:
      default: "bridge_probe"                 # "What happens in between?"
      
    same_level_sibling:
      default: "lateral_probe"                # "Are there other [X] that...?"
      
    nearest_thematic:
      default: "connection_probe"             # "How does [X] relate to...?"

  conversation_level:
    revitalize:
      conditions:
        - signal: "llm.global_response_trend"
          value: "fatigued"
        - signal: "llm.engagement"
          value_lt: 0.3
    close:
      conditions:
        # Existing termination conditions apply
        - signal: "graph.global.chain_completion_ratio"
          value_gte: 0.9
```

### 5.3 Phase Weights (Strategy Modulation, Not Mode Switching)

Phases modulate strategy *priority*, not selection *mechanism*. Same scoring path always runs.

```yaml
phases:
  early:
    turn_range: [1, 5]
    signal_weights:
      branch: 1.5            # Encourage breadth early
      ascend: 0.8            # Don't rush to complete chains
      ground: 1.0
      bridge: 0.5            # Few skips expected early
      anchor: 1.2            # Connect orphans promptly
    phase_bonuses:
      branch: 0.1

  mid:
    turn_range: [6, 15]
    signal_weights:
      ascend: 1.5            # Primary focus: complete chains
      ground: 1.2            # Respond to spontaneous high-level nodes
      bridge: 1.3            # Fill gaps
      branch: 0.8            # Less breadth pressure
      anchor: 1.0

  late:
    turn_range: [16, 999]
    signal_weights:
      ascend: 1.8            # Strong chain completion pressure
      ground: 0.8            # Less grounding — focus on what's already started
      bridge: 1.5            # High priority to fill remaining gaps
      branch: 0.5            # Minimal new breadth
      anchor: 0.6            # Orphans less important now
    phase_bonuses:
      ascend: 0.15
```

### 5.4 JTBD Variant

```yaml
# Differences from MEC
chain_completion:
  expected_branching:
    job: 3
    pain_point: 3             # Higher — JTBD expects rich pain landscape
    desired_outcome: 2
    emotional_outcome: 1

phases:
  early:
    signal_weights:
      branch: 1.8             # JTBD emphasizes job landscape mapping
      ascend: 0.6
  mid:
    signal_weights:
      branch: 1.3             # Still important in JTBD mid-phase
      ascend: 1.3             # Co-equal with branching
```

---

## 6. Architectural Implications

### 6.1 What Changes

| Component | Change | Complexity |
|---|---|---|
| **Signal detectors** (new) | `ChainTopologySignalDetector` computing `gap_above`, `gap_below`, `level_skip`, `branching_deficit`, `fan_in`, `level_gap_size` | Medium — graph traversal, depends on methodology ontology |
| **Global signal detectors** (new) | `chain_completion_ratio`, `frontier_count`, `ungrounded_count` | Low — aggregate counts |
| **Strategy YAML** | Replace 7 strategies with 5 node-bound + 2 conversation-level | Low — config change |
| **StrategySelectionStage** | Add threshold check after scoring; fallback to conversation-level | Low — ~20 lines |
| **QuestionGenerationStage** | Accept `probe_resolution` output: probe type resolved from node type + strategy | Medium — new prompt parameterization |
| **MethodologyConfig parser** | Parse `chain_completion`, `expected_branching`, `probe_resolution` sections | Low — YAML parsing |

### 6.2 What Does NOT Change

| Component | Why unchanged |
|---|---|
| **Scoring mechanism** | Same weighted additive scoring. Same `rank_strategies` / `rank_nodes_for_strategy` pattern. The new strategies just have different signal weights. |
| **D2 two-stage architecture** | Retained. Stage 1 scores strategies (now 5 instead of 7). Stage 2 scores nodes for the winning strategy. Unchanged control flow. |
| **Phase weight application** | Same multiplicative + additive formula. Only the strategy names and weight values change. |
| **Signal pool architecture** | New signals register in graph pool alongside existing ones. Same namespacing, same detection flow. |
| **ExtractionStage, GraphUpdateStage, SlotDiscovery** | Upstream of strategy selection. Unaffected. |
| **ContinuationStage** | May optionally use `chain_completion_ratio` but core logic unchanged. |
| **NodeStateTracker** | Stores new signal values per node, same pattern as existing signals. |
| **ScoredCandidate decomposition** | Same format, different signal names in the breakdown. |

### 6.3 Migration Path

**Phase 1: Additive signals** — Implement `ChainTopologySignalDetector`. Register new signals. They flow into existing scoring with zero weights (no behavioral change). Validate computation correctness via logging.

**Phase 2: New strategies in YAML** — Define the 5 strategies with signal weights. Run alongside existing strategies (both old and new active). Compare selections in logs.

**Phase 3: Remove legacy strategies** — Remove `deepen_branch`, `explore_breadth`, `ensure_coverage`, `resolve_ambiguity`, `validate_confirm`, `reflect`. Add threshold fallback for `revitalize` and `close`.

**Phase 4: Tune** — Adjust signal weights, phase multipliers, threshold value based on interview transcripts.

---

## 7. Open Questions

1. **Threshold tuning**: The `score_threshold` for conversation-level fallback needs empirical calibration. Starting value is a guess. May need per-methodology tuning.
   **Response**: this is understood. A tuning plan it TO BE DEVELOPED after the implementation 

2. **`valid_when` as hard gate vs soft signal**: Current proposal uses `valid_when` as a hard boolean gate (strategy not scored at all for nodes where it's False). Alternative: treat it as a soft signal with very high weight, allowing edge cases where a near-frontier node gets scored for `ascend`. Hard gate is simpler and proposed as default.
   **Response**: the advantage of boolean implementation is that it reduces the set of node-strategy pairs that require scoring.

3. **Canonical graph**: Chain signals computed on surface graph. Should canonical graph deduplication affect chain topology computation? If two surface nodes map to the same canonical slot, are their chains merged for signal purposes?
   **Response**: I do not understand this issue, i need some illustration

4. **`synthesize` reintroduction**: Deferred in this proposal. If cross-chain probing proves valuable, it could be a Tier 1 check gated on `chain_completion_ratio ≥ 0.8` + disconnected chain clusters detected. Not a node-bound strategy.
   **Response**: This could potentially be relevant in the last phase of the interview, but for now i would park it 

5. **Coverage of stimulus elements**: Without `ensure_coverage` as a strategy, how does the system ensure all stimulus elements get explored? Proposal: a Tier 1 check — if any high-priority stimulus element has zero associated nodes after N turns, inject an introduction. This is a veto, not a scored strategy.
   **Response**: I was trying to remove this coverage for ages, but it still pops up somehow. This system is about exploration, and coverage here is not relevant

6. **Early phase with sparse graph**: When the graph has <5 nodes in early turns, most chain signals will be trivially True or False with little differentiation. The phase weights (boosting `branch`, dampening `ascend`) handle this, but worth verifying the scoring produces sensible results with very sparse graphs.
   **Response**: This situation will be characteristical for early stages, and i hope there will be a strategy around some kind of exploration that will be prioritised in these cases. Maybe - if there are multiple new nodes, but they are not differentiated and no node is a clear priority, then "explore"?
