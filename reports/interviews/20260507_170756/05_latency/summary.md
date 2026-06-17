# Pipeline Timing Analysis

- **Log file**: `interview_20260507_180014.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 29.55s (range: 16.04s – 68.85s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 413.76s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 413.74s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 331.88s (runs in background during stages 4–4.6)
- **Bridge await time**: 275.73s (un-overlapped portion on critical path: SignalBridge=0.0s, EdgeBridge=275.7s)
- **Concurrency savings**: 56.15s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     275.72 |    19694.5 |   66.6 |
| ExtractionStage                        |     14 |      73.05 |     5217.5 |   17.7 |
| SlotDiscoveryStage                     |     14 |      46.63 |     3330.4 |   11.3 |
| QuestionGenerationStage                |     14 |      15.53 |     1109.0 |    3.8 |
| GraphUpdateStage                       |     14 |       1.58 |      113.0 |    0.4 |
| StrategySelectionStage                 |     14 |       0.52 |       37.3 |    0.1 |
| ScoringPersistenceStage                |     14 |       0.16 |       11.7 |    0.0 |
| SRLPreprocessingStage                  |     14 |       0.15 |       10.8 |    0.0 |
| EdgeExtractionPrefetchStage            |     14 |       0.09 |        6.2 |    0.0 |
| ResponseSavingStage                    |     14 |       0.08 |        5.8 |    0.0 |
| StateComputationStage                  |     14 |       0.08 |        5.4 |    0.0 |
| ContextLoadingStage                    |     14 |       0.06 |        4.6 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.06 |        4.2 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.7 |    0.0 |
| LLMSignalBridgeStage                   |     14 |       0.01 |        0.5 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.2 |    0.0 |
| TOTAL                                  |        |     413.74 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (413.74s) and wall-clock (413.76s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   259.70 |   0.3753 |    6151 |    4132 |
| extraction           | claude-sonne..   |    14 |    73.02 |   0.1975 |    2916 |     357 |
| signal_scoring       | claude-haiku..   |    14 |    72.19 |   0.0780 |    3087 |     496 |
| question_generation  | claude-haiku..   |    30 |    45.17 |   0.0403 |    1124 |      44 |
| slot_scoring         | claude-haiku..   |    14 |    44.38 |   0.0478 |    1314 |     420 |
| TOTAL                |                  |    86 |   494.46 |   0.7388 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 162.58s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 331.88s — runs in parallel with pipeline stages; only the un-overlapped bridge await (275730.42s) is on the critical path
- **Concurrency savings**: 56.15s (17% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 494.46s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 275.7s (66.6wall)
2. **ExtractionStage**: 73.0s (17.7wall)
3. **SlotDiscoveryStage**: 46.6s (11.3wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.3753 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1975 (14 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0780 (14 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0403 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0478 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.7388**

### Token Usage
- Input:  222,281 tokens
- Output: 76,981 tokens
- Total:  299,262 tokens
