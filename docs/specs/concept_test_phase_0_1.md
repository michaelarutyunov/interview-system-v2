# Concept Test — Phase 0 + Phase 1 Implementation Spec

**Status**: Spec, ready for implementation
**Scope**: Phase 0 (concept schema + Nudge fixture + regression harness) and Phase 1 (anchor infrastructure + coverage state machine + three derived signals). No runtime strategy consumption; `traverse` and later strategies are out of scope.
**Source**: `docs/drafts/concept_test_planning.md` — Parts 1, 3, 4, 6, 7, 8.
**Audience**: Implementation agents working one bead at a time.

---

## 0. Agent Routing

Per `CLAUDE.md` agent-routing table. When picking up a bead in this spec, invoke the specialist matching the primary file(s) touched.

| Spec section / bead area | Primary files | Invoke agent |
|---|---|---|
| §5.1 YAML grammar, ConceptSchemaValidator, node-type registry (Phase 0) | `src/domain/models/concept.py`, `src/methodologies/concept_validator.py`, `src/domain/node_types.py`, `config/concepts/nudge_concept_test.yaml`, `config/methodologies/*.yaml` | `methodology-specialist` |
| §5.3–5.4 AnchorCoverageState model, repo, AnchorSeedingService, session-init wiring | `src/domain/models/anchor_coverage.py`, `src/persistence/repositories/anchor_coverage_repo.py`, `src/services/anchor_seeding_service.py`, `src/services/session_service.py` | `pipeline-specialist` (session lifecycle) with `methodology-specialist` as second reader for validator interplay |
| §5.5 SlotDiscoveryStage (Stage 4.5) extension; §5.6 StateComputationStage (Stage 5) extension; pipeline contract field | `src/services/turn_pipeline/stages/slot_discovery_stage.py`, `src/services/turn_pipeline/stages/state_computation_stage.py`, `src/domain/models/pipeline_contracts.py` | `pipeline-specialist` |
| §5.7 Three new signal classes (`concept.anchor.pending`, `concept.anchor.unelaborated`, `concept.coverage.pressure`) | `src/signals/concept/*.py` | `signal-specialist` |
| §9 Regression harness, golden-fixture capture, CI gate | `scripts/regression_harness.py`, `tests/fixtures/regression/` | `pipeline-specialist` (harness orchestrates the pipeline) |
| `CanonicalSlot.status` enum extension, `first_seen_turn` relaxation, promotion bypass audit | `src/domain/models/canonical_graph.py`, `src/services/canonical_slot_service.py`, `src/persistence/repositories/canonical_slot_repo.py` | `pipeline-specialist` (canonical-slot lifecycle is pipeline-owned) |

**No match** for the extraction stage in Phase 0/1 — extraction code is untouched. `extraction-specialist` is not expected to be invoked for any bead in this spec; if a bead tries to pull in that agent, re-read scope.

---

## 1. Problem Statement & Context

### Problem
Today's engine is exploratory: the canonical graph grows bottom-up from surface utterances. Concept-test interviews require the inverse — a researcher-authored DAG of concept nodes must exist at session start, and the engine must track which of those nodes have been touched, elaborated, and evaluated.

Phase 0 + 1 build the foundation only. No new strategies fire; no probing happens. The deliverable is: a concept can declare anchors, those anchors become pre-seeded canonical slots, the engine tracks their lifecycle silently across a session, and three derived signals expose coverage state. MEC/JTBD/CJM behavior is unchanged.

### Constraints
- **Backward compatibility is non-negotiable.** MEC/JTBD/CJM simulations must produce identical scoring decisions before and after the phase lands (deterministic mode). Enforced by regression harness (§9).
- Pydantic-contract pattern at stage boundaries (existing convention).
- No new LLM calls in Phase 1. Signals derived from canonical slots + coverage state only.
- Feature-flag graceful-skip semantics: concepts without `anchors:` are a no-op.

### Non-negotiable vs flexible
- **Fixed**: the revised ontology from planning Part 4 (node types, edge types, valence on nodes), 5-state coverage machine from Part 6, universal node-type registry, regression harness as gate.
- **Flexible**: exact thresholds (`unelaborated_child_threshold`, `coverage_pressure` denominator semantics beyond the default) — defaults specified here, tunable via config.

