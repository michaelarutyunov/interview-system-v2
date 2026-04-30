# Methodology Parameter Flow Specification

## Current Version: 1.0

Tracks how parameters defined in `config/methodologies/*.yaml` flow through the 12-stage pipeline.
This is the cross-stage reference — for subsystem internals, see the linked Tier 3 docs.

## Strategy-Level Parameters

Each strategy in a methodology YAML defines behavioral parameters that control scoring,
continuation, question generation, and extraction.

| Parameter | Type | Default | Declared In | Consuming Stages |
|-----------|------|---------|-------------|-----------------|
| `signal_weights` | `dict[str, float]` | `{}` | YAML `strategies[].signal_weights` | Stage 6 (R) |
| `valid_when` | `str \| null` | `null` | YAML `strategies[].valid_when` | Stage 6 (R — gate) |
| `node_binding` | `"required" \| "none"` | `"required"` | YAML `strategies[].node_binding` | Stage 6 (R — routing) |
| `focus_mode` | `"recent_node" \| "summary" \| "topic"` | `"recent_node"` | YAML `strategies[].focus_mode` | Stages 6 (R), 7 (R), 8 (indirect) |
| `generates_closing_question` | `bool` | `false` | YAML `strategies[].generates_closing_question` | Stages 6 (R), 7 (R — terminal), 8 (R) |
| `bridge_direction` | `"forward" \| "backward"` | `"forward"` | YAML `strategies[].bridge_direction` | Stage 3 next-turn (R) |
| `bridge_target` | `"most_concrete" \| "most_abstract" \| "either"` | `"most_concrete"` | YAML `strategies[].bridge_target` | Stage 3 next-turn (R) |
| `extraction_mode` | `"extract_new" \| "prefer_existing"` | `"extract_new"` | YAML `strategies[].extraction_mode` | Stage 3 next-turn (R) |

### Parameter-to-Stage Matrix

| Stage | signal_weights | valid_when | node_binding | focus_mode | generates_closing_question | bridge_direction | bridge_target | extraction_mode |
|-------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 Context Loading | - | - | - | - | - | - | - | - |
| 2 Utterance Saving | - | - | - | - | - | - | - | - |
| 2.5 SRL Preprocessing | - | - | - | - | - | - | - | - |
| 3 Extraction | - | - | - | - | - | - | - | - |
| 4 Graph Update | - | - | - | - | - | - | - | - |
| 4.5 Slot Discovery | - | - | - | - | - | - | - | - |
| 5 State Computation | - | - | - | - | - | - | - | - |
| **6 Strategy Selection** | **R** | **R** | **R** | **R→W** | **R→W** | - | - | - |
| **7 Continuation** | - | - | - | **R** | **R** | - | - | - |
| **8 Question Generation** | - | - | - | **R*** | **R** | - | - | - |
| 9 Response Saving | - | - | - | - | - | - | - | - |
| **10 Scoring Persistence** | - | - | - | **W** | - | - | - | - |
| **1 Context Loading (next turn)** | - | - | - | **R*** | - | - | - | - |
| **3 Extraction (next turn)** | - | - | - | **R*** | - | **R** | **R** | **R** |

R = reads from context/registry, W = writes to context/persistence, R* = reads indirectly through a downstream service.
Bridge and extraction parameters are read on the *next* turn — Stage 3 looks up the *previous* turn's strategy config via `_get_bridge_config()`.

## Methodology-Level Parameters

These live at the top level of the methodology YAML, not inside individual strategies.

| Parameter | Type | Consuming Stages | Purpose |
|-----------|------|:----------------|---------|
| `ontology.nodes` | list | Stage 3 (R), Stage 4 (R) | Concept types for extraction validation and permitted_connections |
| `ontology.edges` | list | Stage 3 (R), Stage 4 (R), ChainTopologySignalDetector (R) | Edge types, chain_relevant flag, permitted_connections |
| `extraction_guidelines` | list | Stage 3 (R) | LLM extraction rules |
| `relationship_examples` | dict | Stage 3 (R) | Few-shot examples for extraction |
| `concept_naming_convention` | dict | Stage 3 (R) | Naming instructions for extracted concepts |
| `extractability_criteria` | dict | Stage 3 (R) | When to extract / not extract |
| `method.opening_bias` | str | Stage 8 (R) | First-question generation |
| `method.goal` | str | Stage 8 (R) | Prompt context for question generation |
| `phases.{phase}.signal_weights` | dict | Stage 6 (R) | Per-phase strategy multipliers |
| `phases.{phase}.phase_bonuses` | dict | Stage 6 (R) | Per-phase additive strategy boosts |
| `chain_completion.expected_branching` | dict | Stage 6 (R) | Target out-degree per node type |
| `chain_completion.score_threshold` | float | Stage 6 (R) | Minimum score below which conversation strategies activate |

