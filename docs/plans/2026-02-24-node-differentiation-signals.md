# Node Differentiation Signals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two new node-level signals — `graph.node.type_priority` and `graph.node.slot_saturation` — that break scoring ties among same-turn new nodes, enabling principled (non-random) node selection.

**Architecture:** Both signals are standard `NodeSignalDetector` subclasses that integrate with existing joint scoring via YAML `signal_weights`. Type priority is a pure-config lookup (node_type → priority from methodology YAML). Slot saturation queries canonical slot mappings to penalize nodes in over-represented thematic slots.

**Tech Stack:** Python 3.12, pytest, aiosqlite, Pydantic, YAML methodology configs, structlog

---

## Signal 1: graph.node.type_priority

### Task 1: Add `node_type_priorities` to StrategyConfig

**Files:**
- Modify: `src/methodologies/registry.py:71-78` (StrategyConfig dataclass)

**Step 1: Write the failing test**

File: `tests/methodologies/test_registry.py` (create)

```python
"""Tests for methodology registry — node_type_priorities in StrategyConfig."""

from src.methodologies.registry import StrategyConfig


class TestStrategyConfigNodeTypePriorities:
    """Tests for node_type_priorities field on StrategyConfig."""

    def test_default_empty(self):
        """StrategyConfig defaults to empty node_type_priorities."""
        config = StrategyConfig(
            name="test",
            description="Test",
            signal_weights={"llm.engagement.high": 0.5},
        )
        assert config.node_type_priorities == {}

    def test_explicit_priorities(self):
        """StrategyConfig accepts node_type_priorities."""
        config = StrategyConfig(
            name="test",
            description="Test",
            signal_weights={},
            node_type_priorities={
                "pain_point": 0.8,
                "job_trigger": 0.7,
                "gain_point": 0.5,
            },
        )
        assert config.node_type_priorities["pain_point"] == 0.8
        assert config.node_type_priorities["job_trigger"] == 0.7
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/methodologies/test_registry.py -v
```
Expected: FAIL — `StrategyConfig.__init__() got an unexpected keyword argument 'node_type_priorities'`

**Step 3: Add node_type_priorities field to StrategyConfig**

In `src/methodologies/registry.py`, modify the `StrategyConfig` dataclass (around line 71):

```python
@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    description: str
    signal_weights: dict[str, float]
    generates_closing_question: bool = False
    node_type_priorities: dict[str, float] = field(default_factory=dict)
```

Add `from dataclasses import dataclass, field` at the top if not already imported (it uses `dataclass` already but `field` may be needed).

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/methodologies/test_registry.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/methodologies/registry.py tests/methodologies/test_registry.py
git commit -m "feat: add node_type_priorities field to StrategyConfig"
```

---

### Task 2: Load node_type_priorities from YAML in registry

**Files:**
- Modify: `src/methodologies/registry.py:148-158` (strategy loading in `get_methodology`)

**Step 1: Write the failing test**

Add to `tests/methodologies/test_registry.py`:

```python
import tempfile
import os
import yaml


class TestRegistryLoadsNodeTypePriorities:
    """Test that MethodologyRegistry loads node_type_priorities from YAML."""

    def test_loads_priorities_from_yaml(self, tmp_path):
        """Registry loads node_type_priorities from strategy definition."""
        yaml_content = {
            "method": {"name": "test_method", "description": "Test"},
            "signals": {},
            "strategies": [
                {
                    "name": "explore",
                    "description": "Explore",
                    "signal_weights": {},
                    "node_type_priorities": {
                        "pain_point": 0.8,
                        "job_trigger": 0.7,
                    },
                }
            ],
        }
        config_dir = tmp_path / "methodologies"
        config_dir.mkdir()
        config_file = config_dir / "test_method.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry(config_dir=config_dir)
        config = registry.get_methodology("test_method")

        assert config.strategies[0].node_type_priorities == {
            "pain_point": 0.8,
            "job_trigger": 0.7,
        }

    def test_defaults_to_empty_when_absent(self, tmp_path):
        """Registry defaults node_type_priorities to {} when not in YAML."""
        yaml_content = {
            "method": {"name": "test_method2", "description": "Test"},
            "signals": {},
            "strategies": [
                {
                    "name": "explore",
                    "description": "Explore",
                    "signal_weights": {},
                }
            ],
        }
        config_dir = tmp_path / "methodologies"
        config_dir.mkdir()
        config_file = config_dir / "test_method2.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry(config_dir=config_dir)
        config = registry.get_methodology("test_method2")

        assert config.strategies[0].node_type_priorities == {}
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/methodologies/test_registry.py::TestRegistryLoadsNodeTypePriorities -v
```
Expected: FAIL — priorities not loaded (empty dict regardless of YAML)

**Step 3: Update get_methodology to load node_type_priorities**

In `src/methodologies/registry.py`, find the strategy loading block inside `get_methodology()` (around line 148-158). Change:

```python
            strategies=[
                StrategyConfig(
                    name=s["name"],
                    description=s.get("description", ""),
                    signal_weights=s["signal_weights"],
                    generates_closing_question=s.get(
                        "generates_closing_question", False
                    ),
                    node_type_priorities=s.get("node_type_priorities", {}),
                )
                for s in data.get("strategies", [])
            ],
```

The only addition is the `node_type_priorities=s.get("node_type_priorities", {})` line.

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/methodologies/test_registry.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/methodologies/registry.py tests/methodologies/test_registry.py
git commit -m "feat: load node_type_priorities from methodology YAML"
```

