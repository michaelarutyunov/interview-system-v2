---
task: Implement jobs_to_be_done_v3 methodology configuration
test_command: "uv run pytest tests/unit/test_methodology_registry.py tests/calibration/ -v -k 'jtbd' && uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15 --methodology jobs_to_be_done_v3"
timeout_seconds: 300
working_directory: ~/projects/interview-system-v2
max_iterations: 5
depends: []
---

# Coding Task: Jobs-to-be-Done v3 Methodology

## Agent Model Recommendation

**Primary agent:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
**Mode:** Standard (not extended thinking)
**Rationale:** This task is YAML-authoring and signal registration — no algorithmic complexity requiring deep reasoning. Sonnet 4 has sufficient context window for the full jtbd_v2 YAML plus this spec simultaneously. Use Opus only if simulation output validation requires multi-turn judgment calls.

---

## Executive Summary

Create `config/methodologies/jobs_to_be_done_v3.yaml` — a new JTBD methodology configuration that replaces the generic "jobs + motivations" frame of v2 with a **causal narrative reconstruction** approach: timeline-anchored, force-structured, pyramid-aware. Register one new LLM signal (`llm.temporal_grounding`) required by the veto mechanism. No changes to Python source beyond signal registration.

**Scope boundary:** YAML authoring + signal registration only. Do not modify strategy selection logic, scoring engine, or question generation prompts. The methodology registry loads YAML at runtime — a well-formed YAML file is sufficient for the system to use it.

**Key changes from v2:**
- 7 strategies → 7 strategies (3 replaced, 4 retained/reframed)
- 8 node types → 8 node types (descriptions extended, 1 attribute added, 2 edges added)
- Signals: all v2 signals retained + 3 existing system signals promoted + 1 new signal added
- Phases: early/mid/late retained, weights restructured around timeline logic

---

## Background and Design Rationale

### Why v3

v2 treats JTBD as a generic motivational interview: surface jobs, probe obstacles, ladder into values. v3 treats JTBD as the **Moesta/Christensen switch interview**: reconstruct the specific causal journey that led a respondent to hire a new solution and fire an old one. The research objective is different, so the strategy set and signal weights must be different.

The NotebookLM analysis of JTBD moderation practice identified three structural frameworks operating simultaneously in expert JTBD interviews:

- **Purchase Timeline** (navigational spine): First Thought → Passive Looking → Active Looking → Deciding → Consuming
- **Four Forces** (content targets): Push (frustration with old), Pull (attraction to new), Anxiety (fear of new), Habit/Inertia (comfort with old)
- **JTBD Pyramid** (abstraction ladder): Product Job → Core Job → Role Identity → Image Identity → Emotional Job

A skilled moderator tracks all three simultaneously. v3 encodes this structure into strategy selection logic.

### Core architectural decisions

**Decision 1: Tie-breaking without new architecture**
When `probe_forces` and `dig_motivation` score nearly equally, the tie-breaking rule is: use asymmetric signal weights in Tier 2 (not a new arbitration layer). `dig_motivation` gets a strong bonus on `llm.intellectual_engagement.high`; `probe_forces` gets a strong bonus on `llm.valence.low`. These signals point in opposite directions and naturally differentiate the two strategies.

**Decision 2: Temporal grounding as Tier 1 veto**
The `anchor_timeline` strategy must win in early phase when the respondent is speaking in generalities rather than recalling a specific episode. This is implemented as a boolean veto condition (`llm.temporal_grounding = unanchored`) using the existing Tier 1 veto mechanism, not a weight differential. This requires registering one new signal.

**Decision 3: Force variant selection in question generation, not strategy selection**
The strategy scorer selects `probe_forces` as the strategy. Which of the four forces to probe (Push/Pull/Anxiety/Habit) is decided by the question generation LLM from full conversation context. This avoids four new coverage-tracking signals. The strategy description must instruct the question generation layer accordingly.

**Decision 4: Conservative ontology expansion**
No new node types. Three existing node descriptions are extended to absorb new JTBD concepts (anxiety, inertia, switching trigger). One attribute (`status: hired|fired`) is added to `solution_approach`. Two new edge types are added (`replaced_by`, `preceded`). This keeps the extraction LLM's classification task tractable.

---

## Step 1: Register New Signal

**File:** `src/services/signal_detection/llm_signals.py` (or wherever LLM signals are defined — locate by searching for `llm.specificity` or `llm.engagement`)

**Signal to add:**

