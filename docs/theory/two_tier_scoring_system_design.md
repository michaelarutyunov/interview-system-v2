# Two-Tier Scoring System: Design Specification

## Executive Summary

This document specifies a two-tier hybrid scoring approach for adaptive interview strategy selection, based on 50+ years of Multi-Criteria Decision Analysis (MCDA) research and modern dialogue system practices. The approach addresses critical issues with multiplicative scoring while maintaining veto power and interpretability.

**Core Principle**: Separate hard constraints (boolean vetoes) from soft preferences (weighted scoring) to achieve predictable, debuggable, and production-ready decision-making.

---

## 1. Literature Review: Scoring Methods Comparison

### 1.1 Additive Scoring

**Formula**: `score = w₁×s₁ + w₂×s₂ + ... + wₙ×sₙ` where Σ(weights) = 1.0

**Characteristics**:
- Weights represent percentage importance
- Poor performance on one criterion can be compensated by strong performance elsewhere
- Predictable, bounded output
- Interpretable: "Coverage gaps are 25% of the decision"

**Pros**:
- **Superior interpretability**: Choo & Wedley (2008) explicitly recommend additive over multiplicative, stating "the additive aggregation model is superior and easier for decision makers to use and understand"
- **Predictable behavior**: Linear combination prevents score explosions
- **Compensatory**: Allows trade-offs between criteria (sometimes desirable)
- **Standard practice**: Most common in production MCDA systems

**Cons**:
- **No natural veto power**: A zero score on one criterion doesn't block the alternative
- **Compensation can hide critical failures**: Excellent performance on 7 criteria can mask disaster on the 8th
- **Requires normalization**: All scores must be on comparable scales

**Research Citation**: Choo & Wedley (2008), "Comparing Fundamentals of Additive and Multiplicative Aggregation in Ratio Scale Multi-Criteria Decision Making"

---

### 1.2 Multiplicative Scoring

**Formula**: `score = s₁^w₁ × s₂^w₂ × ... × sₙ^wₙ`

**Characteristics**:
- Weights are exponents, not percentages
- Rewards balanced/consistent performance
- Penalizes uneven profiles (high variance across criteria)
- Natural veto: any score ≈ 0 produces final score ≈ 0

**Pros**:
- **No normalization needed**: Handles heterogeneous units (per Weighted Product Model literature)
- **Natural veto power**: Zero score on any criterion → zero overall
- **Rewards consistency**: Prefers balanced performance across criteria (per arithmetic-geometric mean inequality)

**Cons**:
- **Score explosion with multiple criteria**: With 14 scorers, even modest boosts compound dramatically (1.2^14 = 11.4×)
- **Weight interpretation is complex**: Weights "have complicated meanings which are not well understood and often mixed up in the ambiguous notion of 'criteria importance'" (Choo & Wedley 2008)
- **Unpredictable interactions**: Small changes in one scorer can flip rankings entirely
- **Cancellation effects**: Similar values "cancel each other out mathematically" making ratios unstable
- **Difficult to tune**: Adjusting one weight affects all interactions non-linearly

**Research Citations**: 
- Choo & Wedley (2008) - recommends against multiplicative
- Tofallis (2014), "Add or Multiply? A Tutorial on Ranking and Choosing with Multiple Criteria"

**Behavioral Difference Example** (from Tofallis 2014):
- Alternative A: scores [30, 39, 47, 70, 92, 94, 99, 99] - ranks better additively (compensation)
- Alternative B: scores [54, 58, 69, 71, 72, 75, 79, 95] - ranks better multiplicatively (consistency)

Multiplicative scoring favors consistency; additive allows compensation. For interview systems, you need BOTH: hard constraints (veto) AND flexible trade-offs (compensation).

---

### 1.3 Hybrid/Two-Tier Approaches

**Concept**: Combine boolean constraints with weighted scoring

**Implementation Pattern**:
1. **Stage 1**: Apply hard constraints (veto checks)
2. **Stage 2**: Score remaining candidates with additive weights

