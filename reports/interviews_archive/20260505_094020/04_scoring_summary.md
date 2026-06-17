# Scoring Summary

Source: `04_scoring.csv`
Total rows: 26,919 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1872 | 1941 | 96% | 0.300 |
| convgraph.node.focus.count.none | 1545 | 1941 | 80% | 0.200 |
| interview.strategy.self_count | 1470 | 2616 | 56% | -0.121 |
| meta.saturation.canonical.high | 1356 | 1941 | 70% | -0.300 |
| convgraph.node.novelty.high | 678 | 1941 | 35% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.false | 664 | 762 | 87% | -0.150 |
| convgraph.node.is_orphan.true | 647 | 647 | 100% | 0.500 |
| convgraph.node.recency | 396 | 1941 | 20% | 0.217 |
| convgraph.node.exhaustion | 396 | 1941 | 20% | -0.142 |
| convgraph.node.chain.gap.above.true | 340 | 381 | 89% | 0.500 |
| convgraph.node.chain.gap.below.true | 332 | 381 | 87% | 0.500 |
| response.semantic.llm.engagement.high | 259 | 647 | 40% | 0.100 |
| response.semantic.llm.certainty.low | 243 | 647 | 38% | 0.400 |
| convgraph.node.llm.elaboration.low | 184 | 266 | 69% | 0.150 |
| convgraph.node.llm.charge.negative | 116 | 532 | 22% | 0.275 |
| convgraph.node.chain.has_attribute_foundation.true | 98 | 762 | 13% | 0.075 |
| convgraph.node.yield_stagnation.true | 96 | 647 | 15% | 0.250 |
| canongraph.node.novelty.new | 80 | 647 | 12% | 0.300 |
| response.semantic.llm.certainty.mid | 60 | 647 | 9% | 0.200 |
| convgraph.node.llm.charge.positive | 50 | 266 | 19% | 0.100 |
| convgraph.node.focus.count.high | 38 | 647 | 6% | -0.400 |
| convgraph.node.focus.count.medium | 26 | 1294 | 2% | -0.050 |
| convgraph.node.llm.elaboration.high | 15 | 798 | 2% | 0.117 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.248 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| response.semantic.llm.engagement.trend.fatigued | 2 | 14 | 14% | 0.900 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 14 | 7% | 0.400 |

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

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1872 | 1941 | 96% |
| convgraph.node.chain.has_attribute_foundation.false | 664 | 762 | 87% |
| convgraph.node.is_orphan.true | 647 | 647 | 100% |
| convgraph.node.chain.gap.above.true | 340 | 381 | 89% |
| convgraph.node.chain.gap.below.true | 332 | 381 | 87% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 3/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | ascend | 1.20 | 1.00 | 0.320 |
| 2 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 3 | early | ascend | anchor | 1.00 | 1.20 | -0.308 |
| 4 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 5 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | anchor | 1.30 | 1.00 | 0.444 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 13 | mid | anchor | ground | 1.00 | 1.30 | -0.510 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 771.270 | -185.194 | 586.076 |
| ground | 611.555 | -190.108 | 421.447 |
| ascend | 599.155 | -323.222 | 275.933 |
| surface_tension | 149.000 | -135.600 | 13.400 |
| revitalize | 2.200 | -3.475 | -1.275 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| consuming multiple sodas per day | db574a09 | 2 |
| knowing exactly what you are getting into with regular soda | b45591bc | 2 |
| at work during the day | 2026cc2f | 1 |
| being a little more intentional about drink choice in the moment | 2656d57d | 1 |
| avoiding tooth damage from sugary drinks | 7fba32d4 | 1 |
| feeling thirsty with a drink readily available | 531fc530 | 1 |
| grabbing a drink without checking its contents first | d27ec61e | 1 |
| avoiding the pressure of drink choices feeling like a health identity statement | e9cc6a6e | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
