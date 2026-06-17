# Scoring Summary

Source: `04_scoring.csv`
Total rows: 2,548 (gated: 1,391)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| interview.strategy.self_count | 116 | 156 | 74% | -0.205 |
| convgraph.node.chain.has_attribute_foundation.true | 106 | 131 | 81% | 0.120 |
| convgraph.node.chain.branching_deficit | 91 | 91 | 100% | 0.207 |
| response.semantic.llm.engagement.high | 56 | 91 | 62% | 0.100 |
| convgraph.node.chain.gap.above.true | 24 | 24 | 100% | 0.250 |
| convgraph.node.chain.has_attribute_foundation.false | 19 | 40 | 48% | 0.132 |
| convgraph.node.chain.gap.below.true | 16 | 16 | 100% | 0.300 |
| convgraph.node.chain.fan_in | 14 | 24 | 58% | 0.113 |
| convgraph.node.exhaustion | 13 | 134 | 10% | -0.097 |
| convgraph.node.recency | 13 | 134 | 10% | 0.139 |
| meta.saturation.canonical.high | 13 | 19 | 68% | -0.300 |
| meta.saturation.canonical | 11 | 11 | 100% | -0.345 |
| meta.saturation.conversation | 10 | 11 | 91% | -0.253 |
| interview.phase.mid | 6 | 11 | 54% | -3.000 |
| interview.phase.early | 4 | 11 | 36% | -3.000 |
| convgraph.node.is_orphan.true | 3 | 3 | 100% | 0.500 |
| meta.saturation.conversation.high | 3 | 19 | 16% | -0.400 |
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
| convgraph.node.focus.count.high | 0.80 |
| convgraph.node.focus.count.medium | 0.40 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.low | 0.50 |
| response.semantic.llm.engagement.trend.fatigued | 0.80 |
| response.semantic.llm.engagement.trend.shallowing | 0.30 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.chain.has_attribute_foundation.true | 106 | 131 | 81% |
| convgraph.node.chain.branching_deficit | 91 | 91 | 100% |
| convgraph.node.chain.gap.above.true | 24 | 24 | 100% |
| convgraph.node.chain.gap.below.true | 16 | 16 | 100% |
| meta.saturation.canonical | 11 | 11 | 100% |
| meta.saturation.conversation | 10 | 11 | 91% |
| convgraph.node.is_orphan.true | 3 | 3 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/11 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 2 | early | branch | branch | 1.40 | 1.40 | 0.000 |
| 3 | early | ascend | branch | 1.00 | 1.40 | -0.233 |
| 4 | early | ground | ground | 1.40 | 1.40 | 0.000 |
| 5 | mid | ascend | branch | 1.30 | 1.00 | 0.095 |
| 6 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | branch | branch | 1.00 | 1.00 | 0.000 |
| 8 | mid | branch | branch | 1.00 | 1.00 | 0.000 |
| 9 | mid | ascend | branch | 1.30 | 1.00 | 0.095 |
| 10 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 11 | late | close | branch | 1.50 | 1.10 | 0.320 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| branch | 34.741 | -16.060 | 18.681 |
| ground | 8.800 | -4.640 | 4.160 |
| ascend | 11.784 | -9.900 | 1.884 |
| anchor | 1.500 | -1.000 | 0.500 |
| revitalize | 0.000 | -6.333 | -6.333 |
| close | 0.800 | -30.000 | -29.200 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| no sugar or sweeteners | b6d286b9 | 3 |
| avoiding boredom from repetitive choices | 2b8a794b | 1 |
| feels like drinking a real soda | 8515c114 | 1 |
| not feeling locked into a routine | 4e8505b3 | 1 |
| sense of having options when choosing a drink | 8db57bc2 | 1 |
| off-taste of other diet drinks | a9ebe7a3 | 1 |
| not feeling locked into one thing | cfb59c43 | 1 |
| drinking without worry or guilt | f357342e | 1 |

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| bridge | convgraph.node.chain.level.skip | 42 | 11 |
| anchor | convgraph.node.is_orphan | 41 | 11 |
| ascend | convgraph.node.chain.gap.above | 40 | 11 |
| ground | convgraph.node.chain.gap.below | 40 | 11 |
| branch | convgraph.node.chain.branching_deficit | 31 | 11 |
