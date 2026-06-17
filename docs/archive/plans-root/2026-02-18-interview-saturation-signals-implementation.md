# Interview Saturation Signals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace broken `meta.interview_progress` with two methodology-agnostic saturation signals based on information velocity (EWMA of new node discovery rate).

**Architecture:**
1. Add velocity tracking fields to SessionState (DB persistence) and ContextLoadingOutput (pipeline access)
2. Compute EWMA velocity each turn in ScoringPersistenceStage
3. Two new signals read velocity from context and compute saturation (0-1 scale)
4. Register signals in YAML, add weights to validate_outcome strategy

**Tech Stack:**
- Pydantic BaseModel for data contracts
- Signal auto-registration via `__init_subclass__`
- EWMA (Exponentially Weighted Moving Average) with α=0.4 (hardcoded)

---

## Task 1: Add Velocity Fields to SessionState

**Files:**
- Modify: `src/domain/models/session.py:28-50`

**Step 1: Read the current SessionState class**

Run: `cat src/domain/models/session.py | head -n 50`
Note: Class ends at line 50 with `mode: InterviewMode = InterviewMode.EXPLORATORY`

**Step 2: Add velocity tracking fields to SessionState**

Add these 6 new fields after line 50 (before the closing of the class):

```python
    # Velocity tracking for saturation signals (updated by ScoringPersistenceStage each turn)
    surface_velocity_ewma: float = Field(default=0.0, description="EWMA of surface node delta per turn (α=0.4)")
    surface_velocity_peak: float = Field(default=0.0, description="Peak surface node delta observed in this session")
    prev_surface_node_count: int = Field(default=0, description="Surface node count at end of previous turn")
    canonical_velocity_ewma: float = Field(default=0.0, description="EWMA of canonical node delta per turn (α=0.4)")
    canonical_velocity_peak: float = Field(default=0.0, description="Peak canonical node delta observed in this session")
    prev_canonical_node_count: int = Field(default=0, description="Canonical node count at end of previous turn")
```

**Step 3: Verify Pydantic schema is valid**

Run: `python -c "from src.domain.models.session import SessionState; s = SessionState(methodology='jtbd', concept_id='test', concept_name='Test'); print(f'Fields: {s.model_fields.keys()}')"`
Expected: All 6 new fields appear in output with default values

**Step 4: Commit**

```bash
git add src/domain/models/session.py
git commit -m "feat(h0vk): add velocity tracking fields to SessionState

Adds 6 fields for EWMA velocity computation:
- surface_velocity_ewma, surface_velocity_peak, prev_surface_node_count
- canonical_velocity_ewma, canonical_velocity_peak, prev_canonical_node_count

Backward compatible via default values (0.0/0).

Epic: h0vk - Interview Saturation Signals
Bead: 8b5n"
```

---

## Task 2: Add Velocity Fields to ContextLoadingOutput

**Files:**
- Modify: `src/domain/models/pipeline_contracts.py:17-50`

**Step 1: Find ContextLoadingOutput class**

Run: `grep -n "class ContextLoadingOutput" src/domain/models/pipeline_contracts.py`
Note: Class starts at line 17

**Step 2: Add velocity fields to ContextLoadingOutput**

Add these 6 fields after line 49 (after `recent_node_labels` field, before class closing):

```python
    # Velocity state loaded from SessionState (used by saturation signals)
    surface_velocity_ewma: float = Field(default=0.0, description="Loaded from SessionState")
    surface_velocity_peak: float = Field(default=0.0, description="Loaded from SessionState")
    prev_surface_node_count: int = Field(default=0, description="Loaded from SessionState")
    canonical_velocity_ewma: float = Field(default=0.0, description="Loaded from SessionState")
    canonical_velocity_peak: float = Field(default=0.0, description="Loaded from SessionState")
    prev_canonical_node_count: int = Field(default=0, description="Loaded from SessionState")
```

**Step 3: Verify schema is valid**

Run: `python -c "from src.domain.models.pipeline_contracts import ContextLoadingOutput; o = ContextLoadingOutput(methodology='jtbd', concept_id='test', concept_name='Test', turn_number=0, mode='exploratory', max_turns=15); print(f'Has velocity fields: {hasattr(o, \"surface_velocity_ewma\")}')"`
Expected: `Has velocity fields: True`

**Step 4: Commit**