```
Signal name:   llm.temporal_grounding
Signal group:  llm (global, not node-level)
Values:        anchored | unanchored
Default:       unanchored
```

**Semantic definition:**
- `anchored`: Respondent is recalling a specific remembered episode with temporal markers. Evidence: past tense verbs with time references ("last Tuesday", "before that meeting", "when I switched"), named events, sequential narrative ("first I... then I...").
- `unanchored`: Respondent is speaking in generalities about habits, preferences, or abstract patterns, without reference to a specific incident. Evidence: present tense habitual statements ("I always...", "I usually...", "I tend to..."), hypotheticals, brand opinions without situational context.

**Key distinction from `llm.specificity`:** A respondent can be highly specific AND unanchored. "I always buy Oatly Barista, the large carton, from Sainsbury's" is specific but unanchored — it describes a habit, not an episode.

**LLM scoring prompt addition** (add to the batch LLM signal detection prompt alongside other LLM signals):

```
temporal_grounding: Is the respondent describing a specific remembered episode (anchored) or speaking in general terms about habits/preferences (unanchored)?
- anchored: past-tense episodic recall, temporal markers, sequential narrative
- unanchored: present-tense habits, hypotheticals, general opinions, brand preferences without situational grounding
Score: anchored | unanchored
```

**Moderator guide entry** (add to `docs/signals_moderator_guide.md`):

```
| **llm.temporal_grounding** | Whether response is anchored to a specific episode | anchored = past-tense recall with time markers; unanchored = general habits/opinions |
```

**Verification:** `grep -r "temporal_grounding" src/` returns at least one result after implementation.

---

## Step 2: Add Existing System Signals to Methodology

The following signals exist in the system but are not used in v2. They are referenced in v3 YAML without requiring any code changes.

| Signal | Source | Usage in v3 |
|--------|--------|-------------|
| `graph.avg_depth` | Graph signals | Stable indicator of sustained surface-level conversation; supplements `graph.max_depth` |
| `graph.chain_completion.ratio` | Graph signals | Soft gate for `dig_motivation`: low ratio = functional jobs not yet established |
| `graph.node.recency_score` | Node signals | `anchor_timeline` uses this to resurface early-mentioned nodes that lack follow-up |

Confirm these signal names exactly match the system's signal registry before referencing in YAML. Search: `grep -r "chain_completion" src/` and `grep -r "recency_score" src/`.

---

## Step 3: Author `config/methodologies/jobs_to_be_done_v3.yaml`

Use `config/methodologies/jobs_to_be_done_v2.yaml` as the structural template. The sections below specify every change from v2.

### 3.1 Header

```yaml
method:
  name: jobs_to_be_done_v3
  version: "3.0"
  goal: "Reconstruct the causal journey that led a customer to hire a new solution and fire an old one"
  opening_bias: "Ask about a specific recent time they switched from one solution to another, or first tried something new. Anchor to a real episode, not a general opinion."
  description: "Switch-interview framework reconstructing the purchase timeline, four forces of progress, and motivational hierarchy"
```

### 3.2 Ontology — Nodes

**Keep all 8 node types from v2.** Extend descriptions on three nodes, add `status` attribute to one.

**`job_trigger`** — extend description:
```yaml
description: "Event or stimulus that initiates the job — includes both recurring situational cues 
  (when I have early meetings) and the specific one-time incident that triggered search for a new 
  solution (the switching trigger). For switching triggers, capture the concrete episode: what 
  happened, when, what made it the last straw."
```

**`pain_point`** — extend description:
```yaml
description: "Obstacle, frustration, or resistance that prevents job completion or switching — 
  includes: (1) frustrations with the current/prior solution (Push force), (2) fears or anxieties 
  about adopting the new solution (what if it doesn't work?), and (3) inertia — reasons the 
  respondent stayed with the prior solution despite its shortcomings (it's familiar, switching 
  feels effortful). Distinguish which type is present in the label if possible."
```

**`solution_approach`** — extend description and add status attribute:
```yaml
description: "Current or prior method for accomplishing the job. Use status attribute to 
  distinguish: 'fired' = the solution that was replaced, 'hired' = the new solution adopted. 
  This distinction is required — it anchors the Four Forces analysis."
attributes:
  status:
    values: [hired, fired, considering, unknown]
    default: unknown
    description: "Whether this solution was adopted (hired), replaced (fired), under consideration, or unknown"
```

**All other node types** (`job_statement`, `job_context`, `gain_point`, `emotional_job`, `social_job`): carry forward from v2 unchanged.

