# Scoring Summary

Source: `04_scoring.csv`
Total rows: 20,174 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1095 | 1134 | 97% | 0.300 |
| meta.saturation.canonical.high | 972 | 1134 | 86% | -0.300 |
| convgraph.node.focus.count.none | 936 | 1134 | 82% | 0.200 |
| interview.strategy.self_count | 801 | 1540 | 52% | -0.130 |
| convgraph.state.node.orphan_ratio.mid | 757 | 770 | 98% | 0.248 |
| convgraph.node.chain.has_attribute_foundation.false | 624 | 756 | 82% | -0.150 |
| convgraph.node.novelty.high | 532 | 1512 | 35% | 0.263 |
| convgraph.node.recency | 264 | 1512 | 18% | 0.197 |
| convgraph.node.chain.gap.below.true | 255 | 378 | 68% | 0.500 |
| convgraph.node.llm.charge.negative | 242 | 756 | 32% | 0.275 |
| convgraph.node.chain.gap.above.true | 239 | 378 | 63% | 0.500 |
| convgraph.node.is_orphan.true | 237 | 378 | 63% | 0.500 |
| convgraph.node.exhaustion | 198 | 1134 | 18% | -0.121 |
| convgraph.node.llm.elaboration.low | 171 | 378 | 45% | 0.150 |
| response.semantic.llm.engagement.low | 146 | 770 | 19% | -0.288 |
| meta.saturation.conversation.high | 144 | 756 | 19% | -0.400 |
| convgraph.node.chain.has_attribute_foundation.true | 132 | 756 | 18% | 0.075 |
| response.semantic.llm.engagement.high | 128 | 378 | 34% | 0.100 |
| convgraph.node.llm.elaboration.high | 120 | 1134 | 11% | 0.117 |
| response.semantic.llm.certainty.low | 112 | 378 | 30% | 0.400 |
| convgraph.node.llm.charge.positive | 88 | 378 | 23% | 0.100 |
| response.semantic.llm.certainty.mid | 52 | 378 | 14% | 0.200 |
| convgraph.node.yield_stagnation.true | 34 | 378 | 9% | 0.250 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.264 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| convgraph.state.node.orphan_ratio.high | 6 | 378 | 2% | 0.400 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |
| response.semantic.llm.engagement.trend.fatigued | 1 | 14 | 7% | 0.900 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 14 | 7% | 0.400 |

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
| convgraph.node.focus.count.medium | 0.20 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1095 | 1134 | 97% |
| meta.saturation.canonical.high | 972 | 1134 | 86% |
| convgraph.node.focus.count.none | 936 | 1134 | 82% |
| convgraph.state.node.orphan_ratio.mid | 757 | 770 | 98% |
| convgraph.node.chain.has_attribute_foundation.false | 624 | 756 | 82% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | early | ascend | ground | 1.00 | 1.20 | -0.350 |
| 5 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 10 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 11 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 13 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 14 | late | close | revitalize | 1.50 | 1.20 | 0.600 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ground | 506.505 | -173.304 | 333.201 |
| anchor | 493.770 | -177.882 | 315.888 |
| ascend | 402.655 | -241.206 | 161.449 |
| surface_tension | 135.428 | -97.200 | 38.228 |
| revitalize | 4.450 | -3.700 | 0.750 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| calibrating drink type and quantity to the formality of the social occasion | 14d0704d | 2 |
| rushing before work in the morning | 2598b92b | 2 |
| being at someone else's house with only regular soda available | 4e5f0913 | 2 |
| deliberating over every drink choice feels like too much effort | 62dba493 | 2 |
| minimizing what to carry when heading to a small hangout | 2a4d8eec | 1 |
| feeling tired and needing to wake up | 35e2891a | 1 |
| drink availability at home in the moment of need | 7aaee0ee | 1 |
| arriving at a party without a drink in hand | c3bf068b | 1 |
| having any drink available at a social gathering matters more than which drink it is | f3edf046 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