**Prevalence**:
- **ELECTRE family** (European MCDA tradition): Uses veto thresholds where "when an alternative performs worse than another one by at least the veto value on even a single criterion, then the former cannot outrank the latter, irrespective of its comparative performance on the remaining criteria"
- **Rasa dialogue framework**: Explicit policy hierarchy - RulePolicy (hard constraints) before MemoizationPolicy before TEDPolicy (ML scoring)
- **Alibaba DAMO Academy**: "To ensure stability and interpretability, the industry primarily uses rule-based DM models" with ML as supplementary
- **Knowledge-grounded dialogue systems**: Three-tier hierarchical filtering (domain classification → entity extraction → snippet ranking)
- **Medical/therapeutic AI systems**: Expert-defined scripts (hard constraints) with flexible LLM generation within bounds

**Research Support**:
- Multiple MCDA methods use "veto levels" and "indifference thresholds" as inter-criteria parameters
- Production dialogue systems consistently use "priority-based hierarchies"
- Safety-critical domains (medical, therapeutic) require explicit constraints before flexible scoring

**Why This Works**:
1. **Interpretability**: Rules are explicit; ML/scoring supplements rather than replaces
2. **Safety**: Critical constraints cannot be overridden by high scores elsewhere
3. **Stability**: Prevents pathological ML behavior
4. **Debuggability**: Easy to distinguish rule violations from scoring preferences
5. **Aligns with human decision-making**: "Must-haves" vs. "nice-to-haves"

---

## 2. Recommended Approach: Two-Tier Hybrid System

### 2.1 Architecture Overview

```
Input: (Strategy, Focus, State, History)
           ↓
    ┌──────────────────────────────────┐
    │   TIER 1: Hard Constraints       │
    │   (Boolean Veto Checks)          │
    │                                  │
    │   • Knowledge Ceiling            │
    │   • Element Exhaustion           │
    │   • Recent Redundancy            │
    └──────────┬───────────────────────┘
               │
               ├─→ VETO? → Return score = 0.0
               │            (vetoed_by = scorer_id)
               ↓
               PASS
               ↓
    ┌──────────────────────────────────┐
    │   TIER 2: Weighted Additive      │
    │   (Soft Scoring)                 │
    │                                  │
    │   score = base +                 │
    │           w₁×s₁ +                │
    │           w₂×s₂ +                │
    │           ... +                  │
    │           wₙ×sₙ                  │
    │                                  │
    │   where Σ(weights) = 1.0         │
    └──────────┬───────────────────────┘
               ↓
         Final Score
```

### 2.2 Tier 1: Hard Constraints (Boolean Vetoes)

**Purpose**: Enforce absolute requirements that cannot be compensated by other factors.

**Characteristics**:
- **Binary output**: Pass (continue to Tier 2) or Veto (immediate score = 0)
- **Early exit**: First veto encountered stops evaluation
- **No weights**: All Tier 1 scorers have equal veto power
- **Fast execution**: Simple boolean checks (e.g., similarity > 0.85)

**Configuration Structure** (Conceptual):
Each Tier 1 scorer specifies:
- `id`: Unique identifier
- `enabled`: Boolean flag
- `veto_threshold`: The boundary value that triggers veto
- `config`: Scorer-specific parameters

**Proposed Tier 1 Scorers**:

1. **KnowledgeCeilingScorer**
   - **Checks**: Whether respondent has knowledge about the focus topic
   - **Veto condition**: Respondent explicitly indicated "don't know" or similar
   - **Detection method**: Check dialogue history for knowledge-lack signals ("I don't know", "never heard of", "not familiar with")
   - **Rationale**: Asking about unknown topics frustrates respondents and yields no information

2. **ElementExhaustedScorer**
   - **Checks**: Whether the focus element has been sufficiently explored
   - **Veto condition**: Element mentioned ≥ max_mentions times AND all relationships established
   - **Configuration**: `max_mentions` (e.g., 3-5 depending on methodology)
   - **Rationale**: Repeatedly asking about exhausted elements creates redundancy

3. **RecentRedundancyScorer**
   - **Checks**: Whether proposed question is too similar to recent questions
   - **Veto condition**: Similarity to any of last N questions exceeds threshold
   - **Similarity method**: Jaccard similarity, cosine similarity, or semantic embeddings
   - **Configuration**: `lookback_window` (e.g., 6 turns), `similarity_threshold` (e.g., 0.85)
   - **Rationale**: Prevents asking near-identical questions in succession