**Dead config warning:** `phase_boundaries` was removed April 2026 — never read by any Python code. Phase boundaries come from `interview_config.yaml` (proportional) or `--phase-turns` CLI flag (explicit). See `.claude/context/phase-detection.md`.

## Engine vs Reporting Config

Some config affects the live interview engine. Other config is **reporting-only** (post-hoc analysis).

| Config | Layer | Used by |
|--------|-------|---------|
| `ontology.edges[].chain_relevant: true` | Engine | `ChainTopologySignalDetector` — filters edges for `gap.above`/`gap.below` signals during interview |
| `ontology.edges[].permitted_connections` | Extraction | LLM sees type-pair hints in system prompt (MEC strict only) |
| `ontology.nodes[].level` | Both | Used by engine (chain topology) and reporting (chain classification tiers) |
| `config/chain_rules/*.yaml` | Reporting | `scripts/reporting/generate_causal_chains.py` — post-hoc chain extraction |
| `phases.{phase}.signal_weights` | Engine | Strategy scorer applies per-phase multipliers |
| `interview_config.phases.*.n_turns` | Engine | Phase boundary calculation (when `--phase-turns` not used) |

**Key distinction:** `chain_relevant` in methodology YAML and `chain_rules` in `config/chain_rules/` are separate systems. The engine uses the former; the reporting script uses the latter. Changing chain_rules does NOT affect live interview behavior. See `.claude/context/chain-rules.md`.

## Indirect Data Flow Chains

Parameters that cross turn boundaries or travel through intermediate services.

### focus_mode: 7-stage cross-turn flow

```
YAML strategy.focus_mode
  → registry.py → StrategyConfig.focus_mode
    → Stage 6 (StrategySelectionStage.process)
      → StrategySelectionOutput.focus_mode
        → Stage 7 (ContinuationStage.process)
          → FocusSelectionService.resolve_focus_from_strategy_output()
            → ContinuationOutput.focus_concept (resolved label + node_type)
              → Stage 8 (QuestionGenerationStage.process)
                → QuestionService uses focus_concept in prompt
                  → Stage 10 (ScoringPersistenceStage._update_session_state)
                    → FocusEntry appended to session.state.focus_history
                      → Stage 1 next turn (ContextLoadingStage.process)
                        → ContextLoadingOutput.focus_history
                          → Stage 3 next turn (ExtractionStage._get_previous_focus)
                            → returns focus_label for bridge clause
```

**Key indirection**: focus_mode does not directly affect extraction. The *resolved focus label* from
the previous turn's FocusSelectionService is what extraction reads. Changing focus_mode changes
the label that extraction sees, but extraction is unaware of focus_mode itself.

### bridge_direction / bridge_target / extraction_mode: cross-turn strategy lookup

```
YAML strategy.{bridge_direction, bridge_target, extraction_mode}
  → registry.py → StrategyConfig fields
    → Stage 6 writes selected strategy name to StrategySelectionOutput
      → Stage 10 persists strategy name in FocusEntry
        → Stage 1 next turn loads focus_history
          → Stage 3 next turn (ExtractionStage._get_bridge_config)
            → Looks up the PREVIOUS turn's StrategyConfig by name
              → Reads bridge_direction, bridge_target, extraction_mode
                → Modifies extraction prompt (bridge clause + extraction instruction)
```

**Key indirection**: these parameters are not read from the *current* turn's strategy — they're
read from the *previous* turn's strategy via `_get_bridge_config()`. This means a strategy's
bridge parameters affect what happens on the *next* extraction, not during the turn where it's selected.

### valid_when: per-node gate in joint scoring

```
YAML strategy.valid_when (signal name, e.g. "convgraph.node.chain.gap.above")
  → registry.py → StrategyConfig.valid_when
    → Stage 6 (MethodologyStrategyService)
      → rank_strategy_node_pairs() in scoring.py
        → For each (strategy, node) pair:
          → Look up gate signal value from node_signal_dict
          → If falsy: pair is gated (ScoredCandidate.gated=True), skipped
          → If truthy or None: pair proceeds to scoring
```

