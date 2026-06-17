# Scoring Summary

Source: `04_scoring.csv`
Total rows: 7,940 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 555 | 582 | 95% | 0.300 |
| convgraph.node.focus.count.none | 465 | 582 | 80% | 0.200 |
| response.semantic.llm.engagement.low | 398 | 398 | 100% | -0.277 |
| interview.strategy.self_count | 348 | 796 | 44% | -0.080 |
| meta.saturation.canonical.high | 346 | 388 | 89% | -0.300 |
| meta.saturation.conversation.high | 252 | 388 | 65% | -0.400 |
| convgraph.node.novelty.high | 237 | 582 | 41% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.true | 158 | 208 | 76% | 0.075 |
| response.semantic.llm.certainty.low | 130 | 194 | 67% | 0.400 |
| convgraph.node.exhaustion | 117 | 582 | 20% | -0.172 |
| convgraph.node.recency | 117 | 582 | 20% | 0.232 |
| convgraph.node.llm.elaboration.low | 82 | 90 | 91% | 0.150 |
| convgraph.node.chain.has_attribute_foundation.false | 50 | 208 | 24% | -0.150 |
| convgraph.node.llm.charge.negative | 46 | 180 | 26% | 0.275 |
| canongraph.node.novelty.new | 28 | 194 | 14% | 0.300 |
| response.semantic.llm.certainty.mid | 26 | 194 | 13% | 0.200 |
| convgraph.node.chain.gap.below.true | 22 | 104 | 21% | 0.500 |
| convgraph.node.yield_stagnation.true | 20 | 194 | 10% | 0.250 |
| convgraph.node.llm.charge.positive | 14 | 90 | 16% | 0.100 |
| meta.saturation.canonical | 9 | 10 | 90% | -0.300 |
| convgraph.node.chain.gap.above.true | 8 | 104 | 8% | 0.500 |
| response.semantic.llm.engagement.trend.fatigued | 7 | 10 | 70% | 0.900 |
| interview.phase.mid | 5 | 10 | 50% | -3.000 |
| interview.phase.early | 4 | 10 | 40% | -3.000 |
| convgraph.node.focus.count.medium | 2 | 388 | 0% | -0.050 |
| interview.phase.late | 1 | 10 | 10% | 2.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.canonical`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.is_orphan.true | 0.50 |
| convgraph.node.llm.elaboration.high | 0.20 |
| response.semantic.llm.engagement.high | 0.10 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 555 | 582 | 95% |
| response.semantic.llm.engagement.low | 398 | 398 | 100% |
| meta.saturation.canonical.high | 346 | 388 | 89% |
| convgraph.node.llm.elaboration.low | 82 | 90 | 91% |
| meta.saturation.canonical | 9 | 10 | 90% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/10 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 2 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 3 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | ascend | revitalize | 1.00 | 1.00 | 0.000 |
| 5 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | revitalize | 1.30 | 1.00 | 0.354 |
| 7 | mid | ground | revitalize | 1.30 | 1.00 | 0.327 |
| 8 | mid | revitalize | ascend | 1.00 | 1.30 | -0.360 |
| 9 | mid | ascend | revitalize | 1.30 | 1.00 | 0.363 |
| 10 | late | close | revitalize | 1.50 | 1.20 | 0.600 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| surface_tension | 68.050 | 0.000 | 68.050 |
| ascend | 161.800 | -97.486 | 64.314 |
| revitalize | 12.300 | -2.900 | 9.400 |
| ground | 132.450 | -135.904 | -3.454 |
| close | 2.000 | -27.000 | -25.000 |
| anchor | 132.300 | -163.852 | -31.552 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| uncertainty about drink ingredients | 0e7d1c06 | 1 |
| grocery shopping trip | 4967b8e6 | 1 |
| ingredient content determines purchase decision | 6f27fbc7 | 1 |
| avoid feeling like I'm sabotaging my own goals | 78ecb4c5 | 1 |
| know what's going into my body | 9a79bdac | 1 |
| avoid loading cart with unhealthy items | a0753df2 | 1 |
| avoid artificial ingredients I can't pronounce | c34a2b74 | 1 |
| feel in control of my health choices | d0a2aa2c | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