**Implementation Requirements**:
- Each scorer returns a `ScorerOutput` object containing:
  - `is_veto`: Boolean flag
  - `reasoning`: Human-readable explanation
  - `scorer_id`: For logging/debugging
- First veto encountered stops all further evaluation
- Vetoed results must indicate `vetoed_by` scorer ID for transparency

**Edge Case**: What if all candidates are vetoed?
- **Option A**: Force selection of "least-bad" vetoed candidate (highest partial Tier 2 score before veto)
- **Option B**: Use emergency fallback strategy (e.g., "closing" to end interview gracefully)
- **Option C**: Log error and request human intervention
- **Recommendation**: Option A with loud logging for post-interview analysis

---

### 2.3 Tier 2: Weighted Additive Scoring

**Purpose**: Differentiate among valid candidates based on soft preferences and strategic priorities.

**Formula**:
```
final_score = strategy.priority_base + Σ(weight_i × normalized_score_i)
```

Where:
- `strategy.priority_base`: Starting score (typically 1.0, allows strategy-level prioritization)
- `weight_i`: Importance weight for scorer i, where Σ(weights) = 1.0
- `normalized_score_i`: Scorer output in range [0, 2] where:
  - `1.0` = neutral (no effect)
  - `> 1.0` = boost (favor this candidate)
  - `< 1.0` = penalty (disfavor this candidate)

**Configuration Requirements**:
- Weights MUST sum to exactly 1.0 (validate at initialization)
- Each weight represents the percentage contribution to the final decision
- Weights should be tunable via YAML configuration
- Each scorer specifies its own normalization range and interpretation

**Proposed Tier 2 Scorers**:

1. **CoverageGapScorer** (weight: 0.20-0.25)
   - **Measures**: How many coverage gaps the focus addresses
   - **Scoring logic**:
     - 0 gaps → score ≈ 0.8 (slight penalty)
     - 1-2 gaps → score ≈ 1.2 (moderate boost)
     - 3+ gaps → score ≈ 1.5 (strong boost)
   - **Gap types**: unmentioned, no_reaction, no_comprehension, unconnected
   - **Rationale**: Prioritize breadth early, fill knowledge gaps

2. **AmbiguityScorer** (weight: 0.15-0.20)
   - **Measures**: Clarity/confidence of nodes in the focus area
   - **Scoring logic**:
     - High clarity (confidence > 0.8) → score ≈ 0.9 (no need to clarify)
     - Medium clarity (0.5-0.8) → score ≈ 1.2 (worth clarifying)
     - Low clarity (< 0.5) → score ≈ 1.5 (definitely needs clarification)
   - **Confidence sources**: Extraction confidence, hedge words, uncertainty markers
   - **Rationale**: Clarify ambiguous content to improve graph quality

3. **DepthBreadthBalanceScorer** (weight: 0.20-0.25)
   - **Measures**: Whether strategy aligns with current depth/breadth needs
   - **Scoring logic**:
     - If breadth_needed AND strategy is explore_breadth → boost (1.3-1.5)
     - If depth_needed AND strategy is deepen_branch → boost (1.3-1.5)
     - If misaligned with current need → penalty (0.7-0.9)
   - **Depth calculation**: Average chain length from root nodes to terminal nodes
   - **Breadth calculation**: Percentage of elements mentioned
   - **Target ratios**: Configurable per methodology (e.g., 50/50 balanced, 60/40 depth-favoring)
   - **Rationale**: Prevent monotonic behavior (all depth or all breadth)

4. **EngagementScorer** (weight: 0.10-0.15)
   - **Measures**: Recent respondent engagement/momentum
   - **Scoring logic**:
     - Low engagement (3+ consecutive low momentum) → favor simpler strategies (boost = 1.2 for simple, penalty = 0.8 for complex)
     - High engagement → neutral or slight boost for complex strategies (1.0-1.1)
   - **Momentum indicators**: Response length, elaboration, enthusiasm markers
   - **Rationale**: Adapt to respondent fatigue/enthusiasm

