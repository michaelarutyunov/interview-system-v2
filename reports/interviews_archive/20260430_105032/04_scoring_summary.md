# Scoring Summary

Source: `04_scoring.csv`
Total rows: 16,191 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1509 | 1545 | 98% | 0.300 |
| convgraph.node.focus.count.none | 1386 | 1545 | 90% | 0.200 |
| interview.strategy.self_count | 1014 | 1587 | 64% | -0.089 |
| convgraph.node.novelty.high | 555 | 1545 | 36% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.true | 384 | 576 | 67% | 0.075 |
| response.semantic.llm.engagement.high | 193 | 543 | 36% | 0.077 |
| convgraph.node.chain.has_attribute_foundation.false | 192 | 576 | 33% | -0.150 |
| convgraph.node.recency | 159 | 1545 | 10% | 0.229 |
| convgraph.node.exhaustion | 159 | 1545 | 10% | -0.104 |
| convgraph.node.llm.elaboration.low | 107 | 204 | 52% | 0.150 |
| response.semantic.llm.engagement.low | 99 | 1072 | 9% | -0.282 |
| canongraph.node.novelty.new | 66 | 515 | 13% | 0.300 |
| convgraph.node.chain.gap.below.true | 51 | 288 | 18% | 0.500 |
| convgraph.node.llm.charge.positive | 45 | 204 | 22% | 0.100 |
| convgraph.node.llm.elaboration.high | 42 | 612 | 7% | 0.117 |
| convgraph.node.chain.gap.above.true | 37 | 288 | 13% | 0.500 |
| convgraph.node.llm.charge.negative | 35 | 204 | 17% | 0.300 |
| response.semantic.llm.certainty.low | 18 | 28 | 64% | 1.100 |
| response.semantic.llm.engagement.mid | 16 | 28 | 57% | 0.450 |
| meta.saturation.conversation | 13 | 14 | 93% | 0.173 |
| meta.saturation.canonical | 13 | 14 | 93% | 0.160 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| response.semantic.llm.certainty.mid | 8 | 28 | 29% | 0.600 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 2 | 28 | 7% | -0.400 |
| response.semantic.llm.engagement.trend.shallowing | 2 | 28 | 7% | 0.200 |
| response.semantic.llm.certainty.high | 1 | 14 | 7% | -0.500 |

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
| convgraph.node.focus.count.medium | 0.20 |
| convgraph.node.is_orphan.true | 0.50 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1509 | 1545 | 98% |
| convgraph.node.focus.count.none | 1386 | 1545 | 90% |
| meta.saturation.conversation | 13 | 14 | 93% |
| meta.saturation.canonical | 13 | 14 | 93% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | elaborate | ground | 1.20 | 1.20 | 0.000 |
| 2 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | ground | anchor | 1.20 | 1.20 | 0.000 |
| 5 | early | elaborate | ground | 1.20 | 1.20 | 0.000 |
| 6 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 10 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 11 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 14 | late | validate | ascend | 1.50 | 1.00 | 0.625 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 359.320 | -25.748 | 333.572 |
| ascend | 410.880 | -105.954 | 304.926 |
| ground | 348.630 | -88.876 | 259.754 |
| elaborate | 16.800 | -4.200 | 12.600 |
| revitalize | 4.800 | -2.500 | 2.300 |
| validate | 16.733 | -39.000 | -22.267 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| feel like the day is less routine and more special | 19f34b09 | 2 |
| satisfy craving for fizzy sensation | 1e8438bd | 1 |
| feel like you're having something meaningful | 41f4cabb | 1 |
| regular soda has too much sugar | 44982b3b | 1 |
| feel mentally refreshed during long desk sessions | 908c8601 | 1 |
| grabbing water or regular soda as fallback when ZeroFizz unavailable | d0b3b354 | 1 |
| maintain a sense of enjoyment and humanity during the workday | d7f3cb70 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
