---
name: cr
description: Use at session end to review the session's changes against the codified context constitution. Checks whether new agents, context docs, or CLAUDE.md updates are needed. Triggered by /cr or phrases like "constitution review", "check if context needs updating", "session review". Use /cr --deep for a quarterly semantic audit that verifies doc content against source code.
project: interview-system-v2
---

# Constitution Review (/cr)

## Overview

Session-end review against the project's codified context governance principles (`.claude/codified-context-principles.md`). Analyzes what changed this session and recommends Tier 1/2/3 updates.

**Two modes:**
- **Default (`/cr`)**: Quick structural review (~30s). Run at every session end.
- **Deep (`/cr --deep`)**: Semantic audit (~10-15 min). Run monthly, before releases, or when you suspect docs have drifted from code.

## When to use

**Default mode — end of every work session, before committing and closing.** Especially after:
- Adding new signals, strategies, or methodology files
- Modifying pipeline stages or contracts
- Fixing bugs that revealed missing documentation
- Touching subsystems for the first time
- Any multi-file change

**Deep mode — periodically or on demand:**
- Before a release or major merge
- When the codebase has undergone refactoring (e.g., B11 edge extraction, vxz6 tracker keyspace)
- When agents make correct-looking decisions that produce wrong results (symptom of stale specs)
- When `check_doc_drift.py` is clean but you suspect docs are lying
- Quarterly maintenance

## Mode Detection

If the user's message contains `--deep`, `deep audit`, `semantic audit`, `verify doc content`, or `check docs against code`, run **Deep Mode**.

Otherwise, run **Default Mode**.

---

## DEFAULT MODE

### Step 1 — Gather session state

Run in parallel:

```bash
# What files changed this session
git diff --name-only HEAD~5 HEAD 2>/dev/null || git diff --name-only --cached

# Current CLAUDE.md size
wc -l CLAUDE.md

# Existing agents
ls .claude/agents/*/AGENT.md 2>/dev/null

# Existing context docs
ls .claude/context/*.md 2>/dev/null

# Drift check + cross-reference validation (orphaned docs, missing agents, stale source refs)
uv run python scripts/check_doc_drift.py

# Trigger table for manual coverage analysis (globs can't be evaluated by grep)
echo "=== All src/ directories ===" && fd -t d --maxdepth 2 . src/ | sort
echo ""
echo "=== Trigger patterns from CLAUDE.md ==="
rg -N '^\| `src/' CLAUDE.md | head -20
echo ""
echo "↑ Compare manually: each directory should match a trigger glob (e.g. src/signals/** covers src/signals/meta/)"

# Tier 2/3 counts for growth benchmarks
echo "Tier 2 agents: $(ls .claude/agents/*/AGENT.md 2>/dev/null | wc -l)"
echo "Tier 3 docs: $(ls .claude/context/*.md 2>/dev/null | wc -l)"

# Code LOC estimate (for knowledge-to-code ratio)
fd -e py . src/ -x wc -l {} 2>/dev/null | tail -1

