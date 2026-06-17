# Documentation Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a drift-detecting documentation infrastructure that warns when source code changes outpace doc updates, then restructure large narrative docs into focused subsystem specs.

**Architecture:** A YAML mapping config (`.claude/doc_mapping.yaml`) is the single source of truth for file→doc relationships. A Python drift detector script reads this config, queries git history, and warns when a doc has fallen more than one commit behind its source files. Two hooks (session-start via Claude Code settings, pre-commit via git) invoke the same script. Existing large docs are then migrated into focused subsystem specs in `docs/specs/` using a standardised format.

**Tech Stack:** Python 3.12, PyYAML, subprocess (git), pytest, Claude Code hooks (settings.json), git pre-commit hook.

---

## Phase 1: Drift Detector Tooling

### Task 1: Fix SYSTEM_DESIGN.md D1→D2 architecture description

**Files:**
- Modify: `docs/SYSTEM_DESIGN.md` (Strategy Selection Flow section, ~line 324)

- [ ] **Step 1: Update the Strategy Selection Flow section**

Replace the current D1 description with the correct D2 joint scoring description. Find the section titled `### Strategy Selection Flow` and replace its content:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/SYSTEM_DESIGN.md
git commit -m "docs: fix strategy selection description from D1 to D2 joint scoring"
```

---

### Task 2: Create doc mapping config

**Files:**
- Create: `.claude/doc_mapping.yaml`

- [ ] **Step 1: Create the mapping file**

```yaml
# .claude/doc_mapping.yaml
# Source-of-truth for file→doc relationships.
# Used by: scripts/check_doc_drift.py, pre-commit hook, CLAUDE.md trigger tables.
#
# Each entry maps one or more source glob patterns to a single doc owner.
# Drift is detected when a source file changes >1 time since the doc was last touched.

mappings:
  - sources:
      - "src/methodologies/scoring.py"
      - "src/methodologies/registry.py"
      - "config/methodologies/*.yaml"
    doc: "docs/signals_and_strategies.md"

  - sources:
      - "src/services/turn_pipeline/stages/strategy_selection_stage.py"
      - "src/services/methodology_strategy_service.py"
    doc: "docs/signals_and_strategies.md"

  - sources:
      - "src/signals/graph/*.py"
      - "src/services/node_signal_detection_service.py"
      - "src/services/global_signal_detection_service.py"
    doc: "docs/signals_and_strategies.md"

  - sources:
      - "src/signals/llm/signals/*.py"
      - "src/signals/llm/prompts/signals.md"
    doc: "docs/signals_and_strategies.md"

  - sources:
      - "src/services/graph_service.py"
    doc: "docs/extraction_and_graphs.md"

  - sources:
      - "src/services/canonical_slot_service.py"
      - "src/services/turn_pipeline/stages/slot_discovery_stage.py"
    doc: "docs/extraction_and_graphs.md"

  - sources:
      - "src/services/extraction_service.py"
      - "src/services/turn_pipeline/stages/extraction_stage.py"
      - "src/llm/prompts/extraction.py"
    doc: "docs/extraction_and_graphs.md"

  - sources:
      - "src/services/turn_pipeline/stages/*.py"
      - "src/services/turn_pipeline/context.py"
      - "src/domain/models/pipeline_contracts.py"
    doc: "docs/pipeline_contracts.md"

  - sources:
      - "src/services/node_signal_detection_service.py"
      - "src/core/node_state_tracker.py"
    doc: "docs/NodeStateTracker_mutation.md"

  - sources:
      - "src/methodologies/scoring.py"
      - "src/services/methodology_strategy_service.py"
    doc: "docs/SYSTEM_DESIGN.md"

  - sources:
      - "src/main.py"
      - "src/routers/*.py"
    doc: "docs/API.md"

  - sources:
      - "src/services/synthetic_service.py"
      - "src/llm/prompts/synthetic.py"
      - "scripts/run_simulation.py"
      - "config/personas/*.yaml"
    doc: "docs/interview_ai_simulation.md"
```

- [ ] **Step 2: Verify source paths exist** (spot-check a few)

```bash
ls src/methodologies/scoring.py src/services/graph_service.py src/signals/llm/signals/ src/core/node_state_tracker.py 2>&1
```

If any path is missing, update the mapping to match the actual path before proceeding.

- [ ] **Step 3: Commit**

```bash
git add .claude/doc_mapping.yaml
git commit -m "chore: add doc mapping config for drift detection"
```

---

### Task 3: Write tests for the drift detector

**Files:**
- Create: `tests/test_check_doc_drift.py`

- [ ] **Step 1: Write the tests**

```python
# tests/test_check_doc_drift.py
"""Tests for the doc drift detector (scripts/check_doc_drift.py).

We test the core logic functions in isolation by patching git calls.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# We'll import these after Task 4 implements them.
# These tests define the contract first.
from scripts.check_doc_drift import (
    load_mapping,
    get_last_doc_commit,
    get_source_changes_since,
    check_drift,
    DriftWarning,
)


# --- load_mapping ---

def test_load_mapping_returns_list_of_entries(tmp_path):
    config = tmp_path / "doc_mapping.yaml"
    config.write_text("""