---

### Task 3: Implement NodeTypePrioritySignal detector

**Files:**
- Modify: `src/signals/graph/node_signals.py` (add new class at end, before `__all__`)
- Modify: `src/signals/graph/__init__.py` (add import and export)

**Step 1: Write the failing test**

File: `tests/signals/test_node_type_priority.py` (create)

```python
"""Tests for NodeTypePrioritySignal detector."""

import pytest
from unittest.mock import MagicMock

from src.domain.models.node_state import NodeState
from src.signals.graph.node_signals import NodeTypePrioritySignal


@pytest.fixture
def node_tracker_with_types():
    """Create a mock node tracker with nodes of different types."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = {
        "node-1": NodeState(
            node_id="node-1",
            label="skepticism about messaging",
            created_at_turn=2,
            depth=0,
            node_type="pain_point",
        ),
        "node-2": NodeState(
            node_id="node-2",
            label="store out of stock",
            created_at_turn=2,
            depth=0,
            node_type="job_trigger",
        ),
        "node-3": NodeState(
            node_id="node-3",
            label="enjoy rich coffee",
            created_at_turn=2,
            depth=0,
            node_type="job_statement",
        ),
        "node-4": NodeState(
            node_id="node-4",
            label="grinding fresh",
            created_at_turn=2,
            depth=0,
            node_type="solution_approach",
        ),
    }
    return tracker


class TestNodeTypePrioritySignal:
    """Tests for graph.node.type_priority signal."""

    @pytest.mark.asyncio
    async def test_returns_priorities_for_all_nodes(self, node_tracker_with_types):
        """Signal returns a priority value for every tracked node."""
        priorities = {"pain_point": 0.8, "job_trigger": 0.7, "job_statement": 0.4}
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities=priorities
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        assert len(result) == 4
        assert result["node-1"] == 0.8  # pain_point
        assert result["node-2"] == 0.7  # job_trigger
        assert result["node-3"] == 0.4  # job_statement

    @pytest.mark.asyncio
    async def test_unknown_type_gets_default(self, node_tracker_with_types):
        """Nodes with types not in priorities map get default 0.5."""
        priorities = {"pain_point": 0.8}  # only pain_point defined
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities=priorities
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        assert result["node-1"] == 0.8  # pain_point: defined
        assert result["node-2"] == 0.5  # job_trigger: default
        assert result["node-3"] == 0.5  # job_statement: default
        assert result["node-4"] == 0.5  # solution_approach: default

    @pytest.mark.asyncio
    async def test_empty_priorities_all_default(self, node_tracker_with_types):
        """With empty priorities map, all nodes get default 0.5."""
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities={}
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        for node_id in result:
            assert result[node_id] == 0.5

    @pytest.mark.asyncio
    async def test_signal_name(self, node_tracker_with_types):
        """Signal has correct signal_name."""
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities={}
        )
        assert detector.signal_name == "graph.node.type_priority"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/signals/test_node_type_priority.py -v
```
Expected: FAIL — `ImportError: cannot import name 'NodeTypePrioritySignal'`

**Step 3: Implement NodeTypePrioritySignal**

Add to `src/signals/graph/node_signals.py`, after the `NodeHasOutgoingSignal` class and before the `__all__` block:

```python
# =============================================================================
# Differentiation Signals (for same-turn new-node tie-breaking)
# =============================================================================


class NodeTypePrioritySignal(NodeSignalDetector):
    """Assign strategic priority based on node_type from methodology config.

    Different node types have different strategic value depending on the
    methodology and interview phase. For example, in JTBD, pain_points
    may be more valuable to explore than job_statements.

    Priority values are configured per-strategy in methodology YAML via
    node_type_priorities. Nodes whose type is not in the map get a neutral
    default of 0.5.

    Namespaced signal: graph.node.type_priority
    Cost: negligible (dict lookup per node)
    Refresh: per_turn
    """

    signal_name = "graph.node.type_priority"
    description = "Strategic priority based on node_type (0.0-1.0). Configured per-strategy in methodology YAML."

    def __init__(self, node_tracker, node_type_priorities: dict[str, float] | None = None):
        super().__init__(node_tracker)
        self._priorities = node_type_priorities or {}
        self._default_priority = 0.5

    async def detect(self, context, graph_state, response_text):  # noqa: ARG002
        results = {}
        for node_id, state in self._get_all_node_states().items():
            results[node_id] = self._priorities.get(
                state.node_type, self._default_priority
            )
        return results
```

Also update the `__all__` block at the end of the file to include `"NodeTypePrioritySignal"`:

```python
__all__ = [
    # Exhaustion
    "NodeExhaustedSignal",
    "NodeExhaustionScoreSignal",
    "NodeYieldStagnationSignal",
    # Engagement
    "NodeFocusStreakSignal",
    "NodeIsCurrentFocusSignal",
    "NodeRecencyScoreSignal",
    # Relationships
    "NodeIsOrphanSignal",
    "NodeEdgeCountSignal",
    "NodeHasOutgoingSignal",
    # Differentiation
    "NodeTypePrioritySignal",
]
```

Update `src/signals/graph/__init__.py` to add the import and export:

Add to the node-level imports block:
```python
from src.signals.graph.node_signals import (
    ...
    NodeTypePrioritySignal,
)
```

