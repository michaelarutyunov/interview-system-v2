# LLM Signal Detection

## Core Mechanics

LLM signals are computed in a **single batched API call** per turn via `LLMBatchDetector`. The batch sends both per-concept and global signals together, keeping latency flat regardless of signal count.

Signal classes are partitioned into two scopes:
- **Per-concept** (`@llm_per_concept_signal`) — scored once for each extracted concept (`elaboration`, `charge`)
- **Global** (`@llm_global_signal`) — scored once for the entire response (`engagement`, `certainty`)

The decorators wire up `signal_name`, `description`, and `scope` as class attributes. They also validate at import time that the class defines a non-empty `RUBRIC: str` class constant covering bands 1–5. Signal classes live in `src/signals/llm/signals/` and must be imported and listed in `__all__` in `src/signals/llm/signals/__init__.py` for auto-discovery.

At detection time, global signals and per-concept scores (except elaboration) are **normalised to [0, 1]** via `(score - 1) / 4`. Per-concept `elaboration` is used to derive the categorical `response.semantic.llm.response_depth` for backward compatibility with `llm_response_trend` and question-generation prompts.

`response.semantic.llm.engagement.trend` is **not** a per-turn signal. It is a session-level aggregate computed separately in `GlobalSignalDetectionService` from the rolling history of per-turn `response.semantic.llm.response_depth` values. Its values are categorical strings (`deepening`, `shallowing`, `stable`, `fatigued`).

A signal is **only active** if it appears in the methodology YAML under `signals: llm:`. Signals absent from that list are never sent to the LLM and never appear in scoring.

## Signal Set

| Signal | Scope | Decorator | Normalisation | Replaces |
|--------|-------|-----------|---------------|----------|
| `response.semantic.llm.elaboration` | per-concept | `@llm_per_concept_signal` | 1–5 raw (used to derive `response_depth`) | `response_depth`, `specificity`, `intellectual_engagement` |
| `response.semantic.llm.charge` | per-concept | `@llm_per_concept_signal` | `[0, 1]` | `valence` |
| `response.semantic.llm.engagement` | global | `@llm_global_signal` | `[0, 1]` | `engagement` |
| `response.semantic.llm.certainty` | global | `@llm_global_signal` | `[0, 1]` | `certainty` |

`response.semantic.llm.response_depth` is **derived**, not scored directly. The batch detector computes the mean per-concept `elaboration` score and maps it to a category:
- `surface` — 1 concept with normalised elaboration ≤ 0.25
- `shallow` — normalised mean < 0.34
- `moderate` — normalised mean < 0.67
- `deep` — normalised mean ≥ 0.67

This preserves downstream contracts (`llm_response_trend`, `all_response_depths`, question prompt) that expect categorical response depth.

## Prefetch and Bridge Architecture

LLM batch detection is **prefetched** in Stage 3.1 (`LLMPrefetchStage`), which fires immediately after extraction completes. The LLM call runs as an `asyncio.Task`, overlapping with Stages 4 (GraphUpdate) and 4.5 (SlotDiscovery) to hide latency.

### Stage 3.1 — LLMPrefetchStage
- Invokes `LLMBatchDetector.detect()` and stores the resulting `asyncio.Task` on `PipelineContext.llm_signal_task`.
- Does **not** await the task — it runs concurrently with graph update and slot discovery.

### Stage 4.7 — LLMSignalBridgeStage
- Awaits `PipelineContext.llm_signal_task` to resolve the batch detector result.
- Routes per-concept ratings to `NodeStateTracker`:
  1. Reads `PipelineContext.concept_to_node_id` (populated by `GraphUpdateStage` in Stage 4, keyed by `concept.text.lower()`).
  2. Iterates per-concept ratings from the batch result, looks up the target node, and calls `NodeStateTracker.append_quality(node_id, elaboration, charge)` on each.
  3. `append_quality` records scores into `NodeState.quality_history` and derives a categorical `response_depth` for `all_response_depths` (bins: 0.125 / 0.375 / 0.625).
- Passes global signals forward to Stage 6 via `PipelineContext.llm_global_signals`.

### Stage 6 — StrategySelectionStage
- `GlobalSignalDetectionService.detect()` no longer calls the LLM itself. It accepts `llm_global_signals` (from the bridge stage output) and computes session-level aggregates (`engagement.trend`) from rolling history.
- The removed method `GlobalSignalDetectionService.detect_with_per_concept()` has been replaced by the prefetch/bridge split above.

Three node signals surface the per-concept history as YAML-weightable bins:
- `convgraph.node.llm.elaboration` → flattened sub-keys `convgraph.node.llm.elaboration.{low,mid,high}`
- `convgraph.node.llm.charge` → `convgraph.node.llm.charge.{negative,neutral,positive}`
- `convgraph.node.llm.has_quality_data` — gate for quality-dependent strategies

Sub-keys use dot notation so the `node_signal_detection_service` flattener (which strips the last `.segment` of the signal name) produces YAML-matching flat keys.

## Prompt Architecture

`LLMBatchDetector` loads a base prompt template from `src/signals/llm/llm_signal_baseprompt.md`. The template is injected at runtime with:
- The interview question and respondent's answer
- Extracted concepts with supporting quotes
- Per-concept and global rubrics rendered from each signal class's `RUBRIC` constant
- Embedded output format and JSON example (static constants in `batch_detector.py`)

The LLM returns a JSON object with two top-level sections. **`global` comes first** to prevent Haiku from dropping the trailing global keys due to output-length attention limits:
```json
{
  "global": {
    "engagement": {"score": 1-5, "rationale": "..."},
    "certainty":  {"score": 1-5, "rationale": "..."}
  },
  "concepts": {
    "<exact concept name>": {
      "elaboration": {"score": 1-5, "rationale": "..."},
      "charge":      {"score": 1-5, "rationale": "..."}
    }
  }
}
```

