---
name: extract-causal-chains
description: Use when the user asks to extract causal chains from a synthetic interview JSON (files in synthetic_interviews/). Produces a markdown report in reports/causal_chains/ with methodology-conforming and permissive chains from both surface and canonical graphs, flagged by evidence strength, turn-order inversions, and MEC conformance. Push back if the user does not specify which source file to extract from.
project: interview-system-v2
---

# Extract Causal Chains

## Purpose

Validate that the interview system produces meaningful causal structure by extracting chains from a saved interview graph and classifying them against the methodology's own schema. Serves as a proto-analytical layer until the real analytical layer ships.

## Required input

**Source file path** — a single JSON under `synthetic_interviews/`. If the user's request is vague ("extract chains", "run on the latest one"), **stop and ask for the exact filename**. Do not guess.

Everything else has documented defaults:
- Output path: `reports/causal_chains/<source_timestamp>_causal_chains.md` (timestamp = the `YYYYMMDD_HHMMSS` prefix of the source file)
- Layers: both surface and canonical
- Chain algorithm: maximal paths, length ≥ 2, `leads_to` edges only
- Minimum evidence: report everything, flag visually
- Single file only; no batching

## Rules (do not violate)

1. **Filter superseded nodes** before any chain walk. A node with `superseded_by != null` is a retracted belief. Count retracted chains in a subsection but do not print them fully.
2. **Never traverse `revises` edges.** They are bookkeeping, not reasoning. List them in a separate "Revisions" section as a positive validation signal.
3. **Methodology conformance** comes from `permitted_connections` in the methodology YAML at `config/methodologies/<methodology>.yaml`, where `<methodology>` = `metadata.methodology` from the source JSON.
4. **Analytical overrides** (see block below) **replace** the YAML constraints, not merge. The output header must state which source was used.
5. **Fail loud** on: missing source file, missing methodology YAML, unknown `edge_type` in data not present in methodology YAML, malformed JSON shape (missing `graph`, `canonical_graph`, `turns`, or `metadata`).
6. **No silent defaults.** If `permitted_connections` is absent from the YAML *and* no override exists, emit only the permissive view with an explicit banner in the output.

## Analytical overrides (temporary — delete when analytical layer ships)

This dict is the proto-analytical layer. It lets the skill apply stricter constraints for analysis than were enforced at interview time. Entries are added **only** when you first extract from a methodology whose YAML has no `permitted_connections` and you've decided the analytical rules.

```python
# Keys: methodology name (from metadata.methodology)
# Values: list of [source_node_type, target_node_type] pairs that count as conforming
# Empty = no overrides registered yet; skill falls back to YAML, warns if YAML also empty
ANALYTICAL_OVERRIDES: dict[str, list[list[str]]] = {
    # Example when you need it:
    # "jobs_to_be_done_v2": [
    #     ["job", "outcome"],
    #     ["outcome", "value"],
    # ],  # Reason: <why these constraints, date added>
}
```

When you add an entry: include a comment with the reason and date. When the analytical layer ships: delete this block and the skill entirely.

## Tiered chain reporting

Chains are classified into **laddering tiers** based on the highest ontology level they reach. A chain is placed in the **highest tier** it qualifies for. Same-type (lateral) chains are excluded entirely.

### Tier definitions

| Tier | Qualification | Example |
|------|---------------|---------|
| **Full** | Spans from min level to max terminal level, visiting every intermediate level in order with no skips | `attribute → functional_consequence → psychosocial_consequence → instrumental_value → terminal_value` |
| **Advanced** | Reaches `instrumental_value` or `terminal_value`, but skips at least one level or is out of strict order | `attribute → functional_consequence → terminal_value` |
| **Developing** | Reaches `psychosocial_consequence` but does not reach values | `attribute → functional_consequence → psychosocial_consequence` |
| **Started** | Reaches `functional_consequence` only (lowest rung) | `attribute → functional_consequence` |
| **Excluded** | Same-type only (lateral chains like `attribute → attribute`) | — |

### Computation rules

