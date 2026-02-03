# Plan 1: Fail-Fast Enforcement & Code Hygiene

**Goal**: Eliminate silent failures, remove dead code, and enforce fail-fast behavior per ADR-009.

**Estimated Steps**: 8
**Total Files Modified**: ~15

---

## Step 1: Remove Dead Code and Commented Imports

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/services/__init__.py`
- `src/services/question_service.py`

### Implementation

1. **Delete commented import in `src/services/__init__.py:2`**:
   ```python
   # DELETE THIS LINE:
   # from src.services.strategy_service import StrategyService  # DEPRECATED
   ```

2. **Verify and delete `generate_fallback_question()` in `src/services/question_service.py:267-282`**:
   - Search entire codebase for calls to `generate_fallback_question`
   - If no callers found, delete the method
   - Command to verify: `grep -r "generate_fallback_question" src/`

3. **Verify `select_focus_concept()` usage in `src/services/question_service.py:223-265`**:
   - Search for calls: `grep -r "select_focus_concept" src/`
   - If only called from `continuation_stage.py`, document that it's legacy
   - If no callers, delete it

### Acceptance Criteria
- [ ] No commented imports remain in `services/__init__.py`
- [ ] All deleted methods have zero callers confirmed via grep
- [ ] Tests pass after removal

---

## Step 2: Enforce Fail-Fast in ExtractionService

**Model**: Sonnet
**Risk**: Medium (changes error handling behavior)
**Files**:
- `src/services/extraction_service.py`

### Implementation

**Replace lines 142-151** in `extraction_service.py`:

```python
# BEFORE (silent failure):
try:
    extraction_data = await self._extract_via_llm(text, context, methodology)
except Exception as e:
    log.error("extraction_llm_error", error=str(e))
    # Graceful degradation: return empty result
    return ExtractionResult(
        is_extractable=True,
        extractability_reason=f"LLM error: {e}",
        latency_ms=int((time.perf_counter() - start_time) * 1000),
    )

# AFTER (fail-fast):
try:
    extraction_data = await self._extract_via_llm(text, context, methodology)
except Exception as e:
    log.error("extraction_llm_error", error=str(e), exc_info=True)
    raise ExtractionError(f"LLM extraction failed: {e}") from e
```

**Add import** at top of file:
```python
from src.core.exceptions import ExtractionError
```

### Acceptance Criteria
- [ ] LLM failures now raise `ExtractionError`
- [ ] Error includes original exception context (`from e`)
- [ ] Logging includes `exc_info=True` for stack trace
- [ ] Pipeline properly propagates exception to caller

---

## Step 3: Enforce Fail-Fast in MethodologyStrategyService

**Model**: Sonnet
**Risk**: Medium
**Files**:
- `src/services/methodology_strategy_service.py`

### Implementation

**3a. Replace methodology-not-found fallback (lines 81-88)**:

```python
# BEFORE:
if not config:
    log.warning(
        "methodology_not_found",
        name=methodology_name,
        available=self.methodology_registry.list_methodologies(),
    )
    # Fallback to default strategy
    return "deepen", None, [], None

# AFTER:
if not config:
    available = self.methodology_registry.list_methodologies()
    raise ConfigurationError(
        f"Methodology '{methodology_name}' not found. "
        f"Available methodologies: {available}"
    )
```

**3b. Replace no-strategies fallback (lines 176-184)**:

```python
# BEFORE:
if not strategies:
    log.warning("no_strategies_defined", methodology=methodology_name)
    return "deepen", None, [], global_signals

# AFTER:
if not strategies:
    raise ConfigurationError(
        f"Methodology '{methodology_name}' has no strategies defined. "
        f"Check the YAML config file."
    )
```

**3c. Replace no-scored-pairs fallback (lines 197-208)**:

```python
# BEFORE:
if not scored_pairs:
    log.warning("no_scored_pairs", ...)
    if node_signals:
        first_node_id = next(iter(node_signals.keys()))
        return strategies[0].name, first_node_id, [], global_signals
    return strategies[0].name, None, [], global_signals

# AFTER:
if not scored_pairs:
    raise ScoringError(
        f"No valid (strategy, node) pairs could be scored for methodology "
        f"'{methodology_name}'. Check signal weights and node state."
    )
```

**Add imports**:
```python
from src.core.exceptions import ConfigurationError, ScoringError
```

### Acceptance Criteria
- [ ] Missing methodology raises `ConfigurationError`
- [ ] Missing strategies raises `ConfigurationError`
- [ ] Empty scoring raises `ScoringError`
- [ ] Error messages include actionable debugging info

---

## Step 4: Enforce Fail-Fast in Signal Detection

**Model**: Sonnet
**Risk**: Medium
**Files**:
- `src/methodologies/signals/registry.py`
- `src/services/methodology_strategy_service.py`

### Implementation

**4a. In `registry.py`, replace catch-and-continue (lines 219-227)**:

```python
# BEFORE:
try:
    signals = await detector.detect(context, graph_state, response_text)
    all_signals.update(signals)
