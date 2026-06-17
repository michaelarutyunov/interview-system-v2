# Scoring Summary

Source: `04_scoring.csv`
Total rows: 12,913 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1128 | 1160 | 97% | 0.300 |
| convgraph.node.focus.count.none | 1056 | 1160 | 91% | 0.200 |
| convgraph.node.novelty.high | 572 | 1160 | 49% | 0.250 |
| interview.strategy.self_count | 494 | 1187 | 42% | -0.093 |
| response.semantic.llm.engagement.high | 166 | 299 | 56% | 0.088 |
| convgraph.node.chain.has_attribute_foundation.false | 148 | 292 | 51% | -0.150 |
| convgraph.node.chain.has_attribute_foundation.true | 144 | 292 | 49% | 0.075 |
| canongraph.node.novelty.new | 106 | 580 | 18% | 0.300 |
| convgraph.node.exhaustion | 104 | 1160 | 9% | -0.095 |
| convgraph.node.recency | 104 | 1160 | 9% | 0.223 |
| convgraph.node.llm.elaboration.low | 72 | 138 | 52% | 0.150 |
| convgraph.node.llm.charge.positive | 47 | 138 | 34% | 0.100 |
| convgraph.node.chain.gap.above.true | 46 | 146 | 32% | 0.500 |
| convgraph.node.llm.charge.negative | 38 | 138 | 28% | 0.300 |
| convgraph.node.chain.gap.below.true | 36 | 146 | 25% | 0.500 |
| convgraph.node.llm.elaboration.high | 18 | 414 | 4% | 0.117 |
| response.semantic.llm.engagement.mid | 10 | 18 | 56% | 0.400 |
| meta.saturation.canonical | 9 | 9 | 100% | 0.174 |
| meta.saturation.conversation | 7 | 9 | 78% | 0.096 |
| response.semantic.llm.certainty.mid | 5 | 9 | 56% | 0.700 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| convgraph.node.focus.streak.medium | 3 | 290 | 1% | -0.300 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| response.semantic.llm.certainty.low | 3 | 9 | 33% | 1.000 |
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
| canongraph.node.novelty.orphan | 0.20 |
| convgraph.node.focus.count.high | 0.60 |
| convgraph.node.focus.count.medium | 0.30 |
| convgraph.node.focus.streak.high | 0.60 |
| convgraph.node.is_orphan.true | 0.50 |
| interview.strategy.self_count.high | 1.00 |
| response.semantic.llm.engagement.low | 0.80 |
| response.semantic.llm.engagement.trend.fatigued | 1.00 |
| response.semantic.llm.engagement.trend.shallowing | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1128 | 1160 | 97% |
| convgraph.node.focus.count.none | 1056 | 1160 | 91% |
| meta.saturation.canonical | 9 | 9 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | probe_pain | 1.00 | 1.20 | -0.320 |
| 2 | early | ground | ascend | 1.20 | 1.00 | 0.290 |
| 3 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 4 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 5 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | late | validate | ascend | 1.50 | 1.00 | 0.487 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 217.040 | -1.240 | 215.800 |
| probe_pain | 199.140 | -3.380 | 195.760 |
| ascend | 244.410 | -65.710 | 178.700 |
| ground | 213.210 | -38.060 | 175.150 |
| elaborate | 2.000 | 0.000 | 2.000 |
| revitalize | 2.000 | -2.100 | -0.100 |
| validate | 8.742 | -24.000 | -15.258 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| feel present and purposeful at work | 8d0797bd | 2 |
| coffee causes intense wired-then-crash cycle | 9547ae6c | 2 |
| having something physical to do with hands during breaks | c99899e2 | 2 |
| difficulty recalling specific sugar-free drink occasions | a6f048c2 | 1 |
| maintain steady energy through the afternoon | fc0fd35b | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
