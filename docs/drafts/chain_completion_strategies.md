# Chain Completion Strategies — Brainstorm Notes

**Status:** Draft / ideation. Not a plan, not a spec. Captures thinking from a design conversation on 2026-04-24 before deciding how to implement.

**Goal:** Increase the share of interviews that end with *complete* chains (MEC) or *fully-covered* structures (flat methods) by biasing late-phase strategy selection toward closing structural gaps.

---

## 1. Original idea

Add a new strategy that activates in the last 3–4 turns of an interview, whose purpose is to focus on chains that are missing 1 level to be complete, so the chances of having a complete chain are higher at interview end.

## 2. First reframe — does a dedicated new strategy actually help?

The system already has `bridge`, which is declared in MEC (`means_end_chain_v2_strict` / `_flex`) and CIT (`critical_incident_v2`). `bridge` is one of the six chain-aware MEC strategies alongside `ascend`, `ground`, `branch`, `anchor`, `revitalize`.

Two implementation options surfaced:

- **Option A — new `close_chain` strategy.** More legible in logs, but introduces a third strategy chasing the same nodes as `ascend` / `bridge`, with calibration work across repetition brakes.
- **Option B — late-phase booster on existing `bridge` / `ascend` / `ground`.** Simpler, re-uses already-calibrated strategies, lower surface area. Tradeoff: mixes concerns (phase logic + structural logic).

Leaning toward B but not decided.

## 3. How `bridge` currently knows a chain has a gap

Traced in `src/signals/graph/chain_topology_signals.py` (`ChainTopologySignalDetector._compute_level_skip`, line 230).

- Each node has a **type** (`attribute`, `functional_consequence`, `instrumental_value`, `terminal_value` for MEC), and the methodology YAML declares an **ontology level** per type.
- The detector walks each node's outgoing edges and asks: is there an edge from level L to level L+2 or higher?
- If yes → `convgraph.node.chain.level.skip = True` for that node.
- Runs per-node every turn in Stage 5 (state computation). Stage 6 scoring reads the boolean as `bridge`'s `valid_when` gate.

The "knowledge" is **purely structural / graph-topological** — not a semantic judgement from the LLM. It's the graph literally containing an edge `attribute → instrumental_value` with no `functional_consequence` in between.

### Consequences of the current design

1. **`bridge` only fires if the skip-edge already exists.** If the conversation reached `attribute` but never extracted anything higher, there's no edge, no skip, and `bridge` can't help — `ascend` is needed instead. A true "close the chain" late-phase policy must cover *both* bridge (middle gaps) and ascend / ground (missing endpoints).
2. **The signal is binary per node.** A node with one skip-edge looks identical to one with three. No notion of "how close to complete" — so late-phase prioritisation by *distance to completion* isn't possible with the current signal alone.

## 4. "Closing the narrative" in flat methodologies

Flat methods (CJM, RG, and partially JTBD) explicitly declare **high incompleteness tolerance** in their YAML headers — so "closing" has to be redefined per methodology, not copied from MEC.

The unifying abstraction:

> Each methodology declares an **expected shape**.
> "Closing the narrative" = *what's missing from the expected shape that we could still plausibly elicit?*

Expected shapes per method:

| Method | Expected shape | Completeness computation |
|--------|----------------|--------------------------|
| MEC / CIT | 4-level chain | All ontology levels populated, no skip edges |
| CJM | Stage set (journey template) | `present_stages / expected_stages`; touchpoints per stage |
| RG | Element × construct matrix | Cells with ratings on both poles |
| JTBD | Job trinity (job + struggling moment + desired progress) | All three legs present |

Late-phase amplifier would point each methodology at its own existing gap-targeting strategy:

- MEC → amplify `bridge` / `ascend` / `ground`
- CJM → amplify `advance_stage` / `deepen_stage` toward uncovered stages
- RG → amplify `explore_ideal` / `triadic_elicit` toward half-populated constructs
- JTBD → amplify `ground` / `probe_pain` toward missing trinity legs

One shared mechanism (late-phase multiplier on gap-targeting strategies), methodology-specific gap definitions. Keeps the mechanism/domain separation principle (CLAUDE.md).

Much of the machinery already exists: canonical slots (Stage 4.5) are precisely the "expected template" for CJM / RG, and `support_count` per slot measures fill level.

## 5. Deeper redesign — gap as explicit state

Current `level.skip` is **stateless and reactive**: only fires when a skip-edge already exists in the graph. Blind to the case where two nodes are both present but have no edge at all.

### Proposed: `ChainGapTracker` (sibling of `NodeStateTracker`)

Maintain a registry of **expected-but-missing pairs**:

