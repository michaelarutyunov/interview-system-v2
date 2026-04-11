---
name: interview-simulation-reviewer
description: Use when reviewing a simulated interview from interview-system-v2 to assess conversation quality, signal and strategy diagnostics, scoring decomposition, and knowledge graph health. Accepts JSON simulation output and optional scoring CSV.
---

# Interview Simulation Reviewer

Four-part structured review of simulation output. Each part has a defined input format, embedded domain knowledge, and produces actionable findings with specific module/config pointers. Parts 1–3 use the JSON file. Part 4 uses the scoring CSV (optional but recommended).

**Output**: Save the complete review as `synthetic_interviews/review_<json_filename_without_extension>.md`. For example, if the input is `20260306_223341_meal_planning_jtbd_v2_baseline_cooperative.json`, save to `synthetic_interviews/review_20260306_223341_meal_planning_jtbd_v2_baseline_cooperative.md`.

---

## Preamble — Cross-Run Validation

**When comparing multiple simulation runs:**

Before comparing personas or analyzing trends across runs, verify configuration consistency:

```bash
# Check if methodology YAML changed between runs
git log --since="<earlier_run_timestamp>" --until="<later_run_timestamp>" -- config/methodologies/
```

If any methodology YAML was modified between runs, flag the comparison as potentially invalid. Phase boundaries, signal weights, or strategy definitions may have drifted.

---

## Part 1 — Transcript Quality

**What to provide:**

```
[Turn N | Strategy: strategy_name]
Q: [question field]
A: [response field]
```

Include the strategy name — it explains the interviewer's intent.

**Assess against qualitative interview best practices:**

- **Openness**: Are questions open-ended? Flag yes/no questions or questions with assumed answers.
- **Followership**: Does the interviewer follow the respondent's thread or pivot to its own agenda?
- **Naturalness**: Are topic transitions smooth? Does it feel like a conversation or a survey?
- **Question complexity**: Flag multi-part, overly long, or jargon-heavy questions.
- **Leading**: Does phrasing suggest the expected answer?
- **Strategy-intent fit**: Given the active strategy, does the question make sense? (e.g., `dig_motivation` should probe the "why", not introduce new topics)

**Output format:**

```
TRANSCRIPT QUALITY
Overall: [1-2 sentence summary]

Flags:
- Turn N [strategy]: [issue] — [category: closed/leading/redirect/complex/strategy-mismatch]

Strengths:
- [What worked]
```

---

## Part 2 — Signal and Strategy Diagnostics

**Note:** Part 2 covers per-turn signal values and strategy-level patterns. For per-signal contribution aggregated across the entire session (firing rates, dead signals, weight calibration), use Part 4 (CSV).

**What to provide (per turn, skip turn 0):**

```
Turn | Phase | Depth    | Eng  | Val  | Spc  | Cert | Trend     | Selected             | Top scores
1    | early | deep     | 0.75 | 0.50 | 1.00 | 1.00 | deepening | explore_situation    | 3.20 / 1.20
2    | early | shallow  | 0.50 | 0.50 | 0.25 | 1.00 | stable    | explore_situation    | 3.56 / 1.54
...
```

Fields: `meta.interview.phase`, `llm.response_depth`, `llm.engagement`, `llm.valence`, `llm.specificity`, `llm.certainty`, `llm.global_response_trend`, `strategy_selected`, top-2 scores from `strategy_alternatives`.

**Signal semantics and thresholds (0–1 normalized):**

| Signal | Low concern | Healthy | High concern |
|--------|------------|---------|--------------|
| `engagement` | <0.40 → safety gate risk | 0.50–0.75 | — |
| `response_depth` | `shallow` | `moderate` | `deep` |
| `valence` | <0.40 negative/stressed | 0.50 neutral | >0.65 positive |
| `specificity` | <0.30 vague/abstract | 0.50+ | >0.75 concrete |
| `certainty` | <0.30 hedging | 0.50+ | — |

