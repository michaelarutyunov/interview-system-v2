# Pipeline Timing Analysis

- **Log file**: `interview_20260428_113440.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     10 |     108.40 |    10840.2 |   61.9 |
| SlotDiscoveryStage                     |     10 |      33.80 |     3380.4 |   19.3 |
| LLMSignalBridgeStage                   |     10 |      18.97 |     1897.4 |   10.8 |
| QuestionGenerationStage                |     10 |      11.35 |     1135.1 |    6.5 |
| GraphUpdateStage                       |     10 |       1.76 |      175.5 |    1.0 |
| StrategySelectionStage                 |     10 |       0.33 |       33.1 |    0.2 |
| ScoringPersistenceStage                |     10 |       0.20 |       20.1 |    0.1 |
| SRLPreprocessingStage                  |     10 |       0.12 |       11.5 |    0.1 |
| ContextLoadingStage                    |     10 |       0.08 |        8.5 |    0.0 |
| StateComputationStage                  |     10 |       0.08 |        8.1 |    0.0 |
| UtteranceSavingStage                   |     10 |       0.05 |        5.4 |    0.0 |
| ResponseSavingStage                    |     10 |       0.05 |        5.4 |    0.0 |
| LLMPrefetchStage                       |     10 |       0.02 |        2.2 |    0.0 |
| ContinuationStage                      |     10 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     175.23 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    10 |   108.39 |   0.1830 |    1306 |     959 |
| signal_scoring       | claude-haiku..   |    10 |    54.45 |   0.0545 |    2786 |     532 |
| slot_scoring         | claude-haiku..   |    10 |    31.50 |   0.0346 |    1307 |     431 |
| question_generation  | claude-haiku..   |    22 |    30.70 |   0.0330 |    1239 |      52 |
| TOTAL                |                  |    52 |   225.03 |   0.3051 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 170.58s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 54.45s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 225.03s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 108.4s (61.9sum)
2. **SlotDiscoveryStage**: 33.8s (19.3sum)
3. **LLMSignalBridgeStage**: 19.0s (10.8sum)

### LLM Cost Breakdown
- **extraction**: $0.1830 (10 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0545 (10 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0346 (10 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0330 (22 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3051**

### Token Usage
- Input:  81,253 tokens
- Output: 20,370 tokens
- Total:  101,623 tokens
