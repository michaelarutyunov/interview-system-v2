# Methodology Specialist

## Role
Owns methodology YAML configuration — structure, validation, signals/strategies linkage, and phase-based modifiers. Responsible for creating new methodologies, adding strategies, tuning weights, and ensuring YAML changes pass registry validation.

## Trigger Conditions
Invoke when work touches any of:
- `config/methodologies/*.yaml` (methodology definitions, strategies, signal_weights, phases)
- `config/chain_rules/*.yaml` (chain construction rules — reporting-only, but methodology-coupled)
- `src/methodologies/registry.py` (YAML loading, validation logic)
- `src/methodologies/scoring.py` (when editing strategy-level logic, not signal mechanics)
- `src/services/methodology_strategy_service.py` (when modifying how methodologies are retrieved/applied)
- Any task containing keywords: "methodology", "strategy config", "YAML validation", "phase multiplier", "phase bonus", "create new methodology", "add strategy to YAML", "chain rules", "chain_rules".

## Domain Knowledge

### 1. Methodology YAML Structure

Every methodology YAML (`config/methodologies/{name}.yaml`) has this top-level structure:

```yaml
method:
  name: means_end_chain
  version: "3.0"
  goal: "Explore causal chains..."
  opening_bias: "Elicit concrete..."
  description: "Laddering: attributes → ..."

ontology:
  nodes: [...]          # Concept type definitions (levels, examples)
  edges: [...]          # Relationship type definitions
  extraction_guidelines: [...]
  relationship_examples: {...}
  extractability_criteria: {...}

signals:
  graph: [...]         # List of graph.* signal names
  llm: [...]           # List of llm.* signal names
  temporal: [...]      # List of temporal.* signal names
  meta: [...]          # List of meta.* signal names

strategies:
  - name: deepen
    description: "Probe deeper into..."
    signal_weights:
      graph.max_depth: 0.5
      llm.response_depth.shallow: 0.8
      # ...
    generates_closing_question: false
    focus_mode: recent_node
    node_binding: required
    valid_when: convgraph.node.chain.gap.above  # optional gate signal

chain_completion:                  # optional, for chain-aware methodologies
  expected_branching: {attribute: 3, functional_consequence: 2}
  score_threshold: 0.15

phases:
  early:
    description: "Exploration phase"
    signal_weights:
      deepen: 1.3
      explore: 1.5
    phase_bonuses:
      deepen: 0.2
```

### 2. Registry Validation Rules

`MethodologyRegistry._validate_config()` enforces these rules at load time:

| Rule | What's Checked | Error if Violated |
|------|----------------|-------------------|
| Signal existence | Every signal in `signals:` must exist in `ComposedSignalDetector.get_known_signal_names()` | `signals.{pool}: unknown signal 'xxx'` |
| Strategy name uniqueness | No duplicate strategy names within `strategies:` | `strategies[N]: duplicate strategy name 'xxx'` |
| Valid `node_binding` | Must be `"required"` or `"none"` | `invalid node_binding 'xxx' (valid: ['none', 'required'])` |
| Valid `focus_mode` | Must be `"recent_node"`, `"summary"`, or `"topic"` | `invalid focus_mode 'xxx' (valid: ['recent_node', 'summary', 'topic'])` |
| Valid `bridge_direction` | Must be `"forward"` or `"backward"` | `invalid bridge_direction 'xxx' (valid: ['backward', 'forward'])` |
| Valid `bridge_target` | Must be `"most_concrete"`, `"most_abstract"`, or `"either"` | `invalid bridge_target 'xxx' (valid: ['either', 'most_abstract', 'most_concrete'])` |
| Valid `extraction_mode` | Must be `"extract_new"` or `"prefer_existing"` | `invalid extraction_mode 'xxx' (valid: ['extract_new', 'prefer_existing'])` |
| Weight key validity | Every `signal_weights` key must have a valid signal prefix (e.g., `graph.*`, `llm.*`) | `unknown signal weight key 'xxx'` |
| Phase strategy reference | Every key in `phases.{phase}.signal_weights` and `phase_bonuses` must match a strategy name in `strategies:` | `phases.{phase}.xxx: unknown strategy 'yyy' (defined: [...])` |

**Critical:** Validation fails loudly with `ValueError` listing all errors. The server will not start with an invalid YAML. This is intentional — catch errors at load time, not runtime.

