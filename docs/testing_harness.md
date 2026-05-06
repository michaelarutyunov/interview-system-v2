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
| `scripts/eval/metrics.py` | Metric computation from DB graph (BFS path analysis) |
| `scripts/eval/run_matrix.py` | Matrix runner — config hashing, parallel execution, temperature control |
| `scripts/eval/show_scoreboard.py` | Aggregation, CI computation, pretty-print, delta-vs-baseline |
| `scripts/eval/smoke_test.py` | Minimal validation (2 personas × 2 replicates) |
| `scripts/eval/latency_audit.py` | Per-stage timing, LLM call metrics, cold-vs-warm split |
| `scripts/eval/build_quality_baseline.py` | Snapshot per-turn outputs as regression fixtures |
| `scripts/eval/README.md` | CLI quick reference |

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
uv run python scripts/eval/run_matrix.py \
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
uv run python scripts/eval/show_scoreboard.py --methodology mec

# Specific config version
uv run python scripts/eval/show_scoreboard.py --config-hash 9b7a0a1d03d0913f

# Compare experiment vs baseline (shows delta column)
uv run python scripts/eval/show_scoreboard.py --config-hash <experiment> --compare-to <baseline>

# Group by persona instead of config
uv run python scripts/eval/show_scoreboard.py --label mec_baseline --by-persona

# List all registered configs
uv run python scripts/eval/show_scoreboard.py --list-configs
```

### Smoke test

```bash
uv run python scripts/eval/smoke_test.py
```

Runs 2 personas × 2 replicates with `max_turns=5`. Takes ~3-4 minutes. Verifies plumbing works — does NOT verify statistical properties.

## Typical Workflow

```
1. Establish baseline
   └─ run_matrix.py ... --label "mec_baseline_2026_04"

2. Edit config
   └─ vim config/methodologies/means_end_chain_v2_strict.yaml
   (tweak signal weights, strategy thresholds)

3. Run experiment
   └─ run_matrix.py ... --label "mec_ascend_weight_v1"

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

## Worked Example: an MEC Tuning Cycle

A concrete walkthrough for reducing `revitalize` self-repetition in MEC's late phase without regressing structural completeness. Use this as a template — the same shape applies to any single-parameter tuning experiment.

### Goal

Hypothesis: the current `revitalize` weight on `interview.strategy.self_count` (-0.5) allows the strategy to reappear too often in late phase. Tightening the brake to -0.8 should reduce the strategy's share without hurting chain completion.

Numeric exit criteria (define *before* running anything):
- `revitalize` share of selected strategies drops by ≥20% vs. baseline.
- `structural_completeness` stays within the baseline's 95% CI on every persona.
- `max_chain_depth` does not decrease by more than one full level on any persona.

### Cost & Cadence (read before launching step 1)

A full first-cycle tuning experiment at R=25 is three batches of 200 runs each:

| Step | Batch | Runs | Wall-clock @ `--max-parallel=4` |
|------|-------|------|---------------------------------|
| 1 | Baseline `_a` | 8 personas × 25 replicates = 200 | ~1.5 hr |
| 2 | Baseline `_b` (same config, noise-floor calibration) | 200 | ~1.5 hr |
| 4 | Experiment (one YAML parameter changed) | 200 | ~1.5 hr |
| | **First-cycle total** | **600 runs** | **~4.5 hr** |

**Subsequent cycles on the same baseline are cheaper.** The baseline-vs-baseline calibration (step 2) is per-*baseline*, not per-experiment. Once you've confirmed noise-floor stability for a given config, you reuse that result across many experiments — only re-calibrate if the baseline itself changes (e.g., a methodology refactor). So subsequent cycles are baseline reference + experiment = ~400 runs, ~3 hr.

**LLM spend is non-trivial.** Each 15-turn run triggers ~6-10 LLM calls per turn (extraction + slot scoring + signal scoring + persona gen + question gen). 600 runs ≈ 40,000-60,000 LLM calls. Check the Anthropic dashboard after the first cycle to decide whether R=25 is sustainable for routine tuning or whether to drop to R=15 and reserve R=25 for final-before-adoption validation.

**Don't start at R=25 blind.** The R=25 figure is a starting estimate from a single determinism audit (2026-04-23) — it's the right order of magnitude, not a calibrated value. A sensible first-time approach:

1. Run step 2 (baseline-vs-baseline) at R=10 first — ~40 min.
2. If CIs for `structural_completeness` and `max_chain_depth` overlap between `_a` and `_b` → you're calibrated at R=10. Skip the R=25 escalation entirely. Full cycle becomes ~1.8 hr.
3. If CIs don't overlap → escalate to R=25 and re-run both batches. If they still don't overlap at R=25, go to R=50 before spending more on experiments.

Use R as a *fitted* value, not a *fixed* value.

