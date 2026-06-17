# Scoring Summary

Source: `04_scoring.csv`
Total rows: 31,369 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 2193 | 2262 | 97% | 0.300 |
| interview.strategy.self_count | 1912 | 3044 | 63% | -0.109 |
| convgraph.node.focus.count.none | 1908 | 2262 | 84% | 0.200 |
| meta.saturation.canonical.high | 918 | 2262 | 41% | -0.300 |
| convgraph.node.novelty.high | 801 | 2262 | 35% | 0.267 |
| convgraph.node.is_orphan.true | 656 | 754 | 87% | 0.500 |
| convgraph.node.chain.has_attribute_foundation.false | 616 | 850 | 72% | -0.150 |
| response.semantic.llm.engagement.high | 491 | 754 | 65% | 0.100 |
| convgraph.node.exhaustion | 354 | 2262 | 16% | -0.129 |
| convgraph.node.recency | 354 | 2262 | 16% | 0.219 |
| convgraph.node.chain.gap.above.true | 315 | 425 | 74% | 0.500 |
| convgraph.node.chain.gap.below.true | 274 | 425 | 64% | 0.500 |
| convgraph.node.chain.has_attribute_foundation.true | 234 | 850 | 28% | 0.075 |
| response.semantic.llm.certainty.low | 233 | 754 | 31% | 0.400 |
| response.semantic.llm.certainty.mid | 184 | 754 | 24% | 0.200 |
| convgraph.node.llm.elaboration.low | 157 | 329 | 48% | 0.150 |
| convgraph.node.llm.charge.positive | 133 | 329 | 40% | 0.100 |
| convgraph.node.llm.charge.negative | 112 | 658 | 17% | 0.275 |
| convgraph.node.llm.elaboration.high | 96 | 987 | 10% | 0.117 |
| canongraph.node.novelty.new | 94 | 754 | 12% | 0.300 |
| convgraph.node.yield_stagnation.true | 84 | 754 | 11% | 0.250 |
| convgraph.node.focus.count.high | 38 | 754 | 5% | -0.400 |
| convgraph.node.focus.count.medium | 20 | 1508 | 1% | -0.050 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.223 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.canonical`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 2193 | 2262 | 97% |
| convgraph.node.focus.count.none | 1908 | 2262 | 84% |
| convgraph.node.is_orphan.true | 656 | 754 | 87% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | ascend | 1.20 | 1.00 | 0.320 |
| 2 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 3 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 4 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 5 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | anchor | ascend | 1.00 | 1.30 | -0.582 |
| 11 | mid | anchor | ascend | 1.00 | 1.30 | -0.582 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 874.490 | -177.652 | 696.838 |
| ground | 642.535 | -157.304 | 485.231 |
| ascend | 680.835 | -296.636 | 384.199 |
| surface_tension | 166.000 | -91.800 | 74.200 |
| revitalize | 0.000 | -3.125 | -3.125 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| questioning whether drink choice is genuine preference or mere habit | a604576d | 2 |
| needing something cold and fizzy in the moment | 96e04712 | 2 |
| feeling thirsty or hot in the moment | 1ba74bd1 | 1 |
| artificial sweetener aftertaste in competing sugar-free drinks | 2daaa893 | 1 |
| mid-afternoon energy slump at work | 3fc3b5a4 | 1 |
| at work during the afternoon | 2eb4f41b | 1 |
| being out with friends or at a meal | afd3b8aa | 1 |
| feeling annoyed by having to evaluate drink choices | f37d754d | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
