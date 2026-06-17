# Signal Migration Contract (Phase A — bead ukyk)

Design contract for migrating from 6 global LLM signals to 2 per-concept signals computed at extraction time. This doc freezes the data shapes, name mappings, derivation formulas, and breaking-change inventory that Phases B–D will implement against.

Source proposal: `docs/drafts/per-concept-signals-proposal.md`.

---

## 1. Signal Migration Table

| Old signal (namespaced)       | Scope  | Values                                  | Destination                                                                 | Notes |
|-------------------------------|--------|-----------------------------------------|-----------------------------------------------------------------------------|-------|
| `llm.response_depth`          | global | `surface` / `shallow` / `moderate` / `deep` | **REMOVED as LLM signal**. Reconstructed post-extraction from per-concept `richness` aggregate. Exposed as `llm.response_depth` (kept name for back-compat) AND as `graph.node.richness` per-node. | See §3 derivation. Value set unchanged so node tracker / `llm_response_trend` / question prompt keep working. |
| `llm.specificity`             | global | 1–5 / `low`/`mid`/`high`                | **REMOVED**. Folded into per-concept `richness`.                            | |
| `llm.valence`                 | global | 1–5 / `low`/`mid`/`high`                | **REMOVED**. Folded into per-concept `charge`.                              | |
| `llm.engagement`              | global | 1–5 / `low`/`mid`/`high`                | **REMOVED**. Folded into per-concept `charge`.                              | |
| `llm.intellectual_engagement` | global | 1–5 / `low`/`mid`/`high`                | **REMOVED**. Folded into per-concept `charge`.                              | |
| `llm.certainty`               | global | 1–5 / `low`/`mid`/`high`                | **KEPT AS-IS** (global).                                                    | Certainty is a speaker-state signal orthogonal to richness/charge; no per-concept version in scope for this migration. |
| `llm.global_response_trend`   | session | `fatigued`/`shallowing`/...            | **KEPT** (session-scoped).                                                  | `LlmResponseTrend.add_response_depth()` continues to consume derived `llm.response_depth` bin (see §3). |

**New signals introduced:**

| New signal                            | Scope       | Values                        | Source              |
|---------------------------------------|-------------|-------------------------------|---------------------|
| `graph.node.richness` (float)         | per-node    | `[0, 1]`                      | mean of extractions |
| `graph.node.richness.low/medium/high` | per-node    | bool                          | threshold bin       |
| `graph.node.charge` (float)           | per-node    | `[-1, 1]`                     | mean of extractions |
| `graph.node.charge.positive/negative` | per-node    | bool                          | threshold bin       |
| `graph.node.has_quality_data`         | per-node    | bool                          | `extraction_count >= 1` |
| `llm.response_depth` (derived)        | global      | `surface/shallow/moderate/deep` | aggregate over current-turn extractions (see §3) |

---

## 2. Per-Concept Data Structure

### 2.1 Extraction output (LLM JSON contract)

Extend existing `ExtractedConcept` shape in `src/domain/models/extraction.py`:

```python
# src/domain/models/extraction.py
class ConceptQuality(BaseModel):
    richness: Literal["low", "medium", "high"]
    charge:   Literal["negative", "neutral", "positive"]

class ExtractedConcept(BaseModel):
    name: str
    type: str
    quality: ConceptQuality   # NEW — required field (no Optional, fail-fast per project conventions)
```

LLM JSON schema adds per-concept `richness` and `charge` strings; extraction service validates against `ConceptQuality`.

### 2.2 Pipeline context

No new top-level `PipelineContext` field. Per-concept quality flows through the existing extraction output and then onto the graph node:

- **Stage 3 (extraction)**: produces `List[ExtractedConcept]` with `quality` attached.
- **Stage 4 (graph update / dedup)**: when an extraction maps to a surface node (new or deduplicated), append `(richness, charge)` to a per-node buffer.
- **Stage 5 (state computation)**: compute aggregated `graph.node.richness` / `graph.node.charge` from buffers and expose via the node signal detectors.

### 2.3 Node-level storage (Pydantic model for `NodeState` extension)

```python
# src/domain/models/node_state.py — NEW fields
class NodeQualityHistory(BaseModel):
    richness_scores: list[float] = Field(default_factory=list)   # 0.0 / 0.5 / 1.0
    charge_scores:   list[float] = Field(default_factory=list)   # -1.0 / 0.0 / 1.0

class NodeState(BaseModel):
    # ... existing fields ...
    quality_history: NodeQualityHistory = Field(default_factory=NodeQualityHistory)
    # `all_response_depths: list[str]` is KEPT for now (used by llm_response_trend + node_opportunity);
    # fed from derived `llm.response_depth` (§3) so downstream consumers are unchanged.
```

### 2.4 Categorical → numeric encoding

| richness | → float | charge    | → float |
|----------|---------|-----------|---------|
| low      | 0.0     | negative  | -1.0    |
| medium   | 0.5     | neutral   |  0.0    |
| high     | 1.0     | positive  | +1.0    |

### 2.5 Threshold bins

- `graph.node.richness.low`    = `richness < 0.34`
- `graph.node.richness.medium` = `0.34 ≤ richness < 0.67`
- `graph.node.richness.high`   = `richness ≥ 0.67`
- `graph.node.charge.negative` = `charge ≤ -0.34`
- `graph.node.charge.positive` = `charge ≥ 0.34`
- Neutral band (`|charge| < 0.34`) emits neither positive nor negative bin (matches existing "missing signal = 0 contribution" pattern in `scoring.py:101-106`).

---

## 3. `response_depth` Derivation Formula

Downstream consumers that must keep working unchanged:

- `src/signals/session/llm_response_trend.py:45` — `add_response_depth(depth: str)`
- `src/signals/meta/node_opportunity.py:202` — `_get_response_depth(context)`
- `src/signals/graph/node_base.py:95`, `graph_signals.py:408` — read `state.all_response_depths`
- `src/llm/prompts/question.py:257` — reads `signals["llm.response_depth"]`

These expect string bins `surface` / `shallow` / `moderate` / `deep`.