**`response_depth` safety gate:** When `engagement < 0.40` the system should suppress `dig_motivation` (deepen). If `dig_motivation` is selected despite `engagement < 0.40`, flag as a potential scoring bug → `src/services/methodology_strategy_service.py`.

**Strategy distribution — what to check:**

1. **Dominance**: Any single strategy selected in >50% of turns = monotony risk. Check `temporal.strategy_repetition_count` signal — if it stays low despite repetition, signal may be miscalibrated.
2. **Streaks**: Same strategy 4+ consecutive turns without `temporal.turns_since_strategy_change` rising = stale, signal not penalizing repetition.
3. **Phase alignment** (expected distribution):
   - Early (turns 1 to `early_max_turns` from `config/methodologies/*.yaml`): `explore_situation`, `probe_alternatives`
   - Mid (turns `early_max_turns+1` to `mid_max_turns`): `dig_motivation`, `uncover_obstacles`, `clarify_assumption`
   - Late (turns `mid_max_turns+1` onward): `validate_outcome`, `reflect`
   - `revitalize` can appear any phase when engagement drops

   **Important:** Read actual phase boundaries from the methodology YAML, not hardcoded defaults. Check `phases.early.phase_boundaries.early_max_turns` and `phases.mid.phase_boundaries.mid_max_turns`.

4. **Score separation**: If top-2 scores within 0.30 of each other consistently, selection is near-random → weight tuning candidate.
5. **`meta.interview_progress`**: Should increase monotonically each turn. If it plateaus → investigate progress computation in `src/signals/meta/`.

**Output format:**

```
SIGNAL & STRATEGY DIAGNOSTICS

Signal Sanity: [pass / flags below]
- Turn N: [signal]=X seems [high/low] given respondent said "[brief quote]"

Strategy Distribution:
| Strategy          | Count | % | Avg score |
|-------------------|-------|---|-----------|
| explore_situation |  2    |18%|   3.38    |
...

Phase Alignment: [aligned / issues]
- [specific misalignment]

Score Separation: [healthy / unstable]
- Turn N: gap=[X] between [strategy_1] and [strategy_2]

Anomalies → Investigate:
- Turn N: engagement=0.25 but dig_motivation selected → methodology_strategy_service.py safety gate
- interview_progress plateaus at 0.10 from turn 3 → src/signals/meta/interview_progress.py

Weight Tuning Candidates:
- [signal] appears over/under-weighted in [phase]: [evidence from score trends]
```

---

## Part 3 — Graph Health

**What to provide:**

```
Node growth by turn: 7→9→12→17→21→27→30→35→39→43
Orphan trajectory:   0→0→0→0→0→2→1→1→1→1

Final Surface Graph:
  Nodes: 43 | Edges: 55 | Density: 1.28 | Orphans: 1 (2.3%)
  Nodes by type: job_statement=6, job_context=5, solution_approach=8, gain_point=12, pain_point=9, emotional_job=2
  Edges by type: occurs_in=8, triggered_by=4, addresses=11, enables=16, supports=8, conflicts_with=7

Final Canonical Graph:
  Slots: 6 | Edges: 47 | Density per slot: 7.8
  Slots by type: gain_point=2, pain_point=2, job_context=1, solution_approach=1
  Compression ratio: 6/43 = 14%
```

**Health thresholds:**

| Metric | Concern | Healthy |
|--------|---------|---------|
| Surface edge/node ratio | <0.5 sparse | 1.0–2.0 |
| Orphan ratio | >10% | <5% |
| Node growth per turn | <2 nodes/turn (stalling) | 3–6 nodes/turn |
| Orphan spike then recovery | — | New orphans resolve → edges added |
| Canonical compression (slots/nodes) | <8% over-merged or >40% under-merged | 10–25% for JTBD |
| Canonical edges per slot | <3 weak clustering | >5 |
| Node type diversity | 1–2 types dominate >70% | balanced |

