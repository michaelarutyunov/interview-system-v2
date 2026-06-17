# Scoring Summary

Source: `04_scoring.csv`
Total rows: 1,436 (gated: 1,055)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| interview.strategy.self_count | 28 | 48 | 58% | -0.210 |
| response.semantic.llm.engagement.mid | 26 | 26 | 100% | 0.400 |
| response.semantic.llm.certainty.mid | 13 | 13 | 100% | 0.700 |
| meta.saturation.canonical | 13 | 13 | 100% | 0.155 |
| meta.saturation.conversation | 12 | 13 | 92% | 0.146 |
| convgraph.node.chain.has_attribute_foundation.true | 9 | 9 | 100% | 0.200 |
| convgraph.node.chain.gap.above.true | 9 | 9 | 100% | 0.250 |
| interview.phase.mid | 7 | 13 | 54% | -3.000 |
| interview.phase.early | 5 | 13 | 38% | -3.000 |
| convgraph.node.llm.elaboration.low | 3 | 9 | 33% | 0.150 |
| convgraph.node.exhaustion | 2 | 9 | 22% | -0.234 |
| interview.strategy.self_count.high | 2 | 13 | 15% | -1.000 |
| convgraph.node.recency | 2 | 9 | 22% | 0.200 |
| response.semantic.llm.engagement.trend.fatigued | 2 | 26 | 8% | 0.200 |
| interview.phase.late | 1 | 13 | 8% | -0.500 |

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
| convgraph.node.chain.has_attribute_foundation.false | 0.50 |
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.focus.count.medium | 0.20 |
| convgraph.node.llm.charge.positive | 0.10 |
| convgraph.node.llm.elaboration.high | 0.10 |
| response.semantic.llm.certainty.low | 1.00 |
| response.semantic.llm.engagement.high | 0.40 |
| response.semantic.llm.engagement.low | 0.80 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| response.semantic.llm.engagement.mid | 26 | 26 | 100% |
| response.semantic.llm.certainty.mid | 13 | 13 | 100% |
| meta.saturation.canonical | 13 | 13 | 100% |
| meta.saturation.conversation | 12 | 13 | 92% |
| convgraph.node.chain.has_attribute_foundation.true | 9 | 9 | 100% |
| convgraph.node.chain.gap.above.true | 9 | 9 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/13 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | unknown | elaborate | revitalize | 1.40 | 1.00 | 0.160 |
| 2 | unknown | elaborate | revitalize | 1.40 | 1.00 | 0.104 |
| 3 | unknown | revitalize | elaborate | 1.00 | 1.40 | -0.160 |
| 4 | unknown | elaborate | revitalize | 1.40 | 1.00 | 0.048 |
| 5 | unknown | revitalize | elaborate | 1.00 | 1.40 | -0.120 |
| 6 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.240 |
| 7 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.020 |
| 8 | unknown | elaborate | validate | 0.80 | 0.50 | 0.078 |
| 9 | unknown | revitalize | elaborate | 1.00 | 0.80 | 0.020 |
| 10 | unknown | elaborate | revitalize | 0.80 | 1.00 | -0.052 |
| 11 | unknown | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 12 | unknown | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | unknown | validate | ascend | 1.50 | 1.00 | 0.579 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 4.900 | -0.738 | 4.162 |
| elaborate | 5.200 | -3.820 | 1.380 |
| revitalize | 6.200 | -4.900 | 1.300 |
| validate | 12.870 | -36.000 | -23.130 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| home alone in the evening | b757e974 | 2 |

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| anchor | convgraph.node.is_orphan | 33 | 13 |
| ground | convgraph.node.chain.gap.below | 33 | 13 |
| probe_pain | convgraph.node.is_orphan | 33 | 13 |
| ascend | convgraph.node.chain.gap.above | 30 | 13 |