**Derivation (per turn, computed in Stage 5 after dedup, before Stage 6 signal detection):**

1. Collect all `richness_scores` produced in the current turn across every extracted concept: `R_turn = [r1, r2, ..., rn]` (`ri ∈ {0.0, 0.5, 1.0}`).
2. If `len(R_turn) == 0` → `llm.response_depth = "surface"` (no extractions = no new information).
3. Otherwise compute `r_mean = mean(R_turn)` and `n = len(R_turn)`.
4. Bin:
   - `n == 1 and r_mean ≤ 0.25` → `surface`
   - `r_mean < 0.34` → `shallow`
   - `r_mean < 0.67` → `moderate`
   - `r_mean ≥ 0.67` → `deep`

Rationale: `surface` previously meant "no substance". Our closest analog is "only one concept, and it was rated low-richness" — which captures one-word / terse responses that yield at most one shallow extraction. Above that, mean richness maps monotonically to shallow/moderate/deep, preserving the 4-level semantics that `LlmResponseTrend` and node-tracker rely on.

The derived value is populated into `context.current_turn_global_signals["llm.response_depth"]` so existing reader code paths are untouched.

---

## 4. YAML Weight Migration Plan

Rewrite rules applied uniformly. Source signal → target signal(s). When a rule produces two weights, split as indicated; keep total magnitude similar to original.

### 4.1 Global rewrite rules

| Old weight key                        | New weight key(s)                                                              | Split rule |
|---------------------------------------|--------------------------------------------------------------------------------|------------|
| `llm.response_depth.deep`             | `graph.node.richness.high`                                                     | 1:1 weight |
| `llm.response_depth.moderate`         | `graph.node.richness.medium`                                                   | 1:1 weight |
| `llm.response_depth.shallow`          | `graph.node.richness.low`                                                      | 1:1 weight (sign flipped if original was penalty) |
| `llm.response_depth.surface`          | `graph.node.richness.low`                                                      | 1:1 weight |
| `llm.specificity.high`                | `graph.node.richness.high`                                                     | 1:1 weight (additive with any response_depth.high already mapped — combine by sum) |
| `llm.specificity.mid`                 | `graph.node.richness.medium`                                                   | 1:1 |
| `llm.specificity.low`                 | `graph.node.richness.low`                                                      | 1:1 |
| `llm.valence.high` (positive)         | `graph.node.charge.positive`                                                   | 1:1 |
| `llm.valence.low` (negative)          | `graph.node.charge.negative`                                                   | 1:1 |
| `llm.valence.mid`                     | dropped (neutral band contributes 0)                                           | — |
| `llm.engagement.high`                 | `graph.node.charge.positive` (0.5×)  +  `graph.node.richness.high` (0.5×)      | engagement ≈ richness + positive charge |
| `llm.engagement.mid`                  | dropped (neutral band)                                                         | — |
| `llm.engagement.low`                  | `graph.node.charge.negative` (0.5×)  +  `graph.node.richness.low` (0.5×)       | disengagement = low richness + negative charge |
| `llm.intellectual_engagement.high`    | `graph.node.richness.high` (0.5×) + `graph.node.charge.positive` (0.5×)        | |
| `llm.intellectual_engagement.mid`     | `graph.node.richness.medium`                                                   | |
| `llm.intellectual_engagement.low`     | `graph.node.richness.low` (0.5×) + `graph.node.charge.negative` (0.5×)         | |
| `llm.certainty.*`                     | UNCHANGED — keep as global `llm.certainty.*`                                   | — |
| `llm.global_response_trend.*`         | UNCHANGED — keep as global                                                     | — |

Per-strategy sanity overrides called out in the proposal (e.g. ascend gets `charge.negative: -0.4` because laddering from negative nodes is counterproductive) will be applied during Phase D tuning, not by the mechanical rewrite.

### 4.2 Per-YAML inventory

Files, total rewrite counts (based on grep in §5). Legacy configs under `config/methodologies/legacy/` are **out of scope** (kept frozen).

| YAML                                                       | Signals-pool decls to drop | Weight entries to rewrite |
|------------------------------------------------------------|----------------------------|---------------------------|
| `config/methodologies/means_end_chain_v2_strict.yaml`      | 5 (`response_depth`, `valence`, `specificity`, `engagement`, `intellectual_engagement`) | ~20 |
| `config/methodologies/means_end_chain_v2_flex.yaml`        | 5 | ~14 |
| `config/methodologies/jobs_to_be_done_v2.yaml`             | 5 | ~18 |
| `config/methodologies/critical_incident_v2.yaml`           | 5 | ~15 |
| `config/methodologies/customer_journey_mapping_v2.yaml`    | 5 | TBD (confirm in Phase B) |
| `config/methodologies/repertory_grid_v2.yaml`              | 5 | ~35 |

Signals-pool declaration block to delete in every file (signals_pool.llm):
```yaml
    - llm.response_depth
    - llm.valence
    - llm.specificity
    - llm.engagement
    - llm.intellectual_engagement
```
Keep `- llm.certainty` and global_response_trend line intact.

Signals-pool declaration block to add (graph):
```yaml
    - graph.node.richness
    - graph.node.charge
    - graph.node.has_quality_data
```

---

## 5. Breaking-Change Inventory

Files referencing old global LLM signal names (`response_depth`, `specificity`, `valence`, `engagement`, `intellectual_engagement`):

**Signal definition + detection (to be removed or restructured in Phase B):**
- `src/signals/llm/signals/depth.py`               — DELETE
- `src/signals/llm/signals/specificity.py`         — DELETE
- `src/signals/llm/signals/valence.py`             — DELETE
- `src/signals/llm/signals/engagement.py`          — DELETE
- `src/signals/llm/signals/intellectual_engagement.py` — DELETE
- `src/signals/llm/signals/certainty.py`           — KEEP
- `src/signals/llm/signals/__init__.py`            — prune exports
- `src/signals/llm/batch_detector.py`              — remove 5 signals from batch, add derived-response_depth emitter
- `src/signals/llm/decorator.py`                   — touch only if example uses removed signal
- `src/signals/llm/llm_signal_base.py`             — touch only if base references removed signals
- `src/signals/llm/prompts/signals.md`             — drop 5 rubric entries (keep certainty)
- `src/signals/llm/prompts/output_example.json`    — update example