# Open beads
bd list --status=open 2>/dev/null
bd list --status=in_progress 2>/dev/null
```

### Step 2 — Structural checks

Run each check and record findings. Zero warnings from `check_doc_drift.py` means clean — report it as OK, not as unchecked.

| Check | How | Flag if |
|-------|-----|---------|
| **CLAUDE.md size** | `wc -l CLAUDE.md` | > 800 lines (extract to Tier 2/3) |
| **Agent coverage (session)** | Compare changed files against trigger table in CLAUDE.md | Files touched that match no agent pattern |
| **Agent coverage (full tree)** | Manually compare ALL `src/` directories against trigger table globs (simple grep won't resolve `**` patterns) | Production directory with no trigger match and not in intentional gaps list |
| **Doc drift** | `check_doc_drift.py` output | Any `⚠  Doc drift detected` lines |
| **Cross-reference validation** | `check_doc_drift.py` output | Any `⚠  Cross-reference validation failed` lines (covers: missing agents, missing docs, missing source files, orphaned context docs) |
| **Doc mapping gaps** | Compare changed source files against `.claude/doc_mapping.yaml` | Source file with no mapping entry |
| **Growth benchmarks** | Compare Tier 2/3 counts against `.claude/codified-context-principles.md` §Growth Benchmarks table | Outside expected range for project stage |
| **Knowledge-to-code ratio** | `(CLAUDE.md lines + Σ agent lines + Σ context doc lines) / code LOC` | Below 1:4 (docs:code) |

### Step 3 — Semantic checks (judgment-based)

For each changed file, evaluate:

**Failure mode routing (ALWAYS evaluate first):**
- Did this session surface a new failure mode (bug fix, regression, design constraint discovered the hard way)?
- → Route it to the appropriate Tier 3 doc's "Known Failure Modes" section, or a Tier 2 agent's "Anti-patterns" section if it's operational ("don't do X").
- → **NEVER add diagnostic prose to CLAUDE.md directly.** CLAUDE.md's "Known Failure Mode Index" is a routing table — it maps symptom keywords to authoritative sources. If a genuinely new failure mode category emerges (new symptom→source mapping not covered by any table row), add one row to the table. The diagnostic content (root cause, reproduction steps, fix, commit hashes) lives in Tier 2/3.

**Tier 2 (Agent) triggers:**
- Did Claude make the same type of mistake more than once this session?
- Was domain knowledge needed that general prompting got wrong?
- Is the knowledge too large for CLAUDE.md but domain-specific?
- → If yes to all three: recommend creating/updating a specialist agent

**Tier 3 (Context doc) triggers:**
- Did an agent make a mistake a spec would have prevented?
- Is a subsystem's behavior complex enough multiple agents need it?
- Was external integration behavior undocumented?
- → If yes: recommend creating/updating a context doc

**Tier 1 (CLAUDE.md) triggers:**
- Was a convention violated that wasn't written down? (Convention = universal rule, not subsystem-specific insight)
- Is there a new subsystem ALL agents need to know about?
- Does the failure mode routing table need a new row for a genuinely novel symptom→source mapping?
- → If yes: recommend adding a convention or routing table row (but only if universal)

### Step 4 — Output report

Present findings in this format:

```
=== Constitution Review ===

STRUCTURAL:
  [OK|WARN|ACTION] CLAUDE.md: N lines (limit 800)
  [OK|WARN|ACTION] Agent coverage (session): N changed files, X uncovered
  [OK|WARN|ACTION] Agent coverage (full tree): N dirs, X uncovered
  [OK|WARN|ACTION] Doc drift: N warnings
  [OK|WARN|ACTION] Cross-reference validation: N warnings
  [OK|WARN|ACTION] Doc mapping: N unmapped source files
  [OK|WARN|ACTION] Growth benchmarks: N agents (expected N-N), N context docs (expected N-N)
  [OK|WARN|ACTION] Knowledge-to-code ratio: 1:N (target 1:4)

RECOMMENDATIONS:
  1. [ACTION/WARN] <specific recommendation>
     Why: <why this matters>
     How: <concrete step>

  2. ...

SESSION SUMMARY:
  Files changed: N
  New agents needed: Y/N
  Context docs to update: Y/N
  CLAUDE.md update needed: Y/N
