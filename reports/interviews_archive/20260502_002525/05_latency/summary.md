# Pipeline Timing Analysis

- **Log file**: `interview_20260502_012205.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     11 |      95.12 |     8647.2 |   58.8 |
| SlotDiscoveryStage                     |     11 |      37.99 |     3453.7 |   23.5 |
| LLMSignalBridgeStage                   |     11 |      15.58 |     1416.4 |    9.6 |
| QuestionGenerationStage                |     11 |      10.78 |      980.1 |    6.7 |
| GraphUpdateStage                       |     11 |       1.39 |      126.3 |    0.9 |
| StrategySelectionStage                 |     11 |       0.42 |       37.8 |    0.3 |
| ScoringPersistenceStage                |     11 |       0.17 |       15.7 |    0.1 |
| SRLPreprocessingStage                  |     11 |       0.11 |       10.1 |    0.1 |
| ContextLoadingStage                    |     11 |       0.09 |        8.5 |    0.1 |
| StateComputationStage                  |     11 |       0.09 |        8.1 |    0.1 |
| ResponseSavingStage                    |     11 |       0.07 |        6.5 |    0.0 |
| UtteranceSavingStage                   |     11 |       0.05 |        4.9 |    0.0 |
| LLMPrefetchStage                       |     11 |       0.02 |        1.8 |    0.0 |
| ContinuationStage                      |     11 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     161.89 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    11 |    95.10 |   0.1643 |    1140 |     768 |
| signal_scoring       | claude-haiku..   |    11 |    46.88 |   0.0534 |    2720 |     426 |
| slot_scoring         | claude-haiku..   |    11 |    36.03 |   0.0313 |    1259 |     317 |
| question_generation  | claude-haiku..   |    24 |    31.39 |   0.0299 |    1035 |      42 |
| TOTAL                |                  |    57 |   209.40 |   0.2789 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 162.52s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 46.88s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 209.40s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 95.1s (58.8sum)
2. **SlotDiscoveryStage**: 38.0s (23.5sum)
3. **LLMSignalBridgeStage**: 15.6s (9.6sum)

### LLM Cost Breakdown
- **extraction**: $0.1643 (11 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0534 (11 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0313 (11 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0299 (24 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2789**

### Token Usage
- Input:  81,134 tokens
- Output: 17,639 tokens
- Total:  98,773 tokens
