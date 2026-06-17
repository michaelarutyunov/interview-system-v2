# Pipeline Timing Analysis

- **Log file**: `interview_20260505_103648.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 11.88s (range: 9.24s – 16.50s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 166.38s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 166.37s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 112.32s (runs in background during stages 4–4.6)
- **Bridge await time**: 27.09s (un-overlapped portion on critical path: SignalBridge=24.1s, EdgeBridge=2.9s)
- **Concurrency savings**: 85.23s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     14 |      71.97 |     5140.5 |   43.3 |
| SlotDiscoveryStage                     |     14 |      47.15 |     3368.2 |   28.3 |
| LLMSignalBridgeStage                   |     14 |      24.14 |     1724.6 |   14.5 |
| QuestionGenerationStage                |     14 |      15.79 |     1127.6 |    9.5 |
| EdgeExtractionBridgeStage              |     14 |       2.94 |      210.2 |    1.8 |
| StrategySelectionStage                 |     14 |       1.96 |      140.0 |    1.2 |
| GraphUpdateStage                       |     14 |       1.21 |       86.8 |    0.7 |
| ScoringPersistenceStage                |     14 |       0.31 |       22.4 |    0.2 |
| StateComputationStage                  |     14 |       0.25 |       17.6 |    0.1 |
| ContextLoadingStage                    |     14 |       0.15 |       10.4 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.14 |       10.3 |    0.1 |
| UtteranceSavingStage                   |     14 |       0.12 |        8.4 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.11 |        7.9 |    0.1 |
| ResponseSavingStage                    |     14 |       0.09 |        6.4 |    0.1 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.5 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     166.37 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (166.37s) and wall-clock (166.38s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| signal_scoring       | claude-haiku..   |    14 |    75.27 |   0.0729 |    2755 |     490 |
| extraction           | claude-sonne..   |    14 |    71.95 |   0.1850 |    2795 |     322 |
| question_generation  | claude-haiku..   |    30 |    43.14 |   0.0373 |    1028 |      43 |
| slot_scoring         | claude-haiku..   |    14 |    43.02 |   0.0445 |    1260 |     384 |
| edge_extraction      | claude-haiku..   |    14 |    37.05 |   0.0424 |    1924 |     221 |
| TOTAL                |                  |    86 |   270.43 |   0.3821 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 158.11s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 112.32s — runs in parallel with pipeline stages; only the un-overlapped bridge await (27087.71s) is on the critical path
- **Concurrency savings**: 85.23s (76% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 270.43s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 72.0s (43.3wall)
2. **SlotDiscoveryStage**: 47.2s (28.3wall)
3. **LLMSignalBridgeStage**: 24.1s (14.5wall)

### LLM Cost Breakdown
- **signal_scoring**: $0.0729 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1850 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0373 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0445 (14 calls) `[claude-haiku-4-5]`
- **edge_extraction**: $0.0424 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3821**

### Token Usage
- Input:  153,115 tokens
- Output: 21,140 tokens
- Total:  174,255 tokens