```

### Step 5 — Execute (with user approval)

For each recommendation the user accepts:
- **Tier 1 update**: Edit CLAUDE.md, run drift check after
- **Tier 2 creation**: Create `.claude/agents/{id}/AGENT.md` per spec in `.claude/codified-context-principles.md`
- **Tier 3 creation**: Create `.claude/context/{topic}.md` per spec in `.claude/codified-context-principles.md`
- **Doc mapping update**: Add entry to `.claude/doc_mapping.yaml`

Per the self-modification protocol: do not modify Tier 1 and Tier 2/3 in the same action.

---

## DEEP MODE (`/cr --deep`)

Deep mode performs semantic verification — it reads doc content and checks it against actual source code. This catches drift that structural checks miss: docstrings that contradict implementation, ghost symbols, inconsistent stage numbers, and stale architecture descriptions.

**When structural checks pass but behavior is wrong, run deep mode.**

### Step 1 — Run default mode first

Execute Steps 1-2 of Default Mode. If structural checks fail, note them but continue — deep mode may reveal why they failed.

### Step 2 — Ghost symbol detection

For each Tier 3 context doc and Tier 2 agent spec:

1. **Extract referenced source symbols** using regex patterns:
   - Function/method names: `` `([a-z_][a-z0-9_]*)\(` `` or `` `([a-z_][a-z0-9_]*)` `` in code blocks
   - Class names: CamelCase words that appear with module paths (e.g., `NodeStateTracker`, `StrategySelectionOutput`)
   - File paths: `` `src/[a-zA-Z0-9_/]+\.py` ``

2. **Verify existence** with ripgrep:
   ```bash
   # For each symbol found in docs:
   rg --type py "^(class|def) SymbolName" src/
   # For file paths:
   test -f src/path/to/file.py && echo "EXISTS" || echo "MISSING"
   ```

3. **Flag ghost references**: Symbols mentioned in docs that don't exist in source.
   - Common false positives: parameter names, config keys, YAML values — filter these by checking if the symbol is a valid Python identifier that appears in a code-like context
   - Exclude: signal names (`convgraph.node.*`), strategy names, methodology names — these live in YAML

### Step 3 — Docstring-code divergence

For key functions/classes documented in context docs:

1. **Identify documented entry points**: Functions/classes that have detailed descriptions in context docs (e.g., `record_yield`, `rank_strategy_node_pairs`, `select_strategy_and_focus`)

2. **Read the source docstring** and compare to the doc's description:
   ```bash
   # Get docstring
   uv run python -c "import inspect; from src.services.node_state_tracker import NodeStateTracker; print(inspect.getdoc(NodeStateTracker.record_yield))"
   ```

3. **Flag divergence** when:
   - Docstring describes conditional behavior that code doesn't implement (e.g., "checks X before doing Y" but code does Y unconditionally)
   - Docstring references parameters that don't exist in the signature
   - Docstring describes a return type/shape that contradicts the actual return
   - Context doc describes behavior that contradicts the docstring (both should match the code)

### Step 4 — Cross-doc consistency

1. **Extract version numbers and constants** from all context docs:
   - Schema versions (e.g., "schema version 6")
   - Stage numbers (e.g., "Stage 6", "Stage 4.5B")
   - Numeric defaults (e.g., "threshold: 0.80")
   - Pipeline stage counts (e.g., "16-stage pipeline")

2. **Verify against source**:
   ```bash
   # Schema version
   rg "NODE_TRACKER_SCHEMA_VERSION\s*=" src/
   # Stage count in pipeline
   rg "class.*Stage" src/services/turn_pipeline/stages/ | wc -l
   # Threshold values
   rg "surface_similarity_threshold|canonical_similarity_threshold" src/
   ```

3. **Flag inconsistencies**:
   - Same concept described with different stage numbers in different docs
   - Schema version in doc doesn't match source constant
   - Stage count in doc doesn't match actual stage files
   - Default values in doc don't match source defaults

### Step 5 — Agent spec accuracy

For each agent spec (`AGENT.md`):

1. **Check the trigger table**: Verify the glob patterns in the agent's "Triggers" section actually match files that exist
   ```bash
   # For a pattern like src/signals/graph/*.py:
   ls src/signals/graph/*.py 2>/dev/null | head -5
   ```

2. **Check Context Documents list**: Verify every referenced doc exists and is up to date
   ```bash
   for doc in $(rg -o '`\.claude/context/[^`]+`' .claude/agents/*/AGENT.md | tr -d '`' | sort -u); do
       test -f "$doc" && echo "OK: $doc" || echo "MISSING: $doc"
   done
   ```

3. **Check for ghost methods**: Agent specs often describe internal methods (e.g., "`append_response_signal()` routes..."). Verify these methods exist in the source files the agent covers.

### Step 6 — Methodology config sync

If any methodology YAML or strategy-related code was modified:

1. **Check strategy names**: Names in docs must match names in `config/methodologies/*.yaml`
   ```bash
   rg "^\s+name:" config/methodologies/*.yaml
   ```

2. **Check signal names**: Signal names referenced in `signal_weights` must match actual signal detector output keys
   ```bash
   # List all signal detector classes and their emitted keys
   rg "class.*SignalDetector" src/signals/
   ```

3. **Check edge types**: Edge types in `ontology.edges` must match types used in chain topology signals

### Step 7 — Deep mode output report

Present findings in this format:

```
=== Constitution Review — DEEP MODE ===

STRUCTURAL (from default mode):
  [same as default mode]

SEMANTIC DRIFT:
  [OK|WARN|ACTION] Ghost symbols: N found
    → <symbol> referenced in <doc> but not found in source
  [OK|WARN|ACTION] Docstring divergence: N found
    → <function> docstring says X but code does Y (in <file>:<line>)
  [OK|WARN|ACTION] Cross-doc inconsistency: N found
    → Stage N in <doc1> vs Stage M in <doc2> for same concept
  [OK|WARN|ACTION] Agent spec accuracy: N issues
    → <agent> references missing method <method>
  [OK|WARN|ACTION] Methodology sync: N issues
    → <strategy> in doc but not in YAML

RECOMMENDATIONS:
  1. [ACTION] Fix ghost symbol: remove or update reference to <symbol> in <doc>
     Why: <reason>
     How: <concrete edit>

  2. ...

DEEP AUDIT SUMMARY:
  Ghost symbols: N
  Docstring divergences: N
  Cross-doc inconsistencies: N
  Agent spec issues: N
  Methodology sync issues: N
  Docs requiring update: <list>
```

### Step 8 — Execute fixes (with user approval)

For each finding:
- **Ghost symbol**: Remove the reference or update it to the correct symbol name
- **Docstring divergence**: Update the docstring to match code, OR update code to match docstring (if docstring is the spec of record)
- **Cross-doc inconsistency**: Pick the correct value (source is ground truth) and update all docs
- **Agent spec issue**: Update the agent spec or create the missing method
- **Methodology sync**: Update docs or YAML to match

**Priority order**: Fix ghost symbols first (they're unambiguously wrong), then docstring divergence, then inconsistencies.

---

## Common Patterns

### "New signal files, no context doc update"
Session added `src/signals/graph/new_signal.py` but `.claude/context/signal-detection-graph.md` wasn't updated.
→ Action: Update the context doc to cover the new signal.

### "Bug fix revealed undocumented behavior"
Fixed a bug where Stage 4 reset state invisible to Stage 6.
→ Action: Add to Known Failure Modes in relevant Tier 3 doc. Consider Tier 2 anti-pattern. **Do NOT add the diagnostic prose to CLAUDE.md** — if the symptom→source mapping is novel, add one row to the "Known Failure Mode Index" routing table. The full diagnostic (root cause, fix, commit hash) belongs in the Tier 3 doc.

### "CLAUDE.md grew past 800 lines"
Convention creep from multiple sessions.
→ Action: Identify content that belongs in Tier 2 (domain-specific) or Tier 3 (detailed spec). Extract.

### "New directory with no agent trigger"
Added `src/explorations/` or similar.
→ Action: Only flag if it contains production code. Exploration/experiment directories don't need agents.

### "Pre-existing directory with no trigger match"
Full-tree coverage check found `src/some/dir/` with no trigger pattern in CLAUDE.md.
→ Action: If the directory contains actively-modified production code, add a trigger pattern. If it's stable/simple infrastructure, document the intentional gap (e.g., `-- no agent needed: stable infrastructure` comment in the trigger table). Don't create an agent just to fill a coverage hole — agents require observed failure patterns.

### "Tier 3 doc count outside benchmark"
Context docs count is above the expected range for the project stage (see `.claude/codified-context-principles.md` §Growth Benchmarks).
→ Action: Audit docs with only 1 reference first. These are candidates for consolidation — merge related docs or remove docs that describe dead/stable subsystems. Second pass: check for docs that duplicate content from other docs. The goal is not to hit the benchmark exactly, but to prevent undocumented growth.

### "Knowledge-to-code ratio below 1:4"
Documentation volume is thin relative to code size.
→ Action: Identify the largest undocumented subsystems (most LOC, least doc references). Prioritize subsystems that have caused debugging confusion or agent mistakes. Don't add docs for stable/simple code — the ratio is a signal, not a mandate.

### "Deep mode found ghost symbols after refactoring"
A refactoring (e.g., B11, vxz6) renamed or removed methods, but docs still reference the old names.
→ Action: For each ghost symbol, determine if it's a rename (update reference) or a removal (delete reference and update surrounding text to describe new behavior). Run default mode after fixes to ensure drift detector is clean.

### "Deep mode found docstring-code divergence"
A docstring describes behavior that was changed but the docstring wasn't updated.
→ Action: If the code change was intentional, update the docstring. If the docstring describes intended behavior that the code violates, the code has a bug — file a bead and fix the code, not the docstring.

---

## Anti-patterns

- **Don't create agents proactively** — only when failure patterns are observed
- **Don't add Tier 1 conventions for one-off needs** — only universal rules belong in CLAUDE.md
- **Don't duplicate** — if knowledge exists in Tier 3, reference it from Tier 2, don't copy it
- **Don't skip the drift check** — structural issues compound silently
- **Don't run deep mode on every session** — it's expensive. Use it for quarterly audits or when you suspect semantic drift
- **Don't add failure modes to CLAUDE.md** — the "Known Failure Mode Index" is a routing table, not a diagnostic repository. New failure modes go to Tier 3 doc "Known Failure Modes" sections or Tier 2 agent "Anti-patterns." Only add a row to the CLAUDE.md table if the symptom→source mapping is genuinely novel (no existing row covers it).
- **Don't fix ghost symbols by adding them to code** — docs should describe what exists, not invent what doesn't