```python
chain_gaps: dict[tuple[NodeId, NodeId], GapRecord]

class GapRecord(BaseModel):
    gap_type: Literal["missing_intermediate", "missing_endpoint_above", "missing_endpoint_below"]
    expected_type: str            # "functional_consequence", "terminal_value", ...
    level_distance: int           # how many rungs need to fill
    first_observed_turn: int
    attempts: int                 # how many times a strategy targeted this gap
    priority: float               # derived from level_distance, staleness, node importance
```

### When to populate

End of Stage 4 (GraphUpdate) or Stage 4.5 (SlotDiscovery). Walk the current nodeset and record pairs where:

- Both nodes exist (canonical or surface)
- Ontology levels ≥ 2 apart
- No path between them (or only via a skip-edge)
- Conversation has semantically linked them (co-reference in a turn, or canonical slot co-occurrence)

### When to consume

Stage 6 scoring reads the registry directly. Candidate signals:

- `convgraph.chain.gap.has_open_gaps` (bool, global) — activates late-phase strategies
- `convgraph.chain.gap.priority` (per-node, float) — joint scoring picks *which* gap to target
- `convgraph.chain.gap.distance_one` (per-node, bool) — highest-priority gate for late phase

### Why this is better than current

1. **Detects gaps with no edge at all.** Current detector requires the edge to inspect.
2. **Ranks by urgency.** A gap observed 4 turns ago with no progress is more "closable late-phase" than one that just appeared. Current signal is binary.
3. **Records attempts.** If `bridge` targeted a gap twice and failed to elicit the intermediate, a repetition brake can redirect. Current system has no memory of *which* gaps were attempted.
4. **Natural late-phase hook.** `priority *= phase_multiplier` with an extra boost for `level_distance == 1` directly implements the original late-phase-close idea.

### Costs and risks

- **Combinatorial blowup.** N nodes → O(N²) potential pairs. Must bound: active nodes only, recently-focused only, same canonical cluster only, etc.
- **Schema drift risk.** CLAUDE.md calls out `tracker/slot-key schema drift` as a known failure mode. A new keyed stateful structure is exactly where that class of bug reappears. Would need the same careful key contract as `NodeStateTracker`.
- **"Should be connected on what basis"** is the hard epistemic question. Pure type-level heuristic ("attribute and instrumental_value always *could* be connected") over-generates. Options:
  - Canonical slot co-occurrence
  - SRL argument co-reference
  - Extraction-time LLM hints
  - Some combination
  This is the part that needs design work, not just coding.
- **Generalises cleanly to flat methods.** In RG, the gap is an element × construct cell with no rating. In CJM, a stage with no touchpoints. A generalised `ExpectedStructureGapTracker` could unify all four methodologies under one abstraction — bigger win than just fixing `bridge`.

### Suggested bead split (if pursued)

1. **Bead 1** — stateful gap registry for MEC only. Prove the abstraction; calibrate late-phase boost; validate against simulation runs.
2. **Bead 2** — generalise to slot-coverage gaps for flat methods (CJM, RG, JTBD trinity).

Designing the generalised version first risks over-abstraction before knowing what's load-bearing.

---

## 6. Open questions / decision points

- [ ] Option A (new strategy) vs Option B (phase-boost existing) vs Option C (stateful `ChainGapTracker`)?
- [ ] If C: what signal drives "these two nodes *should* be connected"? Canonical slot co-occurrence feels most principled; needs validation.
- [ ] Late-phase window: turns ≥ `mid_max_turns - 3`? Or absolute `total_turns - 3`? Current simulation hard caps turns, real interviews may not.
- [ ] How to avoid the `revitalize` escape-valve failure mode (CLAUDE.md — positive self-count weights become self-reinforcing loops)?
- [ ] Does the `attempts` counter need its own repetition brake, or is `interview.strategy.self_count` sufficient?
- [ ] Per-methodology gap definitions — should they live in methodology YAML or in code? (YAML keeps domain content out of code, but gap computation is non-trivial.)

## 7. Related code pointers

- `src/signals/graph/chain_topology_signals.py` — current `level.skip` detector (line 230)
- `src/services/node_state_tracker.py` — precedent for per-node stateful tracking
- `src/services/canonical_slot_service.py` — "expected template" infrastructure for flat methods
- `config/methodologies/means_end_chain_v2_strict.yaml` — `bridge` strategy weights
- `.claude/context/signal-detection-graph.md` — signal detection spec
- `.claude/context/strategy-scoring.md` — joint scoring mechanics, `valid_when` gates, repetition brakes
- `.claude/context/node-state-tracker.md` — schema drift failure mode
