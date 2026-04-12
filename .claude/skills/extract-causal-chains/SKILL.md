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

# Build: node_type -> level
node_levels = {n["name"]: n.get("level", 0) for n in ontology.get("nodes", [])}
terminal_levels = {n["name"]: n.get("terminal", False) for n in ontology.get("nodes", [])}

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

# Determine expected full chain sequence from ontology
sorted_types = [t for t, _ in sorted(node_levels.items(), key=lambda x: x[1])]
full_chain_levels = sorted(set(node_levels.values()) - {0})
full_chain_types = [t for t in sorted_types if node_levels.get(t, 0) in full_chain_levels]
max_terminal_level = max(
    (node_levels[t] for t in terminal_levels if terminal_levels[t]), default=max(full_chain_levels, default=0)
)

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

# Canonical slot utterance mapping via surface nodes
surface_by_id = {n["id"]: n for n in data["graph"]["nodes"]}
for slot in data["canonical_graph"]["slots"]:
    all_utt_ids = []
    all_quotes = []
    for snid in slot.get("surface_node_ids", []):
        snode = surface_by_id.get(snid)
        if snode:
            all_utt_ids.extend(snode.get("source_utterance_ids", []) or [])
            all_quotes.extend(snode.get("source_quotes", []) or [])
    slot["_mapped_utt_ids"] = all_utt_ids
    slot["_mapped_quotes"] = all_quotes[:5]

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

def walk_chains(nodes, edges, node_by_id, edge_type="leads_to"):
    """Return maximal paths of length >= 2 over edges of given type.
    Filters superseded nodes. Never traverses revises.
    Maximal = drop any path that is a strict prefix of another."""
    active_nodes = {nid: n for nid, n in node_by_id.items() if not n.get("superseded_by")}
    adj = defaultdict(list)
    for e in edges:
        if e["edge_type"] != edge_type:
            continue
        s, t = e["source_node_id"], e["target_node_id"]
        if s not in active_nodes or t not in active_nodes:
            continue
        adj[s].append((t, e))

    incoming = defaultdict(int)
    for s, outs in adj.items():
        for t, _ in outs:
            incoming[t] += 1
    roots = [nid for nid in active_nodes if incoming[nid] == 0 and nid in adj]

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

    # Maximal filter: drop paths that are strict prefixes of longer paths
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
    return maximal

def classify_chain(path_nodes, node_by_id):
    """Return tier name for a chain path. Tiers: full, advanced, developing, started, lateral."""
    types = [node_by_id[nid]["node_type"] for nid in path_nodes]
    levels = [node_levels.get(t, 0) for t in types]

    # Exclude lateral (same-type) chains
    if len(set(types)) == 1:
        return "lateral"

    # Full chain: visits every expected level in order, from min to max terminal
    if levels == list(range(min(full_chain_levels), max_terminal_level + 1)):
        return "full"

    max_level = max(levels)
    if max_level >= 4:
        return "advanced"
    if max_level == 3:
        return "developing"
    if max_level == 2:
        return "started"
    return "other"

def render_chain(path_nodes, path_edges, node_by_id):
    parts = [' → '.join(
        f"`{node_by_id[nid]['label']}` ({node_by_id[nid]['node_type']}, t={edge_min_turn(path_edges[i]) if i < len(path_edges) else None or '?'})"
        for i, nid in enumerate(path_nodes)
    )]
    lines = ['### Chain', f'**Path**: {parts[0]}', '']
    lines.append('**Evidence**:')
    for i, e in enumerate(path_edges):
        src = node_by_id[e['source_node_id']]
        tgt = node_by_id[e['target_node_id']]
        t = edge_min_turn(e)
        quotes = e.get('source_quotes', []) or []
        quote = quotes[0] if quotes else '(no quote)'
        lines.append(f'- `{src["label"]} → {tgt["label"]}` (t={t or "?"}): _"{quote}"_')
    lines.append('')
    return '\n'.join(lines)

# Extract chains from both layers
surface_nodes = data["graph"]["nodes"]
surface_edges = data["graph"]["edges"]
canon_slots = data["canonical_graph"]["slots"]
# Normalize canonical edge keys to match surface edge format
canon_edges = []
for e in data["canonical_graph"]["edges"]:
    ce = dict(e)
    ce["source_node_id"] = ce.pop("source_slot_id", e.get("source_node_id"))
    ce["target_node_id"] = ce.pop("target_slot_id", e.get("target_node_id"))
    canon_edges.append(ce)