**Assess:**

1. **Growth trajectory**: Is node count growing each turn? Stalling (same count 2+ turns) = extraction may have failed → `src/services/turn_pipeline/stages/extraction_stage.py`.
2. **Orphan dynamics**: Spikes that resolve = acceptable (edge added next turn). Persistent orphans = low-confidence extractions with no connections → `src/services/graph_service.py` dedup thresholds.
3. **Surface density**: Final edge/node ratio. Low = graph is fragmented; high = well-connected narrative.
4. **Node type balance**: Over-dominance of one type (e.g., 40%+ gain_points) may indicate extraction prompt bias → `config/methodologies/*.yaml` extraction schema.
5. **Canonical compression**: Too high compression (few slots, many nodes per slot) = threshold too aggressive, merging distinct concepts → `settings.canonical_similarity_threshold`. Too low = threshold not catching genuine duplicates.
6. **Canonical edge density**: Canonical edges should be denser than surface (deduplication concentrates relationships). If canonical density ≈ surface density, deduplication may not be working → `src/services/canonical_slot_service.py`.

**Output format:**

```
GRAPH HEALTH

Surface Graph:
- Growth: [healthy / stalled at turn N → investigate extraction_stage.py]
- Noise: orphan ratio [peak=X%, final=X%] — [acceptable / concern]
- Density: [X] edge/node — [sparse / healthy / very dense]
- Node type balance: [balanced / [type] over-represented at X%]

Canonical Graph:
- Compression: [X slots from Y nodes = Z%] — [acceptable / too aggressive / too loose]
- Edge density: [X per slot] — [weak / healthy]
- vs Surface: canonical density [higher / similar / lower] than surface — [expected / unexpected → investigate canonical_slot_service.py]

Anomalies → Investigate:
- [finding] → [module or config key]
```

---

## Part 4 — Scoring Decomposition (CSV)

*Optional but recommended. Use when the `_scoring.csv` file is available alongside the JSON.*

**What the CSV provides:** Per-signal, per-node, per-strategy contribution rows for every turn. Columns: `turn_number, phase, strategy, node_id, signal_name, signal_value, signal_weight, weighted_contribution, phase_multiplier, phase_bonus, base_score, final_score, rank, selected`.

This answers questions impractical to derive manually from JSON: which signals drove selection across the whole session, which signals never fired, and whether phase weighting changed any outcomes.

**What to provide (from CSV aggregation):**

```
Signal firing rates (signal_value True or > 0):
  graph.node.focus_streak.none       fired 42/80 rows (53%) — avg contribution: +0.60
  llm.valence.mid                    fired 38/80 rows (48%) — avg contribution: +0.50
  graph.node.exhaustion_score.low    fired 35/80 rows (44%) — avg contribution: +0.40

Dead signals (weight ≠ 0, contribution = 0 across all turns):
  llm.global_response_trend.fatigued  weight=-0.60, fired 0 times
  temporal.strategy_repetition_count.high  weight=0, never triggered

Phase effect on selected strategy (mean scores):
  early: multiplier=1.5, bonus=0.2 — explore_situation avg final=3.20
  mid:   multiplier=1.3, bonus=0.3 — dig_motivation avg final=2.85

Node selection frequency (rank=1 turns):
  node c4ab31d8: selected 5 turns
  node 85df973f: selected 3 turns
```

**Assess:**

1. **Signal Symmetry Check (NEW)**: For each signal with >50% firing rate, compare its `signal_value` across strategies within the same turn. If values are identical for all strategies at a given turn, the signal cannot differentiate strategies — it adds a flat offset to all scores equally. Flag these as "global signals" whose weights waste budget without affecting ranking.

   Common global signals: `temporal.strategy_repetition_count` (same count for all strategies), `meta.interview.phase` (same phase for all strategies), `temporal.turns_since_strategy_change` (same count for all strategies).

   **Key insight**: If a signal is global, changing its weight shifts all scores equally and cannot fix dominance issues. The fix must be strategy-specific weight asymmetry or different signal selection.

