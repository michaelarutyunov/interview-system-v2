# LLM Signal Detection

## Core Mechanics

LLM signals are computed in a **single batched API call** per turn via `LLMBatchDetector`. The batch sends both per-concept and global signals together, keeping latency flat regardless of signal count.

Signal classes are partitioned into two scopes:
- **Per-concept** (`@llm_per_concept_signal`) — scored once for each extracted concept (`elaboration`, `charge`)
- **Global** (`@llm_global_signal`) — scored once for the entire response (`engagement`, `certainty`)

The decorators wire up `signal_name`, `description`, and `scope` as class attributes. They also validate at import time that the class defines a non-empty `RUBRIC: str` class constant covering bands 1–5. Signal classes live in `src/signals/llm/signals/` and must be imported and listed in `__all__` in `src/signals/llm/signals/__init__.py` for auto-discovery.

At detection time, global signals and per-concept scores (except elaboration) are **normalised to [0, 1]** via `(score - 1) / 4`. Per-concept `elaboration` is used to derive the categorical `llm.response_depth` for backward compatibility with `llm_response_trend`, `node_opportunity`, and question-generation prompts.

`llm.global_response_trend` is **not** a per-turn signal. It is a session-level aggregate computed separately in `GlobalSignalDetectionService` from the rolling history of per-turn `llm.response_depth` values. Its values are categorical strings (`improving`, `degrading`, `stable`, `fatigued`).

A signal is **only active** if it appears in the methodology YAML under `signals: llm:`. Signals absent from that list are never sent to the LLM and never appear in scoring.

## Signal Set

| Signal | Scope | Decorator | Normalisation | Replaces |
|--------|-------|-----------|---------------|----------|
| `llm.elaboration` | per-concept | `@llm_per_concept_signal` | 1–5 raw (used to derive `response_depth`) | `response_depth`, `specificity`, `intellectual_engagement` |
| `llm.charge` | per-concept | `@llm_per_concept_signal` | `[0, 1]` | `valence` |
| `llm.engagement` | global | `@llm_global_signal` | `[0, 1]` | `engagement` |
| `llm.certainty` | global | `@llm_global_signal` | `[0, 1]` | `certainty` |

`llm.response_depth` is **derived**, not scored directly. The batch detector computes the mean per-concept `elaboration` score and maps it to a category:
- `surface` — 1 concept with normalised elaboration ≤ 0.25
- `shallow` — normalised mean < 0.34
- `moderate` — normalised mean < 0.67
- `deep` — normalised mean ≥ 0.67

This preserves downstream contracts (`llm_response_trend`, `node_opportunity`, `all_response_depths`, question prompt) that expect categorical response depth.

## Per-Concept → Node Routing (Phase C)

Per-concept ratings from `LLMBatchDetector.detect()` are routed to specific graph nodes via a bridge step in `MethodologyStrategyService.select_strategy_and_focus()`, between global and node signal detection:

1. `GraphUpdateStage` populates `PipelineContext.concept_to_node_id` (keyed by `concept.text.lower()`) from inside the concept loop in `GraphService.add_extraction_to_graph`.
2. `GlobalSignalDetectionService.detect_with_per_concept()` returns `(global_signals, per_concept_ratings)` by stashing the `concepts` sub-dict from the batch detector.
3. The bridge step iterates `per_concept_ratings`, looks up the target node, and calls `NodeStateTracker.append_quality(node_id, elaboration, charge)` on each.
4. `append_quality` records scores into `NodeState.quality_history` and derives a categorical `response_depth` for `all_response_depths` (bins: 0.125 / 0.375 / 0.625).

Three node signals surface the per-concept history as YAML-weightable bins:
- `graph.node.elaboration` → flattened sub-keys `graph.node.elaboration.{low,mid,high}`
- `graph.node.charge` → `graph.node.charge.{negative,neutral,positive}`
- `graph.node.has_quality_data` — gate for quality-dependent strategies

Sub-keys use dot notation so the `node_signal_detection_service` flattener (which strips the last `.segment` of the signal name) produces YAML-matching flat keys.

