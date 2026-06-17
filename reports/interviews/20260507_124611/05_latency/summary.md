# Pipeline Timing Analysis

- **Log file**: `interview_20260507_133951.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 23.96s (range: 9.95s – 49.66s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 335.42s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 335.40s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 287.46s (runs in background during stages 4–4.6)
- **Bridge await time**: 178.11s (un-overlapped portion on critical path: SignalBridge=0.0s, EdgeBridge=178.1s)
- **Concurrency savings**: 109.34s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     178.10 |    12721.7 |   53.1 |
| ExtractionStage                        |     14 |      97.76 |     6982.9 |   29.1 |
| SlotDiscoveryStage                     |     14 |      40.67 |     2905.0 |   12.1 |
| QuestionGenerationStage                |     14 |      15.99 |     1142.2 |    4.8 |
| GraphUpdateStage                       |     14 |       1.54 |      110.3 |    0.5 |
| StrategySelectionStage                 |     14 |       0.48 |       34.2 |    0.1 |
| ScoringPersistenceStage                |     14 |       0.21 |       14.9 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.17 |       11.9 |    0.0 |
| SRLPreprocessingStage                  |     14 |       0.15 |       10.6 |    0.0 |
| StateComputationStage                  |     14 |       0.08 |        5.6 |    0.0 |
| ResponseSavingStage                    |     14 |       0.08 |        5.4 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.07 |        4.8 |    0.0 |
| ContextLoadingStage                    |     14 |       0.06 |        4.4 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.03 |        2.1 |    0.0 |
| LLMSignalBridgeStage                   |     14 |       0.01 |        0.5 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.4 |    0.0 |
| TOTAL                                  |        |     335.40 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (335.40s) and wall-clock (335.42s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   218.31 |   0.3247 |    5798 |    3479 |
| signal_scoring       | claude-haiku..   |    14 |    69.15 |   0.0712 |    2747 |     467 |
| extraction           | claude-sonne..   |    14 |    66.60 |   0.1681 |    2563 |     288 |
| question_generation  | claude-haiku..   |    30 |    44.01 |   0.0411 |    1148 |      44 |
| slot_scoring         | claude-haiku..   |    14 |    38.84 |   0.0400 |    1192 |     333 |
| TOTAL                |                  |    86 |   436.90 |   0.6450 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 149.45s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 287.46s — runs in parallel with pipeline stages; only the un-overlapped bridge await (178110.40s) is on the critical path
- **Concurrency savings**: 109.34s (38% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 436.90s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

### Prompt Caching

| Module               | Cache Created |  Cache Read | Cache Hit % |
|----------------------|---------------|-------------|-------------|
| edge_extraction      |             0 |           0 |        0.0% |
| signal_scoring       |             0 |           0 |        0.0% |
| extraction           |         2,675 |           0 |        0.0% |
| question_generation  |             0 |           0 |        0.0% |
| slot_scoring         |             0 |           0 |        0.0% |

**Cache write cost**: 1.25× base input price per token written. **Cache read savings**: 0.10× base input price — 90% discount on cached prefix.

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 178.1s (53.1wall)
2. **ExtractionStage**: 97.8s (29.1wall)
3. **SlotDiscoveryStage**: 40.7s (12.1wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.3247 (14 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0712 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1681 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0411 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0400 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.6450**

### Token Usage
- Input:  206,644 tokens
- Output: 65,266 tokens
- Total:  271,910 tokens