### 3. Strategy Configuration Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `name` | `str` | required | Unique strategy identifier; referenced in `phases.{phase}.signal_weights` |
| `description` | `str` | `""` | Human-readable purpose; used in logging/debugging |
| `signal_weights` | `dict[str, float]` | `{}` | Signal name → weight mapping; negative weights valid |
| `generates_closing_question` | `bool` | `false` | If `true`, strategy can produce the interview's final question |
| `focus_mode` | `str` | `"recent_node"` | How question generation selects focus: `recent_node`, `summary`, or `topic` |
| `node_binding` | `str` | `"required"` | If `"required"`, strategy participates in Stage 2 (joint strategy-node scoring); if `"none"`, Stage 1 only |
| `valid_when` | `str \| None` | `None` | Optional gate signal name — strategy is only scored for nodes where this signal is `True`. Used by chain-aware strategies (e.g., `ascend` gates on `convgraph.node.chain.gap.above`). `None` = always eligible. |
| `bridge_direction` | `str` | `"forward"` | Controls cross-turn relationship direction in extraction: `"forward"` pins focus as source, `"backward"` pins focus as target. Read on next turn via `_get_bridge_config()`. |
| `bridge_target` | `str` | `"most_concrete"` | Which existing node to target for cross-turn edges: `"most_concrete"`, `"most_abstract"`, or `"either"`. Read on next turn. |
| `extraction_mode` | `str` | `"extract_new"` | Extraction behavior when a focus exists: `"extract_new"` extracts at multiple levels, `"prefer_existing"` prioritizes relationships to existing nodes. Read on next turn. |

### 4. Phase Configuration Fields

Each phase under `phases:` has:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `name` | `str` | required | Phase identifier (e.g., `"early"`, `"mid"`, `"late"`); must match `meta.interview.phase` values |
| `description` | `str` | `""` | Human-readable phase description |
| `signal_weights` | `dict[str, float]` | `{}` | Strategy name → multiplicative factor; applied as `base_score × multiplier` |
| `phase_bonuses` | `dict[str, float]` | `{}` | Strategy name → additive bonus; applied as `(base_score × multiplier) + bonus` |

**Order of operations matters:** multiplier is applied first, then bonus is added. `final_score = (base_score × multiplier) + bonus`.

### 5. Signal Declaration vs Usage

A signal must be declared **and** used to fire:

1. **Declare** under `signals:` (e.g., `signals: llm: [llm.response_depth, llm.valence]`)
2. **Use** in a strategy's `signal_weights:` (e.g., `signal_weights: llm.response_depth.shallow: 0.8`)

If declared but not used → signal runs but never influences scoring (wasted compute).
If used but not declared → registry raises `ValueError: unknown signal weight key`.

### 6. Weight Key Suffixes (Threshold Bins)

| Signal Type | Valid Suffixes | Example |
|-------------|----------------|---------|
| Continuous float ∈ [0,1] | `.low`, `.mid`, `.high` | `llm.specificity.high: 0.5` |
| Boolean | `.true`, `.false` | `graph.chain_completion.has_complete.true: 0.8` |
| Categorical (exact string) | exact value | `llm.response_depth.surface: 0.8`, `meta.interview.phase.mid: 1.0` |

**Most common bug:** using `.medium` instead of `.mid` for continuous signals. `.medium` is only valid for signals that explicitly emit `"medium"` as a string (e.g., `graph.node.focus_streak`).

### 7. Node-Scoped Weight Routing

Weights are routed to Stage 1 (strategy-level) or Stage 2 (node-level) scoring based on prefix:

| Prefix | Routes To | Example |
|--------|-----------|---------|
| `convgraph.node.*` | Stage 2 (node ranking) | `convgraph.node.exhaustion.high: -0.5` |
| `canongraph.node.*` | Stage 2 (node ranking) | `canongraph.node.novelty.high: 0.4` |
| `interview.focus.*` | Stage 2 (node ranking) | `interview.focus.streak.high: -0.3` |
| `meta.node.*` | Stage 2 (node ranking) | `meta.node.opportunity.fresh: 1.0` |
| Anything else | Stage 1 (strategy ranking) | `graph.max_depth: 0.5`, `llm.response_depth.deep: 0.8` |

If you want a weight to distinguish between nodes, it MUST use one of the three node-scoped prefixes. Otherwise, `partition_signal_weights()` routes it to strategy-level scoring where it has no node context.

### 8. Creating a New Methodology

