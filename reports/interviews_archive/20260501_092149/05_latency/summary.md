# Pipeline Timing Analysis

- **Log file**: `interview_20260501_101819.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     11 |     107.32 |     9756.3 |   61.8 |
| SlotDiscoveryStage                     |     11 |      30.54 |     2776.7 |   17.6 |
| LLMSignalBridgeStage                   |     11 |      19.05 |     1732.3 |   11.0 |
| QuestionGenerationStage                |     11 |      13.93 |     1266.5 |    8.0 |
| GraphUpdateStage                       |     11 |       1.63 |      148.6 |    0.9 |
| StrategySelectionStage                 |     11 |       0.61 |       55.3 |    0.4 |
| ScoringPersistenceStage                |     11 |       0.19 |       16.8 |    0.1 |
| SRLPreprocessingStage                  |     11 |       0.11 |       10.4 |    0.1 |
| ResponseSavingStage                    |     11 |       0.10 |        9.5 |    0.1 |
| ContextLoadingStage                    |     11 |       0.09 |        8.2 |    0.1 |
| StateComputationStage                  |     11 |       0.09 |        8.1 |    0.1 |
| UtteranceSavingStage                   |     11 |       0.09 |        7.8 |    0.0 |
| LLMPrefetchStage                       |     11 |       0.02 |        1.9 |    0.0 |
| ContinuationStage                      |     11 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     173.79 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    11 |   107.29 |   0.1858 |    1236 |     879 |
| signal_scoring       | claude-haiku..   |    11 |    51.15 |   0.0572 |    2760 |     488 |
| question_generation  | claude-haiku..   |    24 |    34.49 |   0.0295 |     989 |      48 |
| slot_scoring         | claude-haiku..   |    11 |    28.31 |   0.0339 |    1247 |     366 |
| TOTAL                |                  |    57 |   221.25 |   0.3064 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 170.10s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 51.15s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 221.25s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 107.3s (61.8sum)
2. **SlotDiscoveryStage**: 30.5s (17.6sum)
3. **LLMSignalBridgeStage**: 19.1s (11.0sum)

### LLM Cost Breakdown
- **extraction**: $0.1858 (11 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0572 (11 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0295 (24 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0339 (11 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3064**

### Token Usage
- Input:  81,417 tokens
- Output: 20,222 tokens
- Total:  101,639 tokens
