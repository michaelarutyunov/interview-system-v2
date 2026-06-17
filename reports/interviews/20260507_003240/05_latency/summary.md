# Pipeline Timing Analysis

- **Log file**: `interview_20260507_012704.log`
- **Pipeline runs**: 14
- **Avg pipeline**: 20.82s (range: 11.21s – 37.41s)

## Wall-Clock vs. Stage Sum

- **Wall-clock pipeline total**: 291.54s (authoritative — from `pipeline_completed` events)
- **Σ stage durations**: 291.52s (overstates wall-clock when stages overlap)
- **Prefetched LLM time**: 272.86s (runs in background during stages 4–4.6)
- **Bridge await time**: 156.91s (un-overlapped portion on critical path: SignalBridge=0.9s, EdgeBridge=156.0s)
- **Concurrency savings**: 115.95s (prefetched LLM time fully absorbed by parallel stage execution)

## Stage Timing (by total time)

| Stage                                  |  Calls |   Total(s) |   Mean(ms) |  %wall |
|----------------------------------------|--------|------------|------------|--------|
| EdgeExtractionBridgeStage              |     14 |     155.99 |    11141.9 |   53.5 |
| ExtractionStage                        |     14 |      71.86 |     5132.7 |   24.6 |
| SlotDiscoveryStage                     |     14 |      42.80 |     3057.2 |   14.7 |
| QuestionGenerationStage                |     14 |      17.68 |     1263.0 |    6.1 |
| GraphUpdateStage                       |     14 |       1.05 |       74.8 |    0.4 |
| LLMSignalBridgeStage                   |     14 |       0.92 |       66.0 |    0.3 |
| StrategySelectionStage                 |     14 |       0.46 |       32.7 |    0.2 |
| ScoringPersistenceStage                |     14 |       0.17 |       11.9 |    0.1 |
| SRLPreprocessingStage                  |     14 |       0.13 |        9.1 |    0.0 |
| EdgeExtractionPrefetchStage            |     14 |       0.12 |        8.7 |    0.0 |
| ResponseSavingStage                    |     14 |       0.09 |        6.6 |    0.0 |
| UtteranceSavingStage                   |     14 |       0.09 |        6.3 |    0.0 |
| StateComputationStage                  |     14 |       0.07 |        5.0 |    0.0 |
| ContextLoadingStage                    |     14 |       0.07 |        4.9 |    0.0 |
| LLMPrefetchStage                       |     14 |       0.03 |        1.9 |    0.0 |
| ContinuationStage                      |     14 |       0.00 |        0.3 |    0.0 |
| TOTAL                                  |        |     291.52 |            |        |

_Stage `%wall` columns sum to >100% by design — overlap with the prefetched LLM call shows up as the gap between Σ stages (291.52s) and wall-clock (291.54s)._

## LLM Calls by Module (by total time)

| Module               | Model            | Calls |  Time(s) |  Cost($) |   TokIn |  TokOut |
|----------------------|------------------|-------|----------|----------|---------|---------|
| edge_extraction      | claude-haiku..   |    14 |   198.50 |   0.2972 |    4737 |    3299 |
| signal_scoring       | claude-haiku..   |    14 |    74.36 |   0.0765 |    2773 |     539 |
| extraction           | claude-sonne..   |    14 |    71.84 |   0.1934 |    2879 |     345 |
| question_generation  | claude-haiku..   |    30 |    46.25 |   0.0404 |    1116 |      46 |
| slot_scoring         | claude-haiku..   |    14 |    40.57 |   0.0468 |    1289 |     411 |
| TOTAL                |                  |    86 |   431.50 |   0.6544 |         |         |

### LLM Time by Concurrency

- **Inline (serial)**: 158.65s — on the critical path, fully visible in wall-clock
- **Prefetched (background)**: 272.86s — runs in parallel with pipeline stages; only the un-overlapped bridge await (156910.77s) is on the critical path
- **Concurrency savings**: 115.95s (42% of prefetched LLM time absorbed by parallel execution)
- **Σ LLM latency**: 431.50s (sum of all LLM calls; overlaps with itself — do not use as wall-clock)

## Key Findings

### Top Bottlenecks
1. **EdgeExtractionBridgeStage**: 156.0s (53.5wall)
2. **ExtractionStage**: 71.9s (24.6wall)
3. **SlotDiscoveryStage**: 42.8s (14.7wall)

### LLM Cost Breakdown
- **edge_extraction**: $0.2972 (14 calls) `[claude-haiku-4-5]`
- **signal_scoring**: $0.0765 (14 calls) `[claude-haiku-4-5]`
- **extraction**: $0.1934 (14 calls) `[claude-sonnet-4-6]`
- **question_generation**: $0.0404 (30 calls) `[claude-haiku-4-5]`
- **slot_scoring**: $0.0468 (14 calls) `[claude-haiku-4-5]`

**Total estimated cost: $0.6544**

### Token Usage
- Input:  196,969 tokens
- Output: 65,698 tokens
- Total:  262,667 tokens