2. **Penalty Asymmetry Audit (NEW)**: For each negative-weight signal, list which strategies carry it and which don't. If the dominant strategy lacks a penalty that its top competitors carry, this is a structural advantage. Check methodology YAML for anchor patterns like `<<: [*strategy_break]` — shared profiles may not apply uniformly.

3. **Dead signals**: Any signal with `weight ≠ 0` but `total weighted_contribution = 0` across all turns. Either the condition never triggers (threshold miscalibrated for this persona type) or the signal definition is broken. Point to YAML weight key and signal detector file.

   **For dead categorization signals** (e.g., `focus_streak.high`, `exhaustion_score.critical`): Cross-reference the signal detector's threshold logic against observed behavior. Check the signal definition in `src/signals/` to understand categorization boundaries, then verify if the condition was genuinely rare or if the threshold is unreachable.

   Example: `focus_streak.high` requires 4+ consecutive turns on same node — if top node was selected only 3 turns, "dead" is correct behavior, not a bug.

4. **Always-firing signals** (>80% of rows): Contribute a flat constant — they don't differentiate strategies, just inflate all scores equally. Flag as low-value use of the weight budget.

5. **Weight vs. impact gap**: High weight, low fire rate = high theoretical but low observed impact. Note if behavior didn't match expectations (e.g., repetition penalty never fired despite same strategy repeated 5 turns).

6. **Phase Multiplier Differential Analysis (NEW)**: Compare `phase_multiplier × base_score` between the winning strategy and runner-up at each turn. If the multiplier consistently widens the gap (rather than closing it), the phase weight is amplifying dominance rather than enabling phase-appropriate behavior. Check `phases.*.signal_weights.<strategy>` and `phases.*.phase_bonuses.<strategy>` in methodology YAML.

7. **Signal Budget Decomposition (NEW)**: For each strategy, sum positive vs negative contributions separately. Compare "signal mass" between dominant and runner-up strategies. If both have similar total mass but one wins consistently, look for structural advantages (multiplier differentials, penalty asymmetries, missing negative signals on winner).

8. **Node targeting logic**: Cross-reference which node won (rank=1) with its `exhaustion_score.*` and `focus_streak.*` signals. If an exhausted node keeps winning, the exhaustion penalty may be under-weighted relative to other contributions.

**Output format:**

```
SCORING DECOMPOSITION

Signal Firing Rates:
| Signal                              | Fired  | %  | Avg Contribution |
|-------------------------------------|--------|----|-----------------|
| graph.node.focus_streak.none        | 42/80  | 53%|     +0.60       |
| llm.valence.mid                     | 38/80  | 48%|     +0.50       |
...

Signal Symmetry Analysis:
- temporal.strategy_repetition_count: value=[X] identical across all strategies at each turn
  → Global signal — weight changes shift all scores equally, cannot fix dominance
  → If tuning repetition penalty: use strategy-specific weights, not shared profile

Penalty Asymmetry Audit:
- temporal.turns_since_strategy_change: penalizes [strategy_1, strategy_2] but NOT [dominant_strategy]
  → Structural advantage: dominant strategy exempt from break penalty
  → Check YAML for uneven profile application

Dead Signals (weight ≠ 0, never fired):
- llm.global_response_trend.fatigued (weight=-0.60) — persona never reached fatigue threshold
  → Check: llm signal rubric thresholds or persona energy config/personas/<name>.yaml
- [signal] (weight=[X]) — [hypothesis for why it never triggered]
  → Threshold cross-check: detector requires [condition], observed [actual behavior]

Always-Firing Signals (>80% turns):
- graph.node.yield_stagnation.false (weight=+0.50) — fires constantly, adds flat offset
  → Low differentiation value; consider reducing weight in config/methodologies/*.yaml

Weight Calibration Candidates:
- [signal]: weight=[X] but fired only [Y]% — impact lower than intended given [behavior pattern]

Signal Budget Decomposition (per strategy):
| Strategy          | Positive Mass | Negative Mass | Net    |
|-------------------|---------------|---------------|--------|
| dig_motivation    | +3.47         | -0.20         | +3.27  |
| uncover_obstacles | +3.12         | -0.64         | +2.48  |
→ Similar positive mass, but [strategy] has [X] less negative mass

Phase Multiplier Differential Analysis:
| Turn | Phase (winner) | Winner Multiplier | Runner-up Multiplier | Gap Change |
|------|----------------|-------------------|----------------------|------------|
| 5    | mid            | 1.4×              | 1.0×                 | widened    |
→ Multiplier amplifies gap by [X] points vs flat bonus
→ Check: phases.mid.signal_weights.<strategy> in YAML

Node Targeting:
- Top node [short-id]: selected [N] turns — [signal evidence it was correctly targeted / anomaly]
  → [If anomaly] Check exhaustion signal weights in config/methodologies/*.yaml
```

