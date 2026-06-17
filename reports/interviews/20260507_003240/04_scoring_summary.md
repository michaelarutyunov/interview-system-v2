# Scoring Summary

Source: `04_scoring.csv`
Total rows: 22,209 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1260 | 1299 | 97% | 0.300 |
| convgraph.node.focus.count.none | 1038 | 1299 | 80% | 0.200 |
| interview.strategy.self_count | 788 | 1760 | 45% | -0.151 |
| convgraph.state.node.orphan_ratio.mid | 618 | 866 | 71% | 0.250 |
| meta.saturation.canonical.high | 615 | 1299 | 47% | -0.300 |
| convgraph.node.chain.has_attribute_foundation.false | 526 | 866 | 61% | -0.150 |
| convgraph.node.novelty.high | 465 | 1299 | 36% | 0.267 |
| convgraph.node.chain.has_attribute_foundation.true | 340 | 866 | 39% | 0.075 |
| convgraph.node.chain.gap.above.true | 295 | 433 | 68% | 0.500 |
| convgraph.node.is_orphan.true | 290 | 433 | 67% | 0.500 |
| convgraph.node.recency | 261 | 1299 | 20% | 0.213 |
| convgraph.node.exhaustion | 261 | 1299 | 20% | -0.167 |
| convgraph.node.chain.gap.below.true | 249 | 433 | 58% | 0.500 |
| convgraph.node.llm.elaboration.low | 236 | 433 | 54% | 0.150 |
| response.semantic.llm.certainty.low | 207 | 433 | 48% | 0.400 |
| convgraph.node.llm.charge.negative | 164 | 866 | 19% | 0.275 |
| response.semantic.llm.engagement.high | 147 | 433 | 34% | 0.100 |
| convgraph.state.node.orphan_ratio.high | 124 | 433 | 29% | 0.400 |
| response.semantic.llm.engagement.low | 122 | 880 | 14% | -0.285 |
| response.semantic.llm.certainty.mid | 113 | 433 | 26% | 0.200 |
| convgraph.node.llm.charge.positive | 96 | 433 | 22% | 0.100 |
| convgraph.node.llm.elaboration.high | 81 | 1299 | 6% | 0.117 |
| convgraph.node.yield_stagnation.true | 52 | 433 | 12% | 0.250 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.238 |
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

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1260 | 1299 | 97% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 1/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 4 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 5 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 6 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 7 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 8 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 9 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 12 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 13 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 14 | late | close | ground | 1.50 | 0.90 | 1.200 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| anchor | 572.150 | -114.644 | 457.506 |
| ground | 510.500 | -136.808 | 373.692 |
| ascend | 509.500 | -235.612 | 273.888 |
| surface_tension | 138.900 | -61.500 | 77.400 |
| revitalize | 6.100 | -3.325 | 2.775 |
| close | 2.000 | -39.000 | -37.000 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| carbonation bridging the gap between water and heavy soda | 0a49dc98 | 2 |
| experiencing an energy crash after drinking | 3979425c | 1 |
| craving drives drink choice more than category preference | 4b04fd49 | 1 |
| feeling thirsty and needing refreshment | 6cbe446e | 1 |
| feeling refreshed and cooled down in heat or thirst | 737a9d32 | 1 |
| drink feeling too light leaving thirst unresolved | c1b1e268 | 1 |
| casual thirst reducing drink selectivity to whatever is available | c3d2feb5 | 1 |
| feeling jittery from current drinks | d064bed4 | 1 |
| drink feels unremarkable and unsatisfying | e2afdaf8 | 1 |
| staying alert and focused without a post-drink crash | ec0bd2a4 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
