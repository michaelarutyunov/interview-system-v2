# Pipeline Timing Analysis

- **Log file**: `interview_20260428_152921.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      9 |      90.07 |    10007.8 |   61.8 |
| SlotDiscoveryStage                     |      9 |      28.48 |     3163.9 |   19.5 |
| LLMSignalBridgeStage                   |      9 |      14.44 |     1604.1 |    9.9 |
| QuestionGenerationStage                |      9 |      10.62 |     1180.0 |    7.3 |
| GraphUpdateStage                       |      9 |       1.30 |      144.6 |    0.9 |
| StrategySelectionStage                 |      9 |       0.36 |       39.6 |    0.2 |
| ScoringPersistenceStage                |      9 |       0.15 |       16.5 |    0.1 |
| SRLPreprocessingStage                  |      9 |       0.09 |        9.8 |    0.1 |
| ContextLoadingStage                    |      9 |       0.08 |        8.4 |    0.1 |
| StateComputationStage                  |      9 |       0.07 |        7.9 |    0.0 |
| ResponseSavingStage                    |      9 |       0.06 |        7.1 |    0.0 |
| UtteranceSavingStage                   |      9 |       0.04 |        5.0 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.02 |        2.3 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     145.78 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     9 |    90.06 |   0.1448 |    1157 |     841 |
| signal_scoring       | claude-haiku..   |     9 |    40.44 |   0.0444 |    2740 |     438 |
| question_generation  | claude-haiku..   |    20 |    27.78 |   0.0291 |    1232 |      45 |
| slot_scoring         | claude-haiku..   |     9 |    27.02 |   0.0254 |    1176 |     329 |
| TOTAL                |                  |    47 |   185.29 |   0.2436 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 144.85s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 40.44s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 185.29s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 90.1s (61.8sum)
2. **SlotDiscoveryStage**: 28.5s (19.5sum)
3. **LLMSignalBridgeStage**: 14.4s (9.9sum)

### LLM Cost Breakdown
- **extraction**: $0.1448 (9 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0444 (9 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0291 (20 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0254 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2436**

### Token Usage
- Input:  70,303 tokens
- Output: 15,364 tokens
- Total:  85,667 tokens
