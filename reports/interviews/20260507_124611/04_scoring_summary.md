# Scoring Summary

Source: `04_scoring.csv`
Total rows: 18,107 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 978 | 1017 | 96% | 0.300 |
| meta.saturation.canonical.high | 786 | 1017 | 77% | -0.300 |
| convgraph.node.focus.count.none | 774 | 1017 | 76% | 0.200 |
| interview.strategy.self_count | 738 | 1384 | 53% | -0.168 |
| convgraph.node.chain.has_attribute_foundation.true | 584 | 678 | 86% | 0.075 |
| convgraph.node.novelty.high | 472 | 1356 | 35% | 0.263 |
| convgraph.node.recency | 324 | 1356 | 24% | 0.190 |
| convgraph.node.llm.charge.negative | 272 | 678 | 40% | 0.275 |
| convgraph.node.exhaustion | 243 | 1017 | 24% | -0.141 |
| convgraph.node.llm.elaboration.low | 184 | 339 | 54% | 0.150 |
| response.semantic.llm.engagement.high | 135 | 339 | 40% | 0.100 |
| convgraph.node.chain.gap.above.true | 109 | 339 | 32% | 0.500 |
| response.semantic.llm.certainty.low | 96 | 339 | 28% | 0.400 |
| convgraph.node.chain.has_attribute_foundation.false | 94 | 678 | 14% | -0.150 |
| response.semantic.llm.certainty.mid | 57 | 339 | 17% | 0.200 |
| convgraph.node.llm.charge.positive | 52 | 339 | 15% | 0.100 |
| convgraph.node.llm.elaboration.high | 48 | 1017 | 5% | 0.117 |
| convgraph.node.yield_stagnation.true | 47 | 339 | 14% | 0.250 |
| convgraph.node.chain.gap.below.true | 28 | 339 | 8% | 0.500 |
| convgraph.state.node.orphan_ratio.mid | 21 | 692 | 3% | 0.245 |
| meta.saturation.canonical | 13 | 14 | 93% | -0.281 |
| convgraph.node.focus.count.medium | 8 | 678 | 1% | -0.050 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| convgraph.node.is_orphan.true | 6 | 339 | 2% | 0.500 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.canonical`
- `convgraph.state.node.orphan_ratio.mid`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| canongraph.node.novelty.new | 0.30 |
| convgraph.node.focus.count.high | 0.40 |
| convgraph.state.node.orphan_ratio.high | 0.40 |
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 978 | 1017 | 96% |
| convgraph.node.chain.has_attribute_foundation.true | 584 | 678 | 86% |
| meta.saturation.canonical | 13 | 14 | 93% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | ground | ascend | 1.20 | 1.00 | 0.230 |
| 5 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 6 | mid | ground | ascend | 1.50 | 1.30 | 0.228 |
| 7 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ground | 1.30 | 1.50 | -0.242 |
| 11 | mid | ground | ascend | 1.50 | 1.30 | 0.206 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 14 | late | close | ground | 1.50 | 0.90 | 1.200 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 389.455 | -119.924 | 269.531 |
| anchor | 260.770 | -95.228 | 165.542 |
| surface_tension | 135.178 | -78.600 | 56.578 |
| ground | 225.055 | -182.736 | 42.319 |
| revitalize | 0.150 | -3.650 | -3.500 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| feel less conflicted rather than virtuous about drink choices | 611ff04d | 3 |
| awareness of high sugar content in regular Coke | 1ed1475f | 1 |
| choosing between sugar guilt and going without a desired drink | 11324c39 | 1 |
| post-consumption guilt from unhealthy drink choices | 23871f5e | 1 |
| feel good about drink choices without guilt | 3b2e6913 | 1 |
| distraction from work dissolves health concern entirely | 3ffeea51 | 1 |
| get a caffeine lift without extra calories | b8f87e66 | 1 |
| having a drink option that feels like no compromise | d20660b6 | 1 |
| making choices that undermine personal health goals | d4ae8dab | 1 |
| feel aligned with personal health standards | eb092427 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
