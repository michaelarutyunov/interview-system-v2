# Scoring Summary

Source: `04_scoring.csv`
Total rows: 19,557 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1104 | 1143 | 97% | 0.300 |
| convgraph.node.focus.count.none | 909 | 1143 | 80% | 0.200 |
| meta.saturation.canonical.high | 852 | 1143 | 74% | -0.300 |
| convgraph.state.node.orphan_ratio.mid | 746 | 762 | 98% | 0.250 |
| interview.strategy.self_count | 737 | 1552 | 48% | -0.140 |
| convgraph.node.chain.has_attribute_foundation.true | 442 | 762 | 58% | 0.075 |
| convgraph.node.novelty.high | 390 | 1143 | 34% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.false | 320 | 762 | 42% | -0.150 |
| convgraph.node.exhaustion | 234 | 1143 | 20% | -0.126 |
| convgraph.node.recency | 234 | 1143 | 20% | 0.218 |
| convgraph.node.llm.elaboration.low | 208 | 381 | 55% | 0.150 |
| meta.saturation.conversation.high | 202 | 762 | 26% | -0.400 |
| convgraph.node.chain.gap.above.true | 174 | 381 | 46% | 0.500 |
| response.semantic.llm.certainty.low | 172 | 381 | 45% | 0.400 |
| convgraph.node.llm.charge.negative | 168 | 762 | 22% | 0.275 |
| convgraph.node.is_orphan.true | 145 | 381 | 38% | 0.500 |
| convgraph.node.chain.gap.below.true | 134 | 381 | 35% | 0.500 |
| convgraph.node.llm.charge.positive | 108 | 381 | 28% | 0.100 |
| response.semantic.llm.engagement.low | 78 | 776 | 10% | -0.277 |
| response.semantic.llm.engagement.high | 74 | 381 | 19% | 0.100 |
| convgraph.node.yield_stagnation.true | 44 | 381 | 12% | 0.250 |
| convgraph.node.llm.elaboration.high | 30 | 1143 | 3% | 0.117 |
| meta.saturation.canonical | 13 | 14 | 93% | -0.251 |
| convgraph.state.node.orphan_ratio.high | 8 | 381 | 2% | 0.400 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| response.semantic.llm.engagement.trend.shallowing | 5 | 14 | 36% | 0.400 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.canonical`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| canongraph.node.novelty.new | 0.30 |
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.focus.count.medium | 0.20 |
| response.semantic.llm.certainty.mid | 0.20 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1104 | 1143 | 97% |
| convgraph.state.node.orphan_ratio.mid | 746 | 762 | 98% |
| meta.saturation.canonical | 13 | 14 | 93% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | ascend | 1.20 | 1.00 | 0.302 |
| 4 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 5 | early | ground | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 426.330 | -159.264 | 267.066 |
| ascend | 430.020 | -173.192 | 256.828 |
| ground | 415.420 | -198.728 | 216.692 |
| surface_tension | 100.800 | -85.200 | 15.600 |
| revitalize | 3.200 | -3.265 | -0.065 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| feel in control of personal choices without compromise | 7b27a9a6 | 2 |
| having a headache and running out of usual drink option | 9b6c982b | 2 |
| usual go-to drink being unavailable | 1cd75d12 | 1 |
| drink choice driven by proximity and availability rather than preference | 2e417ef3 | 1 |
| avoiding sugar crash after drinking soda | 1e2fdd3c | 1 |
| resenting a drink even when it tastes fine if it feels imposed | 624c4d09 | 1 |
| drink availability at point of need drives consumption without deliberate choice | 53c3ec54 | 1 |
| being tired in the afternoon but not wanting to rely on caffeine | 743db436 | 1 |
| drink choice driven by what feels right in the moment rather than what is available or prescribed | 9c170d3d | 1 |
| feeling reassured knowing a suitable drink option is available when needed | dcce58e1 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