**Extraction (new fields in Phase B):**
- `src/services/extraction_service.py`             — emit `quality` per concept
- `src/domain/models/extraction.py`                — add `ConceptQuality` + field on `ExtractedConcept`
- `src/llm/prompts/` (extraction prompt files)     — add richness/charge instructions to prompt

**Graph & node state (new derived signals in Phase C):**
- `src/signals/graph/graph_signals.py`             — add richness / charge node signals
- `src/signals/graph/node_base.py`                 — may need helper for quality_history aggregation
- `src/services/node_state_tracker.py`             — populate `quality_history` on graph update
- `src/services/turn_pipeline/stages/state_computation_stage.py` — compute per-node richness/charge means + derived `llm.response_depth`
- `src/domain/models/node_state.py`                — add `quality_history`
- `src/signals/session/llm_response_trend.py`      — unchanged (still reads derived `llm.response_depth`)

**Scoring & routing (assertions to update):**
- `src/methodologies/scoring.py`                   — no code change expected; verify weight lookup passes for new graph.node.* keys
- `src/methodologies/registry.py`                  — update allow-list / signal-name validation
- `src/services/methodology_strategy_service.py`   — remove references to dropped signal names in logs/asserts
- `src/services/turn_pipeline/stages/strategy_selection_stage.py` — remove dropped signal names in logs/asserts
- `src/services/global_signal_detection_service.py`— stop batching dropped 4 signals; keep certainty + derived `llm.response_depth`
- `src/services/session_service.py`                — any log formatter references
- `src/signals/meta/node_opportunity.py`           — unchanged (reads `llm.response_depth` via context; derived value is drop-in)

**Config / questions (light touch):**
- `src/core/config.py`                             — docstring mentions `response_depth, engagement` (line 321); update
- `src/llm/prompts/question.py`                    — references `signals["llm.response_depth"]`; no change needed (derived value is drop-in)

**YAMLs (per §4.2):**
- 6 active `config/methodologies/*_v2*.yaml` files

**Tests:**
- Phase B will update fixtures under `tests/` that build synthetic signal dicts containing the removed keys. Full test-file inventory deferred to Phase B (out of scope for this design doc per acceptance criteria).

---

## 6. Out of Scope / Deferred

- **Mentioned-but-not-extracted concepts.** Proposal open question #1. Accepted for this migration: quality updates only on extraction events. Revisit after Phase D simulations.
- **Novelty as a third dimension.** Proposal open question #2. Not included.
- **Fallback path for legacy global signals during transition.** Proposal open question #3. We commit to a hard cutover — no dual path. Legacy YAMLs frozen under `config/methodologies/legacy/` remain readable by the registry only if they are never loaded at runtime.
- **5-level charge scale.** Proposal open question #5. Rejected for v1; 3-level keeps extraction prompt simple.

---

---

# Section B — Batch Detector & Decorator Design (Phase B-plan, bead 7p6s)

Resolves four design questions before Phase B-impl (bead ymom) writes code.

## B.0 Reconciliation with Phase A

Epic `zltr` and `docs/drafts/rating_prompt_revised.md` are the authoritative source. They use **`elaboration`** (not `richness`) and keep **`engagement`** as a global signal (not folded into charge). Phase A §1 predates the revised prompt. Apply these corrections to §1–§4 before Phase B-impl:

| Phase A (ukyk) wrote       | Corrected (per epic + revised prompt)                            |
|----------------------------|-------------------------------------------------------------------|
| `graph.node.richness`      | `graph.node.elaboration`                                          |
| `ConceptQuality.richness`  | `ConceptQuality.elaboration`                                      |
| `NodeQualityHistory.richness_scores` | `NodeQualityHistory.elaboration_scores`                 |
| `llm.engagement` → split   | `llm.engagement` **KEPT AS GLOBAL** (1–5 scale, like certainty)  |
| `llm.intellectual_engagement` → split across richness + charge | Folded **entirely into per-concept `elaboration`** (richness aspect; proposal §2 table) |

Net new-signal inventory after correction: 2 per-concept (`elaboration`, `charge`), 2 global (`engagement`, `certainty`). Six old signals retired: `response_depth` (→ derived), `specificity`, `valence`, `intellectual_engagement`, plus the old per-scalar `engagement` and `certainty` classes (replaced by new files with embedded rubrics).

The `response_depth` derivation formula in §3 stands, with one rename: source = per-concept `elaboration_scores`, not `richness_scores`.

---

## B.1 Design Q1 — How does `batch_detector.detect()` return per-concept + global data?

**Decision:** single return type, nested dict. Two top-level keys: `"concepts"` and `"global"`. Namespaced downstream.

```python
# return type of LLMBatchDetector.detect(...)
BatchSignalResult = dict[str, Any]
# shape:
{
    "concepts": {
        "<concept_name>": {
            "llm.elaboration": 0.5,    # normalized float [0,1]   (raw 1–5)
            "llm.charge":      0.75,   # normalized float [0,1]   (raw 1–5, centred-friendly)
        },
        ...
    },
    "global": {
        "llm.engagement":    0.5,       # normalized [0,1]
        "llm.certainty":     0.75,      # normalized [0,1]
        "llm.response_depth": "moderate",   # derived categorical (see §3)
    },
}
```

**Rationale:**
- Single call site, single return value — existing `GlobalSignalDetectionService.detect()` callers read `["global"]` and are equivalent to the current flat dict after a shallow key rewrite.
- `["concepts"]` is consumed only by Stage 4 (graph update) when appending to per-node `quality_history`; not read by the scoring engine.
- Derived `llm.response_depth` is computed inside `batch_detector.detect()` *after* parsing, so downstream code (`llm_response_trend`, `node_opportunity`, `question.py`) receives it via the normal `["global"]` path unchanged.
- Charge normalization: raw score 1→0.0, 3→0.5, 5→1.0. Strategy weights that want "negative" bin consume a **derived threshold signal** produced by the graph node aggregator (§2.5), not the raw normalized value.

