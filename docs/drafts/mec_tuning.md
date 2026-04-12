# MEC Calibration Log

Chronological record of tuning iterations for `means_end_chain_v2_strict` and `means_end_chain_v3_flex`.
Each iteration: run ID → what was observed → what changed → files touched.

---

## Iteration 0 — Baseline (pre-calibration)

**Run**: `20260411_231448_glp1_food_mec_strict_baseline_cooperative`  
**Config**: means_end_chain_v2_strict, 15 turns, baseline_cooperative  
**Review**: `synthetic_interviews/review_20260411_231448_glp1_food_mec_strict_baseline_cooperative.md`

### Observations

| Issue | Detail |
|-------|--------|
| Strategy monotony | ascend 9/14 turns (64%) — phase multiplier cliff (0.7 gap) made every turn deterministic |
| Revitalize broken | Net score -28 across session; `temporal.strategy_repetition_count: -1.5` penalized revitalize hardest, it never fired |
| Branch questions generic | "What else changed?" loop for 6 consecutive turns; T6 actually behaved as ascend |
| Attribute extraction | Only 2 attribute nodes out of 83 — branch questions triggered functional/psychosocial extraction |
| Node monopoly | Node `982d112b` selected 14/15 turns — no recency penalty |
| Phase boundaries | YAML path returned fixed 6/7/2 turn counts regardless of CLI `max_turns`; 10-turn runs silently skipped late phase |
| Global signals | 9 signals identical across all strategies per turn — zero discriminative power |
| Ground/anchor/bridge | Zero positive signal mass; never selected |

### Decisions

- **R1**: Narrow phase multiplier gap (0.7 → 0.4)
- **R2**: Flip revitalize repetition weight (-1.5 → +0.5); add -0.15 penalty on structural strategies
- **R3**: Update branch description to specify product attribute elicitation
- **Phase fix**: Refactor `interview_phase.py` to scale YAML proportions by `context.max_turns`

---

## Iteration 1 — Phase fix + R1 + R2 + R3

**Run**: `20260412_070659_glp1_food_mec_strict_baseline_cooperative`  
**Config**: means_end_chain_v2_strict (post-calibration), 15 turns, baseline_cooperative  
**Review**: `synthetic_interviews/review_20260412_070659_glp1_food_mec_strict_baseline_cooperative.md`

### Changes applied

| Change | File | Detail |
|--------|------|--------|
| Phase boundary fix | `src/signals/meta/interview_phase.py:_get_phase_boundaries()` | Scale YAML n_turns proportionally by `context.max_turns`. For 15 turns with YAML 6/7/2=15: early=turns 0–5, mid=turns 6–12, late=turns 13–14 |
| R1 — multiplier gap | `config/methodologies/means_end_chain_v2_strict.yaml`, `means_end_chain_v3_flex.yaml` | early: branch 1.4/ascend 1.0 (was 1.5/0.8); mid: ascend 1.4/branch 1.0 (was 1.5/0.8); late: ascend 1.5/bridge 1.3 (was 1.8/1.5) |
| R2 — revitalize escape | Both MEC YAMLs | `temporal.strategy_repetition_count: +0.5` on revitalize (was -1.5); `temporal.strategy_repetition_count.high: +0.3` (was -1.0); added `-0.15` on ascend/ground/bridge/branch/anchor |
| R3 — branch description | Both MEC YAMLs | "Elicit additional product attributes or features at the same level — ask what other concrete characteristics of the product the respondent experiences or values" |

### Outcomes

| What was fixed | What changed | Status |
|----------------|-------------|--------|
| Phase boundaries | Confirmed: early=1–5, mid=6–12, late=13–15 ✓ | **Fixed** |
| Strategy diversity | ascend 40% / branch 27% / revitalize 33% (was 64% ascend) | **Improved** |
| Revitalize firing | 5/15 turns; escape valve mechanic confirmed working | **Fixed** |
| Branch question framing | Modestly improved — narrows to sensory/embodied domain | **Partial** |
| Attribute yield | 4 attribute nodes from 4 branch turns (was 2) — still too low | **Still broken** |

