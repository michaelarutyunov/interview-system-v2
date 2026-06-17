# Scoring Summary

Source: `04_scoring.csv`
Total rows: 22,875 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 2130 | 2169 | 98% | 0.300 |
| convgraph.node.focus.count.none | 1992 | 2169 | 92% | 0.200 |
| interview.strategy.self_count | 1457 | 2214 | 66% | -0.083 |
| convgraph.node.novelty.high | 720 | 2169 | 33% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.true | 488 | 874 | 56% | 0.075 |
| response.semantic.llm.engagement.high | 426 | 753 | 57% | 0.083 |
| convgraph.node.chain.has_attribute_foundation.false | 386 | 874 | 44% | -0.150 |
| response.semantic.llm.engagement.low | 343 | 1491 | 23% | -0.284 |
| convgraph.node.exhaustion | 177 | 2169 | 8% | -0.122 |
| convgraph.node.recency | 177 | 2169 | 8% | 0.229 |
| convgraph.node.llm.elaboration.low | 164 | 298 | 55% | 0.150 |
| convgraph.node.llm.charge.negative | 105 | 298 | 35% | 0.300 |
| convgraph.node.llm.charge.positive | 89 | 298 | 30% | 0.100 |
| canongraph.node.novelty.new | 86 | 723 | 12% | 0.300 |
| convgraph.node.chain.gap.above.true | 84 | 437 | 19% | 0.500 |
| convgraph.node.chain.gap.below.true | 69 | 437 | 16% | 0.500 |
| response.semantic.llm.certainty.low | 22 | 30 | 73% | 1.100 |
| meta.saturation.canonical | 15 | 15 | 100% | 0.162 |
| meta.saturation.conversation | 14 | 15 | 93% | 0.132 |
| convgraph.node.focus.count.medium | 11 | 723 | 2% | -0.200 |
| convgraph.node.llm.elaboration.high | 9 | 894 | 1% | 0.117 |
| response.semantic.llm.engagement.mid | 8 | 30 | 27% | 0.450 |
| interview.phase.mid | 8 | 15 | 53% | -3.000 |
| interview.phase.early | 5 | 15 | 33% | -3.000 |
| interview.phase.late | 4 | 30 | 13% | -0.400 |
| response.semantic.llm.certainty.mid | 4 | 30 | 13% | 0.600 |
| response.semantic.llm.certainty.high | 2 | 15 | 13% | -0.500 |
| response.semantic.llm.engagement.trend.fatigued | 2 | 30 | 7% | 0.200 |

## Global Signals

- `response.semantic.llm.certainty.low`
- `response.semantic.llm.certainty.mid`
- `response.semantic.llm.engagement.mid`
- `response.semantic.llm.certainty.high`
- `response.semantic.llm.engagement.high`
- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.fatigued`
- `response.semantic.llm.engagement.trend.shallowing`
- `interview.phase.late`
- `interview.strategy.self_count.high`
- `interview.phase.early`
- `interview.phase.mid`
- `meta.saturation.conversation`
- `meta.saturation.canonical`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.is_orphan.true | 0.50 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 2130 | 2169 | 98% |
| convgraph.node.focus.count.none | 1992 | 2169 | 92% |
| meta.saturation.canonical | 15 | 15 | 100% |
| meta.saturation.conversation | 14 | 15 | 93% |

## Phase Multiplier Differential

Gap widened by multiplier: 3/15 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | elaborate | ground | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | ground | 1.20 | 1.20 | 0.000 |
| 3 | early | ground | ascend | 1.20 | 1.00 | 0.290 |
| 4 | early | ground | ascend | 1.20 | 1.00 | 0.278 |
| 5 | early | ascend | anchor | 1.00 | 1.20 | -0.350 |
| 6 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | revitalize | ground | 1.00 | 1.30 | -0.540 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 14 | late | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 15 | late | validate | ascend | 1.50 | 1.00 | 0.625 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 526.840 | -63.240 | 463.600 |
| ground | 494.260 | -110.840 | 383.420 |
| ascend | 582.210 | -214.740 | 367.470 |
| elaborate | 16.200 | -6.600 | 9.600 |
| revitalize | 5.000 | -4.700 | 0.300 |
| validate | 18.477 | -39.000 | -20.523 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| energy crash after drinking regular soda | 699a9463 | 2 |
| avoid the mid-afternoon energy dip | 0d3335a2 | 1 |
| genuinely enjoy social connection rather than going through the motions | 34c1196a | 1 |
| feel better about drink choice in the moment | 3745736a | 1 |
| get a drink that feels interesting and stimulating | 64b2714f | 1 |
| being caught off-guard when asked something in a meeting | 91c882a1 | 1 |
| avoid feeling gross from a drink | 9df22ebb | 1 |
| appear as though you care and put in effort | ba188129 | 1 |
| avoid looking unprepared in front of colleagues | db9daa04 | 1 |
| being judged for having a sugary drink in social settings | fe2512f7 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