Add to `__all__`:
```python
    # Node-level: Differentiation
    "NodeTypePrioritySignal",
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/signals/test_node_type_priority.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/signals/graph/node_signals.py src/signals/graph/__init__.py tests/signals/test_node_type_priority.py
git commit -m "feat: implement NodeTypePrioritySignal detector"
```

---

### Task 4: Wire NodeTypePrioritySignal into NodeSignalDetectionService

**Files:**
- Modify: `src/services/node_signal_detection_service.py:57-98`
- Modify: `src/services/methodology_strategy_service.py:180-186`

The detector needs per-strategy `node_type_priorities`, but the detection service runs once for all strategies. The design: pass the selected top strategy's priorities into detection, OR run detection with the first strategy's priorities. However, since node signals feed into ALL (strategy, node) pairs, we need a single pass.

**Resolution:** Merge all strategies' `node_type_priorities` into a single max-priority map. For each node_type, take the highest priority across all strategies. This gives every type its best-case priority; individual strategy weights in `signal_weights` then modulate how much each strategy cares about the signal.

**Step 1: Write the failing test**

Add to `tests/services/test_node_signal_detection_service.py`:

```python
from src.domain.models.node_state import NodeState


@pytest.mark.asyncio
async def test_detect_includes_type_priority_signal(node_signal_service):
    """Test that detect() includes graph.node.type_priority when priorities provided."""
    mock_context = MagicMock()
    mock_graph_state = MagicMock()
    mock_node_tracker = MagicMock()

    mock_node_tracker.get_all_states.return_value = {
        "node-1": NodeState(
            node_id="node-1",
            label="test node",
            created_at_turn=1,
            depth=0,
            node_type="pain_point",
        ),
    }

    result = await node_signal_service.detect(
        context=mock_context,
        graph_state=mock_graph_state,
        response_text="test",
        node_tracker=mock_node_tracker,
        node_type_priorities={"pain_point": 0.9},
    )

    assert "node-1" in result
    assert "graph.node.type_priority" in result["node-1"]
    assert result["node-1"]["graph.node.type_priority"] == 0.9
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/services/test_node_signal_detection_service.py::test_detect_includes_type_priority_signal -v
```
Expected: FAIL — `detect() got an unexpected keyword argument 'node_type_priorities'`

**Step 3: Update NodeSignalDetectionService.detect() to accept node_type_priorities**

In `src/services/node_signal_detection_service.py`:

1. Add `node_type_priorities` parameter to `detect()`:

```python
    async def detect(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        node_tracker: "NodeStateTracker",
        node_type_priorities: dict[str, float] | None = None,
    ) -> Dict[str, Dict[str, Any]]:
```

2. Add the import and detector instance to the signal_detectors list:

Add to the import block inside `detect()`:
```python
        from src.signals.graph.node_signals import (
            ...
            NodeTypePrioritySignal,
        )
```

Add to the `signal_detectors` list:
```python
            NodeTypePrioritySignal(node_tracker, node_type_priorities=node_type_priorities),
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/services/test_node_signal_detection_service.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/node_signal_detection_service.py tests/services/test_node_signal_detection_service.py
git commit -m "feat: wire NodeTypePrioritySignal into detection service"
```

---

### Task 5: Pass merged node_type_priorities from MethodologyStrategyService

**Files:**
- Modify: `src/services/methodology_strategy_service.py:180-186`

**Step 1: Write the failing test**

File: `tests/services/test_methodology_strategy_priorities.py` (create)

```python
"""Test that MethodologyStrategyService passes node_type_priorities to node signal detection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.methodologies.registry import StrategyConfig, MethodologyConfig


@pytest.mark.asyncio
async def test_merges_priorities_across_strategies():
    """Service merges node_type_priorities from all strategies (max per type)."""
    strategies = [
        StrategyConfig(
            name="explore",
            description="Explore",
            signal_weights={},
            node_type_priorities={"pain_point": 0.8, "job_trigger": 0.6},
        ),
        StrategyConfig(
            name="dig",
            description="Dig",
            signal_weights={},
            node_type_priorities={"pain_point": 0.5, "gain_point": 0.9},
        ),
    ]

    # Verify merge logic: pain_point should be max(0.8, 0.5) = 0.8
    merged = {}
    for strategy in strategies:
        for node_type, priority in strategy.node_type_priorities.items():
            if node_type not in merged or priority > merged[node_type]:
                merged[node_type] = priority

    assert merged == {
        "pain_point": 0.8,
        "job_trigger": 0.6,
        "gain_point": 0.9,
    }
```

**Step 2: Run test to verify it passes (pure logic test)**

