# Edge Extraction — Proposed Spec

## Problem Statement

The current `ExtractionStage` (Stage 3) bundles four cognitively distinct tasks into a single LLM call: node identification, node typing, edge identification, and edge typing. Observations from simulated interview output suggest that edge quality is the weakest layer — specifically:

- **Cross-turn edge over-inference**: edges connecting nodes from different turns are frequently supported by thematic association rather than evidenced causal relationships
- **Question-frame contamination**: when the probing question supplies the causal frame, the respondent's confirmation is extracted as an edge the respondent never actually asserted
- **Circular evidence reuse**: the same transcript span is used to justify both a node and an outgoing edge from that node
- **Hub inflation**: high-salience emotional job nodes accumulate cross-turn edges from many turns without per-edge evidentiary support

The proposed change separates edge identification and typing into a dedicated parallel call, operating on already-resolved nodes with structured input and enforced chain-of-thought output.

---

## Proposed Architecture

### Position in Pipeline

Edge extraction runs as a new parallel stream alongside `SlotDiscoveryStage` (4.5) and LLM signal detection, merging at the existing 4.7 merge point. It depends on `ExtractionOutput` (Stage 3 nodes only — relationships field ignored) and `GraphUpdateOutput` (Stage 4 — post-dedup node IDs).

```
Stage 3: ExtractionStage
  → nodes only (relationships field deprecated for cross-turn edges)

Stage 4: GraphUpdateStage
  → dedup resolution, node IDs assigned

Stage 4.5 [parallel stream A]: SlotDiscoveryStage (existing)
Stage 4.5 [parallel stream B]: EdgeExtractionStage (new)
Stage 4.5 [parallel stream C]: LLM signal detection (existing)

Stage 4.7: Merge (existing — extended to consume EdgeExtractionOutput)
```

### Relationship to Current Stage 3

Stage 3 currently extracts both concepts and relationships. After this change:

- Stage 3 continues to extract **within-turn edges** (relationships between nodes extracted in the same turn from the same utterance). These are low-risk and don't require the additional context.
- Stage 4.5B (EdgeExtractionStage) handles **cross-turn edges** — relationships between the current turn's new nodes and prior-turn nodes in the graph. This is where the failure modes concentrate.

This is an incremental change: Stage 3's relationship extraction is not removed, but its scope is narrowed and its output for cross-turn edges is superseded by Stage 4.5B.

---

## Input Design

### Utterance Formatting

Utterances are passed as clean text with node spans annotated via character offsets in a separate node list — not as inline tags, which break on overlapping spans.

```
utterance_id: utt_007
text: "With regular soda I'd feel kind of wired and then tired an hour later, but ZeroFizz doesn't do that to me."

nodes_in_utterance:
  - id: n_019
    type: pain_point
    span: [0, 69]
    label: "wired-then-tired feeling an hour after regular soda"
  - id: n_020
    type: solution_approach
    span: [71, 104]
    label: "choosing ZeroFizz over regular soda"
```

### Utterance Selection

Utterances are selected by graph derivation, not recency. The relevant set is:

1. **Current utterance** — always included
2. **Previous interviewer question** — always included (frame contamination risk surface)
3. **Originating utterances of focus node and its direct neighbours** — pulled from `source_utterance_id` on each node; included regardless of turn distance

This ensures relevance when strategy jumps to a different graph branch. A turn-9 focus on a node introduced in turn-2 pulls turn-2's utterance, not turns 7 and 8.

The utterance set is bounded and deterministic: given a candidate node list, the input is always reconstructible.

### Candidate Node List

Passed as a structured list with focus signalling:

```
[FOCUS]    n_008: choosing ZeroFizz over regular soda (solution_approach, t=7)
[NEIGHBOR] n_006: avoid putting unnecessary substances into my body (emotional_job, t=6)
[NEIGHBOR] n_012: wired-then-tired feeling (pain_point, t=7)
[CURRENT]  n_019: wired-then-tired feeling an hour after regular soda (pain_point, t=9)
[CURRENT]  n_020: choosing ZeroFizz over regular soda (solution_approach, t=9)
[RECENT]   n_015: feeling like garbage after sugary drinks (pain_point, t=9)
```

Tags:
- `[FOCUS]` — the node selected by StrategySelectionStage as the current turn's focus
- `[NEIGHBOR]` — direct graph neighbours of the focus node
- `[CURRENT]` — nodes extracted this turn (from Stage 3)
- `[RECENT]` — nodes from the previous turn not already tagged above

### Methodology Edge Schema

Passed as the permitted edge types with directionality constraints and type-pair validity. Structured identically to the extraction prompt's edge schema — universal edges always present, methodology-specific edges conditionally included. Example:

```
permitted_edges:
  - type: triggers
    direction: upward
    valid_source_types: [job_trigger, pain_point]
    valid_target_types: [job_statement, solution_approach]
    description: "A trigger initiates or activates a job or response"

  - type: implies
    direction: upward
    valid_source_types: [pain_point, gain_point]
    valid_target_types: [job_statement, emotional_job]
    description: "A node logically entails or strongly suggests another"

  - type: supports
    direction: upward_or_lateral
    valid_source_types: [any]
    valid_target_types: [any]
    description: "A node reinforces or corroborates another"
```

