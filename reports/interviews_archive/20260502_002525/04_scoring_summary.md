# Scoring Summary

Source: `04_scoring.csv`
Total rows: 3,397 (gated: 1,700)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| interview.strategy.self_count | 176 | 222 | 79% | -0.159 |
| convgraph.node.chain.has_attribute_foundation.true | 168 | 200 | 84% | 0.125 |
| convgraph.node.chain.branching_deficit | 142 | 142 | 100% | 0.176 |
| convgraph.node.recency | 51 | 200 | 26% | 0.151 |
| convgraph.node.exhaustion | 51 | 200 | 26% | -0.144 |
| convgraph.node.chain.gap.above.true | 43 | 43 | 100% | 0.250 |
| convgraph.node.chain.fan_in | 42 | 43 | 98% | 0.054 |
| response.semantic.llm.engagement.high | 39 | 142 | 28% | 0.100 |
| convgraph.node.chain.has_attribute_foundation.false | 16 | 58 | 28% | 0.203 |
| convgraph.node.chain.gap.below.true | 15 | 15 | 100% | 0.300 |
| meta.saturation.canonical.high | 12 | 15 | 80% | -0.300 |
| meta.saturation.canonical | 11 | 11 | 100% | -0.358 |
| meta.saturation.conversation | 10 | 11 | 91% | -0.184 |
| interview.phase.mid | 6 | 11 | 54% | -3.000 |
| interview.phase.early | 4 | 11 | 36% | -3.000 |
| interview.phase.late | 1 | 11 | 9% | 0.800 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 11 | 9% | 0.300 |

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
| convgraph.node.focus.count.high | 0.80 |
| convgraph.node.focus.count.medium | 0.40 |
| interview.strategy.self_count.high | 1.00 |
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.low | 0.50 |
| response.semantic.llm.engagement.trend.fatigued | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.chain.has_attribute_foundation.true | 168 | 200 | 84% |
| convgraph.node.chain.branching_deficit | 142 | 142 | 100% |
| convgraph.node.chain.gap.above.true | 43 | 43 | 100% |
| convgraph.node.chain.fan_in | 42 | 43 | 98% |
| convgraph.node.chain.gap.below.true | 15 | 15 | 100% |
| meta.saturation.canonical | 11 | 11 | 100% |
| meta.saturation.conversation | 10 | 11 | 91% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/11 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | branch | ascend | 1.40 | 1.00 | 0.140 |
| 2 | early | ground | branch | 1.40 | 1.40 | 0.000 |
| 3 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 4 | early | ground | ascend | 1.40 | 1.00 | 0.157 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | ground | branch | 1.30 | 1.00 | 0.095 |
| 7 | mid | branch | branch | 1.00 | 1.00 | 0.000 |
| 8 | mid | ground | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ground | branch | 1.30 | 1.00 | 0.082 |
| 10 | mid | ground | branch | 1.30 | 1.00 | 0.163 |
| 11 | late | close | ascend | 1.50 | 1.20 | 0.240 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| branch | 45.298 | -22.276 | 23.022 |
| ascend | 23.557 | -11.808 | 11.749 |
| ground | 9.975 | -5.266 | 4.709 |
| revitalize | 0.300 | -5.773 | -5.473 |
| close | 0.800 | -30.000 | -29.200 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| weird chemical taste as proof of difference from regular soda | 21354f96 | 3 |
| feeling sluggish at work | eb277121 | 3 |
| not allowing oneself to have it too easy / not cheating | 8ab4c3b8 | 2 |
| grabbing a diet cola | fcb1241d | 2 |

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| anchor | convgraph.node.is_orphan | 54 | 11 |
| bridge | convgraph.node.chain.level.skip | 54 | 11 |
| ground | convgraph.node.chain.gap.below | 53 | 11 |
| ascend | convgraph.node.chain.gap.above | 48 | 11 |
| branch | convgraph.node.chain.branching_deficit | 39 | 11 |