mappings:
  - sources: ["src/foo.py"]
    doc: "docs/foo.md"
  - sources: ["src/bar/*.py"]
    doc: "docs/bar.md"
""")
    result = load_mapping(config)
    assert len(result) == 2
    assert result[0]["sources"] == ["src/foo.py"]
    assert result[0]["doc"] == "docs/foo.md"


def test_load_mapping_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_mapping(tmp_path / "nonexistent.yaml")


# --- get_last_doc_commit ---

def test_get_last_doc_commit_returns_hash():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = "abc1234\n"
        result = get_last_doc_commit("docs/foo.md", repo_root=Path("."))
    assert result == "abc1234"
    mock_git.assert_called_once_with(
        ["git", "log", "-1", "--format=%H", "--", "docs/foo.md"],
        cwd=Path(".")
    )


def test_get_last_doc_commit_returns_none_for_untracked_doc():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = ""
        result = get_last_doc_commit("docs/new.md", repo_root=Path("."))
    assert result is None


# --- get_source_changes_since ---

def test_get_source_changes_since_returns_commit_list():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = "def5678 fix something\nabc1234 another fix\n"
        result = get_source_changes_since(
            since_commit="abc1234",
            source_globs=["src/foo.py"],
            repo_root=Path(".")
        )
    assert len(result) == 2
    assert result[0] == "def5678 fix something"


def test_get_source_changes_since_returns_empty_when_no_changes():
    with patch("scripts.check_doc_drift.run_git") as mock_git:
        mock_git.return_value = ""
        result = get_source_changes_since(
            since_commit="abc1234",
            source_globs=["src/foo.py"],
            repo_root=Path(".")
        )
    assert result == []


def test_get_source_changes_since_returns_empty_when_no_prior_commit():
    result = get_source_changes_since(
        since_commit=None,
        source_globs=["src/foo.py"],
        repo_root=Path(".")
    )
    assert result == []


# --- check_drift ---

def test_check_drift_no_warning_when_one_change():
    """One change since last doc update is acceptable — not drift."""
    mapping = [{"sources": ["src/foo.py"], "doc": "docs/foo.md"}]
    with patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc, \
         patch("scripts.check_doc_drift.get_source_changes_since") as mock_src:
        mock_doc.return_value = "abc1234"
        mock_src.return_value = ["def5678 one change"]
        warnings = check_drift(mapping, repo_root=Path("."))
    assert warnings == []


def test_check_drift_warning_when_two_or_more_changes():
    """Two or more changes without a doc update triggers a warning."""
    mapping = [{"sources": ["src/foo.py"], "doc": "docs/foo.md"}]
    with patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc, \
         patch("scripts.check_doc_drift.get_source_changes_since") as mock_src:
        mock_doc.return_value = "abc1234"
        mock_src.return_value = ["def5678 second change", "ccc9999 first change"]
        warnings = check_drift(mapping, repo_root=Path("."))
    assert len(warnings) == 1
    w = warnings[0]
    assert isinstance(w, DriftWarning)
    assert w.doc == "docs/foo.md"
    assert len(w.changes) == 2


def test_check_drift_no_warning_when_doc_never_committed():
    """Untracked doc (None commit) skips drift check — can't compare."""
    mapping = [{"sources": ["src/foo.py"], "doc": "docs/new.md"}]
    with patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc:
        mock_doc.return_value = None
        warnings = check_drift(mapping, repo_root=Path("."))
    assert warnings == []


def test_check_drift_multiple_mappings():
    """Each mapping checked independently."""
    mapping = [
        {"sources": ["src/foo.py"], "doc": "docs/foo.md"},
        {"sources": ["src/bar.py"], "doc": "docs/bar.md"},
    ]
    def mock_src(since_commit, source_globs, repo_root):
        if "src/foo.py" in source_globs:
            return ["c1 change", "c2 change"]  # drift
        return ["c3 change"]  # no drift

    with patch("scripts.check_doc_drift.get_last_doc_commit") as mock_doc, \
         patch("scripts.check_doc_drift.get_source_changes_since", side_effect=mock_src):
        mock_doc.return_value = "abc1234"
        warnings = check_drift(mapping, repo_root=Path("."))

    assert len(warnings) == 1
    assert warnings[0].doc == "docs/foo.md"
```

- [ ] **Step 2: Run tests to verify they fail (script not yet written)**

```bash
uv run pytest tests/test_check_doc_drift.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError` — `scripts.check_doc_drift` doesn't exist yet.

- [ ] **Step 3: Commit the tests**

```bash
git add tests/test_check_doc_drift.py
git commit -m "test: add drift detector tests (red)"
```

---

### Task 4: Implement the drift detector

**Files:**
- Create: `scripts/check_doc_drift.py`

- [ ] **Step 1: Implement the script**

```python
#!/usr/bin/env python3
"""Doc drift detector.

Warns when source files have been modified more than once since their
corresponding doc was last updated. One deferred update is acceptable;
two or more signals drift.

Usage:
    uv run python scripts/check_doc_drift.py [--repo-root PATH] [--config PATH]

Exit code: always 0 (warns but never blocks).
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class DriftWarning:
    doc: str
    changes: list[str]  # list of "hash message" strings


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def run_git(cmd: list[str], cwd: Path) -> str:
    """Run a git command and return stdout. Returns empty string on error."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def get_last_doc_commit(doc: str, repo_root: Path) -> str | None:
    """Return the hash of the last commit that touched `doc`, or None."""
    output = run_git(["git", "log", "-1", "--format=%H", "--", doc], cwd=repo_root)
    result = output.strip()
    return result if result else None


