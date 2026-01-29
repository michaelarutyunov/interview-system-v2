# Refactor Plan: Signal Pools & Technique-Strategy Separation

## Executive Summary

Refactor the methodologies module from "folder per methodology" to **shared signal pools** with YAML-based methodology definitions. This eliminates duplication, enables reuse, and creates clear architectural boundaries.

**Current Problems:**
- Duplicated signals (strategy_repetition_count in both MEC and JTBD)
- Duplicated strategy logic (explore/clarify variants across methodologies)
- Focus selection logic scattered across strategies
- No LLM signal reusability
- Tight coupling between methodology and signals

**Target State:**
- Signal pools grouped by data source (graph, llm, temporal, meta)
- Techniques as reusable "how-to" modules
- **Strategies defined per-methodology in YAML** (not shared pool)
- FocusSelectionService as injected dependency
- **Fresh LLM signals every response** (no stale/cached signals)

**Key Decisions (User Input):**
1. **Big bang migration** - Single coordinated refactor, no dual maintenance
2. **Namespaced signals** - `graph.node_count` (not `node_count`)
3. **Strategies in YAML only** - Methodology-specific, defined in config (no shared strategy files)
4. **Fresh LLM signals** - Recompute every response, minimal caching (only within-turn efficiency)

---

## Phase 1: New Directory Structure

```
src/methodologies/
├── __init__.py                  # Public API
├── registry.py                  # MethodologyRegistry, load from YAML configs
├── base.py                      # Updated base classes
├── scoring.py                   # Strategy ranking (keep)
│
├── config/                      # YAML methodology definitions
│   ├── schema.yaml              # Configuration schema
│   ├── means_end_chain.yaml     # MEC: signals + strategies (techniques separate)
│   └── jobs_to_be_done.yaml     # JTBD: signals + strategies (techniques separate)
│
├── signals/                     # SHARED SIGNAL POOLS
│   ├── __init__.py              # Public API: from methodologies.signals.graph import GraphNodeCountSignal
│   ├── common.py                # BaseSignalDetector, SignalState (shared)
│   │
│   ├── graph/                   # Graph-derived signals (namespaced: graph.*)
│   │   ├── __init__.py
│   │   ├── structure.py          # GraphNodeCountSignal, GraphEdgeCountSignal, OrphanCountSignal
│   │   ├── depth.py              # GraphMaxDepthSignal, GraphAvgDepthSignal, DepthByElementSignal
│   │   ├── coverage.py           # CoverageBreadthSignal, MissingTerminalValueSignal
│   │   ├── connectivity.py       # EdgeDensitySignal, DisconnectedNodesSignal
│   │   └── nodes_by_type.py       # NodesByTypeSignal (helper), ElementCountsSignal
│   │
│   ├── llm/                     # LLM-derived signals (FRESH every response)
│   │   ├── __init__.py
│   │   ├── common.py              # BaseLLMSignal (with LLM client, NO cross-response caching)
│   │   ├── depth.py              # ResponseDepthSignal (surface|moderate|deep)
│   │   ├── quality.py             # SentimentSignal, UncertaintySignal, AmbiguitySignal
│   │   ├── extractable.py         # ExtractableSignal, ExtractabilityReasonSignal
│   │   └── engagement.py          # ResponseLengthSignal, EnthusiasmSignal
│   │
│   ├── temporal/                 # History-derived signals (namespaced: temporal.*)
│   │   ├── __init__.py
│   │   ├── strategy_history.py    # StrategyRepetitionCountSignal, TurnsSinceChangeSignal
│   │   ├── conversation.py        # TurnCountSignal, TimeSinceLastTurnSignal
│   │   ├── trends.py              # CoverageTrendSignal, DepthTrendSignal
│   │   └── patterns.py            # StuckPatternSignal, AlternationPatternSignal
│   │
│   └── meta/                     # Composite signals (depend on others, namespaced: meta.*)
│       ├── __init__.py
│       ├── progress.py            # InterviewProgressSignal, CompletionLikelihoodSignal
│       ├── saturation.py           # NewLearningRateSignal, RedundancySignal
│       ├── quality.py             # OverallResponseQualitySignal
│       └── triggers.py            # ShouldCloseSignal, ShouldSwitchStrategySignal
│
└── techniques/                  # SHARED TECHNIQUE POOLS (the "how")
    ├── __init__.py
    ├── common.py                # BaseTechnique class
    ├── laddering.py              # LadderingTechnique (why, what, how)
    ├── elaboration.py            # ElaborationTechnique (tell me more)
    ├── probing.py                # ProbingTechnique (alternatives, obstacles)
    └── validation.py             # ValidationTechnique (outcome clarity)


src/services/
├── focus_selection_service.py     # NEW: Service for selecting focus
└── methodology_strategy_service.py # UPDATE: Uses YAML-loaded registry


tests/
├── methodologies/
│   ├── signals/                  # Test signal pools
│   │   ├── test_graph_signals.py
│   │   ├── test_llm_signals.py
│   │   ├── test_temporal_signals.py
│   │   └── test_meta_signals.py
│   ├── techniques/               # Test techniques
│   │   ├── test_laddering_technique.py
│   │   └── test_elaboration_technique.py
│   └── test_registry.py          # Test methodology loading from YAML
│
└── services/
    └── test_focus_selection_service.py  # NEW
```

