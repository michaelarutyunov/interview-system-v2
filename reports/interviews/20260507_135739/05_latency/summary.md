# Pipeline Timing Analysis

- **Log file**: `interview_20260507_145212.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 20.09s (range: 10.35s – 30.48s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 281.27s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 281.25s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 263.07s (runs in background during stages 4–4.6)
- **Bridge await time**: 136.71s (un-overlapped portion on critical path: SignalBridge=0.0s, EdgeBridge=136.7s)
- **Concurrency savings**: 126.36s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     136.70 |     9764.6 |   48.6 |
| ExtractionStage                        |     14 |      73.54 |     5252.8 |   26.1 |
| SlotDiscoveryStage                     |     14 |      47.48 |     3391.1 |   16.9 |
| QuestionGenerationStage                |     14 |      20.45 |     1460.4 |    7.3 |
| GraphUpdateStage                       |     14 |       1.78 |      127.4 |    0.6 |
| StrategySelectionStage                 |     14 |       0.47 |       33.5 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.18 |       13.1 |    0.1 |
| LLMPrefetchStage                       |     14 |       0.16 |       11.1 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.15 |       10.9 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.09 |        6.4 |    0.0 |
| ResponseSavingStage                    |     14 |       0.06 |        4.5 |    0.0 |
| ContextLoadingStage                    |     14 |       0.06 |        4.5 |    0.0 |
| StateComputationStage                  |     14 |       0.06 |        4.3 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.06 |        3.9 |    0.0 |
| LLMSignalBridgeStage                   |     14 |       0.01 |        0.5 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     281.25 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (281.25s) and wall-clock (281.27s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   183.90 |   0.2916 |    6007 |    2964 |
| signal_scoring       | claude-haiku..   |    14 |    79.16 |   0.0778 |    2785 |     554 |
| extraction           | claude-sonne..   |    14 |    73.51 |   0.1974 |    2952 |     349 |
| question_generation  | claude-haiku..   |    30 |    48.05 |   0.0436 |    1168 |      57 |
| slot_scoring         | claude-haiku..   |    14 |    45.19 |   0.0473 |    1305 |     415 |
| TOTAL                |                  |    86 |   429.81 |   0.6577 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 166.75s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 263.07s — runs in parallel with pipeline stages; only the un-overlapped bridge await (136711.75s) is on the critical path
- **Concurrency savings**: 126.36s (48% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 429.81s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 136.7s (48.6wall)
2. **ExtractionStage**: 73.5s (26.1wall)
3. **SlotDiscoveryStage**: 47.5s (16.9wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.2916 (14 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0778 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1974 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0436 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0473 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.6577**

### Token Usage
- Input:  217,724 tokens
- Output: 61,673 tokens
- Total:  279,397 tokens
