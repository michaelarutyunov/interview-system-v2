# Pipeline Timing Analysis

- **Log file**: `interview_20260502_205500.log`
- **Pipeline runs**: 5
- **Avg pipeline**: 17.82s (range: 14.56s – 26.49s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 89.12s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 89.12s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 36.04s (runs in background during stages 4–4.6)
- **Bridge await time**: 9.75s (un-overlapped portion on critical path: SignalBridge=7.9s, EdgeBridge=1.8s)
- **Concurrency savings**: 26.29s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      5 |      59.99 |    11998.0 |   67.3 |
| SlotDiscoveryStage                     |      5 |      13.27 |     2654.3 |   14.9 |
| LLMSignalBridgeStage                   |      5 |       7.92 |     1584.0 |    8.9 |
| QuestionGenerationStage                |      5 |       4.47 |      894.0 |    5.0 |
| EdgeExtractionBridgeStage              |      5 |       1.83 |      365.6 |    2.1 |
| GraphUpdateStage                       |      5 |       1.10 |      220.3 |    1.2 |
| StrategySelectionStage                 |      5 |       0.23 |       45.6 |    0.3 |
| ScoringPersistenceStage                |      5 |       0.09 |       17.6 |    0.1 |
| SRLPreprocessingStage                  |      5 |       0.05 |       10.9 |    0.1 |
| ContextLoadingStage                    |      5 |       0.04 |        7.9 |    0.0 |
| StateComputationStage                  |      5 |       0.04 |        7.6 |    0.0 |
| ResponseSavingStage                    |      5 |       0.03 |        5.7 |    0.0 |
| UtteranceSavingStage                   |      5 |       0.03 |        5.0 |    0.0 |
| LLMPrefetchStage                       |      5 |       0.02 |        3.7 |    0.0 |
| EdgeExtractionPrefetchStage            |      5 |       0.02 |        3.2 |    0.0 |
| ContinuationStage                      |      5 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |      89.12 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (89.12s) and wall-clock (89.12s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     5 |    59.98 |   0.0821 |    1112 |     872 |
| signal_scoring       | claude-haiku..   |     5 |    24.11 |   0.0252 |    2749 |     459 |
| question_generation  | claude-haiku..   |    11 |    14.27 |   0.0136 |    1005 |      45 |
| slot_scoring         | claude-haiku..   |     5 |    12.32 |   0.0144 |    1191 |     338 |
| edge_extraction      | claude-haiku..   |     5 |    11.93 |   0.0145 |    1873 |     206 |
| TOTAL                |                  |    31 |   122.62 |   0.1498 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 86.58s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 36.04s — runs in parallel with pipeline stages; only the un-overlapped bridge await (9748.23s) is on the critical path
- **Concurrency savings**: 26.29s (73% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 122.62s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 60.0s (67.3wall)
2. **SlotDiscoveryStage**: 13.3s (14.9wall)
3. **LLMSignalBridgeStage**: 7.9s (8.9wall)

### LLM Cost Breakdown
- **extraction**: $0.0821 (5 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0252 (5 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0136 (11 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0144 (5 calls) `[claude-haiku-4-5]`
- **edge_extraction**: $0.0145 (5 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.1498**

### Token Usage
- Input:  45,687 tokens
- Output: 9,872 tokens
- Total:  55,559 tokens