## Prompt Architecture

`LLMBatchDetector` loads a base prompt template from `src/signals/llm/llm_signal_baseprompt.md`. The template is injected at runtime with:
- The interview question and respondent's answer
- Extracted concepts with supporting quotes
- Per-concept and global rubrics rendered from each signal class's `RUBRIC` constant
- Embedded output format and JSON example (static constants in `batch_detector.py`)

The LLM returns a JSON object with two top-level sections:
```json
{
  "concepts": {
    "<exact concept name>": {
      "elaboration": {"score": 1-5, "rationale": "..."},
      "charge":      {"score": 1-5, "rationale": "..."}
    }
  },
  "global": {
    "engagement": {"score": 1-5, "rationale": "..."},
    "certainty":  {"score": 1-5, "rationale": "..."}
  }
}
```

## Correctness Requirements

1. `RUBRIC` class constant must be a non-empty `str` containing all five numbered bands (`1 =` through `5 =`). The decorator validates this at import time with a regex; a mismatch raises `ValueError` on module load.
2. Every new signal class must be imported and listed in `__all__` in `src/signals/llm/signals/__init__.py`, otherwise the batch detector cannot discover it.
3. The signal name must appear in the methodology YAML `signals: llm:` list for it to fire during interviews.
4. Continuous signals normalise to `[0, 1]` — strategy weight keys must use `.low`, `.mid`, `.high` bin names, not raw integers.
5. `llm.global_response_trend` weight keys use categorical strings (`improving`, `degrading`, `stable`, `fatigued`), not numeric bins.
6. Per-concept signal values are currently consumed downstream via aggregation (e.g. mean elaboration → `response_depth`), not directly as node-scoped weights. Phase C-impl will wire `graph.node.richness` and `graph.node.charge` from per-concept extractions.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError` on import: "must define a non-empty class attribute `RUBRIC: str`" | Signal class missing `RUBRIC` or it is not a string | Add `RUBRIC: str = "..."` with 1–5 bands |
| `ValueError` on import: "RUBRIC must include all five numbered bands" | `RUBRIC` missing one or more `1 =` … `5 =` lines | Ensure all five bands are present |
| New signal class never detected | Missing from `__all__` in `src/signals/llm/signals/__init__.py` | Add import and export entry |
| Signal always 0 / never appears in logs | Signal not listed under `signals: llm:` in methodology YAML | Add signal name to the YAML list |
| Strategy weight never triggers for a continuous signal | Weight key uses integer instead of bin name | Replace with `.low`, `.mid`, or `.high` |
| `global_response_trend` always `stable` | Session history too short or LLM call failed silently | Check `GlobalSignalDetectionService` logs; minimum history requires 4+ turns |
| `llm.response_depth` stuck at `surface` | No concepts extracted, or all elaboration scores are 1 | Check extraction output and per-concept elaboration scores |

## Key Files

| File | Purpose |
|------|---------|
| `src/signals/llm/decorator.py` | `@llm_global_signal` and `@llm_per_concept_signal` decorators; `_registered_llm_signals` registry |
| `src/signals/llm/llm_signal_baseprompt.md` | Base prompt template with placeholders for rubrics, concepts, output format |
| `src/signals/llm/signals/` | One file per signal (`elaboration.py`, `charge.py`, `engagement.py`, `certainty.py`) |
| `src/signals/llm/signals/__init__.py` | `__all__` export list — must include every signal class |
| `src/signals/llm/llm_signal_base.py` | `BaseLLMSignal` base class |
| `src/signals/llm/batch_detector.py` | `LLMBatchDetector` — prompt building, LLM call, parsing, normalisation, and `response_depth` derivation |
| `src/signals/session/llm_response_trend.py` | `llm.global_response_trend` session-level signal |
| `src/services/global_signal_detection_service.py` | Computes `global_response_trend` from rolling history |
| `config/methodologies/*.yaml` | `signals: llm:` lists that gate which signals are active |
