# Signal Naming Convention (Proposed)

Design document for a revised signal naming convention across all signal pools.
Developed 2026-04-21. Intended as the reference for a future refactoring pass.

---

## Design Principles

### 1. Source is always first

The top-level namespace identifies *what is being observed*, not where the signal lives in code
or how it is computed. Six top-level sources:

| Namespace | Subject |
|-----------|---------|
| `convgraph` | Surface/conversation knowledge graph (nodes, edges, topology) |
| `canongraph` | Canonical (deduplicated) graph |
| `response` | Current utterance — single-turn LLM assessment |
| `interview` | Interview process flow — moderator action history, strategy choices |
| `session` | Mechanical session metadata — phase, duration, date |
| `meta` | Cross-source composites — signals that draw from multiple pools |

**`session` is not a catch-all for time-series data.** It is reserved for administrative
session facts. Strategy history, focus counts, and similar accumulators live under their
*subject's* namespace (`convgraph.node.*`, `interview.*`), not `session.*`.

### 2. Scope narrows after source

Within a source, the path narrows from broad to specific:

```
convgraph.state.*          — global graph metrics
convgraph.chain.*          — whole-chain topology
convgraph.node.*           — per-node signals
convgraph.node.chain.*     — chain-position signals for a node
convgraph.node.llm.*       — LLM-derived content signals for a node
convgraph.node.focus.*     — node focus/engagement history
```

### 3. `.llm` is a mechanism qualifier, not a source

`llm` appears *inside* a path (after the source and scope) when the signal was derived via
LLM inference. It is not a top-level source.

- `convgraph.node.llm.elaboration` — LLM-derived elaboration rating, written back to a graph node
- `response.semantic.llm.engagement` — current-turn LLM assessment of a response (see §3a)

### 3a. `response.*` splits by analytical layer before mechanism

Within `response.*`, signals separate by *what they describe about the utterance* before
separating by *how they were computed*:

```
response.lexical.*                   — surface/token-level mechanical facts
response.lexical.word_count          — no interpretation of meaning
response.lexical.length

response.semantic.llm.*              — meaning-layer signals, split by mechanism
response.semantic.llm.engagement
response.semantic.llm.certainty
response.semantic.srl.agent_count    — SRL-derived (non-LLM)
response.semantic.sentiment.polarity — classical NLP library, when added
```

`lexical` vs `semantic` are the standard NLP terms: lexical concerns words as surface forms,
semantic concerns meaning. The `semantic.<mechanism>.*` layer gives `.llm` genuine siblings
(`srl`, `sentiment`, potential future `embedding`) so it satisfies principle 5 — mechanism
qualifiers only appear where the pool actually contains multiple mechanisms.

### 4. `.chain` marks level-hierarchy dependence

The `.chain` infix appears when a signal's meaning depends on the *level hierarchy* of the
MEC chain (or equivalent). A signal that only asks "does this node have outgoing edges?"
is plain graph connectivity — no `.chain`. A signal that asks "is there a gap in the chain
*above* this node?" requires knowing what "above" means — `.chain`.

```
convgraph.node.has_outgoing          — graph connectivity, no level concept
convgraph.node.chain.gap.above       — requires chain level hierarchy
convgraph.node.chain.fan_in          — converging paths from "below" — level concept
```

### 5. `.` encodes real hierarchy; `_` encodes word boundaries

Only replace `_` with `.` when the left part is a genuine sub-namespace with multiple
siblings. Using `.` as a word separator creates false hierarchy.

```yaml
# Good — real sub-namespace with siblings:
convgraph.node.focus.count          # focus.count and focus.streak are siblings
convgraph.node.chain.gap.above      # gap.above and gap.below are siblings
convgraph.node.chain.level.skip     # level.skip and level.gap_size are siblings

# Bad — single compound concept, no siblings:
has.outgoing      # implies has.incoming exists — it doesn't
turns.since.change  # false 3-level hierarchy
yield.stagnation    # no yield.* siblings
```

### 6. Temporal qualifiers: aggregate suffixes