```bash
uv run pytest tests/services/test_methodology_strategy_priorities.py -v
```
Expected: PASS (this just validates the merge logic we'll use)

**Step 3: Update MethodologyStrategyService.select_strategy_and_focus()**

In `src/services/methodology_strategy_service.py`, find the node signal detection call (around line 180-186). Add priority merging before the call:

```python
        # Merge node_type_priorities across all strategies (max per type)
        merged_priorities: dict[str, float] = {}
        for strategy in strategies:
            for node_type, priority in strategy.node_type_priorities.items():
                if node_type not in merged_priorities or priority > merged_priorities[node_type]:
                    merged_priorities[node_type] = priority

        # Detect node-level signals (delegated to NodeSignalDetectionService)
        node_signals = await self.node_signal_service.detect(
            context=context,
            graph_state=graph_state,
            response_text=response_text,
            node_tracker=node_tracker,
            node_type_priorities=merged_priorities if merged_priorities else None,
        )
```

**Step 4: Run full test suite to verify nothing breaks**

```bash
uv run pytest tests/methodologies/ tests/services/test_node_signal_detection_service.py tests/services/test_methodology_strategy_priorities.py -v
```
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/services/methodology_strategy_service.py tests/services/test_methodology_strategy_priorities.py
git commit -m "feat: merge and pass node_type_priorities to signal detection"
```

---

### Task 6: Add node_type_priorities to JTBD methodology YAML

**Files:**
- Modify: `config/methodologies/jobs_to_be_done.yaml`

**Step 1: No test needed — this is pure YAML config**

The signal is already wired end-to-end. This task adds the priorities to each strategy, which are consumed automatically by the detection service.

**Step 2: Add node_type_priorities to each JTBD strategy**

Add `node_type_priorities:` to each strategy in `config/methodologies/jobs_to_be_done.yaml`. Also add `graph.node.type_priority` signal weights to each strategy's `signal_weights:` section.

Priorities per strategy (based on JTBD methodology theory):

**explore_situation:**
```yaml
    node_type_priorities:
      job_trigger: 0.9
      job_context: 0.85
      pain_point: 0.7
      job_statement: 0.6
      gain_point: 0.5
      solution_approach: 0.4
      emotional_job: 0.3
      social_job: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.6   # ADD this line
```

**probe_alternatives:**
```yaml
    node_type_priorities:
      solution_approach: 0.9
      pain_point: 0.8
      gain_point: 0.7
      job_statement: 0.5
      job_trigger: 0.4
      job_context: 0.3
      emotional_job: 0.3
      social_job: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.5
```

**dig_motivation:**
```yaml
    node_type_priorities:
      pain_point: 0.9
      gain_point: 0.85
      job_statement: 0.8
      emotional_job: 0.7
      social_job: 0.7
      solution_approach: 0.5
      job_trigger: 0.4
      job_context: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.5
```

**validate_outcome:**
```yaml
    node_type_priorities:
      gain_point: 0.9
      emotional_job: 0.85
      social_job: 0.85
      job_statement: 0.7
      solution_approach: 0.6
      pain_point: 0.5
      job_trigger: 0.3
      job_context: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.4
```

**revitalize:**
```yaml
    node_type_priorities:
      job_trigger: 0.9
      job_context: 0.85
      solution_approach: 0.7
      pain_point: 0.6
      gain_point: 0.5
      job_statement: 0.4
      emotional_job: 0.3
      social_job: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.5
```

**uncover_obstacles:**
```yaml
    node_type_priorities:
      pain_point: 0.95
      job_trigger: 0.7
      solution_approach: 0.6
      gain_point: 0.5
      job_statement: 0.4
      job_context: 0.4
      emotional_job: 0.3
      social_job: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.5
```

**clarify_assumption:**
```yaml
    node_type_priorities:
      gain_point: 0.85
      pain_point: 0.8
      solution_approach: 0.75
      job_statement: 0.6
      emotional_job: 0.5
      social_job: 0.5
      job_trigger: 0.4
      job_context: 0.3
    signal_weights:
      # ... existing weights ...
      graph.node.type_priority: 0.4
```

**Step 3: Validate YAML loads without errors**

```bash
uv run python -c "from src.methodologies import get_registry; r = get_registry(); c = r.get_methodology('jobs_to_be_done'); print(f'Loaded {len(c.strategies)} strategies'); [print(f'  {s.name}: {len(s.node_type_priorities)} type priorities') for s in c.strategies]"
```
Expected: prints 7 strategies, each with 8 type priorities

**Step 4: Run existing scoring tests to verify no regression**

```bash
uv run pytest tests/methodologies/test_scoring.py tests/pipeline/test_critical_path.py -v
```
Expected: ALL PASS

**Step 5: Commit**

```bash
git add config/methodologies/jobs_to_be_done.yaml
git commit -m "feat: add node_type_priorities to all JTBD strategies"
```

---

## Signal 2: graph.node.slot_saturation

### Task 7: Add get_slot_saturation_map to CanonicalSlotRepository

**Files:**
- Modify: `src/persistence/repositories/canonical_slot_repo.py`

This method returns a dict mapping `surface_node_id → slot_support_count` for all mapped nodes in a session. The saturation signal uses this to determine how over-represented each node's thematic slot is.

**Step 1: Write the failing test**

File: `tests/persistence/test_canonical_slot_repo_saturation.py` (create)

```python
"""Tests for get_slot_saturation_map in CanonicalSlotRepository."""

import pytest
import aiosqlite

from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository


@pytest.fixture
async def db_with_slots(tmp_path):
    """Create a temp DB with canonical slots and mappings."""
    db_path = str(tmp_path / "test.db")

    async with aiosqlite.connect(db_path) as db:
        # Create tables
        await db.execute("""
            CREATE TABLE canonical_slots (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                slot_name TEXT,
                node_type TEXT,
                status TEXT DEFAULT 'candidate',
                support_count INTEGER DEFAULT 0,
                first_seen_turn INTEGER,
                promoted_turn INTEGER,
                description TEXT DEFAULT '',
                embedding BLOB
            )
        """)
        await db.execute("""
            CREATE TABLE surface_to_slot_mapping (
                surface_node_id TEXT,
                canonical_slot_id TEXT,
                similarity_score REAL,
                assigned_turn INTEGER
            )
        """)

        # Insert slots: "flavor" (support=3), "cost" (support=1)
        await db.execute(
            "INSERT INTO canonical_slots (id, session_id, slot_name, node_type, status, support_count, first_seen_turn) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("slot-1", "sess-1", "flavor_complexity", "attribute", "candidate", 3, 1),
        )
        await db.execute(
            "INSERT INTO canonical_slots (id, session_id, slot_name, node_type, status, support_count, first_seen_turn) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("slot-2", "sess-1", "cost_concerns", "consequence", "candidate", 1, 2),
        )

        # Map nodes to slots
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-a", "slot-1", 0.9, 1),
        )
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-b", "slot-1", 0.85, 1),
        )
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-c", "slot-1", 0.8, 2),
        )
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-d", "slot-2", 0.9, 2),
        )
        await db.commit()

    return db_path