### 3.3 Ontology — Edges

Carry forward all 7 edges from v2. Add two new edges:

```yaml
- name: replaced_by
  description: "Prior solution (fired) was substituted by new solution (hired). 
    Directional: source=fired solution, target=hired solution. 
    Core edge for representing the switch event."

- name: preceded
  description: "Temporal sequencing between events on the purchase timeline. 
    Source event occurred before target event. 
    Use to connect timeline stages: switching_trigger preceded active_looking, 
    active_looking preceded deciding, etc."
```

### 3.4 Extraction Guidelines

Replace v2 extraction guidelines with:

```yaml
extraction_guidelines:
  - "Prioritise anchoring to a specific episode: listen for past-tense episodic language 
     ('last time I...', 'when I switched...') over general habits"
  - "Identify the switching trigger: the specific incident that made the respondent start 
     looking for something new — not a recurring frustration but the event that crossed the threshold"
  - "Extract both solutions: the one that was fired (prior) and the one that was hired (new), 
     and label each with status attribute"
  - "Map all four forces: Push (what was wrong with the old), Pull (what attracted them to the new), 
     Anxiety (what they feared about switching), Habit/Inertia (what kept them from switching sooner)"
  - "Listen for timeline markers: 'first I thought', 'then I started looking', 'eventually I decided' — 
     use preceded edges to sequence these"
  - "Extract emotional and social jobs: identity statements, feeling words, peer references, 
     social signal language"
  - "Connect jobs to their context using occurs_in; connect solutions using replaced_by"
  - "Extract gain_points as what the hired solution delivered on — the Pull force made concrete"
  - "Do not conflate pain_point subtypes: Push (old solution failed), Anxiety (fear of new), 
     Inertia (comfort with old) are distinct even when all labelled as pain_point"
```

### 3.5 Signals

```yaml
signals:
  graph:
    - graph.node_count
    - graph.orphan_count
    - graph.max_depth
    - graph.avg_depth          # promoted from system — more stable than max_depth
    - graph.chain_completion.ratio  # promoted — soft gate for pyramid ascension

  llm:
    - llm.response_depth
    - llm.valence
    - llm.certainty
    - llm.specificity
    - llm.engagement
    - llm.intellectual_engagement
    - llm.temporal_grounding   # new signal — anchored | unanchored

  temporal:
    - temporal.strategy_repetition_count
    - temporal.turns_since_strategy_change

  meta:
    - meta.interview.phase
    - meta.conversation.saturation
    - meta.canonical.saturation
```

Note: `meta.interview_progress` intentionally excluded (same reason as v2: deprecated for JTBD, replaced by saturation signals).

### 3.6 Strategies

Seven strategies total. Four carried from v2 with weight adjustments, three new.

---

#### Strategy 1: `anchor_timeline` *(new — replaces `explore_situation`)*

```yaml
- name: anchor_timeline
  description: "Ground the conversation in a specific remembered episode by reconstructing 
    the purchase timeline backward from the switch decision. Ask for the specific moment, 
    what was happening, what triggered the search. Do not accept general habits as an answer — 
    probe for the concrete episode. This strategy fires as a veto when the respondent is 
    unanchored (speaking in generalities) regardless of other signal scores."
  veto_condition: "llm.temporal_grounding = unanchored AND meta.interview.phase = early"
  signal_weights:
    # Primary trigger: unanchored + early phase
    llm.temporal_grounding.unanchored: 1.5
    meta.interview.phase.early: 0.8

    # Suppress when already anchored
    llm.temporal_grounding.anchored: -1.0

    # Suppression: don't anchor when fatigued or late
    llm.global_response_trend.fatigued: -0.8
    meta.interview.phase.late: -2.0

    # Node targeting: prefer early-mentioned nodes not yet followed up
    graph.node.recency_score: -0.3       # low recency = mentioned early, not revisited
    graph.node.novelty.high: 0.4
    graph.node.focus_streak.none: 0.5
    graph.node.focus_streak.high: -0.6

    # Diversity brake
    temporal.strategy_repetition_count: -1.2
    temporal.turns_since_strategy_change: -0.4
```

---

#### Strategy 2: `probe_forces` *(new — replaces `probe_alternatives`)*