When a signal is a session-level or windowed aggregate of a per-turn measurement, the
subject namespace stays the same and an aggregate suffix is appended:

```
response.semantic.llm.engagement          — per-turn snapshot
response.semantic.llm.engagement.trend    — session aggregate of that signal
```

### 6a. Reserved aggregate suffixes

A small, fixed vocabulary of aggregate operators can be appended to any base signal. They
form a global sibling set — their "siblings" are each other across the namespace, not
within a local path. This is an explicit exception to principle 5, carved out because
enumerating every aggregate as a local sub-namespace would be noisy and redundant.

Initial reserved set (add cautiously):

| Suffix | Meaning |
|--------|---------|
| `.trend` | Directional aggregate over a window or the full session (rising/falling/flat) |
| `.peak` | Maximum value observed so far |
| `.delta` | Change since previous turn (or since window start) |
| `.variance` | Spread/stability of the signal over a window |
| `.mean` | Average value over a window |

A `session.` prefix is **not** used for aggregates — it would be redundant since the
suffix already implies accumulation. New aggregate suffixes require doc update before use.

### 7. `meta` for genuine cross-source composites only

A signal that draws from a single source belongs to that source's namespace even if it
involves computation. `meta.*` is reserved for signals that meaningfully combine inputs
from two or more distinct pools (e.g. graph state + session history).

### 8. `interview.focus.*` for (node, strategy) pair signals

The system selects a `(strategy, focus_node)` pair each turn. Signals about the repetition
or streak of that *joint* selection belong to `interview.focus.*` — not `convgraph.node.*`
(node is only half the subject) and not `interview.strategy.*` (strategy is only half).

- `interview.focus.streak` — consecutive turns with the same (node, strategy) pair
- `interview.focus.count` — total times a (node, strategy) pair has been selected (new)

---

## Full Signal Inventory

### Conversation graph — global state

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `convgraph.state.node.count` | `graph.node_count` | `graph/graph_signals.py` | `node.*` sub-namespace buys room for future `node.saturation` etc. |
| `convgraph.state.node.orphan_count` | `graph.orphan_count` | `graph/graph_signals.py` | Moved under `node.*` — it's a node-class metric |
| `convgraph.state.edge.count` | `graph.edge_count` | `graph/graph_signals.py` | `edge.*` sub-namespace buys room for future siblings |
| `convgraph.state.max_depth` | `graph.max_depth` | `graph/graph_signals.py` | No natural siblings — stays flat |

### Conversation graph — chain (global)

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `convgraph.chain.completion` | `graph.chain_completion` | `graph/graph_signals.py` | |
| `convgraph.chain.structure` | `graph.global.chain_topology` | `graph/global_chain_signals.py` | Renamed from `.topology` — clashed with `convgraph.node.chain.role` |
| `convgraph.chain.has_attribute_foundation` | `graph.node.chain.has_attribute_foundation` | `graph/chain_topology_signals.py` | Promoted to global — it's a whole-chain fact, not per-node |
| `convgraph.chain.has_terminal_apex` | `graph.node.chain.has_terminal_apex` | `graph/chain_topology_signals.py` | Promoted to global |

### Conversation graph — node engagement

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `convgraph.node.focus.count` | `graph.node.focus_count` | `graph/node_signals.py` | Grouped under `focus.*` — count and streak are siblings |
| `convgraph.node.focus.streak` | `graph.node.focus_streak` | `graph/node_signals.py` | |
| `convgraph.node.exhaustion` | `graph.node.exhaustion_score` | `graph/node_signals.py` | Dropped `_score` — redundant in a signal system |
| `convgraph.node.exhausted` | `graph.node.exhausted` | `graph/node_base.py` + `graph/node_signals.py` | ⚠️ Declared in two files — deduplicate |
| `convgraph.node.novelty` | `graph.node.novelty` | `graph/node_signals.py` | |
| `convgraph.node.recency` | `graph.node.recency_score` | `graph/node_signals.py` | Dropped `_score` |
| `convgraph.node.yield_stagnation` | `graph.node.yield_stagnation` | `graph/node_signals.py` | No siblings — `_` stays |
| `convgraph.node.is_current_focus` | `graph.node.is_current_focus` | `graph/node_signals.py` | |