**Inputs to `detect()`:**

```python
async def detect(
    self,
    response_text: str,
    question: str,
    concepts: list[ExtractionConcept],      # NEW — required
    signal_classes: list[Type[BaseLLMSignal]] | None = None,
) -> BatchSignalResult:
```

`ExtractionConcept` is the Phase B-impl payload carrying `name` + `source_quote(s)`. `concepts` is required; fail-fast if empty (extraction must have produced at least one concept for batch detection to run).

**Missing-concept fallback** (prompt rule 6 in revised prompt): LLM is instructed to return `elaboration=1, charge=3` for any concept absent from the response text. Batch detector does not retry or repair; the prompt + structured JSON guarantee coverage.

**Key-absence handling** (preserves existing cu72.1 semantics): if a required global key is missing from the LLM JSON, log a warning and substitute `{"score": 3, "rationale": "fallback: key absent"}`. If a concept key is missing, apply the same fallback with `elaboration=1, charge=3` (neutral) per the prompt contract.

---

## B.2 Design Q2 — Does `@llm_signal` extend to multi-output, or does per-concept stay outside the decorator?

**Decision:** split the decorator into two distinct decorators. Per-concept handling is **not** crammed into the existing `@llm_signal`.

```python
# src/signals/llm/decorator.py

def llm_global_signal(
    signal_name: str,            # e.g. "llm.engagement"
    description: str,
) -> Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]]:
    """Class decorator for response-level signals (one scalar per response)."""

def llm_per_concept_signal(
    signal_name: str,            # e.g. "llm.elaboration"
    description: str,
) -> Callable[[Type[BaseLLMSignal]], Type[BaseLLMSignal]]:
    """Class decorator for per-concept signals (one scalar per concept)."""
```

Both register into the same `_registered_llm_signals` dict but additionally set a class attribute `scope: Literal["global", "per_concept"]`. `batch_detector.detect()` partitions registered classes by `scope` to build the prompt's two sections and to route parsed output into the `["concepts"]` / `["global"]` return buckets.

**Rationale:**
- A single `multi_output` flag on `@llm_signal` would force every call site and every downstream consumer to handle both cases. Two decorators give `batch_detector` a clean type partition and keep per-concept consumers (Stage 4 graph update) from accidentally treating a global signal as per-concept.
- The per-concept signal class still produces one *logical* rating dimension — the multiplicity comes from concept count, which is a runtime input, not a class property. So the decorator doesn't need to know the list of concepts.
- `_analyze_with_llm` remains a `NotImplementedError` stub on both — batch detector owns LLM I/O.

**Rubric exposure:** both decorators read `cls.RUBRIC` (see B.3), not a shared `signals.md`. The decorator validates at import time that `cls.RUBRIC` is a non-empty string.

---

## B.3 Design Q3 — Rubric format inside signal `.py` files

**Decision:** **class-level `RUBRIC: str` constant**, consumed by `batch_detector._build_prompt` via `cls.RUBRIC`.

Canonical shape:

```python
# src/signals/llm/signals/elaboration.py
from src.signals.llm.decorator import llm_per_concept_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_per_concept_signal(
    signal_name="llm.elaboration",
    description="Substantive content produced about a specific concept (1-5).",
)
class ElaborationSignal(BaseLLMSignal):
    RUBRIC: str = """\
How much substantive content did the respondent produce about THIS concept? Score content amount and quality, not word count.

1 = Bare mention. Named without substance. No elaboration, context, or detail.
2 = Brief reference. One attribute, a simple fact, or a single reason. Thin.
3 = Moderate. Specifics provided: a reason, comparison, brief anecdote, or causal link.
    Enough to understand what the respondent means.
4 = Detailed. Concrete examples, reasoning chains, or situational detail.
    Explains the what AND the why/how.
5 = Rich. Multiple angles, real-time insight, unexpected connections,
    or a pivot revealing deeper meaning.

Score substance, not length. A terse answer can score high.
"""
```

**Rules (enforced by the decorator at import time):**
1. `RUBRIC` MUST be a non-empty `str` class attribute. Fail-fast `ValueError` if absent.
2. Rubric text MUST include the five numbered bands `1 =`…`5 =`. Enforcement is a simple regex check in the decorator; if missing, raise `ValueError` with the signal name.
3. Rubric is pure prose + band table — no format placeholders, no interpolation. The base prompt template owns `{question}`, `{response}`, `{concepts}` substitution (see B.4).
4. The four new files each own exactly one `RUBRIC`: `elaboration.py`, `charge.py`, `engagement.py`, `certainty.py`. Verbatim band text comes from `docs/drafts/rating_prompt_revised.md` §signals.md.

**Why a class constant (not a classmethod, docstring, or module-level `RUBRIC = ...`):**
- Class-attribute access (`cls.RUBRIC`) makes subclassing / overrides trivial if a future concept-family rubric variant appears.
- Docstrings are stripped under `python -O`; class constants are not. Runtime prompt construction must be deterministic.
- Classmethod is unnecessary indirection — the rubric is static text, no computation.

---

## B.4 Design Q4 — `llm_signal_baseprompt.md` template structure

**Decision:** a single file alongside `batch_detector.py`, with three placeholders plus slots that the batch detector fills with per-signal rubrics and the output example.

**Location:** `src/signals/llm/llm_signal_baseprompt.md` (NOT inside a `prompts/` folder — the old folder is deleted).

**Placeholders filled by `batch_detector._build_prompt`:**

| Placeholder              | Source                                                 |
|--------------------------|--------------------------------------------------------|
| `{question}`             | `question` argument to `detect()`                      |
| `{response}`             | `response_text` argument to `detect()`                 |
| `{concepts}`             | rendered list of `name + source_quote(s)` from `concepts` argument |
| `{per_concept_rubrics}`  | concatenation of `cls.RUBRIC` for every registered per-concept signal class |
| `{global_rubrics}`       | concatenation of `cls.RUBRIC` for every registered global signal class |
| `{output_format}`        | static JSON schema block (embedded constant, see below) |
| `{output_example}`       | static JSON example (embedded constant, see below)      |

