# Testing Harness for Methodology Tuning

## Purpose

The testing harness measures how well the interview system probes a conversation to produce structured knowledge graphs. It runs batches of simulated interviews under controlled conditions, computes graph-derived metrics, and compares results across methodology config versions with statistical confidence intervals.

The core value proposition it measures: **signal-driven strategy selection achieves structural depth (complete chains, explored jobs, resolved narratives) that unguided interviews cannot.**

This is measurement infrastructure only. It does not tune configs automatically.

## How It Works

1. **Config hashing** — SHA256 of the methodology YAML file produces a `config_hash` that uniquely identifies the config state. Every simulation run is tagged with this hash.

2. **Determinism boundary** — Before running simulations, the harness forces `temperature=0` for extraction, slot scoring, and signal scoring LLM calls (algorithmic determinism). Persona response generation and question generation keep stochastic temperatures (ecological validity). This separates "algorithmic variance" from "generative variance."

3. **Matrix execution** — Runs a grid of simulation cells: `(config_hash × concept × persona × replicate_seed)`. Uses `asyncio.Semaphore` for parallelism with a configurable concurrency limit.

4. **Metric computation** — After each simulation, queries the session's knowledge graph from SQLite and computes universal + methodology-specific metrics (see Metrics section).

5. **Scoreboard** — Results stored in `eval_runs` table. Aggregation view computes mean, std, 95% CI per config. Delta-vs-baseline comparison available.

## Files

| File | Purpose |
|------|---------|
| `scripts/eval_metrics.py` | Metric computation from DB graph (BFS path analysis) |
| `scripts/run_eval_matrix.py` | Matrix runner — config hashing, parallel execution, temperature control |
| `scripts/show_scoreboard.py` | Aggregation, CI computation, pretty-print, delta-vs-baseline |
| `scripts/smoke_test_eval.py` | Minimal validation (2 personas × 2 replicates) |
| `scripts/eval_harness_README.md` | CLI quick reference |

### DB Tables (in `data/interview.db`)

- **`eval_config_registry`** — Maps `config_hash` to human-readable label
- **`eval_runs`** — One row per simulation cell with all metrics

### Upstream Dependency

The harness requires the upstream temperature fix in:
- `src/services/extraction_service.py` — reads temperature from config (not hardcoded)
- `src/services/canonical_slot_service.py` — same

## Metrics

### Universal (all methodologies)

| Metric | Column | Definition |
|--------|--------|------------|
| Node count | `node_count` | Total surface nodes in knowledge graph |
| Orphan ratio | `orphan_ratio` | Nodes with no edges / total nodes |
| Canonical slot coverage | `canonical_slot_coverage` | Active canonical slots / ontology node types |
| Total turns | `total_turns` | Turns completed |

### Methodology-specific: structural completeness

The key metric. Counts how many "root" node types have an undirected path to a "resolution" node type in the graph — proving the system guided the interview from a starting point to a conclusion.

| Methodology | Root type | Resolution type | Meaning |
|---|---|---|---|
| MEC | `attribute` | `terminal_value` | Complete attribute→value chain |
| JTBD | `job_statement` | `solution_approach` | Job explored through to solution |
| CIT | `incident` | `emotion`, `attribution`, `learning`, `behavior_change` | Narrative reaching resolution |
| CJM | `stage` | `friction`, `moment_of_truth` | Stage with discovered pain or insight |
| RG | `construct_pole` | `laddered_construct` | Construct deepened via laddering |

### Methodology-specific: max chain depth