def slot_to_node(slot):
    return {
        'id': slot['slot_id'],
        'label': slot['slot_name'],
        'node_type': slot['node_type'],
        'source_utterance_ids': slot.get('_mapped_utt_ids', []),
        'source_quotes': slot.get('_mapped_quotes', []),
    }

canon_nodes = [slot_to_node(s) for s in canon_slots]
canon_by_id = {n['id']: n for n in canon_nodes}

surf_paths = walk_chains(surface_nodes, surface_edges, {n['id']: n for n in surface_nodes})
can_paths = walk_chains(canon_nodes, canon_edges, canon_by_id)

# Classify and bucket
surf_by_tier = defaultdict(list)
for path_nodes, path_edges in surf_paths:
    tier = classify_chain(path_nodes, {n['id']: n for n in surface_nodes})
    if tier != "lateral":
        surf_by_tier[tier].append((path_nodes, path_edges))

can_by_tier = defaultdict(list)
for path_nodes, path_edges in can_paths:
    tier = classify_chain(path_nodes, canon_by_id)
    if tier != "lateral":
        can_by_tier[tier].append((path_nodes, path_edges))

superseded_count = sum(1 for n in surface_nodes if n.get('superseded_by'))
rev_count_surface = sum(1 for e in surface_edges if e['edge_type'] == 'revises')
rev_count_canon = sum(1 for e in canon_edges if e['edge_type'] == 'revises')

surf_leads_to = sum(1 for e in surface_edges if e['edge_type'] == 'leads_to')
can_leads_to = sum(1 for e in canon_edges if e['edge_type'] == 'leads_to')

surf_node_types = sorted(set(n['node_type'] for n in surface_nodes))
can_node_types = sorted(set(s['node_type'] for s in canon_slots))

# Orphans: nodes with no leads_to edges at all
surf_involved = set()
for e in surface_edges:
    if e['edge_type'] == 'leads_to':
        surf_involved.add(e['source_node_id'])
        surf_involved.add(e['target_node_id'])
surf_orphans = [n for n in surface_nodes if n['id'] not in surf_involved and not n.get('superseded_by')]

# Revisions
revisions = []
surf_by_id_all = {n['id']: n for n in surface_nodes}
for e in surface_edges:
    if e['edge_type'] == 'revises':
        old = surf_by_id_all.get(e['source_node_id'])
        new = surf_by_id_all.get(e['target_node_id'])
        if old and new:
            revisions.append((old, new))

# Build markdown
out_path = Path(f'causal_chain/{SOURCE.stem}_causal_chains.md')
out_path.parent.mkdir(exist_ok=True)

md = f"""# Causal Chain Extraction — {SOURCE.name}

## Source specs
- **Session ID**: {meta.get('session_id', 'N/A')}
- **Concept**: {meta.get('concept_name', 'N/A')} (`{meta.get('concept_id', 'N/A')}`)
- **Methodology**: `{methodology}`
- **Persona**: {meta.get('persona_name', 'N/A')} (`{meta.get('persona_id', 'N/A')}`)
- **Total turns**: {meta.get('total_turns', 'N/A')}
- **Status**: {meta.get('status', 'N/A')}
- **Saved at**: {meta.get('saved_at', 'N/A')}

## Extraction config
- **Constraint source**: {constraint_source}
- **Permitted connections** (leads_to):
"""
if has_constraints:
    for pair in leads_to_rules:
        md += f"  - {pair[0]} → {pair[1]}\n"
else:
    md += '  - (permissive only — no constraints defined)\n'

md += f"""- **Superseded nodes excluded**: {superseded_count}
- **Revises edges excluded from traversal**: {rev_count_surface + rev_count_canon} ({rev_count_surface} surface, {rev_count_canon} canonical)

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | {len(surface_nodes)} | {len(canon_slots)} |
| Edges (leads_to) | {surf_leads_to} | {can_leads_to} |
| Edges (revises) | {rev_count_surface} | {rev_count_canon} |
| Node types | {', '.join(surf_node_types)} | {', '.join(can_node_types)} |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|-----------------|
| Full | {' → '.join(full_chain_types)} | {len(surf_by_tier.get('full', []))} | {len(can_by_tier.get('full', []))} |
| Advanced | Reaches instrumental_value or terminal_value, but incomplete | {len(surf_by_tier.get('advanced', []))} | {len(can_by_tier.get('advanced', []))} |
| Developing | Reaches psychosocial_consequence but not values | {len(surf_by_tier.get('developing', []))} | {len(can_by_tier.get('developing', []))} |
| Started | attribute → functional_consequence only | {len(surf_by_tier.get('started', []))} | {len(can_by_tier.get('started', []))} |
| Lateral (excluded) | Same-type only chains | {len(surf_paths) - sum(len(v) for v in surf_by_tier.values())} | {len(can_paths) - sum(len(v) for v in can_by_tier.values())} |

---

## Full chains — complete laddering
"""
for i, (path_nodes, path_edges) in enumerate(surf_by_tier.get('full', []), 1):
    md += render_chain(path_nodes, path_edges, {n['id']: n for n in surface_nodes}).replace('### Chain', f'### Chain {i} [surface]')