### New issues identified

| # | Issue | Root cause | Where |
|---|-------|-----------|-------|
| N1 | Revitalize fires mid-phase without engagement drop | `specificity=0.25` alone sufficient to trigger; no co-condition requiring engagement < 0.60 or shallowing trend | `means_end_chain_v2_strict.yaml` revitalize weights |
| N2 | Late-phase floor override (turns 14–15) | Revitalize base-score floor (~0.08 from repetition escape) exceeds ascend's penalized base (~0.02); ascend's 1.5× multiplier advantage overridden | Both MEC YAMLs late-phase multipliers + revitalize floor |
| N3 | Attribute extraction miscategorizes sensory experiences | Branch questions prompt embodied/experiential answers → LLM classifies as `functional_consequence`, not `attribute`; YAML attribute examples don't include sensory/hedonic features | `means_end_chain_v2_strict.yaml` ontology attribute examples |
| N4 | Ground/anchor/bridge still zero positive mass | Gate signals (`gap_below`, `is_orphan`, `level_skip`) not present in this session type — likely correct for cooperative cooperative ascent, but worth monitoring | — |

### Decisions

- **N1 fix**: Add `llm.specificity.low: -0.3` dampener to revitalize in mid-phase context — alternatively, reduce `temporal.strategy_repetition_count` escape weight slightly (0.5 → 0.3) so it doesn't override structural strategies mid-chain. Use YAML weight adjustment, not code change.
- **N2 fix**: Add `meta.interview.is_late_stage: -0.4` on revitalize — suppresses escape-valve floor in late phase, allowing ascend's multiplier to re-assert
- **N3 fix**: Expand attribute examples in YAML ontology to include sensory/hedonic/embodied food attributes (taste, texture, satiety sensation, appetite signal), not just structural product features

---

## Iteration 2 — N1 + N2 + N3 fixes

**Run**: *(pending)*  
**Config**: means_end_chain_v2_strict (post-N1/N2/N3), 15 turns, baseline_cooperative  

### Changes applied

| Change | File | Detail |
|--------|------|--------|
| N1 — revitalize mid-phase dampener | Both MEC YAMLs | `temporal.strategy_repetition_count: 0.5 → 0.3`; added `llm.specificity.low: -0.2` to revitalize |
| N2 — late-phase floor suppression | Both MEC YAMLs | Added `meta.interview.is_late_stage: -0.5` on revitalize |
| N3 — attribute ontology examples | Both MEC YAMLs | Expanded attribute examples to include sensory/hedonic/embodied food characteristics |

### Outcomes

| What was fixed | What changed | Status |
|----------------|-------------|--------|
| N1 — revitalize mid-phase false triggers | `llm.specificity.low: -0.2` fired turns 7–15, suppressed mid-phase revitalize — zero false triggers | **Fixed** |
| N2 — late-phase floor override | `meta.interview.phase.late: -0.5` fired turns 13–15; revitalize ranked last all three | **Fixed** |
| N3 — attribute yield | 4 → 6 attribute nodes (marginal); extraction still classifies GLP-1 behavioral attributes as functional_consequence | **Partial** |

### New issues identified

| # | Issue | Root cause | Where |
|---|-------|-----------|-------|
| N4 | Phase multiplier inversion on negative scores | When all base scores go negative in late phase, higher multiplier (ascend 1.5×) amplifies the negative more than lower (branch 0.8×), so branch "wins" by being least penalized — not by being most appropriate | Both MEC YAMLs late-phase multipliers |
| N5 | `temporal.strategy_repetition_count.high` double-counts | Fires simultaneously with base `temporal.strategy_repetition_count` at turn 5, producing +0.54 burst on revitalize with no engagement drop or fatigue | Both MEC YAMLs revitalize signal weights |
| N6 | Attribute extraction still misclassifies | GLP-1 behavioral attributes (`reduced appetite`, `faster satiety`) extracted as `functional_consequence` not `attribute` — ontology description change insufficient; extraction prompt needs explicit examples showing these as attributes | Extraction prompt for MEC in `config/methodologies/` |

