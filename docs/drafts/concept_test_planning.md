# Concept Test Methodology — Planning & Reasoning

**Date**: 2026-04-14
**Status**: Pre-planning brainstorm, no implementation yet
**Scope**: Extending the interview engine from exploratory to evaluative (concept-test) interviews

---

## Purpose of this Document

This captures the reasoning trail from a design discussion on adding concept-test capability to the interview engine. It is intentionally a thinking document — hypotheses, pivots, dead-ends, and final positions are all preserved so the design rationale is traceable when this moves to a formal spec.

The user's starting objective: enable the system to run traditional concept tests (e.g., testing a product/positioning concept against synthetic target-group personas), where specific "points of interest" must be monitored for spontaneous mention and probed explicitly if absent.

---

## Part 1 — Initial Arc & the Build Sequence

### First proposal (later revised)

Initial suggestion: treat the discussion guide as a **seeded canonical graph** with coverage obligations. Anchors become first-class canonical slots with `required=True` + a coverage state machine (unmentioned → spontaneous → probed → confirmed).

Proposed phased sequence:

1. **Phase 1**: Anchors as seeded canonical slots. Extend methodology YAML with `discussion_guide:` block.
2. **Phase 2**: Two new strategies — `probe_anchor` (ask about an unmentioned anchor) and `capture_reaction` (evaluate a touched anchor).
3. **Phase 3**: Concept artifact + stimulus injection.
4. **Phase 4**: Evaluative scoring dimensions (comprehension, believability, relevance, uniqueness, intent).
5. **Phase 5**: Dedicated `concept_test` methodology.
6. **Phase 6**: Target-group personas + aggregation reporting.

### First user challenge — YAML separation of concerns

**User push**: discussion topics should not live in methodology.yaml — that mixes concerns. Concept yaml already exists.

**Resolution**: User is right. Clean separation:
- **concept.yaml** gains an optional `anchors:` block. Each anchor: `{id, description, required, canonical_slot_hint, prompt_if_absent}`. Any concept can carry anchors; exploratory interviews ignore them.
- **methodology.yaml** (a new `concept_test` methodology) declares *how to use* anchors when present: which strategies fire, how coverage affects termination, phase-to-strategy weighting.

Principle: methodology is *mechanism*, concept is *content/territory*. Same pattern as MEC (hierarchy in methodology, specific goal in concept).

A methodology can *require* anchors (concept_test refuses to run without them) while anchors themselves remain a concept-level construct.

### Second user challenge — graph-language precision

**User push**: "probe_anchor" and "capture_reaction" are moderator verbs, and moderator verbs don't translate cleanly to graph operations. Also wary of the word "depth" — overloaded in this codebase.

**Resolution**: User is right. Reworked in graph terms:

#### What an anchor IS in graph terms
A pre-seeded canonical slot in `pending` state with no supporting surface nodes. Exists in canonical graph but has no surface representation yet.

**Architectural wrinkle to name**: the canonical layer today is bottom-up (emerges from surface via similarity). Anchors are top-down (declared, waiting for surface to attach). Worth making this difference explicit in implementation.

#### "probe_anchor" as graph operation
**Targeted surface graph growth to fulfill a pending canonical slot:**
- **Precondition**: canonical slot A is `pending`, no surface node maps to A.
- **Action**: generate question whose expected answer produces surface node mapping to A.
- **Postcondition (success)**: surface node S created; S maps to A via similarity; A transitions pending→active.
- **Postcondition (failure)**: user deflects; anchor marked `refused`; slot stays pending.

This is a **new kind of graph action** — neither deepen nor bridge nor branch. It's "materialize surface from canonical." Worth its own name: `traverse` or `fulfill_anchor`.

#### "capture_reaction" — the bigger insight
Evaluative reactions **aren't graph structure at all**. When asking "how believable is X?", the answer isn't a new node or edge — it's an *evaluative property* on the existing node. Comprehension, believability, relevance, intent are things the user *feels about the stimulus*, not things they *know about the world*.

**Two kinds of follow-up after an anchor lands:**

| Follow-up intent | Graph operation | Data produced |
|---|---|---|
| Get more detail ("what do you mean?") | Grow children under anchor node — existing `deepen`/`branch` | New surface nodes + edges |
| Get evaluation ("do you believe it?") | No graph growth — attach signals to node | Node-scoped evaluation signals |