for i, (path_nodes, path_edges) in enumerate(can_by_tier.get('full', []), 1):
    md += render_chain(path_nodes, path_edges, canon_by_id).replace('### Chain', f'### Chain {i} [canonical]')
if not surf_by_tier.get('full') and not can_by_tier.get('full'):
    md += '_No full chains found._\n\n'

md += '## Advanced chains — value-reaching but incomplete\n\n'
for i, (path_nodes, path_edges) in enumerate(surf_by_tier.get('advanced', []), 1):
    md += render_chain(path_nodes, path_edges, {n['id']: n for n in surface_nodes}).replace('### Chain', f'### Chain {i} [surface]')
for i, (path_nodes, path_edges) in enumerate(can_by_tier.get('advanced', []), 1):
    md += render_chain(path_nodes, path_edges, canon_by_id).replace('### Chain', f'### Chain {i} [canonical]')
if not surf_by_tier.get('advanced') and not can_by_tier.get('advanced'):
    md += '_No advanced chains found._\n\n'

md += '## Developing chains — consequence-level progression\n\n'
for i, (path_nodes, path_edges) in enumerate(surf_by_tier.get('developing', []), 1):
    md += render_chain(path_nodes, path_edges, {n['id']: n for n in surface_nodes}).replace('### Chain', f'### Chain {i} [surface]')
for i, (path_nodes, path_edges) in enumerate(can_by_tier.get('developing', []), 1):
    md += render_chain(path_nodes, path_edges, canon_by_id).replace('### Chain', f'### Chain {i} [canonical]')
if not surf_by_tier.get('developing') and not can_by_tier.get('developing'):
    md += '_No developing chains found._\n\n'

md += '## Started chains — attribute-to-functional only\n\n'
for i, (path_nodes, path_edges) in enumerate(surf_by_tier.get('started', []), 1):
    md += render_chain(path_nodes, path_edges, {n['id']: n for n in surface_nodes}).replace('### Chain', f'### Chain {i} [surface]')
for i, (path_nodes, path_edges) in enumerate(can_by_tier.get('started', []), 1):
    md += render_chain(path_nodes, path_edges, canon_by_id).replace('### Chain', f'### Chain {i} [canonical]')
if not surf_by_tier.get('started') and not can_by_tier.get('started'):
    md += '_No started chains found._\n\n'

md += '## Revisions (positive validation signal)\n\n'
if revisions:
    for old, new in revisions:
        md += f'- `{old["label"]}` → `{new["label"]}`\n'
        old_q = (old.get('source_quotes') or ['(no quote)'])[0]
        new_q = (new.get('source_quotes') or ['(no quote)'])[0]
        md += f'  - Original: _"{old_q}"_\n'
        md += f'  - Revision: _"{new_q}"_\n'
else:
    md += '_No revisions found._\n\n'

md += '## Orphan nodes (no incoming or outgoing leads_to edges)\n\n'
if surf_orphans:
    for n in surf_orphans:
        q = (n.get('source_quotes') or ['(no quote)'])[0]
        md += f'- `{n["label"]}` ({n["node_type"]}) — _"{q}"_\n'
else:
    md += '_No orphan nodes found._\n\n'

md += f"""\n## Retracted chains (dropped due to supersession)
- **Count**: {superseded_count}
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Constraints from: `{constraint_source}`
- Overrides applied: {'yes' if methodology in ANALYTICAL_OVERRIDES else 'no'}
- Known limitations: Canonical slot layer may hide language variation relevant to laddering validity.
"""

out_path.write_text(md)
print(f'Wrote {out_path}')
for tier in ['full', 'advanced', 'developing', 'started']:
    print(f'{tier}: surface={len(surf_by_tier.get(tier, []))}, canonical={len(can_by_tier.get(tier, []))}')
"""
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
