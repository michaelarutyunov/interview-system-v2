# Design: Eliminate Hardcoded Strategy Names

**Date**: 2026-02-22
**Status**: Implemented
**Goal**: Make the strategy consumption layer fully YAML-driven so new methodologies can define new strategies without code changes.

## Problem

The scoring engine (`scoring.py`, `methodology_strategy_service.py`) is fully data-driven — it reads strategies from YAML and scores them by signal weights. However, the **consumption layer** (what happens after a strategy wins) has 5 hardcoded spots that reference specific strategy names like `"deepen"`, `"close"`, `"broaden"`, etc.

This means adding a new methodology with novel strategy names (e.g., `"triadic_elicitation"`, `"explore_ideal"`) requires code changes in addition to YAML configuration — breaking the principle of "no hardcoded keywords."

## Hardcoded Spots Inventory

| # | File | Line(s) | Hardcoded Names | Severity |
|---|------|---------|-----------------|----------|
| 1 | `src/services/focus_selection_service.py` | 134-156 | `deepen`, `broaden`, `cover`, `cover_element`, `close`, `reflect` | Medium |
| 2 | `src/llm/prompts/question.py` | 271-276 | `deepen`, `broaden`, `clarify` | Low |
| 3 | `src/services/turn_pipeline/stages/continuation_stage.py` | 152 | `close` | High |
| 4 | `src/services/session_service.py` | 545, 548 | `close`, `deepen` | Low (legacy) |
| 5 | `src/llm/prompts/qualitative_signals.py` | 123 | `deepen`, `broaden`, `stay` | None (LLM hint, not consumed by code) |

## Approach: Flat Fields on StrategyConfig (Approach A)

Add behavioral metadata as flat fields on the existing `StrategyConfig` dataclass. No new abstractions, no nested sections.

### New YAML Fields

```yaml
strategies:
  - name: validate_outcome
    description: "Confirm understanding..."
    generates_closing_question: true   # existing — now also means "terminates interview"
    focus_mode: summary                # NEW: recent_node (default) | summary | topic
    signal_weights: { ... }
```

#### `focus_mode` Values

| Value | Behavior | Current equivalent |
|-------|----------|-------------------|
| `recent_node` (default) | Focus on most recently discussed node | `deepen`, `broaden`, `reflect`, `cover` |
| `summary` | Focus on "what we've discussed" | `close` |
| `topic` | Focus on the research topic itself | Future use |

#### `generates_closing_question`

Already exists. Reused as the "terminates interview" signal in the continuation stage. When `true`:
- Continuation stage ends the interview
- Question generation stage still generates a closing question

## File Changes

### 1. `src/methodologies/registry.py` — Schema

```python
@dataclass
class StrategyConfig:
    name: str
    description: str
    signal_weights: dict[str, float]
    generates_closing_question: bool = False
    focus_mode: str = "recent_node"  # NEW
```

- Parse `focus_mode` from YAML in `get_methodology()`
- Validate `focus_mode` is one of `{"recent_node", "summary", "topic"}` in `_validate_config()`

### 2. `src/domain/models/pipeline_contracts.py` — Pipeline contract

Add `focus_mode: str = "recent_node"` to `StrategySelectionOutput` so it flows through the pipeline.

### 3. `src/services/turn_pipeline/stages/strategy_selection_stage.py` — Populate focus_mode

Look up `focus_mode` from the selected `StrategyConfig` (same pattern as existing `generates_closing_question` lookup at line 138).

### 4. `src/services/focus_selection_service.py` — Replace if/elif branches

Replace `_select_by_strategy` method:

```python
def _select_by_strategy(self, recent_nodes, strategy, focus_mode="recent_node", ...):
    if not recent_nodes:
        return "the topic"
    if focus_mode == "summary":
        return "what we've discussed"
    if focus_mode == "topic":
        return topic or "the topic"
    return recent_nodes[0].label  # recent_node (default)
```

Update `resolve_focus_from_strategy_output` signature to accept `focus_mode`.

### 5. `src/services/turn_pipeline/stages/continuation_stage.py` — Replace close check

Replace:
```python
if strategy == "close":
    return False, "Closing strategy selected"
```
With:
```python
if context.strategy_selection_output.generates_closing_question:
    return False, "Closing strategy selected"
```

### 6. `src/llm/prompts/question.py` — Remove hardcoded rationale

In `_build_strategy_rationale`, remove the `if strategy == "deepen"` block (lines 271-276). The strategy description from YAML is already injected in both system and user prompts. Replace with:

```python
rationale_parts.append(f"- Strategy: {strategy}")
```

### 7. `src/services/session_service.py` — Legacy fallbacks

Replace hardcoded `"close"`/`"deepen"` returns in legacy `_select_strategy` method with references to methodology config's closing/default strategy. Low priority since the pipeline uses `MethodologyStrategyService`.

### 8. `config/methodologies/*.yaml` — Add focus_mode

Add `focus_mode: summary` to closing strategies only:
- `jobs_to_be_done.yaml`: `validate_outcome`
- `means_end_chain.yaml`: `validate_chain`
- `critical_incident.yaml`: `validate_pattern`

All other strategies use the default (`recent_node`) — no YAML change needed.

## What Does NOT Change

- **`scoring.py`** — already fully YAML-driven
- **Signal detection services** — no strategy names referenced
- **`qualitative_signals.py:123`** — `"deepen"/"broaden"/"stay"` hint is LLM documentation, not consumed by code
- **Existing YAML signal_weights** — no changes to scoring behavior

## Validation

After implementation:
1. Run existing tests: `uv run pytest`
2. Run simulation with each methodology to verify no behavioral regression
3. Verify that creating a new methodology YAML with novel strategy names works end-to-end without code changes