```yaml
- name: probe_forces
  description: "Systematically excavate the Four Forces of Progress: Push (frustrations with 
    the prior solution), Pull (attractions of the new solution), Anxiety (fears about switching), 
    and Habit/Inertia (reasons to stay with the old solution). 
    
    QUESTION GENERATION INSTRUCTION: Select which force to probe based on full conversation 
    context — prefer whichever force has least coverage so far. Force selection heuristics: 
    llm.valence.low + pain_point nodes → Push or Anxiety; llm.valence.high + gain_point nodes 
    → Pull; low engagement + solution_approach(fired) nodes present → Habit/Inertia."
  signal_weights:
    # Primary: negative valence suggests friction territory (Push or Anxiety)
    llm.valence.low: 0.9
    llm.valence.mid: 0.3

    # Positive valence suggests Pull territory
    llm.valence.high: 0.5

    # Specificity: concrete answers can be probed for force
    llm.specificity.high: 0.4
    llm.specificity.mid: 0.2

    # Engagement: mid engagement = probing OK
    llm.engagement.mid: 0.4
    llm.engagement.high: 0.5
    llm.engagement.low: -0.3

    # Graph coverage: orphans = unexplored forces
    graph.orphan_count: 0.4
    graph.node.is_orphan.true: 0.6

    # Saturation suppression
    meta.canonical.saturation.high: -0.5
    meta.conversation.saturation.high: -0.4

    # Node freshness
    graph.node.focus_streak.none: 0.5
    graph.node.focus_streak.medium: -0.4
    graph.node.focus_streak.high: -0.7
    graph.node.novelty.high: 0.5
    graph.node.novelty.medium: 0.2
    graph.node.focus_count.high: -0.6
    graph.node.focus_count.none: 0.3
    graph.node.exhaustion_score.low: 0.5

    # Diversity
    temporal.strategy_repetition_count: -0.8
```

---

#### Strategy 3: `struggling_moment` *(new — replaces `clarify_assumption`)*

```yaml
- name: struggling_moment
  description: "Probe for the concrete failure scenario of the prior solution — the specific 
    incident where it let the respondent down badly enough to prompt search for an alternative. 
    This is the highest-yield JTBD data point. Fires when frustration is expressed with 
    specificity but the switching trigger has not yet been established. 
    Ask backward-looking questions: 'Tell me about the last time the old solution really 
    failed you. What was happening?'"
  signal_weights:
    # Primary: negative valence + high specificity = articulated frustration worth excavating
    llm.valence.low: 1.0
    llm.specificity.high: 0.6
    llm.specificity.mid: 0.3

    # Engagement: need engagement to go deep on painful moments
    llm.engagement.high: 0.6
    llm.engagement.mid: 0.4
    llm.engagement.low: -0.6

    # Graph: pain_point nodes present but no switching trigger yet = prime target
    graph.node_count: 0.2        # some nodes extracted = have material to probe
    graph.orphan_count: 0.3      # orphaned pain nodes = unconnected frustrations

    # Temporal: works best mid-phase after rapport established
    meta.interview.phase.early: -0.5
    meta.interview.phase.mid: 0.6
    meta.interview.phase.late: 0.3

    # Response quality
    llm.response_depth.moderate: 0.3
    llm.response_depth.deep: 0.4
    llm.response_depth.surface: -0.3

    # Saturation
    meta.canonical.saturation.high: -0.6
    meta.conversation.saturation.high: -0.5

    # Node targeting
    graph.node.focus_streak.none: 0.4
    graph.node.focus_streak.low: 0.5
    graph.node.focus_streak.high: -0.6
    graph.node.novelty.high: 0.3
    graph.node.exhaustion_score.low: 0.5

    # Diversity: struggling_moment is high-yield but fatiguing if repeated
    temporal.strategy_repetition_count: -1.2
    temporal.strategy_repetition_count.high: -0.8
```

---

#### Strategy 4: `dig_motivation` *(retained from v2 — reframed as pyramid ascension)*

