# Pipeline Timing Analysis

- **Log file**: `interview_20260430_172335.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     12 |     147.01 |    12250.5 |   63.4 |
| SlotDiscoveryStage                     |     12 |      38.17 |     3180.8 |   16.5 |
| LLMSignalBridgeStage                   |     12 |      30.82 |     2568.1 |   13.3 |
| QuestionGenerationStage                |     12 |      12.55 |     1046.1 |    5.4 |
| GraphUpdateStage                       |     12 |       1.60 |      133.3 |    0.7 |
| StrategySelectionStage                 |     12 |       1.02 |       84.9 |    0.4 |
| ScoringPersistenceStage                |     12 |       0.24 |       20.3 |    0.1 |
| SRLPreprocessingStage                  |     12 |       0.18 |       14.9 |    0.1 |
| StateComputationStage                  |     12 |       0.11 |        9.4 |    0.0 |
| ContextLoadingStage                    |     12 |       0.10 |        8.3 |    0.0 |
| UtteranceSavingStage                   |     12 |       0.07 |        5.5 |    0.0 |
| ResponseSavingStage                    |     12 |       0.06 |        5.1 |    0.0 |
| LLMPrefetchStage                       |     12 |       0.02 |        2.0 |    0.0 |
| ContinuationStage                      |     12 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     231.95 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    12 |   146.99 |   0.2579 |    1698 |    1094 |
| signal_scoring       | claude-haiku..   |    12 |    70.48 |   0.0686 |    2854 |     572 |
| question_generation  | claude-haiku..   |    25 |    47.83 |   0.0360 |    1039 |      80 |
| slot_scoring         | claude-haiku..   |    12 |    34.92 |   0.0408 |    1288 |     422 |
| TOTAL                |                  |    61 |   300.22 |   0.4033 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 229.74s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 70.48s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 300.22s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 147.0s (63.4sum)
2. **SlotDiscoveryStage**: 38.2s (16.5sum)
3. **LLMSignalBridgeStage**: 30.8s (13.3sum)

### LLM Cost Breakdown
- **extraction**: $0.2579 (12 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0686 (12 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0360 (25 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0408 (12 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.4033**

### Token Usage
- Input:  96,059 tokens
- Output: 27,050 tokens
- Total:  123,109 tokens
