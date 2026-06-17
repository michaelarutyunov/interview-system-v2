# Scoring Summary

Source: `04_scoring.csv`
Total rows: 2,792 (gated: 1,332)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.chain.has_attribute_foundation.true | 145 | 154 | 94% | 0.269 |
| interview.strategy.self_count | 129 | 190 | 68% | -0.133 |
| convgraph.node.chain.branching_deficit | 104 | 104 | 100% | 0.177 |
| response.semantic.llm.engagement.high | 84 | 104 | 81% | 0.100 |
| convgraph.node.chain.gap.above.true | 46 | 46 | 100% | 0.250 |
| convgraph.node.chain.fan_in | 38 | 46 | 83% | 0.090 |
| convgraph.node.is_orphan.true | 14 | 14 | 100% | 0.500 |
| meta.saturation.canonical.high | 12 | 18 | 67% | -0.300 |
| meta.saturation.canonical | 10 | 11 | 91% | -0.337 |
| meta.saturation.conversation | 8 | 11 | 73% | -0.185 |
| interview.phase.mid | 6 | 11 | 54% | -3.000 |
| convgraph.node.chain.has_attribute_foundation.false | 5 | 50 | 10% | 0.100 |
| convgraph.node.chain.gap.below.true | 4 | 4 | 100% | 0.300 |
| interview.phase.early | 4 | 11 | 36% | -3.000 |
| interview.phase.late | 1 | 11 | 9% | 0.800 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.conversation`
- `meta.saturation.canonical`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.chain.has_terminal_apex.true | 0.50 |
| convgraph.node.exhaustion | 0.80 |
| convgraph.node.focus.count.high | 0.80 |
| convgraph.node.focus.count.medium | 0.40 |
| convgraph.node.recency | 0.25 |
| interview.strategy.self_count.high | 1.00 |
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.low | 0.50 |
| response.semantic.llm.engagement.trend.fatigued | 0.80 |
| response.semantic.llm.engagement.trend.shallowing | 0.30 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.chain.has_attribute_foundation.true | 145 | 154 | 94% |
| convgraph.node.chain.branching_deficit | 104 | 104 | 100% |
| response.semantic.llm.engagement.high | 84 | 104 | 81% |
| convgraph.node.chain.gap.above.true | 46 | 46 | 100% |
| convgraph.node.chain.fan_in | 38 | 46 | 83% |
| convgraph.node.is_orphan.true | 14 | 14 | 100% |
| meta.saturation.canonical | 10 | 11 | 91% |
| convgraph.node.chain.gap.below.true | 4 | 4 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 3/11 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 2 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 3 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 4 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | branch | branch | 1.00 | 1.00 | 0.000 |
| 7 | mid | ground | branch | 1.30 | 1.00 | 0.165 |
| 8 | mid | branch | branch | 1.00 | 1.00 | 0.000 |
| 9 | mid | branch | branch | 1.00 | 1.00 | 0.000 |
| 10 | mid | ground | branch | 1.30 | 1.00 | 0.156 |
| 11 | late | close | branch | 1.50 | 1.10 | 0.320 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| branch | 56.858 | -9.300 | 47.558 |
| ascend | 23.932 | -8.300 | 15.632 |
| anchor | 7.000 | -3.000 | 4.000 |
| ground | 2.200 | -0.720 | 1.480 |
| revitalize | 0.000 | -4.847 | -4.847 |
| close | 0.800 | -30.000 | -29.200 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| acceptable taste despite no sugar | 158b1eca | 5 |
| zero sugar formulation | 7ab35cff | 2 |
| noticing when companies skip usability details | 02eb46f0 | 1 |
| avoiding unpleasant taste experience | 382fe8cb | 1 |
| brand prioritizing what people actually want over mere product existence | 4de5c0b9 | 1 |

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| bridge | convgraph.node.chain.level.skip | 48 | 11 |
| ground | convgraph.node.chain.gap.below | 47 | 11 |
| anchor | convgraph.node.is_orphan | 46 | 11 |
| ascend | convgraph.node.chain.gap.above | 41 | 11 |
| branch | convgraph.node.chain.branching_deficit | 35 | 11 |
