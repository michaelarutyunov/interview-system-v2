# Scoring Summary

Source: `04_scoring.csv`
Total rows: 20,598 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1119 | 1158 | 97% | 0.300 |
| convgraph.node.focus.count.none | 897 | 1158 | 78% | 0.200 |
| meta.saturation.canonical.high | 858 | 1158 | 74% | -0.300 |
| interview.strategy.self_count | 802 | 1572 | 51% | -0.180 |
| convgraph.node.novelty.high | 564 | 1544 | 36% | 0.263 |
| convgraph.node.chain.has_attribute_foundation.true | 430 | 772 | 56% | 0.075 |
| convgraph.node.recency | 348 | 1544 | 22% | 0.190 |
| convgraph.node.chain.has_attribute_foundation.false | 342 | 772 | 44% | -0.150 |
| convgraph.node.exhaustion | 261 | 1158 | 22% | -0.155 |
| convgraph.node.llm.elaboration.low | 225 | 386 | 58% | 0.150 |
| convgraph.node.chain.gap.above.true | 165 | 386 | 43% | 0.500 |
| convgraph.node.llm.charge.negative | 164 | 772 | 21% | 0.275 |
| response.semantic.llm.certainty.low | 164 | 386 | 42% | 0.400 |
| convgraph.state.node.orphan_ratio.mid | 152 | 786 | 19% | 0.247 |
| convgraph.node.chain.gap.below.true | 144 | 386 | 37% | 0.500 |
| response.semantic.llm.engagement.high | 121 | 386 | 31% | 0.100 |
| convgraph.node.is_orphan.true | 81 | 386 | 21% | 0.500 |
| meta.saturation.conversation.high | 68 | 772 | 9% | -0.400 |
| convgraph.node.yield_stagnation.true | 52 | 386 | 14% | 0.250 |
| response.semantic.llm.engagement.low | 51 | 786 | 6% | -0.282 |
| convgraph.node.llm.charge.positive | 34 | 386 | 9% | 0.100 |
| convgraph.node.llm.elaboration.high | 24 | 1158 | 2% | 0.117 |
| meta.saturation.canonical | 13 | 14 | 93% | -0.269 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| response.semantic.llm.engagement.trend.fatigued | 5 | 14 | 36% | 0.900 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| response.semantic.llm.engagement.trend.shallowing | 3 | 14 | 21% | 0.400 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.canonical`
- `convgraph.state.node.orphan_ratio.mid`
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
| convgraph.state.node.orphan_ratio.high | 0.40 |
| response.semantic.llm.certainty.mid | 0.20 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1119 | 1158 | 97% |
| meta.saturation.canonical | 13 | 14 | 93% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | ascend | anchor | 1.00 | 1.20 | -0.330 |
| 5 | early | ascend | ground | 1.00 | 1.20 | -0.280 |
| 6 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 7 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 8 | mid | ascend | ground | 1.30 | 1.50 | -0.310 |
| 9 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ascend | ground | 1.30 | 1.50 | -0.310 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ascend | 1.50 | 1.30 | 0.228 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 423.500 | -209.492 | 214.008 |
| anchor | 325.200 | -126.024 | 199.176 |
| ground | 352.900 | -191.748 | 161.152 |
| surface_tension | 144.775 | -85.800 | 58.975 |
| revitalize | 6.900 | -3.500 | 3.400 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| meetings being a slog regardless of what you drink | 4e10afa2 | 2 |
| settling for regular soda when sugar-free option isn't available | 08f63f6b | 1 |
| low attachment to any specific drink when preferred option is unavailable | 0ee6cc8a | 1 |
| drifting passively rather than actively struggling to stay focused | 09006913 | 1 |
| avoiding leaving a meeting to seek out a preferred drink | 20f78946 | 1 |
| choosing ZeroFizz over water or coffee when thirsty | 76585528 | 1 |
| not consciously framing drink choice around focus or productivity | 96db72c7 | 1 |
| already zoning out during meetings | bda02c29 | 1 |
| breaking focus and workflow by leaving mid-meeting | c8df24be | 1 |
| having to walk to the vending machine mid-task | cb41d80d | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