---

## 2. Requirements

### Functional

**F1.** Concept YAML grammar accepts an optional `anchors:` block with per-anchor metadata (id, description, required, node_type, authored_valence, canonical_slot_hint).

**F2.** Concept YAML grammar accepts node/edge declarations for the concept-test ontology (`headline`, `feature`, `consequence_functional`, `consequence_psychosocial`, `rtb`, `context`; edges `leads_to`, `supports`, `applies_to`).

**F3.** A validator rejects structurally malformed concept files and enforces methodology-level constraints (e.g., `concept_test` methodology requires ≥1 required anchor; other methodologies must not declare `anchors:`).

**F4.** At session init, every anchor in the concept produces one pre-seeded `CanonicalSlot` row with status `pending`, `support_count=0`, `first_seen_turn=0`.

**F5.** During Stage 4.5 (SlotDiscoveryStage), surface nodes that map to a pending anchor transition it to `active_unelaborated`. No demotions.

**F6.** Coverage state is persisted per (session, anchor) and advances monotonically under defined transitions (§6).

**F7.** Three signals emit per turn from Stage 5 (StateComputation) or Stage 6 (signal detection) — placement §7:
  - `concept.anchor.pending` (per-node boolean)
  - `concept.anchor.unelaborated` (per-node boolean)
  - `concept.coverage.pressure` (session scalar, 0.0–∞, clipped)

**F8.** Nudge concept YAML exists as a test fixture (`config/concepts/nudge_concept_test.yaml`) with full DAG and 3 required anchors per planning Part 7.

### Non-Functional
- **Zero regression** on MEC/JTBD/CJM golden simulations (scoring decisions, per-turn, deterministic).
- **Latency budget**: anchor pre-seeding at session init <50ms for concepts with ≤20 anchors; signal derivation <5ms per turn.
- **Storage**: anchor coverage state fits in existing canonical-slot table plus one new table (§5).

### Dependencies
- Existing `CanonicalSlot` / `SlotMapping` models and `canonical_slot_repo`.
- spaCy `en_core_web_md` (already wired for similarity).
- No new LLM providers.

---

## 3. System Architecture

### Components (Phase 0 + 1 additions)

| Component | Purpose | Inputs | Outputs |
|---|---|---|---|
| **ConceptSchemaValidator** *(new)* | Parse and validate concept YAML including `anchors:` block | YAML file path, methodology id | `Concept` pydantic model or raises `ConceptValidationError` |
| **Node-type registry** *(extend)* | Central list of allowed concept-node types | — | Static module-level constant |
| **AnchorSeedingService** *(new)* | Pre-seed canonical slots from anchors at session init | `Concept`, `session_id` | N `CanonicalSlot` rows with status=`pending`, plus N `AnchorCoverageState` rows |
| **AnchorCoverageStateRepo** *(new)* | CRUD for per-session anchor state | session_id | `List[AnchorCoverageState]` |
| **SlotDiscoveryStage** *(extend)* | Detect surface→anchor attachment; transition state | surface nodes, canonical slots (incl. pending) | Updated state rows |
| **StateComputationStage** *(extend)* | Emit coverage signals into `GraphState` extended_properties | canonical slots, coverage states | Signal values in context |
| **Signal pool** *(extend)* | Register 3 new signals in `src/signals/meta/` (or new `concept/` dir) | — | Signal classes |
| **Regression harness** *(new)* | Golden simulation diff tool | pre-phase and post-phase scoring traces | Pass/fail + diff report |

### Data Flow

```
Session init
   └─ AnchorSeedingService.seed(concept, session_id)
        ├─ writes N CanonicalSlot rows (status=pending, support_count=0)
        └─ writes N AnchorCoverageState rows (state=pending)

Turn N pipeline
   Stage 1..4  (unchanged)
   Stage 4.5  SlotDiscoveryStage
         - compute similarity between new surface nodes and ALL canonical slots (including pending)
         - if match ≥ threshold AND slot.status == pending:
              slot.status = active
              coverage.state = active_unelaborated
         - if match ≥ threshold AND slot.status == active AND state == active_unelaborated:
              child-count check (§6); may transition to active_unevaluated
   Stage 5   StateComputationStage
         - derive three signals from coverage states + canonical graph
   Stage 6   signal detection
         - signals already in context; no detector changes in Phase 1
```

