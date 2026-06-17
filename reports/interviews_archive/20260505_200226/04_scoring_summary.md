# Scoring Summary

Source: `04_scoring.csv`
Total rows: 3,819 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 243 | 267 | 91% | 0.300 |
| meta.saturation.canonical.high | 207 | 267 | 78% | -0.300 |
| convgraph.node.focus.count.none | 159 | 267 | 60% | 0.200 |
| interview.strategy.self_count | 148 | 374 | 40% | -0.142 |
| convgraph.node.novelty.high | 120 | 267 | 45% | 0.267 |
| convgraph.node.exhaustion | 108 | 267 | 40% | -0.156 |
| convgraph.node.recency | 108 | 267 | 40% | 0.236 |
| convgraph.node.is_orphan.true | 55 | 89 | 62% | 0.500 |
| response.semantic.llm.engagement.high | 47 | 89 | 53% | 0.100 |
| convgraph.node.llm.elaboration.low | 44 | 89 | 49% | 0.150 |
| response.semantic.llm.engagement.low | 36 | 187 | 19% | -0.250 |
| response.semantic.llm.certainty.low | 33 | 89 | 37% | 0.400 |
| convgraph.node.llm.charge.negative | 22 | 178 | 12% | 0.275 |
| convgraph.node.yield_stagnation.true | 15 | 89 | 17% | 0.250 |
| canongraph.node.novelty.new | 14 | 89 | 16% | 0.300 |
| response.semantic.llm.certainty.mid | 12 | 89 | 14% | 0.200 |
| convgraph.node.llm.charge.positive | 11 | 89 | 12% | 0.100 |
| meta.saturation.canonical | 9 | 9 | 100% | -0.262 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| response.semantic.llm.engagement.trend.shallowing | 2 | 9 | 22% | 0.400 |
| interview.phase.late | 1 | 9 | 11% | 2.000 |

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
| convgraph.node.llm.elaboration.high | 0.20 |
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 243 | 267 | 91% |
| meta.saturation.canonical | 9 | 9 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | anchor | ascend | 1.00 | 1.30 | -0.306 |
| 7 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 9 | late | close | revitalize | 1.50 | 1.20 | 0.600 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 92.960 | -41.088 | 51.872 |
| ascend | 62.140 | -22.044 | 40.096 |
| ground | 54.440 | -26.316 | 28.124 |
| surface_tension | 22.100 | -20.700 | 1.400 |
| revitalize | 2.000 | -2.355 | -0.355 |
| close | 2.000 | -24.000 | -22.000 |

## Node Selection Frequency

No node-level selections found.

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
