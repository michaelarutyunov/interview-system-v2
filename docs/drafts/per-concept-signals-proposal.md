# Proposal: Per-Concept LLM Signals at Extraction Time

## Current Architecture

The system has a 12-stage pipeline for conducting adaptive interviews. Strategy selection (Stage 8) uses joint strategy-node scoring where signals are combined to select the next question strategy and target node.

Current LLM signals (Stage 6-7) evaluate the ENTIRE response as one blob:
- `llm.response_depth` (surface/shallow/deep)
- `llm.specificity` (1-5 scale)
- `llm.engagement` (1-5 scale)
- `llm.valence` (1-5 scale)
- `llm.intellectual_engagement` (1-5 scale)

These are GLOBAL signals — same value for every node being scored. They can differentiate between strategies but NOT between nodes, because they contribute identically to every (strategy, node) pair's score.

### How Scoring Works

In `rank_strategy_node_pairs()` (scoring.py:407):
```python
combined_signals = {**global_signals, **node_signal_dict}
base_score = Σ(signal_weight × signal_value)
```

For each (strategy, node) pair, global signals contribute identically. They shift all candidates equally and don't affect ranking between nodes. Only node-scoped signals (`graph.node.*`) can differentiate between nodes.

## The Problem

1. **Global LLM signals don't differentiate nodes** — they shift all candidates equally
2. **Whole-response evaluation loses per-concept variation** — a response discussing "side effects" negatively and "energy" positively gets one blended score
3. **Focus-node selection is a bottleneck** — only one node gets selected per turn, so focus-node-only attribution leaves other extracted concepts without quality data
4. **Selection pressure compounds** — promising but unselected nodes compete at a disadvantage in subsequent turns because they lack quality signals

### Moderator Analogy

Experienced moderators don't evaluate responses globally. They assess each concept as it emerges:
- "side effects" → rich detail, negative emotional charge, high probe potential
- "feel energetic" → positive, but thin — could ladder up
- "doctor recommended" → brief mention, neutral, low priority

The moderator does per-concept quality assessment in real time. They notice richness (how much the respondent says about a concept) and charge (emotional engagement with that concept). They use this to decide what to probe — based on which specific concept has the most productive potential, not a global metric.

## Proposed Architecture: Per-Concept Signals at Extraction Time

### Core Change

Fold per-concept quality assessment into the existing extraction LLM call (Stage 3). Instead of 5 global LLM signals, add 2 per-concept dimensions to each extracted concept:

- **richness** (low/medium/high): How much did the respondent say about THIS concept? Specific details, examples, elaboration. Replaces `response_depth` + `specificity`.
- **charge** (negative/neutral/positive): Emotional engagement with THIS concept — enthusiasm, frustration, excitement. Replaces `valence` + `engagement` + `intellectual_engagement`.

### Extraction Output Change

From:
```json
{
  "concepts": [
    {"name": "side effects", "type": "attribute"}
  ],
  "relationships": [...]
}
```

To:
```json
{
  "concepts": [
    {"name": "side effects", "type": "attribute", "richness": "high", "charge": "negative"},
    {"name": "feeling energetic", "type": "functional_consequence", "richness": "medium", "charge": "positive"},
    {"name": "doctor recommended", "type": "attribute", "richness": "low", "charge": "neutral"}
  ],
  "relationships": [...]
}
```

### Key Properties

1. **Every extracted concept gets quality data** at extraction time, not just the focus node
2. **No new LLM call** — just richer output from existing extraction (~5 extra tokens per concept)
3. After dedup (Stage 5), each node accumulates a quality profile from all extractions that mapped to it
4. Derived signals (computed like existing `exhaustion_score`):
   - `graph.node.richness` (float [0,1]): average richness across extractions
   - `graph.node.charge` (float [-1,1]): average charge
   - `graph.node.richness.high` / `.medium` / `.low` (bool): threshold bins
   - `graph.node.charge.positive` / `.negative` (bool): threshold bins
   - `graph.node.has_quality_data` (bool): True if node has been extracted at least once

### Cold Start Handling

Nodes never extracted have `has_quality_data = False` → quality weights contribute 0 (neutral). New nodes compete on structural signals alone. This is the same pattern as existing `exhaustion_score` (which returns 0.0 for never-focused nodes).

The scoring engine already handles missing signals:
```python
# scoring.py:101-106
for signal_key, weight in weights.items():
    signal_value = _get_signal_value(signal_key, signals)
    if signal_value is None:
        continue  # contributes 0.0
```

### What Gets Replaced

The 5 global LLM signals would be REMOVED. Their informational content redistributed:
- `response_depth` + `specificity` → per-concept `richness`
- `valence` + `engagement` + `intellectual_engagement` → per-concept `charge`

Keep only:
- `llm.global_response_trend` — conversation-level fatigue indicator (for `revitalize` strategy)
- `meta.interview.phase` — already structural, not LLM-detected
- `temporal.*` signals — already session-level

### Strategy YAML Usage

```yaml
# ascend: prefer rich, positively charged nodes for laddering
graph.node.richness: 0.3
graph.node.charge.positive: 0.2
graph.node.charge.negative: -0.4  # don't ladder from negative nodes — ground them first

# ground: useful for negatively charged concepts (understand the pain)
graph.node.charge.negative: 0.3
graph.node.richness: -0.2  # shallow nodes need grounding more than rich ones

# anchor: connect isolated nodes regardless of quality
# (no quality signal weights needed — purely structural)

# revitalize: triggered by global_response_trend (unchanged)
llm.global_response_trend.fatigued: 1.0
```

## Open Questions

1. **Existing concepts discussed but not re-extracted**: A response discusses an existing node without producing a new extraction. Should extraction also rate mentioned-but-not-extracted concepts? Or accept that quality data only updates on new extractions?

2. **Two dimensions sufficient?** Is `richness + charge` enough, or should there be a third dimension (e.g., novelty — is this new information or reiteration)?

3. **Transition strategy**: Should the global LLM signal batch detector be kept as a fallback during transition, or removed entirely?

4. **Impact on extraction prompt complexity**: Adding per-concept ratings increases extraction output complexity. Will this degrade extraction quality (concept identification, relationship extraction)?

5. **Charge scale**: Is 3-level (negative/neutral/positive) sufficient granularity, or should charge be on a 5-point scale like current signals?

## Context Files

- Extraction service: `src/services/extraction_service.py`
- Extraction prompts: `src/llm/prompts/`
- LLM signal detection: `src/signals/llm/`
- Strategy scoring: `src/methodologies/scoring.py`
- Node state tracker: `src/services/node_state_tracker.py`
- Node signal detectors: `src/signals/graph/node_signals.py`
- Methodology YAMLs: `config/methodologies/*.yaml`
- Pipeline contracts: `.claude/context/pipeline-contracts.md`
- Strategy scoring spec: `.claude/context/strategy-scoring.md`
- Node state tracker spec: `.claude/context/node-state-tracker.md`
