# Pipeline Timing Analysis

- **Log file**: `interview_20260501_160017.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     11 |     102.60 |     9327.4 |   62.7 |
| SlotDiscoveryStage                     |     11 |      28.41 |     2582.9 |   17.4 |
| LLMSignalBridgeStage                   |     11 |      18.27 |     1660.6 |   11.2 |
| QuestionGenerationStage                |     11 |      11.77 |     1069.7 |    7.2 |
| GraphUpdateStage                       |     11 |       1.60 |      145.3 |    1.0 |
| StrategySelectionStage                 |     11 |       0.38 |       34.5 |    0.2 |
| ScoringPersistenceStage                |     11 |       0.17 |       15.7 |    0.1 |
| SRLPreprocessingStage                  |     11 |       0.11 |       10.1 |    0.1 |
| StateComputationStage                  |     11 |       0.09 |        8.2 |    0.1 |
| ContextLoadingStage                    |     11 |       0.09 |        8.1 |    0.1 |
| ResponseSavingStage                    |     11 |       0.07 |        6.4 |    0.0 |
| UtteranceSavingStage                   |     11 |       0.05 |        4.7 |    0.0 |
| LLMPrefetchStage                       |     11 |       0.03 |        2.5 |    0.0 |
| ContinuationStage                      |     11 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     163.64 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    11 |   102.59 |   0.1720 |    1200 |     802 |
| signal_scoring       | claude-haiku..   |    11 |    48.20 |   0.0544 |    2733 |     443 |
| question_generation  | claude-haiku..   |    24 |    35.06 |   0.0292 |     980 |      47 |
| slot_scoring         | claude-haiku..   |    11 |    26.54 |   0.0310 |    1224 |     319 |
| TOTAL                |                  |    57 |   212.38 |   0.2866 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 164.18s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 48.20s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 212.38s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 102.6s (62.7sum)
2. **SlotDiscoveryStage**: 28.4s (17.4sum)
3. **LLMSignalBridgeStage**: 18.3s (11.2sum)

### LLM Cost Breakdown
- **extraction**: $0.1720 (11 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0544 (11 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0292 (24 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0310 (11 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2866**

### Token Usage
- Input:  80,249 tokens
- Output: 18,341 tokens
- Total:  98,590 tokens
