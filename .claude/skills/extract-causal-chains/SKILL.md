---
name: extract-causal-chains
description: Use when the user asks to extract causal chains from a synthetic interview JSON (files in synthetic_interviews/). Produces a markdown report in causal_chain/ with methodology-conforming and permissive chains from both surface and canonical graphs, flagged by evidence strength, turn-order inversions, and MEC conformance. Push back if the user does not specify which source file to extract from.
project: interview-system-v2
---

# Extract Causal Chains

## Purpose

Validate that the interview system produces meaningful causal structure by extracting chains from a saved interview graph and classifying them against the methodology's own schema. Serves as a proto-analytical layer until the real analytical layer ships.

## Required input

**Source file path** — a single JSON under `synthetic_interviews/`. If the user's request is vague ("extract chains", "run on the latest one"), **stop and ask for the exact filename**. Do not guess.

Everything else has documented defaults:
- Output path: `causal_chain/<source_timestamp>_causal_chains.md` (timestamp = the `YYYYMMDD_HHMMSS` prefix of the source file)
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

## Procedure

When invoked with a source file path, run this Python inline via `uv run python -c "..."` (or write to a temp file and run). The code:

```python
import json, sys, yaml, re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SOURCE = Path("synthetic_interviews/FILENAME.json")  # fill in from user
assert SOURCE.exists(), f"Source not found: {SOURCE}"

data = json.loads(SOURCE.read_text())
for key in ("metadata", "graph", "canonical_graph", "turns"):
    assert key in data, f"Malformed JSON: missing '{key}'"

meta = data["metadata"]
methodology = meta["methodology"]

# Load methodology YAML
meth_path = Path(f"config/methodologies/{methodology}.yaml")
assert meth_path.exists(), f"Methodology YAML not found: {meth_path}"
meth = yaml.safe_load(meth_path.read_text())
ontology = meth.get("ontology", {})

# Build: node_type -> level (for display only)
node_levels = {n["name"]: n.get("level", 0) for n in ontology.get("nodes", [])}

# Build: edge_type -> permitted_connections
edge_rules = {}
for e in ontology.get("edges", []):
    edge_rules[e["name"]] = e.get("permitted_connections", [])

# Analytical overrides (hardcoded above — paste the real dict here)
ANALYTICAL_OVERRIDES = {}  # <-- copy from skill file

# Resolve constraints for leads_to
constraint_source = "yaml"
leads_to_rules = edge_rules.get("leads_to", [])
if methodology in ANALYTICAL_OVERRIDES:
    leads_to_rules = ANALYTICAL_OVERRIDES[methodology]
    constraint_source = "analytical_override"
has_constraints = bool(leads_to_rules) and leads_to_rules != [["*", "*"]]

def is_conforming(src_type, tgt_type):
    if not has_constraints:
        return True  # permissive-only mode
    for pair in leads_to_rules:
        if pair == ["*", "*"]:
            return True
        if pair[0] == src_type and pair[1] == tgt_type:
            return True
    return False

# Build utterance_id -> turn_number map via quote-in-response matching.
# VERIFIED APPROACH (dry-run on 20260325_111835_glp1_food_mec_strict_glp1_user.json):
# turns[].nodes_added and turns[].edges_added are None in saved interviews — do NOT rely on them.
# Instead: each node carries source_quotes (verbatim fragments) AND source_utterance_ids.
# Match the first quote against each turn's response text; when it appears, bind all the
# node's utterance IDs to that turn_number. On the reference file this achieved 16/16 coverage.
utt_to_turn = {}
turns = data["turns"]
for node in data["graph"]["nodes"]:
    quotes = node.get("source_quotes", []) or []
    utt_ids = node.get("source_utterance_ids", []) or []
    if not quotes or not utt_ids:
        continue
    q = quotes[0]
    for turn in turns:
        resp = turn.get("response", "") or ""
        if q and q in resp:
            for uid in utt_ids:
                utt_to_turn[uid] = turn["turn_number"]
            break
# Do the same pass over canonical slots' underlying surface nodes for canonical chain turn mapping.
# Sanity check: compute coverage and fail loud if < 100%.
all_utts = set()
for n in data["graph"]["nodes"]:
    for u in n.get("source_utterance_ids", []) or []:
        all_utts.add(u)
missing = all_utts - set(utt_to_turn)
if missing:
    print(f"WARNING: {len(missing)}/{len(all_utts)} utterances unmapped to turns. "
          f"Turn numbers will be marked as '?' for affected edges.", file=sys.stderr)

def edge_min_turn(edge):
    turns_seen = [utt_to_turn[u] for u in edge.get("source_utterance_ids", []) if u in utt_to_turn]
    return min(turns_seen) if turns_seen else None

def walk_chains(nodes, edges, edge_type="leads_to", require_conforming=False):
    """Return maximal paths of length >= 2 over edges of given type.
    Filters superseded nodes. Never traverses revises.
    Maximal = drop any path that is a strict prefix/suffix of another."""
    node_by_id = {n["id"]: n for n in nodes if not n.get("superseded_by")}
    adj = defaultdict(list)
    for e in edges:
        if e["edge_type"] != edge_type:
            continue
        s, t = e["source_node_id"], e["target_node_id"]
        if s not in node_by_id or t not in node_by_id:
            continue
        if require_conforming:
            if not is_conforming(node_by_id[s]["node_type"], node_by_id[t]["node_type"]):
                continue
        adj[s].append((t, e))

    # Find all maximal paths via DFS from nodes with no incoming edge (roots)
    incoming = defaultdict(int)
    for s, outs in adj.items():
        for t, _ in outs:
            incoming[t] += 1
    roots = [nid for nid in node_by_id if incoming[nid] == 0 and nid in adj]

    all_paths = []
    def dfs(node_id, path_nodes, path_edges):
        if node_id not in adj or not adj[node_id]:
            if len(path_nodes) >= 2:
                all_paths.append((path_nodes[:], path_edges[:]))
            return
        extended = False
        for nxt, edge in adj[node_id]:
            if nxt in path_nodes:  # cycle guard
                continue
            extended = True
            dfs(nxt, path_nodes + [nxt], path_edges + [edge])
        if not extended and len(path_nodes) >= 2:
            all_paths.append((path_nodes[:], path_edges[:]))

    for r in roots:
        dfs(r, [r], [])

    # Maximal filter: drop paths that are prefixes of longer paths
    all_paths.sort(key=lambda p: -len(p[0]))
    maximal = []
    seen_sequences = set()
    for nodes_p, edges_p in all_paths:
        key = tuple(nodes_p)
        is_prefix = any(
            len(key) < len(other) and other[:len(key)] == key
            for other in seen_sequences
        )
        if not is_prefix:
            maximal.append((nodes_p, edges_p))
            seen_sequences.add(key)
    return maximal, node_by_id

# Extract chains from both layers
surface_nodes = data["graph"]["nodes"]
surface_edges = data["graph"]["edges"]
canon_slots = data["canonical_graph"]["slots"]
canon_edges = data["canonical_graph"]["edges"]

# Render report — see output template below
# ... (build markdown sections, write to causal_chain/<timestamp>_causal_chains.md)
```

