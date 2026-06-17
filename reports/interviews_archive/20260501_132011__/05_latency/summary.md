# Pipeline Timing Analysis

- **Log file**: `interview_20260501_141639.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     11 |     107.42 |     9765.1 |   62.8 |
| SlotDiscoveryStage                     |     11 |      30.80 |     2800.2 |   18.0 |
| LLMSignalBridgeStage                   |     11 |      17.92 |     1629.2 |   10.5 |
| QuestionGenerationStage                |     11 |      11.83 |     1075.8 |    6.9 |
| GraphUpdateStage                       |     11 |       1.68 |      152.9 |    1.0 |
| StrategySelectionStage                 |     11 |       0.62 |       56.8 |    0.4 |
| ScoringPersistenceStage                |     11 |       0.18 |       15.9 |    0.1 |
| SRLPreprocessingStage                  |     11 |       0.12 |       11.0 |    0.1 |
| StateComputationStage                  |     11 |       0.10 |        8.7 |    0.1 |
| ContextLoadingStage                    |     11 |       0.09 |        8.2 |    0.1 |
| UtteranceSavingStage                   |     11 |       0.07 |        6.1 |    0.0 |
| ResponseSavingStage                    |     11 |       0.06 |        5.7 |    0.0 |
| LLMPrefetchStage                       |     11 |       0.02 |        1.8 |    0.0 |
| ContinuationStage                      |     11 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     170.91 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    11 |   107.40 |   0.1846 |    1194 |     880 |
| signal_scoring       | claude-haiku..   |    11 |    50.33 |   0.0558 |    2758 |     463 |
| question_generation  | claude-haiku..   |    24 |    33.89 |   0.0300 |    1010 |      48 |
| slot_scoring         | claude-haiku..   |    11 |    28.40 |   0.0341 |    1241 |     371 |
| TOTAL                |                  |    57 |   220.01 |   0.3045 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 169.69s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 50.33s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 220.01s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 107.4s (62.8sum)
2. **SlotDiscoveryStage**: 30.8s (18.0sum)
3. **LLMSignalBridgeStage**: 17.9s (10.5sum)

### LLM Cost Breakdown
- **extraction**: $0.1846 (11 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0558 (11 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0300 (24 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0341 (11 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3045**

### Token Usage
- Input:  81,342 tokens
- Output: 20,019 tokens
- Total:  101,361 tokens