Captures partial chain progress for hierarchical ontologies. Measures the deepest ontology level reached by any path starting at a root node, in 1–N levels (where N is the methodology's ontology depth).

| Methodology | Levels (root → terminal) | Depth | `max_chain_depth` meaning |
|---|---|---|---|
| MEC | attribute → functional_consequence → psychosocial_consequence → instrumental_value → terminal_value | 5 | 4 = reached instrumental_value, 5 = reached terminal_value (equivalent to structural_completeness ≥ 1) |
| JTBD | job_statement → emotional_job / social_job | 2 | 2 = reached emotional/social job (equivalent to structural_completeness ≥ 1) |
| CIT | incident → situation → action → outcome → emotion/attribution/learning/behavior_change | 5 | 4 = reached outcome, 5 = reached resolution |
| CJM | — | 0 | Flat ontology — not applicable |
| RG | — | 0 | Flat ontology — not applicable |

**Consistency check:** `max_chain_depth == ontology_depth` implies `structural_completeness ≥ 1` for the same run.

### Methodology-specific: breadth and depth

- **`ontology_breadth`** — Fraction of ontology node types that have at least one instance (how much of the conceptual space was covered)
- **`exploration_depth`** — Average shortest undirected path length from root nodes to resolution nodes (how deeply the system probed)

## CLI Reference

### Methodology short names

`mec`, `mec_flex`, `jtbd`, `cit`, `cjm`, `rg` — or use the full YAML name (e.g. `means_end_chain_v2_strict`).

### Available personas

`baseline_cooperative`, `brief_responder`, `verbose_tangential`, `fatiguing_responder`, `single_topic_fixator`, `uncertain_hedger`, `skeptical_analyst`, `disengaged_responder`

### Run a matrix

```bash
uv run python scripts/run_eval_matrix.py \
  --methodology mec \
  --concept zerofizz_beverage_mec \
  --personas baseline_cooperative,brief_responder,verbose_tangential \
  --replicates 10 \
  --max-turns 15 \
  --max-parallel 4 \
  --label "mec_baseline_2026_04"
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--methodology` | yes | — | Short name or full YAML name |
| `--concept` | yes | — | Concept ID from `config/concepts/` |
| `--personas` | yes | — | Comma-separated persona IDs |
| `--replicates` | no | 10 | Replicates per persona cell (default is a floor — use ≥25 for calibration and A/B comparisons; see Statistical Notes) |
| `--max-turns` | no | 15 | Max turns per simulation |
| `--max-parallel` | no | 4 | Concurrent simulations (LLM API budget) |
| `--label` | yes | — | Human-readable config label for scoreboard |

### View scoreboard

```bash
# All runs for a methodology
uv run python scripts/show_scoreboard.py --methodology mec

# Specific config version
uv run python scripts/show_scoreboard.py --config-hash 9b7a0a1d03d0913f

# Compare experiment vs baseline (shows delta column)
uv run python scripts/show_scoreboard.py --config-hash <experiment> --compare-to <baseline>

# Group by persona instead of config
uv run python scripts/show_scoreboard.py --label mec_baseline --by-persona

# List all registered configs
uv run python scripts/show_scoreboard.py --list-configs
```

### Smoke test

```bash
uv run python scripts/smoke_test_eval.py
```

Runs 2 personas × 2 replicates with `max_turns=5`. Takes ~3-4 minutes. Verifies plumbing works — does NOT verify statistical properties.

## Typical Workflow

```
1. Establish baseline
   └─ run_eval_matrix.py ... --label "mec_baseline_2026_04"

2. Edit config
   └─ vim config/methodologies/means_end_chain_v2_strict.yaml
   (tweak signal weights, strategy thresholds)

3. Run experiment
   └─ run_eval_matrix.py ... --label "mec_ascend_weight_v1"

4. Compare
   └─ show_scoreboard.py --methodology mec
   (look at structural_completeness and exploration_depth deltas)

5. Decide
   └─ If CIs don't overlap → adopt change
   └─ If CIs overlap → no significant effect, revert or increase replicates
```

### Baseline-vs-baseline calibration

Run the same config twice under different labels, then compare. If the 95% CIs overlap, the statistical framing is valid. If they don't, increase `--replicates`.

## Concept IDs for Testing

The `domain:zerofizz_beverage_v1` concept suite provides methodology-matched concepts with a shared domain brief:

| Concept ID | Methodology |
|---|---|
| `zerofizz_beverage_mec` | means_end_chain_v2_strict |
| `zerofizz_beverage_jtbd` | jobs_to_be_done_v2 |
| `zerofizz_beverage_cit` | critical_incident_v2 |
| `zerofizz_beverage_cjm` | customer_journey_mapping_v2 |
| `zerofizz_beverage_rg` | repertory_grid_v2 |

## Statistical Notes

- **Replicates**: Default R=10 is a floor, not a target. For baseline-vs-baseline calibration and real config comparisons use R≥25. Step 5 determinism audit (2026-04-23) showed `node_count` drift of up to ~30% between repeated runs of the same config, which means small effect sizes need more samples to detect.
- **Comparisons are unpaired.** `replicate_seed` is stored as a row label (for uniqueness and traceability) but is **not threaded into the simulation or LLM calls** — `simulate_interview()` receives no seed, and the Anthropic Messages API does not expose a `seed` parameter. Two runs with the same `(persona_id, replicate_seed)` are independent samples, not paired observations. Treat all analysis as unpaired; do not expect the variance reduction a paired design would give.
- **Replicate seeds**: Deterministic from `hash(persona_id:replicate_idx)` — stable as a *label* across runs, but does not fix LLM state. Useful for joining rows, not for reducing variance.
- **95% CI**: Computed as `1.96 × std / sqrt(n)` using sample standard deviation. With unpaired variance, expect wider CIs than a paired design would produce.
- **Determinism boundary**: `temperature=0` is forced for extraction, slot scoring, and signal scoring. Persona and question generation keep stochastic temperatures. Observed divergence across identical-config runs is driven by those generative calls, not by the deterministic pathway.