```bash
git add src/domain/models/pipeline_contracts.py
git commit -m "feat(h0vk): add velocity fields to ContextLoadingOutput

Adds 6 velocity fields (matching SessionState) so pipeline
can read velocity state without accessing SessionState directly.

Epic: h0vk - Interview Saturation Signals
Bead: 8b5n"
```

---

## Task 3: Update ContextLoadingStage to Populate Velocity Fields

**Files:**
- Modify: `src/services/turn_pipeline/stages/context_loading_stage.py`

**Step 1: Find where ContextLoadingOutput is constructed**

Run: `grep -n "ContextLoadingOutput" src/services/turn_pipeline/stages/context_loading_stage.py`
Note: Find the line where output is created (likely in `process()` method)

**Step 2: Read the current ContextLoadingOutput construction**

Run: `grep -A 10 "ContextLoadingOutput(" src/services/turn_pipeline/stages/context_loading_stage.py`
Note: Current field names and structure

**Step 3: Add velocity fields to ContextLoadingOutput constructor**

Map SessionState velocity fields to ContextLoadingOutput. Find where `session.state` is accessed and add:

```python
# Velocity state from SessionState
surface_velocity_ewma=session.state.surface_velocity_ewma,
surface_velocity_peak=session.state.surface_velocity_peak,
prev_surface_node_count=session.state.prev_surface_node_count,
canonical_velocity_ewma=session.state.canonical_velocity_ewma,
canonical_velocity_peak=session.state.canonical_velocity_peak,
prev_canonical_node_count=session.state.prev_canonical_node_count,
```

**Step 4: Verify the stage loads correctly**

Run: `python -c "from src.services.turn_pipeline.stages.context_loading_stage import ContextLoadingStage; print('Stage loads successfully')"`
Expected: No import errors

**Step 5: Commit**

```bash
git add src/services/turn_pipeline/stages/context_loading_stage.py
git commit -m "feat(h0vk): populate velocity fields in ContextLoadingStage

Maps SessionState velocity fields to ContextLoadingOutput
so signals can access velocity state via context contract.

Epic: h0vk - Interview Saturation Signals
Bead: 8b5n"
```

---

## Task 4: Update ScoringPersistenceStage to Compute Velocity

**Files:**
- Modify: `src/services/turn_pipeline/stages/scoring_persistence_stage.py:252-267`

**Step 1: Read the current _update_turn_count method**

Run: `sed -n '252,267p' src/services/turn_pipeline/stages/scoring_persistence_stage.py`
Note: Currently only saves methodology/concept_id/concept_name/turn_count

**Step 2: Replace _update_turn_count with velocity computation**

Replace the entire method (lines 252-267) with:

```python
    async def _update_turn_count(self, context: "PipelineContext") -> None:
        """Update session turn count and velocity state.

        Computes EWMA velocity for surface and canonical graphs.
        Velocity = new nodes discovered this turn.

        Note: context.turn_number already represents the current turn number
        (equal to the number of user turns completed so far). We store it
        directly without incrementing.
        """
        from src.domain.models.session import SessionState

        # EWMA smoothing factor (hardcoded, matches theoretical saturation research)
        alpha = 0.4

        # Load current velocity state from ContextLoadingOutput
        clo = context.context_loading_output

        # Surface graph velocity computation
        current_surface = context.graph_state.node_count
        prev_surface = clo.prev_surface_node_count
        surface_delta = max(current_surface - prev_surface, 0)
        new_surface_ewma = alpha * surface_delta + (1 - alpha) * clo.surface_velocity_ewma
        new_surface_peak = max(clo.surface_velocity_peak, float(surface_delta))

        # Canonical graph velocity computation (may be None if disabled)
        cg_state = context.canonical_graph_state
        if cg_state is not None:
            current_canonical = cg_state.concept_count
            prev_canonical = clo.prev_canonical_node_count
            canonical_delta = max(current_canonical - prev_canonical, 0)
            new_canonical_ewma = alpha * canonical_delta + (1 - alpha) * clo.canonical_velocity_ewma
            new_canonical_peak = max(clo.canonical_velocity_peak, float(canonical_delta))
        else:
            # Canonical slots disabled — preserve zeros
            current_canonical = 0
            new_canonical_ewma = 0.0
            new_canonical_peak = 0.0

        # Preserve fields that were previously lost
        last_strategy = context.strategy
        mode = getattr(context, 'mode', 'exploratory')

        updated_state = SessionState(
            methodology=context.methodology,
            concept_id=context.concept_id,
            concept_name=context.concept_name,
            turn_count=context.turn_number,
            last_strategy=last_strategy,
            mode=mode,
            # Velocity fields (NEW)
            surface_velocity_ewma=new_surface_ewma,
            surface_velocity_peak=new_surface_peak,
            prev_surface_node_count=current_surface,
            canonical_velocity_ewma=new_canonical_ewma,
            canonical_velocity_peak=new_canonical_peak,
            prev_canonical_node_count=current_canonical,
        )
        await self.session_repo.update_state(context.session_id, updated_state)
```

