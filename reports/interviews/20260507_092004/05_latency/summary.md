# Pipeline Timing Analysis

- **Log file**: `interview_20260507_101533.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 15.84s (range: 7.70s – 32.28s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 221.70s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 221.69s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 198.93s (runs in background during stages 4–4.6)
- **Bridge await time**: 84.55s (un-overlapped portion on critical path: SignalBridge=1.1s, EdgeBridge=83.5s)
- **Concurrency savings**: 114.38s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |      83.49 |     5963.6 |   37.7 |
| ExtractionStage                        |     14 |      72.59 |     5184.7 |   32.7 |
| SlotDiscoveryStage                     |     14 |      43.81 |     3128.9 |   19.8 |
| QuestionGenerationStage                |     14 |      17.93 |     1280.9 |    8.1 |
| GraphUpdateStage                       |     14 |       1.53 |      109.0 |    0.7 |
| LLMSignalBridgeStage                   |     14 |       1.06 |       75.8 |    0.5 |
| StrategySelectionStage                 |     14 |       0.54 |       38.6 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.18 |       12.7 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.15 |       11.0 |    0.1 |
| UtteranceSavingStage                   |     14 |       0.09 |        6.6 |    0.0 |
| EdgeExtractionPrefetchStage            |     14 |       0.08 |        5.9 |    0.0 |
| ResponseSavingStage                    |     14 |       0.08 |        5.9 |    0.0 |
| ContextLoadingStage                    |     14 |       0.07 |        5.2 |    0.0 |
| StateComputationStage                  |     14 |       0.06 |        4.2 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.5 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     221.69 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (221.69s) and wall-clock (221.70s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   127.12 |   0.1989 |    4093 |    2022 |
| extraction           | claude-sonne..   |    14 |    72.57 |   0.1870 |    2870 |     316 |
| signal_scoring       | claude-haiku..   |    14 |    71.81 |   0.0738 |    2762 |     502 |
| question_generation  | claude-haiku..   |    30 |    45.14 |   0.0409 |    1136 |      45 |
| slot_scoring         | claude-haiku..   |    14 |    41.82 |   0.0447 |    1290 |     380 |
| TOTAL                |                  |    86 |   358.45 |   0.5452 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 159.52s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 198.93s — runs in parallel with pipeline stages; only the un-overlapped bridge await (84551.34s) is on the critical path
- **Concurrency savings**: 114.38s (57% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 358.45s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 83.5s (37.7wall)
2. **ExtractionStage**: 72.6s (32.7wall)
3. **SlotDiscoveryStage**: 43.8s (19.8wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.1989 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1870 (14 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0738 (14 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0409 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0447 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.5452**

### Token Usage
- Input:  188,311 tokens
- Output: 46,447 tokens
- Total:  234,758 tokens