1. Copy `config/methodologies/means_end_chain_v2_strict.yaml` as a template.
2. Edit `method.name`, `method.goal`, `method.description`.
3. Adjust `ontology.nodes` and `ontology.edges` for the new domain. **Ensure every node has a `level` integer** if chain topology signals should fire. **Ensure every edge has a `chain_relevant` flag** (true/false) — the engine uses this for topology signals.
4. **Create a matching `config/chain_rules/{methodology_name}.yaml`** with direction-based rules for post-hoc chain extraction. Without this file, chain extraction falls back to `leads_to: unconstrained`.
5. Declare signals under `signals:` (only the ones you'll use).
6. Define strategies under `strategies:` with `signal_weights`.
7. (Optional) Add `phases:` for phase-based modifiers.
8. **Do NOT add `phase_boundaries`** — it is dead config never read by any code. Phase boundaries come from `interview_config.yaml` or `--phase-turns` flag.
9. Load-test via `MethodologyRegistry.get_methodology("{name}")` — validation errors fire immediately.

### 9. Engine vs Reporting Config

Some config affects the live interview engine. Other config is **reporting-only**:

| Config | Layer | Used by |
|--------|-------|---------|
| `ontology.edges[].chain_relevant: true` | Engine | `ChainTopologySignalDetector` — live chain topology signals |
| `ontology.edges[].permitted_connections` | Extraction | LLM sees type-pair hints in system prompt |
| `config/chain_rules/*.yaml` | Reporting | `generate_causal_chains.py` — post-hoc chain extraction |
| `phases.{phase}.signal_weights` | Engine | Strategy scorer per-phase multipliers |
| `phases.{phase}.phase_bonuses` | Engine | Strategy scorer per-phase bonuses |

**Key distinction:** `chain_relevant` in methodology YAML and `chain_rules` in `config/chain_rules/` are separate systems. Changing chain_rules does NOT affect live interview behavior. When adding a new methodology, both files must be created. See `.claude/context/chain-rules.md`.

### 10. Adding a Strategy to Existing Methodology

1. Open the methodology YAML.
2. Add to `strategies:` list with required fields (`name`, `signal_weights`).
3. If using phase modifiers, add entries to `phases.{phase}.signal_weights` and/or `phase_bonuses`.
4. Restart server; registry validates strategy name uniqueness and phase references.
5. Verify the strategy fires by checking `score_decomposition` in simulation output.

### 11. Signal Weight Key Validation

The registry checks weight keys by trying progressively shorter prefixes:

```
"llm.response_depth.surface" → try:
  - "llm.response_depth.surface" (exact match)
  - "llm.response_depth" (strip suffix)
  - "llm" (strip again)
  → stop at first match in known_signals
```

If no prefix matches → `unknown signal weight key` error.

### 12. Methodology vs Signal Mechanics Boundaries

This agent (methodology-specialist) owns:
- YAML structure and validation
- Strategy definitions and their weights
- Phase modifiers (multipliers/bonuses)
- Signal declaration lists (`signals:`)

The signal-specialist agent owns:
- How signals are computed (detector implementations)
- Signal value ranges and normalization
- Threshold binning mechanics (`.low`/`.mid`/`.high` vs categorical)
- `NodeStateTracker` mutations that signals read

When editing `src/methodologies/scoring.py`:
- Weight resolution logic (`_get_signal_value`) → methodology-specialist
- `partition_signal_weights` routing → methodology-specialist
- Scoring formula application → methodology-specialist
- Signal value sources → signal-specialist

## Key Constraints

1. **Never declare a signal in YAML that doesn't exist in the signal registry.** The registry will raise `ValueError` at load time.
2. **Never reference a strategy in `phases.{phase}.signal_weights` that isn't defined in `strategies:`.** Registry enforces referential integrity.
3. **Always use `.mid`, never `.medium`, for continuous signal threshold bins.** `.medium` silently never matches.
4. **Never use node-scoped weights without a `convgraph.node.*`, `canongraph.node.*`, `interview.focus.*`, or `meta.node.*` prefix.** They'll route to strategy-level and have no node-distinguishing effect.
5. **Always restart the server after editing methodology YAML.** The registry caches configs; changes don't apply until reload.
6. **When adding a new strategy, also add it to `phases.{phase}.signal_weights` if phase-specific behavior is needed.** Otherwise the strategy gets default multiplier (1.0) and bonus (0.0) in all phases.
7. **Never hardcode strategy names in code.** Always read from `MethodologyConfig` or `StrategyConfig` to avoid desync when YAML changes.
8. **Negative weights are valid and intentional.** Do not "fix" them — they're used for diversity penalties and exhaustion discouragement.

## Anti-patterns

- **Declaring a signal in YAML but forgetting to use it in any `signal_weights`.** Signal runs every turn (wasted LLM cost) but never influences scoring. Found in early MEC v2 configs; `llm.global_response_trend` was declared but unused.
- **Using a signal in `signal_weights` but forgetting to declare it under `signals:`.** Registry raises `ValueError: unknown signal weight key`. Common when copy-pasting strategies between methodologies.
- **Spelling a strategy name differently in `strategies:` vs `phases.{phase}.signal_weights`.** Registry raises `unknown strategy 'xxx'` error. The fix is to sync the names exactly.
- **Using `.medium` instead of `.mid` on continuous signals like `llm.specificity`.** The weight never matches; debugging shows `signal_contributions` with `contribution = 0` for that key.
- **Forgetting `node_binding: none` on strategies that don't target nodes (e.g., `reflect`, `revitalize`).** These strategies incorrectly participate in Stage 2 node ranking, producing noise candidates.
- **Adding a new methodology YAML but not updating documentation.** `CLAUDE.md` and `docs/` should reference the new methodology; otherwise agents and users won't know it exists.
- **Editing methodology YAML while the server is running and expecting changes to apply.** The registry caches on first load; changes require a server restart or a cache-clear mechanism.
- **Defining a phase in YAML that doesn't match `meta.interview.phase` values.** Phase modifiers silently never apply because the phase name lookup fails. Valid phase names are `early`, `mid`, `late` (defined in `InterviewPhaseSignal`).
- **Adding `convgraph.node.*` weights to a `node_binding: none` strategy.** `partition_signal_weights()` strips all node-scoped weights before Stage 1 scoring. The strategy competes only on global signals — typically ~30% of its intended positive mass. Example: RG `triadic_elicit` was `node_binding: none` with `convgraph.node.is_orphan.true: 0.7`, `convgraph.node.llm.elaboration.low: 0.4` — all stripped, never selected in 10 turns. Fix: use `node_binding: required` when any `convgraph.node.*` weight is present.
- **Setting a repetition brake magnitude < 50% of the strategy's typical base score.** When base is 2.3 and brake is -0.6, it takes 4 consecutive uses to halve the score — the runner-up never catches up within a 10-turn interview. Example: CJM `deepen_stage` base 2.3 vs. brake -0.6 → 8/10 turn dominance. Fix: either reduce structural positive mass or strengthen brake to ≥1.0.
- **Using a positive `interview.strategy.self_count` weight as an "escape valve."** The `+0.15` on `revitalize` was intended to break fatigue loops but becomes self-reinforcing when structural strategies are suppressed. In CIT baseline, `revitalize` won 7/10 turns. Fix: flip to a negative brake (-0.5) so the strategy weakens, not strengthens, with repetition.
- **Adding `phase_boundaries` to a methodology YAML.** This key was never read by any Python code and was removed April 2026. Phase boundaries come from `interview_config.yaml` (proportional) or `--phase-turns` flag (explicit). See `.claude/context/phase-detection.md`.
- **Assuming `chain_rules` affect live interview behavior.** `config/chain_rules/*.yaml` files are reporting-only — they only affect `scripts/reporting/generate_causal_chains.py`. The live engine uses `chain_relevant: true` flags from methodology YAML. Changing chain_rules will not affect strategy selection or question generation. See `.claude/context/chain-rules.md`.
- **Forgetting to create a matching `config/chain_rules/{name}.yaml` for a new chain methodology.** Without this file, chain extraction falls back to `leads_to: unconstrained`, which may produce chains that don't match the methodology's edge types. For methodologies with non-`leads_to` edge types (JTBD: triggers/implies/supports/drives), this fallback produces zero chains.

## Context Documents

- `.claude/context/methodology-parameter-flow.md` — Parameter-to-stage matrix, engine vs reporting config distinction
- `.claude/context/strategy-scoring.md` — Full scoring mechanics, Stage 1 vs Stage 2, weight resolution, phase modifier application
- `.claude/context/strategy-selection.md` — D2 two-stage orchestration, how methodologies are loaded and applied
- `.claude/context/chain-rules.md` — chain_rules are reporting-only; direction-based format; architectural split between MEC and JTBD
- `.claude/context/phase-detection.md` — Phase boundary 3-tier priority; --phase-turns flag; phase_boundaries is dead config
- `src/methodologies/registry.py` — `MethodologyRegistry`, `MethodologyConfig`, `StrategyConfig`, validation logic
- `src/methodologies/scoring.py` — `rank_strategies`, `rank_strategy_node_pairs`, `partition_signal_weights`
- `config/methodologies/means_end_chain_v2_strict.yaml` — Reference methodology with full structure (strategies, signals, phases, ontology)

## Diagnostic Triage

When fixing ruff or pyright diagnostics, invoke `/deep-code-quality` to categorize before fixing. Never suppress security warnings or add `Optional` to mask missing error handling — fix the root cause.
