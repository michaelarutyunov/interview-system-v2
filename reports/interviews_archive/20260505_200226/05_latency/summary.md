# Pipeline Timing Analysis

- **Log file**: `interview_20260505_205910.log`
- **Pipeline runs**: 9
- **Avg pipeline**: 17.90s (range: 9.50s – 31.22s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 161.06s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 161.04s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 148.04s (runs in background during stages 4–4.6)
- **Bridge await time**: 75.91s (un-overlapped portion on critical path: SignalBridge=3.0s, EdgeBridge=72.9s)
- **Concurrency savings**: 72.12s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |      9 |      72.88 |     8097.9 |   45.3 |
| ExtractionStage                        |      9 |      42.28 |     4698.1 |   26.3 |
| SlotDiscoveryStage                     |      9 |      26.67 |     2962.8 |   16.6 |
| QuestionGenerationStage                |      9 |      13.79 |     1532.3 |    8.6 |
| LLMSignalBridgeStage                   |      9 |       3.03 |      337.1 |    1.9 |
| GraphUpdateStage                       |      9 |       1.05 |      116.3 |    0.6 |
| StrategySelectionStage                 |      9 |       0.61 |       67.9 |    0.4 |
| EdgeExtractionPrefetchStage            |      9 |       0.18 |       20.4 |    0.1 |
| ScoringPersistenceStage                |      9 |       0.16 |       17.9 |    0.1 |
| SRLPreprocessingStage                  |      9 |       0.10 |       11.5 |    0.1 |
| StateComputationStage                  |      9 |       0.07 |        8.2 |    0.0 |
| ContextLoadingStage                    |      9 |       0.07 |        8.1 |    0.0 |
| UtteranceSavingStage                   |      9 |       0.06 |        6.2 |    0.0 |
| ResponseSavingStage                    |      9 |       0.06 |        6.2 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.02 |        2.4 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.5 |    0.0 |
| TOTAL                                  |        |     161.04 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (161.04s) and wall-clock (161.06s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |     9 |    98.53 |   0.1476 |    4050 |    2470 |
| signal_scoring       | claude-haiku..   |     9 |    49.51 |   0.0479 |    2777 |     510 |
| extraction           | claude-sonne..   |     9 |    42.26 |   0.1197 |    2782 |     331 |
| question_generation  | claude-haiku..   |    20 |    34.76 |   0.0252 |    1017 |      49 |
| slot_scoring         | claude-haiku..   |     9 |    24.72 |   0.0284 |    1263 |     378 |
| TOTAL                |                  |    56 |   249.78 |   0.3689 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 101.74s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 148.04s — runs in parallel with pipeline stages; only the un-overlapped bridge await (75914.97s) is on the critical path
- **Concurrency savings**: 72.12s (49% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 249.78s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 72.9s (45.3wall)
2. **ExtractionStage**: 42.3s (26.3wall)
3. **SlotDiscoveryStage**: 26.7s (16.6wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.1476 (9 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0479 (9 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1197 (9 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0252 (20 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0284 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3689**

### Token Usage
- Input:  118,203 tokens
- Output: 34,178 tokens
- Total:  152,381 tokens