@pytest.mark.asyncio
async def test_get_slot_saturation_map(db_with_slots):
    """Returns surface_node_id -> support_count for all mapped nodes."""
    repo = CanonicalSlotRepository(db_path=db_with_slots)
    result = await repo.get_slot_saturation_map(session_id="sess-1")

    assert result == {
        "node-a": 3,  # maps to slot-1 (support=3)
        "node-b": 3,  # maps to slot-1 (support=3)
        "node-c": 3,  # maps to slot-1 (support=3)
        "node-d": 1,  # maps to slot-2 (support=1)
    }


@pytest.mark.asyncio
async def test_get_slot_saturation_map_empty_session(db_with_slots):
    """Returns empty dict for session with no mappings."""
    repo = CanonicalSlotRepository(db_path=db_with_slots)
    result = await repo.get_slot_saturation_map(session_id="nonexistent")
    assert result == {}
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/persistence/test_canonical_slot_repo_saturation.py -v
```
Expected: FAIL — `AttributeError: 'CanonicalSlotRepository' has no attribute 'get_slot_saturation_map'`

**Step 3: Implement get_slot_saturation_map**

Add to `src/persistence/repositories/canonical_slot_repo.py`, in the `CanonicalSlotRepository` class, after the existing methods:

```python
    async def get_slot_saturation_map(self, session_id: str) -> Dict[str, int]:
        """Get support_count for each surface node's canonical slot.

        Returns a mapping from surface_node_id to the support_count of the
        canonical slot it belongs to. Used by the slot saturation signal to
        determine how over-represented each node's thematic slot is.

        Includes both candidate and active slots (min_support=1 for signaling).

        Args:
            session_id: Session ID

        Returns:
            Dict mapping surface_node_id -> slot support_count
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT m.surface_node_id, s.support_count
                FROM surface_to_slot_mapping m
                JOIN canonical_slots s ON m.canonical_slot_id = s.id
                WHERE s.session_id = ?
                """,
                (session_id,),
            )
            rows = await cursor.fetchall()

        return {row["surface_node_id"]: row["support_count"] for row in rows}
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/persistence/test_canonical_slot_repo_saturation.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/persistence/repositories/canonical_slot_repo.py tests/persistence/test_canonical_slot_repo_saturation.py
git commit -m "feat: add get_slot_saturation_map to CanonicalSlotRepository"
```

---

### Task 8: Implement NodeSlotSaturationSignal detector

**Files:**
- Modify: `src/signals/graph/node_signals.py` (add class before `__all__`)
- Modify: `src/signals/graph/__init__.py` (add import and export)

The signal computes: `1.0 - (slot_support_count / max_support_count)` so that nodes in underrepresented slots score higher (closer to 1.0) and nodes in saturated slots score lower (closer to 0.0). Nodes without slot mappings get a neutral 0.5.

**Step 1: Write the failing test**

File: `tests/signals/test_node_slot_saturation.py` (create)

```python
"""Tests for NodeSlotSaturationSignal detector."""

import pytest
from unittest.mock import MagicMock

from src.domain.models.node_state import NodeState
from src.signals.graph.node_signals import NodeSlotSaturationSignal