```yaml
- name: dig_motivation
  description: "Ascend the JTBD Pyramid from product jobs (concrete tasks) toward identity 
    and emotional jobs (who the respondent wants to become, how they want to feel). 
    Only valid after functional jobs are established — chain_completion.ratio acts as a 
    soft gate. Use 'why' questions that invite reflection on meaning, not just function."
  signal_weights:
    # Pyramid ascension gate: chain completion indicates functional base established
    graph.chain_completion.ratio: 0.6   # higher ratio = base established, safe to ascend
    graph.avg_depth: 0.4                # deeper average = more established base

    # Primary: intellectual engagement = motivational reasoning surfaced
    llm.intellectual_engagement.high: 0.8   # KEY DIFFERENTIATOR vs probe_forces
    llm.intellectual_engagement.mid: 0.4

    # Engagement safety
    llm.engagement.high: 0.5
    llm.engagement.mid: 0.3
    llm.engagement.low: -0.6

    # Response depth
    llm.response_depth.moderate: 0.3
    llm.response_depth.deep: 0.4
    llm.response_depth.surface: 0.3    # surface on a motivation node → dig deeper
    llm.response_depth.shallow: 0.3

    # Positive valence: aspirational territory is safe to probe
    llm.valence.high: 0.4
    llm.valence.mid: 0.2
    llm.valence.low: -0.2              # negative valence → probe_forces is better choice

    # Saturation suppression
    meta.canonical.saturation.high: -0.5
    meta.conversation.saturation.high: -0.4

    # Heavy repetition brake (same as v2 — prevents dig_motivation dominance)
    temporal.strategy_repetition_count: -1.5
    temporal.strategy_repetition_count.high: -1.0

    # Node signals
    graph.node.focus_streak.low: 0.5
    graph.node.focus_streak.medium: -0.4
    graph.node.focus_streak.high: -0.8
    graph.node.novelty.high: 0.2
    graph.node.focus_count.high: -0.6
    graph.node.focus_count.none: 0.3
    graph.node.canonical_novelty.confirming: 0.2
```

---

#### Strategy 5: `uncover_obstacles` *(retained from v2 — weights adjusted)*

```yaml
- name: uncover_obstacles
  description: "Surface pain points and frustrations preventing jobs from being done well — 
    covering Push force (old solution failures) and probing for unarticulated obstacles. 
    Distinct from probe_forces (which covers all four forces systematically) and 
    struggling_moment (which targets the specific failure incident): this strategy 
    addresses ongoing, recurring obstacles."
  signal_weights:
    llm.valence.low: 0.9
    llm.valence.mid: 0.3
    llm.response_depth.moderate: 0.2
    llm.certainty.mid: 0.2
    llm.engagement.mid: 0.3

    meta.canonical.saturation.high: -0.5
    meta.conversation.saturation.high: -0.4

    temporal.strategy_repetition_count: -0.7

    graph.node.is_orphan.true: 0.7
    graph.node.yield_stagnation.false: 0.5
    graph.node.exhaustion_score.low: 0.4
    graph.node.focus_streak.medium: -0.3
    graph.node.focus_streak.high: -0.6
    graph.node.novelty.high: 0.4
    graph.node.novelty.medium: 0.2
    graph.node.focus_count.high: -0.6
    graph.node.focus_count.none: 0.3
    graph.node.canonical_novelty.new: 0.5
```

---

#### Strategy 6: `validate_outcome` *(retained from v2 — unchanged)*

Carry forward from v2 exactly. Phase gate (`meta.interview.phase.early: -3.0`, `meta.interview.phase.mid: -3.0`) is critical — do not modify.

---

#### Strategy 7: `revitalize` *(retained from v2 — unchanged)*

Carry forward from v2 exactly. Heavy repetition penalty (`temporal.strategy_repetition_count: -1.5`) is critical — do not modify.

---

### 3.7 Phases

```yaml
phases:
  early:
    description: "Timeline anchoring phase — establish the specific switch episode before exploring motivations. 
      anchor_timeline dominates via veto condition. probe_forces begins light coverage. 
      Pyramid ascension (dig_motivation) suppressed until functional base exists."
    signal_weights:
      anchor_timeline: 1.8        # Primary early objective
      probe_forces: 1.1           # Begin force coverage
      struggling_moment: 0.4      # Light probe only — rapport not yet established
      uncover_obstacles: 0.5
      dig_motivation: 0.3         # Suppressed: base not yet established
      validate_outcome: 0.2
      revitalize: 0.8
    phase_bonuses:
      anchor_timeline: 0.3        # Additive — ensure it fires even with zero base score
      probe_forces: 0.1

  mid:
    description: "Force excavation and pyramid ascension phase — the 20-minute threshold where 
      highest-yield data emerges. probe_forces and struggling_moment dominate. 
      dig_motivation activates as chain_completion rises. energy_following via 
      intellectual_engagement weight differential."
    signal_weights:
      probe_forces: 1.4           # Primary mid objective
      struggling_moment: 1.3      # High-yield window — rapport established
      dig_motivation: 1.1         # Pyramid ascension now valid
      uncover_obstacles: 1.2
      anchor_timeline: 0.4        # Residual — re-anchor if respondent drifts to generalities
      validate_outcome: 0.4
      revitalize: 1.0
    phase_bonuses:
      probe_forces: 0.2
      struggling_moment: 0.15
      dig_motivation: 0.1
      uncover_obstacles: 0.2

  late:
    description: "Synthesis and validation phase — consolidate the causal narrative, 
      complete any uncovered forces, validate understanding."
    signal_weights:
      validate_outcome: 1.5
      dig_motivation: 0.8         # Final pyramid push if identity/emotional jobs not yet reached
      probe_forces: 0.7           # Mop up uncovered forces
      struggling_moment: 0.6      # Final excavation if not yet achieved
      uncover_obstacles: 1.0
      anchor_timeline: 0.2
      revitalize: 0.6
    phase_bonuses:
      validate_outcome: 0.25
```

