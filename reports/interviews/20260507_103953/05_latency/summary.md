# Pipeline Timing Analysis

- **Log file**: `interview_20260507_113127.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 33.06s (range: 7.99s – 71.75s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 462.77s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 462.76s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 290.79s (runs in background during stages 4–4.6)
- **Bridge await time**: 328.76s (un-overlapped portion on critical path: SignalBridge=0.0s, EdgeBridge=328.8s)
- **Concurrency savings**: 0.00s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     328.75 |    23482.3 |   71.0 |
| ExtractionStage                        |     14 |      70.73 |     5052.1 |   15.3 |
| SlotDiscoveryStage                     |     14 |      42.76 |     3053.9 |    9.2 |
| QuestionGenerationStage                |     14 |      17.67 |     1262.0 |    3.8 |
| GraphUpdateStage                       |     14 |       1.60 |      114.3 |    0.3 |
| StrategySelectionStage                 |     14 |       0.50 |       35.9 |    0.1 |
| ScoringPersistenceStage                |     14 |       0.17 |       12.1 |    0.0 |
| SRLPreprocessingStage                  |     14 |       0.14 |       10.2 |    0.0 |
| EdgeExtractionPrefetchStage            |     14 |       0.09 |        6.4 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.08 |        6.0 |    0.0 |
| ResponseSavingStage                    |     14 |       0.08 |        5.7 |    0.0 |
| StateComputationStage                  |     14 |       0.08 |        5.6 |    0.0 |
| ContextLoadingStage                    |     14 |       0.07 |        5.1 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.6 |    0.0 |
| LLMSignalBridgeStage                   |     14 |       0.01 |        0.6 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     462.76 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (462.76s) and wall-clock (462.77s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    13 |   216.57 |   0.3240 |    5959 |    3793 |
| signal_scoring       | claude-haiku..   |    14 |    74.21 |   0.0756 |    2763 |     527 |
| extraction           | claude-sonne..   |    14 |    70.71 |   0.1912 |    2872 |     336 |
| question_generation  | claude-haiku..   |    30 |    43.09 |   0.0401 |    1121 |      43 |
| slot_scoring         | claude-haiku..   |    14 |    40.56 |   0.0454 |    1287 |     391 |
| TOTAL                |                  |    85 |   445.14 |   0.6763 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 154.35s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 290.79s — runs in parallel with pipeline stages; only the un-overlapped bridge await (328760.73s) is on the critical path
- **Concurrency savings**: 0.00s (0% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 445.14s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 328.8s (71.0wall)
2. **ExtractionStage**: 70.7s (15.3wall)
3. **SlotDiscoveryStage**: 42.8s (9.2wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.3240 (13 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0756 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1912 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0401 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0454 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.6763**

### Token Usage
- Input:  208,011 tokens
- Output: 68,153 tokens
- Total:  276,164 tokens