**Template skeleton** (to be written verbatim from revised prompt §high_level.md plus section headers; the content below is the skeleton, not the final text):

```markdown
You are a qualitative research analyst evaluating a respondent's answer in a structured interview.

You receive:
1. The question asked
2. The respondent's answer
3. A list of concepts extracted from the answer, each with supporting quote(s)

Your task:
- Rate EACH concept on: {per_concept_signal_names}
- Rate the response overall on: {global_signal_names}

[critical rules block — verbatim from revised prompt]

**Interview context:**
- Question asked: {question}
- Respondent's answer: {response}
- Extracted concepts: {concepts}

---

## PER-CONCEPT DIMENSIONS

{per_concept_rubrics}

---

## GLOBAL DIMENSIONS

{global_rubrics}

---

## OUTPUT FORMAT

{output_format}

## EXAMPLE

{output_example}
```

**Embedded JSON example & output format** live as module-level string constants in `batch_detector.py` (not separate files), per epic directive "output example embedded in batch_detector.py or as a small static constant". Rationale: one canonical location, deletable with the batch detector if the design is ever re-platformed; avoids fragmenting the prompt across a file + folder.

**Size discipline:** response and question continue to truncate at 500 / 200 chars (existing behavior). Concept source quotes truncate at 200 chars each; concept list capped at the count produced by extraction for that turn (no separate cap).

---

## B.5 Artifacts produced by Phase B-impl (bead ymom), derived from this spec

1. Delete: `src/signals/llm/prompts/` (3 files).
2. Create: `src/signals/llm/llm_signal_baseprompt.md` (template per B.4).
3. Create: `src/signals/llm/signals/elaboration.py`, `charge.py`, `engagement.py`, `certainty.py` — each with `RUBRIC` constant + appropriate decorator (B.2, B.3).
4. Delete: `depth.py`, `specificity.py`, `valence.py`, `intellectual_engagement.py`, and the old `engagement.py` / `certainty.py` (replaced, not edited in place, to avoid rubric-in-docstring leftovers).
5. Update: `src/signals/llm/signals/__init__.py` — export the 4 new classes only.
6. Rewrite: `src/signals/llm/batch_detector.py` — new signature (B.1), partition by `scope`, nested return, derived `llm.response_depth`, embedded output example + format.
7. Rewrite: `src/signals/llm/decorator.py` — two decorators (B.2), `RUBRIC` validation at import time, deletion of `_parse_signals_rubrics` and `_load_output_example` helpers.

Pre-plan review gate (per CLARITY REVIEW issue 2): bead ymom's acceptance criteria should include a check box "Section B of docs/drafts/signal-migration-contract.md reviewed; elaboration/charge/engagement/certainty naming confirmed against epic zltr".

---

## 7. Acceptance Checklist (traces to bead acceptance criteria)

- [x] Migration table covers all 6 old signals with clear destinations — §1
- [x] Per-concept data structure defined as Pydantic model — §2.1, §2.3 (`ConceptQuality`, `NodeQualityHistory`)
- [x] `response_depth` derivation formula specified — §3
- [x] All 6 YAML weight migration plans documented — §4 (rewrite rules + per-file inventory)
- [x] Full list of files referencing old signal names produced — §5

---

# Section C — Per-Concept → Node-Scoped Routing (Phase C-plan, bead 4540)

Resolves the routing question left open by Phases A/B: per-concept LLM ratings are **concept-scoped** (key = concept name), but strategy scoring consumes **node-scoped** signals (key = `graph.node.*`, partitioned by prefix in `scoring.partition_signal_weights`). This section freezes the mapping, call sites, and contract extensions so bead `f965` (Phase C-impl) can wire them without re-deriving constraints.

## C.0 Decision summary

**Chosen routing: Option A — project per-concept ratings onto node ids in Stage 6 via the Stage 4 `label_to_node` map, then aggregate into `graph.node.elaboration` / `graph.node.charge` signals.** Rejected alternatives and rationale:

| Option | Sketch | Why rejected |
|--------|--------|--------------|
| **A (chosen)** | Append per-concept ratings to `NodeStateTracker.quality_history`, emit `graph.node.elaboration.*` / `graph.node.charge.*` via existing node-signal pipeline | Reuses `NODE_SIGNAL_PREFIXES` routing (zero change to `partition_signal_weights`). YAML rewrites in §4 already use `graph.node.*` keys. Matches Section A §2.3 plan. |
| B | New `llm.concept.<concept_name>.*` namespace threaded through scoring | Concept names aren't stable identifiers — they rename via dedup. Would require a new prefix constant, new partition branch, new scoring code path. |
| C | Store per-concept dict on `PipelineContext`, inject at scoring time outside the signal dict | Breaks single-responsibility of `score_strategy`; creates a second, parallel input to scoring; every YAML rewrite becomes bespoke. |

Every per-concept signal becomes a per-node signal via a **single bridge step** in Stage 6. No new prefixes, no new scoring paths.

---

## C.1 Concept → node id bridge

### C.1.1 Source of truth

`GraphService.add_extraction_to_graph()` already builds (graph_service.py:107):

```python
label_to_node: dict[str, KGNode] = {}
for concept in extraction.concepts:
    node = await self._add_or_get_node(session_id, concept, utterance_id)
    if node:
        label_to_node[concept.text.lower()] = node
```

This dict is the **authoritative concept-text → resolved-node-id map for the turn**. It accounts for:
- Exact-label dedup (Stage 1 of node dedup)
- Semantic-similarity dedup (Stage 2, threshold 0.80)
- New-node creation (Stage 3)

`concept.text` values in this turn's extraction are **guaranteed** to be keys in `label_to_node` (if the concept was extractable; non-extractable concepts short-circuit on line 95 before map population).

### C.1.2 Persisting the map to Stage 6

Add one field to `PipelineContext` (not to `ExtractionOutput` — the map is a turn-lifecycle artifact, not an extraction-model property):