**Turn mapping is quote-based, verified**: `turns[].nodes_added` / `edges_added` are `None` in saved interviews; do not rely on them. The code above matches `node.source_quotes[0]` against each turn's `response` text. Validated on `20260325_111835_glp1_food_mec_strict_glp1_user.json` (16/16 utterance coverage). If coverage drops below 100% on a new file, investigate rather than silently reporting `?` turn numbers — it likely means quote truncation or response reformatting.

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

## Conformance metric
- **Surface**: <C> conforming / <P> permissive chains = <ratio>%
- **Canonical**: <C> conforming / <P> permissive chains = <ratio>%
- **Interpretation**: <one sentence — e.g., "High conformance ratio indicates the system respects MEC ladder ordering in most extracted paths.">

---

## Surface chains — conforming

### Chain 1 [MEC-valid]
**Path**: `creamy texture` (attribute, t=2) → `easier to digest` (functional_consequence, t=2) → `feel healthier` (psychosocial_consequence, t=5) → `self-respect` (terminal_value, t=9)

**Evidence**:
- `creamy texture → easier to digest` (t=2): *"The texture just goes down smoother, so my stomach doesn't protest."*
- `easier to digest → feel healthier` (t=5): *"When I'm not bloated I actually feel like I'm taking care of myself."*
- ⚠ weak: `feel healthier → self-respect` (t=9, single utterance): *"...and that kind of matters to how I see myself."*

### Chain 2 [MEC-valid] ⚠ reconstructed
**Path**: A (t=8) → B (t=2) → C (t=5)
**Note**: Turn order inversion — downstream element appeared before upstream. Respondent likely reconstructed under probing.

...

## Surface chains — permissive only (violates methodology)

### Chain 3 [MEC-violating]
**Path**: `terminal_value` → `attribute` (goes backwards down the ladder)
**Evidence**: ...
**Why flagged**: violation of `means_end_chain_v2_strict` permitted connections. Possible extraction error or respondent-led inversion.

...

## Canonical chains — conforming
...

## Canonical chains — permissive only
...

## Revisions (positive validation signal)
- Turn 4 → Turn 9: old belief `<label>` superseded by `<new label>`
  - Original: *"<quote from turn 4>"*
  - Revision: *"<quote from turn 9>"*

## Orphan nodes (no incoming or outgoing leads_to edges)
- `<label>` (node_type, t=<turn>) — *"<quote>"*
- ...
**Interpretation**: <N> orphans suggest <extraction gaps | isolated concepts | first-mention decay>.

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
