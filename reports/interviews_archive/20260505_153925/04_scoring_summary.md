# Scoring Summary

Source: `04_scoring.csv`
Total rows: 13,272 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 900 | 939 | 96% | 0.300 |
| convgraph.node.focus.count.none | 672 | 939 | 72% | 0.200 |
| meta.saturation.canonical.high | 606 | 939 | 64% | -0.300 |
| interview.strategy.self_count | 510 | 1280 | 40% | -0.168 |
| convgraph.node.novelty.high | 315 | 939 | 34% | 0.267 |
| convgraph.node.is_orphan.true | 305 | 313 | 97% | 0.500 |
| convgraph.node.exhaustion | 267 | 939 | 28% | -0.149 |
| convgraph.node.recency | 267 | 939 | 28% | 0.213 |
| response.semantic.llm.engagement.high | 156 | 313 | 50% | 0.100 |
| convgraph.node.llm.elaboration.low | 141 | 313 | 45% | 0.150 |
| response.semantic.llm.certainty.low | 137 | 313 | 44% | 0.400 |
| convgraph.node.llm.charge.negative | 120 | 626 | 19% | 0.275 |
| response.semantic.llm.certainty.mid | 84 | 313 | 27% | 0.200 |
| convgraph.node.llm.charge.positive | 78 | 313 | 25% | 0.100 |
| convgraph.node.llm.elaboration.high | 72 | 939 | 8% | 0.117 |
| convgraph.node.yield_stagnation.true | 54 | 313 | 17% | 0.250 |
| canongraph.node.novelty.new | 36 | 313 | 12% | 0.300 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.243 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |

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
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 900 | 939 | 96% |
| convgraph.node.is_orphan.true | 305 | 313 | 97% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 5 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 8 | mid | anchor | ascend | 1.00 | 1.30 | -0.408 |
| 9 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 10 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 11 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ascend | anchor | 1.30 | 1.00 | 0.282 |
| 14 | late | close | anchor | 1.50 | 0.70 | 1.600 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 382.210 | -138.556 | 243.654 |
| ascend | 213.715 | -34.128 | 179.587 |
| ground | 183.565 | -73.832 | 109.733 |
| surface_tension | 100.100 | -60.600 | 39.500 |
| revitalize | 0.000 | -3.400 | -3.400 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

No node-level selections found.

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
