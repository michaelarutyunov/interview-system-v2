# Pipeline Timing Analysis

- **Log file**: `interview_20260430_193407.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     10 |      56.28 |     5627.7 |   56.9 |
| SlotDiscoveryStage                     |     10 |      18.55 |     1854.8 |   18.7 |
| LLMSignalBridgeStage                   |     10 |      12.02 |     1201.6 |   12.1 |
| QuestionGenerationStage                |     10 |      10.40 |     1040.0 |   10.5 |
| GraphUpdateStage                       |     10 |       0.74 |       74.2 |    0.7 |
| StrategySelectionStage                 |     10 |       0.44 |       44.2 |    0.4 |
| ScoringPersistenceStage                |     10 |       0.16 |       15.6 |    0.2 |
| ContextLoadingStage                    |     10 |       0.08 |        7.6 |    0.1 |
| StateComputationStage                  |     10 |       0.07 |        7.2 |    0.1 |
| ResponseSavingStage                    |     10 |       0.07 |        7.0 |    0.1 |
| SRLPreprocessingStage                  |     10 |       0.06 |        6.0 |    0.1 |
| UtteranceSavingStage                   |     10 |       0.05 |        4.7 |    0.0 |
| LLMPrefetchStage                       |     10 |       0.02 |        2.3 |    0.0 |
| ContinuationStage                      |     10 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |      98.93 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    10 |    56.27 |   0.0922 |     893 |     436 |
| signal_scoring       | claude-haiku..   |    10 |    31.27 |   0.0417 |    2653 |     304 |
| question_generation  | claude-haiku..   |    22 |    25.02 |   0.0205 |     807 |      25 |
| slot_scoring         | claude-haiku..   |     9 |    17.55 |   0.0189 |    1038 |     213 |
| TOTAL                |                  |    51 |   130.11 |   0.1733 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 98.84s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 31.27s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 130.11s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 56.3s (56.9sum)
2. **SlotDiscoveryStage**: 18.5s (18.7sum)
3. **LLMSignalBridgeStage**: 12.0s (12.1sum)

### LLM Cost Breakdown
- **extraction**: $0.0922 (10 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0417 (10 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0205 (22 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0189 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.1733**

### Token Usage
- Input:  62,555 tokens
- Output: 9,868 tokens
- Total:  72,423 tokens
