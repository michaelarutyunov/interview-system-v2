# Pipeline Timing Analysis

- **Log file**: `interview_20260428_212341.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      9 |      83.38 |     9264.4 |   59.3 |
| SlotDiscoveryStage                     |      9 |      25.49 |     2832.7 |   18.1 |
| LLMSignalBridgeStage                   |      9 |      18.20 |     2022.5 |   12.9 |
| QuestionGenerationStage                |      9 |      11.18 |     1242.7 |    8.0 |
| GraphUpdateStage                       |      9 |       1.29 |      142.8 |    0.9 |
| StrategySelectionStage                 |      9 |       0.50 |       55.4 |    0.4 |
| ScoringPersistenceStage                |      9 |       0.15 |       16.5 |    0.1 |
| SRLPreprocessingStage                  |      9 |       0.10 |       11.1 |    0.1 |
| StateComputationStage                  |      9 |       0.07 |        8.0 |    0.1 |
| ContextLoadingStage                    |      9 |       0.07 |        7.8 |    0.1 |
| UtteranceSavingStage                   |      9 |       0.06 |        7.1 |    0.0 |
| ResponseSavingStage                    |      9 |       0.05 |        5.2 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.02 |        2.2 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     140.57 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     9 |    83.37 |   0.1424 |    1232 |     808 |
| signal_scoring       | claude-haiku..   |     9 |    44.92 |   0.0472 |    2749 |     500 |
| question_generation  | claude-haiku..   |    20 |    28.55 |   0.0292 |    1219 |      48 |
| slot_scoring         | claude-haiku..   |     9 |    23.64 |   0.0274 |    1227 |     364 |
| TOTAL                |                  |    47 |   180.47 |   0.2462 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 135.55s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 44.92s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 180.47s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 83.4s (59.3sum)
2. **SlotDiscoveryStage**: 25.5s (18.1sum)
3. **LLMSignalBridgeStage**: 18.2s (12.9sum)

### LLM Cost Breakdown
- **extraction**: $0.1424 (9 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0472 (9 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0292 (20 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0274 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2462**

### Token Usage
- Input:  71,252 tokens
- Output: 16,008 tokens
- Total:  87,260 tokens
