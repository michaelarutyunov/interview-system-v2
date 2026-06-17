# Pipeline Timing Analysis

- **Log file**: `interview_20260430_114536.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     14 |     166.39 |    11884.7 |   66.6 |
| SlotDiscoveryStage                     |     14 |      38.97 |     2783.9 |   15.6 |
| LLMSignalBridgeStage                   |     14 |      21.28 |     1519.9 |    8.5 |
| QuestionGenerationStage                |     14 |      19.22 |     1373.0 |    7.7 |
| GraphUpdateStage                       |     14 |       2.09 |      149.1 |    0.8 |
| StrategySelectionStage                 |     14 |       0.91 |       64.8 |    0.4 |
| ScoringPersistenceStage                |     14 |       0.26 |       18.3 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.19 |       13.2 |    0.1 |
| StateComputationStage                  |     14 |       0.13 |        9.4 |    0.1 |
| ContextLoadingStage                    |     14 |       0.13 |        9.2 |    0.1 |
| UtteranceSavingStage                   |     14 |       0.08 |        5.9 |    0.0 |
| ResponseSavingStage                    |     14 |       0.08 |        5.5 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.6 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     249.75 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    14 |   166.37 |   0.2401 |    1330 |     877 |
| signal_scoring       | claude-haiku..   |    14 |    62.24 |   0.0709 |    2753 |     462 |
| question_generation  | claude-haiku..   |    30 |    45.19 |   0.0394 |    1052 |      52 |
| slot_scoring         | claude-haiku..   |    14 |    35.75 |   0.0401 |    1202 |     333 |
| TOTAL                |                  |    72 |   309.54 |   0.3906 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 247.30s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 62.24s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 309.54s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 166.4s (66.6sum)
2. **SlotDiscoveryStage**: 39.0s (15.6sum)
3. **LLMSignalBridgeStage**: 21.3s (8.5sum)

### LLM Cost Breakdown
- **extraction**: $0.2401 (14 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0709 (14 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0394 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0401 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3906**

### Token Usage
- Input:  105,565 tokens
- Output: 24,987 tokens
- Total:  130,552 tokens
