# Pipeline Timing Analysis

- **Log file**: `interview_20260430_173235.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     10 |     129.20 |    12919.7 |   65.0 |
| SlotDiscoveryStage                     |     10 |      35.88 |     3588.2 |   18.1 |
| LLMSignalBridgeStage                   |     10 |      20.19 |     2019.1 |   10.2 |
| QuestionGenerationStage                |     10 |      10.53 |     1052.9 |    5.3 |
| GraphUpdateStage                       |     10 |       1.52 |      152.1 |    0.8 |
| StrategySelectionStage                 |     10 |       0.81 |       81.5 |    0.4 |
| ScoringPersistenceStage                |     10 |       0.18 |       18.1 |    0.1 |
| SRLPreprocessingStage                  |     10 |       0.13 |       12.9 |    0.1 |
| StateComputationStage                  |     10 |       0.10 |       10.0 |    0.1 |
| ContextLoadingStage                    |     10 |       0.08 |        8.0 |    0.0 |
| ResponseSavingStage                    |     10 |       0.07 |        7.0 |    0.0 |
| UtteranceSavingStage                   |     10 |       0.06 |        6.1 |    0.0 |
| LLMPrefetchStage                       |     10 |       0.02 |        2.1 |    0.0 |
| ContinuationStage                      |     10 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     198.78 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    10 |   129.18 |   0.2277 |    1527 |    1212 |
| signal_scoring       | claude-haiku..   |    10 |    57.48 |   0.0590 |    2839 |     612 |
| question_generation  | claude-haiku..   |    22 |    34.52 |   0.0280 |     964 |      62 |
| slot_scoring         | claude-haiku..   |    10 |    32.95 |   0.0368 |    1326 |     470 |
| TOTAL                |                  |    52 |   254.14 |   0.3515 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 196.65s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 57.48s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 254.14s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 129.2s (65.0sum)
2. **SlotDiscoveryStage**: 35.9s (18.1sum)
3. **LLMSignalBridgeStage**: 20.2s (10.2sum)

### LLM Cost Breakdown
- **extraction**: $0.2277 (10 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0590 (10 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0280 (22 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0368 (10 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3515**

### Token Usage
- Input:  78,140 tokens
- Output: 24,306 tokens
- Total:  102,446 tokens
