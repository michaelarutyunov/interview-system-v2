# Strategy Flexibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate all hardcoded strategy names from the consumption layer so new methodologies can define novel strategies via YAML only.

**Architecture:** Add `focus_mode` field to `StrategyConfig` dataclass, flow it through `StrategySelectionOutput` pipeline contract, and replace all `if strategy == "X"` branches with config-driven lookups. Delete legacy dead code in `session_service.py`.

**Tech Stack:** Python, Pydantic, pytest, YAML configs

**Bead:** `interview-system-v2-yk9c`

**Design doc:** `docs/plans/2026-02-22-strategy-flexibility-design.md`

---

### Task 1: Add `focus_mode` to StrategyConfig and parse from YAML

**Files:**
- Modify: `src/methodologies/registry.py:70-78` (StrategyConfig dataclass)
- Modify: `src/methodologies/registry.py:148-158` (YAML parsing)
- Modify: `src/methodologies/registry.py:188-201` (validation)
- Test: `tests/methodologies/test_registry.py` (new file)

**Step 1: Write failing tests**

```python
# tests/methodologies/test_registry.py
"""Tests for MethodologyRegistry and StrategyConfig."""

import pytest
from src.methodologies.registry import StrategyConfig, MethodologyRegistry

VALID_FOCUS_MODES = {"recent_node", "summary", "topic"}


class TestStrategyConfigFocusMode:
    """Test focus_mode field on StrategyConfig."""

    def test_default_focus_mode_is_recent_node(self):
        config = StrategyConfig(
            name="test", description="test", signal_weights={}
        )
        assert config.focus_mode == "recent_node"

    def test_focus_mode_summary(self):
        config = StrategyConfig(
            name="test", description="test", signal_weights={},
            focus_mode="summary",
        )
        assert config.focus_mode == "summary"

    def test_focus_mode_topic(self):
        config = StrategyConfig(
            name="test", description="test", signal_weights={},
            focus_mode="topic",
        )
        assert config.focus_mode == "topic"


class TestRegistryFocusModeValidation:
    """Test that registry validates focus_mode values."""

    def test_invalid_focus_mode_raises(self, tmp_path):
        """Invalid focus_mode should fail validation."""
        yaml_content = """
method:
  name: test_method
  description: test
strategies:
  - name: bad_strategy
    description: test
    signal_weights: {}
    focus_mode: invalid_value
"""
        config_file = tmp_path / "test_method.yaml"
        config_file.write_text(yaml_content)

        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(ValueError, match="invalid focus_mode"):
            registry.get_methodology("test_method")

    def test_valid_focus_modes_pass_validation(self, tmp_path):
        """All valid focus_mode values should pass."""
        yaml_content = """
method:
  name: test_method
  description: test
strategies:
  - name: strategy_a
    description: recent node focus
    signal_weights: {}
    focus_mode: recent_node
  - name: strategy_b
    description: summary focus
    signal_weights: {}
    focus_mode: summary
  - name: strategy_c
    description: default focus
    signal_weights: {}
"""
        config_file = tmp_path / "test_method.yaml"
        config_file.write_text(yaml_content)

        registry = MethodologyRegistry(config_dir=tmp_path)
        config = registry.get_methodology("test_method")
        assert config.strategies[0].focus_mode == "recent_node"
        assert config.strategies[1].focus_mode == "summary"
        assert config.strategies[2].focus_mode == "recent_node"  # default
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/methodologies/test_registry.py -v`
Expected: FAIL — `StrategyConfig` does not have `focus_mode` field yet.

**Step 3: Implement changes to registry.py**

3a. Add `focus_mode` field to `StrategyConfig` (line 77):

```python
@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    description: str
    signal_weights: dict[str, float]
    generates_closing_question: bool = False
    focus_mode: str = "recent_node"
```

3b. Parse `focus_mode` from YAML in `get_methodology()` (inside the list comprehension at line 148-158). Add after the `generates_closing_question` line:

```python
                    focus_mode=s.get("focus_mode", "recent_node"),
```

