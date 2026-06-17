# Scoring Summary

Source: `04_scoring.csv`
Total rows: 5,471 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 262 | 278 | 94% | 0.400 |
| convgraph.node.focus.count.none | 206 | 278 | 74% | 0.250 |
| convgraph.node.exhaustion | 144 | 556 | 26% | -0.105 |
| convgraph.node.recency | 144 | 556 | 26% | 0.188 |
| convgraph.node.novelty.high | 134 | 278 | 48% | 0.350 |
| interview.strategy.self_count | 132 | 583 | 23% | -0.124 |
| response.semantic.llm.engagement.high | 121 | 148 | 82% | 0.071 |
| convgraph.node.llm.elaboration.low | 79 | 139 | 57% | 0.150 |
| canongraph.node.novelty.new | 48 | 278 | 17% | 0.400 |
| convgraph.node.llm.charge.negative | 40 | 139 | 29% | 0.300 |
| convgraph.node.llm.elaboration.high | 27 | 417 | 6% | 0.117 |
| convgraph.node.llm.charge.positive | 25 | 139 | 18% | 0.100 |
| response.semantic.llm.engagement.low | 21 | 305 | 7% | -0.205 |
| meta.saturation.canonical | 9 | 9 | 100% | 0.161 |
| response.semantic.llm.certainty.low | 8 | 9 | 89% | 1.000 |
| meta.saturation.conversation | 8 | 9 | 89% | 0.177 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| response.semantic.llm.engagement.mid | 2 | 18 | 11% | 0.400 |
| interview.phase.late | 1 | 9 | 11% | -0.500 |

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
| canongraph.node.novelty.orphan | 0.30 |
| convgraph.node.focus.count.high | 0.60 |
| convgraph.node.focus.count.medium | 0.30 |
| convgraph.node.focus.streak.high | 0.60 |
| convgraph.node.focus.streak.medium | 0.30 |
| convgraph.node.is_orphan.true | 0.50 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.certainty.mid | 0.70 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 262 | 278 | 94% |
| response.semantic.llm.engagement.high | 121 | 148 | 82% |
| meta.saturation.canonical | 9 | 9 | 100% |
| response.semantic.llm.certainty.low | 8 | 9 | 89% |
| meta.saturation.conversation | 8 | 9 | 89% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 2 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 3 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 4 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 5 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 6 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 7 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 8 | unknown | probe_pain | probe_pain | 1.20 | 1.20 | 0.000 |
| 9 | unknown | validate | probe_pain | 1.50 | 1.10 | 0.495 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| probe_pain | 155.360 | -20.156 | 135.204 |
| anchor | 104.960 | -4.588 | 100.372 |
| ascend | 21.610 | -8.364 | 13.246 |
| ground | 8.400 | -3.776 | 4.624 |
| elaborate | 0.400 | -0.300 | 0.100 |
| revitalize | 1.200 | -3.300 | -2.100 |
| validate | 11.461 | -24.000 | -12.539 |

## Node Selection Frequency

No node-level selections found.

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
