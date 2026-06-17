# Pipeline Timing Analysis

- **Log file**: `interview_20260505_134645.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 31.24s (range: 21.46s – 39.70s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 437.39s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 437.37s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 418.04s (runs in background during stages 4–4.6)
- **Bridge await time**: 286.92s (un-overlapped portion on critical path: SignalBridge=0.1s, EdgeBridge=286.8s)
- **Concurrency savings**: 131.12s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     286.82 |    20486.8 |   65.6 |
| ExtractionStage                        |     14 |      77.91 |     5565.2 |   17.8 |
| SlotDiscoveryStage                     |     14 |      50.64 |     3617.4 |   11.6 |
| QuestionGenerationStage                |     14 |      18.20 |     1300.0 |    4.2 |
| GraphUpdateStage                       |     14 |       1.66 |      118.6 |    0.4 |
| StrategySelectionStage                 |     14 |       0.99 |       70.4 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.24 |       17.3 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.15 |       11.0 |    0.0 |
| StateComputationStage                  |     14 |       0.14 |       10.0 |    0.0 |
| ResponseSavingStage                    |     14 |       0.13 |        9.4 |    0.0 |
| SRLPreprocessingStage                  |     14 |       0.13 |        9.1 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.12 |        8.4 |    0.0 |
| ContextLoadingStage                    |     14 |       0.11 |        7.9 |    0.0 |
| LLMSignalBridgeStage                   |     14 |       0.11 |        7.7 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.5 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.2 |    0.0 |
| TOTAL                                  |        |     437.37 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (437.37s) and wall-clock (437.39s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   337.31 |   0.3532 |    6045 |    3837 |
| signal_scoring       | claude-haiku..   |    14 |    80.73 |   0.0788 |    2790 |     568 |
| extraction           | claude-sonne..   |    14 |    77.89 |   0.1996 |    2890 |     372 |
| slot_scoring         | claude-haiku..   |    14 |    47.18 |   0.0497 |    1350 |     440 |
| question_generation  | claude-haiku..   |    30 |    44.44 |   0.0392 |    1068 |      48 |
| TOTAL                |                  |    86 |   587.55 |   0.7206 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 169.51s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 418.04s — runs in parallel with pipeline stages; only the un-overlapped bridge await (286923.94s) is on the critical path
- **Concurrency savings**: 131.12s (31% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 587.55s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 286.8s (65.6wall)
2. **ExtractionStage**: 77.9s (17.8wall)
3. **SlotDiscoveryStage**: 50.6s (11.6wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.3532 (14 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0788 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1996 (14 calls) `[claude-sonnet-4-6]`
- **slot_scoring**: $0.0497 (14 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0392 (30 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.7206**

### Token Usage
- Input:  215,107 tokens
- Output: 74,482 tokens
- Total:  289,589 tokens