3c. Add focus_mode validation in `_validate_config()` after the duplicate name check (after line 194). Add inside the `for i, strategy in enumerate(config.strategies):` loop:

```python
            if strategy.focus_mode not in VALID_FOCUS_MODES:
                errors.append(
                    f"strategies[{i}] '{strategy.name}': "
                    f"invalid focus_mode '{strategy.focus_mode}' "
                    f"(valid: {sorted(VALID_FOCUS_MODES)})"
                )
```

Also add `VALID_FOCUS_MODES` as a module-level constant near the top of the file:

```python
VALID_FOCUS_MODES = frozenset({"recent_node", "summary", "topic"})
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/methodologies/test_registry.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/methodologies/registry.py tests/methodologies/test_registry.py
git commit -m "feat: add focus_mode field to StrategyConfig with YAML parsing and validation"
```

---

### Task 2: Add `focus_mode` to StrategySelectionOutput pipeline contract

**Files:**
- Modify: `src/domain/models/pipeline_contracts.py:255-258` (add field after generates_closing_question)
- Test: `tests/methodologies/test_registry.py` (add contract test)

**Step 1: Write failing test**

Add to `tests/methodologies/test_registry.py` (or a new small test, but this is simple enough to go inline):

```python
# Add to tests/methodologies/test_registry.py or tests/pipeline/test_contracts.py

from src.domain.models.pipeline_contracts import StrategySelectionOutput


class TestStrategySelectionOutputFocusMode:
    def test_default_focus_mode(self):
        output = StrategySelectionOutput(strategy="explore")
        assert output.focus_mode == "recent_node"

    def test_explicit_focus_mode(self):
        output = StrategySelectionOutput(strategy="close", focus_mode="summary")
        assert output.focus_mode == "summary"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/methodologies/test_registry.py::TestStrategySelectionOutputFocusMode -v`
Expected: FAIL — `focus_mode` field doesn't exist on `StrategySelectionOutput`.

**Step 3: Add focus_mode field to StrategySelectionOutput**

In `src/domain/models/pipeline_contracts.py`, after line 258 (after `generates_closing_question`), add:

```python
    focus_mode: str = Field(
        default="recent_node",
        description="Focus selection mode: 'recent_node' (default), 'summary', or 'topic'",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/methodologies/test_registry.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/domain/models/pipeline_contracts.py tests/methodologies/test_registry.py
git commit -m "feat: add focus_mode to StrategySelectionOutput pipeline contract"
```

---

### Task 3: Populate focus_mode in StrategySelectionStage

**Files:**
- Modify: `src/services/turn_pipeline/stages/strategy_selection_stage.py:132-158`

**Step 1: No new test needed**

This is a wiring change — Task 6 (integration) will test the full flow. The existing `generates_closing_question` lookup pattern at lines 132-145 is the template.

**Step 2: Add focus_mode lookup and pass to output**

In `strategy_selection_stage.py`, after the `generates_closing_question` lookup block (after line 145), add:

```python
        focus_mode = next(
            (
                s.focus_mode
                for s in methodology_config.strategies
                if s.name == strategy
            ),
            "recent_node",
        )
```

Then add `focus_mode=focus_mode` to the `StrategySelectionOutput` constructor at line 149-158:

```python
        context.strategy_selection_output = StrategySelectionOutput(
            strategy=strategy,
            focus=focus_dict,
            signals=signals,
            node_signals=node_signals,
            strategy_alternatives=list(alternatives) if alternatives else [],
            generates_closing_question=generates_closing_question,
            focus_mode=focus_mode,
            score_decomposition=score_decomposition,
        )
```

**Step 3: Commit**

```bash
git add src/services/turn_pipeline/stages/strategy_selection_stage.py
git commit -m "feat: populate focus_mode from StrategyConfig in StrategySelectionStage"
```

---

### Task 4: Replace hardcoded focus selection with focus_mode

**Files:**
- Modify: `src/services/focus_selection_service.py:33-156`
- Modify: `tests/services/test_focus_selection_service.py` (update existing tests)

