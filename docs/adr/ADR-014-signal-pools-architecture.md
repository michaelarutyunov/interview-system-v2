# ADR-014: Signal Pools Architecture

**Status:** Accepted
**Date:** 2025-01-28
**Supersedes:** Parts of ADR-013 (signal detection)
**Related:** ADR-007 (YAML-Based Methodology Schema), ADR-010 (Pipeline Contracts)

## Context

### Problem Statement

ADR-013 introduced a methodology-centric architecture where each methodology (Means-End Chain, JTBD) had its own Python module with:
- Methodology-specific signal detectors
- Strategy implementations as Python classes
- Embedded focus selection logic
- Cross-response LLM signal caching

This approach led to:
1. **Code Duplication**: Similar signals (response_depth, sentiment) implemented multiple times
2. **Signal Collision Risk**: Different methodologies using same signal names with different semantics
3. **High Overhead**: Adding a new methodology required creating a full Python module
4. **Tight Coupling**: Strategy logic, focus selection, and signal detection tightly coupled
5. **Stale LLM Signals**: Caching LLM signals across responses led to outdated analysis

### Decision

Transition from **methodology-specific modules** to **shared signal pools** with YAML-based methodology definitions.

### Architecture Overview

```
src/methodologies/
├── signals/              # Shared signal pools
│   ├── common.py        # Base classes, enums
│   ├── graph/           # Graph-based signals
│   ├── llm/             # LLM-based signals (fresh per response)
│   ├── temporal/        # Temporal/history signals
│   ├── meta/            # Composite signals
│   └── registry.py      # ComposedSignalDetector
├── techniques/          # Shared "how-to" modules
│   ├── laddering.py
│   ├── elaboration.py
│   ├── probing.py
│   └── validation.py
├── config/              # YAML methodology definitions
│   ├── means_end_chain.yaml
│   └── jobs_to_be_done.yaml
└── registry.py          # MethodologyRegistry (YAML loader)
```

### Key Concepts

#### 1. Signal Pools with Namespacing

Signals are grouped by data source with namespace prefixes:
- **graph.***: Signals from knowledge graph (node_count, max_depth, orphan_count)
- **llm.***: LLM-based signals from response text (response_depth, sentiment, topics)
- **temporal.***: Turn-level temporal signals (strategy_repetition_count, turns_since_focus_change)
- **meta.***: Composite signals derived from other signals (interview_progress, exploration_score)

Example namespaced signals:
```python
{
    "graph.node_count": 5,
    "graph.max_depth": 2,
    "llm.response_depth": "surface",
    "llm.sentiment": "positive",
    "temporal.strategy_repetition_count": 3,
    "meta.interview_progress": 0.25
}
```

#### 2. Signal Detection Lifecycle

All signals implement `SignalDetector` base class:

```python
class SignalDetector(ABC):
    signal_name: str
    cost_tier: SignalCostTier = SignalCostTier.LOW
    refresh_trigger: RefreshTrigger = RefreshTrigger.PER_TURN

    @abstractmethod
    async def detect(self, context, graph_state, response_text) -> dict[str, Any]:
        ...
```

**Cost Tiers:**
- `FREE`: No computation (cached values)
- `LOW`: Simple calculations (counts, ratios)
- `MEDIUM`: Graph traversals
- `HIGH`: LLM calls

**Refresh Triggers:**
- `PER_RESPONSE`: Computed every response (LLM signals)
- `PER_TURN`: Computed once per turn
- `PER_SESSION`: Computed once per session

#### 3. Fresh LLM Signals

LLM signals extend `BaseLLMSignal` which guarantees fresh computation:

```python
class BaseLLMSignal(SignalDetector):
    cost_tier = SignalCostTier.HIGH
    refresh_trigger = RefreshTrigger.PER_RESPONSE

    async def detect(self, context, graph_state, response_text):
        return await self._analyze_with_llm(response_text)
```

**Key Principle**: LLM signals are **never cached across responses**. Each response gets fresh analysis.

#### 4. Composed Signal Detection

`ComposedSignalDetector` pools multiple signals and handles dependencies:

```python
detector = ComposedSignalDetector([
    "graph.node_count",
    "graph.max_depth",
    "llm.response_depth",
    "llm.sentiment",
    "meta.interview_progress"  # Depends on graph signals
])

signals = await detector.detect(context, graph_state, response_text)
```

**Two-Pass Detection:**
1. First pass: Detect all non-meta signals
2. Second pass: Detect meta signals (which may depend on first-pass signals)

#### 5. YAML-Based Methodology Configuration

Methodologies are defined in YAML with three sections:

```yaml
methodology:
  name: means_end_chain
  display_name: Means-End Chain

  # Signal definitions (namespaced)
  signals:
    graph: [graph.node_count, graph.max_depth, ...]
    llm: [llm.response_depth, llm.sentiment, ...]
    temporal: [temporal.strategy_repetition_count, ...]
    meta: [meta.interview_progress]

  # Strategy definitions (weighted by signals)
  strategies:
    - name: deepen
      technique: laddering
      signal_weights:
        llm.response_depth.surface: 0.8
        graph.max_depth: 0.5
      focus_preference: shallow
```

#### 6. Techniques vs Strategies