---

## Preparing Input from JSON

```python
import json

with open("synthetic_interviews/<filename>.json") as f:
    data = json.load(f)

# Part 1 — Transcript
for t in data["turns"]:
    print(f'[Turn {t["turn_number"]} | Strategy: {t["strategy_selected"]}]')
    print(f'Q: {t["question"]}')
    print(f'A: {t["response"]}')
    print()

# Part 2 — Signals and strategy scores
for t in data["turns"][1:]:   # skip turn 0 (no signals)
    s = t["signals"]
    top2 = t["strategy_alternatives"][:2]
    scores = " / ".join(f'{x["score"]:.2f}' for x in top2)
    print(f'{t["turn_number"]:>4} | {s["meta.interview.phase"]:5} | {s["llm.response_depth"]:8} | '
          f'{s["llm.engagement"]:.2f} | {s["llm.valence"]:.2f} | {s["llm.specificity"]:.2f} | '
          f'{s["llm.certainty"]:.2f} | {s["llm.global_response_trend"]:10} | '
          f'{t["strategy_selected"]:20} | {scores}')

# Part 3 — Graph trajectory
# Note: Node and orphan counts come from per-turn signals (graph.node_count, graph.orphan_count)
# The graph.summary does not include total_orphans — it must be aggregated from per-turn signals
nodes = [t["signals"]["graph.node_count"] for t in data["turns"][1:]]
orphans = [t["signals"]["graph.orphan_count"] for t in data["turns"][1:]]
print("Node growth:", "→".join(str(n) for n in nodes))
print("Orphan trajectory:", "→".join(str(o) for o in orphans))
g = data["graph"]["summary"]
c = data["canonical_graph"]["summary"]
total_orphans = orphans[-1] if orphans else 0  # Get final orphan count from trajectory
print(f'Surface: {g["total_nodes"]} nodes, {g["total_edges"]} edges, density={g["total_edges"]/g["total_nodes"]:.2f}, orphans={total_orphans}')
print(f'Canonical: {c["total_slots"]} slots, {c["total_edges"]} edges, density/slot={c["total_edges"]/c["total_slots"]:.1f}')
print(f'Compression: {c["total_slots"]}/{g["total_nodes"]} = {c["total_slots"]/g["total_nodes"]*100:.0f}%')
print(f'Nodes by type: {g["nodes_by_type"]}')
print(f'Slots by type: {c["slots_by_type"]}')
```

