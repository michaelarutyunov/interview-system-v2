# Documentation Infrastructure Design
**Date:** 2026-04-06  
**Approach:** Codified Context Infrastructure (CCI) — adapted from arxiv:2602.20478v1  
**Status:** Approved, awaiting implementation plan

---

## Problem

Documentation across ~9,200 lines in 10 files has become difficult to maintain. The primary pain is **staleness drift**: source code changes faster than docs are updated, causing agents to silently operate on outdated specifications. Secondary pain (agent-side): discoverability — which doc covers this subsystem?

---

## Approach

**Approach B: Drift Detector + Light Restructuring**

Build a drift detector first (immediate value on the staleness problem), then restructure the largest docs into focused subsystem specs (reduces the cost of responding to detector warnings and improves agent discoverability as a side effect). Skip the MCP retrieval server until doc count exceeds ~25 files.

---

## Component 1: Doc Mapping Config

**File:** `.claude/doc_mapping.yaml`

Single source of truth for all file→doc relationships. Used by the drift detector, pre-commit hook, and CLAUDE.md trigger tables — all three stay in sync from this one file.

Structure: each entry maps one or more source glob patterns to a single doc owner.

```yaml
mappings:
  - sources: ["src/methodologies/scoring.py", "src/methodologies/registry.py"]
    doc: "docs/specs/strategy-scoring.md"
  - sources: ["src/services/turn_pipeline/stages/strategy_selection_stage.py"]
    doc: "docs/specs/strategy-selection.md"
  - sources: ["src/signals/graph/*.py"]
    doc: "docs/specs/signal-detection-graph.md"
  - sources: ["src/signals/llm/**/*.py"]
    doc: "docs/specs/signal-detection-llm.md"
  - sources: ["src/services/graph_service.py"]
    doc: "docs/specs/graph-dedup.md"
  - sources: ["src/services/canonical_slot_service.py"]
    doc: "docs/specs/canonical-slots.md"
  - sources: ["src/services/turn_pipeline/stages/*.py"]
    doc: "docs/specs/pipeline-contracts.md"
  - sources: ["src/services/turn_pipeline/context.py", "src/domain/models/pipeline_contracts.py"]
    doc: "docs/specs/pipeline-contracts.md"
  - sources: ["src/services/node_signal_detection_service.py", "src/signals/graph/node_signals.py"]
    doc: "docs/specs/node-state-tracker.md"
  - sources: ["config/methodologies/*.yaml"]
    doc: "docs/specs/strategy-scoring.md"
  - sources: ["src/services/extraction_service.py", "src/llm/prompts/extraction*.py"]
    doc: "docs/specs/extraction.md"
  - sources: ["src/methodologies/scoring.py"]
    doc: "docs/SYSTEM_DESIGN.md"
```

~25–30 total entries covering the highest-churn files.

---

## Component 2: Drift Detector

**File:** `scripts/check_doc_drift.py`

**Algorithm (option C — adaptive):** For each mapping, warn if the source file(s) have been modified more than once since the doc was last touched. One deferred update is fine; two is drift.

```
for each mapping:
    last_doc_commit = git log -1 --format=%H -- <doc>
    changes_since = git log --oneline <last_doc_commit>..HEAD -- <source_files>
    if len(changes_since) > 1:
        emit warning
```

**Output format:**
```
⚠ Doc drift detected:
  docs/specs/strategy-scoring.md — 3 source changes since last update
    → src/methodologies/scoring.py (2 commits ago)
    → config/methodologies/means_end_chain_v3_flex.yaml (1 commit ago)
```

**Behaviour:**
- Exits 0 always (warns, never blocks)
- Silent when no drift detected
- Reads mapping from `.claude/doc_mapping.yaml`

---

## Component 3: Hooks

**Session-start hook** (`~/.claude/hooks/session_start.sh` or `.claude/hooks/`):
- Runs `uv run python scripts/check_doc_drift.py`
- Output surfaces in session context at the start of every Claude Code session

**Pre-commit hook** (`.git/hooks/pre-commit`):
- Same script invocation
- Non-blocking (exits 0) — warns but does not prevent commit
- Catches drift when pre-commit is the last chance before a push

Both hooks invoke the same script; behaviour differences are handled by the hook wrappers, not the script.

---

## Component 4: Subsystem Specs

**Location:** `docs/specs/`

**Standard format** (every spec):
```markdown
# [Subsystem Name]

## Core Mechanics
Essential mental model — how it works, ~150–200 words.

## Correctness Requirements
Numbered list of invariants that must hold.
These are the things that break silently if violated.

## Symptom → Cause → Fix
| Symptom | Cause | Fix |
|---------|-------|-----|

## Key Files
Pointers to source — no duplication of code.
```

