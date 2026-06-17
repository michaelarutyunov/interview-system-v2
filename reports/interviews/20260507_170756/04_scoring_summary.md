# Scoring Summary

Source: `04_scoring.csv`
Total rows: 25,519 (gated: 0)

> ⚠ **Scope**: This summary detects systemic issues — dead signals, always-firing signals, gate blockages, phase multiplier effects. It does **not** support weight tuning decisions. Weight changes require per-turn conversational evidence: identify the specific turn where a different strategy should have been selected, quote the respondent's words, and verify the needed strategy's signals actually fired. See `.claude/context/methodology-parameter-flow.md` §Calibration Principles.

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1296 | 1335 | 97% | 0.300 |
| convgraph.node.focus.count.none | 1098 | 1335 | 82% | 0.200 |
| interview.strategy.self_count | 1032 | 1808 | 57% | -0.173 |
| meta.saturation.canonical.high | 918 | 1335 | 69% | -0.300 |
| convgraph.state.node.orphan_ratio.mid | 756 | 904 | 84% | 0.249 |
| convgraph.node.chain.has_attribute_foundation.true | 638 | 890 | 72% | 0.075 |
| convgraph.node.novelty.high | 604 | 1780 | 34% | 0.263 |
| convgraph.node.recency | 316 | 1780 | 18% | 0.196 |
| convgraph.node.llm.elaboration.low | 293 | 445 | 66% | 0.150 |
| convgraph.node.chain.has_attribute_foundation.false | 252 | 890 | 28% | -0.150 |
| convgraph.node.llm.charge.negative | 252 | 890 | 28% | 0.275 |
| convgraph.node.exhaustion | 237 | 1335 | 18% | -0.159 |
| meta.saturation.conversation.high | 206 | 890 | 23% | -0.400 |
| convgraph.node.chain.gap.above.true | 179 | 445 | 40% | 0.500 |
| response.semantic.llm.certainty.low | 178 | 445 | 40% | 0.400 |
| response.semantic.llm.engagement.high | 129 | 445 | 29% | 0.100 |
| response.semantic.llm.engagement.low | 128 | 904 | 14% | -0.286 |
| convgraph.node.llm.charge.positive | 112 | 445 | 25% | 0.100 |
| convgraph.node.chain.gap.below.true | 71 | 445 | 16% | 0.500 |
| convgraph.node.yield_stagnation.true | 44 | 445 | 10% | 0.250 |
| convgraph.node.is_orphan.true | 43 | 445 | 10% | 0.500 |
| convgraph.node.llm.elaboration.high | 30 | 1335 | 2% | 0.117 |
| meta.saturation.canonical | 14 | 14 | 100% | -0.246 |
| convgraph.state.node.orphan_ratio.high | 14 | 445 | 3% | 0.400 |
| interview.phase.mid | 8 | 14 | 57% | -3.000 |
| response.semantic.llm.engagement.trend.fatigued | 7 | 14 | 50% | 0.900 |
| interview.phase.early | 5 | 14 | 36% | -3.000 |
| interview.phase.late | 1 | 14 | 7% | 2.000 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `response.semantic.llm.frame_resistance.true`
- `meta.saturation.canonical`
- `convgraph.state.node.orphan_ratio.mid`
- `interview.phase.late`
- `interview.phase.early`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| canongraph.node.novelty.new | 0.30 |
| convgraph.node.focus.count.high | 0.90 |
| convgraph.node.focus.count.medium | 0.50 |
| response.semantic.llm.certainty.mid | 0.20 |
| response.semantic.llm.engagement.trend.shallowing | 0.40 |
| response.semantic.llm.frame_resistance.true | 1.50 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1296 | 1335 | 97% |
| convgraph.node.focus.count.none | 1098 | 1335 | 82% |
| convgraph.state.node.orphan_ratio.mid | 756 | 904 | 84% |
| meta.saturation.canonical | 14 | 14 | 100% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/14 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 2 | early | anchor | anchor | 1.20 | 1.20 | 0.000 |
| 3 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | anchor | ascend | 1.20 | 1.00 | 0.282 |
| 5 | early | ascend | ascend | 1.00 | 1.00 | 0.000 |
| 6 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 7 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 8 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 9 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 10 | mid | ascend | ascend | 1.30 | 1.30 | 0.000 |
| 11 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 12 | mid | revitalize | ascend | 1.00 | 1.30 | -0.405 |
| 13 | mid | ground | ground | 1.50 | 1.50 | 0.000 |
| 14 | late | close | ascend | 1.50 | 1.00 | 1.000 |