**Step 3: Verify the method compiles**

Run: `python -c "from src.services.turn_pipeline.stages.scoring_persistence_stage import ScoringPersistenceStage; print('Stage loads successfully')"`
Expected: No syntax errors

**Step 4: Commit**

```bash
git add src/services/turn_pipeline/stages/scoring_persistence_stage.py
git commit -m "feat(h0vk): compute and persist velocity state each turn

Implements EWMA velocity computation in _update_turn_count:
- Surface graph: tracks node discovery rate
- Canonical graph: tracks concept discovery rate (if enabled)
- Preserves last_strategy and mode (previously lost)

Formula: new_ewma = α × delta + (1-α) × old_ewma where α=0.4

Epic: h0vk - Interview Saturation Signals
Bead: nig9"
```

---

## Task 5: Implement ConversationSaturationSignal

**Files:**
- Create: `src/signals/meta/conversation_saturation.py`

**Step 1: Create the signal file**

```python
"""Conversation saturation signal from surface graph velocity.

Measures interview saturation using information velocity — the rate at which
new concepts are being discovered. When velocity decays (slowing discovery),
the interview approaches theoretical saturation.

Combines three components:
- 60% velocity decay (primary indicator)
- 25% edge density (graph richness)
- 15% turn floor (minimum duration)
"""

from src.signals.signal_base import SignalDetector


class ConversationSaturationSignal(SignalDetector):
    """Estimate interview saturation from surface graph velocity.

    Computes saturation score (0.0-1.0) combining velocity decay,
    edge density, and turn floor. Higher values indicate the interview
    is approaching theoretical saturation (few new concepts).

    Scoring components (weighted sum):
    - Velocity decay (60%): 1 - (ewma / peak), high when discovery slows
    - Edge density (25%): edges/nodes normalized to 2.0, measures richness
    - Turn floor (15%): turn_number / 15, prevents early saturation signal

    Namespaced signal: meta.conversation.saturation
    Cost: low (reads from ContextLoadingOutput and graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.conversation.saturation"
    description = "Interview saturation from surface graph: 0=still learning, 1=saturated. Combines node velocity decay (primary), edge density (graph richness), and turn floor (minimum duration)."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate conversation saturation from velocity, density, and turns.

        Args:
            context: Pipeline context with ContextLoadingOutput containing
                velocity state (ewma, peak, prev counts)
            graph_state: Current knowledge graph state (for edge density)
            response_text: User's response text (unused)

        Returns:
            Dict with meta.conversation.saturation: float (0.0-1.0)
        """
        # Load velocity state from ContextLoadingOutput
        clo = context.context_loading_output
        ewma = clo.surface_velocity_ewma
        peak = clo.surface_velocity_peak

        # Component 1: velocity decay (primary, 60%)
        # High when new nodes are arriving slower than peak rate
        if peak > 0:
            velocity_decay = 1.0 - (ewma / peak)
        else:
            velocity_decay = 0.0
        velocity_decay = max(0.0, min(1.0, velocity_decay))

        # Component 2: edge density (graph richness, 25%)
        # Plateau at 2.0 edges/node (well-connected graph)
        node_count = graph_state.node_count if graph_state else 0
        edge_count = graph_state.edge_count if graph_state else 0
        if node_count > 0:
            raw_density = edge_count / node_count
            edge_density_norm = min(raw_density / 2.0, 1.0)
        else:
            edge_density_norm = 0.0

        # Component 3: turn floor (absolute minimum, 15%)
        # Prevents early saturation signal on turn 1-2
        turn_floor = min(context.turn_number / 15.0, 1.0)

        saturation = 0.60 * velocity_decay + 0.25 * edge_density_norm + 0.15 * turn_floor

        return {self.signal_name: round(saturation, 4)}
```