**Step 1: Update existing tests to use focus_mode instead of strategy names**

The existing tests in `TestStrategyBasedSelection` test specific strategy names (`deepen`, `broaden`, `close`, etc.). Replace them with `focus_mode`-driven tests:

```python
class TestFocusModeSelection:
    """Test focus_mode-driven focus selection (replaces strategy name matching)."""

    def test_recent_node_focus_mode(self, focus_service, mock_nodes):
        """focus_mode=recent_node returns most recent node."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy_name",
            focus_mode="recent_node",
        )
        assert result == "oat milk"

    def test_summary_focus_mode(self, focus_service, mock_nodes):
        """focus_mode=summary returns 'what we've discussed'."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy_name",
            focus_mode="summary",
        )
        assert result == "what we've discussed"

    def test_topic_focus_mode(self, focus_service, mock_nodes):
        """focus_mode=topic returns 'the topic' (placeholder)."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="any_strategy_name",
            focus_mode="topic",
        )
        assert result == "the topic"

    def test_default_focus_mode_is_recent_node(self, focus_service, mock_nodes):
        """Omitting focus_mode defaults to recent_node behavior."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="totally_new_strategy",
        )
        assert result == "oat milk"

    def test_novel_strategy_name_works_without_code_change(self, focus_service, mock_nodes):
        """A strategy name that has never existed in code should still work."""
        result = focus_service.resolve_focus_from_strategy_output(
            focus_dict=None,
            recent_nodes=mock_nodes,
            strategy="triadic_elicitation",
            focus_mode="recent_node",
        )
        assert result == "oat milk"
```

Also update existing `TestFocusResolutionOrder` and `TestEdgeCases` tests to pass `focus_mode` parameter where relevant (defaults should still work).

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/services/test_focus_selection_service.py -v`
Expected: FAIL — `resolve_focus_from_strategy_output` doesn't accept `focus_mode` yet.

**Step 3: Implement the changes**

3a. Update `resolve_focus_from_strategy_output` signature to add `focus_mode`:

```python
    def resolve_focus_from_strategy_output(
        self,
        focus_dict: Optional[Dict[str, Any]],
        recent_nodes: List[KGNode],
        strategy: str,
        graph_state: Optional[GraphState] = None,
        focus_mode: str = "recent_node",
    ) -> str:
```

3b. Pass `focus_mode` through to `_select_by_strategy`:

```python
        return self._select_by_strategy(
            recent_nodes=recent_nodes,
            strategy=strategy,
            graph_state=graph_state,
            focus_mode=focus_mode,
        )
```

3c. Replace the entire `_select_by_strategy` method body:

```python
    def _select_by_strategy(
        self,
        recent_nodes: List[KGNode],
        strategy: str,
        graph_state: Optional[GraphState] = None,  # noqa: ARG002
        focus_mode: str = "recent_node",
    ) -> str:
        """Select focus concept using focus_mode from strategy config.

        Args:
            recent_nodes: Recently added nodes
            strategy: Strategy name (for logging only)
            graph_state: Current graph state (reserved for future use)
            focus_mode: Focus mode from StrategyConfig YAML

        Returns:
            Focus concept label
        """
        log.debug(
            "focus_selecting_by_mode",
            strategy=strategy,
            focus_mode=focus_mode,
            recent_node_count=len(recent_nodes),
        )

        if not recent_nodes:
            return "the topic"

        if focus_mode == "summary":
            return "what we've discussed"

        if focus_mode == "topic":
            return "the topic"

        # Default: recent_node
        return recent_nodes[0].label
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/services/test_focus_selection_service.py -v`
Expected: All PASS

**Step 5: Update the caller in ContinuationStage**

In `src/services/turn_pipeline/stages/continuation_stage.py`, line 80, pass `focus_mode` from the strategy selection output:

```python
            focus_concept = self.focus_selection.resolve_focus_from_strategy_output(
                focus_dict=context.focus,
                recent_nodes=context.recent_nodes,
                strategy=context.strategy,
                graph_state=context.graph_state,
                focus_mode=context.strategy_selection_output.focus_mode,
            )
