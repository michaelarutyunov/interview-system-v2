# Scoring Summary

Source: `04_scoring.csv`
Total rows: 4,350 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 291 | 312 | 93% | 0.300 |
| convgraph.node.focus.count.none | 264 | 312 | 85% | 0.200 |
| convgraph.node.novelty.high | 219 | 312 | 70% | 0.267 |
| interview.strategy.self_count | 191 | 426 | 45% | -0.077 |
| meta.saturation.canonical.high | 117 | 312 | 38% | -0.300 |
| convgraph.node.chain.has_attribute_foundation.true | 86 | 112 | 77% | 0.075 |
| response.semantic.llm.certainty.low | 65 | 104 | 62% | 0.400 |
| meta.saturation.conversation.high | 56 | 208 | 27% | -0.400 |
| convgraph.node.recency | 48 | 312 | 15% | 0.254 |
| convgraph.node.exhaustion | 48 | 312 | 15% | -0.105 |
| convgraph.node.llm.charge.negative | 28 | 94 | 30% | 0.275 |
| canongraph.node.novelty.new | 28 | 104 | 27% | 0.300 |
| response.semantic.llm.engagement.high | 28 | 104 | 27% | 0.100 |
| convgraph.node.chain.has_attribute_foundation.false | 26 | 112 | 23% | -0.150 |
| convgraph.node.llm.elaboration.low | 23 | 47 | 49% | 0.150 |
| convgraph.node.llm.elaboration.high | 12 | 141 | 8% | 0.117 |
| convgraph.node.yield_stagnation.true | 11 | 104 | 11% | 0.250 |
| convgraph.node.chain.gap.below.true | 10 | 56 | 18% | 0.500 |
| convgraph.node.llm.charge.positive | 10 | 47 | 21% | 0.100 |
| convgraph.node.chain.gap.above.true | 8 | 56 | 14% | 0.500 |
| convgraph.node.focus.count.medium | 8 | 208 | 4% | -0.050 |
| meta.saturation.canonical | 4 | 5 | 80% | -0.225 |
| interview.phase.early | 3 | 5 | 60% | -3.000 |
| interview.phase.mid | 2 | 5 | 40% | -3.000 |
| convgraph.node.focus.count.high | 1 | 104 | 1% | -0.400 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 5 | 20% | 0.400 |

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
| convgraph.node.is_orphan.true | 0.50 |
| interview.phase.late | 2.00 |
| response.semantic.llm.certainty.mid | 0.20 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 291 | 312 | 93% |
| convgraph.node.focus.count.none | 264 | 312 | 85% |

## Phase Multiplier Differential

Gap widened by multiplier: 0/5 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | ground | 1.20 | 1.20 | 0.000 |
| 3 | early | ground | anchor | 1.20 | 1.20 | 0.000 |
| 4 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 93.425 | -11.912 | 81.513 |
| anchor | 87.850 | -28.124 | 59.726 |
| ground | 77.325 | -41.768 | 35.557 |
| surface_tension | 32.650 | -11.700 | 20.950 |
| revitalize | 0.400 | -0.900 | -0.500 |
| close | 0.000 | -15.000 | -15.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| light, enjoyable taste without caffeine or heaviness | 0d918b14 | 1 |
| feeling too heavy or weighed down by regular soda | 179595a8 | 1 |
| difficulty focusing while feeling sluggish at desk | 3986735b | 1 |
| bloated and sluggish after drinking soda | 60cd48a1 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