**Consequences:**
- Only ONE genuinely new strategy family needed: `fulfill_anchor` / `traverse`.
- **No `capture_reaction` strategy** — reactions are a signal-collection concern. QG stage asks an evaluation question when anchor is `active_unevaluated`.
- "Detailing" follow-ups reuse existing strategies focused on anchor nodes.

#### Coverage state machine
Per anchor, per session:
- `pending` — canonical slot exists, no surface node
- `active_unevaluated` — surface node created (spontaneously or via `traverse`), no evaluation signals yet
- `evaluated` — required evaluation signals captured
- `refused` — user declined

Termination: all `required` anchors are `evaluated` or `refused`.

---

## Part 2 — Spontaneous Phase & Moderator Moves

### User question
What strategies maximize opportunity for spontaneous feedback in the opening section, and how do they map to graph operations?

### Analysis — what moderators actually do

1. **Post-stimulus open prompt** — "What comes to mind?" — one broad invitation, then silence.
2. **Minimal encouragers** — "Tell me more." / "What else?" — zero new content.
3. **Echoing/mirroring** — reflect user's own word back.
4. **Breadth probes** — "Anything else you noticed?" — lateral before deep.
5. **Narrative prompts** — "Walk me through your thinking."
6. **Silence / one-word prompts** — user fills space with priorities.

Common thread: **zero new concepts introduced by moderator**. Everything references stimulus-as-whole or what user already said.

### Mapping to graph operations

| Moderator move | Graph operation | Existing primitive |
|---|---|---|
| Post-stimulus open prompt | No focus node; open elicitation QG mode | New QG template, no new strategy |
| Minimal encourager | Focus = user's most recent surface node; deepen minimally | `deepen` / existing |
| Echoing/mirroring | Focus = highest-salience user node; quote user literally | `deepen` with salience-preserving QG |
| Breadth probe | Invite siblings/parallels | `branch` / `explore` |
| Narrative prompt | Focus = stimulus root; invite temporal walkthrough | QG mode, reuses focus selection |

**Key conclusion**: Phase 1 of concept test = **exploratory engine with anchors held private**. Need:
1. Phase config boosting breadth strategies, **hard-gating off `fulfill_anchor`**.
2. Focus selection scoped to user-originated surface nodes (anchors only visible once user touches them).
3. "Minimal-steering" QG templates.
4. **Anchor-blindness guarantee** at QG: anchor text must not appear in QG context during spontaneous phase. Cheapest enforcement: don't pass anchors into QG context.

### What the system can't approximate well
- **Silence / wait time** — no analog in text-based turn-taking. Partial compensation: rely on minimal-encourager prompts.
- **Reading the room** — engagement/valence signals approximate post-hoc from text.
- **Strategic patience** — system will jump on anchor hits immediately unless we add a "let them finish" heuristic (conversational momentum signal that suppresses strategy switching while user is mid-thought).

### Free bonus: phase-transition signal
Because system tracks anchor hits silently in spontaneous phase, transition criterion is natural:
- **Stay in spontaneous while**: new surface nodes per turn > threshold AND elaboration signals healthy.
- **Transition to explicit when**: surface growth plateaus OR user volunteering drops OR turn budget forces it.

Better than hard turn-count boundary — respects individual variance.

---

## Part 3 — The Ontology Question

### User question
Is concept-test methodology structured like MEC? Is an anchor equivalent to a "terminal value"? Or is it flexible with minimal hierarchy?

### Core ontological finding

**MEC vs. Concept Test are fundamentally different**:

| | MEC | Concept Test |
|---|---|---|
| Graph direction | User-constructed (bottom-up) | Researcher-constructed (top-down) |
| Interview goal | Help user build value hierarchy | See how user reactions map onto pre-authored structure |
| Output | Discovered chains | Coverage + reactions on known structure |
| Anchor meaning | N/A (terminal values emerge) | Pre-declared checkpoints in researcher's DAG |

**Anchors are NOT terminal values.** Terminal values are emergent endpoints; anchors are pre-declared checkpoints. The hierarchy doesn't imply importance the same way.

### Initial node type proposal (later revised)