**Migration plan:**

| Current doc | Target specs | Notes |
|-------------|-------------|-------|
| `data_flow_paths.md` (1,654 lines) | `turn-count.md`, `strategy-selection.md`, `graph-mutation.md`, `traceability.md`, `canonical-slots.md`, `node-exhaustion.md` | 6 focused specs; Mermaid diagrams stay where relevant |
| `pipeline_contracts.md` (820 lines) | `pipeline-contracts.md` | One consolidated spec with stage-group sections |
| `signals_and_strategies.md` (1,010 lines) | `signal-detection-graph.md`, `signal-detection-llm.md`, `strategy-scoring.md` | Split by signal namespace |
| `extraction_and_graphs.md` (1,336 lines) | `extraction.md`, `graph-dedup.md`, `canonical-slots.md` | 3 focused specs |
| `NodeStateTracker_mutation.md` (308 lines) | `node-state-tracker.md` | Already well-scoped; light reformat only |
| `SYSTEM_DESIGN.md`, `API.md`, `DEVELOPMENT.md`, `interview_ai_simulation.md`, `signals_moderator_guide.md` | Unchanged | Architecture/ops/user-facing docs — not subsystem specs |

**Target count:** ~16–20 specs  
**Authorship:** Agent-drafted under developer direction, ~5 min review per spec. Source material: existing docs + current source code.

**Prerequisite:** Fix D1→D2 architecture description in `SYSTEM_DESIGN.md` before drafting specs (strategy selection section references `select_strategy_and_focus()` / D1; should reflect `rank_strategy_node_pairs()` / D2 joint scoring).

---

## Component 5: CLAUDE.md Additions

Three additions to the project-level `CLAUDE.md`:

### 5a: Trigger tables
```markdown
## Documentation Routing

### Before editing — read first
| Editing | Read |
|---------|------|
| `src/methodologies/scoring.py`, `src/methodologies/registry.py`, `config/methodologies/*.yaml` | `docs/specs/strategy-scoring.md` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py` | `docs/specs/strategy-selection.md` |
| `src/signals/graph/*.py` | `docs/specs/signal-detection-graph.md` |
| `src/signals/llm/**/*.py` | `docs/specs/signal-detection-llm.md` |
| `src/services/graph_service.py` | `docs/specs/graph-dedup.md` |
| `src/services/canonical_slot_service.py` | `docs/specs/canonical-slots.md` |
| Any pipeline stage (`stages/*.py`) | `docs/specs/pipeline-contracts.md` |
| `src/services/node_signal_detection_service.py` | `docs/specs/node-state-tracker.md` |

### After editing — update
Same mappings as above — symmetric.
```

### 5b: Freshness policy
```markdown
## Doc Freshness Policy
After editing any mapped source file: update the corresponding spec before or in the same commit.
One deferred update is acceptable (the drift detector allows it).
Two commits without a doc update triggers a warning.
```

### 5c: Known failure modes
```markdown
## Known Failure Modes
- **Stage ordering (Stage 4 < Stage 6):** Any state reset in Stage 4 (GraphUpdateStage) is invisible to Stage 6 signal detectors. Do not reset signal-relevant state in early stages.
- **Stale specs:** Agents trust specs absolutely. An outdated spec produces silent failures — wrong code that passes review. The drift detector warns but does not prevent this. When in doubt, verify spec against source.
- **Canonical slot timing:** Canonical slots are only `active` after `support_count >= canonical_min_support_nodes` (default 2). Signals depending on canonical data return empty/zero on first occurrence.
```

---

## Sequencing

1. **Fix `SYSTEM_DESIGN.md`** D1→D2 correction (prerequisite)
2. **Build drift detector + hooks** — immediate value, no doc restructuring required yet
3. **Add trigger tables + freshness policy + known failure modes to CLAUDE.md**
4. **Draft subsystem specs** — agent-assisted, one subsystem at a time, starting with highest-churn areas (signals, strategy scoring, pipeline contracts)
5. **Retire migrated sections** from source docs once specs are validated
6. **MCP retrieval server** — defer until spec count > 25

---

## Out of Scope

- MCP retrieval service (premature at current doc count)
- Semantic drift detection (keyword git-log approach is sufficient)
- Blocking pre-commit (non-blocking by design — discipline, not enforcement)
- Restructuring `SYSTEM_DESIGN.md`, `API.md`, `DEVELOPMENT.md` (not subsystem specs)