1. Build all maximal paths over `leads_to` edges (length ≥ 2), filtering superseded nodes.
2. Exclude any path where **all node types are identical** (lateral clustering).
3. For each remaining path, compute the ordered list of ontology levels.
4. Determine the **max level reached** in the path.
5. Assign to the highest qualifying tier:
   - **Full**: levels == `[1, 2, 3, 4, 5]` (or the methodology's full sequence)
   - **Advanced**: max level ≥ 4 (instrumental_value) AND not Full
   - **Developing**: max level == 3 (psychosocial_consequence)
   - **Started**: max level == 2 (functional_consequence)

## Procedure

When invoked with a source file path, run the dedicated script:

```bash
uv run python scripts/reporting/generate_causal_chains.py synthetic_interviews/FILENAME.json
```

For a custom output path:
```bash
uv run python scripts/reporting/generate_causal_chains.py synthetic_interviews/FILENAME.json -o /path/to/output.md
```

**Turn mapping is quote-based, verified**: `turns[].nodes_added` / `edges_added` are `None` in saved interviews; do not rely on them. The script matches `node.source_quotes[0]` against each turn's `response` text. Validated on `20260325_111835_glp1_food_mec_strict_glp1_user.json` (16/16 utterance coverage). If coverage drops below 100% on a new file, investigate rather than silently reporting `?` turn numbers — it likely means quote truncation or response reformatting.

The script source is at `scripts/reporting/generate_causal_chains.py` — edit that file for algorithmic changes, not this skill.

## Output template

```markdown
# Causal Chain Extraction — <source_filename>

## Source specs
- **Session ID**: <metadata.session_id>
- **Concept**: <metadata.concept_name> (`<metadata.concept_id>`)
- **Methodology**: `<metadata.methodology>`
- **Persona**: <metadata.persona_name> (`<metadata.persona_id>`)
- **Total turns**: <metadata.total_turns>
- **Status**: <metadata.status>
- **Saved at**: <metadata.saved_at>

## Extraction config
- **Constraint source**: <yaml | analytical_override | none (permissive only)>
- **Permitted connections** (leads_to):
  - attribute → functional_consequence
  - functional_consequence → psychosocial_consequence
  - ... (list all)
- **Superseded nodes excluded**: <N>
- **Revises edges excluded from traversal**: <N>

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | <n> | <n> |
| Edges (leads_to) | <n> | <n> |
| Edges (revises) | <n> | <n> |
| Node types | <list> | <list> |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|-----------------|
| Full | attribute → functional_consequence → psychosocial_consequence → instrumental_value → terminal_value | 0 | 0 |
| Advanced | Reaches instrumental_value or terminal_value, but incomplete | 12 | 3 |
| Developing | Reaches psychosocial_consequence but not values | 34 | 8 |
| Started | attribute → functional_consequence only | 46 | 9 |
| Lateral (excluded) | Same-type only chains | 15 | 2 |

---

## Full chains — complete laddering
_No full chains found._

## Advanced chains — value-reaching but incomplete
### Chain 1 [surface]
**Path**: `creamy texture` (attribute, t=2) → `easier to digest` (functional_consequence, t=2) → `feel healthier` (psychosocial_consequence, t=5) → `self-respect` (terminal_value, t=9)

**Evidence**:
- `creamy texture → easier to digest` (t=2): *"The texture just goes down smoother, so my stomach doesn't protest."*
- `easier to digest → feel healthier` (t=5): *"When I'm not bloated I actually feel like I'm taking care of myself."*
- ⚠ weak: `feel healthier → self-respect` (t=9, single utterance): *"...and that kind of matters to how I see myself."*

## Developing chains — consequence-level progression
...

## Started chains — attribute-to-functional only
...

## Revisions (positive validation signal)
- Turn 4 → Turn 9: old belief `<label>` superseded by `<new label>`
  - Original: *"<quote from turn 4>"*
  - Revision: *"<quote from turn 9>"*

## Orphan nodes (no incoming or outgoing leads_to edges)
- `<label>` (node_type, t=<turn>) — *"<quote>"*
- ...

## Retracted chains (dropped due to supersession)
- **Count**: <N>
- **Not printed in full** — these chains passed through nodes later marked as superseded. The supersession events themselves are in the Revisions section.

## Methodology notes
- Constraints from: `<source>`
- Overrides applied: <yes/no — if yes, include override dict entry and reason>
- Known limitations: <e.g., "canonical slot layer may hide language variation relevant to laddering validity">
```

## When to push back on the user

- Vague request ("extract chains") → **ask for the exact filename**
- File doesn't exist → report the path that failed, list nearby filenames in `synthetic_interviews/`
- Methodology YAML missing → stop, report, suggest next steps (create YAML or add override)
- Unknown edge type in data → stop, report, ask whether to treat as causal or meta
- `permitted_connections` missing AND no override → proceed in permissive-only mode BUT include the banner in the output; warn the user in chat that conformance was not assessed

## What NOT to do

- Do not infer the source file from context. Ask.
- Do not merge YAML constraints with overrides. Overrides replace.
- Do not traverse `revises` edges "just to see what's there."
- Do not include superseded nodes in chains under any circumstance.
- Do not hardcode methodology names anywhere except the `ANALYTICAL_OVERRIDES` dict.
- Do not batch multiple files. One invocation = one source file.
- Do not add narrative commentary to the extracted chains beyond what the template calls for. The report is an analytical artifact, not an essay.