| Node type | Example | Role |
|---|---|---|
| `headline` | "Lose 15% body weight without dieting" | Core claim (usually 1) |
| `benefit_functional` | "Reduces appetite automatically" | What it does |
| `benefit_emotional` | "Feel in control around food" | How it feels |
| `feature` | "Weekly injection" | What it is |
| `rtb` | "Clinically proven GLP-1 mechanism" | Reason to believe |
| `context` | "For adults with BMI > 30" | Scope |
| `differentiator` | "Unlike willpower-based diets" | Contrast |

Edge types (initial): `supports`, `enables`, `applies_to`, `contrasts_with`.

### Three-layer graph during interview

1. **Concept layer** (researcher-authored, static): DAG pre-seeded into canonical at session start.
2. **Reaction layer** (user-generated): surface nodes from utterances. Each either maps to a concept node (activates it) or is off-territory (orphan branch — signal about what's missing from concept or how user reframes).
3. **Evaluations** (signal overlay): node-scoped scores (comprehension, believability, relevance, intent) attached to concept nodes. Not graph structure.

### Strategy set (first version)

| Strategy | Graph operation | Moderator equivalent |
|---|---|---|
| `traverse` | Shift focus to concept node with no surface support yet | "Let's talk about X" |
| `ground` | Grow user-originated children under a touched concept node | "Why do you say that?" |
| `contrast` | Create user-authored edge between two concept nodes | "How does X compare to Y?" |
| `reconcile` | Address contradiction between user edge and concept-authored edge | "You said X leads to Y but concept says Z" |
| `cultivate` | Grow off-territory user node | "That's interesting — say more" |
| `appraise` | Attach evaluation signals to a concept node (no graph growth) | "How believable is that?" |
| `revitalize` | Conversation-level fallback | "Let's zoom back out" |

**Absent by design**: no `ascend` (concept test doesn't ladder to values), no `branch` (siblings pre-authored).

---

## Part 4 — Valence-Neutral Consequences

### User insight
MEC keeps functional and psychosocial consequence nodes **valence-neutral** — single `leads_to` edge works whether consequence is positive or negative. Alternative (allow `blocks` edge + only positive consequences) is more complex.

Should concept test replace `benefit_functional/emotional` with `consequence_functional/psychosocial`? What about blockers?

### Resolution: user is right, this is a real upgrade

**"Benefit" smuggles valence into structure. "Consequence" keeps valence as node-level data.**

### Revised node types

| Node type | Valence | Example |
|---|---|---|
| `headline` | — | "Lose 15% body weight without dieting" |
| `feature` | neutral | "Weekly injection" |
| `consequence_functional` | **neutral (+/−)** | "Reduces appetite" / "Causes nausea" |
| `consequence_psychosocial` | **neutral (+/−)** | "Feel in control" / "Feel dependent" |
| `rtb` | neutral | "Clinically proven GLP-1 mechanism" |
| `context` | neutral | "For adults with BMI > 30" |

### Revised edge types
- `leads_to` — feature→consequence, consequence→consequence (MEC-style)
- `supports` — rtb→{headline, consequence, feature}
- `applies_to` — context→anything

**No `blocks`, `prevents`, `enables`.** Valence lives on nodes as signal data.

### What blockers become — three cases in one graph

1. **Researcher-anticipated blockers**: pre-authored negative-valence consequence nodes. `{type: consequence_functional, anticipated_valence: negative, anchor: required}`. Treated exactly like any other anchor. Cleaner than a separate "objections" section.
2. **Emergent blockers**: user introduces negative consequence not in concept DAG. `cultivate` grows it as off-territory consequence with captured negative valence. **Most research-valuable output** — unanticipated barriers.
3. **Reframed blockers** (NEW): user takes a researcher-authored *positive* consequence and reacts negatively ("lose 15% body weight" → user says "that sounds extreme"). Concept node activates but with opposite valence to what was authored. **Valence mismatch signal at node level** — cheaper to detect than edge-level contradiction. Potentially more common than `reconcile` cases.

### One new strategy falls out

If user reacts only positively, system has no signal about blockers. Moderators handle this with devil's-advocate moves. Graph-wise: **invite growth of negative-valence consequence nodes when positive-valence dominates**.

| Strategy | Graph operation | Gate |
|---|---|---|
| `invite_counter` | Elicit new consequence nodes with expected negative valence; no forced focus | `consequence_valence_distribution.positive_heavy AND phase.explicit_probing` |

Narrow gate — only when one-sided reaction pattern detected. Does not fire in spontaneous phase (too leading).

### What we give up (and accept)
Researcher cannot pre-declare "this is a benefit" vs. "this is a concern" at **structural** level. Moves to metadata: `authored_valence: positive | negative | neutral`. Schema expressiveness loss, graph simplicity gain. Same trade MEC made. Alternative (edge-type zoo) makes every strategy gate and every mapping rule more complicated.

### Deferred decision: should concept test `ascend` to values?
**Not in v1.** MEC's terminal-value ladder exists because MEC is *about* value hierarchies. Concept testing is about whether stimulus lands. A late-phase `ascend` from a loaded psychosocial consequence ("feel in control" → why does control matter?) could enrich output, but muddies methodology focus. Consider for v2.

### Split in evaluation signals
With valence-neutral consequences, evaluation signals need splitting:
- `comprehension`, `believability` — valence-agnostic
- `relevance`, `intent` — valence-sensitive

```yaml
evaluation_dimensions:
  comprehension: {scope: any_concept_node}
  believability: {scope: any_concept_node}
  relevance:     {scope: consequence, valence_aware: true}
  intent:        {scope: consequence, valence_aware: true}
```

---

## Part 5 — QG Modes and Signal Discipline

### User question 1: can QG modes be collapsed into strategies rather than branching at QG?

**Yes, and should.** Each strategy **owns its prompt-template family** as part of its definition. QG becomes a table lookup.

```yaml
ground:
  graph_operation: grow_children_under_focus
  valid_when: ...
  prompt_family: elaborate       # "tell me more about X"

traverse:
  graph_operation: activate_pending_anchor
  valid_when: ...
  prompt_family: introduce       # "let's talk about Y"

appraise:
  graph_operation: attach_evaluation_signal
  valid_when: ...
  prompt_family: evaluate        # "how believable is Y?"

cultivate:
  graph_operation: grow_off_territory
  valid_when: ...
  prompt_family: open_elaborate  # "what else comes to mind?"

invite_counter:
  graph_operation: elicit_negative_consequence
  valid_when: ...
  prompt_family: devils_advocate # "what might make this not work?"
```

**Consequences:**
- Phase-appropriateness emerges automatically: phase gates select strategies whose templates happen to be phase-appropriate.
- Anchor-blindness: `ground` and `cultivate` templates never receive anchor text in their binding context.
- No "mode" concept exposed to pipeline. QG stays simple.

**Net**: QG gets *simpler* under concept test, not more complex. Distinct behavior lives in strategy definitions.

### User question 2: what new signals? Keep sprawl tamed.

### Principle for discipline
**A new signal is only justified if it gates a strategy OR captures research output the researcher will read.** Internal state that does neither belongs in node properties or coverage state, not in the signal system.

### Graph-level gating signals (derived from concept DAG + coverage state)

| Signal | Measures | Gates | Scope |
|---|---|---|---|
| `concept.anchor.pending` | Pre-seeded anchor has no surface support | `traverse` | Per-node |
| `concept.anchor.unelaborated` | Anchor active, child count below threshold | `ground` on anchors | Per-node |
| `concept.anchor.unevaluated` | Anchor active, required eval dimensions missing | `appraise` | Per-node |
| `concept.coverage.pressure` | (required pending anchors) / (turns remaining) | phase transition; `traverse` priority | Session scalar |
| `concept.off_territory.salient` | Unmapped surface node passes salience threshold | `cultivate` | Per-node |
| `consequence.valence_skew` | Distribution of observed consequence valences | `invite_counter` | Session-level |

**6 signals.** All derivable from existing state (canonical slots, surface nodes, turn count) + one new piece: anchor coverage machine.

### Node-scoped evaluation signals — NEW CLASS

| Signal | Applies to | Valence-aware? |
|---|---|---|
| `evaluation.comprehension` | any concept node | no |
| `evaluation.believability` | any concept node | no |
| `evaluation.relevance` | consequence nodes | yes |
| `evaluation.intent` | consequence nodes | yes |

**4 dimensions.** Captured by LLM during `appraise` turns (or opportunistically when user volunteers).

### Reused signals — no new additions needed
- `engagement`, `valence`, `response_depth` — existing turn-level LLM signals work as-is.
- "Spontaneous anchor mention" — derivable from extraction + coverage state, not a signal.
- Turn-pressure / budget exhaustion — existing turn-count signals.
- Per-turn reaction valence — existing `valence` signal.

### The architectural delta worth surfacing
Existing signals are mostly **turn-scoped** (per-turn, recomputed). Evaluation signals are **node-scoped** and **persistent** (attached to a concept node, accumulated across turns, never recomputed).

If current signal infrastructure assumes turn-scoped-only, this is a real extension. Affects:
- **Storage**: where do node-scoped signals live? Extended properties on canonical slots seems natural.
- **Freshness**: they're not stale across turns — they're *cumulative*.
- **Scoring**: per-node signals participate in joint scoring differently than per-turn signals.

### Total new vocabulary
- **6 gating signals** (graph-level, derived)
- **4 evaluation dimensions** (node-scoped, new class)
- **0 new conversational/LLM turn-level signals** (reuse existing)

**10 names total, clustered into two concepts (coverage tracking + evaluation capture).** Defensible footprint. If it creeps past that during implementation — especially more evaluation dimensions or new per-anchor gating signals — that's a warning sign of encoding research-specific taxonomy in signals when it belongs in YAML schema.

---

## Consolidated Position

### What concept-test methodology looks like

**Concept (concept.yaml)**:
- New `anchors:` block with node_ids marked as `required`
- Node types: `headline`, `feature`, `consequence_functional`, `consequence_psychosocial`, `rtb`, `context`
- Edge types: `leads_to`, `supports`, `applies_to`
- Valence as node-level data: `authored_valence: positive | negative | neutral`
- Evaluation dimensions declared per anchor or globally

**Methodology (new `concept_test` methodology yaml)**:
- Strategy set: `traverse`, `ground`, `contrast`, `cultivate`, `appraise`, `invite_counter`, `revitalize`
- Each strategy carries `prompt_family` pointing to template set
- Phase configuration: spontaneous phase suppresses `traverse`, `appraise`, `invite_counter`
- Phase transition driven by `concept.coverage.pressure` + surface-growth plateau
- Coverage-based termination (all required anchors `evaluated` or `refused`)
- Anchor-blindness enforced by template context binding, not runtime check

**Pipeline changes**:
- Session init: pre-seed pending canonical slots from concept `anchors:`
- Stage 4/4.5: anchor lifecycle management (pending → active_unelaborated → active_unevaluated → evaluated/refused)
- Stage 5: emit new coverage signals
- Stage 6: concept-test strategy gates
- Stage 7: coverage-based termination
- Stage 8: prompt-family resolution from winning strategy

### Minimal viable v1 scope
- `headline + 2 consequences + 1 RTB`, all marked required anchors.
- Strategies: `traverse`, `ground`, `cultivate`, `appraise` (no `contrast`, no `reconcile`, no `invite_counter` yet).
- 4 evaluation dimensions, all on anchor nodes.
- 1 synthetic persona matched to target group.
- Spontaneous + explicit-probing phases; no reconciliation phase yet.

### Deferred to v2+
- `contrast` and `reconcile` strategies (edge-level comparisons and contradictions)
- `invite_counter` (valence-balancing devil's advocate)
- Late-phase `ascend` to values (MEC-borrowed)
- Stimulus presentation mechanics (how/when concept is shown to AI persona)
- Aggregation reporting across persona runs
- Target-group `concept_fit` persona schema

---

## Open Design Questions

1. **Storage of node-scoped evaluation signals**: extended properties on canonical slots, or new storage pathway?
2. **Spontaneous-phase "conversational momentum" signal**: worth adding? Suppresses strategy switching while user is mid-thought.
3. **Valence-mismatch detection**: is reframed-blocker case (user reacts negatively to authored-positive consequence) a first-class v1 signal, or emerge-only?
4. **Required anchor refusal**: if user refuses (`refused` state), should methodology allow reattempt later in the interview, or lock once refused?
5. **Off-territory consequence salience**: threshold for `cultivate` — how to set without overfitting to any one concept?

---

## Key Principles Enforced

1. **Mechanism vs. domain separation**: anchors on concept (territory), strategies in methodology (mechanism).
2. **Graph-operation-first strategy naming**: `traverse` not `probe_anchor`, `ground` not `capture_reaction`. Forces precision about what actually happens in the data.
3. **Valence as data, not structure**: single edge type, node-level valence signals. Same discipline as MEC.
4. **Signal discipline**: must gate a strategy OR appear in researcher-facing report. Else it's state, not signal.
5. **QG simplicity**: modes collapse into strategy-owned prompt families. No new pipeline axis.
6. **Reuse before invent**: 80% of concept-test engine is exploratory engine configured differently. New primitives are `traverse` and node-scoped evaluations — that's it.

---

## Part 6 — Plan Revision After Discussion

### What changed from the original 6-phase plan

| Original assumption | Discussion finding | Revision |
|---|---|---|
| Anchors in methodology.yaml | Mixes mechanism and territory | Anchors in concept.yaml; new Phase 0 for schema |
| Two new strategies: `probe_anchor` + `capture_reaction` | Only `traverse` is graph growth; evaluations are signals, not a strategy | One new strategy family (`traverse`); evaluations are their own phase |
| `benefit_functional` / `benefit_emotional` node types | Valence-neutral `consequence_*` + single `leads_to` is MEC-consistent | Ontology rewritten; blockers dissolve into negative consequences |
| QG modes as new pipeline axis | Strategies own prompt families; QG stays simple | No QG-mode phase needed |
| "Evaluative scoring" as Phase 4 (late add-on) | It's a new signal *class* with persistence/storage implications | Phase 4 reconceived around the architectural delta |
| Phase structure implied hard turn boundaries | Coverage pressure + surface-growth plateau better | Phase transition signal emerges from existing infrastructure |
| Spontaneous phase as later refinement | v1 requires both phases to be useful | Phase 6 work folded into Phase 5 release bundle |

### Revised phase sequence

**Phase 0 — Concept schema & concrete test concept (foundation, no runtime)**
- concept.yaml extension: `node_types`, `edges`, `anchors` block, `authored_valence` metadata
- Validator
- Author the Nudge concept (see locked v1 scope below)

**Phase 1 — Anchor infrastructure & coverage state machine**
- Pre-seed pending canonical slots from concept `anchors:`
- Coverage state machine: `pending → active_unelaborated → active_unevaluated → evaluated/refused`
- Surface→anchor similarity mapping
- 3 derived signals: `concept.anchor.pending`, `concept.anchor.unelaborated`, `concept.coverage.pressure`
- Internal milestone (tracks spontaneous hits, no probing yet)

**Phase 2 — `traverse` strategy**
- Graph op: activate pending anchor
- Prompt family: `introduce`
- Gate: `pending AND required AND coverage.pressure > threshold`
- Internal milestone (probing works, no evaluations)

**Phase 3 — Stimulus + target-group persona wiring**
- Persona receives concept at session start (system-prompt context)
- Persona schema: `category_relationship: current_user | potential_user | lapsed_user | non_user`
- Opening-question template variants keyed on `category_relationship`
- Internal milestone

**Phase 4 — Node-scoped signal class (platform work)**
- Canonical-slot extended-properties pathway — **committed as platform work, not concept-test-specific**
- Cumulative lifecycle, scoring integration
- LLM detector for 4 evaluation dimensions: `comprehension`, `believability`, `relevance`, `intent`
- Derived signal: `concept.anchor.unevaluated`
- Benefits future methodologies beyond concept test (per-node persistent state for MEC confidence, emotional salience, etc.)

**Phase 5 — Full v1 bundle (the release)**
All of the following land together — both phases must work for v1 to be useful:
- `appraise` strategy (gate: `unevaluated AND required`; prompt family: `evaluate`)
- `cultivate` strategy (gate: `off_territory.salient`; prompt family: `open_elaborate`) — required for real spontaneous phase
- Anchor-blindness enforcement: anchor text excluded from QG template context in spontaneous phase
- Phase transition heuristic: growth plateau + `coverage.pressure`
- Coverage-based termination
- **Deliverable: full working concept test on Nudge with two personas, end-to-end.**

**Post-v1 tuning (not a hard phase)**
- Opening-question refinement by target group if the Phase 3 version proves too coarse
- Optional: target-group-specific weighting of evaluation dimensions

**v2 backlog (explicitly deferred)**
- `contrast` (user-authored edges between concept nodes)
- `reconcile` (edge-level contradiction detection)
- `invite_counter` (devil's advocate when valence one-sided)
- Valence-mismatch detection (user reacts negatively to authored-positive consequence)
- Late-phase `ascend` to values
- Stimulus re-presentation mechanics
- **Cross-persona aggregation reporting** — this is analytical layer, out of scope for the engine

### On target-group variation — graph logic holds

User pushed back on what target-group means: concept test might be among current product users OR among potential users. Does graph logic need to branch?

**Finding: no.** The concept DAG is the same; what varies lives outside the graph.

| What varies with target group | Where it lives |
|---|---|
| Persona's prior category knowledge/attitudes | Persona system prompt |
| Opening question ("how do you currently buy X?" vs. "when you think about morning routines...") | QG template variant keyed on `category_relationship` |
| What spontaneous mentions look like | Emerges from persona behavior; no engine change |
| What counts as "off-territory" salience | Same threshold; content differs, mechanism identical |

**Interesting case**: current users will spontaneously reference competing products ("this sounds like Athletic Greens but with coffee"). These become off-territory surface nodes that `cultivate` grows. Valuable competitive-framing data, falls out for free.

---

## Part 7 — Locked v1 Scope

### Concept
**Nudge** — functional cold-brew with protein + adaptogens (see Part 5 concept.yaml sketch for full DAG).

Full concept DAG retained for structural completeness; required-anchor subset is smaller for first validation.

### Required anchors (capped at 3 for first validation)
1. `consequence_sustained_energy` — core positive functional benefit
2. `consequence_focus_calm` — psychosocial benefit tied to the adaptogen differentiator
3. `consequence_taste_concern` — anticipated negative consequence (validates valence-neutral model on a real blocker)

Non-required nodes (features, RTB, context, other consequences) stay in the DAG. System maps spontaneous hits to them but has no probing obligation. This tests the "anchor hit without probing obligation" path cheaply.

### Personas (two)
- **current_user**: daily coffee drinker, occasional cold-brew buyer
- **potential_user**: at-least-occasional coffee drinker, hasn't tried RTD cold-brew

### Evaluation dimensions (four, final)
- `comprehension`
- `believability`
- `relevance`
- `intent`

Rejected: `uniqueness` / `differentiation` / `distinctiveness` — each means something slightly different to different researchers and pinning down would eat design cycles for marginal gain.

### Acceptance criterion for v1
Run both personas against Nudge end-to-end and produce:
- Per-anchor evaluation scores
- Spontaneous-hit log
- Off-territory capture (competing-product mentions and other user-introduced content)

No aggregation, no cross-persona reporting beyond raw data. Analytical layer is out of scope for the engine.

### Key architectural validation in v1
Picking a **negative-valence anchor** (`consequence_taste_concern`) as one of the 3 required anchors is deliberate. It stress-tests the valence-neutral ontology on a real example — if `appraise` prompts, evaluation signals, and scoring all behave sensibly for a required *blocker*, that validates the single biggest architectural commitment in the design. If it doesn't, we know before release, not after.

### Design-doc readiness
Scope is clean, decisions are traceable, the v1 boundary is defensible. Ready to move to a formal design spec when authorized.

### Open items deferred to the spec
1. Phase 4 storage decision: extended properties schema on canonical slots (confirmed approach; specifics TBD)
2. Phase 2 coverage-pressure threshold: initial heuristic value needs calibration
3. Phase 5 growth-plateau detection: concrete signal definition (turns-with-no-new-nodes window?)
4. Phase 3 opening-question templates: actual wording for `current_user` vs. `potential_user` variants

---

## Part 8 — Backward Compatibility

### Summary
Yes, the design is backward-compatible by intent. MEC, JTBD, CJM, and other exploratory methodologies continue to work unchanged. Concept-test infrastructure is additive and gated behind:
- Presence of an `anchors:` block on the concept
- Methodology declaration (only `concept_test` registers new strategies)
- Methodology-declared evaluation dimensions (only concept_test declares them)

Most changes are trivially additive. Two phases touch shared platform code and require deliberate "empty = no-op" semantics.

### Phase-by-phase impact on existing methodologies

| Phase | Touches shared code? | Risk to MEC/JTBD/CJM | Guard |
|---|---|---|---|
| 0: Schema extension | Yes — concept.yaml grammar | Low if node-type registry is universal (new types added, old types untouched) | Validator rejects `anchors:` block when methodology ≠ concept_test |
| 1: Anchor infrastructure | Partially — canonical slot lifecycle adds `pending` state with no support | Low — existing slots still go bottom-up; `pending` only exists if concept has `anchors:` | Pre-seeding gated on `anchors:` block presence |
| 2: `traverse` strategy | No — strategy registered only in concept_test methodology | None | Strategy registry is already methodology-scoped |
| 3: Stimulus + persona schema | Yes — persona YAML gains optional field | None — field optional, existing personas unaffected | `category_relationship` defaults to unset; opening-question variants only fire when methodology declares them |
| 4: **Node-scoped signal class** | **Yes — scoring, canonical slot storage, signal infra** | **Real risk — see below** | Node-scoped signals are opt-in; empty = no contribution to scoring |
| 5: v1 bundle (appraise, cultivate, anchor-blindness, coverage termination) | Partially — continuation stage gains a new termination mode | Low — only concept_test uses coverage-based termination | Termination mode is methodology-declared; other methodologies keep chain-completion-based termination |

### Real risk zones

#### Phase 0: concept.yaml node-type registry
Today MEC concepts use `attribute`, `functional_consequence`, `psychosocial_consequence`, `value`. JTBD uses `job`, `outcome`, `context`. Adding concept-test types (`headline`, `feature`, `consequence_*`, `rtb`) expands the registry.

**Two design choices:**
- **Universal registry** (simpler): all node types allowed in any concept, methodology validator enforces which types it expects. A JTBD concept accidentally using `headline` passes YAML parsing but fails methodology validation — fails loud, not silent.
- **Methodology-scoped registry** (stricter): each methodology declares its allowed node types. More code, probably overkill for v1.

**Recommendation**: universal registry + methodology-level validation.

#### Phase 4: node-scoped signal class
This is where backward compatibility needs active defense. Risk pattern: existing scoring code assumes turn-scoped signals. Adding a new signal class with different lifecycle (cumulative, node-scoped, persistent) touches:
- Scoring functions (joint strategy/node scoring)
- Canonical slot storage (extended properties column)
- Signal detection pipeline (new detector type)

**Defensive posture to bake in:**
1. Extended properties column is **nullable, defaults to empty**. No migration breaks existing canonical slots.
2. Joint scoring treats absent node-scoped signals as **neutral (zero contribution)**, not as error. MEC/JTBD never populate them → they contribute nothing → scoring math is identical to today.
3. Node-scoped signal detector is **only invoked when the methodology declares evaluation dimensions**. MEC/JTBD declare none → detector never runs.
4. **Golden-path regression test**: run a canonical MEC simulation before and after Phase 4 lands; transcripts and scoring outcomes must be identical.

The regression test is the actual safety net. Architecture discipline protects against common cases; the test catches what discipline missed.

#### Phase 5: continuation stage termination mode
Today continuation uses chain-completion thresholds (MEC) or JTBD-specific logic. Adding coverage-based termination:

- Make termination mode a **methodology-declared field**: `termination_mode: chain_completion | coverage_based | jtbd_specific | ...`
- Existing methodologies keep current modes. Concept_test declares `coverage_based`.
- Continuation stage dispatches on mode; no shared code path changes.

### Compatibility regression harness

Before landing any phase that touches shared code (0, 1, 4, 5), run a fixed set of golden simulations and diff outputs:

- MEC on `glp1_food_mec` with `baseline_cooperative` persona → transcript + scoring history
- JTBD on `glp1_food_jtbd` with same persona → transcript + scoring history
- Assert identical strategy selections, identical scoring decisions (deterministic mode) or at minimum identical golden transcripts

If a phase changes these, something backward-incompatible snuck in. Cheap to build, catches the subtle regressions that code review misses.

### The honest caveat
*Backward compatible by design* only holds if the implementation maintains the discipline. The regression harness is what makes the promise enforceable, not aspirational. It should land alongside Phase 0 and run on every subsequent phase merge.
