# Scoring Summary

Source: `04_scoring.csv`
Total rows: 4,131 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 288 | 303 | 95% | 0.300 |
| convgraph.node.focus.count.none | 258 | 303 | 85% | 0.200 |
| convgraph.node.novelty.high | 189 | 303 | 62% | 0.267 |
| response.semantic.llm.engagement.low | 187 | 208 | 90% | -0.276 |
| meta.saturation.canonical.high | 160 | 202 | 79% | -0.300 |
| interview.strategy.self_count | 154 | 416 | 37% | -0.076 |
| convgraph.node.chain.has_attribute_foundation.true | 88 | 98 | 90% | 0.075 |
| response.semantic.llm.certainty.low | 67 | 101 | 66% | 0.400 |
| meta.saturation.conversation.high | 60 | 202 | 30% | -0.400 |
| convgraph.node.llm.charge.negative | 52 | 98 | 53% | 0.275 |
| convgraph.node.llm.elaboration.low | 49 | 49 | 100% | 0.150 |
| convgraph.node.exhaustion | 45 | 303 | 15% | -0.149 |
| convgraph.node.recency | 45 | 303 | 15% | 0.249 |
| canongraph.node.novelty.new | 24 | 101 | 24% | 0.300 |
| convgraph.node.chain.has_attribute_foundation.false | 10 | 98 | 10% | -0.150 |
| convgraph.node.chain.gap.above.true | 9 | 49 | 18% | 0.500 |
| interview.phase.early | 8 | 12 | 67% | -2.000 |
| meta.saturation.canonical | 6 | 6 | 100% | -0.275 |
| convgraph.node.chain.gap.below.true | 5 | 49 | 10% | 0.500 |
| convgraph.node.yield_stagnation.true | 3 | 101 | 3% | 0.250 |
| response.semantic.llm.engagement.trend.fatigued | 3 | 6 | 50% | 0.900 |
| interview.phase.mid | 2 | 6 | 33% | -3.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.canonical`
- `interview.phase.early`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.focus.count.medium | 0.20 |
| convgraph.node.is_orphan.true | 0.50 |
| convgraph.node.llm.charge.positive | 0.10 |
| convgraph.node.llm.elaboration.high | 0.20 |
| interview.phase.late | 2.00 |
| response.semantic.llm.certainty.mid | 0.20 |
| response.semantic.llm.engagement.high | 0.10 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 288 | 303 | 95% |
| convgraph.node.focus.count.none | 258 | 303 | 85% |
| response.semantic.llm.engagement.low | 187 | 208 | 90% |
| convgraph.node.chain.has_attribute_foundation.true | 88 | 98 | 90% |
| convgraph.node.llm.elaboration.low | 49 | 49 | 100% |
| meta.saturation.canonical | 6 | 6 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/6 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ground | 1.00 | 1.20 | -0.320 |
| 2 | early | ascend | ground | 1.00 | 1.20 | -0.254 |
| 3 | early | ground | ascend | 1.20 | 1.00 | 0.230 |
| 4 | early | ascend | ground | 1.00 | 1.20 | -0.248 |
| 5 | mid | ground | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 93.200 | -39.610 | 53.590 |
| surface_tension | 34.050 | 0.000 | 34.050 |
| anchor | 82.700 | -64.420 | 18.280 |
| ground | 69.450 | -52.260 | 17.190 |
| revitalize | 5.700 | -5.650 | 0.050 |
| close | 0.000 | -18.000 | -18.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| experiencing a mild crash later in the afternoon | af89def6 | 2 |
| Tuesday afternoon at work | 8e3bb68e | 1 |
| stay focused through the afternoon | b530e242 | 1 |
| avoid energy crash after drinking | d1641d73 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