**Techniques** (how-to):
- Shared, reusable modules
- Define how to generate questions
- No knowledge of when to use
- Examples: LadderingTechnique, ElaborationTechnique

**Strategies** (when-to-use):
- Methodology-specific
- Define when to apply which technique
- Use signal weights for selection
- Defined in YAML configs

#### 7. Focus Selection Service

`FocusSelectionService` centralizes focus selection logic:

```python
class FocusSelectionService:
    async def select(self, input_data: FocusSelectionInput) -> Optional[str]:
        # Maps strategy.focus_preference to actual focus node
        # shallow: nodes with depth < 2
        # recent: most recently created nodes
        # related: nodes with most relationships
        # deep: nodes with depth >= 3
```

### Data Flow

```
User Response
    ↓
StrategySelectionStage
    ↓
MethodologyStrategyService.select_strategy()
    ↓
1. Load methodology config from YAML
    ↓
2. Create ComposedSignalDetector from config.signals
    ↓
3. Detect all signals (namespaced)
    ↓
4. Score strategies using signal_weights
    ↓
5. Select best strategy
    ↓
6. FocusSelectionService.select() for focus node
    ↓
Return (strategy, focus, alternatives, signals)
```

### Implementation Details

#### Signal Namespace Format

All signals use dot-notation namespacing:
- `graph.{signal_name}`: Graph-derived signals
- `llm.{signal_name}`: LLM-derived signals
- `temporal.{signal_name}`: Temporal/history signals
- `meta.{signal_name}`: Composite/directory signals

#### Signal Value Matching

Strategy scoring supports compound key matching:

```python
# YAML signal weight
signal_weights:
  llm.response_depth.surface: 0.8  # Matches when llm.response_depth == "surface"

# Detected signals
signals = {
    "llm.response_depth": "surface",
    "graph.max_depth": 2
}

# Score calculation
if signals["llm.response_depth"] == "surface":
    score += 0.8
```

### Migration Path

#### From Old Architecture

```python
# Old: Methodology-specific module
class MeansEndChainMethodology(BaseMethodology):
    def detect_signals(self, context):
        return {
            "response_depth": self._analyze_depth(...),
            "sentiment": self._analyze_sentiment(...)
        }

# New: Shared signal pool
class ResponseDepthSignal(BaseLLMSignal):
    signal_name = "llm.response_depth"
    # Implementation shared across all methodologies
```

#### YAML Config Creation

1. Identify methodology-specific signals
2. Map to shared signal pool equivalents
3. Define strategies with signal weights
4. Configure focus_preferences per strategy
5. Add to `src/methodologies/config/{methodology}.yaml`

### Benefits

1. **Reduced Duplication**: Shared signals across methodologies
2. **Consistent Semantics**: Namespaced signals prevent collision
3. **Lower Overhead**: New methodologies only require YAML config
4. **Better Testability**: Signals tested independently of methodologies
5. **Fresh Analysis**: LLM signals always computed on current response
6. **Explicit Costs**: Cost tiers signal computational expense
7. **Clear Refresh Triggers**: Explicit control over when signals refresh

### Tradeoffs

**Pros:**
- Shared signal pool reduces code duplication
- YAML configs make methodology definitions declarative
- Namespaced signals prevent naming collisions
- Fresh LLM signals ensure up-to-date analysis
- Focus selection centralized and testable

**Cons:**
- More complex initial setup (requires signal pool infrastructure)
- YAML adds configuration layer (vs pure Python)
- Signal naming must be disciplined (namespace adherence)
- Migration required for existing methodologies

### Alternatives Considered

1. **Keep methodology-specific modules**: Rejected due to duplication and collision risk
2. **Use database for signal storage**: Rejected as overkill for MVP
3. **Cache LLM signals with TTL**: Rejected in favor of fresh computation per response
4. **Dynamic signal discovery**: Rejected in favor of explicit YAML configuration

### Related Documents

- ADR-007: YAML-Based Methodology Schema
- ADR-010: Pipeline Contracts Formalization
- ADR-013: Methodology-Centric Architecture (supersedes signal detection portions)
- docs/plans/refactor-signals-strategies-plan.md: Detailed implementation plan

### Implementation Status

- [x] Signal pool base classes and enums
- [x] Graph signals (node_count, max_depth, orphan_count, etc.)
- [x] LLM signals (response_depth, sentiment, topics, etc.)
- [x] Temporal signals (strategy_repetition_count, turns_since_focus_change)
- [x] Meta signals (interview_progress, exploration_score)
- [x] ComposedSignalDetector with two-pass detection
- [x] Technique pool (laddering, elaboration, probing, validation)
- [x] MethodologyRegistry (YAML loader)
- [x] MethodologyStrategyService integration
- [x] FocusSelectionService
- [x] YAML configs for MEC and JTBD
- [x] Test updates for namespaced signals
- [x] Deletion of old methodology modules

### Future Considerations

1. **Signal Cost Optimization**: Use cost_tier to skip expensive signals when not needed
2. **Signal Caching**: Consider per-response caching for expensive non-LLM signals
3. **Signal Composition**: Allow user-defined composite signals in YAML
4. **Signal Testing**: Auto-generate tests for signal detection
5. **Methodology Authoring**: Create tools to help generate YAML configs