except Exception as e:
    log.error("signal_detector_failed", signal_name=detector.signal_name, error=str(e))

# AFTER:
try:
    signals = await detector.detect(context, graph_state, response_text)
    all_signals.update(signals)
except Exception as e:
    log.error(
        "signal_detector_failed",
        signal_name=detector.signal_name,
        error=str(e),
        exc_info=True,
    )
    raise ScorerFailureError(
        f"Signal detector '{detector.signal_name}' failed: {e}"
    ) from e
```

**4b. Apply same pattern to meta signal detection (lines 245-255)**

**4c. In `methodology_strategy_service.py:_detect_node_signals` (lines 297-310)**:

```python
# BEFORE:
except Exception as e:
    log.warning("node_signal_detection_failed", signal=detector.signal_name, error=str(e))

# AFTER:
except Exception as e:
    log.error(
        "node_signal_detection_failed",
        signal=detector.signal_name,
        error=str(e),
        exc_info=True,
    )
    raise ScorerFailureError(
        f"Node signal detector '{detector.signal_name}' failed: {e}"
    ) from e
```

**Add imports** where needed:
```python
from src.core.exceptions import ScorerFailureError
```

### Acceptance Criteria
- [ ] All signal detection failures raise `ScorerFailureError`
- [ ] Error messages identify which signal failed
- [ ] Stack traces are logged via `exc_info=True`
- [ ] ADR-009 fail-fast principle is honored

---

## Step 5: Enforce Fail-Fast in Chain Completion Signal

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/methodologies/signals/graph/chain_completion.py`

### Implementation

**5a. Replace schema load fallback (lines 49-59)**:

```python
# BEFORE:
try:
    schema = load_methodology(methodology_name)
except Exception:
    return {self.signal_name: {"complete_chain_count": 0, ...}}

# AFTER:
try:
    schema = load_methodology(methodology_name)
except Exception as e:
    raise ConfigurationError(
        f"ChainCompletionSignal failed to load methodology schema "
        f"'{methodology_name}': {e}"
    ) from e
```

**5b. Replace graph repo fallback in `_get_session_nodes` (lines 116-127)**:

```python
# BEFORE:
try:
    repo = GraphRepository(await get_db_connection())
    return await repo.get_nodes_by_session(session_id)
except Exception:
    if hasattr(context, "recent_nodes"):
        return context.recent_nodes
return []

# AFTER:
try:
    repo = GraphRepository(await get_db_connection())
    return await repo.get_nodes_by_session(session_id)
except Exception as e:
    raise GraphError(
        f"ChainCompletionSignal failed to load nodes for session "
        f"'{session_id}': {e}"
    ) from e
```

**5c. Apply same pattern to `_get_session_edges` (lines 140-158)**

**Add imports**:
```python
from src.core.exceptions import ConfigurationError, GraphError
```

### Acceptance Criteria
- [ ] Schema load failures raise `ConfigurationError`
- [ ] Graph access failures raise `GraphError`
- [ ] No silent fallbacks to empty data

---

## Step 6: Enforce Fail-Fast in Interview Phase Signal

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/methodologies/signals/meta/interview_phase.py`

### Implementation

**Replace silent exception catch (lines 88-100)**:

```python
# BEFORE:
try:
    config = self.methodology_registry.get_methodology(methodology_name)
    if config and config.phases:
        for phase_config in config.phases.values():
            if phase_config.phase_boundaries:
                return phase_config.phase_boundaries
except Exception:
    pass
return self.DEFAULT_BOUNDARIES

# AFTER:
try:
    config = self.methodology_registry.get_methodology(methodology_name)
    if config and config.phases:
        for phase_config in config.phases.values():
            if phase_config.phase_boundaries:
                return phase_config.phase_boundaries
    # No phase boundaries defined - use defaults (this is valid)
    return self.DEFAULT_BOUNDARIES
except Exception as e:
    raise ConfigurationError(
        f"InterviewPhaseSignal failed to load phase config for "
        f"'{methodology_name}': {e}"
    ) from e
```

### Acceptance Criteria
- [ ] Config loading errors raise `ConfigurationError`
- [ ] Missing phase boundaries (but valid config) returns defaults
- [ ] Clear distinction between "no config" vs "config error"

---

## Step 7: Enforce Fail-Fast in Extraction Stage

**Model**: Sonnet
**Risk**: Low
**Files**:
- `src/services/turn_pipeline/stages/extraction_stage.py`

### Implementation

**Replace concept load warning (lines 48-65)**:

```python
# BEFORE:
try:
    self.extraction.concept = load_concept(context.concept_id)
    self.extraction.element_alias_map = get_element_alias_map(self.extraction.concept)
