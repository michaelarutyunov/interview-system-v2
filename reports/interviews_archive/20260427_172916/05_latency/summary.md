# Pipeline Timing Analysis

- **Log file**: `interview_20260427_182436.log`
- **Pipeline runs**: 0

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |      % |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     13 |     163.20 |    12553.6 |   69.2 |
| SlotDiscoveryStage                     |     13 |      41.16 |     3166.2 |   17.5 |
| QuestionGenerationStage                |     13 |      16.35 |     1257.4 |    6.9 |
| LLMSignalBridgeStage                   |     13 |      12.11 |      931.9 |    5.1 |
| GraphUpdateStage                       |     13 |       1.83 |      140.9 |    0.8 |
| StrategySelectionStage                 |     13 |       0.36 |       27.7 |    0.2 |
| SRLPreprocessingStage                  |     13 |       0.29 |       22.1 |    0.1 |
| ScoringPersistenceStage                |     13 |       0.20 |       15.7 |    0.1 |
| ResponseSavingStage                    |     13 |       0.09 |        7.2 |    0.0 |
| ContextLoadingStage                    |     13 |       0.09 |        7.1 |    0.0 |
| StateComputationStage                  |     13 |       0.08 |        6.1 |    0.0 |
| UtteranceSavingStage                   |     13 |       0.07 |        5.4 |    0.0 |
| LLMPrefetchStage                       |     13 |       0.02 |        1.6 |    0.0 |
| ContinuationStage                      |     13 |       0.00 |        0.2 |    0.0 |
| TOTAL                                  |        |     235.86 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    13 |   163.18 |   0.2333 |    1293 |     938 |
| signal_scoring       | claude-haiku..   |    13 |    54.69 |   0.0574 |    2588 |     365 |
| question_generation  | claude-haiku..   |    28 |    42.58 |   0.0412 |    1248 |      45 |
| slot_scoring         | claude-haiku..   |    13 |    38.19 |   0.0432 |    1291 |     406 |
| TOTAL                |                  |    67 |   298.65 |   0.3751 |         |         |

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 163.2s (69.2%)
2. **SlotDiscoveryStage**: 41.2s (17.5%)
3. **QuestionGenerationStage**: 16.3s (6.9%)

### LLM Cost Breakdown
- **extraction**: $0.2333 (13 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0574 (13 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0412 (28 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0432 (13 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3751**

### Token Usage
- Input:  102,189 tokens
- Output: 23,476 tokens
- Total:  125,665 tokens
