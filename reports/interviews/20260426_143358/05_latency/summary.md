# Pipeline Timing Analysis

- **Log file**: `interview_20260426_153028.log`
- **Pipeline runs**: 0

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |      % |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      9 |     119.63 |    13292.1 |   67.8 |
| SlotDiscoveryStage                     |      9 |      39.66 |     4406.5 |   22.5 |
| QuestionGenerationStage                |      9 |       9.73 |     1081.1 |    5.5 |
| LLMSignalBridgeStage                   |      9 |       5.57 |      618.5 |    3.2 |
| GraphUpdateStage                       |      9 |       1.31 |      145.5 |    0.7 |
| StrategySelectionStage                 |      9 |       0.17 |       18.7 |    0.1 |
| ScoringPersistenceStage                |      9 |       0.11 |       12.1 |    0.1 |
| SRLPreprocessingStage                  |      9 |       0.10 |       11.2 |    0.1 |
| ResponseSavingStage                    |      9 |       0.06 |        6.7 |    0.0 |
| ContextLoadingStage                    |      9 |       0.04 |        4.0 |    0.0 |
| UtteranceSavingStage                   |      9 |       0.03 |        3.9 |    0.0 |
| StateComputationStage                  |      9 |       0.03 |        3.4 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.02 |        2.0 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.2 |    0.0 |
| TOTAL                                  |        |     176.45 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     9 |   119.62 |   0.1671 |    1216 |     995 |
| signal_scoring       | claude-haiku..   |     9 |    40.19 |   0.0431 |    2618 |     434 |
| slot_scoring         | claude-haiku..   |     9 |    38.07 |   0.0345 |    1397 |     488 |
| question_generation  | claude-haiku..   |    20 |    27.57 |   0.0294 |    1229 |      48 |
| TOTAL                |                  |    47 |   225.44 |   0.2742 |         |         |

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 119.6s (67.8%)
2. **SlotDiscoveryStage**: 39.7s (22.5%)
3. **QuestionGenerationStage**: 9.7s (5.5%)

### LLM Cost Breakdown
- **extraction**: $0.1671 (9 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0431 (9 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0345 (9 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0294 (20 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2742**

### Token Usage
- Input:  71,646 tokens
- Output: 18,218 tokens
- Total:  89,864 tokens