### Conversation graph — node connectivity

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `convgraph.node.edge_count` | `graph.node.edge_count` | `graph/node_signals.py` | Generic connectivity — no `.chain` |
| `convgraph.node.has_outgoing` | `graph.node.has_outgoing` | `graph/node_signals.py` | Generic connectivity — no `.chain` |
| `convgraph.node.is_orphan` | `graph.node.is_orphan` | `graph/node_signals.py` | Generic connectivity (applies to CJM/RG too) — no `.chain` |

### Conversation graph — node chain position

These signals require the level hierarchy to have meaning — `.chain` is earned.

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `convgraph.node.chain.gap.above` | `graph.node.gap_above` | `graph/chain_topology_signals.py` | `gap.*` sub-namespace: above + below are siblings |
| `convgraph.node.chain.gap.below` | `graph.node.gap_below` | `graph/chain_topology_signals.py` | |
| `convgraph.node.chain.level.skip` | `graph.node.level_skip` | `graph/chain_topology_signals.py` | `level.*` sub-namespace: skip + gap_size are siblings |
| `convgraph.node.chain.level.gap_size` | `graph.node.level_gap_size` | `graph/chain_topology_signals.py` | `gap_size` keeps `_` — no sub-siblings within `level.gap_*` |
| `convgraph.node.chain.branching_deficit` | `graph.node.branching_deficit` | `graph/chain_topology_signals.py` | No siblings — `_` stays |
| `convgraph.node.chain.fan_in` | `graph.node.fan_in` | `graph/chain_topology_signals.py` | Requires "below" level concept — `.chain` earned |
| `convgraph.node.chain.role` | `graph.node.chain_topology` | `graph/chain_topology_signals.py` | Renamed: describes the node's *role* in the chain (leaf, root, etc.) |

### Conversation graph — node LLM-derived

Signals derived via LLM per-concept ratings, written back to the node.

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `convgraph.node.llm.elaboration` | `graph.node.elaboration` | `graph/node_signals.py` | `.llm` marks mechanism: derived via per-concept LLM rating |
| `convgraph.node.llm.charge` | `graph.node.charge` | `graph/node_signals.py` | |
| `convgraph.node.llm.has_quality_data` | `graph.node.has_quality_data` | `graph/node_signals.py` | |

### Canonical graph

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `canongraph.state.node.count` | `graph.canonical_concept_count` | `graph/graph_signals.py` | `node.*` sub-namespace for future siblings |
| `canongraph.state.edge.density` | `graph.canonical_edge_density` | `graph/graph_signals.py` | `edge.*` sub-namespace for future siblings |
| `canongraph.state.exhaustion` | `graph.canonical_exhaustion_score` | `graph/graph_signals.py` | Dropped `_score` |
| `canongraph.node.novelty` | `graph.node.canonical_novelty` | `graph/node_signals.py` | |

### Response (current utterance, per-turn LLM assessment)

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `response.semantic.llm.certainty` | `llm.certainty` | `llm/signals/certainty.py` | |
| `response.semantic.llm.engagement` | `llm.engagement` | `llm/signals/engagement.py` | |
| `response.semantic.llm.elaboration` | `llm.elaboration` | `llm/signals/elaboration.py` | |
| `response.semantic.llm.charge` | `llm.charge` | `llm/signals/charge.py` | |
| `response.semantic.llm.engagement.trend` | `llm.global_response_trend` | `session/llm_response_trend.py` | Aggregate suffix: session-level trend of a per-turn semantic signal; `session.` prefix dropped as redundant |

Future candidates (not yet implemented):

| Proposed name | Notes |
|---------------|-------|
| `response.lexical.word_count` | Mechanical token count — no interpretation |
| `response.lexical.length` | Char or sentence count |
| `response.semantic.srl.agent_count` | SRL-derived, if/when surfaced as a signal |
| `response.semantic.llm.engagement.peak` | Max engagement observed so far |
| `response.semantic.llm.engagement.delta` | Change since previous turn |