**Step 2: Verify auto-registration works**

Run: `python -c "from src.signals.signal_base import SignalDetector; cls = SignalDetector.get_signal_class('meta.conversation.saturation'); print(f'Auto-registered: {cls.__name__}')"`
Expected: `Auto-registered: ConversationSaturationSignal`

**Step 3: Commit**

```bash
git add src/signals/meta/conversation_saturation.py
git commit -m "feat(h0vk): implement meta.conversation.saturation signal

Computes interview saturation from surface graph:
- 60% velocity decay (EWMA slowing)
- 25% edge density (graph richness)
- 15% turn floor (minimum duration)

Auto-registers via SignalDetector.__init_subclass__.

Epic: h0vk - Interview Saturation Signals
Bead: f1ej"
```

---

## Task 6: Implement CanonicalSaturationSignal

**Files:**
- Create: `src/signals/meta/canonical_saturation.py`

**Step 1: Create the signal file**

```python
"""Canonical saturation signal from canonical graph velocity.

Parallel to ConversationSaturationSignal but uses canonical (deduplicated)
concept velocity. Enables empirical comparison — hypothesis is that
conversational graph may produce better results.
"""

from src.signals.signal_base import SignalDetector


class CanonicalSaturationSignal(SignalDetector):
    """Estimate interview saturation from canonical graph velocity.

    Computes saturation score (0.0-1.0) using the same formula as
    ConversationSaturationSignal but reads from canonical graph state.

    Returns empty dict if canonical slots are disabled (feature flag).

    Namespaced signal: meta.canonical.saturation
    Cost: low (reads from ContextLoadingOutput and canonical_graph_state)
    Refresh: per_turn
    """

    signal_name = "meta.canonical.saturation"
    description = "Interview saturation from canonical graph: 0=still learning, 1=saturated. Combines canonical concept velocity decay (primary), canonical edge density (graph richness), and turn floor."
    dependencies = []

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate canonical saturation from velocity, density, and turns.

        Args:
            context: Pipeline context with ContextLoadingOutput and
                canonical_graph_state
            graph_state: Current knowledge graph state (unused, uses canonical)
            response_text: User's response text (unused)

        Returns:
            Dict with meta.canonical.saturation: float (0.0-1.0)
            Returns empty dict if canonical_graph_state is None.
        """
        # Load canonical velocity state from ContextLoadingOutput
        clo = context.context_loading_output
        ewma = clo.canonical_velocity_ewma
        peak = clo.canonical_velocity_peak

        # Check if canonical graph is available
        cg_state = context.canonical_graph_state
        if cg_state is None:
            # Canonical slots disabled — signal not applicable
            return {}

        # Component 1: velocity decay (primary, 60%)
        if peak > 0:
            velocity_decay = 1.0 - (ewma / peak)
        else:
            velocity_decay = 0.0
        velocity_decay = max(0.0, min(1.0, velocity_decay))

        # Component 2: canonical edge density (25%)
        concept_count = cg_state.concept_count
        edge_count = cg_state.edge_count
        if concept_count > 0:
            raw_density = edge_count / concept_count
            edge_density_norm = min(raw_density / 2.0, 1.0)
        else:
            edge_density_norm = 0.0

        # Component 3: turn floor (15%)
        turn_floor = min(context.turn_number / 15.0, 1.0)

        saturation = 0.60 * velocity_decay + 0.25 * edge_density_norm + 0.15 * turn_floor

        return {self.signal_name: round(saturation, 4)}
```

**Step 2: Verify auto-registration works**

Run: `python -c "from src.signals.signal_base import SignalDetector; cls = SignalDetector.get_signal_class('meta.canonical.saturation'); print(f'Auto-registered: {cls.__name__}')"`
Expected: `Auto-registered: CanonicalSaturationSignal`

**Step 3: Commit**

```bash
git add src/signals/meta/canonical_saturation.py
git commit -m "feat(h0vk): implement meta.canonical.saturation signal

Computes interview saturation from canonical graph:
- Same formula as conversation.saturation
- Returns empty dict if canonical slots disabled

Enables empirical comparison of surface vs canonical metrics.

Epic: h0vk - Interview Saturation Signals
Bead: agax"
```

---

## Task 7: Register Saturation Signals in JTBD YAML

**Files:**
- Modify: `config/methodologies/jobs_to_be_done.yaml:231-233`

