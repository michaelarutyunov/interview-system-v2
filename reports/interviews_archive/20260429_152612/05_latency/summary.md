# Pipeline Timing Analysis

- **Log file**: `interview_20260429_162109.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     15 |     161.02 |    10734.4 |   62.6 |
| SlotDiscoveryStage                     |     15 |      49.22 |     3281.0 |   19.1 |
| LLMSignalBridgeStage                   |     15 |      21.71 |     1447.3 |    8.4 |
| QuestionGenerationStage                |     15 |      20.33 |     1355.2 |    7.9 |
| GraphUpdateStage                       |     15 |       2.78 |      185.3 |    1.1 |
| StrategySelectionStage                 |     15 |       1.13 |       75.6 |    0.4 |
| ScoringPersistenceStage                |     15 |       0.34 |       22.6 |    0.1 |
| SRLPreprocessingStage                  |     15 |       0.27 |       17.7 |    0.1 |
| StateComputationStage                  |     15 |       0.17 |       11.2 |    0.1 |
| ContextLoadingStage                    |     15 |       0.16 |       10.4 |    0.1 |
| ResponseSavingStage                    |     15 |       0.12 |        8.0 |    0.0 |
| UtteranceSavingStage                   |     15 |       0.09 |        6.2 |    0.0 |
| LLMPrefetchStage                       |     15 |       0.03 |        2.0 |    0.0 |
| ContinuationStage                      |     15 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     257.36 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    15 |   160.98 |   0.2757 |    1370 |     951 |
| signal_scoring       | claude-haiku..   |    15 |    73.37 |   0.0788 |    2751 |     500 |
| question_generation  | claude-haiku..   |    32 |    48.42 |   0.0472 |    1257 |      44 |
| slot_scoring         | claude-haiku..   |    15 |    44.78 |   0.0493 |    1302 |     397 |
| TOTAL                |                  |    77 |   327.55 |   0.4509 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 254.18s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 73.37s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 327.55s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 161.0s (62.6sum)
2. **SlotDiscoveryStage**: 49.2s (19.1sum)
3. **LLMSignalBridgeStage**: 21.7s (8.4sum)

### LLM Cost Breakdown
- **extraction**: $0.2757 (15 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0788 (15 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0472 (32 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0493 (15 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.4509**

### Token Usage
- Input:  121,571 tokens
- Output: 29,120 tokens
- Total:  150,691 tokens
