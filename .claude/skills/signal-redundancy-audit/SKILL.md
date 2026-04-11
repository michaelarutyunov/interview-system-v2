---
name: signal-redundancy-audit
description: Audit signal configurations across methodology YAMLs to identify dead, dormant, or non-decisive signals that can be safely removed. Combines static YAML analysis with empirical simulation data.
---

# Signal Redundancy Audit

Identifies signals in methodology YAML configs that are configured but do not influence strategy selection. Produces removal recommendations with rationale.

Two-phase process: static analysis (no simulation needed) then empirical analysis (requires simulation data).

---

## Phase 1 — Static Analysis (always run first)

No simulation data required. Catches structural issues immediately.

### Step 1: Enumerate declared vs. used signals

```python
uv run python3 -c "
import yaml, glob, collections

declared = collections.defaultdict(list)
used = collections.defaultdict(list)

for f in sorted(glob.glob('config/methodologies/*.yaml')):
    with open(f) as fh:
        data = yaml.safe_load(fh)
    name = f.split('/')[-1].replace('.yaml','')
    for pool, items in (data.get('signals') or {}).items():
        for s in (items or []):
            declared[s].append(name)
    for strategy in data.get('strategies', []):
        for sig in strategy.get('signal_weights', {}).keys():
            used[sig].append((name, strategy['name']))

print('DECLARED BUT NEVER IN signal_weights:')
for sig in sorted(declared):
    if not any(u.startswith(sig) or sig.startswith(u.rsplit('.',1)[0]) for u in used):
        matched = any(u == sig or u.startswith(sig + '.') for u in used)
        if not matched:
            print(f'  {sig}: {declared[sig]}')

print()
print('USED IN signal_weights BUT NEVER DECLARED:')
for sig in sorted(used):
    parts = sig.split('.')
    found = any('.'.join(parts[:i]) in declared for i in range(len(parts), 0, -1))
    if not found:
        print(f'  {sig}: {[(x[0],x[1]) for x in used[sig]]}')
"
```

**Interpret results:**

- **Declared but never used**: The signal is detected (costs a call) but its value is never read in scoring. Safe to remove from the `signals:` section.
- **Used but never declared**: The signal participates in scoring but is not in the `signals:` section. This works only if the detector runs unconditionally. Add to `signals:` for correctness or verify it's intentional.

### Step 2: Check for zero-weight entries

Any signal entry where the weight is 0 contributes nothing. These are likely copy-paste artifacts:

```bash
rg ":\s+0\.0?\s*$" config/methodologies/ --include="*.yaml"
```

### Step 3: Check for near-zero weights

Weights with `|weight| < 0.05` are noise — they can never flip a strategy decision given typical score magnitudes (1.0–3.0 range):

```python
uv run python3 -c "
import yaml, glob
for f in sorted(glob.glob('config/methodologies/*.yaml')):
    with open(f) as fh:
        data = yaml.safe_load(fh)
    name = f.split('/')[-1].replace('.yaml','')
    for strategy in data.get('strategies', []):
        for sig, w in strategy.get('signal_weights', {}).items():
            if 0 < abs(w) < 0.05:
                print(f'{name} / {strategy[\"name\"]} / {sig}: {w}')
"
```

---

## Phase 2 — Empirical Analysis (requires simulation data)

### Step 1: Ensure simulation data exists

```bash
ls synthetic_interviews/v2/*.json | wc -l
```

If fewer than 5 files, run simulations first:

```bash
# Run with a cooperative and a resistant persona to cover LLM signal range
uv run python scripts/run_simulation.py <concept_id> health_conscious 15
uv run python scripts/run_simulation.py <concept_id> skeptical_analyst 15
```

Why two personas: graph/temporal signals are persona-independent; LLM signals (engagement, valence, response_depth) vary by persona behavior. One cooperative + one resistant covers the full signal value range.

### Step 2: Extract scoring data

```bash
uv run python scripts/extract_simulation_data.py synthetic_interviews/v2/ analysis/simulation_extract/
```

Or skip this and pass the JSON dir directly to the audit script.

### Step 3: Run redundancy audit

```bash
# Against all available data
uv run python scripts/analyze_signal_redundancy.py analysis/simulation_extract/

# Filter to one methodology
uv run python scripts/analyze_signal_redundancy.py analysis/simulation_extract/ --methodology means_end_chain_v3_flex

# Filter to specific personas
uv run python scripts/analyze_signal_redundancy.py analysis/simulation_extract/ --personas health_conscious skeptical_analyst

# Against raw JSONs (no extract step needed)
uv run python scripts/analyze_signal_redundancy.py synthetic_interviews/v2/
```

### Step 4: Interpret the report

The script classifies each signal into one of four verdicts:

| Verdict | Meaning | Default action |
|---------|---------|----------------|
| **DEAD** | `fire_rate == 0` — contribution is always 0 | Remove from YAML immediately |
| **DORMANT** | `fire_rate < 5%` — almost never fires | Verify edge case intent; if none, remove |
| **MARGINAL** | Fires but `decisive_rate == 0` — never flips the winner | Review — may be intentional padding or redundant with a higher-weight signal |
| **ACTIVE** | Fires and occasionally changes which strategy wins | Keep |

**Metrics explained:**
- `fire_rate`: fraction of turns where contribution ≠ 0
- `avg_magnitude`: mean |contribution| when fired (how strongly it pushes scores)
- `decisive_rate`: fraction of turns where removing this signal would change the rank-1 strategy

---

## Judgment Layer — When to Keep a "MARGINAL" Signal

The script cannot see intent. Apply these checks before removing any MARGINAL signal:

1. **Phase specificity**: Does it only fire in `late` phase? If late-phase data is underrepresented in simulations, the signal looks dormant but isn't. Check: filter `--personas` and look at phase distribution.

2. **Persona specificity**: `llm.valence.low` will look dead if all test personas are cooperative. A signal targeting resistant-persona behavior needs a resistant persona in the test set.

3. **Protective role**: Some signals are designed as safety rails (e.g., suppressing a strategy when conditions are wrong) rather than boosters. A weight of -0.5 that never fires means the protected condition never occurred — the rail isn't broken, it just wasn't needed.

4. **Redundancy with higher-weight signal**: If signal A (weight 0.3) and signal B (weight 1.0) always fire together, removing A won't change outcomes but it accurately models the domain. Keep it if it has distinct semantic meaning; remove if it's a copy-paste of B.

---

## Removal Protocol

Once a signal is confirmed redundant:

1. **From `signals:` section only** (declared but unused): remove the line from the relevant YAML's `signals:` pool list.
2. **From `signal_weights`** (used but non-decisive): remove the key from each strategy's `signal_weights`. If this empties a strategy's weights entirely, flag for review.
3. **Run drift check** after edits:
   ```bash
   uv run python scripts/check_doc_drift.py
   ```
4. **Re-run audit** to confirm the signal no longer appears:
   ```bash
   uv run python scripts/analyze_signal_redundancy.py analysis/simulation_extract/ --methodology <name>
   ```
5. **Commit with rationale** in the commit message: which signals were removed and why (DEAD/DORMANT/MARGINAL + evidence from audit).

---

## Output Location

Save audit reports to `analysis/signal_audit/` with a datestamp:

```bash
uv run python scripts/analyze_signal_redundancy.py analysis/simulation_extract/ \
  --methodology means_end_chain_v3_flex \
  > analysis/signal_audit/$(date +%Y%m%d)_means_end_chain_v3_flex.txt
```
