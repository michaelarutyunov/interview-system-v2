# Scoring Summary

Source: `04_scoring.csv`
Total rows: 25,731 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1920 | 1953 | 98% | 0.300 |
| convgraph.node.focus.count.none | 1794 | 1953 | 92% | 0.200 |
| interview.strategy.self_count | 1341 | 2628 | 51% | -0.086 |
| meta.saturation.canonical.high | 1100 | 1302 | 84% | -0.300 |
| convgraph.node.novelty.high | 732 | 1953 | 38% | 0.267 |
| response.semantic.llm.certainty.low | 651 | 651 | 100% | 0.800 |
| response.semantic.llm.engagement.high | 651 | 651 | 100% | 0.100 |
| convgraph.node.chain.has_attribute_foundation.false | 396 | 722 | 55% | -0.150 |
| convgraph.node.llm.elaboration.low | 340 | 578 | 59% | 0.375 |
| convgraph.node.chain.has_attribute_foundation.true | 326 | 722 | 45% | 0.075 |
| meta.saturation.conversation.high | 170 | 1302 | 13% | -0.400 |
| convgraph.node.exhaustion | 159 | 1953 | 8% | -0.121 |
| convgraph.node.recency | 159 | 1953 | 8% | 0.223 |
| convgraph.node.llm.charge.negative | 112 | 578 | 19% | 0.275 |
| convgraph.node.llm.elaboration.high | 112 | 1156 | 10% | -0.012 |
| convgraph.node.chain.gap.below.true | 109 | 361 | 30% | 0.500 |
| canongraph.node.novelty.new | 85 | 651 | 13% | 0.300 |
| convgraph.node.llm.charge.positive | 70 | 289 | 24% | 0.100 |
| convgraph.node.chain.gap.above.true | 56 | 361 | 16% | 0.500 |
| convgraph.node.is_orphan.true | 13 | 651 | 2% | 0.500 |
| meta.saturation.canonical | 12 | 12 | 100% | -0.354 |
| meta.saturation.conversation | 11 | 12 | 92% | -0.214 |
| interview.phase.early | 8 | 24 | 33% | -3.000 |
| interview.phase.mid | 5 | 12 | 42% | -3.000 |
| interview.phase.late | 3 | 12 | 25% | 0.800 |
| convgraph.node.focus.count.medium | 1 | 651 | 0% | -0.200 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.conversation`
- `meta.saturation.canonical`
- `interview.phase.early`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.focus.count.high | 0.40 |
| response.semantic.llm.certainty.mid | 0.40 |
| response.semantic.llm.engagement.low | 0.50 |
| response.semantic.llm.engagement.trend.fatigued | 0.80 |
| response.semantic.llm.engagement.trend.shallowing | 0.30 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1920 | 1953 | 98% |
| convgraph.node.focus.count.none | 1794 | 1953 | 92% |
| meta.saturation.canonical.high | 1100 | 1302 | 84% |
| response.semantic.llm.certainty.low | 651 | 651 | 100% |
| response.semantic.llm.engagement.high | 651 | 651 | 100% |
| meta.saturation.canonical | 12 | 12 | 100% |
| meta.saturation.conversation | 11 | 12 | 92% |

## Phase Multiplier Differential

Gap widened by multiplier: 3/12 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | ascend | surface_tension | 1.00 | 1.00 | 0.000 |
| 3 | early | ascend | surface_tension | 1.00 | 1.00 | 0.000 |
| 4 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 5 | mid | ascend | surface_tension | 1.30 | 1.00 | 0.462 |
| 6 | mid | ascend | surface_tension | 1.30 | 1.00 | 0.453 |
| 7 | mid | ascend | surface_tension | 1.30 | 1.00 | 0.444 |
| 8 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | surface_tension | ground | 1.00 | 1.30 | -0.495 |
| 10 | late | surface_tension | close | 1.00 | 1.50 | -0.795 |
| 11 | late | surface_tension | close | 1.00 | 1.50 | -0.765 |
| 12 | late | surface_tension | close | 1.00 | 1.50 | -0.735 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| surface_tension | 636.800 | -40.960 | 595.840 |
| ascend | 506.255 | -164.732 | 341.523 |
| anchor | 513.170 | -213.904 | 299.266 |
| ground | 481.405 | -255.648 | 225.757 |
| revitalize | 0.000 | -18.603 | -18.603 |
| close | 2.400 | -27.000 | -24.600 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| relax and let go of tension around drink choices | 5d0136c8 | 2 |
| regular soda tastes more like an actual treat | 32796570 | 1 |
| feel like a responsible person who doesn't sabotage themselves | 29e114c7 | 1 |
| feel like I'm taking care of myself while still enjoying fizzy drinks | 491014d8 | 1 |
| craving something fizzy | 69375adc | 1 |
| feel like I'm actively doing something (not passively drinking) | a29ae3c7 | 1 |
| water feels boring when craving carbonation | cfc80c2e | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