---

## Phase 2: Signal Pool Implementation

### 2.1 Namespaced Signals

```python
# signals/graph/structure.py
class GraphNodeCountSignal(SignalDetector):
    """Number of nodes in the graph."""

    cost_tier = "free"
    refresh_trigger = "graph_update"
    signal_name = "graph.node_count"  # Namespaced!

    async def detect(self, context, graph_state, response_text):
        return {"graph.node_count": graph_state.node_count}
```

### 2.2 Fresh LLM Signals (No Cross-Response Caching)

```python
# signals/llm/common.py
class BaseLLMSignal(SignalDetector):
    """Base for LLM signals with fresh computation."""

    cost_tier = "high"
    refresh_trigger = "per_response"  # Always recompute per response

    def __init__(self, llm_client):
        self.llm = llm_client
        # NO cross-response caching - always fresh

    async def detect(self, context, graph_state, response_text):
        # Always compute fresh - user wants current signal state
        return await self._analyze_with_llm(response_text)
```

### 2.3 Signal Composition

```python
# registry.py
class MethodologySignalDetector:
    """Composed signal detector from YAML config."""

    def __init__(self, signal_configs: List[dict]):
        self.detectors = self._create_detectors(signal_configs)

    async def detect(self, context, graph_state, response_text):
        """Detect all signals fresh every turn."""
        all_signals = {}

        # Detect all signals (LLM signals compute fresh each time)
        for detector in self.detectors:
            signals = await detector.detect(context, graph_state, response_text)
            all_signals.update(signals)

        # Return as dict (no methodology-specific state class needed)
        return all_signals
```

---

## Phase 3: Techniques (The "How")

```python
# techniques/common.py
class Technique(ABC):
    """A questioning technique - the 'how' of asking."""

    name: str
    description: str

    @abstractmethod
    async def generate_questions(
        self,
        focus: str,
        context: "PipelineContext",
    ) -> list[str]:
        """Generate 1-3 questions using this technique."""
        ...


# techniques/laddering.py
class LadderingTechnique(Technique):
    """Means-end chain probing technique."""

    name = "laddering"
    description = "Probe deeper: 'why is that important?'"

    async def generate_questions(self, focus, context) -> list[str]:
        questions = [
            f"Why is {focus} important to you?",
            f"What does {focus} give you?",
        ]

        # Check current depth from namespaced signal
        if context.signals.get("graph.max_depth", 0) < 2:
            questions.append(f"And what does that mean for you?")

        return questions
```

---

## Phase 4: YAML Configuration (Strategies, Not Techniques)

### 4.1 Schema

```yaml
# config/schema.yaml
methodology:
  name: str
  description: str

  # Signals to include (select from pools)
  signals:
    graph: list[str]      # ["graph.node_count", "graph.max_depth", "graph.coverage_breadth"]
    llm: list[str]        # ["llm.response_depth", "llm.sentiment"]
    temporal: list[str]   # ["temporal.strategy_repetition_count"]
    meta: list[str]       # ["meta.interview_progress"]

  # Strategies defined HERE (not in separate files)
  strategies:
    - name: str
      technique: str      # "laddering", "elaboration", "probing", "validation"
      signal_weights: dict  # When to use this strategy
      focus_preference: str  # "shallow", "recent", "related", "deep"
```

### 4.2 Example Config (MEC)