**Step 1: Find the signals.meta section**

Run: `grep -n "signals:" config/methodologies/jobs_to_be_done.yaml`
Note: signals section starts at line 213, meta at line 231

**Step 2: Add saturation signals to signals.meta**

Replace the meta section (lines 231-233) with:

```yaml
  meta:
    - meta.interview.phase
    - meta.conversation.saturation
    - meta.canonical.saturation
```

**Step 3: Verify YAML is valid**

Run: `python -c "from src.core.schema_loader import load_methodology; m = load_methodology('jobs_to_be_done'); print(f'Meta signals: {m.signals.meta}')"`
Expected: Both new signals appear in list

**Step 4: Commit**

```bash
git add config/methodologies/jobs_to_be_done.yaml
git commit -m "feat(h0vk): register saturation signals in JTBD YAML

Adds meta.conversation.saturation and meta.canonical.saturation
to signals.meta list for methodology-based detection.

Epic: h0vk - Interview Saturation Signals
Bead: 3p9w"
```

---

## Task 8: Register Saturation Signals in Other Methodology YAMLs

**Files:**
- Modify: `config/methodologies/means_end_chain.yaml`
- Check if `config/methodologies/critical_incident.yaml` exists

**Step 1: Add signals to means_end_chain.yaml**

Run: `grep -n "signals:" config/methodologies/means_end_chain.yaml | head -5`
Find the signals.meta section and add both saturation signals (keeping meta.interview_progress since chain_completion is valid for MEC).

**Step 2: Check if critical_incident.yaml exists**

Run: `ls config/methodologies/critical_incident.yaml 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"`
If exists, add saturation signals to its signals.meta section too.

**Step 3: Commit**

```bash
git add config/methodologies/means_end_chain.yaml
git add config/methodologies/critical_incident.yaml  # If exists
git commit -m "feat(h0vk): register saturation signals in other methodologies

Adds saturation signals to means_end_chain.yaml
(and critical_incident.yaml if exists).

Note: Keeps meta.interview_progress in MEC where chain_completion
is meaningful.

Epic: h0vk - Interview Saturation Signals
Bead: 3p9w"
```

---

## Task 9: Add Saturation Weights to validate_outcome Strategy

**Files:**
- Modify: `config/methodologies/jobs_to_be_done.yaml:294-313`

**Step 1: Find the validate_outcome strategy**

Run: `grep -n "validate_outcome:" config/methodologies/jobs_to_be_done.yaml`
Note: Strategy starts at line 294

**Step 2: Add saturation weights to signal_weights**

Add these lines to the signal_weights section (after line 313, before the next strategy):

```yaml
      # Saturation triggers (Phase 6)
      meta.conversation.saturation: 0.5  # High saturation = validate
      meta.canonical.saturation: 0.3     # Supportive metric
```

**Step 3: Verify YAML is valid**

Run: `python -c "from src.core.schema_loader import load_methodology; m = load_methodology('jobs_to_be_done'); vo = [s for s in m.strategies if s.name == 'validate_outcome'][0]; print(f'Has saturation weights: {\"meta.conversation.saturation\" in vo.signal_weights}')"`
Expected: `Has saturation weights: True`

**Step 4: Commit**

```bash
git add config/methodologies/jobs_to_be_done.yaml
git commit -m "feat(h0vk): add saturation weights to validate_outcome

validate_outcome strategy now uses saturation signals:
- meta.conversation.saturation: 0.5 (primary)
- meta.canonical.saturation: 0.3 (supportive)

High saturation triggers validation/closing.

Epic: h0vk - Interview Saturation Signals
Bead: ewxf"
```

---

## Task 10: Add Saturation Weights to Other Methodology YAMLs

**Files:**
- Modify: `config/methodologies/means_end_chain.yaml`
- Check: `config/methodologies/critical_incident.yaml`

**Step 1: Add weights to means_end_chain.yaml**

If validate_outcome strategy exists, add the same saturation weights used in JTBD.

**Step 2: Add weights to critical_incident.yaml (if exists)**

Same as above — add saturation weights to validate_outcome if present.

**Step 3: Commit**

```bash
git add config/methodologies/*.yaml
git commit -m "feat(h0vk): add saturation weights to other methodologies

Adds saturation signal weights to validate_outcome strategy
in means_end_chain.yaml (and critical_incident.yaml if exists).

Epic: h0vk - Interview Saturation Signals
Bead: ewxf"
```