### Decisions

- **N4 fix**: Late-phase base scores go negative because structural strategies have -0.15 repetition penalty accumulating with no matching positive signal. Two approaches: (a) add a small positive base for structural strategies in late phase via `phase_bonuses`; (b) reduce late-phase multiplier spread so sign inversion is less harmful. Use (a): add `phase_bonuses: {ascend: 0.1, bridge: 0.05}` in late phase.
- **N5 fix**: Remove `temporal.strategy_repetition_count.high` from revitalize — the base `temporal.strategy_repetition_count` already encodes the escape valve; the `.high` threshold is double-counting.
- **N6 fix**: Add explicit attribute vs functional_consequence disambiguation examples to extraction_guidelines in the MEC YAML — show that `reduced appetite` is an attribute (characteristic of the drug), `feeling full faster` is a functional consequence (outcome of taking the drug).

---

## Iteration 3 — N4 + N5 + N6 fixes

**Run**: *(pending)*
**Config**: means_end_chain_v2_strict (post-N4/N5/N6), 15 turns, baseline_cooperative

### Changes applied

| Change | File | Detail |
|--------|------|--------|
| N4 — late-phase base score fix | Both MEC YAMLs | Added `phase_bonuses: {ascend: 0.10, bridge: 0.05}` to late phase |
| N5 — double-count fix | Both MEC YAMLs | Removed `temporal.strategy_repetition_count.high: 0.3` from revitalize |
| N6 — extraction disambiguation | Both MEC YAMLs | Added attribute vs functional_consequence examples to `extraction_guidelines` |

### Outcomes

| What was fixed | What changed | Status |
|----------------|-------------|--------|
| N4 — late-phase multiplier inversion | ascend wins turns 13–15 (final=1.07 vs branch=-0.02); decisive margin | **Fixed** |
| N5 — revitalize double-count burst | Turn-5 burst gone this run; but structural risk remains — `temporal.strategy_repetition_count: 0.3` still positive on revitalize; only suppressed by `llm.engagement.high` penalty | **Partial** |
| N6 — attribute extraction | Attribute count still 6 (identical to Iteration 2); GLP-1 mechanical effects still classified as functional_consequence | **Not fixed** |

### New issues identified

| # | Issue | Root cause | Where |
|---|-------|-----------|-------|
| N7 | Late-phase node lock | Node `36d31f6b` wins all 3 late turns; `graph.node.exhaustion_score` not accumulating per focus turn — stuck at 0.3 | `src/services/node_state_tracker.py` exhaustion tracking |
| N8 | Branch early-phase streak (5 turns) | Base goes negative at turn 5 but phase_bonus+multiplier rescues it — 5 consecutive branch turns before revitalize can fire | Phase bonus creates a floor that delays the escape valve |
| N9 | Ascend chain exits topic domain | Turns 12–14 ladder from GLP-1 → child-rearing aspirations — valid MEC logic but drifts far from product territory | Question prompt topic anchoring (`src/llm/prompts/question.py`) |
| N10 | `graph.node.fan_in` over-contribution | fan_in=4 produces +0.268 (second-largest node signal); raw count not normalized | `means_end_chain_v2_strict.yaml` fan_in weight |

### Decisions