### 1. Establish the baseline (~1.5 hr wall-clock at `--max-parallel=4`)

```bash
uv run python scripts/eval/run_matrix.py \
  --methodology mec \
  --concept zerofizz_beverage_mec \
  --personas baseline_cooperative,brief_responder,verbose_tangential,fatiguing_responder,single_topic_fixator,uncertain_hedger,skeptical_analyst,disengaged_responder \
  --replicates 25 \
  --max-turns 15 \
  --max-parallel 4 \
  --label "mec_baseline_2026_04_23_a"
```

### 2. Baseline-vs-baseline calibration (~1.5 hr)

Run the exact same command again, changing only the label to `mec_baseline_2026_04_23_b`. This does nothing to the config — it exercises the harness against itself to measure the noise floor.

```bash
uv run python scripts/eval/show_scoreboard.py \
  --config-hash <mec_baseline_hash> \
  --by-persona
```

Decision gate:
- CIs for `structural_completeness` and `max_chain_depth` overlap between `_a` and `_b` → statistical framing is valid, proceed to step 3.
- CIs do not overlap → the baseline itself is unstable. Increase `--replicates` to 50 and re-run both batches. Do not proceed until this gate passes.

### 3. Edit exactly one parameter

```yaml
# config/methodologies/means_end_chain_v2_strict.yaml
strategies:
  revitalize:
    weights:
      interview.strategy.self_count: -0.8   # was -0.5
```

Commit the edit in isolation — no other YAML changes. This makes the experiment attributable: if the scoreboard improves, the cause is unambiguous.

### 4. Run the experiment (~1.5 hr)

```bash
uv run python scripts/eval/run_matrix.py \
  --methodology mec \
  --concept zerofizz_beverage_mec \
  --personas <same 8> \
  --replicates 25 \
  --max-turns 15 \
  --max-parallel 4 \
  --label "mec_revitalize_brake_v1"
```

### 5. Compare against baseline

```bash
uv run python scripts/eval/show_scoreboard.py \
  --config-hash <experiment_hash> \
  --compare-to <baseline_a_hash>
```

Evaluate against the numeric exit criteria from step 0:
- **`revitalize` share delta**: is it ≥20% lower?
- **`structural_completeness` delta per persona**: any drop below baseline's lower CI bound?
- **`max_chain_depth` delta per persona**: any level regression?

### 6. Decide

- All three criteria met → adopt the change. Update CLAUDE.md's strategy-scoring notes if the rationale generalizes. Close the tuning bead.
- Structural regression on any persona → revert. The brake was too harsh; try -0.65 next. Do not stack experiments; one parameter per cycle.
- `revitalize` share unchanged but no regression → the brake isn't load-bearing at this weight. Pick a different signal to tune, or increase the magnitude further.

### What not to do

- Don't tune two parameters in the same cycle. Coupled effects mean you won't know which delta caused which outcome. See CLAUDE.md Known Failure Modes ("Base score asymmetry overwhelms repetition brakes") for a concrete case.
- Don't inspect transcripts and tune based on moderator intuition. The scoreboard is the objective function; use it. Transcript review is for canary cases only (step 7 below).
- Don't skip baseline-vs-baseline. If you do, you'll attribute noise to effects.

### Optional: canary regression check

Before adopting a change, spot-check the specific failure-mode scenarios referenced in CLAUDE.md — e.g., CIT `revitalize` runaway, CJM `deepen_stage` monoculture. The harness's aggregate metrics can hide pathological single-interview behavior that a targeted transcript review catches. If canaries pass and scoreboard passes, you're safe to adopt.

## Statistical Notes

- **Replicates**: Default R=10 is a floor, not a target. For baseline-vs-baseline calibration and real config comparisons use R≥25. Step 5 determinism audit (2026-04-23) showed `node_count` drift of up to ~30% between repeated runs of the same config, which means small effect sizes need more samples to detect.
- **Comparisons are unpaired.** `replicate_seed` is stored as a row label (for uniqueness and traceability) but is **not threaded into the simulation or LLM calls** — `simulate_interview()` receives no seed, and the Anthropic Messages API does not expose a `seed` parameter. Two runs with the same `(persona_id, replicate_seed)` are independent samples, not paired observations. Treat all analysis as unpaired; do not expect the variance reduction a paired design would give.
- **Replicate seeds**: Deterministic from `hash(persona_id:replicate_idx)` — stable as a *label* across runs, but does not fix LLM state. Useful for joining rows, not for reducing variance.
- **95% CI**: Computed as `1.96 × std / sqrt(n)` using sample standard deviation. With unpaired variance, expect wider CIs than a paired design would produce.
- **Determinism boundary**: `temperature=0` is forced for extraction, slot scoring, and signal scoring. Persona and question generation keep stochastic temperatures. Observed divergence across identical-config runs is driven by those generative calls, not by the deterministic pathway.
