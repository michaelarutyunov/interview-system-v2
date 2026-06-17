# Pipeline Timing Analysis

- **Log file**: `interview_20260428_130952.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |      9 |     108.77 |    12085.8 |   66.3 |
| SlotDiscoveryStage                     |      9 |      25.82 |     2868.7 |   15.7 |
| LLMSignalBridgeStage                   |      9 |      14.77 |     1641.2 |    9.0 |
| QuestionGenerationStage                |      9 |      11.64 |     1293.1 |    7.1 |
| GraphUpdateStage                       |      9 |       1.89 |      209.6 |    1.1 |
| StrategySelectionStage                 |      9 |       0.40 |       44.0 |    0.2 |
| ScoringPersistenceStage                |      9 |       0.26 |       29.3 |    0.2 |
| SRLPreprocessingStage                  |      9 |       0.11 |       11.8 |    0.1 |
| ResponseSavingStage                    |      9 |       0.09 |       10.4 |    0.1 |
| UtteranceSavingStage                   |      9 |       0.09 |       10.3 |    0.1 |
| StateComputationStage                  |      9 |       0.08 |        8.9 |    0.0 |
| ContextLoadingStage                    |      9 |       0.08 |        8.9 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.02 |        2.5 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     164.02 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |     9 |   108.76 |   0.1543 |    1226 |     898 |
| signal_scoring       | claude-haiku..   |     9 |    42.40 |   0.0468 |    2758 |     489 |
| question_generation  | claude-haiku..   |    20 |    30.86 |   0.0289 |    1216 |      46 |
| slot_scoring         | claude-haiku..   |     9 |    23.68 |   0.0276 |    1230 |     366 |
| TOTAL                |                  |    47 |   205.70 |   0.2576 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 163.30s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 42.40s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 205.70s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 108.8s (66.3sum)
2. **SlotDiscoveryStage**: 25.8s (15.7sum)
3. **LLMSignalBridgeStage**: 14.8s (9.0sum)

### LLM Cost Breakdown
- **extraction**: $0.1543 (9 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0468 (9 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0289 (20 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0276 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2576**

### Token Usage
- Input:  71,239 tokens
- Output: 16,698 tokens
- Total:  87,937 tokens
