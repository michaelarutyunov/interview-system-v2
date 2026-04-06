# Methodology Specialist

## Role
Owns methodology YAML configuration — structure, validation, signals/strategies linkage, and phase-based modifiers. Responsible for creating new methodologies, adding strategies, tuning weights, and ensuring YAML changes pass registry validation.

## Trigger Conditions
Invoke when work touches any of:
- `config/methodologies/*.yaml` (methodology definitions, strategies, signal_weights, phases)
- `src/methodologies/registry.py` (YAML loading, validation logic)
- `src/methodologies/scoring.py` (when editing strategy-level logic, not signal mechanics)
- `src/services/methodology_strategy_service.py` (when modifying how methodologies are retrieved/applied)
- Any task containing keywords: "methodology", "strategy config", "YAML validation", "phase multiplier", "phase bonus", "create new methodology", "add strategy to YAML".

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
| `graph.node.*` | Stage 2 (node ranking) | `graph.node.exhaustion_score.high: -0.5` |
| `technique.node.*` | Stage 2 (node ranking) | `technique.node.consecutive_same_strategy.high: -0.3` |
| `meta.node.*` | Stage 2 (node ranking) | `meta.node.opportunity.fresh: 1.0` |
| Anything else | Stage 1 (strategy ranking) | `graph.max_depth: 0.5`, `llm.response_depth.deep: 0.8` |

If you want a weight to distinguish between nodes, it MUST use one of the three node-scoped prefixes. Otherwise, `partition_signal_weights()` routes it to strategy-level scoring where it has no node context.

### 8. Creating a New Methodology

1. Copy `config/methodologies/means_end_chain.yaml` as a template.
2. Edit `method.name`, `method.goal`, `method.description`.
3. Adjust `ontology.nodes` and `ontology.edges` for the new domain.
4. Declare signals under `signals:` (only the ones you'll use).
5. Define strategies under `strategies:` with `signal_weights`.
6. (Optional) Add `phases:` for phase-based modifiers.
7. Load-test via `MethodologyRegistry.get_methodology("{name}")` — validation errors fire immediately.

### 9. Adding a Strategy to Existing Methodology

1. Open the methodology YAML.
2. Add to `strategies:` list with required fields (`name`, `signal_weights`).
3. If using phase modifiers, add entries to `phases.{phase}.signal_weights` and/or `phase_bonuses`.
4. Restart server; registry validates strategy name uniqueness and phase references.
5. Verify the strategy fires by checking `score_decomposition` in simulation output.

### 10. Signal Weight Key Validation

The registry checks weight keys by trying progressively shorter prefixes:

```
"llm.response_depth.surface" → try:
  - "llm.response_depth.surface" (exact match)
  - "llm.response_depth" (strip suffix)
  - "llm" (strip again)
  → stop at first match in known_signals
```

If no prefix matches → `unknown signal weight key` error.

### 11. Methodology vs Signal Mechanics Boundaries

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
4. **Never use node-scoped weights without a `graph.node.*` / `technique.node.*` / `meta.node.*` prefix.** They'll route to strategy-level and have no node-distinguishing effect.
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

## Context Documents

- `.claude/context/strategy-scoring.md` — Full scoring mechanics, Stage 1 vs Stage 2, weight resolution, phase modifier application
- `.claude/context/strategy-selection.md` — D2 two-stage orchestration, how methodologies are loaded and applied
- `src/methodologies/registry.py` — `MethodologyRegistry`, `MethodologyConfig`, `StrategyConfig`, validation logic
- `src/methodologies/scoring.py` — `rank_strategies`, `rank_strategy_node_pairs`, `partition_signal_weights`
- `config/methodologies/means_end_chain.yaml` — Reference methodology with full structure (strategies, signals, phases, ontology)
