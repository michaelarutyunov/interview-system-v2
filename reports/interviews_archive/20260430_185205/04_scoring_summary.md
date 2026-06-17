# Scoring Summary

Source: `04_scoring.csv`
Total rows: 21,418 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1557 | 1584 | 98% | 0.300 |
| convgraph.node.focus.count.none | 1473 | 1584 | 93% | 0.200 |
| meta.saturation.canonical.high | 970 | 1056 | 92% | -0.300 |
| interview.strategy.self_count | 838 | 2132 | 39% | -0.091 |
| convgraph.node.novelty.high | 705 | 1584 | 44% | 0.267 |
| response.semantic.llm.engagement.high | 528 | 528 | 100% | 0.100 |
| response.semantic.llm.certainty.low | 376 | 528 | 71% | 0.400 |
| convgraph.node.chain.has_attribute_foundation.false | 338 | 598 | 56% | -0.150 |
| convgraph.node.chain.has_attribute_foundation.true | 260 | 598 | 44% | 0.075 |
| meta.saturation.conversation.high | 166 | 1056 | 16% | -0.400 |
| convgraph.node.llm.elaboration.high | 147 | 678 | 22% | 0.117 |
| response.semantic.llm.certainty.mid | 137 | 528 | 26% | 0.200 |
| convgraph.node.recency | 111 | 1584 | 7% | 0.230 |
| convgraph.node.exhaustion | 111 | 1584 | 7% | -0.119 |
| convgraph.node.chain.gap.below.true | 106 | 299 | 36% | 0.500 |
| convgraph.node.llm.charge.negative | 100 | 452 | 22% | 0.275 |
| convgraph.node.llm.charge.positive | 89 | 226 | 39% | 0.100 |
| canongraph.node.novelty.new | 83 | 528 | 16% | 0.300 |
| convgraph.node.llm.elaboration.low | 77 | 226 | 34% | 0.150 |
| convgraph.node.chain.gap.above.true | 52 | 299 | 17% | 0.500 |
| convgraph.node.yield_stagnation.true | 18 | 528 | 3% | 0.250 |
| meta.saturation.canonical | 10 | 10 | 100% | -0.265 |
| convgraph.node.focus.count.medium | 6 | 1056 | 1% | -0.050 |
| interview.phase.mid | 5 | 10 | 50% | -3.000 |
| interview.phase.early | 4 | 10 | 40% | -3.000 |
| interview.phase.late | 1 | 10 | 10% | 2.000 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 10 | 10% | 0.400 |

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
| convgraph.node.is_orphan.true | 0.50 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1557 | 1584 | 98% |
| convgraph.node.focus.count.none | 1473 | 1584 | 93% |
| meta.saturation.canonical.high | 970 | 1056 | 92% |
| response.semantic.llm.engagement.high | 528 | 528 | 100% |
| meta.saturation.canonical | 10 | 10 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/10 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | anchor | 1.00 | 1.20 | -0.320 |
| 2 | early | ascend | anchor | 1.00 | 1.20 | -0.314 |
| 3 | early | ascend | ground | 1.00 | 1.20 | -0.308 |
| 4 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 10 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 419.070 | -148.430 | 270.640 |
| anchor | 433.280 | -180.900 | 252.380 |
| surface_tension | 195.100 | 0.000 | 195.100 |
| ground | 411.470 | -228.600 | 182.870 |
| revitalize | 0.400 | -2.647 | -2.248 |
| close | 2.000 | -27.000 | -25.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| take a break without feeling like I'm failing at something | 0628e706 | 1 |
| feel like I'm actively choosing, not settling | 1da38fa2 | 1 |
| need for a low-friction, guilt-free daily ritual | 5d9814f7 | 1 |
| drink choice reduces decision friction | 65b6eadf | 1 |
| treat myself without guilt | 79c75460 | 1 |
| at desk mid-afternoon | 916d8db2 | 1 |
| feel like I'm doing something right, even in small ways | 9b33a27e | 1 |
| avoid spending mental energy on drink decisions | a7259dba | 1 |
| feel like someone who makes deliberate, self-caring choices | ada83ae0 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