5. **StrategyDiversityScorer** (weight: 0.10-0.15)
   - **Measures**: Recency of strategy use
   - **Scoring logic**:
     - Strategy used 0-1 times in last 5 turns → neutral (1.0)
     - Strategy used 2 times in last 5 turns → penalty (0.8)
     - Strategy used 3+ times in last 5 turns → strong penalty (0.6)
   - **Rationale**: Encourage varied questioning patterns, avoid repetitive interview feel

6. **NoveltyScorer** (weight: 0.10-0.15)
   - **Measures**: Whether focus target is "fresh" (not recently discussed)
   - **Scoring logic**:
     - Focus mentioned 0-1 times in last 8 turns → boost (1.2)
     - Focus mentioned 2-3 times → neutral (1.0)
     - Focus mentioned 4+ times → penalty (0.7)
   - **Rationale**: Distribute attention across topics, prevent fixation

**Weight Distribution Guidance**:
- **Coverage/Exploration** (CoverageGapScorer + DepthBreadthBalanceScorer): 40-50% combined
  - These drive the core interview goals (breadth and depth)
- **Quality** (AmbiguityScorer): 15-20%
  - Ensuring graph quality through clarification
- **Engagement/Adaptation** (EngagementScorer + StrategyDiversityScorer + NoveltyScorer): 30-40% combined
  - Adapting to respondent state and preventing monotony

**Normalization Requirements**:
- All Tier 2 scorers must output scores in comparable ranges
- Recommended range: [0, 2] with 1.0 as neutral
- Extreme values (< 0.5 or > 1.8) should be rare and well-justified
- Document the reasoning behind each scorer's scale

**Reasoning Trace**:
Each Tier 2 scorer must provide human-readable reasoning:
- Which factor was measured
- What value was observed
- Why this led to the assigned score
- Example: "CoverageGapScorer: Focus addresses 3 coverage gaps (unmentioned: product_A, no_reaction: feature_B, no_comprehension: benefit_C) → score=1.5 × weight=0.25 = 0.375 contribution"

---

## 3. Strategy Selection Pipeline

### 3.1 Complete Selection Algorithm

The selection process evaluates ALL (strategy, focus) combinations and selects the maximum score:

**Stage 1: Applicability Filtering**
- **Purpose**: Quickly eliminate strategies that cannot be used given current state
- **Examples**:
  - `deepen_branch` requires existing nodes to deepen → inapplicable if graph is empty
  - `explore_breadth` requires unmentioned elements → inapplicable if all mentioned
  - `closing` requires minimum turns elapsed → inapplicable before turn threshold
- **Implementation**: Simple boolean checks based on graph state, coverage state, turn count
- **Performance**: Should be O(1) per strategy, very fast

**Stage 2: Focus Generation**
- **Purpose**: For each applicable strategy, generate all valid focus targets
- **One strategy → Multiple focuses**: A single strategy can have 0 to 20+ focuses
  - `deepen_branch` on product_A → [clarify_feature_X, explore_benefit_Y, strengthen_relationship_Z, ...]
  - `explore_breadth` → [element_1, element_2, element_3, ...]
  - `closing` → [summary_focus] (typically just one)
- **Result**: If 3 strategies are applicable with average 5 focuses each = 15 candidates
- **Implementation**: Strategy-specific logic that queries graph state and coverage state

**Stage 3: Scoring All Candidates**
- **Process**: For each (strategy, focus) pair:
  1. Run all Tier 1 scorers sequentially
  2. If any veto → mark as vetoed, record vetoed_by, stop evaluation
  3. If all pass → run all Tier 2 scorers
  4. Compute final score: base + Σ(weight × scorer_output)
- **Output**: List of (final_score, strategy, focus, ScoringResult) tuples
- **Performance target**: < 50ms for typical ~15 candidates

**Stage 4: Filtering Vetoed Candidates**
- **Remove** all candidates where `vetoed_by` is not None
- **Edge case handling**: If ALL candidates vetoed, invoke fallback logic

**Stage 5: Maximum Selection**
- **Simple case**: Select candidate with highest final_score
- **Tie-breaking** (when multiple candidates have same score within tolerance):
  - **Option A**: Prefer strategy with higher `priority_base`
  - **Option B**: Prefer strategy used less recently (diversity)
  - **Option C**: Random selection (for exploration)
  - **Recommendation**: Use Option A (strategy priority) as default