```python
# Part 4 — Scoring decomposition (requires pandas; install with: uv add pandas)
import pandas as pd

df = pd.read_csv("synthetic_interviews/<filename>_scoring.csv")

# Normalize signal_value to bool (CSV stores True/False as strings)
df["fired"] = df["signal_value"].astype(str).isin(["True", "1"]) | (
    pd.to_numeric(df["signal_value"], errors="coerce").fillna(0) > 0
)

# Signal firing rates — denominator is per-signal (how many rows exist for that signal)
signal_total_rows = df.groupby("signal_name").size().rename("total")
fired_agg = (df[df["fired"]]
             .groupby("signal_name")
             .agg(fired_count=("signal_name", "count"),
                  avg_contribution=("weighted_contribution", "mean")))
rates = fired_agg.join(signal_total_rows).assign(
    pct=lambda x: (x["fired_count"] / x["total"] * 100).round(1)
).sort_values("fired_count", ascending=False)
print("=== Signal Firing Rates ===")
print(rates[["fired_count", "total", "pct", "avg_contribution"]].to_string())

# Signal Symmetry Check — identify global signals (strategy-level only, node_id="" or empty)
# Node signals naturally differ per node, so only check strategy-level rows
print("\n=== Signal Symmetry Check ===")
strategy_level = df[df["node_id"].fillna("") == ""]
for signal in strategy_level["signal_name"].unique():
    signal_df = strategy_level[strategy_level["signal_name"] == signal][["turn_number", "strategy", "signal_value"]]
    turn_variance = signal_df.groupby("turn_number")["signal_value"].nunique()
    if (turn_variance == 1).all() and len(turn_variance) > 0:
        print(f"{signal}: GLOBAL — identical value across all strategies per turn")

# Dead signals (weight set, total contribution = 0)
signal_totals = df.groupby("signal_name").agg(
    total_contribution=("weighted_contribution", "sum"),
    max_weight=("signal_weight", lambda x: x.abs().max())
)
dead = signal_totals[(signal_totals["total_contribution"] == 0) & (signal_totals["max_weight"] > 0)]
print("\n=== Dead Signals ===")
print(dead.to_string())

# Always-firing signals (>80% of per-signal rows)
always = rates[rates["pct"] > 80]
print("\n=== Always-Firing Signals (>80%) ===")
print(always.to_string())

# Phase multiplier differential analysis
# Deduplicate to one row per turn: rank/selected/phase_multiplier are identical across signal rows
# for the same strategy-node pair, so drop_duplicates on turn-level columns
print("\n=== Phase Multiplier Differential ===")
winner = (df[df["selected"] & (df["rank"] == 1)]
          [["turn_number", "phase", "strategy", "node_id", "phase_multiplier", "base_score", "final_score"]]
          .drop_duplicates(subset=["turn_number"]))
runner_up = (df[df["rank"] == 2]
             [["turn_number", "strategy", "node_id", "phase_multiplier", "base_score", "final_score"]]
             .drop_duplicates(subset=["turn_number"]))
merged = winner.merge(runner_up, on="turn_number", suffixes=("_winner", "_runner"))
merged["multiplier_effect"] = (merged["phase_multiplier_winner"] - merged["phase_multiplier_runner"]) * merged["base_score_winner"]
print(merged[["turn_number", "phase", "strategy_winner", "strategy_runner",
              "phase_multiplier_winner", "phase_multiplier_runner", "multiplier_effect"]].to_string())

# Signal budget decomposition
print("\n=== Signal Budget Decomposition ===")
budget = df.groupby(["strategy", df["weighted_contribution"] > 0]).agg(
    total_contribution=("weighted_contribution", "sum")
).unstack(fill_value=0)
budget.columns = ["negative_mass", "positive_mass"]
budget["net"] = budget["positive_mass"] + budget["negative_mass"]
print(budget.sort_values("net", ascending=False).to_string())

# Node selection frequency — nunique handles duplicate signal rows correctly
node_wins = (df[df["selected"] & (df["rank"] == 1)]
             .groupby("node_id")["turn_number"]
             .nunique()
             .sort_values(ascending=False))
print("\n=== Node Selection Frequency ===")
print(node_wins.to_string())
```