def get_source_changes_since(
    since_commit: str | None,
    source_globs: list[str],
    repo_root: Path,
) -> list[str]:
    """Return commits that touched any source glob since `since_commit`.

    Returns empty list if since_commit is None (doc never committed).
    Each entry is "hash short-message".
    """
    if since_commit is None:
        return []

    cmd = [
        "git", "log",
        "--oneline",
        f"{since_commit}..HEAD",
        "--",
        *source_globs,
    ]
    output = run_git(cmd, cwd=repo_root)
    lines = [line for line in output.splitlines() if line.strip()]
    return lines


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_mapping(config_path: Path) -> list[dict]:
    """Load and return the mappings list from doc_mapping.yaml."""
    if not config_path.exists():
        raise FileNotFoundError(f"Mapping config not found: {config_path}")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("mappings", [])


def check_drift(
    mapping: list[dict],
    repo_root: Path,
) -> list[DriftWarning]:
    """Check all mappings for drift. Returns list of DriftWarning."""
    warnings: list[DriftWarning] = []

    for entry in mapping:
        doc = entry["doc"]
        sources = entry["sources"]

        last_doc_commit = get_last_doc_commit(doc, repo_root)
        if last_doc_commit is None:
            # Doc not yet committed — skip
            continue

        changes = get_source_changes_since(last_doc_commit, sources, repo_root)

        # Allow one deferred update; two or more is drift
        if len(changes) > 1:
            warnings.append(DriftWarning(doc=doc, changes=changes))

    return warnings


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_warnings(warnings: list[DriftWarning]) -> str:
    if not warnings:
        return ""
    lines = ["⚠  Doc drift detected:"]
    for w in warnings:
        lines.append(f"  {w.doc} — {len(w.changes)} source changes since last update")
        for change in w.changes:
            lines.append(f"    → {change}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check for doc drift.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to doc_mapping.yaml (default: <repo-root>/.claude/doc_mapping.yaml)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config or repo_root / ".claude" / "doc_mapping.yaml"

    try:
        mapping = load_mapping(config_path)
    except FileNotFoundError as e:
        print(f"check_doc_drift: {e}", file=sys.stderr)
        sys.exit(0)

    warnings = check_drift(mapping, repo_root)
    output = format_warnings(warnings)
    if output:
        print(output)

    sys.exit(0)  # Always exit 0 — warn, never block


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_check_doc_drift.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Run the script manually to verify it works against the actual repo**

```bash
uv run python scripts/check_doc_drift.py
```

Expected: either silent (no drift) or drift warnings for docs that have fallen behind. Either is correct — it means the script runs without errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/check_doc_drift.py
git commit -m "feat: add doc drift detector script"
```

---

### Task 5: Wire up session-start hook

**Files:**
- Modify: `.claude/settings.local.json` (add hooks entry — or create `.claude/settings.json` if project-level settings don't yet have hooks)

Note: Claude Code hooks live in the project's `.claude/settings.json` (checked into git, shared) or `settings.local.json` (local only). We use `settings.local.json` since it already exists, but the hook command itself is repo-relative so it works for any checkout.

- [ ] **Step 1: Read the current settings.local.json hooks section**

```bash
python3 -c "
import json
with open('.claude/settings.local.json') as f:
    d = json.load(f)
print(json.dumps(d.get('hooks', 'NO HOOKS KEY'), indent=2))
"
```

Note the current structure before editing.

- [ ] **Step 2: Add the session-start hook**

Open `.claude/settings.local.json` and add (or merge into) the `hooks` key:

```json
"hooks": {
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "cd \"$CLAUDE_PROJECT_DIR\" && uv run python scripts/check_doc_drift.py --repo-root \"$CLAUDE_PROJECT_DIR\" 2>/dev/null || true"
        }
      ]
    }
  ]
}
```

If a `SessionStart` array already exists, append to it rather than replacing.

- [ ] **Step 3: Verify the hook runs (start a new session or trigger manually)**

```bash
uv run python scripts/check_doc_drift.py --repo-root .
```

Expected: silent or drift warnings — no Python errors.

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.local.json
git commit -m "chore: add session-start doc drift hook"
```

---

### Task 6: Wire up pre-commit hook

**Files:**
- Modify: `.git/hooks/pre-commit` (append drift check after existing beads shim)

Note: `.git/hooks/pre-commit` is currently a beads shim. We append to it rather than replacing.

- [ ] **Step 1: Append drift check to pre-commit hook**