**Why `global` comes first:** Smaller models like Haiku generate output token-by-token. When `concepts` came first, the variable-length per-concept section consumed most of Haiku's output budget, and the trailing `global` section was frequently truncated or omitted entirely. This caused `engagement.mid` and `certainty.mid` to fire at 100% (fallback values) across all turns, neutralizing engagement/certainty suppressors and brakes in strategy scoring. Reordering fixed the issue (commit `c1e5a7b`).

## Correctness Requirements

1. `RUBRIC` class constant must be a non-empty `str` containing all five numbered bands (`1 =` through `5 =`). The decorator validates this at import time with a regex; a mismatch raises `ValueError` on module load.
2. Every new signal class must be imported and listed in `__all__` in `src/signals/llm/signals/__init__.py`, otherwise the batch detector cannot discover it.
3. The signal name must appear in the methodology YAML `signals: llm:` list for it to fire during interviews.
4. Continuous signals normalise to `[0, 1]` — strategy weight keys must use `.low`, `.mid`, `.high` bin names, not raw integers.
5. `response.semantic.llm.engagement.trend` weight keys use categorical strings (`improving`, `degrading`, `stable`, `fatigued`), not numeric bins.
6. Per-concept signals have a **producer/consumer split**. Producers (`response.semantic.llm.elaboration`, `response.semantic.llm.charge`) generate per-concept scores and must appear in `signals: llm:`. Consumers (`convgraph.node.llm.elaboration`, `convgraph.node.llm.charge`, `convgraph.node.llm.has_quality_data`) read scores bridged into `NodeStateTracker` and are detected by `NodeSignalDetectionService`. Both must be present in YAML — producers for batch detection, consumers for node scoring. If producers are absent, `per_concept_classes` is empty, no per-concept records are generated, and all consumer node signals return zero regardless of how rich the LLM response was.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError` on import: "must define a non-empty class attribute `RUBRIC: str`" | Signal class missing `RUBRIC` or it is not a string | Add `RUBRIC: str = "..."` with 1–5 bands |
| `ValueError` on import: "RUBRIC must include all five numbered bands" | `RUBRIC` missing one or more `1 =` … `5 =` lines | Ensure all five bands are present |
| New signal class never detected | Missing from `__all__` in `src/signals/llm/signals/__init__.py` | Add import and export entry |
| Signal always 0 / never appears in logs | Signal not listed under `signals: llm:` in methodology YAML | Add signal name to the YAML list |
| Strategy weight never triggers for a continuous signal | Weight key uses integer instead of bin name | Replace with `.low`, `.mid`, or `.high` |
| `global_response_trend` always `stable` | Session history too short or LLM call failed silently | Check `GlobalSignalDetectionService` logs; minimum history requires 4+ turns |
| `response.semantic.llm.response_depth` stuck at `surface` | No concepts extracted, or all elaboration scores are 1 | Check extraction output and per-concept elaboration scores |
| `bridged_count=0` every turn; `convgraph.node.llm.has_quality_data` always False | `response.semantic.llm.elaboration` and/or `response.semantic.llm.charge` missing from `signals: llm:` in methodology YAML — `per_concept_classes` is empty so batch detector generates no per-concept records; or `LLMSignalBridgeStage` not wired into pipeline | Add `response.semantic.llm.elaboration` and `response.semantic.llm.charge` to `signals: llm:` in the YAML; verify Stage 4.7 is in pipeline |
| Per-concept records are empty dicts `{}` despite LLM responding with concept data | `_concept_fields` in batch_detector reading `.name` instead of `.text` on `ExtractedConcept` — lookup misses all concepts | Use `concept.text` (not `.name`) everywhere an `ExtractedConcept` label is accessed |
| `engagement.mid` and `certainty.mid` fire at 100% across all turns; strategy suppressors/brakes never activate | Haiku drops the `global` section from JSON output because it comes after the variable-length `concepts` section and the model runs out of output attention | Fixed by reordering JSON template/example to put `global` before `concepts` (commit `c1e5a7b`). If the issue recurs with more concepts, consider switching to Sonnet for signal scoring |

## Key Files

| File | Purpose |
|------|---------|
| `src/signals/llm/decorator.py` | `@llm_global_signal` and `@llm_per_concept_signal` decorators; `_registered_llm_signals` registry |
| `src/signals/llm/llm_signal_baseprompt.md` | Base prompt template with placeholders for rubrics, concepts, output format |
| `src/signals/llm/signals/` | One file per signal (`elaboration.py`, `charge.py`, `engagement.py`, `certainty.py`) |
| `src/signals/llm/signals/__init__.py` | `__all__` export list — must include every signal class |
| `src/signals/llm/llm_signal_base.py` | `BaseLLMSignal` base class |
| `src/signals/llm/batch_detector.py` | `LLMBatchDetector` — prompt building, LLM call, parsing, normalisation, and `response_depth` derivation |
| `src/signals/session/llm_response_trend.py` | `response.semantic.llm.engagement.trend` session-level signal |
| `src/services/turn_pipeline/stages/llm_prefetch_stage.py` | Stage 3.1 — fires `LLMBatchDetector.detect()` as `asyncio.Task`, stores on `PipelineContext.llm_signal_task` |
| `src/services/turn_pipeline/stages/llm_signal_bridge_stage.py` | Stage 4.7 — awaits LLM task, routes per-concept ratings to `NodeStateTracker`, passes global signals to Stage 6 |
| `src/services/global_signal_detection_service.py` | Computes `global_response_trend` from rolling history; accepts `llm_global_signals` param (no longer calls LLM itself) |
| `config/methodologies/*.yaml` | `signals: llm:` lists that gate which signals are active |