```yaml
# config/means_end_chain.yaml
methodology:
  name: means_end_chain
  description: "Means-End Chain interview methodology"

  signals:
    graph:
      - graph.node_count
      - graph.max_depth
      - graph.coverage_breadth
      - graph.missing_terminal_value
      - graph.edge_density

    llm:
      - llm.response_depth

    temporal:
      - temporal.strategy_repetition_count
      - temporal.turns_since_strategy_change

    meta:
      - meta.interview_progress

  strategies:
    - name: deepen
      technique: laddering
      signal_weights:
        llm.response_depth.surface: 0.8
        llm.response_depth.moderate: 0.3
        graph.max_depth: 0.5
      focus_preference: shallow

    - name: clarify
      technique: probing
      signal_weights:
        graph.edge_density: 0.7
        graph.coverage_breadth: -0.3
      focus_preference: related

    - name: explore
      technique: elaboration
      signal_weights:
        graph.coverage_breadth: 0.6
        llm.response_new_concepts: 0.4
      focus_preference: recent

    - name: reflect
      technique: validation
      signal_weights:
        graph.max_depth: 0.7
        meta.interview_progress: 0.5
      focus_preference: deep
```

---

## Phase 5: FocusSelectionService

```python
# services/focus_selection_service.py
class FocusSelectionService:
    """Service for selecting what to focus on next."""

    async def select(
        self,
        strategy: str,
        context: "PipelineContext",
        graph_state: "GraphState",
    ) -> Optional[str]:
        """
        Select focus based on strategy requirements.

        Strategy-specific logic from YAML config:
        - deepen: prefer nodes with low depth
        - explore: prefer recently added nodes
        - clarify: prefer nodes with relationships
        """
        if strategy == "deepen":
            return await self._select_for_laddering(context, graph_state)
        elif strategy == "explore":
            return await self._select_for_exploration(context, graph_state)
        elif strategy in ["clarify", "probe"]:
            return await self._select_for_clarification(context, graph_state)
        elif strategy == "reflect":
            return await self._select_for_validation(context, graph_state)
        elif strategy == "close":
            return None
        else:
            return self._select_most_recent(context)

    async def _select_for_laddering(self, context, graph_state):
        """For deepening, prefer nodes with shallow depth."""
        shallow_nodes = [
            n for n in context.recent_nodes
            if graph_state.depth_metrics.depth_by_element.get(str(n.id), 0) < 2
        ]
        return shallow_nodes[0].label if shallow_nodes else None
```

---

## Phase 6: Big Bang Migration Path

### Step 1: Create New Structure (2-3 hours)
```
mkdir -p src/methodologies/{signals/{graph,llm,temporal,meta},techniques,config}
Create base classes, common utilities
```

### Step 2: Implement Signal Pools (6-8 hours)
```
1. Implement graph/ signals (move/extract from MEC/JTBD)
2. Implement llm/ signals (extract and improve)
3. Implement temporal/ signals (extract common)
4. Implement meta/ signals (new composite signals)
```

### Step 3: Implement Techniques (2-3 hours)
```
1. Create base Technique class
2. Extract laddering from ladder_deeper.py
3. Create elaboration, probing, validation techniques
```

### Step 4: Implement FocusSelectionService (2-3 hours)
```
1. Create service in src/services/
2. Extract focus logic from existing strategies
3. Write tests
```

### Step 5: Implement YAML Registry (4-5 hours)
```
1. Create YAML schema
2. Implement config loader
3. Create MEC and JTBD configs (with strategies!)
4. Update get_methodology() to use registry
```

### Step 6: Update Services (4-6 hours)
```
1. Update MethodologyStrategyService to use composed signals
2. Update StrategySelectionStage to use FocusSelectionService
3. Update QuestionGenerationStage to use FocusSelectionService
4. Update PipelineContext to pass signals through
```

### Step 7: Update Tests (4-6 hours)
```
1. Rewrite methodology tests for signal pools
2. Update integration tests
3. Update pipeline tests
4. Write new tests (techniques, focus service, registry)
```

### Step 8: Big Bang Switch (2-3 hours)
```
1. Delete old structure:
   - src/methodologies/means_end_chain/
   - src/methodologies/jtbd/
2. Update __init__.py to point to registry
3. Run full test suite
4. Fix any remaining issues
```

---

## Phase 7: What Needs Updating

### Services
- [ ] `src/services/methodology_strategy_service.py` - Use composed signal detector from registry
- [ ] `src/services/turn_pipeline/stages/strategy_selection_stage.py` - Use FocusSelectionService
- [ ] `src/services/turn_pipeline/stages/question_generation_stage.py` - Use FocusSelectionService
- [ ] `src/services/turn_pipeline/context.py` - Pass signals through pipeline stages

