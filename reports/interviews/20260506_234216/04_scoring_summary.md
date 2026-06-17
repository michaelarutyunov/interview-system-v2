# Scoring Summary

Source: `04_scoring.csv`
Total rows: 21,852 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| meta.saturation.canonical.high | 1248 | 1278 | 98% | -0.300 |
| convgraph.node.focus.streak.none | 1239 | 1278 | 97% | 0.300 |
| convgraph.node.focus.count.none | 1056 | 1278 | 83% | 0.200 |
| interview.strategy.self_count | 1022 | 1732 | 59% | -0.117 |
| convgraph.node.chain.has_attribute_foundation.false | 732 | 852 | 86% | -0.150 |
| convgraph.node.novelty.high | 450 | 1278 | 35% | 0.267 |
| convgraph.node.is_orphan.true | 332 | 426 | 78% | 0.500 |
| convgraph.node.chain.gap.above.true | 330 | 426 | 78% | 0.500 |
| convgraph.node.chain.gap.below.true | 316 | 426 | 74% | 0.500 |
| convgraph.state.node.orphan_ratio.high | 287 | 426 | 67% | 0.400 |
| convgraph.state.node.orphan_ratio.mid | 278 | 852 | 33% | 0.250 |
| response.semantic.llm.certainty.low | 230 | 426 | 54% | 0.400 |
| convgraph.node.exhaustion | 222 | 1278 | 17% | -0.133 |
| convgraph.node.llm.charge.negative | 222 | 852 | 26% | 0.275 |
| convgraph.node.recency | 222 | 1278 | 17% | 0.218 |
| convgraph.node.llm.elaboration.low | 187 | 426 | 44% | 0.150 |
| response.semantic.llm.engagement.high | 177 | 426 | 42% | 0.100 |
| meta.saturation.conversation.high | 172 | 852 | 20% | -0.400 |
| convgraph.node.llm.charge.positive | 157 | 426 | 37% | 0.100 |
| response.semantic.llm.engagement.low | 126 | 866 | 14% | -0.286 |
| convgraph.node.chain.has_attribute_foundation.true | 120 | 852 | 14% | 0.075 |
| response.semantic.llm.certainty.mid | 110 | 426 | 26% | 0.200 |
| convgraph.node.llm.elaboration.high | 66 | 1278 | 5% | 0.117 |
| convgraph.node.yield_stagnation.true | 41 | 426 | 10% | 0.250 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.275 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| convgraph.node.focus.count.medium | 4 | 852 | 0% | -0.050 |
| response.semantic.llm.engagement.trend.shallowing | 2 | 14 | 14% | 0.400 |
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
| response.semantic.llm.engagement.trend.fatigued | 0.90 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| meta.saturation.canonical.high | 1248 | 1278 | 98% |
| convgraph.node.focus.streak.none | 1239 | 1278 | 97% |
| convgraph.node.focus.count.none | 1056 | 1278 | 83% |
| convgraph.node.chain.has_attribute_foundation.false | 732 | 852 | 86% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | ascend | ground | 1.00 | 1.20 | -0.350 |
| 3 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 5 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | anchor | 1.30 | 1.00 | 0.414 |
| 9 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | anchor | anchor | 1.00 | 1.00 | 0.000 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 622.370 | -230.072 | 392.298 |
| ground | 517.030 | -192.284 | 324.746 |
| ascend | 481.930 | -277.576 | 204.354 |
| surface_tension | 152.200 | -124.800 | 27.400 |
| revitalize | 2.000 | -3.853 | -1.853 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| during afternoon work hours when trying to stay focused | 2684928f | 3 |
| avoiding excess sugar rather than embracing diet drinks | ae2214a9 | 2 |
| after a heavy meal | 1e3618ed | 1 |
| being at a social setting or restaurant where sugar-free options are available | 39fcef42 | 1 |
| staying late due to mid-afternoon productivity loss | 5e042fe9 | 1 |
| dragging by 3pm mid-afternoon | 4f9a89a8 | 1 |
| uncertainty about whether ZeroFizz meaningfully improves focus versus regular soda | a20d9214 | 1 |
| experiencing a sugar crash that disrupts focus | a93f5217 | 1 |
| drinking regular soda in the afternoon | e627b9b1 | 1 |
| being in a flow state at work without interruption | ed3ea243 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
