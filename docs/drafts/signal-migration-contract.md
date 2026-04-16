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
