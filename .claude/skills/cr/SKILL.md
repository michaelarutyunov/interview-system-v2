---
name: cr
description: Use at session end to review the session's changes against the codified context constitution. Checks whether new agents, context docs, or CLAUDE.md updates are needed. Triggered by /cr or phrases like "constitution review", "check if context needs updating", "session review".
project: interview-system-v2
---

# Constitution Review (/cr)

## Overview

Session-end review against the project's codified context governance principles (`.claude/codified-context-principles.md`). Analyzes what changed this session and recommends Tier 1/2/3 updates.

## When to use

End of a work session, before committing and closing. Especially after:
- Adding new signals, strategies, or methodology files
- Modifying pipeline stages or contracts
- Fixing bugs that revealed missing documentation
- Touching subsystems for the first time
- Any multi-file change

## Process

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

# Complete trigger coverage: every src/ directory vs. trigger table
for dir in $(fd -t d --maxdepth 2 . src/ | sort); do
  covered=$(rg -c "$dir" CLAUDE.md 2>/dev/null || echo "0")
  echo "  $dir → $( [ \"$covered\" -gt 0 ] && echo 'covered' || echo 'UNCOVERED' )"
done

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
| **Agent coverage (full tree)** | Compare ALL `src/` directories against trigger table | Production directory with no trigger match |
| **Doc drift** | `check_doc_drift.py` output | Any `⚠  Doc drift detected` lines |
| **Cross-reference validation** | `check_doc_drift.py` output | Any `⚠  Cross-reference validation failed` lines (covers: missing agents, missing docs, missing source files, orphaned context docs) |
| **Doc mapping gaps** | Compare changed source files against `.claude/doc_mapping.yaml` | Source file with no mapping entry |
| **Growth benchmarks** | Compare Tier 2/3 counts against `.claude/codified-context-principles.md` §Growth Benchmarks table | Outside expected range for project stage |
| **Knowledge-to-code ratio** | `(CLAUDE.md lines + Σ agent lines + Σ context doc lines) / code LOC` | Below 1:4 (docs:code) |

### Step 3 — Semantic checks (judgment-based)

For each changed file, evaluate:

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
- Was a convention violated that wasn't written down?
- Is there a new subsystem ALL agents need to know about?
- → If yes: recommend adding a convention (but only if universal)

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

## Common Patterns

### "New signal files, no context doc update"
Session added `src/signals/graph/new_signal.py` but `.claude/context/signal-detection-graph.md` wasn't updated.
→ Action: Update the context doc to cover the new signal.

### "Bug fix revealed undocumented behavior"
Fixed a bug where Stage 4 reset state invisible to Stage 6.
→ Action: Add to Known Failure Modes in relevant Tier 3 doc. Consider Tier 2 anti-pattern.

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

## Anti-patterns

- **Don't create agents proactively** — only when failure patterns are observed
- **Don't add Tier 1 conventions for one-off needs** — only universal rules belong in CLAUDE.md
- **Don't duplicate** — if knowledge exists in Tier 3, reference it from Tier 2, don't copy it
- **Don't skip the drift check** — structural issues compound silently