```python
# src/services/turn_pipeline/context.py
class PipelineContext(BaseModel):
    # ... existing fields ...
    concept_to_node_id: Dict[str, str] = Field(default_factory=dict)
    """Lowercased concept text -> resolved KGNode.id for this turn's extraction.
    Populated in Stage 4 (graph_update). Consumed in Stage 6 to route
    per-concept LLM ratings to node-scoped quality_history."""
```

`GraphUpdateStage` writes it after `add_extraction_to_graph` returns, deriving the mapping from `added_nodes` + the extraction's concept list (re-using `concept.text.lower()` as the key — same key function as `GraphService`).

### C.1.3 Invariants (fail-fast checks in Stage 6)

Before using the map, `strategy_selection_stage` MUST assert:

1. Every `concept.text.lower()` in `context.extraction_output.extraction.concepts` is present as a key in `context.concept_to_node_id`. Violation → `PipelineContractError` naming the missing concept.
2. Every value is a non-empty string. Violation → same.

These invariants are cheap and catch the exact class of silent-drift bugs that bit bead 119q (stage-ordering mismatches yielding empty signal sets).

---

## C.2 End-to-end data flow

Stage-by-stage, with the concrete artifact moving between stages:

```
Stage 3 extraction
   └─ produces: ExtractionOutput.extraction.concepts: list[ExtractedConcept]
        (each carries .text, .node_type, .source_quote)

Stage 4 graph_update
   ├─ runs GraphService.add_extraction_to_graph()
   ├─ builds label_to_node internally
   └─ NEW: writes context.concept_to_node_id = {c.text.lower(): node.id}

Stage 4.5 slot_discovery     (unchanged; reads graph, not concept map)
Stage 5 state_computation    (unchanged; graph-metric recompute)

Stage 6 strategy_selection
   │
   ├─ GlobalSignalDetectionService.detect()
   │    │
   │    └─ LLMBatchDetector.detect(
   │           response_text,
   │           question=last_question,
   │           concepts=context.extraction_output.extraction.concepts,  # NEW arg
   │       )
   │       returns: {"concepts": {name: {llm.elaboration, llm.charge}}, "global": {...}}
   │
   ├─ NEW bridge step (in strategy_selection_stage, BEFORE node-signal detection):
   │    for concept_name, ratings in batch_result["concepts"].items():
   │        node_id = context.concept_to_node_id[concept_name.lower()]
   │        node_state_tracker.append_quality(
   │            node_id,
   │            elaboration=ratings["llm.elaboration"],
   │            charge=ratings["llm.charge"],
   │        )
   │
   ├─ NodeSignalDetectionService.detect()
   │    └─ reads NodeState.quality_history per node, emits
   │       graph.node.elaboration (float mean), graph.node.elaboration.{low,medium,high} (bool),
   │       graph.node.charge (float mean), graph.node.charge.{positive,negative} (bool),
   │       graph.node.has_quality_data (bool, extraction_count >= 1)
   │
   ├─ global_signals merges batch_result["global"] (elaboration-derived response_depth + engagement + certainty)
   │    and existing session-scoped signals (llm.global_response_trend, temporal.*, meta.*)
   │
   └─ rank_strategy_node_pairs(strategies, node_signals, global_signals)
        uses partition_signal_weights — graph.node.* -> node_weights, rest -> strategy_weights
        (no change to scoring.py)
```

**Key observation:** the bridge step lives in `strategy_selection_stage` (or a helper on `GlobalSignalDetectionService`), NOT in Stage 4. It must run **after** `LLMBatchDetector.detect()` and **before** `NodeSignalDetectionService.detect()`. This is the only ordering constraint added by this migration.

---

## C.3 Contract & service signature changes

### C.3.1 `PipelineContext` (src/services/turn_pipeline/context.py)

Add:
```python
concept_to_node_id: Dict[str, str] = Field(default_factory=dict)
```

### C.3.2 `NodeStateTracker` (src/services/node_state_tracker.py)

Replace / supplement the existing `append_response_signal(node_id, depth: str)` method. Two new responsibilities:

```python
def append_quality(
    self,
    node_id: str,
    elaboration: float,   # normalized [0, 1]
    charge: float,        # normalized [0, 1]; threshold bins applied downstream
) -> None:
    """Append one per-concept rating to NodeState.quality_history."""
```

`append_response_signal` is **retained** for back-compat with the derived `llm.response_depth` path (see C.5). It now wraps the elaboration append: internal callers bin the float back to `surface/shallow/moderate/deep` only when populating `NodeState.all_response_depths`, which feeds `graph.node.shallow_response_ratio` and `llm_response_trend`.

Prefer the **derived** wrapper: Stage 6 bridge only calls `append_quality`; the tracker itself derives the categorical depth from the elaboration float using §3's formula (applied per-concept) and pushes it into `all_response_depths`. This collapses two update paths into one.

### C.3.3 `GlobalSignalDetectionService.detect()` (src/services/global_signal_detection_service.py)

Signature unchanged externally, but it must now:

1. Read `concepts = context.extraction_output.extraction.concepts` and pass them to the underlying `LLMBatchDetector.detect(..., concepts=concepts)` (Section B.1 signature).
2. Return the **global** dict only from this service's public API: `return batch_result["global"] | {"llm.global_response_trend": trend}`. The per-concept payload is threaded separately — see C.3.4.

### C.3.4 New helper on `GlobalSignalDetectionService` OR a new small service

Two options. Prefer **(a)** for minimal surface area:

**(a) Extend service with a second method:**
```python
async def detect_with_per_concept(
    self, methodology_name, context, graph_state, response_text
) -> tuple[Dict[str, Any], Dict[str, Dict[str, float]]]:
    """Returns (global_signals, per_concept_signals)."""
```
`strategy_selection_stage` calls `detect_with_per_concept`; the existing `detect()` method becomes a thin wrapper that drops the second tuple element for callers that only need globals.

**(b)** Create `PerConceptSignalService` owning the batch detector. Duplicates LLM-client setup. Rejected for now.

### C.3.5 `strategy_selection_stage.py` — bridge step

Append between global-signal detection and node-signal detection:

