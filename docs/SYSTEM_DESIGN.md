# Interview System v2 - System Design

> **Purpose**: Architecture reference for the interview system.
> **Related**: [Pipeline Contracts](./pipeline_contracts.md) | [Data Flow Paths](./data_flow_paths.md)

## Table of Contents

- [Overview](#overview)
- [Core Architecture](#core-architecture)
- [The Turn Pipeline](#the-turn-pipeline)
- [Signal Pools Architecture](#signal-pools-architecture)
- [Concept-Driven Coverage](#concept-driven-coverage)
- [Methodology-Centric Design](#methodology-centric-design)
- [Knowledge Graph State](#knowledge-graph-state)
- [Question Generation](#question-generation)
- [LLM Integration](#llm-integration)
- [Container Deployment](#container-deployment)

---

## Overview

A knowledge-graph-based conversational research system that conducts semi-structured interviews through adaptive questioning. Each turn flows through a **12-stage pipeline** that transforms user input into follow-up questions while building a knowledge graph.

### Key Design Principles

1. **Pipeline Pattern**: 12 stages with Pydantic contracts between stages
2. **Dual-Graph Architecture**: Surface graph (fidelity) + canonical graph (stable, deduplicated signals)
3. **Signal Pools**: Namespaced signals from graph, LLM, temporal, and meta sources drive strategy selection
4. **Methodology-Centric**: All interview behavior driven by pluggable YAML configs
5. **No Hardcoded Keywords**: Configurable values live in YAML, not code
6. **Feature Flags**: Optional stages (`enable_srl`, `enable_canonical_slots`) for graceful skip
7. **Fail-Fast**: Errors raise immediately rather than degrading silently

### Pipeline Stages

| Stage | Name | Purpose |
|-------|------|---------|
| 1 | ContextLoadingStage | Session metadata, turn number, conversation history |
| 2 | UtteranceSavingStage | Persist user utterance to DB |
| 2.5 | SRLPreprocessingStage | Linguistic parsing (optional: `enable_srl`) |
| 3 | ExtractionStage | Extract concepts/relationships via LLM |
| 4 | GraphUpdateStage | Update surface graph with deduplication |
| 4.5 | SlotDiscoveryStage | Map surface nodes to canonical slots (optional: `enable_canonical_slots`) |
| 5 | StateComputationStage | Refresh graph metrics and saturation indicators |
| 6 | StrategySelectionStage | Signal Pools → joint strategy-node scoring |
| 7 | ContinuationStage | Decide if interview continues |
| 8 | QuestionGenerationStage | Generate follow-up question via LLM |
| 9 | ResponseSavingStage | Persist system response to DB |
| 10 | ScoringPersistenceStage | Save scoring, update session state, persist LLM usage |

### Key Configuration (`config/interview_config.yaml`)

- **Phase turns**: Exploratory (6), Focused (7), Closing (2) — auto-calculated to `max_turns=15`
- **Deduplication**: Surface similarity 0.80, Canonical similarity 0.60, Min support nodes 2
- **LLM clients**: Four task-specific client types (see [LLM Integration](#llm-integration))

---

## Core Architecture

### Two-Layer Design

Separates **what to explore** (concepts) from **how to explore it** (methodologies):

```
CONCEPT LAYER     →    Domain entities and research objectives (YAML)
METHODOLOGY LAYER →    Node types, strategies, signals, question guidance (YAML)
```

The same concept (e.g., headphones) can be studied with different methodologies (JTBD, MEC, Critical Incident) without changing the concept definition.

### Dual-Graph Architecture

| Layer | Purpose | Dedup Threshold |
|-------|---------|----------------|
| **Surface Graph** (KGNode / KGEdge) | Preserves respondent language exactly; full provenance to source utterances | 0.80 cosine |
| **Canonical Graph** (CanonicalSlot / CanonicalEdge) | Abstracts language variation ("fast car" = "quick vehicle" = `speed_performance`); LLM-proposed groupings promoted after min support | 0.60 cosine |

Canonical slot lifecycle: `candidate` → `active` (requires `support_count >= canonical_min_support_nodes`)

### Pipeline Context and Contracts

`PipelineContext` (`src/services/turn_pipeline/context.py`) accumulates stage outputs as named Pydantic contract fields. Convenience properties derive from contracts; ordering enforced via `RuntimeError` on premature access.

| Stage | Contract |
|-------|----------|
| 1 | `ContextLoadingOutput` — methodology, concept_id, turn_number, history, strategy_history |
| 2 | `UtteranceSavingOutput` — user_utterance_id, utterance |
| 2.5 | `SrlPreprocessingOutput` — discourse_relations, srl_frames |
| 3 | `ExtractionOutput` — concepts, relationships |
| 4 | `GraphUpdateOutput` — nodes_added, edges_added, counts |
| 4.5 | `SlotDiscoveryOutput` — slots_created, slots_updated, mappings_created |
| 5 | `StateComputationOutput` — graph_state, canonical_graph_state, saturation_metrics |
| 6 | `StrategySelectionOutput` — strategy, focus, signals, node_signals, score_decomposition |
| 7 | `ContinuationOutput` — should_continue, reason, turns_remaining |
| 8 | `QuestionGenerationOutput` — question, strategy, focus |
| 9 | `ResponseSavingOutput` — system_utterance_id, system_utterance |
| 10 | `ScoringPersistenceOutput` — turn_number, strategy, depth_score, saturation_score |

### Key Domain Models

**KGNode** (surface concept): `label`, `node_type`, `source_utterance_ids`, `stance` (-1/0/+1), `embedding`

**GraphState**: `node_count`, `edge_count`, `depth_metrics` (max_depth, longest_chain_path), `saturation_metrics`, `current_phase`, `strategy_history` (deque, maxlen=30)

**CanonicalSlot**: `slot_name` (LLM-generated), `node_type`, `status`, `support_count`, `embedding` (float32, 300-dim via spaCy)

**CanonicalGraphState**: `concept_count` (active only), `orphan_count`, `avg_support`, `max_depth`

### Services

**GraphService** (`src/services/graph_service.py`): exact match → semantic similarity → create new. Cross-turn edge resolution. Aggregates surface edges to canonical edges.

**CanonicalSlotService** (`src/services/canonical_slot_service.py`): batched LLM slot proposals (max 8 nodes/call), embedding similarity merge, lemmatization, candidate→active promotion.

### Configuration Layout

```
config/
├── concepts/              # Production research topics
│   ├── coffee_jtbd_v2.yaml
│   ├── glp1_food_jtbd.yaml
│   ├── glp1_food_mec.yaml
│   ├── glp1_food_mec_flex.yaml
│   ├── glp1_food_mec_strict.yaml
│   └── meal_planning_jtbd_v2.yaml
├── concepts_wip/          # Work-in-progress (not loaded in production)
├── methodologies/         # Interview logic
│   ├── jobs_to_be_done.yaml
│   ├── jobs_to_be_done_v2.yaml
│   ├── means_end_chain.yaml
│   ├── means_end_chain_v2_strict.yaml
│   ├── means_end_chain_v3_flex.yaml
│   ├── critical_incident.yaml
│   ├── customer_journey_mapping.yaml
│   └── repertory_grid.yaml
├── personas/              # Synthetic respondent profiles
│   ├── baseline_cooperative.yaml
│   ├── brief_responder.yaml
│   ├── emotionally_reactive.yaml
│   ├── fatiguing_responder.yaml
│   ├── glp1_user.yaml
│   ├── retrospective_rationalizer.yaml
│   ├── single_topic_fixator.yaml
│   ├── skeptical_analyst.yaml
│   ├── uncertain_hedger.yaml
│   └── verbose_tangential.yaml
└── interview_config.yaml  # Phases, dedup thresholds, LLM config
```

---

## The Turn Pipeline

### Continuation and Termination

**ContinuationStage** (Stage 7) checks in order:

| Reason | Condition |
|--------|-----------|
| `Maximum turns reached` | `turn_number >= max_turns` |
| `Closing strategy selected` | Strategy with `generates_closing_question=true` |
| `graph_saturated` | `consecutive_low_info >= 5` (after MIN_TURN=5) |
| `quality_degraded` | `consecutive_shallow >= 6` |
| `depth_plateau` | `consecutive_depth_plateau >= 6` (zero-yield turns only) |
| `all_nodes_exhausted` | All nodes have `turns_since_last_yield >= 3` |

### TurnResult

The pipeline returns `TurnResult` (`src/services/turn_pipeline/result.py`) with: `turn_number`, `extracted`, `graph_state`, `scoring`, `strategy_selected`, `next_question`, `should_continue`, `signals`, `strategy_alternatives`, `canonical_graph`, `nodes_added`, `edges_added`, `saturation_metrics`, `node_signals`, `score_decomposition`.

---

## Signal Pools Architecture

### Signal Namespacing

| Pool | Namespace | Key Signals |
|------|-----------|-------------|
| **Graph (Global)** | `graph.*` | `node_count`, `max_depth`, `orphan_count`, `chain_completion.ratio`, `chain_completion.has_complete`, `canonical_concept_count`, `canonical_edge_density`, `canonical_exhaustion_score` |
| **Graph (Node)** | `graph.node.*` | `exhausted`, `exhaustion_score`, `yield_stagnation`, `focus_streak`, `recency_score`, `is_current_focus`, `is_orphan`, `edge_count`, `has_outgoing`; chain topology: `gap_above`, `gap_below`, `level_skip`, `branching_deficit`, `fan_in`, `level_gap_size` (MEC only) |
| **LLM** | `llm.*` | `response_depth` (categorical: surface/shallow/moderate/deep), `valence`, `certainty`, `specificity`, `engagement`, `intellectual_engagement` (all float [0,1]), `global_response_trend` |
| **Temporal** | `temporal.*` | `strategy_repetition_count`, `turns_since_strategy_change` |
| **Meta (Global)** | `meta.*` | `interview.phase`, `conversation.saturation`, `canonical.saturation` |
| **Meta (Node)** | `meta.node.*` | `opportunity` (exhausted/probe_deeper/fresh) |
| **Technique (Node)** | `technique.node.*` | `strategy_repetition` (none/low/medium/high) |

### LLM Signals

All 6 LLM signals detected in a single batched API call via `LLMBatchDetector`. Rubrics loaded from `src/signals/llm/prompts/signals.md`.

- **Categorical** (response_depth): Integer 1–5 → string (surface/shallow/moderate/deep)
- **Continuous** (others): Integer 1–5 → float [0,1] via `(score-1)/4`; matched via `.low`/`.mid`/`.high` threshold bins

Signal creation uses zero-boilerplate `@llm_signal` decorator:
```python
@llm_signal(signal_name="llm.response_depth", rubric_key="response_depth", ...)
class ResponseDepthSignal(BaseLLMSignal):
    pass
```

### Node-Level Signals

| Signal | Type | Detector |
|--------|------|----------|
| `graph.node.exhausted` | bool | `NodeExhaustedSignal` |
| `graph.node.exhaustion_score` | float 0–1 | `NodeExhaustionScoreSignal` |
| `graph.node.yield_stagnation` | bool (3+ turns) | `NodeYieldStagnationSignal` |
| `graph.node.focus_streak` | categorical | `NodeFocusStreakSignal` |
| `graph.node.is_current_focus` | bool | `NodeIsCurrentFocusSignal` |
| `graph.node.recency_score` | float 0–1 | `NodeRecencyScoreSignal` |
| `graph.node.is_orphan` | bool | `NodeIsOrphanSignal` |
| `graph.node.edge_count` | int | `NodeEdgeCountSignal` |
| `graph.node.has_outgoing` | bool | `NodeHasOutgoingSignal` |
| `technique.node.strategy_repetition` | categorical | `NodeStrategyRepetitionSignal` |

All inherit `NodeSignalDetector` (`src/signals/graph/node_base.py`); return `Dict[node_id, value]`.

### Meta Signals

**`meta.interview.phase`**: Proportional from `max_turns` — early (~10%, min 2 turns), mid (middle), late (last 2 turns). Computed per-turn from `context.turn_number` and `context.max_turns`.

**`meta.node.opportunity`**: Combines `graph.node.exhausted`, `graph.node.focus_streak`, `llm.response_depth` → exhausted / probe_deeper / fresh.

**`meta.conversation.saturation`**: `1.0 - min(current_delta / peak, 1.0)` — extraction yield vs peak.

**`meta.canonical.saturation`**: `1.0 - min(canonical_delta / surface_delta, 1.0)` — thematic novelty ratio.

### Joint Strategy-Node Scoring

Scores all `(strategy, node)` pairs in one pass:

```python
final_score = (base_score * phase_multiplier) + phase_bonus
```

- **base_score**: Weighted sum of matched signals (`score_strategy()` in `src/methodologies/scoring.py`)
- **phase_multiplier**: From `config.phases[phase].signal_weights[strategy]` (default 1.0)
- **phase_bonus**: From `config.phases[phase].phase_bonuses[strategy]` (default 0.0, additive)

Node-scoped signal weights (`graph.node.*`, `technique.node.*`, `meta.node.*`) are automatically partitioned from strategy weights and applied at the node scoring level.

Returns `ScoredCandidate` objects with full `signal_contributions` breakdown for observability.

---

## Concept-Driven Coverage

Concepts (YAML in `config/concepts/`) define the research topic. Structure:

```yaml
id: headphones_mec
name: "Wireless Headphones Means-End Chain"
methodology: means_end_chain
objective: "Explore how people evaluate wireless headphones..."
```

**How concepts drive interviews:**
1. **Opening question**: `objective` + methodology `opening_bias` → LLM prompt
2. **Extraction context**: concept provides methodology-appropriate extraction guidelines
3. **Question anchoring**: `context.concept_name` prevents questions drifting to abstract philosophy

Concepts are methodology-agnostic — the same topic can use different methodologies for comparison. Loaded via `src/core/concept_loader.py` with module-level caching.

---

## Methodology-Centric Design

### Methodology Registry

`MethodologyRegistry` (`src/methodologies/registry.py`) lazy-loads and validates YAML configs:

```python
registry.get_methodology("means_end_chain")  # loads + caches
registry.create_signal_detector(config)      # returns ComposedSignalDetector
```

Global access: `from src.methodologies import get_registry`.

### YAML Structure

```yaml
method:
  name: means_end_chain
  goal: "..."
  opening_bias: "..."

ontology:
  nodes: [{name, level, terminal, description, examples}]
  edges: [{name, description, permitted_connections}]

signals:
  graph: [graph.node_count, graph.max_depth, ...]
  llm: [llm.response_depth, llm.engagement]
  temporal: [temporal.strategy_repetition_count]
  meta: [meta.interview.phase]

strategies:
  - name: deepen
    description: "..."
    node_binding: required      # "required" (default) or "none"
    focus_mode: recent_node     # "recent_node" (default), "summary", "topic"
    generates_closing_question: false
    signal_weights:
      llm.response_depth.low: 0.8
      graph.node.exhaustion_score.low: 1.0
      temporal.strategy_repetition_count: -0.3

phases:
  early:
    signal_weights: {explore: 1.5, deepen: 0.5}
    phase_bonuses: {explore: 0.2}
  mid:
    signal_weights: {deepen: 1.3}
    phase_bonuses: {deepen: 0.3}
  late:
    signal_weights: {reflect: 1.2}
    phase_bonuses: {reflect: 0.2}
```

### Strategy Selection Flow

`MethodologyStrategyService.select_strategy_and_focus()`:

1. Load methodology config from registry
2. Detect global signals (`GlobalSignalDetectionService`)
3. Detect node-level signals (`NodeSignalDetectionService`)
4. Detect interview phase → get phase weights and bonuses
5. `rank_strategy_node_pairs()` → scored `(strategy, node_id)` pairs across all strategy × node combinations
6. Top-ranked pair becomes selected strategy + focus node

**Joint scoring formula:**
```python
final_score = (base_score * phase_multiplier) + phase_bonus
```

- **base_score**: Weighted sum of matched signals from strategy `signal_weights` in YAML
- **phase_multiplier**: From `config.phases[phase].signal_weights[strategy]` (default 1.0, multiplicative)
- **phase_bonus**: From `config.phases[phase].phase_bonuses[strategy]` (default 0.0, additive)
- Node-scoped signal weights (`graph.node.*`, `technique.node.*`, `meta.node.*`) partitioned automatically and applied at node scoring level
- Returns `ScoredCandidate` objects with full `signal_contributions` breakdown

### Registry Validation (at load time)

- Signal names must be known to `ComposedSignalDetector`
- No duplicate strategy names; valid `node_binding`/`focus_mode` values
- Phase `signal_weights`/`phase_bonuses` keys must reference defined strategy names

---

## Knowledge Graph State

### Session State

`SessionState` (Pydantic, persisted as JSON in DB):

```python
class SessionState(BaseModel):
    methodology: str
    concept_id: str
    concept_name: str
    turn_count: int = 0
    last_strategy: Optional[str] = None
    mode: InterviewMode = InterviewMode.EXPLORATORY

    # Velocity tracking (saturation signals)
    surface_velocity_peak: float = 0.0
    prev_surface_node_count: int = 0
    canonical_velocity_peak: float = 0.0
    prev_canonical_node_count: int = 0

    # Exploration trace
    focus_history: List[FocusEntry] = []
```

**FocusEntry**: `{turn, node_id, label, strategy}` — appended by Stage 10, loaded by Stage 1.

### GraphState Metrics

```python
class GraphState(BaseModel):
    node_count: int; edge_count: int
    nodes_by_type: Dict[str, int]; edges_by_type: Dict[str, int]
    orphan_count: int
    depth_metrics: DepthMetrics           # max_depth, avg_depth, longest_chain_path
    saturation_metrics: SaturationMetrics # consecutive_low_info, consecutive_shallow, ...
    current_phase: Literal["exploratory", "focused", "closing"]
    strategy_history: deque(maxlen=30)
    extended_properties: Dict[str, Any]
```

**SaturationMetrics**: `chao1_ratio`, `new_info_rate`, `consecutive_low_info`, `consecutive_shallow`, `consecutive_depth_plateau`, `prev_max_depth`, `is_saturated`.

### Node State Tracking

`NodeStateTracker` tracks per-node state in memory, persisted to `sessions.node_tracker_state` (JSON) each turn.

**NodeState** fields: `focus_count`, `last_focus_turn`, `current_focus_streak`, `turns_since_last_yield`, `yield_count`, `yield_rate`, `all_response_depths`, `connected_node_ids`, `edge_count_outgoing`, `edge_count_incoming`, `strategy_usage_count`.

**Exhaustion score**:
```python
exhaustion_score = (
    min(turns_since_last_yield, 10) / 10.0 * 0.4 +  # Yield stagnation
    min(current_focus_streak, 5) / 5.0 * 0.3 +       # Persistent focus
    shallow_response_ratio * 0.3                      # Response quality
)
# 0.0–0.3 = fresh; 0.3–0.6 = moderate; 0.6–1.0 = exhausted
```

**Dual-graph support**: When `canonical_slot_repo` is provided, surface node IDs resolve to canonical slot IDs — aggregating paraphrases into a single tracking unit.

**Persistence flow**: Stage 1 loads via `NodeStateTracker.from_dict()` → stages update in-memory → Stage 10 saves via `to_dict()`.

---

## Question Generation

### Opening vs Follow-Up

| | Opening | Follow-Up |
|--|---------|-----------|
| Goal | Invite initial thoughts | Execute selected strategy |
| Context | `objective` + methodology `opening_bias` | Strategy desc + graph state + conversation + topic anchoring |
| Temperature | 0.9 | 0.7–0.8 |

### Topic Anchoring

When `concept_name` is provided, the system prompt includes:
```
This interview is about **{topic}**. While exploring deeper motivations and values,
ensure questions remain connected to the respondent's experience with {topic}.
```

At depth ≥ 2, an additional user prompt reminder is added to prevent abstract drift.

### Strategy Descriptions

Strategy `description` fields from YAML are injected into prompts — making prompt behavior fully configurable without code changes.

---

## LLM Integration

### Four-Client Architecture

Configured in `config/interview_config.yaml` under `llm:`:

| Client Type | Stage | Default Model | Purpose |
|-------------|-------|---------------|---------|
| `extraction` | 3 | claude-sonnet-4-6 | Extract concepts/relationships |
| `slot_scoring` | 4.5 | claude-haiku-4-5 | Canonical slot discovery |
| `signal_scoring` | 6 | claude-haiku-4-5 | LLM signal detection (batched) |
| `question_generation` | 8 + opening | claude-haiku-4-5 | Generate questions |

Factory: `get_llm_client(client_type: LLMClientType)` reads provider/model/temperature/max_tokens/timeout/effort from config.

### Supported Providers

| Provider | API | Key Env Var |
|----------|-----|-------------|
| `anthropic` | Messages API | `ANTHROPIC_API_KEY` |
| `kimi` | OpenAI-compatible | `KIMI_API_KEY` |
| `deepseek` | OpenAI-compatible | `DEEPSEEK_API_KEY` |
| `grok` | OpenAI-compatible | `GROK_API_KEY` |

**Structured output**: Anthropic uses tool_use with JSON schema; OpenAI-compatible providers use `response_format={"type": "json_object"}`. Eliminates post-hoc JSON repair.

**`effort` parameter** (Anthropic only): `extraction` supports `effort` for output token budget control.

### Retry and Error Handling

- Max 1 retry (2 total attempts), exponential backoff (base 1.0s)
- Retryable: `TimeoutException`, `429` rate limit
- Non-retryable: Other 4xx/5xx → raised immediately
- Error types: `LLMTimeoutError`, `LLMRateLimitError` (`src/core/exceptions`)

### Token Usage Tracking

All calls record input/output tokens via `TokenUsageService.record_llm_call()`. Session ID passed via context variable `set_llm_session_id()`.

**Pricing (per million tokens)**:
- Claude Sonnet 4.6: $3.00 in / $15.00 out
- Claude Haiku 4.5: $0.80 in / $4.00 out
- DeepSeek Chat: $0.14 in / $0.28 out
- Kimi K2: $0.60 in / $2.50 out

---

## Container Deployment

### Architecture (Cloud Run)

Single container runs FastAPI (port 8000, internal) + Streamlit (port 8501, exposed). Single Uvicorn worker for SQLite safety.

**Database**: File-based SQLite at `/tmp/interview.db` (not `:memory:` — multiple aiosqlite connections would each get separate in-memory DBs).

**WebSocket settings**: Compression, CORS, and XSRF protection disabled — Cloud Run's load balancer can stall Streamlit's `st.rerun()` with compression enabled.

### Deployment

```bash
./scripts/deploy_cloud_run.sh [PROJECT_ID] [REGION]
# Service: https://interview-system-<HASH>.<REGION>.run.app
```

### Environment Variables

| Variable | Purpose | Secret? |
|----------|---------|---------|
| `DATABASE_PATH` | SQLite path (default: `/tmp/interview.db`) | No |
| `API_URL` | Backend URL (default: `http://localhost:8000`) | No |
| `ANTHROPIC_API_KEY` | Claude API | Yes |
| `KIMI_API_KEY` | Kimi API | Yes |
| `DEEPSEEK_API_KEY` | DeepSeek API | Yes |
| `GCS_BUCKET` | Export storage (optional) | Yes |

---

## References

- [Pipeline Contracts](./pipeline_contracts.md) — Stage read/write specifications
- [Data Flow Paths](./data_flow_paths.md) — Critical data flow visualizations (19 diagrams)
- [Signals & Strategies](./signals_and_strategies.md) — Signal pool configuration
- [Extraction & Graphs](./extraction_and_graphs.md) — Extraction and graph configuration
- [NodeStateTracker Mutation](./NodeStateTracker_mutation.md) — Per-turn lifecycle
