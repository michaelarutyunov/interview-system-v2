# Pipeline Timing Analysis

- **Log file**: `interview_20260507_003651.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 20.15s (range: 10.21s – 71.52s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 282.12s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 282.11s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 203.03s (runs in background during stages 4–4.6)
- **Bridge await time**: 142.84s (un-overlapped portion on critical path: SignalBridge=0.5s, EdgeBridge=142.3s)
- **Concurrency savings**: 60.19s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     142.30 |    10164.1 |   50.4 |
| ExtractionStage                        |     14 |      73.16 |     5226.0 |   25.9 |
| SlotDiscoveryStage                     |     14 |      45.59 |     3256.4 |   16.2 |
| QuestionGenerationStage                |     14 |      17.70 |     1264.1 |    6.3 |
| GraphUpdateStage                       |     14 |       1.62 |      115.6 |    0.6 |
| LLMSignalBridgeStage                   |     14 |       0.55 |       39.0 |    0.2 |
| StrategySelectionStage                 |     14 |       0.45 |       31.8 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.18 |       12.7 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.14 |       10.1 |    0.1 |
| ResponseSavingStage                    |     14 |       0.10 |        7.5 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.09 |        6.7 |    0.0 |
| EdgeExtractionPrefetchStage            |     14 |       0.08 |        6.0 |    0.0 |
| ContextLoadingStage                    |     14 |       0.07 |        5.0 |    0.0 |
| StateComputationStage                  |     14 |       0.06 |        4.0 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.02 |        1.6 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.2 |    0.0 |
| TOTAL                                  |        |     282.11 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (282.11s) and wall-clock (282.12s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    13 |   126.48 |   0.2007 |    3953 |    2297 |
| signal_scoring       | claude-haiku..   |    14 |    76.54 |   0.0784 |    2788 |     562 |
| extraction           | claude-sonne..   |    14 |    73.13 |   0.1969 |    2893 |     359 |
| question_generation  | claude-haiku..   |    30 |    44.05 |   0.0412 |    1132 |      48 |
| slot_scoring         | claude-haiku..   |    14 |    43.61 |   0.0471 |    1309 |     411 |
| TOTAL                |                  |    85 |   363.82 |   0.5642 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 160.79s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 203.03s — runs in parallel with pipeline stages; only the un-overlapped bridge await (142842.43s) is on the critical path
- **Concurrency savings**: 60.19s (30% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 363.82s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 142.3s (50.4wall)
2. **ExtractionStage**: 73.2s (25.9wall)
3. **SlotDiscoveryStage**: 45.6s (16.2wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.2007 (13 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0784 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1969 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0412 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0471 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.5642**

### Token Usage
- Input:  183,202 tokens
- Output: 49,960 tokens
- Total:  233,162 tokens
