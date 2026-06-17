# Pipeline Timing Analysis

- **Log file**: `interview_20260505_235042.log`
- **Pipeline runs**: 9
- **Avg pipeline**: 17.97s (range: 11.72s – 29.53s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 161.75s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 161.74s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 149.94s (runs in background during stages 4–4.6)
- **Bridge await time**: 80.91s (un-overlapped portion on critical path: SignalBridge=0.7s, EdgeBridge=80.2s)
- **Concurrency savings**: 69.03s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |      9 |      80.21 |     8911.9 |   49.6 |
| ExtractionStage                        |      9 |      43.76 |     4862.4 |   27.1 |
| SlotDiscoveryStage                     |      9 |      25.78 |     2864.2 |   15.9 |
| QuestionGenerationStage                |      9 |       9.79 |     1088.3 |    6.1 |
| GraphUpdateStage                       |      9 |       0.77 |       85.3 |    0.5 |
| LLMSignalBridgeStage                   |      9 |       0.70 |       78.0 |    0.4 |
| StrategySelectionStage                 |      9 |       0.27 |       29.5 |    0.2 |
| ScoringPersistenceStage                |      9 |       0.13 |       14.1 |    0.1 |
| SRLPreprocessingStage                  |      9 |       0.08 |        9.4 |    0.1 |
| EdgeExtractionPrefetchStage            |      9 |       0.06 |        6.2 |    0.0 |
| UtteranceSavingStage                   |      9 |       0.05 |        5.4 |    0.0 |
| ResponseSavingStage                    |      9 |       0.05 |        5.0 |    0.0 |
| StateComputationStage                  |      9 |       0.04 |        4.9 |    0.0 |
| ContextLoadingStage                    |      9 |       0.04 |        4.6 |    0.0 |
| LLMPrefetchStage                       |      9 |       0.02 |        2.0 |    0.0 |
| ContinuationStage                      |      9 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     161.74 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (161.74s) and wall-clock (161.75s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |     9 |   105.75 |   0.1596 |    3921 |    2762 |
| signal_scoring       | claude-haiku..   |     9 |    44.19 |   0.0473 |    2774 |     497 |
| extraction           | claude-sonne..   |     9 |    43.75 |   0.1181 |    2708 |     333 |
| question_generation  | claude-haiku..   |    20 |    26.98 |   0.0246 |    1012 |      43 |
| slot_scoring         | claude-haiku..   |     9 |    24.37 |   0.0290 |    1277 |     388 |
| TOTAL                |                  |    56 |   245.04 |   0.3786 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 95.10s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 149.94s — runs in parallel with pipeline stages; only the un-overlapped bridge await (80909.01s) is on the critical path
- **Concurrency savings**: 69.03s (46% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 245.04s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 80.2s (49.6wall)
2. **ExtractionStage**: 43.8s (27.1wall)
3. **SlotDiscoveryStage**: 25.8s (15.9wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.1596 (9 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0473 (9 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1181 (9 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0246 (20 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0290 (9 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.3786**

### Token Usage
- Input:  116,377 tokens
- Output: 36,686 tokens
- Total:  153,063 tokens
