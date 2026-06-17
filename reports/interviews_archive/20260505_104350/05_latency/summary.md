# Pipeline Timing Analysis

- **Log file**: `interview_20260505_113725.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 24.38s (range: 10.52s – 38.90s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 341.39s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 341.38s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 325.82s (runs in background during stages 4–4.6)
- **Bridge await time**: 213.22s (un-overlapped portion on critical path: SignalBridge=0.1s, EdgeBridge=213.1s)
- **Concurrency savings**: 112.60s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     213.09 |    15220.6 |   62.4 |
| ExtractionStage                        |     14 |      64.35 |     4596.1 |   18.8 |
| SlotDiscoveryStage                     |     14 |      46.03 |     3287.7 |   13.5 |
| QuestionGenerationStage                |     14 |      14.96 |     1068.3 |    4.4 |
| GraphUpdateStage                       |     14 |       1.03 |       73.8 |    0.3 |
| StrategySelectionStage                 |     14 |       0.74 |       53.1 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.24 |       17.4 |    0.1 |
| EdgeExtractionPrefetchStage            |     14 |       0.16 |       11.4 |    0.0 |
| SRLPreprocessingStage                  |     14 |       0.15 |       10.9 |    0.0 |
| LLMSignalBridgeStage                   |     14 |       0.13 |        9.6 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.13 |        9.6 |    0.0 |
| ResponseSavingStage                    |     14 |       0.12 |        8.9 |    0.0 |
| StateComputationStage                  |     14 |       0.12 |        8.5 |    0.0 |
| ContextLoadingStage                    |     14 |       0.09 |        6.4 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.6 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.2 |    0.0 |
| TOTAL                                  |        |     341.38 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (341.38s) and wall-clock (341.39s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   258.78 |   0.2438 |    4030 |    2676 |
| signal_scoring       | claude-haiku..   |    14 |    67.04 |   0.0709 |    2759 |     461 |
| extraction           | claude-sonne..   |    14 |    64.33 |   0.1783 |    2806 |     288 |
| slot_scoring         | claude-haiku..   |    13 |    43.47 |   0.0397 |    1238 |     363 |
| question_generation  | claude-haiku..   |    30 |    41.52 |   0.0398 |    1088 |      48 |
| TOTAL                |                  |    85 |   475.15 |   0.5724 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 149.33s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 325.82s — runs in parallel with pipeline stages; only the un-overlapped bridge await (213222.51s) is on the critical path
- **Concurrency savings**: 112.60s (35% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 475.15s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 213.1s (62.4wall)
2. **ExtractionStage**: 64.3s (18.8wall)
3. **SlotDiscoveryStage**: 46.0s (13.5wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.2438 (14 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0709 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1783 (14 calls) `[claude-sonnet-4-6]`
- **slot_scoring**: $0.0397 (13 calls) `[claude-haiku-4-5]`
- **question_generation**: $0.0398 (30 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.5724**

### Token Usage
- Input:  183,064 tokens
- Output: 54,094 tokens
- Total:  237,158 tokens
