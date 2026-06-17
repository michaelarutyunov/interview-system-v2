# Pipeline Timing Analysis

- **Log file**: `interview_20260430_174620.log`
- **Pipeline runs**: 0

## Wall-Clock vs. Stage Sum

- No `pipeline_completed` events found — percentages below use Σ stages and may overstate wall-clock contribution.

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |   %sum |
|----------------------------------------|--------|------------|------------|--------|
| ExtractionStage                        |     11 |     112.94 |    10267.5 |   62.9 |
| SlotDiscoveryStage                     |     11 |      32.87 |     2987.9 |   18.3 |
| LLMSignalBridgeStage                   |     11 |      19.56 |     1778.2 |   10.9 |
| QuestionGenerationStage                |     11 |      10.82 |      984.0 |    6.0 |
| GraphUpdateStage                       |     11 |       1.81 |      164.1 |    1.0 |
| StrategySelectionStage                 |     11 |       0.79 |       72.0 |    0.4 |
| ScoringPersistenceStage                |     11 |       0.19 |       17.0 |    0.1 |
| SRLPreprocessingStage                  |     11 |       0.12 |       10.5 |    0.1 |
| StateComputationStage                  |     11 |       0.11 |        9.6 |    0.1 |
| ContextLoadingStage                    |     11 |       0.09 |        8.5 |    0.1 |
| ResponseSavingStage                    |     11 |       0.08 |        7.2 |    0.0 |
| UtteranceSavingStage                   |     11 |       0.06 |        5.2 |    0.0 |
| LLMPrefetchStage                       |     11 |       0.03 |        2.4 |    0.0 |
| ContinuationStage                      |     11 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     179.46 |            |        |

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| extraction           | claude-sonne..   |    11 |   112.93 |   0.2001 |    1363 |     940 |
| signal_scoring       | claude-haiku..   |    11 |    54.15 |   0.0589 |    2766 |     518 |
| question_generation  | claude-haiku..   |    24 |    32.15 |   0.0301 |    1009 |      49 |
| slot_scoring         | claude-haiku..   |    11 |    30.24 |   0.0357 |    1289 |     391 |
| TOTAL                |                  |    57 |   229.45 |   0.3247 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 175.31s — on the critical path, fully visible in wall-clock
- **Prefetched (concurrent with stages 4–4.5)**: 54.15s — runs in parallel; only the portion exceeding stage 4–4.5 wall-clock contributes to total
- **Σ LLM latency**: 229.45s (double-counts the overlap window — do not sum against wall-clock)

## Key Findings

### Top Bottlenecks
1. **ExtractionStage**: 112.9s (62.9sum)
2. **SlotDiscoveryStage**: 32.9s (18.3sum)
3. **LLMSignalBridgeStage**: 19.6s (10.9sum)

### LLM Cost Breakdown
- **extraction**: $0.2001 (11 calls) `[claude-sonnet-4-6]`
- **signal_scoring**: $0.0589 (11 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0301 (24 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0357 (11 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3247**

### Token Usage
- Input:  83,803 tokens
- Output: 21,512 tokens
- Total:  105,315 tokens