**Stage 6: Logging and Traceability**
- Log selected strategy and focus with score
- Log top 3-5 alternatives for comparison
- Log complete reasoning trace from Tier 1 and Tier 2
- Store decision for post-interview analysis

### 3.2 Edge Cases and Fallback Logic

**Edge Case 1: No Applicable Strategies**
- **Cause**: All strategies filtered out in Stage 1
- **Example**: Interview at turn 2, closing requires min 10 turns, graph empty so no deepening, all elements mentioned so no breadth
- **Fallback**: Force enable emergency strategy (e.g., "reflection" or "meta_question")
- **Logging**: ERROR level - indicates configuration issue

**Edge Case 2: All Candidates Vetoed**
- **Cause**: Every (strategy, focus) fails Tier 1 constraints
- **Example**: All questions too similar to recent, all topics exhausted, respondent indicated no knowledge on everything
- **Fallback Options**:
  - **A**: Select "least-bad" vetoed candidate (one with highest partial Tier 2 score before veto)
  - **B**: Force closing strategy to end interview gracefully
  - **C**: Insert meta-question ("Is there anything else you'd like to share about {concept}?")
- **Logging**: WARNING level - indicates interview nearing natural end or respondent disengagement

**Edge Case 3: Zero Focuses Generated**
- **Cause**: Strategy is applicable but cannot generate any valid focuses
- **Example**: `deepen_branch` applicable but all nodes have high confidence and complete relationships
- **Handling**: Skip this strategy (treat as if not applicable)
- **Logging**: DEBUG level - normal occurrence

**Edge Case 4: Identical Scores**
- **Cause**: Multiple candidates have exactly the same final score
- **Frequency**: Should be rare (< 5% of selections) if scorers are well-calibrated
- **Handling**: Apply deterministic tie-breaker (strategy priority → alphabetical → random with seeded RNG)
- **Logging**: INFO level - document which tie-breaker was used

### 3.3 Performance Considerations

**Complexity Analysis**:
- S = number of strategies (typically 5-8)
- F = average focuses per strategy (typically 3-6)
- N = number of candidates = S × F (typically 15-30)
- T1 = number of Tier 1 scorers (typically 3-4)
- T2 = number of Tier 2 scorers (typically 5-7)

**Per-candidate cost**:
- Tier 1: O(T1) boolean checks, early exit on first veto
- Tier 2: O(T2) weighted computations (only if Tier 1 passes)
- Expected Tier 1 pass rate: 60-80% (40-20% vetoed)

**Total per-turn cost**:
- Worst case: N × (T1 + T2) evaluations
- Typical: 20 candidates × (3 + 5×0.7) ≈ 130 scorer invocations
- Target: < 50ms total selection time (< 0.5ms per scorer)

**Optimization Opportunities** (if needed):
- **Lazy evaluation**: Stop as soon as best_score > threshold (e.g., 2.5)
- **Caching**: Cache graph state computations used by multiple scorers
- **Parallel scoring**: Score multiple candidates concurrently (if thread-safe)
- **Focus pruning**: Limit focuses per strategy to top K (e.g., 5) based on quick heuristic

---

## 4. Configuration and Tuning

### 4.1 Configuration File Structure

The scoring system requires a configuration file (YAML format) specifying:

**Section 1: Tier 1 Scorers**
```
tier1_scorers:
  - id: knowledge_ceiling
    class: KnowledgeCeilingScorer
    enabled: true
    veto_threshold: 0.1
    config:
      min_confidence: 0.5
      negative_patterns: ["don't know", "not sure", "never heard"]
```

**Section 2: Tier 2 Scorers**
```
tier2_scorers:
  - id: coverage_gap
    class: CoverageGapScorer
    enabled: true
    weight: 0.25
    config:
      gap_types: ["unmentioned", "no_reaction"]
      boost_per_gap: 0.15
```

**Section 3: Validation Rules**
```
validation:
  tier2_weights_must_sum_to: 1.0
  tolerance: 0.001
  require_at_least_one_tier1: true
  warn_if_tier1_veto_rate_exceeds: 0.8
```

### 4.2 Weight Tuning Methodology

