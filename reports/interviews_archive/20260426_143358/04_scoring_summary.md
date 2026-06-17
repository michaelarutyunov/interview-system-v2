# Scoring Summary

Source: `04_scoring.csv`
Total rows: 773 (gated: 584)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| response.semantic.llm.engagement.mid | 18 | 18 | 100% | 0.400 |
| interview.strategy.self_count | 14 | 27 | 52% | -0.251 |
| meta.saturation.canonical | 9 | 9 | 100% | 0.152 |
| response.semantic.llm.certainty.mid | 9 | 9 | 100% | 0.700 |
| meta.saturation.conversation | 7 | 9 | 78% | 0.100 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| interview.strategy.self_count.high | 2 | 9 | 22% | -1.000 |
| interview.phase.late | 1 | 9 | 11% | -0.500 |

## Global Signals

- `response.semantic.llm.engagement.trend.fatigued`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.mid`
- `response.semantic.llm.engagement.low`
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
| response.semantic.llm.certainty.low | 1.00 |
| response.semantic.llm.engagement.high | 0.40 |
| response.semantic.llm.engagement.low | 0.80 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| response.semantic.llm.engagement.mid | 18 | 18 | 100% |
| meta.saturation.canonical | 9 | 9 | 100% |
| response.semantic.llm.certainty.mid | 9 | 9 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 3/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | unknown | elaborate | revitalize | 1.40 | 1.00 | 0.160 |
| 2 | unknown | elaborate | revitalize | 1.40 | 1.00 | 0.104 |
| 3 | unknown | revitalize | elaborate | 1.00 | 1.40 | -0.160 |
| 4 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.060 |
| 5 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.040 |
| 6 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.020 |
| 7 | unknown | elaborate | revitalize | 0.80 | 1.00 | -0.052 |
| 8 | unknown | elaborate | revitalize | 0.80 | 1.00 | -0.052 |
| 9 | unknown | validate | elaborate | 1.50 | 0.30 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| elaborate | 3.600 | -1.820 | 1.780 |
| revitalize | 3.600 | -4.200 | -0.600 |
| validate | 8.370 | -24.000 | -15.630 |

## Node Selection Frequency

No node-level selections found.

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| anchor | convgraph.node.is_orphan | 27 | 9 |
| ascend | convgraph.node.chain.gap.above | 27 | 9 |
| ground | convgraph.node.chain.gap.below | 27 | 9 |
| probe_pain | convgraph.node.is_orphan | 27 | 9 |