```python
global_signals, per_concept = await global_signal_service.detect_with_per_concept(
    methodology_name, context, graph_state, response_text
)

# Bridge: per-concept -> per-node quality history
for concept_name, ratings in per_concept.items():
    key = concept_name.lower()
    if key not in context.concept_to_node_id:
        raise PipelineContractError(
            f"per-concept rating for '{concept_name}' has no node mapping "
            f"(extraction and graph_update disagree)"
        )
    node_state_tracker.append_quality(
        node_id=context.concept_to_node_id[key],
        elaboration=ratings["llm.elaboration"],
        charge=ratings["llm.charge"],
    )

node_signals = await node_signal_service.detect(...)  # existing call, unchanged
```

### C.3.6 `pipeline_contracts.py` deltas

- `StrategySelectionInput`: no change (still receives context + graph_state).
- `StrategySelectionOutput`: no change.
- New: document `concept_to_node_id` on the pipeline contract doc (`.claude/context/pipeline-contracts.md`) as a Stage 4 output / Stage 6 input.

No Pydantic model changes are forced by the routing itself — only the new `PipelineContext` field. `NodeQualityHistory` (Section A §2.3) remains the per-node storage model.

---

## C.4 YAML weight migration rules (extending §4 with per-file inventory)

Section §4.1 froze the **global** rewrite rules (old key → new key). Section C.4 adds the per-file application procedure and the validation gate.

### C.4.1 Application procedure (applied to every v2 YAML in §4.2)

For each file:

1. In the `signals_pool.llm` block, delete the 5 old signal lines listed in §4 ("block to delete"). Keep `- llm.certainty` and `- llm.global_response_trend`. **Add** `- llm.engagement` (kept as global per B.0).
2. In the `signals_pool.graph` block, append the three new per-node signal names from §4 ("block to add"): `- graph.node.elaboration`, `- graph.node.charge`, `- graph.node.has_quality_data`. (Rename: `richness` → `elaboration` per B.0 reconciliation.)
3. For each strategy's `signal_weights`:
   a. Apply every matching row of the §4.1 table. If a rule produces two keys (e.g. `engagement.high` → charge + elaboration), emit two entries.
   b. If both a §4.1 rule and an existing `graph.node.*` entry target the same key, **sum the weights** (do not pick max).
   c. Round to 2 decimals.
   d. Preserve sign (penalty remains penalty).
4. Apply the elaboration/richness rename **globally** (§4 was written with `richness`; §B.0 renames it): every `graph.node.richness*` key in the generated output becomes `graph.node.elaboration*`.
5. For any `phase_bonuses` block, apply the same key-rename rules. Phase bonuses referencing dropped signals (`llm.specificity`, `llm.valence`, `llm.intellectual_engagement`) are dropped; phase bonuses on `llm.engagement` are **kept** (engagement is still global).

### C.4.2 Per-file counts (authoritative list for Phase C-impl)

| YAML                                                    | Drop from llm-pool | Add to graph-pool | Add to llm-pool | Weight rows to rewrite |
|---------------------------------------------------------|--------------------|-------------------|-----------------|------------------------|
| `means_end_chain_v2_strict.yaml`                        | 4 (`response_depth`, `valence`, `specificity`, `intellectual_engagement`) | 3                 | 1 (`engagement`)¹ | ~20                    |
| `means_end_chain_v2_flex.yaml`                          | 4                  | 3                 | 1¹              | ~14                    |
| `jobs_to_be_done_v2.yaml`                               | 4                  | 3                 | 1¹              | ~18                    |
| `critical_incident_v2.yaml`                             | 4                  | 3                 | 1¹              | ~15                    |
| `customer_journey_mapping_v2.yaml`                      | 4                  | 3                 | 1¹              | audit-first²           |
| `repertory_grid_v2.yaml`                                | 4                  | 3                 | 1¹              | ~35                    |

¹ Only add `- llm.engagement` if it was in the old pool. If a methodology never declared engagement, don't add it.
² `customer_journey_mapping_v2` was marked TBD in §4.2; Phase C-impl must grep the file and list the rewrite count before editing, then confirm the plan with the spec before applying.

### C.4.3 Validation gate (hard requirement before commit)

Phase C-impl runs, in order:

1. `uv run python -c "from src.methodologies.registry import get_registry; r = get_registry(); [r.get_methodology(m) for m in r.list_methodologies()]"` — all 6 YAMLs must load without `ConfigurationError`.
2. `uv run python scripts/check_doc_drift.py` — no new drift warnings.
3. `uv run pytest tests/methodologies/ tests/signals/` — must pass.
4. `ruff check .` — zero new warnings.

Any failure halts the bead; the YAMLs are reverted and the migration plan is revisited.

---

## C.5 `response_depth` derivation for node-tracker compatibility

Section §3 defined the turn-level aggregation. Section C.5 specifies how the same mechanism feeds the **per-node** `all_response_depths` list that `llm_response_trend` and `graph.node.shallow_response_ratio` depend on.

### C.5.1 Per-node derivation

When the bridge step (C.3.5) calls `node_state_tracker.append_quality(node_id, elaboration, charge)`:

1. The tracker bins `elaboration` (a normalized float in `[0, 1]`) to the categorical `surface/shallow/moderate/deep` using the **single-concept** variant of §3:
   - `elaboration < 0.125`        → `surface`   (covers raw score = 1 after normalization 0.0)
   - `0.125 ≤ elaboration < 0.375` → `shallow`  (raw score ≈ 2)
   - `0.375 ≤ elaboration < 0.625` → `moderate` (raw score ≈ 3)
   - `elaboration ≥ 0.625`         → `deep`     (raw scores 4–5)
2. The resulting string is appended to `NodeState.all_response_depths`.
3. `NodeState.quality_history.elaboration_scores.append(elaboration)` and `.charge_scores.append(charge)` also fire.

Cutpoints above are derived by mapping the raw 1–5 band midpoints through `(score-1)/4`: 0.0, 0.25, 0.5, 0.75, 1.0 — cutpoints sit halfway between consecutive bands (0.125, 0.375, 0.625).

### C.5.2 Turn-level derivation (for `llm_response_trend` and question-prompt reader)