### Prompt Structure

Three-part structure matching the existing extraction prompt pattern:

1. **Universal instructions** — task definition, chain-of-thought requirement, output format
2. **Methodology-specific instructions** — edge types in scope, any methodology-level heuristics (e.g. JTBD: distinguish job-chain edges from forces-field edges)
3. **Turn-specific input** — formatted utterances, candidate node list, existing edges on focus node (to avoid duplication)

---

## Output Design — Enforced Chain of Thought

The model is required to produce a structured intermediate reasoning artifact before edge verdicts. This is enforced by schema — reasoning is a required output field, not optional prose.

```xml
<edge_analysis>
  <candidate pair="n_006,n_019">
    <evidence>
      "With regular soda I'd feel kind of wired and then tired an hour later"
    </evidence>
    <reasoning>
      The respondent describes a physical consequence of regular soda consumption (n_019).
      The interviewer's prior question framed avoiding such consequences as the reason for choosing ZeroFizz.
      The respondent did not explicitly connect this experience to the body-purity belief (n_006) —
      that connection was implied by the question frame, not stated.
      The edge is associative, not evidenced.
      Frame contamination: YES.
    </reasoning>
    <verdict>rejected</verdict>
    <rejection_reason>question_frame_contamination</rejection_reason>
  </candidate>

  <candidate pair="n_019,n_020">
    <evidence>
      "With regular soda I'd feel kind of wired and then tired an hour later,
       but ZeroFizz doesn't do that to me."
    </evidence>
    <reasoning>
      The respondent directly contrasts regular soda's physical consequence (n_019)
      with ZeroFizz's absence of that consequence, making n_020 the explicit solution.
      Directionality is clear: the pain drives the solution choice.
      Frame contamination: NO — the interviewer asked about body sensation, not this contrast.
      Relationship type: implies (pain_point → solution_approach).
    </reasoning>
    <verdict>confirmed</verdict>
    <edge_type>implies</edge_type>
    <source>n_019</source>
    <target>n_020</target>
    <confidence>high</confidence>
    <supporting_span>[0, 104]</supporting_span>
    <utterance_id>utt_007</utterance_id>
  </candidate>
</edge_analysis>
```

### Confidence Calibration

`confidence` is a required field on confirmed edges:
- `high` — relationship explicitly stated by respondent; direction unambiguous; no frame contamination
- `medium` — relationship implied or inferred; direction clear; minor frame influence possible
- `low` — relationship inferred across turns; direction uncertain; or frame contamination detected but edge retained

`low` confidence edges are flagged in `EdgeExtractionOutput` for downstream audit handling. The pipeline should not reject them automatically — they are valid candidates for analyst review.

### Rejection Reasons (Taxonomy)

Standardised rejection reason codes for auditability:

| Code | Meaning |
|------|---------|
| `question_frame_contamination` | Causal frame supplied by interviewer, not respondent |
| `circular_evidence` | Supporting span already used to justify source node |
| `associative_only` | Thematic connection without evidenced directionality |
| `type_constraint_violation` | Edge type not permitted for this source/target type pair |
| `no_evidence_found` | No transcript span supports the relationship |

---

## Model Selection

**Sonnet** for the full call (identification + typing in a single pass). The reasoning requirements — frame contamination detection, directionality assessment, evidence isolation — exceed Haiku's reliable capability. The structured XML output with mandatory reasoning fields is designed to make the task tractable for Sonnet without requiring a separate thinking model.

A two-call Haiku split (identification → typing) is theoretically possible but introduces sequential latency and risks the typing call losing the reasoning context that justified the identification verdict. Not recommended unless benchmarking shows Sonnet latency is unacceptable.

---

## New Pipeline Contract

`EdgeExtractionOutput` — new Pydantic contract for Stage 4.5B:

```python
class ConfirmedEdge(BaseModel):
    source_node_id: str
    target_node_id: str
    edge_type: str
    confidence: Literal["high", "medium", "low"]
    supporting_span: tuple[int, int]
    utterance_id: str
    reasoning_summary: str  # condensed from XML reasoning block

class RejectedEdgeCandidate(BaseModel):
    source_node_id: str
    target_node_id: str
    rejection_reason: str
    reasoning_summary: str

class EdgeExtractionOutput(BaseModel):
    confirmed_edges: list[ConfirmedEdge]
    rejected_candidates: list[RejectedEdgeCandidate]
    low_confidence_count: int
    timestamp: datetime
    latency_ms: int
```

Rejected candidates are retained in the output for audit logging — they should not be silently discarded.

---

## Integration — Key Points for Codebase Investigation

The following integration points are not fully specified here and require inspection of the current codebase before implementation.

### 1. Stage 3 Relationship Scope Narrowing

