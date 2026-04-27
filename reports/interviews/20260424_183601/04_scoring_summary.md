# Scoring Summary

Source: `04_scoring.csv`
Total rows: 1,858 (gated: 653)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| interview.strategy.self_count | 96 | 140 | 69% | -0.141 |
| convgraph.node.chain.has_attribute_foundation.true | 73 | 110 | 66% | 0.256 |
| convgraph.node.chain.branching_deficit | 62 | 62 | 100% | 0.196 |
| convgraph.node.chain.gap.above.true | 45 | 45 | 100% | 0.250 |
| convgraph.node.exhaustion | 35 | 122 | 29% | -0.190 |
| convgraph.node.recency | 35 | 122 | 29% | 0.159 |
| convgraph.node.chain.fan_in | 32 | 45 | 71% | 0.035 |
| convgraph.node.llm.charge.positive | 24 | 45 | 53% | 0.100 |
| convgraph.node.chain.has_attribute_foundation.false | 16 | 48 | 33% | -0.359 |
| convgraph.node.is_orphan.true | 12 | 12 | 100% | 0.500 |
| response.semantic.llm.engagement.mid | 9 | 9 | 100% | 0.400 |
| response.semantic.llm.certainty.mid | 8 | 9 | 89% | 0.700 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| convgraph.node.chain.gap.below.true | 3 | 3 | 100% | 0.300 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| interview.phase.late | 1 | 9 | 11% | -0.500 |
| response.semantic.llm.certainty.low | 1 | 9 | 11% | 1.000 |

## Global Signals

- `response.semantic.llm.engagement.trend.fatigued`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.mid`
- `response.semantic.llm.engagement.high`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`
- `response.semantic.llm.certainty.low`
- `response.semantic.llm.certainty.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.chain.has_terminal_apex.true | 0.50 |
| convgraph.node.focus.count.high | 0.80 |
| convgraph.node.focus.count.medium | 0.40 |
| convgraph.node.llm.elaboration.high | 0.40 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.high | 0.40 |
| response.semantic.llm.engagement.low | 0.80 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.chain.branching_deficit | 62 | 62 | 100% |
| convgraph.node.chain.gap.above.true | 45 | 45 | 100% |
| convgraph.node.is_orphan.true | 12 | 12 | 100% |
| response.semantic.llm.engagement.mid | 9 | 9 | 100% |
| response.semantic.llm.certainty.mid | 8 | 9 | 89% |
| convgraph.node.chain.gap.below.true | 3 | 3 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 4/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | unknown | anchor | revitalize | 1.20 | 1.00 | 0.100 |
| 2 | unknown | branch | anchor | 1.40 | 1.20 | 0.110 |
| 3 | unknown | branch | branch | 1.40 | 1.40 | 0.000 |
| 4 | unknown | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 5 | unknown | anchor | branch | 1.00 | 1.00 | 0.000 |
| 6 | unknown | anchor | branch | 1.00 | 1.00 | 0.000 |
| 7 | unknown | ground | anchor | 1.30 | 1.00 | 0.165 |
| 8 | unknown | ground | anchor | 1.30 | 1.00 | 0.188 |
| 9 | unknown | validate | branch | 1.50 | 1.10 | 0.280 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| branch | 25.662 | -3.468 | 22.194 |
| anchor | 7.910 | -1.296 | 6.614 |
| revitalize | 3.600 | -0.500 | 3.100 |
| ground | 2.150 | -0.402 | 1.748 |
| ascend | 23.085 | -21.496 | 1.589 |
| validate | 6.600 | -24.000 | -17.400 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| being productive and self-sufficient | 68dcb24c | 2 |
| perceived active cooling effect | 6e42aace | 2 |
| greater satisfaction vs flat drink | 73314a7d | 1 |

## Gate Analysis

| Strategy | Gate Signal | Nodes Gated | Turns Affected |
|----------|-------------|-------------|----------------|
| bridge | convgraph.node.chain.level.skip | 29 | 9 |
| ground | convgraph.node.chain.gap.below | 28 | 9 |
| anchor | convgraph.node.is_orphan | 27 | 9 |
| ascend | convgraph.node.chain.gap.above | 21 | 9 |
| branch | convgraph.node.chain.branching_deficit | 16 | 9 |