### Interview (moderator process flow)

Strategy signals whose *subject* is the interview process, not the knowledge graph.

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `interview.strategy.self_count` | `temporal.strategy_repetition_count` | `session/strategy_history.py` | Per-strategy dict `{name: count}`, resolves per-candidate during scoring. Named `self_count` (not `count`) to signal candidate-scoped resolution and avoid confusion with `interview.strategy.diversity` (a true scalar). See CLAUDE.md "Known Failure Modes". |
| `interview.strategy.streak` | *(new)* | — | Consecutive turns with same strategy (global, not per-node) |
| `interview.strategy.turns_since_change` | `temporal.turns_since_strategy_change` | `session/strategy_history.py` | |
| `interview.strategy.diversity` | *(new)* | — | Scalar: distinct strategies used so far |
| `interview.focus.streak` | `technique.node.strategy_repetition` | `session/node_strategy_repetition.py` | Tracks `consecutive_same_strategy` on a node — this IS a streak, not a count. Subject is (node, strategy) pair — belongs to `interview.focus.*` not `convgraph.node.*` |
| `interview.focus.count` | *(new)* | — | Total times a (node, strategy) pair selected — complement to streak |
| `interview.phase` | `meta.interview.phase` | `meta/interview_phase.py` | Moved from `session.*`: phase governs interview flow (strategy gating), not administrative session metadata |

### Session (mechanical metadata)

Reserved for administrative session facts only (facts about the session as an event).
Derived analytics that govern interview flow live under `interview.*`.

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| *(none currently)* | — | — | `session.duration`, `session.started_at`, etc. are future candidates if surfaced as signals |

### Meta (genuine cross-source composites)

| New name | Old name | Source file | Notes |
|----------|----------|-------------|-------|
| `meta.saturation.conversation` | `meta.conversation.saturation` | `meta/conversation_saturation.py` | Combines convgraph state + session history |
| `meta.saturation.canonical` | `meta.canonical.saturation` | `meta/canonical_saturation.py` | Combines canongraph state + session history |
| `meta.node.opportunity` | `meta.node.opportunity` | `meta/node_opportunity.py` | Combines convgraph.node.* + interview.* signals. **Audit usage before refactor — remove if not load-bearing.** |

---

## Refactoring Checklist

When implementing this rename:

1. **Signal class `signal_name` attributes** — string constant in each signal file
2. **YAML methodology configs** — `signals:` sections and `signal_weights:` keys in every strategy
3. **`strategy-scoring.md` and other context docs** — signal names appear in examples and tables
4. **`STRATEGY_SCOPED_SIGNALS` constant** — list of per-strategy-resolved signal names; `interview.strategy.self_count` replaces `temporal.strategy_repetition_count`
5. **`ComposedSignalDetector._is_llm_signal()`** — currently checks `llm.` prefix to route to batch detector; update to match `response.semantic.llm.*` and `convgraph.node.llm.*`
6. **Signal-name registry + strict loader validation** — build a registry by collecting `signal_name` from every `SignalBase` subclass; validate that every YAML `signals:` and `signal_weights:` key exists in the registry at methodology load time. Without this, a stale/typo'd signal name in YAML silently drops to zero weight and causes invisible behavioral drift. Rename is the right moment to introduce this — otherwise the refactor itself could ship broken weights undetected.
7. **Audit `meta.node.opportunity`** — confirm it is actually consumed by any strategy; drop it during the rename if unused rather than cementing dead weight.
8. **`NodeStateTracker`** — any hardcoded signal name references
9. **Tests** — assert on signal name strings
10. **`CLAUDE.md` Known Failure Modes section** — references old names in examples
11. **`graph.node.exhausted` duplication** — declared in both `node_base.py` and `node_signals.py`; resolve before renaming

> Consider implementing as a single atomic commit with a mechanical find-replace pass,
> then verifying with `uv run pytest` and a simulation run.