### Tests
- [ ] `tests/methodologies/` - Complete rewrite
- [ ] `tests/integration/test_full_interview_flow.py` - Update for new structure
- [ ] `tests/pipeline/test_strategy_selection_*.py` - Update for service injection
- [ ] `tests/services/test_focus_selection_service.py` - New
- [ ] `tests/methodologies/test_registry.py` - New

### Documentation
- [ ] Update ADRs for new architecture
- [ ] Update README in methodologies/
- [ ] Document YAML schema

---

## Success Criteria

1. **Signal Reuse**: Same signal usable across methodologies
2. **Technique Reuse**: Laddering usable by any methodology that needs it
3. **No Duplication**: Zero copy-paste of signal/strategy logic
4. **YAML Config**: Methodologies fully defined in YAML
5. **Focus as Service**: Centralized, testable focus selection
6. **Namespaced Signals**: Clear `graph.*`, `llm.*`, `temporal.*`, `meta.*` prefixes
7. **Fresh LLM Signals**: Always computed per response, no staleness

---

## Migration Effort (Big Bang)

| Phase | Effort | Risk |
|-------|--------|------|
| 1. Directory structure | 2-3 hours | Low |
| 2. Signal pools | 6-8 hours | Medium |
| 3. Techniques | 2-3 hours | Low |
| 4. Focus service | 2-3 hours | Low |
| 5. YAML registry | 4-5 hours | Medium |
| 6. Services update | 4-6 hours | High |
| 7. Tests update | 4-6 hours | High |
| 8. Big bang switch | 2-3 hours | High |
| **Total** | **26-37 hours** | **High** |

---

## Updated YAML Config Examples

### Means-End Chain

```yaml
# config/means_end_chain.yaml
methodology:
  name: means_end_chain
  description: "Means-End Chain interview methodology"

  signals:
    graph:
      - graph.node_count
      - graph.max_depth
      - graph.coverage_breadth
      - graph.missing_terminal_value
      - graph.edge_density

    llm:
      - llm.response_depth

    temporal:
      - temporal.strategy_repetition_count
      - temporal.turns_since_strategy_change

    meta:
      - meta.interview_progress

  strategies:
    - name: deepen
      technique: laddering
      signal_weights:
        llm.response_depth.surface: 0.8
        llm.response_depth.moderate: 0.3
        graph.max_depth: 0.5
      focus_preference: shallow

    - name: clarify
      technique: probing
      signal_weights:
        graph.edge_density: 0.7
        graph.coverage_breadth: -0.3
      focus_preference: related

    - name: explore
      technique: elaboration
      signal_weights:
        graph.coverage_breadth: 0.6
      focus_preference: recent

    - name: reflect
      technique: validation
      signal_weights:
        graph.max_depth: 0.7
        meta.interview_progress: 0.5
      focus_preference: deep
```

### Jobs-to-be-Done

```yaml
# config/jobs_to_be_done.yaml
methodology:
  name: jobs_to_be_done
  description: "Jobs-to-be-Done interview methodology"

  signals:
    graph:
      - graph.node_count
      - graph.orphan_count

    llm:
      - llm.response_depth
      - llm.sentiment
      - llm.mentioned_competitor

    temporal:
      - temporal.strategy_repetition_count
      - temporal.turns_since_strategy_change

    meta:
      - meta.interview_progress
      - meta.coverage_balance

  strategies:
    - name: explore_situation
      technique: elaboration
      signal_weights:
        graph.job_identified: 0.5
        llm.mentioned_trigger: 0.3
      focus_preference: recent

    - name: probe_alternatives
      technique: probing
      signal_weights:
        llm.mentioned_competitor: 0.5
        graph.alternatives_count: -0.4
      focus_preference: related

    - name: dig_motivation
      technique: laddering
      signal_weights:
        llm.response_depth.surface: 0.7
        graph.motivation_depth: -0.5
      focus_preference: shallow

    - name: uncover_obstacles
      technique: probing
      signal_weights:
        llm.mentioned_struggle: 0.5
        graph.obstacles_count: -0.4
      focus_preference: related

    - name: validate_outcome
      technique: validation
      signal_weights:
        graph.outcome_clarity: -0.5
        meta.interview_progress: 0.3
      focus_preference: deep

    - name: balance_coverage
      technique: elaboration
      signal_weights:
        meta.coverage_imbalance: 0.7
      focus_preference: shallow
```
