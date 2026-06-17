# Scoring Summary

Source: `04_scoring.csv`
Total rows: 15,088 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1095 | 1125 | 97% | 0.300 |
| convgraph.node.focus.count.none | 981 | 1125 | 87% | 0.200 |
| interview.strategy.self_count | 850 | 1522 | 56% | -0.096 |
| convgraph.node.novelty.high | 489 | 1125 | 44% | 0.267 |
| meta.saturation.canonical.high | 440 | 750 | 59% | -0.300 |
| convgraph.node.chain.has_attribute_foundation.true | 228 | 394 | 58% | 0.075 |
| response.semantic.llm.engagement.high | 224 | 375 | 60% | 0.100 |
| response.semantic.llm.certainty.low | 168 | 375 | 45% | 0.400 |
| convgraph.node.chain.has_attribute_foundation.false | 166 | 394 | 42% | -0.150 |
| convgraph.node.exhaustion | 144 | 1125 | 13% | -0.126 |
| convgraph.node.recency | 144 | 1125 | 13% | 0.229 |
| response.semantic.llm.certainty.mid | 115 | 375 | 31% | 0.200 |
| convgraph.node.llm.elaboration.low | 90 | 151 | 60% | 0.150 |
| canongraph.node.novelty.new | 61 | 375 | 16% | 0.300 |
| convgraph.node.llm.charge.negative | 50 | 302 | 17% | 0.275 |
| convgraph.node.chain.gap.below.true | 47 | 197 | 24% | 0.500 |
| convgraph.node.llm.charge.positive | 40 | 151 | 26% | 0.100 |
| convgraph.node.yield_stagnation.true | 22 | 375 | 6% | 0.250 |
| convgraph.node.llm.elaboration.high | 12 | 453 | 3% | 0.117 |
| meta.saturation.canonical | 11 | 11 | 100% | -0.232 |
| interview.phase.mid | 6 | 11 | 54% | -3.000 |
| convgraph.node.chain.gap.above.true | 5 | 197 | 2% | 0.500 |
| interview.phase.early | 4 | 11 | 36% | -3.000 |
| convgraph.node.focus.count.medium | 2 | 750 | 0% | -0.050 |
| interview.phase.late | 1 | 11 | 9% | 2.000 |

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
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.is_orphan.true | 0.50 |
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.low | 0.60 |
| response.semantic.llm.engagement.trend.fatigued | 0.90 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1095 | 1125 | 97% |
| convgraph.node.focus.count.none | 981 | 1125 | 87% |
| meta.saturation.canonical | 11 | 11 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/11 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ground | 1.00 | 1.20 | -0.320 |
| 2 | early | anchor | ascend | 1.20 | 1.00 | 0.220 |
| 3 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 5 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 6 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 288.325 | -67.116 | 221.209 |
| anchor | 281.050 | -77.972 | 203.078 |
| ground | 268.325 | -151.564 | 116.761 |
| surface_tension | 102.050 | 0.000 | 102.050 |
| revitalize | 0.000 | -2.550 | -2.550 |
| close | 2.000 | -30.000 | -28.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| choosing ZeroFizz over regular soda | 6ceaeb23 | 2 |
| fizz provides refreshment and a little kick | 17df1309 | 1 |
| excessive sweetness of juice feels like drinking liquid candy | 1803a953 | 1 |
| at work during the afternoon | 3d7ee457 | 1 |
| caffeine provides the real functional benefit | bd481bcf | 1 |
| choosing zero sugar soda as easy, low-caffeine alternative | c12f5a9d | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
