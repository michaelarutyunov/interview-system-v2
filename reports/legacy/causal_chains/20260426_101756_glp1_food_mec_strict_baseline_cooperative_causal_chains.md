# Causal Chain Extraction — 20260426_101756_glp1_food_mec_strict_baseline_cooperative.json

## Source specs
- **Session ID**: 18b4e7e5-9ebd-4bfe-b53e-f308665c6ec6
- **Concept**: GLP-1 Medication and Food Choices - Means-End Chain (Strict) (`glp1_food_mec_strict`)
- **Methodology**: `means_end_chain_v2_strict`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 5
- **Status**: Closing strategy selected
- **Saved at**: 2026-04-26T10:17:56.346760+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/means_end_chain_v2_strict.yaml`
- **Chain edge types**: leads_to
- **Permitted connections**:
  - `leads_to`: unconstrained
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 4

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 16 | 3 |
| Chain edges traversed | 13 | 7 |
| Edges (revises) | 3 | 1 |
| Node types | functional_consequence, instrumental_value, psychosocial_consequence | functional_consequence, psychosocial_consequence |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches terminal_value | 0 | 0 |
| Advanced | Reaches instrumental_value, not terminal | 0 | 0 |
| Developing | Reaches psychosocial_consequence | 1 | 2 |
| Started | Lower-level nodes only, terminal not reached | 0 | 0 |
| Lateral (excluded) | Same-type only chains | 6 | 0 |

---

## Full chains — complete narrative arc

_No full chains found._

## Advanced chains — near-terminal

_No advanced chains found._

## Developing chains — mid-level progression

### Chain 1 [surface]
**Path**: `reduced portion consumption (eating half of normal amount)` (functional_consequence, t=?) → `gentle fullness sensation (not uncomfortable, just done)` (functional_consequence, t=?) → `sense of surprise at changed eating behaviour` (psychosocial_consequence, t=?)

**Evidence**:
- `reduced portion consumption (eating half of normal amount) → gentle fullness sensation (not uncomfortable, just done)` [leads_to] (t=?): _"(no quote)"_
- `gentle fullness sensation (not uncomfortable, just done) → sense of surprise at changed eating behaviour` [leads_to] (t=?): _"(no quote)"_
### Chain 1 [canonical]
**Path**: `satiety_awareness` (functional_consequence, t=?) → `reduce_eat_struggle` (psychosocial_consequence, t=?)

**Evidence**:
- `satiety_awareness → reduce_eat_struggle` [leads_to] (t=?): _"(no quote)"_
### Chain 2 [canonical]
**Path**: `mental_space_relief` (functional_consequence, t=?) → `reduce_eat_struggle` (psychosocial_consequence, t=?)

**Evidence**:
- `mental_space_relief → reduce_eat_struggle` [leads_to] (t=?): _"(no quote)"_
## Started chains — lower-level only

_No started chains found._

## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `being mentally free from food preoccupation` (instrumental_value) — _"not having food be this constant thing in my head... make a choice and move on"_
- `denial of prior food obsession` (functional_consequence) — _"I don't think I was obsessing over food before or anything"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/means_end_chain_v2_strict.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
