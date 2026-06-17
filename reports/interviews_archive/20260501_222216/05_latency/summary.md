# Pipeline Timing Analysis

- **Log file**: `interview_20260501_231857.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     11 |     102.04 |     9276.6 |   63.1 |
| SlotDiscoveryStage                     |     11 |      26.37 |     2397.1 |   16.3 |
| LLMSignalBridgeStage                   |     11 |      18.92 |     1720.3 |   11.7 |
| QuestionGenerationStage                |     11 |      11.74 |     1067.2 |    7.3 |
| GraphUpdateStage                       |     11 |       1.50 |      136.7 |    0.9 |
| StrategySelectionStage                 |     11 |       0.40 |       36.2 |    0.2 |
| ScoringPersistenceStage                |     11 |       0.19 |       17.6 |    0.1 |
| SRLPreprocessingStage                  |     11 |       0.14 |       12.7 |    0.1 |
| StateComputationStage                  |     11 |       0.09 |        8.5 |    0.1 |
| ContextLoadingStage                    |     11 |       0.09 |        8.2 |    0.1 |
| ResponseSavingStage                    |     11 |       0.07 |        6.4 |    0.0 |
| UtteranceSavingStage                   |     11 |       0.05 |        4.7 |    0.0 |
| LLMPrefetchStage                       |     11 |       0.02 |        1.9 |    0.0 |
| ContinuationStage                      |     11 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     161.64 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    11 |   102.02 |   0.1754 |    1216 |     819 |
| signal_scoring       | claude-haiku..   |    11 |    46.72 |   0.0536 |    2733 |     428 |
| question_generation  | claude-haiku..   |    24 |    33.37 |   0.0312 |    1055 |      49 |
| slot_scoring         | claude-haiku..   |    11 |    24.75 |   0.0288 |    1192 |     285 |
| TOTAL                |                  |    57 |   206.85 |   0.2890 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 160.14s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 46.72s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 206.85s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 102.0s (63.1sum)
2. **SlotDiscoveryStage**: 26.4s (16.3sum)
3. **LLMSignalBridgeStage**: 18.9s (11.7sum)

### LLM Cost Breakdown
- **extraction**: $0.1754 (11 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0536 (11 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0312 (24 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0288 (11 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.2890**

### Token Usage
- Input:  81,884 tokens
- Output: 18,034 tokens
- Total:  99,918 tokens