Batch detector already emits `global_out["llm.response_depth"]` via `_score_to_category(mean, n)` (batch_detector.py:266). This matches §3 verbatim. No change required for `llm_response_trend` — it reads `llm.response_depth` from the global dict.

### C.5.3 `graph.node.shallow_response_ratio`

Existing computation: `count(d in all_response_depths if d in {"surface", "shallow"}) / len(all_response_depths)`. Unchanged — per C.5.1 `all_response_depths` is still populated.

### C.5.4 Cross-check

After C.5 is implemented, the two representations should be **consistent by construction**:

| Signal                                | Source                                   | Consumed by                        |
|---------------------------------------|------------------------------------------|------------------------------------|
| `llm.response_depth` (turn, categorical) | Batch detector mean → §3 bins            | `question.py`, `llm_response_trend`|
| `all_response_depths` (per-node list) | Per-concept binning (C.5.1)              | `graph.node.shallow_response_ratio`, node-level signals |
| `graph.node.elaboration` (per-node float) | `mean(quality_history.elaboration_scores)` | New YAML weights |
| `graph.node.charge` (per-node float)  | `mean(quality_history.charge_scores)`    | New YAML weights |

No single signal is derived through two different code paths — each has one owner.

---

## C.6 Edge cases and invariants

1. **Concept-with-no-matching-node.** Cannot happen: Section C.1.1 invariant holds by virtue of `GraphService` building `label_to_node` for exactly the concepts it received. Fail-fast in the bridge step catches implementation regressions.
2. **Semantic dedup collapses two concepts onto one node.** `label_to_node` maps BOTH concept texts to the same `node.id`. The bridge step appends BOTH ratings to the same node's `quality_history` — this is correct: two mentions of the same concept contribute two samples to the mean.
3. **Cross-turn node referenced in new extraction.** `label_to_node` at Stage 4 line 122–128 also populates cross-turn nodes. A concept extracted this turn that resolves to a previously-created node still routes correctly: the rating appends to that existing node's `quality_history`.
4. **No extractable concepts this turn.** `extraction.is_extractable == False` → Stage 4 returns early, `concept_to_node_id` stays empty, batch detector is NOT called (ValueError per B.1). `global_signals` defaults to neutral values, `llm.response_depth = "surface"`, node signals emit zeroed floats. Strategy scoring proceeds with degraded but valid input.
5. **Extraction produces concepts but some fail to become nodes.** `_add_or_get_node` returns `None` only on hard DB failure (otherwise it dedup's or creates). If `None`, the concept is NOT added to `label_to_node`. Bridge-step invariant C.1.3(1) would fail. This is the intended behavior — a failed graph write should not be masked.
6. **Reserved concept names collide with global keys.** Concept names arrive as freeform text. They never appear as keys at the strategy-scoring level (they only appear inside `batch_result["concepts"]`, never promoted to signal keys). No collision risk.

---

## C.7 Out of scope for Phase C-impl (deferred to Phase D)

- Weight tuning per methodology (the §4.1 rewrite rules produce mechanically-correct but not-yet-tuned weights).
- Adding new `graph.node.elaboration*` / `graph.node.charge*` weight entries to strategies that previously had no LLM-signal coverage (e.g. some chain-topology-only strategies).
- Context-doc rewrites (`.claude/context/signal-detection-llm.md`, `.claude/agents/signal-specialist/AGENT.md`). Per CLARITY REVIEW issue 2, these move to a separate follow-up bead to keep Phase C-impl scoped to code + YAML. `scripts/check_doc_drift.py` will flag them until updated.

---

## C.8 Artifacts produced by Phase C-impl (bead f965), derived from this spec

1. `src/services/turn_pipeline/context.py` — add `concept_to_node_id` field.
2. `src/services/turn_pipeline/stages/graph_update_stage.py` — populate the new field after `add_extraction_to_graph`.
3. `src/services/node_state_tracker.py` — add `append_quality(node_id, elaboration, charge)`; derive categorical depth per C.5.1 and keep `all_response_depths` populated.
4. `src/services/global_signal_detection_service.py` — pass `concepts=` to `LLMBatchDetector.detect`; add `detect_with_per_concept` returning `(global_signals, per_concept_signals)`.
5. `src/services/turn_pipeline/stages/strategy_selection_stage.py` — insert the bridge step (C.3.5) between global-signal detection and node-signal detection, with the C.1.3 invariants asserted.
6. `src/signals/graph/graph_signals.py` (and/or `node_base.py`) — emit `graph.node.elaboration[.low/.medium/.high]`, `graph.node.charge[.positive/.negative]`, `graph.node.has_quality_data` from `NodeState.quality_history`.
7. `src/domain/models/node_state.py` — add `NodeQualityHistory` (per Section A §2.3, renamed per B.0).
8. 6 YAML files in `config/methodologies/*_v2*.yaml` — apply §4.1 rewrites with C.4 procedure.
9. `src/methodologies/registry.py` — update signal-name allow-list if it enumerates LLM signal names (drop 4, add `elaboration`, `charge`, `has_quality_data`, keep `engagement`, `certainty`).

Phase C-impl acceptance adds one line: **"Section C of `docs/drafts/signal-migration-contract.md` reviewed; routing bridge and invariants implemented as specified."**

---

## C.9 Acceptance checklist (traces to bead 4540 acceptance criteria)

- [x] Per-concept → node routing: concept.text.lower() → node.id via Stage 4 `label_to_node`, persisted as `context.concept_to_node_id`, consumed in Stage 6 bridge step. No new signal namespace; reuses `graph.node.*` prefix. — §C.0, §C.1
- [x] Concrete data flow from batch_detector → GlobalSignalDetectionService → strategy_selection_stage → NodeStateTracker → NodeSignalDetectionService → scoring. — §C.2, §C.3
- [x] Migration rules for all 6 methodology YAML `signal_weights` with per-file counts and validation gate. — §C.4 (extending §4)
- [x] `response_depth` derivation for node-tracker compatibility: single-concept binning from normalized elaboration (C.5.1); turn-level aggregation unchanged from §3; two-path consistency table (C.5.4). — §C.5
