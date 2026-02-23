# ADR-004: Adopt Two-Tier Hybrid Scoring System

## Status
**Superseded by ADR-014** (Signal Pools Architecture)

> **Note**: This ADR was never implemented. The system evolved toward a signal-pools-based approach (ADR-014) rather than the two-tier hybrid scoring described here. The Signal Pools architecture uses YAML-configured signal detection with weighted additive scoring, which achieved the same goals of interpretability and predictable scoring without the complexity of separate Tier 1/Tier 2 scorers.

## Context
**Supersedes**: ADR-003 (Phase 3 multiplicative approach)
**Superseded By**: ADR-014 (Signal Pools Architecture)

The interview system currently has three options for strategy selection:

1. **Phase 2 (current)**: Hardcoded "deepen" strategy with no adaptivity
2. **Phase 3 multiplicative** (ADR-003): `score = base × ∏(scorer^weight)` - complex tuning, unpredictable
3. **Two-tier hybrid**: Separate hard constraints from soft preferences

After researching Multi-Criteria Decision Analysis (MCDA) literature and production dialogue systems (Rasa, Alibaba DAMO), the two-tier approach emerges as the industry standard for adaptive decision-making.

### Problems with Multiplicative Scoring

From research by Choo & Wedley (2008) and Tofallis (2014):
- **Score explosion**: With 14 scorers, modest boosts compound dramatically (1.2^14 = 11.4×)
- **Unpredictable interactions**: Small changes in one scorer flip entire rankings
- **Weight interpretation**: Weights are exponents with "complicated meanings which are not well understood"
- **Difficult tuning**: Adjusting one weight affects all interactions non-linearly

### Why Two-Tier Works

Production systems use **priority-based hierarchies**:
- **Rasa**: RulePolicy → MemoizationPolicy → TEDPolicy
- **Alibaba DAMO**: "Rule-based DM models" with ML as supplementary
- **Medical AI**: Expert scripts (hard constraints) with flexible LLM generation

This mirrors human decision-making: "Must-haves" (Tier 1 vetoes) vs "Nice-to-haves" (Tier 2 trade-offs).

## Decision
**Adopt the two-tier hybrid scoring system** with direct replacement of current hardcoded approach.

### Architecture

```
Tier 1: Hard Constraints (Boolean Vetoes)
├── KnowledgeCeilingScorer - "don't know" detection
├── ElementExhaustedScorer - mention count threshold
└── RecentRedundancyScorer - cosine similarity (TF-IDF)

Tier 2: Weighted Additive Scoring
├── CoverageGapScorer (weight: ~0.20)
├── AmbiguityScorer (weight: ~0.15)
├── DepthBreadthBalanceScorer (weight: ~0.20)
├── EngagementScorer (weight: ~0.15)
├── StrategyDiversityScorer (weight: ~0.15)
└── NoveltyScorer (weight: ~0.15)

Formula: final_score = priority_base + Σ(weight_i × score_i)
where Σ(weights) = 1.0
```

### Key Implementation Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Similarity method | Cosine (TF-IDF) | Good accuracy, medium complexity |
| Fallback behavior | Force closing strategy | Clean interview termination |
| Migration | Direct replacement | Faster, simplifies codebase |
| Strategies | Expand from 3 to 5+ | Add closing, reflection, etc. |

## Rationale

### Benefits
1. **Interpretability**: "Coverage gaps are 25% of the decision" vs "why did score explode?"
2. **Predictable**: Linear combination prevents score explosions
3. **Explicit vetoes**: Boolean flags vs implicit low scores
4. **Production-proven**: Used in real dialogue systems at scale
5. **Easier tuning**: Weights as percentages, not exponents

### Costs
1. **New components**: 9 scorers vs current 5
2. **Configuration system**: YAML file with validation
3. **Cosine similarity**: Need TF-IDF vectorization
4. **Implementation time**: ~2-3 days vs ~1 day for multiplicative

### Why Not Alternatives?

| Alternative | Rejected Because |
|-------------|------------------|
| Phase 2 hardcoded | No adaptivity, questions are repetitive |
| Multiplicative | Unpredictable, hard to debug, not production-ready |
| Incremental migration | Slower; direct replacement simplifies codebase |

## Actual Implementation (ADR-014 Signal Pools)

The system ultimately implemented **Signal Pools Architecture** (ADR-014) instead of the two-tier approach. Key differences:

| Aspect | Two-Tier (This ADR) | Signal Pools (Implemented) |
|--------|---------------------|---------------------------|
| Scoring | Tier 1 vetoes + Tier 2 weighted | Weighted additive with phase multipliers |
| Configuration | Custom scorer classes | YAML signal_weights per strategy |
| Hard constraints | Boolean vetoes | Negative weights in YAML config |
| Node awareness | Separate node selection | Joint strategy-node scoring (D1) |
| Similarity | TF-IDF cosine | Sentence-transformers embeddings |

The Signal Pools approach achieved the same goals:
- ✅ **Interpretability**: YAML weights are explicit percentages
- ✅ **Predictable**: Linear scoring formula with bounded signals
- ✅ **Easier tuning**: Edit YAML, no code changes
- ✅ **Production-proven**: Similar to implemented architecture

## Migration Path (Historical)

1. Implement TwoTierScoringEngine alongside ArbitrationEngine
2. Implement all 9 scorers
3. Replace StrategyService to use TwoTierScoringEngine
4. Remove ArbitrationEngine and multiplicative code
5. Add YAML configuration loading

**Actual Path Taken**: See ADR-014 for the Signal Pools implementation that replaced both the multiplicative approach and this two-tier design.

## Consequences

### Historical Note
This ADR represents a design direction that was superseded before implementation. The Signal Pools architecture (ADR-014) became the production approach, offering similar benefits with less complexity.

### Related Decisions
- **ADR-001**: Dual sync/async API - Unaffected
- **ADR-002**: Streamlit framework choice - Unaffected
- **ADR-003**: Superseded by this decision (two-tier vs multiplicative)
- **ADR-014**: Supersedes this decision (Signal Pools Architecture)

## References
- Choo & Wedley (2008): "Comparing Fundamentals of Additive and Multiplicative Aggregation"
- Tofallis (2014): "Add or Multiply? A Tutorial on Ranking and Choosing"
- `docs/theory/two_tier_scoring_system_design.md`: Complete design specification
- Rasa 2.0: Dialogue management hierarchy
- Alibaba DAMO: Rule-based DM models
- **ADR-014**: Signal Pools Architecture (implemented approach)