Currently `ExtractionStage` extracts both concepts and relationships in a single LLM call. The `ExtractionResult.relationships` field is consumed by `GraphUpdateStage` (Stage 4).

**To investigate:**
- How to gate within-turn vs cross-turn relationship extraction cleanly — ideally Stage 3 continues producing within-turn edges (same-utterance node pairs) and Stage 4.5B handles cross-turn only, but the boundary needs to be defined precisely
- Whether `ExtractionResult` needs a new field to distinguish within-turn from cross-turn relationships, or whether this is handled by node ID lookup at merge
- The known gap `bead ui0f` (cross-turn edges bypassing `permitted_connections` validation in ExtractionService) — Stage 4.5B's type-constraint validation supersedes this for cross-turn edges, so ui0f may be closeable after this change

### 2. GraphUpdateStage — Edge Ingestion Path

Currently `GraphUpdateStage` consumes `ExtractionOutput.relationships` and writes edges to the DB via `GraphRepository`. After this change, confirmed cross-turn edges from `EdgeExtractionOutput` also need to be written to the DB.

**To investigate:**
- Whether GraphUpdateStage should be extended to consume `EdgeExtractionOutput` at the merge point, or whether a new `EdgePersistenceStage` is cleaner
- `_add_edge_from_relationship()` in `graph_service.py` — whether it can accept `ConfirmedEdge` directly or needs an adapter
- Post-dedup validation in GraphUpdateStage currently uses resolved node types — confirm this still applies to edges arriving from Stage 4.5B (it should, since Stage 4 runs before 4.5B)
- `record_yield()` on `NodeStateTracker` — whether edges from Stage 4.5B should credit the focus node in the same way as Stage 4 edges

### 3. Merge Point at Stage 4.7

The existing 4.7 merge waits on SlotDiscovery and LLM signals before proceeding to Stage 5. Adding EdgeExtractionOutput to the merge means Stage 5 (StateComputation) cannot proceed until edge extraction completes.

**To investigate:**
- Current merge implementation in `session_service.py:_build_pipeline()` — confirm it supports adding a third parallel stream and that the merge wait logic extends cleanly
- Whether confirmed edges need to be written to DB before Stage 5 runs (yes — StateComputation reads graph metrics from DB, so edge counts must be current)
- Latency impact: edge extraction is a Sonnet call and may be the slowest of the three parallel streams — measure against the 800ms budget

### 4. Utterance Retrieval for Input Construction

The input design requires pulling originating utterances for the focus node and its neighbours by `source_utterance_id`. This requires a DB read at Stage 4.5B construction time.

**To investigate:**
- Whether `source_utterance_id` is reliably populated on all graph nodes (extraction.md notes `"unknown"` as fallback — these nodes cannot participate in utterance-grounded edge extraction)
- Whether utterance text is retrievable from DB by ID at this point in the pipeline, or whether it needs to be carried forward in `PipelineContext` from Stage 2
- Whether `recent_utterances` already on `ContextLoadingOutput` (Stage 1) covers the needed window, or whether historical utterance retrieval is required for focus nodes introduced many turns ago

### 5. NodeStateTracker — Edge Count Updates

`GraphUpdateStage` calls `update_edge_counts()` on `NodeStateTracker` after writing edges to DB. Cross-turn edges confirmed by Stage 4.5B also affect edge counts on prior-turn nodes.

**To investigate:**
- Whether `update_edge_counts()` needs to be called again after Stage 4.7 merge, or whether a single call covering all edges (Stage 4 within-turn + Stage 4.5B cross-turn) is cleaner
- Ordering constraint: `NodeStateTracker` must be updated before signal detection reads it in Stage 6/8 — confirm the merge-then-update sequence preserves this

### 6. Audit Logging

Rejected edge candidates and low-confidence edges should be persisted for offline analysis, not just logged.

**To investigate:**
- Whether a new DB table for `rejected_edge_candidates` is warranted, or whether structlog output is sufficient for current development stage
- How to surface `low_confidence_count` in the API response / `TurnResult` — determine whether this belongs in `TurnResult` or is internal telemetry only

---

## Open Questions

1. **Should within-turn edges from Stage 3 bypass Stage 4.5B entirely?** The failure modes are concentrated in cross-turn edges, but within-turn edges share the same circular-evidence risk when a single utterance produces multiple nodes. Probably safe to exclude from Stage 4.5B initially and revisit if within-turn edge quality proves problematic.

2. **What is the candidate pair generation strategy?** Passing all possible pairs of `[CURRENT]` × `[FOCUS, NEIGHBOR, RECENT]` nodes could produce a large candidate list in later turns. A pre-filter based on `permitted_connections` type pairs would reduce this — pairs where no valid edge type exists can be excluded before the LLM call.

3. **Does the audit logging of `RejectedEdgeCandidate` create a training signal?** Rejected edges with `rejection_reason` codes are structured supervision signal for future fine-tuning of the extraction model. Worth preserving the schema even if the training pipeline doesn't exist yet.
