# Pipeline Timing Analysis

- **Log file**: `interview_20260430_191424.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      6 |      38.87 |     6477.8 |   59.3 |
| SlotDiscoveryStage                     |      6 |      12.90 |     2150.1 |   19.7 |
| LLMSignalBridgeStage                   |      6 |       7.65 |     1275.1 |   11.7 |
| QuestionGenerationStage                |      6 |       4.54 |      756.8 |    6.9 |
| GraphUpdateStage                       |      6 |       0.92 |      153.9 |    1.4 |
| StrategySelectionStage                 |      6 |       0.28 |       47.3 |    0.4 |
| ScoringPersistenceStage                |      6 |       0.11 |       18.0 |    0.2 |
| StateComputationStage                  |      6 |       0.05 |        8.7 |    0.1 |
| ContextLoadingStage                    |      6 |       0.05 |        8.6 |    0.1 |
| SRLPreprocessingStage                  |      6 |       0.05 |        7.8 |    0.1 |
| ResponseSavingStage                    |      6 |       0.03 |        5.5 |    0.1 |
| UtteranceSavingStage                   |      6 |       0.03 |        4.6 |    0.0 |
| LLMPrefetchStage                       |      6 |       0.02 |        3.6 |    0.0 |
| ContinuationStage                      |      6 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |      65.51 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     6 |    38.86 |   0.0634 |     874 |     530 |
| signal_scoring       | claude-haiku..   |     6 |    21.44 |   0.0266 |    2656 |     354 |
| question_generation  | claude-haiku..   |    13 |    14.74 |   0.0125 |     825 |      27 |
| slot_scoring         | claude-haiku..   |     6 |    11.84 |   0.0142 |    1089 |     254 |
| TOTAL                |                  |    31 |    86.87 |   0.1166 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 65.43s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 21.44s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 86.87s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 38.9s (59.3sum)
2. **SlotDiscoveryStage**: 12.9s (19.7sum)
3. **LLMSignalBridgeStage**: 7.7s (11.7sum)

### LLM Cost Breakdown
- **extraction**: $0.0634 (6 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0266 (6 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0125 (13 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0142 (6 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.1166**

### Token Usage
- Input:  38,440 tokens
- Output: 7,178 tokens
- Total:  45,618 tokens