**Initial Weights** (based on domain expertise):
- Start with equal weights for all Tier 2 scorers
- Adjust based on strategic priorities:
  - If breadth is critical → increase CoverageGapScorer weight
  - If quality is critical → increase AmbiguityScorer weight
  - If engagement is critical → increase EngagementScorer weight

**Empirical Tuning** (based on interview data):
1. Run 20-50 interviews with initial weights
2. Analyze post-interview:
   - Which strategies were selected most often?
   - Were coverage goals met? (breadth/depth targets)
   - Did engagement drop prematurely?
   - Were there redundant questions despite scoring?
3. Adjust weights to correct imbalances
4. Iterate until satisfactory balance achieved

**Weight Constraints**:
- Minimum weight: 0.05 (5%) - below this, scorer has negligible impact
- Maximum weight: 0.40 (40%) - above this, single scorer dominates
- Recommended: Most weights in 0.10-0.25 range

**A/B Testing** (for production):
- Run parallel scoring with different weight configurations
- Compare interview quality metrics:
  - Graph completeness (coverage percentage)
  - Graph depth (average chain length)
  - Respondent satisfaction (post-interview survey)
  - Interview duration (time to saturation)
- Select configuration with best overall performance

### 4.3 Scorer Calibration

**For each Tier 2 scorer, verify**:
1. **Range compliance**: Does scorer actually produce scores in [0, 2]?
2. **Neutral baseline**: Does "normal/expected" state produce ~1.0?
3. **Distribution**: Are extreme values (< 0.7 or > 1.3) rare (< 10% of invocations)?
4. **Reasoning clarity**: Can a human understand why the score was assigned?

**Calibration process**:
1. Log all scorer outputs over 50 interviews
2. Check distribution:
   - Mean should be close to 1.0
   - Std dev should be 0.15-0.30 (not too narrow or too wide)
   - Min/max should be within [0.5, 1.8] for most scorers
3. Adjust scorer logic if distribution is problematic
4. Re-test until distribution is appropriate

---

## 5. Implementation Requirements for Coding Agent

### 5.1 Data Structures Needed

**Input Types**:
- `Strategy`: Contains id, name, priority_base, enabled flag
- `StrategyFocus`: Contains strategy_id and target (what to ask about)
- `ComputedState`: Contains graph_state, coverage_state, momentum, turn_count
- `History`: Contains conversation turns, recent questions

**Output Types**:
- `ScorerOutput`: Contains scorer_id, raw_score, is_veto flag, reasoning string
- `ScoringResult`: Contains strategy, focus, final_score, tier1_outputs, tier2_outputs, reasoning_trace, vetoed_by

### 5.2 Abstract Base Classes

**Tier1Scorer**: Base class for all hard constraint scorers
- Method: `evaluate()` returns ScorerOutput with is_veto flag
- Properties: config, veto_threshold, enabled

**Tier2Scorer**: Base class for all weighted scorers
- Method: `score()` returns ScorerOutput with raw_score
- Properties: config, weight, enabled
- Validation: weight must be in [0, 1]

### 5.3 Orchestrator Class

**TwoTierScoringEngine**: Main coordinator
- Loads and initializes all scorers from config
- Validates configuration (weights sum to 1.0)
- Method: `score_strategy_focus()` executes two-tier pipeline
- Implements early exit on Tier 1 veto
- Computes weighted sum for Tier 2
- Returns ScoringResult with complete reasoning trace

**StrategySelector**: High-level selection coordinator
- Loads strategies from config
- Method: `select()` runs complete pipeline:
  1. Filter by applicability
  2. Generate focuses for each applicable strategy
  3. Score all candidates via TwoTierScoringEngine
  4. Filter vetoed candidates
  5. Select maximum score
  6. Apply tie-breaking if needed
  7. Handle fallback if all vetoed
  8. Log decision with reasoning

### 5.4 Configuration Loading

**Requirements**:
- Load from YAML file
- Validate at startup:
  - All required fields present
  - Tier 2 weights sum to 1.0 ± tolerance
  - All scorer classes are importable
  - No duplicate scorer IDs
- Fail fast with clear error messages if invalid

### 5.5 Logging Requirements

