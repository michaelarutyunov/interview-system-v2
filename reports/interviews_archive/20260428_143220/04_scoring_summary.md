# Scoring Summary

Source: `04_scoring.csv`
Total rows: 4,787 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 226 | 242 | 93% | 0.300 |
| interview.strategy.self_count | 210 | 511 | 41% | -0.146 |
| convgraph.node.focus.count.none | 184 | 242 | 76% | 0.200 |
| convgraph.node.exhaustion | 116 | 484 | 24% | -0.106 |
| convgraph.node.recency | 116 | 484 | 24% | 0.226 |
| convgraph.node.novelty.high | 108 | 242 | 45% | 0.250 |
| convgraph.node.llm.elaboration.low | 81 | 121 | 67% | 0.150 |
| response.semantic.llm.engagement.high | 69 | 130 | 53% | 0.064 |
| canongraph.node.novelty.new | 36 | 242 | 15% | 0.300 |
| convgraph.node.llm.charge.negative | 32 | 121 | 26% | 0.300 |
| convgraph.node.llm.charge.positive | 15 | 121 | 12% | 0.100 |
| meta.saturation.conversation | 8 | 9 | 89% | 0.204 |
| response.semantic.llm.engagement.mid | 8 | 18 | 44% | 0.400 |
| meta.saturation.canonical | 8 | 9 | 89% | 0.171 |
| response.semantic.llm.certainty.low | 7 | 9 | 78% | 1.000 |
| convgraph.node.is_orphan.true | 6 | 242 | 2% | 0.425 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| interview.phase.late | 1 | 9 | 11% | -0.500 |
| response.semantic.llm.certainty.mid | 1 | 9 | 11% | 0.700 |

## Global Signals

- `response.semantic.llm.engagement.trend.fatigued`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.mid`
- `response.semantic.llm.engagement.low`
- `interview.strategy.self_count`
- `response.semantic.llm.engagement.high`
- `interview.strategy.self_count.high`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`
- `meta.saturation.conversation`
- `meta.saturation.canonical`
- `response.semantic.llm.certainty.low`
- `response.semantic.llm.certainty.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| canongraph.node.novelty.orphan | 0.20 |
| convgraph.node.focus.count.high | 0.60 |
| convgraph.node.focus.count.medium | 0.30 |
| convgraph.node.focus.streak.high | 0.60 |
| convgraph.node.focus.streak.medium | 0.30 |
| convgraph.node.llm.elaboration.high | 0.20 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.low | 0.80 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 226 | 242 | 93% |
| meta.saturation.conversation | 8 | 9 | 89% |
| meta.saturation.canonical | 8 | 9 | 89% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | probe_pain | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 5 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 6 | mid | probe_pain | anchor | 1.20 | 1.00 | 0.220 |
| 7 | mid | probe_pain | anchor | 1.20 | 1.00 | 0.220 |
| 8 | mid | probe_pain | anchor | 1.20 | 1.00 | 0.147 |
| 9 | late | validate | probe_pain | 1.50 | 1.10 | 0.566 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 86.600 | -8.496 | 78.104 |
| probe_pain | 84.850 | -26.772 | 58.078 |
| ascend | 21.525 | -4.608 | 16.917 |
| ground | 7.875 | -3.072 | 4.803 |
| elaborate | 1.600 | 0.000 | 1.600 |
| revitalize | 1.600 | -2.500 | -0.900 |
| validate | 10.695 | -24.000 | -13.305 |

## Node Selection Frequency

No node-level selections found.

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
