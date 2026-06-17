# Scoring Summary

Source: `04_scoring.csv`
Total rows: 8,342 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 765 | 789 | 97% | 0.300 |
| convgraph.node.focus.count.none | 684 | 789 | 87% | 0.200 |
| interview.strategy.self_count | 533 | 816 | 65% | -0.086 |
| convgraph.node.novelty.high | 390 | 789 | 49% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.true | 164 | 302 | 54% | 0.075 |
| convgraph.node.chain.has_attribute_foundation.false | 138 | 302 | 46% | -0.150 |
| response.semantic.llm.engagement.high | 131 | 272 | 48% | 0.085 |
| convgraph.node.recency | 105 | 789 | 13% | 0.235 |
| convgraph.node.exhaustion | 105 | 789 | 13% | -0.102 |
| convgraph.node.llm.elaboration.low | 55 | 112 | 49% | 0.150 |
| convgraph.node.chain.gap.below.true | 49 | 151 | 32% | 0.500 |
| canongraph.node.novelty.new | 48 | 263 | 18% | 0.300 |
| convgraph.node.llm.charge.positive | 48 | 112 | 43% | 0.100 |
| convgraph.node.llm.charge.negative | 36 | 112 | 32% | 0.300 |
| convgraph.node.chain.gap.above.true | 31 | 151 | 20% | 0.500 |
| response.semantic.llm.engagement.mid | 10 | 18 | 56% | 0.400 |
| meta.saturation.canonical | 9 | 9 | 100% | 0.170 |
| meta.saturation.conversation | 8 | 9 | 89% | 0.120 |
| response.semantic.llm.certainty.low | 5 | 9 | 56% | 1.000 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| response.semantic.llm.engagement.trend.fatigued | 4 | 18 | 22% | 0.200 |
| response.semantic.llm.engagement.trend.shallowing | 4 | 18 | 22% | 0.200 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| response.semantic.llm.certainty.mid | 2 | 9 | 22% | 0.700 |
| interview.phase.late | 1 | 9 | 11% | -0.500 |

## Global Signals

- `response.semantic.llm.engagement.trend.fatigued`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.mid`
- `response.semantic.llm.engagement.low`
- `interview.strategy.self_count`
- `response.semantic.llm.engagement.high`
- `interview.strategy.self_count.high`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`
- `meta.saturation.conversation`
- `meta.saturation.canonical`
- `response.semantic.llm.certainty.low`
- `response.semantic.llm.certainty.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.focus.count.medium | 0.20 |
| convgraph.node.is_orphan.true | 0.50 |
| convgraph.node.llm.elaboration.high | 0.20 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.low | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 765 | 789 | 97% |
| convgraph.node.focus.count.none | 684 | 789 | 87% |
| meta.saturation.canonical | 9 | 9 | 100% |
| meta.saturation.conversation | 8 | 9 | 89% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ground | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | ground | ascend | 1.20 | 1.00 | 0.278 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | late | validate | ascend | 1.50 | 1.00 | 0.480 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 205.170 | -12.162 | 193.008 |
| ground | 202.155 | -36.464 | 165.691 |
| ascend | 221.105 | -58.716 | 162.389 |
| revitalize | 5.600 | -2.100 | 3.500 |
| elaborate | 2.000 | -2.000 | 0.000 |
| validate | 8.887 | -24.000 | -15.113 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| guilt-free drinking improves overall experience | 31ba74af | 2 |
| cold caffeinated drink as habitual go-to | 3316cb12 | 1 |
| avoid feeling like I'm punishing myself | 3ce48b74 | 1 |
| feel like I'm treating myself, not just hydrating | 4bce5cc1 | 1 |
| having something to do with hands while working | 6cf4724c | 1 |
| carbonation sensation snapping out of sluggishness | 7256d5a3 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
