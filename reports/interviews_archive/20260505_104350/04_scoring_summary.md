# Scoring Summary

Source: `04_scoring.csv`
Total rows: 24,939 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1731 | 1797 | 96% | 0.300 |
| interview.strategy.self_count | 1401 | 2424 | 58% | -0.115 |
| convgraph.node.focus.count.none | 1386 | 1797 | 77% | 0.200 |
| meta.saturation.canonical.high | 915 | 1797 | 51% | -0.300 |
| convgraph.node.novelty.high | 615 | 1797 | 34% | 0.267 |
| convgraph.node.exhaustion | 411 | 1797 | 23% | -0.134 |
| convgraph.node.recency | 411 | 1797 | 23% | 0.218 |
| convgraph.node.chain.has_attribute_foundation.false | 400 | 690 | 58% | -0.150 |
| convgraph.node.is_orphan.true | 378 | 599 | 63% | 0.500 |
| convgraph.node.chain.has_attribute_foundation.true | 290 | 690 | 42% | 0.075 |
| response.semantic.llm.engagement.high | 289 | 599 | 48% | 0.100 |
| response.semantic.llm.certainty.low | 234 | 599 | 39% | 0.400 |
| meta.saturation.conversation.high | 212 | 1198 | 18% | -0.400 |
| convgraph.node.chain.gap.above.true | 192 | 345 | 56% | 0.500 |
| convgraph.node.llm.charge.negative | 184 | 508 | 36% | 0.275 |
| response.semantic.llm.engagement.low | 174 | 1212 | 14% | -0.290 |
| response.semantic.llm.certainty.mid | 140 | 599 | 23% | 0.200 |
| convgraph.node.chain.gap.below.true | 129 | 345 | 37% | 0.500 |
| convgraph.node.llm.charge.positive | 123 | 254 | 48% | 0.100 |
| convgraph.node.llm.elaboration.low | 116 | 254 | 46% | 0.150 |
| convgraph.node.yield_stagnation.true | 103 | 599 | 17% | 0.250 |
| canongraph.node.novelty.new | 69 | 599 | 12% | 0.300 |
| convgraph.node.focus.count.medium | 34 | 1198 | 3% | -0.050 |
| convgraph.node.focus.count.high | 30 | 599 | 5% | -0.400 |
| convgraph.node.llm.elaboration.high | 21 | 762 | 3% | 0.117 |
| meta.saturation.canonical | 13 | 14 | 93% | -0.241 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
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
| response.semantic.llm.engagement.trend.fatigued | 0.90 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1731 | 1797 | 96% |
| meta.saturation.canonical | 13 | 14 | 93% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 4 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 5 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 13 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 616.990 | -208.834 | 408.156 |
| ascend | 527.485 | -242.582 | 284.903 |
| ground | 455.185 | -227.988 | 227.197 |
| surface_tension | 172.050 | -91.500 | 80.550 |
| revitalize | 1.600 | -3.139 | -1.539 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| being at a work event or grabbing lunch | 5efd40e3 | 1 |
| feeling lighter and less burdened during a busy day | 643f4b42 | 1 |
| regular soda feeling indulgent and guilt-laden | 70a616ee | 1 |
| get a satisfying carbonation kick | 7a102047 | 1 |
| drink choice deliberation piling onto an already full mental load | 7bd91611 | 1 |
| defaulting to water or regular soda when ZeroFizz is unavailable | 86afd36d | 1 |
| being at work during the day | 9322de03 | 1 |
| juggling many competing demands during the workday | 9938e2ce | 1 |
| get a drink with satisfying flavor | cac67331 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
