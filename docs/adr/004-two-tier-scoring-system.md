# ADR-004: Adopt Two-Tier Hybrid Scoring System

## Status
Accepted

## Context
**Supersedes**: ADR-003 (Phase 3 multiplicative approach)

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

## Implementation

See beads issues for detailed tasks:
- `interview-system-v2-xxx`: Implement two-tier scoring engine
- `interview-system-v2-yyy`: Implement Tier 1 scorers (3)
- `interview-system-v2-zzz`: Implement Tier 2 scorers (6)

### Migration Path

1. Implement TwoTierScoringEngine alongside ArbitrationEngine
2. Implement all 9 scorers
3. Replace StrategyService to use TwoTierScoringEngine
4. Remove ArbitrationEngine and multiplicative code
5. Add YAML configuration loading

### Strategies

Expanding from 3 to 5+ strategies:
- **deepen**: Deepen existing branches
- **broaden**: Explore new aspects
- **cover_element**: Cover stimulus elements
- **closing**: End interview gracefully (NEW)
- **reflection**: Meta-questions when stuck (NEW)

## Consequences

### Positive
- Strategy selection becomes transparent and debuggable
- Scores bounded and predictable
- Explicit veto behavior prevents inappropriate questions
- Weights can be tuned from interview data
- Aligns with production dialogue system practices

### Negative
- More code to maintain (9 scorers vs 5)
- Initial configuration complexity
- Need to tune weights from real data
- Cosine similarity adds computational overhead

### Neutral
- Cosine similarity requires TF-IDF but can cache vectors
- Direct replacement means no A/B comparison data
- More strategies require focus generation logic

## Related Decisions
- **ADR-001**: Dual sync/async API - Unaffected
- **ADR-002**: Streamlit framework choice - Unaffected
- **ADR-003**: Superseded by this decision (two-tier vs multiplicative)

## References
- Choo & Wedley (2008): "Comparing Fundamentals of Additive and Multiplicative Aggregation"
- Tofallis (2014): "Add or Multiply? A Tutorial on Ranking and Choosing"
- `docs/theory/two_tier_scoring_system_design.md`: Complete design specification
- Rasa 2.0: Dialogue management hierarchy
- Alibaba DAMO: Rule-based DM models
