# Pipeline Timing Analysis

- **Log file**: `interview_20260429_123532.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      9 |     104.23 |    11580.7 |   67.3 |
| SlotDiscoveryStage                     |      9 |      24.93 |     2769.6 |   16.1 |
| LLMSignalBridgeStage                   |      9 |      13.08 |     1452.9 |    8.4 |
| QuestionGenerationStage                |      9 |      10.30 |     1144.5 |    6.7 |
| GraphUpdateStage                       |      9 |       1.10 |      122.5 |    0.7 |
| StrategySelectionStage                 |      9 |       0.51 |       56.1 |    0.3 |
| ContextLoadingStage                    |      9 |       0.18 |       19.7 |    0.1 |
| SRLPreprocessingStage                  |      9 |       0.14 |       15.8 |    0.1 |
| ScoringPersistenceStage                |      9 |       0.14 |       15.2 |    0.1 |
| StateComputationStage                  |      9 |       0.10 |       10.6 |    0.1 |
| UtteranceSavingStage                   |      9 |       0.09 |       10.2 |    0.1 |
| ResponseSavingStage                    |      9 |       0.07 |        8.2 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.03 |        3.1 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     154.88 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     9 |   104.21 |   0.1472 |    1208 |     848 |
| signal_scoring       | claude-haiku..   |     9 |    38.98 |   0.0437 |    2736 |     424 |
| question_generation  | claude-haiku..   |    20 |    33.12 |   0.0292 |    1220 |      48 |
| slot_scoring         | claude-haiku..   |     9 |    22.99 |   0.0269 |    1203 |     358 |
| TOTAL                |                  |    47 |   199.30 |   0.2470 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 160.32s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 38.98s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 199.30s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 104.2s (67.3sum)
2. **SlotDiscoveryStage**: 24.9s (16.1sum)
3. **LLMSignalBridgeStage**: 13.1s (8.4sum)

### LLM Cost Breakdown
- **extraction**: $0.1472 (9 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0437 (9 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0292 (20 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0269 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2470**

### Token Usage
- Input:  70,735 tokens
- Output: 15,632 tokens
- Total:  86,367 tokens