---

## Task 11: Deprecate progress.py Signal

**Files:**
- Modify: `src/signals/meta/progress.py:1-31`

**Step 1: Add deprecation notice to docstring**

Add to the class docstring (after line 31):

```python

    DEPRECATED for JTBD: Replaced by meta.conversation.saturation and
    meta.canonical.saturation signals which are methodology-agnostic and
    based on information velocity rather than structural completeness.

    Retained in means_end_chain.yaml where chain_completion is meaningful
    for Means-End Chain methodology.
```

**Step 2: Commit**

```bash
git add src/signals/meta/progress.py
git commit -m "docs(h0vk): deprecate meta.interview_progress for JTBD

Adds deprecation notice to InterviewProgressSignal docstring.

Signal is replaced by saturation signals which are:
- Methodology-agnostic (not MEC-specific)
- Based on information velocity (not structural depth)
- Free from double-normalization bugs

Retained for MEC where chain_completion is valid.

Epic: h0vk - Interview Saturation Signals
Bead: ewxf"
```

---

## Task 12: Close orbj Bead

**Step 1: Close the orbj bead with reason**

Run: `bd close interview-system-v2-orbj --reason='Superseded by meta.conversation.saturation and meta.canonical.saturation redesign (epic h0vk). meta.interview_progress already removed from JTBD YAML. Progress signal retained for means_end_chain.yaml where chain_completion is meaningful.'`

**Step 2: Verify bead is closed**

Run: `bd show interview-system-v2-orbj`
Expected: Status shows CLOSED

**Step 3: Sync beads**

```bash
bd sync
```

**Step 4: Commit**

```bash
git add .beads/
git commit -m "chore(h0vk): close orbj bead superseded by saturation signals

Bead interview-system-v2-orbj closed.
meta.interview_progress bug fix replaced by new saturation design.

Epic: h0vk - Interview Saturation Signals
Bead: ewxf"
```

---

## Task 13: Final Verification and Documentation Update

**Step 1: Run linting and format check**

Run: `ruff check . --fix && ruff format .`
Expected: No errors, files auto-formatted

**Step 2: Update data_flow_paths.md if needed**

Check if saturation signals should be documented: `grep -i saturation docs/data_flow_paths.md`
If not present, add a new path for "Saturation Signal Computation"

**Step 3: Run a simulation to verify end-to-end**

Run: `uv run python scripts/run_simulation.py coffee_jtbd_v2 health_conscious 5`
Check logs for `meta.conversation.saturation` and `meta.canonical.saturation` signal values

**Step 4: Final commit**

```bash
git add docs/
git commit -m "docs(h0vk): update documentation for saturation signals

- Update data_flow_paths.md with saturation signal flow
- Document EWMA velocity computation

Epic: h0vk - Interview Saturation Signals"
```

---

## Task 14: Beads Workflow Completion

**Step 1: Mark all epic beads as in_progress/completed**

```bash
bd update interview-system-v2-8b5n --status completed
bd update interview-system-v2-nig9 --status completed
bd update interview-system-v2-f1ej --status completed
bd update interview-system-v2-agax --status completed
bd update interview-system-v2-3p9w --status completed
bd update interview-system-v2-ewxf --status completed
```

**Step 2: Mark epic h0vk as completed**

```bash
bd close interview-system-v2-h0vk
```

**Step 3: Sync beads**

```bash
bd sync
```

**Step 4: Push to remote**

```bash
git push origin master
```

---

## Summary

This plan implements Epic h0vk in 14 tasks:

1. **Data Model (Tasks 1-3):** Add velocity fields to SessionState, ContextLoadingOutput, ContextLoadingStage
2. **Velocity Computation (Task 4):** ScoringPersistenceStage computes EWMA each turn
3. **Signal Detection (Tasks 5-6):** Two new signals read velocity and compute saturation
4. **Registration (Tasks 7-8):** YAML configuration for all methodologies
5. **Integration (Tasks 9-11):** Weights in validate_outcome, deprecate old signal
6. **Cleanup (Tasks 12-14):** Close old bead, verification, beads workflow

**Key decisions:**
- EWMA α=0.4 hardcoded (not configurable)
- Backward compatible via default values (no migration needed)
- CanonicalSaturationSignal returns empty dict when feature disabled
- Unit tests only (no integration tests specified)