### Boundary discipline
Concept-test code paths are guarded at three entry points:
1. Anchor seeding is a no-op when `concept.anchors` is empty (other methodologies unaffected).
2. Coverage transitions in Stage 4.5 short-circuit when no pending/anchor-derived slots exist.
3. New signals return neutral values (False / 0.0) when no anchors exist; cannot contribute to scoring.

---

## 4. Design Decisions & Rationale

### D1. Anchor identity = pre-seeded canonical slot with new status `pending`

**Decision**: Extend `CanonicalSlot.status` enum from `{candidate, active}` to `{pending, candidate, active}`. Anchors are canonical slots with `pending` status and `support_count=0`.

**Rationale**: Canonical layer is the right place — anchors are latent concepts with no surface expression yet. Alternative (parallel "anchor table") duplicates similarity/mapping infrastructure. Alternative (overload `candidate`) loses the semantic distinction between bottom-up-candidate (has support, awaiting promotion) and top-down-pending (no support, declared).

**Tradeoffs**: Gain reuse of existing similarity/mapping pipeline. Sacrifice: `CanonicalSlot.first_seen_turn` must relax from `ge=1` to `ge=0` (anchors exist pre-turn-1). One model change ripples to validator.

**Constraints**: `support_count >= canonical_min_support_nodes` promotion rule must be bypassed for pending slots — they go `pending → active` on first surface attachment, not after N supporters.

### D2. Universal node-type registry + methodology-level validation

