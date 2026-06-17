# Scoring Summary

Source: `04_scoring.csv`
Total rows: 22,453 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1224 | 1263 | 97% | 0.300 |
| convgraph.node.focus.count.none | 1038 | 1263 | 82% | 0.200 |
| meta.saturation.canonical.high | 831 | 1263 | 66% | -0.300 |
| interview.strategy.self_count | 785 | 1712 | 46% | -0.148 |
| convgraph.node.novelty.high | 600 | 1684 | 36% | 0.263 |
| convgraph.node.chain.has_attribute_foundation.true | 550 | 842 | 65% | 0.075 |
| convgraph.node.llm.elaboration.low | 310 | 421 | 74% | 0.150 |
| convgraph.node.recency | 300 | 1684 | 18% | 0.196 |
| convgraph.node.chain.has_attribute_foundation.false | 292 | 842 | 35% | -0.150 |
| convgraph.state.node.orphan_ratio.mid | 247 | 856 | 29% | 0.248 |
| response.semantic.llm.certainty.low | 235 | 421 | 56% | 0.400 |
| convgraph.node.exhaustion | 225 | 1263 | 18% | -0.164 |
| response.semantic.llm.engagement.low | 163 | 856 | 19% | -0.283 |
| convgraph.node.chain.gap.above.true | 157 | 421 | 37% | 0.500 |
| convgraph.node.chain.gap.below.true | 139 | 421 | 33% | 0.500 |
| convgraph.node.is_orphan.true | 131 | 421 | 31% | 0.500 |
| convgraph.node.llm.charge.negative | 102 | 842 | 12% | 0.275 |
| convgraph.node.llm.charge.positive | 89 | 421 | 21% | 0.100 |
| response.semantic.llm.certainty.mid | 53 | 421 | 13% | 0.200 |
| meta.saturation.conversation.high | 44 | 842 | 5% | -0.400 |
| convgraph.node.yield_stagnation.true | 40 | 421 | 10% | 0.250 |
| response.semantic.llm.engagement.high | 36 | 421 | 9% | 0.100 |
| convgraph.state.node.orphan_ratio.high | 31 | 421 | 7% | 0.400 |
| convgraph.node.llm.elaboration.high | 24 | 1263 | 2% | 0.117 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.262 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| response.semantic.llm.engagement.trend.fatigued | 5 | 14 | 36% | 0.900 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 14 | 7% | 0.400 |

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

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1224 | 1263 | 97% |
| convgraph.node.focus.count.none | 1038 | 1263 | 82% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 3 | early | ascend | anchor | 1.00 | 1.20 | -0.314 |
| 4 | early | ascend | anchor | 1.00 | 1.20 | -0.326 |
| 5 | early | ground | revitalize | 1.20 | 1.00 | 0.280 |
| 6 | mid | ascend | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 8 | mid | ground | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 14 | late | close | ground | 1.50 | 0.90 | 1.200 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 478.620 | -191.992 | 286.628 |
| anchor | 377.630 | -126.964 | 250.666 |
| ground | 377.020 | -193.628 | 183.392 |
| surface_tension | 174.135 | -83.100 | 91.035 |
| revitalize | 7.450 | -3.670 | 3.780 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| mid-afternoon energy slump at work | 12c1e9b2 | 2 |
| sugar consciousness varies day to day rather than being a fixed rule | ed1fcc3a | 2 |
| grabbing a regular Coke or Sprite when not watching sugar | 2a163e1e | 1 |
| physical placement and visibility removes the need to decide | 4dea9b50 | 1 |
| eliminate the moment of choosing between drink options | 5de56cb5 | 1 |
| feel instantly resolved without deliberation | 726d76e2 | 1 |
| brand is irrelevant when any available option satisfies the need | 63fb949f | 1 |
| morning thirst or routine as context for coffee choice | 7a607226 | 1 |
| when at work during the afternoon | 7b641832 | 1 |
| zero-sugar drink grab is a pre-gym ritual, like putting on shoes | 998a5a9d | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
