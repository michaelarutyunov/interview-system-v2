# Pipeline Timing Analysis

- **Log file**: `interview_20260505_162501.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 57.71s (range: 18.37s – 71.53s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 807.89s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 807.82s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 168.04s (runs in background during stages 4–4.6)
- **Bridge await time**: 642.86s (un-overlapped portion on critical path: SignalBridge=0.6s, EdgeBridge=642.3s)
- **Concurrency savings**: 0.00s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     642.29 |    45877.8 |   79.5 |
| ExtractionStage                        |     14 |      72.49 |     5177.6 |    9.0 |
| SlotDiscoveryStage                     |     14 |      54.89 |     3921.1 |    6.8 |
| QuestionGenerationStage                |     14 |      18.93 |     1352.0 |    2.3 |
| GraphUpdateStage                       |     14 |       8.27 |      591.1 |    1.0 |
| SRLPreprocessingStage                  |     14 |       4.73 |      337.6 |    0.6 |
| StrategySelectionStage                 |     14 |       2.62 |      187.4 |    0.3 |
| ScoringPersistenceStage                |     14 |       0.87 |       62.4 |    0.1 |
| StateComputationStage                  |     14 |       0.71 |       50.4 |    0.1 |
| LLMSignalBridgeStage                   |     14 |       0.57 |       40.6 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.53 |       37.6 |    0.1 |
| ResponseSavingStage                    |     14 |       0.33 |       23.8 |    0.0 |
| ContextLoadingStage                    |     14 |       0.28 |       20.0 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.15 |       11.1 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.12 |        8.8 |    0.0 |
| ContinuationStage                      |     14 |       0.03 |        2.1 |    0.0 |
| TOTAL                                  |        |     807.82 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (807.82s) and wall-clock (807.89s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| signal_scoring       | claude-haiku..   |    14 |    85.05 |   0.0820 |    2803 |     610 |
| edge_extraction      | claude-haiku..   |     4 |    83.00 |   0.0814 |    4454 |    3177 |
| extraction           | claude-sonne..   |    14 |    72.27 |   0.2078 |    2984 |     393 |
| question_generation  | claude-haiku..   |    30 |    48.98 |   0.0386 |    1040 |      49 |
| slot_scoring         | claude-haiku..   |    14 |    45.93 |   0.0517 |    1403 |     458 |
| TOTAL                |                  |    76 |   335.23 |   0.4614 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 167.19s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 168.04s — runs in parallel with pipeline stages; only the un-overlapped bridge await (642857.05s) is on the critical path
- **Concurrency savings**: 0.00s (0% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 335.23s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 642.3s (79.5wall)
2. **ExtractionStage**: 72.5s (9.0wall)
3. **SlotDiscoveryStage**: 54.9s (6.8wall)

### LLM Cost Breakdown
- **signal_scoring**: $0.0820 (14 calls) `[claude-haiku-4-5]`
- **edge_extraction**: $0.0814 (4 calls) `[claude-haiku-4-5]`
- **extraction**: $0.2078 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0386 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0517 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.4614**

### Token Usage
- Input:  149,651 tokens
- Output: 34,632 tokens
- Total:  184,283 tokens