```bash
cat >> .git/hooks/pre-commit << 'EOF'

# Doc drift check (warns, never blocks)
if command -v uv >/dev/null 2>&1; then
    uv run python scripts/check_doc_drift.py --repo-root "$(git rev-parse --show-toplevel)" 2>/dev/null || true
fi
EOF
```

- [ ] **Step 2: Verify the hook is still executable and runs**

```bash
chmod +x .git/hooks/pre-commit
bash .git/hooks/pre-commit
```

Expected: beads shim output (normal), then drift output (silent or warnings) — no errors.

- [ ] **Step 3: Note — git hooks are not committed**

`.git/hooks/` is not tracked by git. Document the setup in `docs/DEVELOPMENT.md` under a "Hooks Setup" section:

```markdown
## Hooks Setup

The pre-commit hook includes a doc drift detector. After cloning, append it manually:

```bash
cat >> .git/hooks/pre-commit << 'EOF'

# Doc drift check (warns, never blocks)
if command -v uv >/dev/null 2>&1; then
    uv run python scripts/check_doc_drift.py --repo-root "$(git rev-parse --show-toplevel)" 2>/dev/null || true
fi
EOF
```
```

- [ ] **Step 4: Commit**

```bash
git add docs/DEVELOPMENT.md
git commit -m "docs: add hooks setup instructions for drift detector"
```

---

### Task 7: Update CLAUDE.md with trigger tables and freshness policy

**Files:**
- Modify: `CLAUDE.md` (project-level, in repo root)

- [ ] **Step 1: Add Documentation Routing section**

Find the `## Common Tasks` section in `CLAUDE.md` and insert the following block immediately before it:

```markdown
## Documentation Routing

Run `scripts/check_doc_drift.py` any time to check for drift. The session-start and pre-commit hooks do this automatically.

### Before editing — read first
| Editing | Read first |
|---------|-----------|
| `src/methodologies/scoring.py`, `src/methodologies/registry.py`, `config/methodologies/*.yaml` | `docs/signals_and_strategies.md` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py`, `src/services/methodology_strategy_service.py` | `docs/signals_and_strategies.md` |
| `src/signals/graph/*.py`, `src/services/*signal_detection_service.py` | `docs/signals_and_strategies.md` |
| `src/signals/llm/signals/*.py` | `docs/signals_and_strategies.md` |
| `src/services/graph_service.py` | `docs/extraction_and_graphs.md` |
| `src/services/canonical_slot_service.py` | `docs/extraction_and_graphs.md` |
| `src/services/extraction_service.py` | `docs/extraction_and_graphs.md` |
| Any pipeline stage (`stages/*.py`), `context.py`, `pipeline_contracts.py` | `docs/pipeline_contracts.md` |
| `src/core/node_state_tracker.py`, `src/services/node_signal_detection_service.py` | `docs/NodeStateTracker_mutation.md` |
| `src/main.py`, `src/routers/*.py` | `docs/API.md` |

### After editing — update the same doc
Same mappings apply symmetrically. Update the corresponding doc in the same commit or the commit immediately after.

### Freshness policy
One deferred update is acceptable — the drift detector allows it. Two commits without a doc update triggers a warning. When you see a warning, update the doc before continuing.

---

## Known Failure Modes

- **Stage ordering (Stage 4 < Stage 6):** Any state reset in Stage 4 (GraphUpdateStage) is invisible to Stage 6 signal detectors. Do not reset signal-relevant state in early stages. See `docs/NodeStateTracker_mutation.md`.
- **Stale specs:** Agents trust docs absolutely. An outdated doc produces silent failures — correct-looking code based on wrong assumptions. The drift detector warns but does not prevent this. When in doubt, verify the doc against source.
- **Canonical slot timing:** Canonical slots are only `active` after `support_count >= canonical_min_support_nodes` (default 2). Signals depending on canonical data return empty/zero on first occurrence.
- **`select_strategy_and_focus()` is D2:** The current architecture uses `rank_strategy_node_pairs()` for joint strategy-node scoring. Any doc or code referencing the old single-strategy D1 flow is outdated.

---
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add documentation routing tables and known failure modes to CLAUDE.md"
```

---

## Phase 2: Subsystem Specs

> **Note:** Each task in Phase 2 follows the same pattern: draft the spec from the existing doc + source code, validate it matches current implementation, retire the migrated section from the source doc. Tasks can be done in any order.

### Task 8: Create spec for signal detection (graph + node signals)

**Files:**
- Create: `docs/specs/signal-detection-graph.md`
- Modify: `docs/signals_and_strategies.md` (remove migrated content, add pointer)
- Modify: `.claude/doc_mapping.yaml` (update doc pointer for graph signal mappings)

- [ ] **Step 1: Draft the spec**

Read `docs/signals_and_strategies.md` (graph signal sections) and `src/signals/graph/node_signals.py` to verify current implementation. Then create `docs/specs/signal-detection-graph.md`:

```markdown
# Signal Detection: Graph & Node Signals

## Core Mechanics

Graph signals are computed from `GraphState` and `NodeStateTracker` data — no LLM calls involved. They split into two scopes:

**Global graph signals** (`graph.*`) reflect the interview-level knowledge graph: `node_count`, `max_depth`, `orphan_count`, `chain_completion.ratio`, `chain_completion.has_complete`, `canonical_concept_count`, `canonical_edge_density`, `canonical_exhaustion_score`. Computed in `GlobalSignalDetectionService` from `graph_state` and `canonical_graph_state`.

**Node-level signals** (`graph.node.*`, `technique.node.*`, `meta.node.*`) are computed per tracked node from `NodeStateTracker`. All node signal detectors inherit `NodeSignalDetector` and return `Dict[node_id, value]`. They are aggregated by `NodeSignalDetectionService`.

Signal values are matched against YAML weight keys using threshold bins: `.low` (≤0.25), `.mid` (0.26–0.75), `.high` (>0.75) for continuous signals; `.true`/`.false` for booleans; named categories for categoricals.

## Correctness Requirements

1. Node signal detectors must return an entry for **every** node in `graph_state` — absent entries are treated as zero, not as "not applicable".
2. `graph.node.exhaustion_score` must be in range [0.0, 1.0]. Inputs: `turns_since_last_yield` (max 10), `current_focus_streak` (max 5), `shallow_response_ratio` (from `all_response_depths`).
3. `graph.node.focus_streak` resets only on focus **change** in `NodeStateTracker.update_focus()` — never in `record_yield()`. Resetting in `record_yield()` causes the streak to appear 0 at signal detection time (Stage 4 runs before Stage 6).
4. `meta.node.opportunity` combines `graph.node.exhausted`, `graph.node.focus_streak`, and `llm.response_depth` — it depends on LLM signals being detected first. If LLM signals are unavailable, it falls back to graph signals only.
5. Boolean weight keys must use `.true` or `.false` suffix (e.g., `graph.node.exhausted.true: -1.0`).

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `focus_streak` signal always 0 | `record_yield()` resets `current_focus_streak` before Stage 6 reads it | Remove reset from `record_yield()`; streak resets only in `update_focus()` on focus change |
| Node signals missing for some nodes | Detector not iterating all tracked nodes | Use `self._get_all_node_states()` in `NodeSignalDetector.detect()` |
| `exhaustion_score` not growing | `turns_since_last_yield` not ticking for unfocused nodes | Ensure `update_focus()` increments `turns_since_last_yield` for ALL nodes, not just current focus |
| Signal weight key never matching | Threshold bin wrong (e.g., `exhaustion_score.medium` instead of `.mid`) | Valid bins: `.low`, `.mid`, `.high` for continuous; `.true`/`.false` for bool |

## Key Files

- `src/signals/graph/node_signals.py` — all node signal detector classes
- `src/signals/graph/node_base.py` — `NodeSignalDetector` base class
- `src/signals/graph/__init__.py` — `__all__` export list
- `src/services/node_signal_detection_service.py` — aggregation service
- `src/services/global_signal_detection_service.py` — global graph signals
- `src/core/node_state_tracker.py` — `NodeState`, `NodeStateTracker`
```

- [ ] **Step 2: Update the doc mapping to point to the new spec**

In `.claude/doc_mapping.yaml`, update the graph signal mappings to point to `docs/specs/signal-detection-graph.md` instead of `docs/signals_and_strategies.md`.

- [ ] **Step 3: Add a pointer in the source doc**

In `docs/signals_and_strategies.md`, replace the graph signal sections with:
```markdown
## Graph & Node Signals

> Moved to [`docs/specs/signal-detection-graph.md`](specs/signal-detection-graph.md)
```

- [ ] **Step 4: Commit**

```bash
git add docs/specs/signal-detection-graph.md docs/signals_and_strategies.md .claude/doc_mapping.yaml
git commit -m "docs: extract graph signal detection spec"
```

---

### Task 9: Create spec for LLM signal detection

**Files:**
- Create: `docs/specs/signal-detection-llm.md`
- Modify: `docs/signals_and_strategies.md` (remove migrated LLM signal content, add pointer)
- Modify: `.claude/doc_mapping.yaml`

- [ ] **Step 1: Draft the spec**

Read `docs/signals_and_strategies.md` (LLM signal sections) and `src/signals/llm/signals/` to verify. Create `docs/specs/signal-detection-llm.md`:

```markdown
# Signal Detection: LLM Signals

## Core Mechanics

All 6 LLM signals are detected in a **single batched API call** via `LLMBatchDetector` (Stage 6). Rubrics are loaded from `src/signals/llm/prompts/signals.md` — each rubric defines a 1–5 integer scale. Adding a signal requires adding a rubric entry there AND a detector class.

Signals use the zero-boilerplate `@llm_signal` decorator:
```python
@llm_signal(signal_name="llm.engagement", rubric_key="engagement", ...)
class EngagementSignal(BaseLLMSignal):
    pass
```

**Categorical signal** (`llm.response_depth`): Integer 1–5 → named category (surface/shallow/moderate/deep/rich). Matched via exact category name in YAML weights (e.g., `llm.response_depth.surface: 0.8`).

**Continuous signals** (valence, certainty, specificity, engagement, intellectual_engagement): Integer 1–5 → float [0,1] via `(score-1)/4`. Matched via threshold bins: `.low` (≤0.25), `.mid` (0.26–0.75), `.high` (>0.75).

`global_response_trend` is a session-level aggregate derived from the last N `response_depth` values, not a single-turn LLM call.

## Correctness Requirements

1. `rubric_key` in the detector class must exactly match the key in `signals.md`. Mismatch causes a KeyError at detection time.
2. The `@llm_signal` decorator handles all plumbing. Class body must be `pass` — no custom `detect()` override.
3. Every new signal class must be added to `__all__` in `src/signals/llm/signals/__init__.py` and imported there.
4. Every new signal must be listed in the methodology YAML under `signals: llm:` to be active. Detector classes not listed in YAML are never called.
5. Continuous signal values are always in [0,1]. YAML weight keys using absolute integers (e.g., `llm.engagement: 3`) will never match — use threshold bins.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Signal always returns 0 or never fires | Not listed in methodology YAML `signals: llm:` | Add signal name to YAML |
| `KeyError` on rubric key at runtime | `rubric_key` doesn't match key in `signals.md` | Align the two — check exact spelling |
| New signal class not detected | Missing from `__all__` in `__init__.py` | Add to `__all__` and import |
| Weight key never matches continuous signal | Using wrong bin name (`.medium` vs `.mid`) | Valid bins: `.low`, `.mid`, `.high` |

## Key Files

- `src/signals/llm/signals/*.py` — one file per signal
- `src/signals/llm/signals/__init__.py` — exports
- `src/signals/llm/prompts/signals.md` — rubric definitions
- `src/signals/llm/decorators.py` (or similar) — `@llm_signal` decorator
- `src/services/global_signal_detection_service.py` — invokes `LLMBatchDetector`
```

- [ ] **Step 2: Update doc mapping and add pointer in source doc** (same pattern as Task 8)

- [ ] **Step 3: Commit**

```bash
git add docs/specs/signal-detection-llm.md docs/signals_and_strategies.md .claude/doc_mapping.yaml
git commit -m "docs: extract LLM signal detection spec"
```

---

### Task 10: Create spec for strategy scoring

**Files:**
- Create: `docs/specs/strategy-scoring.md`
- Modify: `docs/signals_and_strategies.md` (retire remaining content, replace with index of specs)

- [ ] **Step 1: Draft the spec**

Read `src/methodologies/scoring.py` and the strategy scoring sections of `docs/signals_and_strategies.md`. Create `docs/specs/strategy-scoring.md`:

```markdown
# Strategy Scoring

## Core Mechanics

`rank_strategy_node_pairs()` in `src/methodologies/scoring.py` scores all `(strategy, node_id)` pairs in a single pass and returns ranked `ScoredCandidate` objects.

```python
final_score = (base_score * phase_multiplier) + phase_bonus
```

- **base_score**: Weighted sum of matched signals from strategy `signal_weights` in YAML. Each weight key is a compound signal identifier: `llm.response_depth.surface` (categorical), `graph.node.exhaustion_score.low` (threshold bin), `graph.chain_completion.has_complete.false` (boolean negation).
- **phase_multiplier**: From `config.phases[phase].signal_weights[strategy]` — default 1.0. Multiplicative.
- **phase_bonus**: From `config.phases[phase].phase_bonuses[strategy]` — default 0.0. Additive, applied after multiplication.

Node-scoped signal weight keys (`graph.node.*`, `technique.node.*`, `meta.node.*`) are automatically partitioned from strategy-level weights and applied at the node scoring level. Strategy-level keys (`graph.*`, `llm.*`, `temporal.*`, `meta.interview.*`) are applied uniformly across all nodes for that strategy.

`ScoredCandidate` includes `signal_contributions: dict[str, float]` for full observability — every matched weight is recorded with its contribution.

## Correctness Requirements

1. Phase multiplier and bonus are applied **after** base scoring — they scale the result, not individual signal weights.
2. Node-scoped weight keys must use namespaces `graph.node.*`, `technique.node.*`, or `meta.node.*`. Any other namespace is treated as strategy-level and applied before node partitioning.
3. Negative weights are valid and encouraged (e.g., `temporal.strategy_repetition_count: -0.3` for diversity penalties).
4. Strategy names in `phases[phase].signal_weights` and `phases[phase].phase_bonuses` must match strategy names defined in the `strategies:` list. Registry validation raises at load time if they don't.
5. Strategies with `node_binding: none` receive a single score (no node dimension). Strategies with `node_binding: required` (default) receive one score per tracked node.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Strategy never selected despite high base score | Phase multiplier of 0 (or very low) in current phase | Check `phases[current_phase].signal_weights[strategy_name]` |
| Phase bonus not applying | Strategy name typo in `phase_bonuses` key | Registry validation catches this at load; check logs for validation errors |
| Node-level signal weight treated as strategy-level | Wrong namespace prefix | Use `graph.node.*` not `graph.*` for per-node weights |
| All strategies scoring equally | No signal weights defined or no signals firing | Check methodology YAML `signal_weights` and verify signals are listed in `signals:` section |

## Key Files

- `src/methodologies/scoring.py` — `rank_strategy_node_pairs()`, `score_strategy()`
- `src/methodologies/registry.py` — YAML loading + validation
- `config/methodologies/*.yaml` — strategy definitions, signal weights, phase config
- `src/services/methodology_strategy_service.py` — orchestrates signal detection + scoring
```

- [ ] **Step 2: Replace `docs/signals_and_strategies.md` with an index**

Once all three signal/scoring specs exist, replace the content of `docs/signals_and_strategies.md` with:

```markdown
# Signals and Strategies

> This document has been split into focused subsystem specs.

| Topic | Spec |
|-------|------|
| Graph & node signal detection | [`docs/specs/signal-detection-graph.md`](specs/signal-detection-graph.md) |
| LLM signal detection | [`docs/specs/signal-detection-llm.md`](specs/signal-detection-llm.md) |
| Strategy scoring (joint strategy-node) | [`docs/specs/strategy-scoring.md`](specs/strategy-scoring.md) |
```

- [ ] **Step 3: Commit**

```bash
git add docs/specs/strategy-scoring.md docs/signals_and_strategies.md .claude/doc_mapping.yaml
git commit -m "docs: extract strategy scoring spec; retire signals_and_strategies.md to index"
```

---

### Task 11: Create pipeline contracts spec

**Files:**
- Create: `docs/specs/pipeline-contracts.md`
- Modify: `docs/pipeline_contracts.md` (replace with index pointer)
- Modify: `.claude/doc_mapping.yaml`

- [ ] **Step 1: Draft the spec**

Read `docs/pipeline_contracts.md` and `src/services/turn_pipeline/context.py`. Create `docs/specs/pipeline-contracts.md` using the standard format. Include:

- Core mechanics: PipelineContext as accumulator, Pydantic contracts, ordering enforcement via RuntimeError
- The stage→contract table (all 10 stages + their output contracts)
- Correctness requirements: freshness guarantees, ordering, no stage reading its own output
- Symptom→Cause→Fix: RuntimeError on premature access, missing contract field, type mismatch
- Key files

- [ ] **Step 2: Replace `docs/pipeline_contracts.md` with index pointer**

```markdown
# Pipeline Contracts

> Moved to [`docs/specs/pipeline-contracts.md`](specs/pipeline-contracts.md)
```

- [ ] **Step 3: Update doc mapping and commit**

```bash
git add docs/specs/pipeline-contracts.md docs/pipeline_contracts.md .claude/doc_mapping.yaml
git commit -m "docs: extract pipeline contracts spec"
```

---

### Task 12: Create extraction and graph specs

**Files:**
- Create: `docs/specs/extraction.md`
- Create: `docs/specs/graph-dedup.md`
- Create: `docs/specs/canonical-slots.md`
- Modify: `docs/extraction_and_graphs.md` (replace with index pointer)
- Modify: `.claude/doc_mapping.yaml`

- [ ] **Step 1: Draft extraction spec**

Read `docs/extraction_and_graphs.md` (extraction sections) and `src/services/extraction_service.py`. Create `docs/specs/extraction.md` covering: LLM-based concept/relationship extraction, the extraction prompt structure, output schema (concepts with node_type, relationships with edge_type), structured output via tool_use, correctness requirements (node_type must match methodology ontology, edge permitted_connections), symptom→cause→fix.

- [ ] **Step 2: Draft graph dedup spec**

Read `docs/extraction_and_graphs.md` (surface graph sections) and `src/services/graph_service.py`. Create `docs/specs/graph-dedup.md` covering: exact match → embedding similarity → create new flow, `surface_similarity_threshold` (0.80), cross-turn edge resolution, correctness requirements (embedding required before similarity check, dedup is per-session not global).

- [ ] **Step 3: Draft canonical slots spec**

Read `docs/extraction_and_graphs.md` (canonical sections) and `src/services/canonical_slot_service.py`. Create `docs/specs/canonical-slots.md` covering: candidate→active lifecycle, `support_count >= canonical_min_support_nodes`, batched LLM slot proposals (max 8 nodes/call), embedding merge, correctness requirements (active-only slots in signals, timing: slots available after Stage 4.5).

- [ ] **Step 4: Replace source doc with index pointer and update mapping**

```markdown
# Extraction and Graphs

> This document has been split into focused subsystem specs.

| Topic | Spec |
|-------|------|
| LLM concept/relationship extraction | [`docs/specs/extraction.md`](specs/extraction.md) |
| Surface graph deduplication | [`docs/specs/graph-dedup.md`](specs/graph-dedup.md) |
| Canonical slot discovery | [`docs/specs/canonical-slots.md`](specs/canonical-slots.md) |
```

- [ ] **Step 5: Commit**

```bash
git add docs/specs/extraction.md docs/specs/graph-dedup.md docs/specs/canonical-slots.md docs/extraction_and_graphs.md .claude/doc_mapping.yaml
git commit -m "docs: extract extraction, graph-dedup, canonical-slots specs"
```

---

### Task 13: Create data flow path specs

**Files:**
- Create: `docs/specs/turn-count.md`
- Create: `docs/specs/strategy-selection.md`
- Create: `docs/specs/graph-mutation.md`
- Create: `docs/specs/node-exhaustion.md`
- Modify: `docs/data_flow_paths.md` (replace with index pointer)
- Modify: `.claude/doc_mapping.yaml`

- [ ] **Step 1: Draft turn-count spec**

Read `docs/data_flow_paths.md` (Path 1). Create `docs/specs/turn-count.md` covering: `turn_count` (DB) vs `turn_number` (context) distinction, the load→increment→persist cycle, phase boundary calculation from `max_turns`, correctness requirements (turn_number = turn_count + 1; never skip Stage 10 update).

- [ ] **Step 2: Draft strategy-selection spec**

Read `docs/data_flow_paths.md` (Path 2) and `src/services/methodology_strategy_service.py`. Create `docs/specs/strategy-selection.md` covering: the full signal detection → scoring → selection flow (referencing `docs/specs/strategy-scoring.md` for scoring details), the `StrategySelectionOutput` contract, correctness requirements (phase detected before scoring; node signals merged with global before partitioning).

- [ ] **Step 3: Draft graph-mutation spec**

Read `docs/data_flow_paths.md` (Path 3). Create `docs/specs/graph-mutation.md` covering: extraction → dedup → DB write → StateComputation refresh cycle, why StateComputation must run after GraphUpdate (freshness guarantee), correctness requirements.

- [ ] **Step 4: Draft node-exhaustion spec**

Read `docs/data_flow_paths.md` (node exhaustion paths) and `docs/NodeStateTracker_mutation.md`. Create `docs/specs/node-exhaustion.md` incorporating the Stage 4/Stage 6 ordering insight as a correctness requirement.

- [ ] **Step 5: Replace data_flow_paths.md with index and update mapping**

```markdown
# Data Flow Paths

> This document has been split into focused subsystem specs.
> Mermaid diagrams are preserved in the specs where they add clarity.

| Path | Spec |
|------|------|
| Turn count evolution | [`docs/specs/turn-count.md`](specs/turn-count.md) |
| Strategy selection | [`docs/specs/strategy-selection.md`](specs/strategy-selection.md) |
| Graph state mutation | [`docs/specs/graph-mutation.md`](specs/graph-mutation.md) |
| Node exhaustion & rotation | [`docs/specs/node-exhaustion.md`](specs/node-exhaustion.md) |
| Traceability chain | See [`docs/specs/pipeline-contracts.md`](specs/pipeline-contracts.md) |
| Canonical slot discovery | See [`docs/specs/canonical-slots.md`](specs/canonical-slots.md) |
```

- [ ] **Step 6: Commit**

```bash
git add docs/specs/turn-count.md docs/specs/strategy-selection.md docs/specs/graph-mutation.md docs/specs/node-exhaustion.md docs/data_flow_paths.md .claude/doc_mapping.yaml
git commit -m "docs: extract data flow path specs; retire data_flow_paths.md to index"
```

---

### Task 14: Reformat NodeStateTracker spec

**Files:**
- Modify: `docs/NodeStateTracker_mutation.md` → reformat to standard spec format (keep content, restructure)
- Modify: `.claude/doc_mapping.yaml` (update pointer to `docs/specs/node-state-tracker.md` if moved)

- [ ] **Step 1: Reformat to standard spec format**

Read `docs/NodeStateTracker_mutation.md` and rewrite it using the Core Mechanics / Correctness Requirements / Symptom→Cause→Fix / Key Files structure. Keep all existing content — this is a reformat, not a rewrite. The Stage 4/Stage 6 ordering issue must appear as a Correctness Requirement.

Either update in place or move to `docs/specs/node-state-tracker.md` and add a redirect in the original.

- [ ] **Step 2: Commit**

```bash
git add docs/NodeStateTracker_mutation.md  # or docs/specs/node-state-tracker.md
git commit -m "docs: reformat NodeStateTracker spec to standard format"
```

---

### Task 15: Final verification and push

- [ ] **Step 1: Run the drift detector against the restructured docs**

```bash
uv run python scripts/check_doc_drift.py
```

Expected: silent or warnings only for docs not yet updated. No Python errors.

- [ ] **Step 2: Run all tests**

```bash
uv run pytest tests/test_check_doc_drift.py -v
```

Expected: all pass.

- [ ] **Step 3: Verify doc mapping coverage**

```bash
python3 -c "
import yaml
from pathlib import Path
mapping = yaml.safe_load(open('.claude/doc_mapping.yaml'))['mappings']
docs = {m['doc'] for m in mapping}
for doc in sorted(docs):
    exists = Path(doc).exists()
    print(f'{'✓' if exists else '✗'} {doc}')
"
```

Expected: all docs exist (✓).

- [ ] **Step 4: Push**

```bash
git push
```