**Constraint**: valid_when only works with `node_binding: "required"`. A strategy with
`node_binding: "none"` cannot use valid_when (registry validation raises on load).

### node_binding: scoring path selection

```
YAML strategy.node_binding
  → registry.py → StrategyConfig.node_binding
    → Stage 6 (MethodologyStrategyService)
      → "required" → rank_strategy_node_pairs() (joint scoring with node signals)
      → "none"     → rank_strategies() (global-only scoring, node_id=None)
```

**Weight partitioning**: `partition_signal_weights()` in scoring.py splits weights by
namespace. Node-scoped prefixes (`convgraph.node.*`, `canongraph.node.*`, `interview.focus.*`)
route to node_weights. For `node_binding: "none"` strategies, node_weights are discarded —
any `convgraph.node.*` weights silently have no effect. See Known Failure Modes.

### generates_closing_question: terminal condition

```
YAML strategy.generates_closing_question
  → registry.py → StrategyConfig.generates_closing_question
    → Stage 6 (StrategySelectionStage.process)
      → StrategySelectionOutput.generates_closing_question
        → Stage 7 (ContinuationStage._should_continue)
          → If true: returns False ("Closing strategy selected")
          → Interview ends after this turn
```

## Known Failure Modes

1. **Node binding mismatch silently strips weights** — A strategy with `node_binding: "none"`
   that references `convgraph.node.*` weights loses ~70% of its positive mass because
   `partition_signal_weights()` discards node-scoped weights. The strategy appears to
   "never fire." Fix: use `node_binding: "required"` for any strategy with node-scoped weights.
   See CLAUDE.md Known Failure Modes for full causal chain.

2. **valid_when on non-node-bound strategy** — Registry validation rejects this at load
   time. If bypassed, the gate check would attempt to look up a node-scoped signal with
   node_id=None, silently passing (no gate = always eligible).

3. **focus_mode indirect path misunderstood** — Changing focus_mode from "recent_node" to
   "summary" does not change the extraction prompt directly. It changes the *label* that
   FocusSelectionService resolves, which then flows through focus_history into the next
   turn's bridge clause. The extraction stage is unaware of focus_mode — it only sees
   the resolved label.

4. **Bridge parameters read from previous turn's strategy** — When strategy A selects on
   turn N and strategy B selects on turn N+1, the bridge clause in turn N+1's extraction
   uses strategy A's bridge_direction/bridge_target/extraction_mode — not strategy B's.
   This is correct behavior (the question was generated around strategy A's focus), but
   it's a common source of confusion.

5. **Dead extraction_mode before wiring** — If `extraction_mode: "prefer_existing"` is
   set in YAML but `_get_bridge_config()` returns `{}` (e.g., registry unavailable or
   strategy name not found), extraction falls back to "extract_new" silently. The
   `_get_bridge_config()` method returns `{}` on any exception — catch this by
   inspecting extraction prompts in simulation output for missing "prefer existing" wording.

## Source Files

| File | Role |
|------|------|
| `src/methodologies/registry.py` | YAML → MethodologyConfig/StrategyConfig/PhaseConfig |
| `src/methodologies/scoring.py` | `partition_signal_weights()`, `rank_strategies()`, `rank_strategy_node_pairs()` |
| `src/services/methodology_strategy_service.py` | Strategy orchestration, phase resolution |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Stage 6: reads strategy params, writes selection output |
| `src/services/turn_pipeline/stages/continuation_stage.py` | Stage 7: reads focus_mode + generates_closing_question |
| `src/services/turn_pipeline/stages/question_generation_stage.py` | Stage 8: reads strategy name + focus for prompt |
| `src/services/turn_pipeline/stages/extraction_stage.py` | Stage 3: reads bridge params from previous turn's strategy |
| `src/services/turn_pipeline/stages/scoring_persistence_stage.py` | Stage 10: persists focus_history |
| `src/services/turn_pipeline/stages/context_loading_stage.py` | Stage 1: loads focus_history into context |
| `src/services/focus_selection_service.py` | Resolves focus_mode → concrete focus label |
| `config/methodologies/*.yaml` | Parameter definitions (6 methodologies) |