@pytest.fixture
def node_tracker_for_saturation():
    """Create a mock node tracker with several nodes."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = {
        "node-a": NodeState(
            node_id="node-a", label="a", created_at_turn=1, depth=0, node_type="attr"
        ),
        "node-b": NodeState(
            node_id="node-b", label="b", created_at_turn=1, depth=0, node_type="attr"
        ),
        "node-c": NodeState(
            node_id="node-c", label="c", created_at_turn=2, depth=0, node_type="attr"
        ),
        "node-d": NodeState(
            node_id="node-d", label="d", created_at_turn=2, depth=0, node_type="attr"
        ),
    }
    return tracker


class TestNodeSlotSaturationSignal:
    """Tests for graph.node.slot_saturation signal."""

    @pytest.mark.asyncio
    async def test_saturation_scores(self, node_tracker_for_saturation):
        """Nodes in saturated slots score low; underrepresented score high."""
        saturation_map = {
            "node-a": 4,  # slot with 4 nodes (most saturated)
            "node-b": 4,  # same slot
            "node-c": 1,  # slot with 1 node (underrepresented)
            # node-d: not mapped (no slot)
        }
        detector = NodeSlotSaturationSignal(
            node_tracker_for_saturation, slot_saturation_map=saturation_map
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        assert len(result) == 4
        # max_support = 4
        # node-a: 1 - 4/4 = 0.0 (saturated)
        assert result["node-a"] == pytest.approx(0.0)
        # node-b: 1 - 4/4 = 0.0 (saturated)
        assert result["node-b"] == pytest.approx(0.0)
        # node-c: 1 - 1/4 = 0.75 (underrepresented)
        assert result["node-c"] == pytest.approx(0.75)
        # node-d: no mapping = default 0.5
        assert result["node-d"] == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_empty_saturation_map(self, node_tracker_for_saturation):
        """With no slot mappings, all nodes get default 0.5."""
        detector = NodeSlotSaturationSignal(
            node_tracker_for_saturation, slot_saturation_map={}
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        for node_id in result:
            assert result[node_id] == 0.5

    @pytest.mark.asyncio
    async def test_single_slot(self, node_tracker_for_saturation):
        """All nodes in same slot with same count = all 0.0 (no diversity)."""
        saturation_map = {"node-a": 2, "node-b": 2, "node-c": 2, "node-d": 2}
        detector = NodeSlotSaturationSignal(
            node_tracker_for_saturation, slot_saturation_map=saturation_map
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        for node_id in result:
            assert result[node_id] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_signal_name(self, node_tracker_for_saturation):
        """Signal has correct signal_name."""
        detector = NodeSlotSaturationSignal(
            node_tracker_for_saturation, slot_saturation_map={}
        )
        assert detector.signal_name == "graph.node.slot_saturation"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/signals/test_node_slot_saturation.py -v
```
Expected: FAIL — `ImportError: cannot import name 'NodeSlotSaturationSignal'`

**Step 3: Implement NodeSlotSaturationSignal**

Add to `src/signals/graph/node_signals.py`, after `NodeTypePrioritySignal` and before `__all__`:

```python
class NodeSlotSaturationSignal(NodeSignalDetector):
    """Penalize nodes in over-represented canonical slots.

    Computes a diversity score where nodes in underrepresented thematic
    slots score higher (closer to 1.0) and nodes in saturated slots score
    lower (closer to 0.0). Uses candidate+active slots (min_support=1)
    for early coverage.

    Formula: 1.0 - (node_slot_support / max_slot_support)
    Nodes without slot mappings get a neutral default of 0.5.

    Namespaced signal: graph.node.slot_saturation
    Cost: low (dict lookup per node, data pre-fetched from DB)
    Refresh: per_turn
    """

    signal_name = "graph.node.slot_saturation"
    description = "Slot diversity score 0.0-1.0. Higher means node is in an underrepresented thematic slot."

    def __init__(self, node_tracker, slot_saturation_map: dict[str, int] | None = None):
        super().__init__(node_tracker)
        self._saturation_map = slot_saturation_map or {}
        self._default_score = 0.5

    async def detect(self, context, graph_state, response_text):  # noqa: ARG002
        results = {}
        all_states = self._get_all_node_states()

        if not self._saturation_map:
            return {nid: self._default_score for nid in all_states}

        max_support = max(self._saturation_map.values()) if self._saturation_map else 1

        for node_id in all_states:
            if node_id in self._saturation_map:
                support = self._saturation_map[node_id]
                results[node_id] = 1.0 - (support / max_support)
            else:
                results[node_id] = self._default_score

        return results
```

Update `__all__` to include `"NodeSlotSaturationSignal"`.

Update `src/signals/graph/__init__.py` to import and export `NodeSlotSaturationSignal`.

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/signals/test_node_slot_saturation.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/signals/graph/node_signals.py src/signals/graph/__init__.py tests/signals/test_node_slot_saturation.py
git commit -m "feat: implement NodeSlotSaturationSignal detector"
```

---

### Task 9: Wire NodeSlotSaturationSignal into detection service

**Files:**
- Modify: `src/services/node_signal_detection_service.py`
- Modify: `src/services/methodology_strategy_service.py`

**Step 1: Write the failing test**

Add to `tests/services/test_node_signal_detection_service.py`:

```python
@pytest.mark.asyncio
async def test_detect_includes_slot_saturation_signal(node_signal_service):
    """Test that detect() includes graph.node.slot_saturation when map provided."""
    mock_context = MagicMock()
    mock_graph_state = MagicMock()
    mock_node_tracker = MagicMock()

    mock_node_tracker.get_all_states.return_value = {
        "node-1": NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
            node_type="pain_point",
        ),
    }

    result = await node_signal_service.detect(
        context=mock_context,
        graph_state=mock_graph_state,
        response_text="test",
        node_tracker=mock_node_tracker,
        slot_saturation_map={"node-1": 3},
    )

    assert "graph.node.slot_saturation" in result["node-1"]
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/services/test_node_signal_detection_service.py::test_detect_includes_slot_saturation_signal -v
```
Expected: FAIL — `detect() got an unexpected keyword argument 'slot_saturation_map'`

**Step 3: Update NodeSignalDetectionService.detect()**

In `src/services/node_signal_detection_service.py`:

1. Add `slot_saturation_map` parameter:

```python
    async def detect(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        node_tracker: "NodeStateTracker",
        node_type_priorities: dict[str, float] | None = None,
        slot_saturation_map: dict[str, int] | None = None,
    ) -> Dict[str, Dict[str, Any]]:
```

2. Add import and detector:

```python
        from src.signals.graph.node_signals import (
            ...
            NodeSlotSaturationSignal,
        )
```

Add to detector list:
```python
            NodeSlotSaturationSignal(node_tracker, slot_saturation_map=slot_saturation_map),
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/services/test_node_signal_detection_service.py -v
```
Expected: PASS

**Step 5: Update MethodologyStrategyService to fetch and pass saturation map**

In `src/services/methodology_strategy_service.py`:

1. Add `canonical_slot_repo` to `__init__`:

```python
    def __init__(
        self,
        global_signal_service: Optional[GlobalSignalDetectionService] = None,
        node_signal_service: Optional[NodeSignalDetectionService] = None,
        canonical_slot_repo=None,
    ):
        ...
        self.canonical_slot_repo = canonical_slot_repo
```

2. Before the node signal detection call, fetch the saturation map:

```python
        # Fetch slot saturation map for diversity signal
        slot_saturation_map = None
        if self.canonical_slot_repo:
            try:
                slot_saturation_map = await self.canonical_slot_repo.get_slot_saturation_map(
                    session_id=context.session_id
                )
            except Exception as e:
                log.warning("slot_saturation_map_fetch_failed", error=str(e))

        # Detect node-level signals (delegated to NodeSignalDetectionService)
        node_signals = await self.node_signal_service.detect(
            context=context,
            graph_state=graph_state,
            response_text=response_text,
            node_tracker=node_tracker,
            node_type_priorities=merged_priorities if merged_priorities else None,
            slot_saturation_map=slot_saturation_map,
        )
```

3. Update the StrategySelectionStage initialization to pass canonical_slot_repo. Find where `MethodologyStrategyService()` is instantiated in `src/services/turn_pipeline/stages/strategy_selection_stage.py:48`:

```python
    def __init__(self, canonical_slot_repo=None):
        self.methodology_strategy = MethodologyStrategyService(
            canonical_slot_repo=canonical_slot_repo,
        )
```

4. Update the pipeline builder in `src/services/session_service.py` to pass `canonical_slot_repo` to `StrategySelectionStage`. Search for where `StrategySelectionStage()` is instantiated and pass the repo. The exact location depends on the pipeline wiring (around line 160).

**Step 6: Run all tests**

```bash
uv run pytest tests/ -v --tb=short
```
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/services/node_signal_detection_service.py src/services/methodology_strategy_service.py src/services/turn_pipeline/stages/strategy_selection_stage.py src/services/session_service.py tests/services/test_node_signal_detection_service.py
git commit -m "feat: wire NodeSlotSaturationSignal into detection and strategy services"
```

---

### Task 10: Add slot saturation signal weights to JTBD YAML

**Files:**
- Modify: `config/methodologies/jobs_to_be_done.yaml`

**Step 1: Add signal_weights for graph.node.slot_saturation**

Add to each strategy's `signal_weights:` section:

**explore_situation** (early breadth strategy — wants diversity most):
```yaml
      graph.node.slot_saturation.high: 0.7   # Underrepresented themes boosted
      graph.node.slot_saturation.low: -0.3   # Saturated themes penalized
```

**probe_alternatives** (wants fresh alternatives):
```yaml
      graph.node.slot_saturation.high: 0.6
      graph.node.slot_saturation.low: -0.2
```

**dig_motivation** (depth strategy — saturation less important):
```yaml
      graph.node.slot_saturation.high: 0.3
      graph.node.slot_saturation.low: -0.1
```

**validate_outcome** (wants well-covered themes for validation):
```yaml
      graph.node.slot_saturation.high: 0.2    # Slight preference for fresh themes
      graph.node.slot_saturation.low: 0.1     # But saturated is OK for validation
```

**revitalize** (wants fresh topics — high diversity weight):
```yaml
      graph.node.slot_saturation.high: 0.8
      graph.node.slot_saturation.low: -0.4
```

**uncover_obstacles** (wants diverse obstacles):
```yaml
      graph.node.slot_saturation.high: 0.5
      graph.node.slot_saturation.low: -0.2
```

**clarify_assumption** (targets confident claims — saturation neutral):
```yaml
      graph.node.slot_saturation.high: 0.3
      graph.node.slot_saturation.low: -0.1
```

**Step 2: Validate YAML loads**

```bash
uv run python -c "from src.methodologies import get_registry; r = get_registry(); c = r.get_methodology('jobs_to_be_done'); print('OK')"
```
Expected: `OK` (no validation errors)

**Step 3: Run full test suite**

```bash
uv run pytest tests/ -v --tb=short
```
Expected: ALL PASS

**Step 4: Commit**

```bash
git add config/methodologies/jobs_to_be_done.yaml
git commit -m "feat: add slot saturation signal weights to JTBD strategies"
```

---

### Task 11: Integration test — verify tie-breaking works end-to-end

**Files:**
- Create: `tests/signals/test_node_differentiation_integration.py`

**Step 1: Write integration test**

```python
"""Integration test: verify same-turn new nodes produce differentiated scores."""

import pytest
from unittest.mock import MagicMock

from src.domain.models.node_state import NodeState
from src.methodologies.registry import StrategyConfig
from src.methodologies.scoring import rank_strategy_node_pairs


class TestNodeDifferentiationIntegration:
    """Verify that type_priority and slot_saturation break ties among new nodes."""

    def test_same_turn_nodes_no_longer_tie(self):
        """8 new nodes from same turn should produce differentiated scores."""
        strategy = StrategyConfig(
            name="explore_situation",
            description="Explore",
            signal_weights={
                "graph.node.focus_streak.none": 0.6,
                "graph.node.yield_stagnation.false": 0.5,
                "graph.node.exhaustion_score.low": 0.4,
                "llm.valence.mid": 0.5,
                # NEW: differentiation signals
                "graph.node.type_priority": 0.6,
                "graph.node.slot_saturation.high": 0.7,
                "graph.node.slot_saturation.low": -0.3,
            },
        )

        global_signals = {
            "llm.valence": 0.5,  # mid
            "meta.interview.phase": "early",
        }

        # 8 nodes from the Turn 2 example, all with identical history
        base_node_signals = {
            "graph.node.exhausted": False,
            "graph.node.exhaustion_score": 0.0,
            "graph.node.yield_stagnation": False,
            "graph.node.focus_streak": "none",
            "graph.node.is_current_focus": False,
            "graph.node.recency_score": 0.0,
        }

        node_signals = {
            "node-1": {
                **base_node_signals,
                "graph.node.type_priority": 0.4,  # solution_approach
                "graph.node.slot_saturation": 0.0,  # saturated slot
            },
            "node-2": {
                **base_node_signals,
                "graph.node.type_priority": 0.9,  # job_trigger
                "graph.node.slot_saturation": 0.75,  # underrepresented
            },
            "node-3": {
                **base_node_signals,
                "graph.node.type_priority": 0.7,  # pain_point
                "graph.node.slot_saturation": 0.0,  # saturated
            },
            "node-4": {
                **base_node_signals,
                "graph.node.type_priority": 0.7,  # pain_point
                "graph.node.slot_saturation": 0.0,  # saturated
            },
            "node-5": {
                **base_node_signals,
                "graph.node.type_priority": 0.4,  # solution_approach
                "graph.node.slot_saturation": 0.0,  # saturated
            },
            "node-6": {
                **base_node_signals,
                "graph.node.type_priority": 0.7,  # pain_point
                "graph.node.slot_saturation": 1.0,  # new slot!
            },
            "node-7": {
                **base_node_signals,
                "graph.node.type_priority": 0.5,  # gain_point
                "graph.node.slot_saturation": 1.0,  # new slot!
            },
            "node-8": {
                **base_node_signals,
                "graph.node.type_priority": 0.6,  # job_statement
                "graph.node.slot_saturation": 0.0,  # saturated
            },
        }

        ranked, decomposition = rank_strategy_node_pairs(
            strategies=[strategy],
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Extract scores
        scores = [(nid, score) for _, nid, score in ranked]

        # Key assertion: NOT all same score (the original problem)
        unique_scores = set(score for _, score in scores)
        assert len(unique_scores) > 1, (
            f"Expected differentiated scores, got all identical: {scores}"
        )

        # The pain_point in a new slot (node-6) should rank highest
        # because it has high type_priority (0.7) AND max slot_saturation (1.0)
        assert ranked[0][1] == "node-6", (
            f"Expected node-6 (pain_point, new slot) to rank first, "
            f"got {ranked[0][1]} with score {ranked[0][2]}"
        )

        # Nodes in saturated slots should rank lower than similar types in fresh slots
        node6_score = next(s for _, nid, s in ranked if nid == "node-6")
        node3_score = next(s for _, nid, s in ranked if nid == "node-3")
        assert node6_score > node3_score, (
            "Node in underrepresented slot should score higher than same-type in saturated slot"
        )
```

**Step 2: Run test**

```bash
uv run pytest tests/signals/test_node_differentiation_integration.py -v
```
Expected: PASS

**Step 3: Commit**

```bash
git add tests/signals/test_node_differentiation_integration.py
git commit -m "test: integration test verifying node differentiation breaks ties"
```

---

### Task 12: Run simulation to validate end-to-end behavior

**Step 1: Run simulation with JTBD methodology**

```bash
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 10
```

**Step 2: Check the scoring CSV output**

Look at the generated CSV in `synthetic_interviews/`. Verify:
- Same-turn new nodes now have different `final_score` values
- The `signal_contributions` column includes `graph.node.type_priority` and `graph.node.slot_saturation` entries
- The selected node for each turn has a defensible priority (not random list-order)

**Step 3: Run ruff and check diagnostics**

```bash
ruff check . --fix && ruff format .
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete node differentiation signals (type_priority + slot_saturation)"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/methodologies/registry.py` | Add `node_type_priorities` field to `StrategyConfig`, load from YAML |
| `src/signals/graph/node_signals.py` | Add `NodeTypePrioritySignal` and `NodeSlotSaturationSignal` classes |
| `src/signals/graph/__init__.py` | Export new signal classes |
| `src/services/node_signal_detection_service.py` | Accept and wire `node_type_priorities` and `slot_saturation_map` |
| `src/services/methodology_strategy_service.py` | Merge priorities, fetch saturation map, pass to detection |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | Accept `canonical_slot_repo` |
| `src/services/session_service.py` | Pass `canonical_slot_repo` to `StrategySelectionStage` |
| `src/persistence/repositories/canonical_slot_repo.py` | Add `get_slot_saturation_map()` method |
| `config/methodologies/jobs_to_be_done.yaml` | Add `node_type_priorities` and saturation weights to all strategies |
| `tests/methodologies/test_registry.py` | Tests for StrategyConfig and registry loading |
| `tests/signals/test_node_type_priority.py` | Tests for type priority signal |
| `tests/signals/test_node_slot_saturation.py` | Tests for slot saturation signal |
| `tests/signals/test_node_differentiation_integration.py` | Integration test for tie-breaking |
| `tests/services/test_node_signal_detection_service.py` | Tests for detection service wiring |
| `tests/services/test_methodology_strategy_priorities.py` | Tests for priority merging logic |
| `tests/persistence/test_canonical_slot_repo_saturation.py` | Tests for saturation map query |
