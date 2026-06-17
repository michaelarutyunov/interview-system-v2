# Scoring Summary

Source: `04_scoring.csv`
Total rows: 938 (gated: 728)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| interview.strategy.self_count | 16 | 30 | 53% | -0.286 |
| meta.saturation.canonical | 10 | 10 | 100% | 0.187 |
| response.semantic.llm.engagement.mid | 8 | 20 | 40% | 0.400 |
| response.semantic.llm.certainty.low | 7 | 10 | 70% | 1.000 |
| meta.saturation.conversation | 7 | 10 | 70% | 0.094 |
| response.semantic.llm.engagement.high | 6 | 10 | 60% | -0.400 |
| interview.phase.mid | 5 | 10 | 50% | -3.000 |
| response.semantic.llm.engagement.trend.shallowing | 4 | 20 | 20% | 0.200 |
| interview.phase.early | 3 | 10 | 30% | -3.000 |
| interview.phase.late | 2 | 10 | 20% | -0.500 |
| response.semantic.llm.certainty.mid | 1 | 10 | 10% | 0.700 |

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
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.low | 0.80 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| meta.saturation.canonical | 10 | 10 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/10 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | unknown | elaborate | revitalize | 1.40 | 1.00 | 0.160 |
| 2 | unknown | elaborate | validate | 1.40 | 0.20 | -0.168 |
| 3 | unknown | revitalize | elaborate | 1.00 | 1.40 | -0.160 |
| 4 | unknown | elaborate | revitalize | 0.80 | 1.00 | 0.056 |
| 5 | unknown | elaborate | revitalize | 0.80 | 1.00 | 0.084 |
| 6 | unknown | elaborate | revitalize | 0.80 | 1.00 | 0.112 |
| 7 | unknown | elaborate | revitalize | 0.80 | 1.00 | 0.112 |
| 8 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.060 |
| 9 | unknown | revitalize | validate | 1.20 | 1.50 | -0.180 |
| 10 | unknown | validate | revitalize | 1.50 | 1.20 | 0.378 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| revitalize | 3.200 | -4.200 | -1.000 |
| elaborate | 1.600 | -4.580 | -2.980 |
| validate | 10.230 | -24.000 | -13.770 |

## Node Selection Frequency

No node-level selections found.

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| anchor | convgraph.node.is_orphan | 32 | 10 |
| ascend | convgraph.node.chain.gap.above | 32 | 10 |
| ground | convgraph.node.chain.gap.below | 32 | 10 |
| probe_pain | convgraph.node.is_orphan | 32 | 10 |