- **N5 fix (complete)**: Set `temporal.strategy_repetition_count: 0.0` on revitalize — remove the positive escape valve signal entirely. Rely on `llm.engagement.low`, `llm.global_response_trend.fatigued`, and `llm.global_response_trend.shallowing` as proper triggers. The repetition count should only penalize structural strategies, not reward revitalize.
- **N6 fix (stronger)**: The extraction disambiguation text isn't reaching the LLM effectively. Strategy: move the distinction into the node `description` field itself (not just extraction_guidelines), and add a `non_attribute_examples` list showing what NOT to classify as attribute.
- **N7**: Monitor across more runs — may be correct behavior if the node is genuinely the best target in late phase. Check exhaustion accumulation logic before changing.
- **N8**: Acceptable for now — 5 branch turns is slightly high but the interview still produces useful content. The phase_bonus is doing its job (keeping branch positive in early phase).
- **N9**: Add `depth_achieved >= 3` topic anchor note in question prompt — already exists in `question.py` at depth >= 2 but may need tightening.
- **N10**: Normalize `fan_in` weight — cap at 0.15 max contribution (currently unbounded integer).

---

## Iteration 4 — N5 (complete) + N6 (stronger) fixes

**Run**: *(pending)*
**Config**: means_end_chain_v2_strict (post-N5/N6 v2), 15 turns, baseline_cooperative

### Changes applied

| Change | File | Detail |
|--------|------|--------|
| N5 complete | Both MEC YAMLs | `temporal.strategy_repetition_count: 0.3 → 0.0` on revitalize (removed positive escape valve) |
| N6 v2 — attribute description | Both MEC YAMLs | Updated attribute node `description` field to include "NOT: outcomes the person experiences" |
| N6 v2 — non-attribute examples | Both MEC YAMLs | Added negative examples to attribute node spec |

### Outcomes

| What was fixed | What changed | Status |
|----------------|-------------|--------|
| N5 — repetition escape valve removed | Revitalize no longer triggered by `temporal.strategy_repetition_count` | **Fixed** |
| N5 — revitalize over-firing | Still 40% of turns (6/15); `llm.global_response_trend.shallowing` persists once triggered; LLM parsing bug causes 2 spurious firings when `llm.engagement` absent | **Still broken — different cause** |
| N6 — attribute extraction | Count 5 (lower than before); `non_attribute_examples` not reaching extraction LLM call | **Not fixed — wrong lever** |

### Root causes identified (YAML tuning cannot fix these)

| # | Root cause | Where |
|---|-----------|-------|
| RC1 | LLM signal parsing bug: `llm.engagement` absent at turns 4 and 11 → normal revitalize suppressor disappears → spurious firing | `src/signals/llm/` signal parsing; likely JSON parse failure or missing field in LLM response |
| RC2 | `non_attribute_examples` and updated `description` in ontology section not forwarded to extraction LLM call | `src/services/extraction_service.py` or `src/llm/prompts/` — extraction prompt builder reads extraction_guidelines but not node `non_attribute_examples` |

### Decisions

- **Stop YAML weight tuning on revitalize** — the over-firing is caused by RC1 (parsing bug) and a persistent `shallowing` signal, not weights
- **Fix RC1**: Investigate `src/signals/llm/` for the turns where `llm.engagement` goes absent; add defensive fallback or log the parsing failure explicitly
- **Fix RC2**: Trace `src/services/extraction_service.py` → find where node type descriptions are assembled into the extraction prompt → inject `non_attribute_examples` there

---

## Status: YAML Calibration Complete (for now)

Phase multiplier gap, repetition penalty, late-phase floor, branch description — all addressed across Iterations 0–4. Remaining issues require code fixes, not weight tuning:

| Issue | Type | Priority |
|-------|------|----------|
| RC1 — LLM signal parsing drops `llm.engagement` | Code bug | High |
| RC2 — Attribute extraction ignores node description/non_attribute_examples | Code/prompt bug | High |
| N7 — `graph.node.exhaustion_score` functionally inert | Signal calibration | Medium |
| N9 — Topic drift at depth ≥ 3 | Prompt tuning | Low |