**Levels**:
- DEBUG: Individual scorer outputs, candidate generation
- INFO: Strategy selection, final decision, top alternatives
- WARNING: All candidates vetoed, fallback triggered
- ERROR: No applicable strategies, configuration invalid

**Traceability**:
- Each selection must log complete reasoning trace
- Format: "scorer_id: observation → score (contribution)"
- Example: "coverage_gap: 3 gaps found → 1.5 × 0.25 = 0.375"

### 5.6 Error Handling

**Expected Errors**:
- `NoApplicableStrategiesError`: Raised when all strategies filtered in Stage 1
- `NoValidCandidatesError`: Raised when all candidates vetoed (after fallback attempts)
- `ConfigurationError`: Raised on invalid config (weights don't sum, missing required fields)
- `ScorerError`: Raised when individual scorer fails

**Error Recovery**:
- Configuration errors: Fail at startup (don't allow interview to begin)
- Runtime errors: Log extensively, attempt fallback, raise if fallback fails
- Scorer errors: Log warning, skip scorer (continue with remaining scorers)

---

## 6. Testing Strategy

### 6.1 Unit Testing

**Test each Tier 1 scorer**:
- Verify veto triggers on expected conditions
- Verify pass on valid conditions
- Verify reasoning is human-readable
- Test edge cases (empty state, missing data)

**Test each Tier 2 scorer**:
- Verify score range [0, 2]
- Verify neutral case returns ~1.0
- Verify boost cases return > 1.0
- Verify penalty cases return < 1.0
- Test edge cases

**Test TwoTierScoringEngine**:
- Verify early exit on first Tier 1 veto
- Verify weighted sum computation
- Verify reasoning trace format
- Test with all scorers enabled vs. selective

**Test StrategySelector**:
- Verify applicability filtering
- Verify focus generation
- Verify maximum selection
- Verify tie-breaking
- Verify fallback on all-vetoed

### 6.2 Integration Testing

**Test realistic scenarios**:
- Early interview (turn 2): Should favor breadth strategies
- Mid interview (turn 10): Should balance depth and breadth
- Late interview (turn 18): Should favor depth or closing
- Low engagement: Should favor simpler strategies
- All topics exhausted: Should trigger closing

**Test edge cases**:
- All strategies vetoed → fallback works
- No applicable strategies → error or fallback
- Identical scores → tie-breaking works
- Empty graph → appropriate strategy selection

### 6.3 Scoring Distribution Analysis

**After 20+ interviews, verify**:
- Tier 1 veto rate: 20-40% (not too permissive, not too restrictive)
- Tier 2 score distribution: Mean ~1.5-2.0, std dev ~0.3-0.5
- Strategy diversity: No single strategy > 60% of selections
- Coverage achievement: 80%+ of elements mentioned
- Depth achievement: Average chain length > 3

---

## 7. Comparison to Previous Multiplicative Approach

### 7.1 Key Differences

| Aspect | Multiplicative (v1) | Two-Tier Hybrid (v2) |
|--------|---------------------|----------------------|
| Veto mechanism | Implicit (score drops to ~0) | Explicit (boolean flag, early exit) |
| Score predictability | Highly nonlinear, explosive | Linear, bounded |
| Weight interpretation | Exponents (unclear meaning) | Percentages (clear importance) |
| Debugging | "Why did score explode?" | "Which constraint failed?" or "Which factors dominated?" |
| Tuning difficulty | Very difficult (nonlinear interactions) | Moderate (linear contributions) |
| Compensation | Minimal (penalizes imbalance) | Controllable (weighted trade-offs) |
| Production use | Rare (research-oriented) | Standard (MCDA and dialogue systems) |

### 7.2 Migration Path

**Phase 1: Parallel Implementation**
- Implement two-tier system alongside multiplicative
- Run both on same interviews
- Compare selections and scores
- Analyze divergence cases

**Phase 2: Validation**
- Tune two-tier weights to match desired behavior
- Verify coverage and depth metrics similar or better
- Validate reasoning traces are clearer
- Confirm no critical regressions

**Phase 3: Cutover**
- Switch to two-tier as primary
- Retain multiplicative as fallback (disabled by default)
- Monitor for unexpected behavior
- Iterate on weights based on production data

---

## 8. Success Criteria

### 8.1 Functional Requirements

- ✅ All Tier 1 scorers implemented and tested
- ✅ All Tier 2 scorers implemented and tested
- ✅ Weights sum to 1.0 (validated at startup)
- ✅ Early exit on first veto (Tier 1)
- ✅ Weighted sum correctly computed (Tier 2)
- ✅ Complete reasoning trace available
- ✅ Fallback logic handles all-vetoed case
- ✅ Configuration-driven (no hardcoded thresholds)

### 8.2 Performance Requirements

- ✅ Strategy selection < 50ms per turn
- ✅ Individual scorer < 5ms average
- ✅ Configuration loading < 100ms at startup
- ✅ Memory footprint < 50MB for scoring system

### 8.3 Quality Requirements

- ✅ Tier 1 veto rate: 20-40% (indicates well-calibrated constraints)
- ✅ Coverage achievement: 80%+ elements mentioned
- ✅ Depth achievement: Average chain length ≥ 3
- ✅ Strategy diversity: No single strategy > 60% selections
- ✅ Respondent satisfaction: Minimal redundant questions (< 10%)

### 8.4 Maintainability Requirements

- ✅ Clear separation: Tier 1 vs. Tier 2 logic
- ✅ Extensibility: New scorers can be added without modifying orchestrator
- ✅ Configuration: All tunable parameters in YAML
- ✅ Documentation: Each scorer has clear docstring explaining logic
- ✅ Logging: Complete audit trail of every decision

---

## 9. References

### Academic Literature

1. Choo, E.U. & Wedley, W.C. (2008). "Comparing Fundamentals of Additive and Multiplicative Aggregation in Ratio Scale Multi-Criteria Decision Making." The Open Operational Research Journal, 2, 1-7.

2. Tofallis, C. (2014). "Add or Multiply? A Tutorial on Ranking and Choosing with Multiple Criteria." INFORMS Transactions on Education, 14(3), 109-119.

3. Wikipedia. (2025). "Weighted Product Model." Multi-criteria decision analysis.

4. ScienceDirect. (2020). "Multiple-Criteria Decision Analysis - Overview."

5. Springer. (2021). "A Hybrid Decision Support Model Using Grey Relational Analysis and the Additive-Veto Model."

### Dialogue Systems Literature

6. Alibaba DAMO Academy. "Progress in Dialog Management Model Research."

7. Rasa. (2020). "Zooming in on Dialogue Management in Rasa 2.0."

8. MIT Press. (2024). "Decision-Oriented Dialogue for Human-AI Collaboration." Transactions of the Association for Computational Linguistics.

9. MDPI. (2023). "A Knowledge-Grounded Task-Oriented Dialogue System with Hierarchical Structure."

10. arXiv. (2024). "Script-Based Dialog Policy Planning for LLM-Powered Conversational Agents."

---

## Appendix A: Scorer Implementation Checklist

For each scorer, verify:

- [ ] Class inherits from Tier1Scorer or Tier2Scorer
- [ ] `__init__` accepts config dict
- [ ] Config parameters validated (ranges, required fields)
- [ ] `evaluate()` or `score()` method implemented
- [ ] Returns properly formatted ScorerOutput
- [ ] Reasoning string is clear and specific
- [ ] Edge cases handled (empty state, missing data)
- [ ] Unit tests cover normal and edge cases
- [ ] Docstring explains purpose and logic
- [ ] Configuration example provided

## Appendix B: Configuration Template

See `interview_config.yaml` for complete example with all scorers configured.

Required sections:
- `scoring.tier1_scorers`: List of hard constraint scorers
- `scoring.tier2_scorers`: List of weighted scorers
- `scoring.validation`: Validation rules
- Strategy-specific overrides (if needed)

## Appendix C: Glossary

- **Veto**: A hard constraint that immediately disqualifies a candidate (score = 0)
- **Weight**: A percentage (0-1) indicating relative importance in Tier 2
- **Focus**: The specific target (node, element, relationship) a strategy will address
- **Applicability**: Whether a strategy can be used given current state (boolean check)
- **Coverage gap**: An element or aspect that has not been explored
- **Saturation**: The state when further questions yield diminishing information
- **Momentum**: Respondent engagement level based on response quality
