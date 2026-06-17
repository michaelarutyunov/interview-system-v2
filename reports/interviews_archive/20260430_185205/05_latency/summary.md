# Pipeline Timing Analysis

- **Log file**: `interview_20260430_194733.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     10 |     143.30 |    14330.1 |   65.0 |
| SlotDiscoveryStage                     |     10 |      38.18 |     3818.4 |   17.3 |
| LLMSignalBridgeStage                   |     10 |      24.30 |     2430.4 |   11.0 |
| QuestionGenerationStage                |     10 |      11.32 |     1132.0 |    5.1 |
| GraphUpdateStage                       |     10 |       1.92 |      192.4 |    0.9 |
| StrategySelectionStage                 |     10 |       0.73 |       73.4 |    0.3 |
| SRLPreprocessingStage                  |     10 |       0.19 |       19.0 |    0.1 |
| ScoringPersistenceStage                |     10 |       0.17 |       17.2 |    0.1 |
| StateComputationStage                  |     10 |       0.09 |        8.5 |    0.0 |
| ContextLoadingStage                    |     10 |       0.07 |        7.3 |    0.0 |
| ResponseSavingStage                    |     10 |       0.05 |        5.1 |    0.0 |
| UtteranceSavingStage                   |     10 |       0.05 |        4.9 |    0.0 |
| LLMPrefetchStage                       |     10 |       0.02 |        2.5 |    0.0 |
| ContinuationStage                      |     10 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     220.42 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    10 |   143.29 |   0.2518 |    1839 |    1310 |
| signal_scoring       | claude-haiku..   |    10 |    64.32 |   0.0627 |    2880 |     677 |
| question_generation  | claude-haiku..   |    22 |    45.61 |   0.0368 |    1168 |     101 |
| slot_scoring         | claude-haiku..   |    10 |    35.24 |   0.0383 |    1377 |     490 |
| TOTAL                |                  |    52 |   288.46 |   0.3895 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 224.14s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 64.32s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 288.46s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 143.3s (65.0sum)
2. **SlotDiscoveryStage**: 38.2s (17.3sum)
3. **LLMSignalBridgeStage**: 24.3s (11.0sum)

### LLM Cost Breakdown
- **extraction**: $0.2518 (10 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0627 (10 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0368 (22 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0383 (10 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3895**

### Token Usage
- Input:  86,659 tokens
- Output: 26,996 tokens
- Total:  113,655 tokens
