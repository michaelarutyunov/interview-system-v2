# Pipeline Timing Analysis

- **Log file**: `interview_20260506_225323.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 20.59s (range: 6.51s – 69.63s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 288.28s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 288.26s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 235.18s (runs in background during stages 4–4.6)
- **Bridge await time**: 157.92s (un-overlapped portion on critical path: SignalBridge=4.2s, EdgeBridge=153.7s)
- **Concurrency savings**: 77.27s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     153.68 |    10977.1 |   53.3 |
| ExtractionStage                        |     14 |      66.46 |     4747.4 |   23.1 |
| SlotDiscoveryStage                     |     14 |      41.15 |     2939.0 |   14.3 |
| QuestionGenerationStage                |     14 |      19.87 |     1419.3 |    6.9 |
| LLMSignalBridgeStage                   |     14 |       4.24 |      302.7 |    1.5 |
| GraphUpdateStage                       |     14 |       1.44 |      102.8 |    0.5 |
| StrategySelectionStage                 |     14 |       0.61 |       43.4 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.20 |       14.2 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.15 |       10.6 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.12 |        8.9 |    0.0 |
| StateComputationStage                  |     14 |       0.09 |        6.4 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.09 |        6.2 |    0.0 |
| ResponseSavingStage                    |     14 |       0.08 |        5.7 |    0.0 |
| ContextLoadingStage                    |     14 |       0.06 |        4.6 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.6 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     288.26 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (288.26s) and wall-clock (288.28s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   163.15 |   0.2464 |    4111 |    2698 |
| signal_scoring       | claude-haiku..   |    14 |    72.03 |   0.0738 |    2757 |     503 |
| extraction           | claude-sonne..   |    14 |    66.43 |   0.1858 |    2857 |     313 |
| question_generation  | claude-haiku..   |    30 |    47.81 |   0.0384 |    1070 |      42 |
| slot_scoring         | claude-haiku..   |    13 |    39.16 |   0.0439 |    1309 |     414 |
| TOTAL                |                  |    85 |   388.59 |   0.5884 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 153.40s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 235.18s — runs in parallel with pipeline stages; only the un-overlapped bridge await (157915.99s) is on the critical path
- **Concurrency savings**: 77.27s (33% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 388.59s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 153.7s (53.3wall)
2. **ExtractionStage**: 66.5s (23.1wall)
3. **SlotDiscoveryStage**: 41.1s (14.3wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.2464 (14 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0738 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1858 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0384 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0439 (13 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.5884**

### Token Usage
- Input:  185,260 tokens
- Output: 55,856 tokens
- Total:  241,116 tokens