## Per-Turn Score Separation

Shows the winner and runner-up (strategy, node) pair for each turn with their score gap and top signal contributions. Use this to identify specific turns where selection was close and which signals drove the outcome.

| Turn | Phase | Winner | Runner-up | Gap | Winner Top Signals | Runner-up Top Signals |
|------|-------|--------|-----------|-----|--------------------|-----------------------|
| 1 | early | ascend / being at work during the … | ascend / sugar crash disrupting en… | +0.00 | true: +0.50, true: +0.35, none: +0.30 | true: +0.50, true: +0.35, none: +0.30 |
| 2 | early | anchor / experiencing an energy di… | anchor / sugar causing a wired-the… | +0.00 | true: +0.50, high: +0.40, negative: +0.30 | true: +0.50, high: +0.40, negative: +0.30 |
| 3 | early | ground / staying energised and fun… | ground / getting through afternoon… | +0.00 | true: +0.50, high: +0.40, none: +0.30 | true: +0.50, high: +0.40, none: +0.30 |
| 4 | early | anchor / experiencing an energy di… | ascend / steady, uninterrupted foc… | +0.24 | true: +0.50, none: +0.30, negative: +0.30 | true: +0.50, true: +0.35, none: +0.30 |
| 5 | early | ascend / steady, uninterrupted foc… | ascend / sugar crash disrupting en… | +0.10 | true: +0.50, true: +0.35, none: +0.30 | true: +0.50, true: +0.35, none: +0.30 |
| 6 | mid | ground / feeling foggy and unable … | ground / passively waiting for mee… | +0.00 | true: +0.50, none: +0.30, high: +0.30 | true: +0.50, none: +0.30, high: +0.30 |
| 7 | mid | ground / passively waiting for mee… | ground / missing meeting decisions… | +0.00 | true: +0.50, none: +0.30, mid: +0.25 | true: +0.50, none: +0.30, mid: +0.25 |
| 8 | mid | ground / missing meeting decisions… | ground / getting immediate answers… | +0.00 | true: +0.50, none: +0.30, mid: +0.25 | true: +0.50, none: +0.30, mid: +0.25 |
| 9 | mid | ascend / deep focus making it hard… | ascend / no break between meetings… | +0.00 | true: +0.50, true: +0.35, none: +0.30 | true: +0.50, true: +0.35, none: +0.30 |
| 10 | mid | ascend / no break between meetings… | ascend / sugar crash disrupting en… | +0.32 | true: +0.50, true: +0.35, none: +0.30 | true: +0.50, true: +0.35, none: +0.30 |
| 11 | mid | ground / not proactively hydrating… | ground / missing meeting decisions… | +0.32 | true: +0.50, none: +0.30, mid: +0.25 | true: +0.50, none: +0.30, recency: +0.27 |
| 12 | mid | revitalize / nan | ascend / sugar crash disrupting en… | +0.18 | fatigued: +0.90, low: +0.60, canonical: +0.30 | true: +0.50, true: +0.35, none: +0.30 |
| 13 | mid | ground / break room being the fall… | ground / not making a dedicated tr… | +0.00 | true: +0.50, none: +0.30, high: +0.30 | true: +0.50, none: +0.30, high: +0.30 |
| 14 | late | close / nan | ascend / sugar crash disrupting en… | +2.00 | late: +2.00, early: +0.00, mid: +0.00 | true: +0.50, true: +0.35, none: +0.30 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| experiencing an energy dip around 3pm | 3d4604a2 | 2 |
| missing meeting decisions and needing to catch up secondhand | 17fcc220 | 1 |
| break room being the fallback source when drinks aren't near the meeting room | 396566ac | 1 |
| deep focus making it hard to step away | 85add58d | 1 |
| being at work during the day | 987434ee | 1 |
| staying energised and functional through the workday without a crash | b2492ebc | 1 |
| passively waiting for meetings to end due to disengagement | e0265775 | 1 |
| feeling foggy and unable to focus on what people are saying | e477553d | 1 |
| steady, uninterrupted focus during the workday | e5740b2f | 1 |
| not proactively hydrating before meetings begin | f43f4d23 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