---

## Step 4: Verification

### 4.1 YAML Validity

```bash
cd ~/projects/interview-system-v2
uv run python -c "
from src.methodologies.registry import get_registry
registry = get_registry()
config = registry.get_methodology('jobs_to_be_done_v3')
print(f'Loaded: {config.name}')
print(f'Strategies: {[s.name for s in config.strategies]}')
print(f'Phases: {list(config.phases.keys())}')
print(f'Signals: {sum(len(v) for v in config.signals.values())} total')
"
```

Expected output:
```
Loaded: jobs_to_be_done_v3
Strategies: ['anchor_timeline', 'probe_forces', 'struggling_moment', 'dig_motivation', 'uncover_obstacles', 'validate_outcome', 'revitalize']
Phases: ['early', 'mid', 'late']
Signals: 18 total
```

### 4.2 Signal Registration

```bash
grep -r "temporal_grounding" src/
```
Must return at least 2 results (definition + prompt inclusion).

### 4.3 Unit Tests

```bash
uv run pytest tests/unit/test_methodology_registry.py -v -k 'jtbd'
```

All existing JTBD tests should pass. Add one test asserting `jobs_to_be_done_v3` loads without error.

### 4.4 Simulation Smoke Test

```bash
uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 15 --methodology jobs_to_be_done_v3
```

Inspect output for:
- [ ] `anchor_timeline` selected at least once in turns 1–5
- [ ] `probe_forces` selected at least twice in turns 6–15
- [ ] `validate_outcome` selected at least once
- [ ] No strategy dominates >50% of turns (diversity check)
- [ ] `dig_motivation` does not appear in turn 1 or 2

### 4.5 Signal Coverage Check

```bash
uv run python -c "
from src.methodologies.registry import get_registry
from src.services.signal_detection import GlobalSignalDetectionService

registry = get_registry()
config = registry.get_methodology('jobs_to_be_done_v3')
detector = registry.create_signal_detector(config)
declared = set(sum(config.signals.values(), []))
detectable = set(detector.signal_names)
missing = declared - detectable
if missing:
    print(f'MISSING SIGNALS: {missing}')
else:
    print('All declared signals are detectable')
"
```

Must output `All declared signals are detectable`.

---

## Step 5: Calibration Notes (Post-Verification)

These are not automated acceptance criteria but should be assessed by reviewing simulation transcripts:

- **Does `anchor_timeline` correctly fire when the respondent gives a generic opener?** The veto condition depends on `llm.temporal_grounding = unanchored` being reliably detected on first turns.
- **Does `probe_forces` produce varied force targeting across turns?** Check that question generation is selecting different forces, not repeating Push.
- **Does `dig_motivation` wait for chain completion?** It should not appear in the first 4–5 turns. If it does, increase the `graph.chain_completion.ratio` weight or lower the `mid` phase multiplier.
- **Is `struggling_moment` reaching the switching trigger?** Look for questions that ask about a specific failure incident, not just general frustrations.

These observations should inform weight tuning in a follow-up calibration pass, not block initial delivery.

---

## Reference Files

| File | Purpose |
|------|---------|
| `config/methodologies/jobs_to_be_done_v2.yaml` | Base template — structural reference |
| `docs/signals_moderator_guide.md` | Signal definitions — add `llm.temporal_grounding` entry |
| `src/services/signal_detection/llm_signals.py` | Signal registration — add `temporal_grounding` |
| `tests/unit/test_methodology_registry.py` | Add one loading test for v3 |
| `tests/calibration/` | Simulation-based calibration tests |