```

**Step 6: Commit**

```bash
git add src/services/focus_selection_service.py tests/services/test_focus_selection_service.py src/services/turn_pipeline/stages/continuation_stage.py
git commit -m "refactor: replace hardcoded strategy names in focus selection with focus_mode"
```

---

### Task 5: Replace hardcoded `close` check in ContinuationStage

**Files:**
- Modify: `src/services/turn_pipeline/stages/continuation_stage.py:152-158`
- Test: `tests/pipeline/test_continuation_stage.py` (new file)

**Step 1: Write failing tests**

```python
# tests/pipeline/test_continuation_stage.py
"""Tests for ContinuationStage closing strategy detection."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.services.turn_pipeline.stages.continuation_stage import ContinuationStage
from src.services.focus_selection_service import FocusSelectionService
from src.domain.models.pipeline_contracts import (
    StrategySelectionOutput,
    StateComputationOutput,
)


@pytest.fixture
def stage():
    return ContinuationStage(focus_selection_service=FocusSelectionService())


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.turn_number = 3
    ctx.max_turns = 10
    ctx.recent_nodes = []
    ctx.focus = None
    ctx.signals = {"meta.interview.phase": "mid"}
    ctx.state_computation_output = MagicMock(spec=StateComputationOutput)
    ctx.state_computation_output.saturation_metrics = None
    ctx.node_tracker = MagicMock()
    ctx.node_tracker.states = {}
    return ctx


class TestClosingStrategyDetection:
    """Test that closing is driven by generates_closing_question, not strategy name."""

    @pytest.mark.asyncio
    async def test_generates_closing_question_true_ends_interview(
        self, stage, mock_context
    ):
        """Any strategy with generates_closing_question=True should end interview."""
        mock_context.strategy_selection_output = StrategySelectionOutput(
            strategy="validate_pattern",  # NOT "close"
            generates_closing_question=True,
            focus_mode="summary",
        )
        mock_context.strategy = "validate_pattern"

        result = await stage.process(mock_context)
        assert result.continuation_output.should_continue is False
        assert "Closing strategy" in result.continuation_output.reason

    @pytest.mark.asyncio
    async def test_generates_closing_question_false_continues(
        self, stage, mock_context
    ):
        """Strategy without generates_closing_question should continue."""
        mock_context.strategy_selection_output = StrategySelectionOutput(
            strategy="explore_situation",
            generates_closing_question=False,
        )
        mock_context.strategy = "explore_situation"

        result = await stage.process(mock_context)
        assert result.continuation_output.should_continue is True

    @pytest.mark.asyncio
    async def test_novel_strategy_name_does_not_trigger_close(
        self, stage, mock_context
    ):
        """A strategy named 'close' but without the flag should NOT end interview."""
        mock_context.strategy_selection_output = StrategySelectionOutput(
            strategy="close",
            generates_closing_question=False,
        )
        mock_context.strategy = "close"

        result = await stage.process(mock_context)
        assert result.continuation_output.should_continue is True
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/pipeline/test_continuation_stage.py -v`
Expected: Mixed — the third test will FAIL because `if strategy == "close"` still exists.

**Step 3: Replace the hardcoded check**

In `continuation_stage.py`, replace lines 152-158:

```python
        # Before (hardcoded):
        # if strategy == "close":

        # After (config-driven):
        if context.strategy_selection_output.generates_closing_question:
            log.info(
                "session_ending",
                reason="closing_strategy",
                strategy=strategy,
                phase=current_phase,
            )
            return False, "Closing strategy selected"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/pipeline/test_continuation_stage.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/services/turn_pipeline/stages/continuation_stage.py tests/pipeline/test_continuation_stage.py
git commit -m "refactor: replace hardcoded 'close' check with generates_closing_question flag"
```

---

### Task 6: Remove hardcoded rationale in question.py

**Files:**
- Modify: `src/llm/prompts/question.py:270-281`

**Step 1: No test needed**

This is a cosmetic change — the strategy description from YAML is already injected at lines 54/91 and 196-208. The hardcoded rationale lines are redundant. Removing them is safe.

**Step 2: Replace the hardcoded block**

In `src/llm/prompts/question.py`, replace lines 270-281 (the `# Strategy-specific rationale` block):

```python
    # Strategy rationale (description already in system/user prompt from YAML)
    rationale_parts.append(f"- Strategy: {strategy}")

    if not rationale_parts:
        return f"Selected {strategy} strategy based on current state"

    return "\n".join(rationale_parts)
```

This replaces the `if strategy == "deepen"` / `elif strategy == "broaden"` / `elif strategy == "clarify"` block.

**Step 3: Run existing tests**

Run: `uv run pytest tests/ -v -k "question or prompt"`
Expected: PASS (no existing tests directly test `_build_strategy_rationale`)

**Step 4: Commit**

```bash
git add src/llm/prompts/question.py
git commit -m "refactor: remove hardcoded strategy rationale, use generic strategy name"
```

---

### Task 7: Delete legacy dead code in session_service.py

**Files:**
- Modify: `src/services/session_service.py:522-586` (delete `_select_strategy` and `_should_continue`)

**Step 1: Verify no callers exist**

Already verified: `grep -rn "_select_strategy\|_should_continue" src/` only finds the definitions in `session_service.py` and the pipeline's own methods (different classes). No tests reference them either.

**Step 2: Delete the two methods**

Delete `_select_strategy` (lines 522-548) and `_should_continue` (lines 550-586) from `SessionService`.

**Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS — nothing calls these methods.

**Step 4: Commit**

```bash
git add src/services/session_service.py
git commit -m "refactor: delete unused legacy _select_strategy and _should_continue methods"
```

---

### Task 8: Add focus_mode to methodology YAML files

**Files:**
- Modify: `config/methodologies/jobs_to_be_done.yaml:315` (add focus_mode after generates_closing_question)
- Modify: `config/methodologies/means_end_chain.yaml:299` (same)
- Modify: `config/methodologies/critical_incident.yaml:449` (same)

**Step 1: Add `focus_mode: summary` to each closing strategy**

In each file, add `focus_mode: summary` on the line after `generates_closing_question: true`:

`jobs_to_be_done.yaml` — strategy `validate_outcome`:
```yaml
    generates_closing_question: true
    focus_mode: summary
```

`means_end_chain.yaml` — strategy `validate_chain`:
```yaml
    generates_closing_question: true
    focus_mode: summary
```

`critical_incident.yaml` — strategy `validate_pattern`:
```yaml
    generates_closing_question: true
    focus_mode: summary
```

**Step 2: Validate YAML loads correctly**

Run: `uv run python -c "from src.methodologies import get_registry; r = get_registry(); [print(f'{m}: OK') for m in r.list_methodologies() if r.get_methodology(m)]"`
Expected: All methodologies print OK.

**Step 3: Commit**

```bash
git add config/methodologies/jobs_to_be_done.yaml config/methodologies/means_end_chain.yaml config/methodologies/critical_incident.yaml
git commit -m "feat: add focus_mode: summary to closing strategies in methodology YAMLs"
```

---

### Task 9: Run full test suite and ruff

**Step 1: Lint**

Run: `uv run ruff check . --fix && uv run ruff format .`

**Step 2: Full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

**Step 3: Fix any failures, then commit**

```bash
git add -A
git commit -m "chore: lint and format after strategy flexibility refactor"
```

---

### Task 10: Update design doc status and close bead

**Step 1: Update design doc**

Change status from "Approved" to "Implemented" in `docs/plans/2026-02-22-strategy-flexibility-design.md`.

**Step 2: Close bead**

```bash
bd close interview-system-v2-yk9c --reason="All hardcoded strategy names eliminated. focus_mode and generates_closing_question are now YAML-driven."
bd sync
```

**Step 3: Final commit and push**

```bash
git add docs/plans/2026-02-22-strategy-flexibility-design.md
git commit -m "docs: mark strategy flexibility design as implemented"
bd sync
git push
```