**Decision**: All node types (MEC's, JTBD's, concept-test's, future) live in one registry (`src/domain/node_types.py`). Each methodology declares which subset it accepts; validator enforces.

**Rationale**: Per planning Part 8. Simpler than per-methodology registry; fails loud if a JTBD concept uses `headline` (validator rejects).

**Tradeoff**: A growing registry. Mitigated by keeping it append-only and documented.

### D3. Coverage state stored in a new table, not canonical-slot extended_properties

**Decision**: New table `anchor_coverage_state(session_id, anchor_id, canonical_slot_id, state, child_count, last_transition_turn, refused_turn)`.

**Rationale**: Coverage state is concept-test-specific and has five discrete values plus per-anchor audit fields. Canonical slot's `extended_properties` (JSON blob, Phase 4 work) is overloaded when used for structured workflow state. Separating keeps Phase 4 free to design evaluation-signal storage without the baggage.

**Tradeoff**: One new table + repo. Accepted: trivial cost, clean boundary.

### D4. Refusal is terminal in v1

**Decision**: Once `state = refused`, no reattempt. Closes planning open question #4.

**Rationale**: Simplest semantics. Reattempt logic needs policy (after how many turns? once only?) that would be guessed. v2 can relax.

### D5. `coverage.pressure` defaults to `required_pending / max(1, turns_remaining)`

**Decision**: `turns_remaining = session.config.max_turns - current_turn`, floored at 1. `required_pending` = count of required anchors still in `pending` state.

**Rationale**: Simple monotone pressure; undefined when budget exhausted is nonsense, hence the floor. Value is unused in Phase 1 (no strategy gates on it yet) so this is a provisional formula — recorded as `Phase 2 open item` in planning, pinned here so tests can assert.

**Tradeoff**: Formula may need replacement once `traverse` gates on it. Kept simple to avoid premature optimization.

### D6. Regression harness diffs scoring decisions, not transcripts

**Decision**: Golden-run artifacts are per-turn `(selected_strategy, selected_node_id, top_3_strategy_scores)` tuples in deterministic mode. Transcripts (LLM-authored) are not in the diff.

**Rationale**: Transcripts depend on LLM nondeterminism even with temperature=0 in some providers. Scoring is pure function of state + signals; deterministic. This is the real safety net for backward compatibility.

**Tradeoff**: Will miss LLM-facing regressions (wrong prompt context, etc.) — out of scope for Phase 0/1 (no LLM-facing changes).

---

## 5. Component Specifications

### 5.1 Concept YAML grammar (Phase 0)

**Grammar additions** (backward-compatible; all top-level keys optional):

```yaml
# existing fields
id: nudge_concept_test_v1
name: "Nudge Functional Cold Brew - Concept Test"
methodology: concept_test           # new methodology id (registered in Phase 5 bundle; Phase 0 only needs validator to accept)
objective: "..."

# NEW — concept DAG declaration (optional; if absent, treated as exploratory concept)
concept_dag:
  nodes:
    - id: headline_energy
      type: headline
      text: "Cold brew that keeps you focused without the crash"
      authored_valence: positive    # positive | negative | neutral
    - id: consequence_sustained_energy
      type: consequence_functional
      text: "Delivers stable energy for 4+ hours"
      authored_valence: positive
    - id: consequence_focus_calm
      type: consequence_psychosocial
      text: "Feel calm and focused, not jittery"
      authored_valence: positive
    - id: consequence_taste_concern
      type: consequence_functional
      text: "Might taste chalky because of protein and adaptogens"
      authored_valence: negative
    # ...features, rtb, context nodes
  edges:
    - source: feature_protein
      target: consequence_sustained_energy
      type: leads_to
    - source: rtb_clinical
      target: consequence_focus_calm
      type: supports

# NEW — anchor declaration (optional)
anchors:
  - id: anchor_sustained_energy
    concept_node_id: consequence_sustained_energy   # must match a node in concept_dag.nodes
    required: true
    description: "Ability to deliver stable energy without a crash over several hours"
    canonical_slot_hint: energy_stability           # optional; biases similarity matching
  - id: anchor_focus_calm
    concept_node_id: consequence_focus_calm
    required: true
    description: "Feeling of calm focus, not jittery or anxious"
  - id: anchor_taste_concern
    concept_node_id: consequence_taste_concern
    required: true
    description: "Concern about unpleasant taste from protein and adaptogens"
```

**Pydantic models** (new in `src/domain/models/concept.py` or extended there):

```
class ConceptNode(BaseModel):
    id: str
    type: str                           # validated against node-type registry
    text: str
    authored_valence: Literal["positive", "negative", "neutral"] = "neutral"

class ConceptEdge(BaseModel):
    source: str
    target: str
    type: Literal["leads_to", "supports", "applies_to"]  # concept-test edges
    # (existing MEC/JTBD edge types allowed too; enforced by methodology validator)

class ConceptAnchor(BaseModel):
    id: str
    concept_node_id: str                # FK into concept_dag.nodes
    required: bool = False
    description: str
    canonical_slot_hint: Optional[str] = None

class ConceptDAG(BaseModel):
    nodes: List[ConceptNode]
    edges: List[ConceptEdge]

class Concept(BaseModel):               # extended
    id: str
    name: str
    methodology: str
    objective: str
    concept_dag: Optional[ConceptDAG] = None
    anchors: List[ConceptAnchor] = []
```

**Validator** (`src/methodologies/concept_validator.py`, new):

Rules (methodology-agnostic first, then methodology-scoped):
1. Every `anchors[].concept_node_id` exists in `concept_dag.nodes[].id`.
2. Every `concept_dag.edges[].source/target` exists in `concept_dag.nodes[].id`.
3. Every `concept_dag.nodes[].type` is in the universal node-type registry.
4. No duplicate anchor ids, node ids, or edge (source,target,type) triples.
5. **Methodology-scoped**: when `methodology == "concept_test"`, `anchors` must contain ≥1 required anchor. When `methodology != "concept_test"`, `anchors` must be empty (fails loud on mixing concerns).
6. **Methodology-scoped**: node types restricted to each methodology's allowed subset (MEC: attribute/functional_consequence/psychosocial_consequence/value; concept_test: headline/feature/consequence_functional/consequence_psychosocial/rtb/context).

**Error behavior**: raise `ConceptValidationError` with a list of issues. Never degrade silently. Existing concepts (no `anchors`, no `concept_dag`) pass unchanged.

### 5.2 Node-type registry (Phase 0)

**Location**: `src/domain/node_types.py` (new).

**Content**: one dict mapping methodology id → allowed node types. Types used across methodologies (e.g., `context`) appear in multiple entries.

**Consumers**: ConceptSchemaValidator (§5.1). No pipeline code reads this; it's validation-only.

### 5.3 AnchorCoverageState model + repo (Phase 1)

**Model** (`src/domain/models/anchor_coverage.py`, new):

```
class AnchorCoverageState(BaseModel):
    session_id: str
    anchor_id: str                      # concept-level anchor id
    canonical_slot_id: str              # pre-seeded slot backing this anchor
    state: Literal["pending", "active_unelaborated", "active_unevaluated",
                   "evaluated", "refused"]
    child_count: int = 0                # surface children under the anchor's canonical slot
    last_transition_turn: int = 0
    refused_turn: Optional[int] = None
```

**Repo** (`src/persistence/repositories/anchor_coverage_repo.py`, new):

Methods:
- `create_batch(states)` — called once at session init by AnchorSeedingService.
- `get_by_session(session_id) -> List[AnchorCoverageState]` — loaded into context at Stage 1.
- `update_state(session_id, anchor_id, new_state, turn)` — called by Stage 4.5.
- `increment_child_count(session_id, anchor_id, turn)` — called by Stage 4.5 when new surface child attaches.

### 5.4 AnchorSeedingService (Phase 1)

**Location**: `src/services/anchor_seeding_service.py`, new.

**Purpose**: At session init, write N pending canonical slots + N coverage-state rows for a concept's required+optional anchors.

**Interface**:
- Input: `Concept`, `session_id`.
- Output: None (side-effects: DB rows).

**Behavior**:
1. If `concept.anchors` is empty → return immediately (no-op).
2. For each anchor:
   a. Compute embedding of `anchor.description` using spaCy.
   b. Write `CanonicalSlot(id="anchor:{concept.id}:{anchor.id}", session_id=..., slot_name=anchor.canonical_slot_hint or anchor.id, description=anchor.description, node_type=<node_type from concept_dag lookup>, status="pending", support_count=0, first_seen_turn=0, promoted_turn=None, embedding=...)`.
   c. Write `AnchorCoverageState(session_id=..., anchor_id=anchor.id, canonical_slot_id=<above>, state="pending", child_count=0, last_transition_turn=0)`.
3. Call point: `session_service.create_session()`, after concept load, before pipeline first-turn.

**Error handling**:
- If any seed insert fails → raise, abort session creation. Half-seeded sessions are a bug magnet.
- If `concept_dag` is missing but `anchors` present → validator caught this; if not, raise `AnchorSeedingError`.

### 5.5 SlotDiscoveryStage (Stage 4.5) — extension

**Current behavior** (unchanged for non-anchor slots): bottom-up candidate creation, promotion at `support_count >= min_support_nodes`.

**Additions**:

After existing surface-node-to-slot matching runs, for each new surface node:
1. Look up any pending canonical slot whose embedding similarity ≥ `canonical_similarity_threshold`.
2. If matched:
   a. Set `slot.status = "active"` (bypass support-count gate — anchors promote on first hit).
   b. Find corresponding `AnchorCoverageState` by canonical_slot_id. Transition `pending → active_unelaborated`.
   c. Record `child_count = 1` (the new surface node counts as first child).
3. If matched slot is already `active_unelaborated`:
   a. Increment `child_count`.
   b. If `child_count >= unelaborated_child_threshold` (config, default 1) → transition `active_unelaborated → active_unevaluated`.

**Ordering note**: this must run AFTER existing candidate-slot logic so normal-flow slots are promoted on the usual path. Pending→active bypass is anchor-only.

### 5.6 StateComputationStage (Stage 5) — extension

**Additions**: derive and attach three signals to the pipeline context.

- `concept.anchor.pending`: map `{anchor_id: bool}` — true iff state == `pending`.
- `concept.anchor.unelaborated`: map `{anchor_id: bool}` — true iff state == `active_unelaborated`.
- `concept.coverage.pressure`: scalar, see §4 D5.

Storage location: add `concept_coverage` field to `PipelineContext` (pydantic contract extension). Existing MEC/JTBD flows leave it None.

### 5.7 New signal classes (Phase 1)

**Location**: `src/signals/concept/` (new directory).

Three signal classes, all deriving from existing `SignalBase`. Each reads from `PipelineContext.concept_coverage` and returns neutral when it's None.

Not yet consumed by any strategy's `valid_when` — Phase 2 wires them up. Tests in Phase 1 assert they emit correct values; they do not change scoring.

---

## 6. Coverage State Machine

```
                  ┌─────────────────────┐
                  │      pending        │  (pre-seeded at session init)
                  └──────────┬──────────┘
                             │ surface node maps to anchor slot (Stage 4.5)
                             ▼
                  ┌─────────────────────┐
                  │ active_unelaborated │  (at least one surface child)
                  └──────────┬──────────┘
                             │ child_count >= unelaborated_child_threshold
                             ▼
                  ┌─────────────────────┐
                  │ active_unevaluated  │  (enough elaboration)
                  └──────────┬──────────┘
                             │ (Phase 4 — not in scope here)
                             ▼
                  ┌─────────────────────┐
                  │     evaluated       │
                  └─────────────────────┘

     any of {pending, active_unelaborated, active_unevaluated}
                             │ user refuses (Phase 5 gesture; not emitted in Phase 1)
                             ▼
                  ┌─────────────────────┐
                  │      refused        │  (terminal in v1)
                  └─────────────────────┘
```

**Phase 1 emits transitions**: `pending → active_unelaborated` and `active_unelaborated → active_unevaluated` only. `evaluated` and `refused` transitions are defined but not triggered in Phase 1 (reserved for Phase 4/5).

**Invariants**:
- Monotone forward progress on the pending → active_unelaborated → active_unevaluated → evaluated spine.
- `refused` is reachable from any non-terminal state and is terminal.
- `child_count` is monotone non-decreasing.
- `last_transition_turn <= current_turn` always.

**Property-test assertion (§9 test T-P1.5)**: no downward transition, no skipping from pending directly to active_unevaluated.

---

## 7. Configuration & Parameters

New config fields (in `src/core/config.py` `Settings`):

| Parameter | Default | Range | Purpose |
|---|---|---|---|
| `enable_concept_test` | `True` | bool | Feature flag. If False, AnchorSeedingService is a no-op even when anchors present. |
| `anchor_similarity_threshold` | reuses `canonical_similarity_threshold` (0.60) | [0.4, 0.9] | Threshold for surface→anchor attachment. Same as canonical by default; separate symbol lets Phase 2 tune independently. |
| `unelaborated_child_threshold` | `1` | [1, 5] | Surface-child count at which an active_unelaborated anchor advances. Default 1 = advance immediately on first child (most permissive). |
| `coverage_pressure_floor` | `1` | [1, ∞) | Floor on `turns_remaining` to avoid division by zero. |

No existing parameter values change.

---

## 8. Error Handling Strategy

| Failure | Cause | Detection | Recovery |
|---|---|---|---|
| Concept validation fails at load | Malformed YAML, anchor refs unknown node, disallowed node type, mixed concerns (anchors on non-concept_test methodology) | `ConceptSchemaValidator` raises `ConceptValidationError` | Abort; surface error at API boundary. No fallback — malformed concept should never run. |
| Anchor seeding DB insert fails | DB error, duplicate key | `AnchorSeedingService` catches per-anchor write, raises after logging | Abort session creation. No partial state. |
| Stage 4.5 pending-slot similarity match ambiguous (two pending slots match one surface node above threshold) | Anchor descriptions too similar | Top-k check in stage | Match highest similarity; log warning with both scores. No runtime error. Concept author should tighten anchor descriptions — detectable in validator? Out of scope; runtime log is sufficient. |
| Coverage state repo read returns stale (state row missing for known anchor) | Bug / migration miss | Stage 4.5 guard: if no row, log error and create `pending` state on the fly | Self-healing; log loud so the underlying bug is visible. |
| `concept.anchor.pending` signal requested but no anchors seeded | Non-concept-test session | Signal returns empty dict (neutral) | No error. |
| Backward-compat regression detected by harness | Phase 0/1 change altered scoring for MEC/JTBD | Harness diff non-empty | **Block merge.** Fix before landing. |

---

## 9. Testing Strategy

### Unit tests

**T-P0.1** `ConceptSchemaValidator` rejects each violation in §5.1 rules 1–6 with specific error messages.
**T-P0.2** Existing MEC/JTBD concept YAMLs load unchanged (no `anchors`, no `concept_dag`).
**T-P0.3** Nudge fixture (`config/concepts/nudge_concept_test.yaml`) loads and passes validator.
**T-P1.1** `AnchorSeedingService` writes exactly N canonical slots + N coverage-state rows for a concept with N anchors.
**T-P1.2** `AnchorSeedingService` is a no-op when `anchors` is empty.
**T-P1.3** `SlotDiscoveryStage` transitions anchor `pending → active_unelaborated` on first matching surface node.
**T-P1.4** `SlotDiscoveryStage` increments child_count and advances to `active_unevaluated` at threshold.
**T-P1.5** Property test: random sequence of surface nodes never produces downward or skipping transitions (hypothesis-based if available, else 50 hand-crafted sequences).
**T-P1.6** `StateComputationStage` emits neutral values when context has no anchors; emits correct values when anchors exist.
**T-P1.7** Three signal classes return `0.0 / False / {}` (neutral) when `concept_coverage` is None.

### Integration tests

**T-I1** End-to-end: create session with Nudge concept → pre-seeded slots visible in DB at turn 0.
**T-I2** End-to-end: run 3-turn simulation where user spontaneously mentions `energy_stability` → coverage state for `anchor_sustained_energy` advances to `active_unelaborated` after turn 1. No other coverage advances.
**T-I3** End-to-end: run 3-turn MEC simulation with `glp1_food_mec`+`baseline_cooperative` → zero anchor-related DB rows written, zero coverage signals in context, scoring identical to pre-phase baseline (bridges to regression harness).

### Regression harness (§4 D6)

**Location**: `scripts/regression_harness.py` (new).

**Inputs**:
- List of (concept_id, persona_id, turn_count) triples — the "golden set".
  - v0 golden set: `(glp1_food_mec, baseline_cooperative, 10)`, `(glp1_food_jtbd, baseline_cooperative, 10)`, `(glp1_food_mec_strict, baseline_cooperative, 10)`.
- Deterministic mode: LLM calls replaced with fixture responses (stored under `tests/fixtures/regression/`). Phase 0 must build the fixture capture path — run once before Phase 0 changes, commit captured LLM responses, replay in harness.

**Outputs**: for each triple, per-turn tuple `(selected_strategy, selected_focus_node_id, top_3_strategy_scores)` serialized to JSONL.

**Diff**: JSONL equality against committed golden artifacts. Any diff → fail.

**Gate**: harness runs in CI on every commit touching `src/services/turn_pipeline/`, `src/signals/`, `src/methodologies/`, `src/services/*slot*`, `src/domain/models/canonical_graph.py`, `src/domain/models/concept.py`, `src/domain/models/anchor_coverage.py`. Must pass before merge.

**Known limitation**: harness does not cover LLM prompt content drift. Phase 1 makes no LLM changes, so this is acceptable. Phase 3+ will extend.

### Nudge fixture as regression tool

Nudge concept YAML doubles as:
1. Unit/integration test input for Phase 0/1.
2. Known-good concept for manual inspection at phase sign-off.

File: `config/concepts/nudge_concept_test.yaml`. Full DAG per planning Part 7 (§ Nudge). Required anchors: exactly the three specified there.

---

## 10. Implementation Notes

### Recommended ordering (for bead decomposition after spec lands)

1. Extend `Concept` / new pydantic models + validator (Phase 0a).
2. Universal node-type registry (Phase 0a).
3. Author Nudge fixture; add fixture loading test (Phase 0b).
4. Build regression harness skeleton; capture golden fixtures from current master (Phase 0c). **Run before any other code changes.**
5. `CanonicalSlot.status` enum extension + migration; relax `first_seen_turn` (Phase 1a).
6. `AnchorCoverageState` model + repo + table migration (Phase 1b).
7. `AnchorSeedingService` + wire into session init (Phase 1c).
8. Extend `SlotDiscoveryStage` for pending→active bypass + state transitions (Phase 1d).
9. Extend `StateComputationStage` + pipeline contract field (Phase 1e).
10. Three new signal classes (Phase 1f).
11. Full test sweep + regression harness pass (Phase 1g — gate).

Each item (1–11) is a candidate bead; each should be loopable (small, self-contained, testable). Do not create beads until spec is accepted — planning doc Part 7 final line applies.

### Known pitfalls

- **Stage ordering (well-known)**: any state reset in Stage 4 is invisible to Stage 6. Coverage state is written in Stage 4.5 and read in Stage 5 — this is within the safe direction.
- **`first_seen_turn` relaxation**: downstream code may assume `>= 1`. Audit `src/services/canonical_slot_service.py` and `src/signals/` for assumptions.
- **`support_count` bypass**: the anchor promotion path bypasses support-count gate. Any analytics code that assumes `status == "active" ⇒ support_count >= min_support` will be wrong. Audit `src/services/graph_service.py`, `src/signals/graph/`.
- **Deterministic-mode LLM replay**: the fixture capture step (§9) must run against unchanged master. Capturing after any Phase 0/1 change invalidates the regression comparison.
- **Anchor description quality**: poor descriptions → bad embeddings → spurious or missed matches. Document this in Nudge fixture's authoring notes.

### Files likely touched (non-exhaustive)

```
config/concepts/nudge_concept_test.yaml                    (new)
docs/specs/concept_test_phase_0_1.md                       (this file)
scripts/regression_harness.py                              (new)
src/core/config.py                                         (new settings)
src/domain/models/concept.py                               (extend)
src/domain/models/canonical_graph.py                       (status enum, first_seen_turn)
src/domain/models/anchor_coverage.py                       (new)
src/domain/models/pipeline_contracts.py                    (concept_coverage field)
src/domain/node_types.py                                   (new)
src/methodologies/concept_validator.py                     (new)
src/persistence/repositories/anchor_coverage_repo.py       (new)
src/persistence/repositories/canonical_slot_repo.py        (handle pending status)
src/services/anchor_seeding_service.py                     (new)
src/services/session_service.py                            (wire seeding)
src/services/turn_pipeline/stages/slot_discovery_stage.py  (extend)
src/services/turn_pipeline/stages/state_computation_stage.py (extend)
src/signals/concept/__init__.py                            (new)
src/signals/concept/anchor_pending.py                      (new)
src/signals/concept/anchor_unelaborated.py                 (new)
src/signals/concept/coverage_pressure.py                   (new)
tests/fixtures/regression/                                 (new, captured LLM responses)
tests/...                                                   (new test modules per T-* above)
```

### References
- `docs/drafts/concept_test_planning.md` — design rationale.
- `.claude/context/canonical-slots.md` — canonical slot lifecycle (current behavior).
- `.claude/context/pipeline-contracts.md` — stage contract pattern.
- `.claude/context/node-state-tracker.md` — Stage-ordering rules.

---

## Acceptance Criteria (for spec-completion bead)

- [ ] This file exists at `docs/specs/concept_test_phase_0_1.md`.
- [ ] Ontology from planning Part 4 is encoded in §5.1 grammar.
- [ ] 5-state coverage machine from planning Part 6 is defined in §6 with invariants.
- [ ] Every open item in planning Part 7 (§ Deferred) that Phase 0/1 must resolve is resolved here (refusal terminality, coverage-pressure formula, unelaborated threshold).
- [ ] Nudge fixture content specified in §5.1 and §9.
- [ ] Regression harness scope, inputs, outputs, and gate defined in §9.
- [ ] File list in §10 covers all new/modified modules.
- [ ] MEC/JTBD/CJM backward compatibility explicitly defended in §4 D1/D2, §5.5, §8 regression row, §9 harness.