except Exception as e:
    log.warning("concept_load_failed", concept_id=context.concept_id, error=str(e))

# AFTER:
try:
    self.extraction.concept = load_concept(context.concept_id)
    self.extraction.element_alias_map = get_element_alias_map(self.extraction.concept)
except FileNotFoundError:
    # Concept file not found - this is a configuration error
    raise ConfigurationError(
        f"Concept '{context.concept_id}' not found. "
        f"Ensure concept YAML exists in concepts/ directory."
    )
except Exception as e:
    raise ConfigurationError(
        f"Failed to load concept '{context.concept_id}': {e}"
    ) from e
```

**Add import**:
```python
from src.core.exceptions import ConfigurationError
```

### Acceptance Criteria
- [ ] Missing concept raises `ConfigurationError`
- [ ] Error message includes concept_id
- [ ] Extraction doesn't proceed with degraded element linking

---

## Step 8: Enforce Fail-Fast in GraphUpdateStage

**Model**: Sonnet
**Risk**: Medium
**Files**:
- `src/services/turn_pipeline/stages/graph_update_stage.py`

### Implementation

**Replace early returns with assertions (lines 54-62)**:

```python
# BEFORE:
if not context.extraction:
    log.warning("no_extraction_to_add", session_id=context.session_id)
    return context

if not context.user_utterance:
    log.warning("no_user_utterance_for_graph_update", session_id=context.session_id)
    return context

# AFTER:
if not context.extraction:
    raise ValueError(
        f"Pipeline contract violation: extraction is None at GraphUpdateStage. "
        f"ExtractionStage (Stage 3) must set extraction_output before GraphUpdateStage (Stage 4). "
        f"Session: {context.session_id}"
    )

if not context.user_utterance:
    raise ValueError(
        f"Pipeline contract violation: user_utterance is None at GraphUpdateStage. "
        f"UtteranceSavingStage (Stage 2) must set utterance_saving_output before GraphUpdateStage (Stage 4). "
        f"Session: {context.session_id}"
    )
```

### Acceptance Criteria
- [ ] Missing extraction raises `ValueError` with stage info
- [ ] Missing utterance raises `ValueError` with stage info
- [ ] Error messages clearly identify the contract violation

---

## Step 9: Audit and Fix PipelineContext Default Returns

**Model**: Opus (requires careful analysis)
**Risk**: High (may affect many call sites)
**Files**:
- `src/services/turn_pipeline/context.py`

### Implementation

This step requires careful analysis. The following properties return potentially dangerous defaults:

| Property | Current Default | Recommendation |
|----------|----------------|----------------|
| `strategy` | `"deepen"` | Return `None` or raise |
| `turn_number` | `1` | Raise (turn 1 when no context is a bug) |
| `methodology` | `""` | Return `None` or raise |
| `mode` | `"exploratory"` | Consider if default is valid |
| `max_turns` | `20` | Consider if default is valid |

**Approach**:
1. First, grep for all usages of each property
2. Determine if callers handle `None` or if they assume non-None
3. For each property, decide:
   - If callers already check for None: return None
   - If callers assume non-None: raise RuntimeError

**Example change for `strategy` property**:

```python
# BEFORE:
@property
def strategy(self) -> str:
    """Get strategy from StrategySelectionOutput."""
    if self.strategy_selection_output:
        return self.strategy_selection_output.strategy
    return "deepen"

# AFTER:
@property
def strategy(self) -> str:
    """Get strategy from StrategySelectionOutput.

    Raises:
        RuntimeError: If strategy_selection_output is not set
    """
    if self.strategy_selection_output:
        return self.strategy_selection_output.strategy
    raise RuntimeError(
        "Pipeline contract violation: strategy accessed before "
        "StrategySelectionStage completed. Ensure stages run in order."
    )
```

### Acceptance Criteria
- [ ] Each modified property has explicit raise or documented None return
- [ ] All call sites verified to handle new behavior
- [ ] Tests updated to expect exceptions where appropriate

---

## Testing Strategy

After each step:
1. Run `ruff check src/` - ensure no lint errors
2. Run `pytest tests/` - ensure no test regressions
3. Run a synthetic interview to verify pipeline still works

After all steps:
1. Run full test suite
2. Run 3 synthetic interviews with different methodologies
3. Verify that config errors (missing methodology, bad YAML) produce clear exceptions

---

## Rollback Plan

If issues arise:
1. Each step is independently revertable via git
2. Keep original behavior behind feature flag if needed:
   ```python
   FAIL_FAST_MODE = os.getenv("FAIL_FAST_MODE", "true").lower() == "true"
   ```
