# Eval Harness for Methodology Tuning

## Overview

Measurement infrastructure for empirical methodology tuning. Runs simulation matrices, computes graph-derived metrics, and compares config versions with statistical confidence intervals.

**This is measurement infrastructure only.** Tuning decisions are yours.

## CLI Usage

### Run a full eval matrix

```bash
uv run python scripts/run_eval_matrix.py \
  --methodology mec \
  --concept zerofizz_beverage_mec \
  --personas baseline_cooperative,brief_responder,verbose_tangential \
  --replicates 10 \
  --max-turns 15 \
  --label "mec_baseline_2026_04"
```

**Methodology short names:** `mec`, `mec_flex`, `jtbd`, `cit`, `cjm`, `rg` (or use full YAML name).

**Available personas:** `baseline_cooperative`, `brief_responder`, `verbose_tangential`, `fatiguing_responder`, `single_topic_fixator`, `uncertain_hedger`, `skeptical_analyst`, `disengaged_responder`.

### View the scoreboard

```bash
# All runs for a methodology
uv run python scripts/show_scoreboard.py --methodology mec

# Specific config
uv run python scripts/show_scoreboard.py --config-hash abc123

# Compare against baseline
uv run python scripts/show_scoreboard.py --config-hash abc123 --compare-to def456

# List registered configs
uv run python scripts/show_scoreboard.py --list-configs
```

### Baseline-vs-baseline calibration

```bash
# Run same config twice under different labels
uv run python scripts/run_eval_matrix.py ... --label "mec_baseline_A"
uv run python scripts/run_eval_matrix.py ... --label "mec_baseline_B"

# Compare — if CIs don't overlap materially, increase replicates
uv run python scripts/show_scoreboard.py --methodology mec
```

### Smoke test

```bash
uv run python scripts/smoke_test_eval.py
```

## Workflow

1. **Establish baseline:** Run matrix with current config, label as baseline.
2. **Tweak config:** Edit `config/methodologies/*.yaml` (signal weights, strategy thresholds).
3. **Run experiment:** Same matrix, new label.
4. **Compare:** `show_scoreboard.py --compare-to <baseline_hash>`.
5. **Decide:** If delta is real (CIs don't overlap), adopt the change.

## Metrics

### Universal (all methodologies)
| Metric | Definition |
|--------|-----------|
| `node_count` | Total surface nodes in knowledge graph |
| `orphan_ratio` | Nodes with no edges / total nodes |
| `canonical_slot_coverage` | Active canonical slots / ontology node types |
| `total_turns` | Turns completed |

### Methodology-specific: structural completeness
| Methodology | Root type | Resolution type | "Complete structure" |
|---|---|---|---|
| MEC | attribute | terminal_value | Chain attribute→...→terminal_value |
| JTBD | job_statement | solution_approach | Job explored through to solution |
| CIT | incident | emotion/attribution/learning/behavior_change | Narrative reaching resolution |
| CJM | stage | friction/moment_of_truth | Stage with discovered pain or insight |
| RG | construct_pole | laddered_construct | Construct deepened via laddering |

### Methodology-specific: breadth & depth
- `ontology_breadth`: fraction of ontology node types with instances
- `exploration_depth`: average shortest path from root to resolution nodes

## Architecture

```
scripts/eval_metrics.py        — Metric computation from DB graph
scripts/run_eval_matrix.py     — Matrix runner (config hash, parallel, temperature control)
scripts/show_scoreboard.py     — Aggregation + pretty-print + delta-vs-baseline
scripts/smoke_test_eval.py     — Minimal validation (2 personas × 2 replicates)
```

**Tables in `data/interview.db`:**
- `eval_config_registry` — config_hash → label mapping
- `eval_runs` — one row per simulation cell with all metrics

## Determinism Boundary

The harness enforces `temperature=0` for extraction, slot scoring, and signal scoring LLM calls (deterministic), while preserving stochastic temperature for persona response generation and question generation. This was achieved by removing hardcoded temperature overrides in `extraction_service.py` and `canonical_slot_service.py`, letting the config be the single source of truth.
