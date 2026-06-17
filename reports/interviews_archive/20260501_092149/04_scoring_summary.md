# Scoring Summary

Source: `04_scoring.csv`
Total rows: 15,136 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1086 | 1116 | 97% | 0.300 |
| convgraph.node.focus.count.none | 981 | 1116 | 88% | 0.200 |
| interview.strategy.self_count | 844 | 1510 | 56% | -0.078 |
| meta.saturation.canonical.high | 602 | 744 | 81% | -0.300 |
| convgraph.node.novelty.high | 519 | 1116 | 46% | 0.267 |
| response.semantic.llm.certainty.low | 332 | 372 | 89% | 0.400 |
| convgraph.node.chain.has_attribute_foundation.true | 242 | 430 | 56% | 0.075 |
| convgraph.node.chain.has_attribute_foundation.false | 188 | 430 | 44% | -0.150 |
| response.semantic.llm.engagement.high | 156 | 372 | 42% | 0.100 |
| convgraph.node.recency | 135 | 1116 | 12% | 0.231 |
| convgraph.node.exhaustion | 135 | 1116 | 12% | -0.130 |
| convgraph.node.llm.charge.negative | 106 | 314 | 34% | 0.275 |
| convgraph.node.llm.elaboration.low | 105 | 157 | 67% | 0.150 |
| canongraph.node.novelty.new | 64 | 372 | 17% | 0.300 |
| response.semantic.llm.certainty.mid | 40 | 372 | 11% | 0.200 |
| convgraph.node.chain.gap.below.true | 35 | 215 | 16% | 0.500 |
| convgraph.node.llm.charge.positive | 34 | 157 | 22% | 0.100 |
| meta.saturation.conversation.high | 30 | 744 | 4% | -0.400 |
| convgraph.node.chain.gap.above.true | 23 | 215 | 11% | 0.500 |
| convgraph.node.yield_stagnation.true | 20 | 372 | 5% | 0.250 |
| meta.saturation.canonical | 11 | 11 | 100% | -0.272 |
| interview.phase.mid | 6 | 11 | 54% | -3.000 |
| interview.phase.early | 4 | 11 | 36% | -3.000 |
| interview.phase.late | 1 | 11 | 9% | 2.000 |

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
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.focus.count.medium | 0.20 |
| convgraph.node.is_orphan.true | 0.50 |
| convgraph.node.llm.elaboration.high | 0.20 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1086 | 1116 | 97% |
| convgraph.node.focus.count.none | 981 | 1116 | 88% |
| meta.saturation.canonical.high | 602 | 744 | 81% |
| response.semantic.llm.certainty.low | 332 | 372 | 89% |
| meta.saturation.canonical | 11 | 11 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/11 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 2 | early | ground | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 4 | early | anchor | ground | 1.20 | 1.20 | 0.000 |
| 5 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 11 | late | close | ground | 1.50 | 0.90 | 1.200 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 301.920 | -88.934 | 212.986 |
| anchor | 284.380 | -110.868 | 173.512 |
| surface_tension | 159.050 | 0.000 | 159.050 |
| ground | 265.220 | -147.716 | 117.504 |
| revitalize | 0.000 | -2.990 | -2.990 |
| close | 2.000 | -30.000 | -28.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| carbonation cuts through heavy food | b104dc94 | 2 |
| artificial sweetener taste is off-putting | 0a2106c2 | 1 |
| feel at ease and unselfconscious while drinking | 726b00d0 | 1 |
| low engagement with fizzy drinks category | 0fc41e1d | 1 |
| drinking without a guilty inner voice | 7689bc60 | 1 |
| eating out at a restaurant | 98148e9d | 1 |
| lingering metallic or chemical aftertaste | fd36c0cd | 1 |
| feel free from self-monitoring and dietary vigilance | fe39a0ee | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
