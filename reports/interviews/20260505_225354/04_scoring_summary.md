# Scoring Summary

Source: `04_scoring.csv`
Total rows: 8,433 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 498 | 522 | 95% | 0.300 |
| convgraph.node.focus.count.none | 414 | 522 | 79% | 0.200 |
| meta.saturation.canonical.high | 375 | 522 | 72% | -0.300 |
| interview.strategy.self_count | 279 | 714 | 39% | -0.151 |
| convgraph.node.novelty.high | 255 | 522 | 49% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.false | 182 | 348 | 52% | -0.150 |
| convgraph.node.chain.has_attribute_foundation.true | 166 | 348 | 48% | 0.075 |
| response.semantic.llm.engagement.high | 151 | 174 | 87% | 0.100 |
| response.semantic.llm.certainty.low | 118 | 174 | 68% | 0.400 |
| convgraph.node.chain.gap.above.true | 109 | 174 | 63% | 0.500 |
| convgraph.node.recency | 108 | 522 | 21% | 0.236 |
| convgraph.node.exhaustion | 108 | 522 | 21% | -0.129 |
| convgraph.node.is_orphan.true | 94 | 174 | 54% | 0.500 |
| convgraph.node.chain.gap.below.true | 86 | 174 | 49% | 0.500 |
| convgraph.node.llm.charge.negative | 80 | 348 | 23% | 0.275 |
| convgraph.node.llm.charge.positive | 79 | 174 | 45% | 0.100 |
| convgraph.node.llm.elaboration.low | 72 | 174 | 41% | 0.150 |
| convgraph.node.llm.elaboration.high | 63 | 522 | 12% | 0.117 |
| response.semantic.llm.certainty.mid | 24 | 174 | 14% | 0.200 |
| convgraph.node.yield_stagnation.true | 15 | 174 | 9% | 0.250 |
| response.semantic.llm.engagement.low | 13 | 357 | 4% | -0.231 |
| meta.saturation.canonical | 9 | 9 | 100% | -0.267 |
| interview.phase.mid | 5 | 9 | 56% | -3.000 |
| interview.phase.early | 3 | 9 | 33% | -3.000 |
| interview.phase.late | 1 | 9 | 11% | 2.000 |

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
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 498 | 522 | 95% |
| response.semantic.llm.engagement.high | 151 | 174 | 87% |
| meta.saturation.canonical | 9 | 9 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/9 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 2 | early | ascend | anchor | 1.00 | 1.20 | -0.338 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 5 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | late | close | ground | 1.50 | 0.90 | 1.200 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 187.560 | -48.288 | 139.272 |
| ascend | 212.540 | -89.684 | 122.856 |
| ground | 170.440 | -58.756 | 111.684 |
| surface_tension | 65.750 | -37.500 | 28.250 |
| revitalize | 0.600 | -2.400 | -1.800 |
| close | 2.000 | -24.000 | -22.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| avoiding a sugar crash during long sedentary work sessions | 14391cb3 | 1 |
| feel in control of health goals without active deliberation | 3420854e | 1 |
| freedom from questioning whether a drink choice is bad | 460bcc71 | 1 |
| navigating decision fatigue across food and drink choices daily | 7fcb5017 | 1 |
| opportunistic availability of sugar-free option prompts selection | 8bc221d2 | 1 |
| sitting at desk for extended hours during the workday | b8f6a3cb | 1 |
| knowing a drink won't interfere with health goals | cf1be543 | 1 |
| navigating high cognitive demands throughout the day | d8d19714 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
