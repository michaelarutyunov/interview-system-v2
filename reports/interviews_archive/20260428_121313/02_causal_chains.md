# Causal Chain Extraction — 20260428_121313_zerofizz_beverage_jtbd_baseline_cooperative.json

## Source specs
- **Session ID**: ef918363-2f8e-4959-8df4-3fc47aec517f
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 10
- **Status**: Closing strategy selected
- **Saved at**: 2026-04-28T12:13:13.561787+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/jobs_to_be_done_v2.yaml`
- **Chain edge types**: triggers, implies, supports, drives
- **Permitted connections**:
  - `triggers`: 6 permitted pairs
  - `implies`: 2 permitted pairs
  - `supports`: 6 permitted pairs
  - `drives`: 3 permitted pairs
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 2

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 30 | 6 |
| Chain edges traversed | 28 | 24 |
| Edges (revises) | 1 | 1 |
| Node types | emotional_job, gain_point, job_context, job_statement, job_trigger, pain_point, solution_approach | gain_point, pain_point |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches solution_approach | 4 | 0 |
| Advanced | Reaches emotional_job / social_job, not terminal | 0 | 0 |
| Developing | Reaches job_statement | 0 | 0 |
| Started | Lower-level nodes only, terminal not reached | 1 | 0 |
| Lateral (excluded) | Same-type only chains | 4 | 1 |

---

## Full chains — complete narrative arc

### Chain 1 [surface]
**Path**: `sugar crash from drinks` (pain_point, t=?) → `get a flavorful drink without sugar consequences` (job_statement, t=?) → `grabbing a sugar-free can from the break room fridge` (solution_approach, t=?)

**Evidence**:
- `sugar crash from drinks → get a flavorful drink without sugar consequences` [implies] (t=?): _"(no quote)"_
- `get a flavorful drink without sugar consequences → grabbing a sugar-free can from the break room fridge` [drives] (t=?): _"(no quote)"_
### Chain 2 [surface]
**Path**: `more flavor than plain water` (gain_point, t=?) → `get a flavorful drink without sugar consequences` (job_statement, t=?) → `grabbing a sugar-free can from the break room fridge` (solution_approach, t=?)

**Evidence**:
- `more flavor than plain water → get a flavorful drink without sugar consequences` [implies] (t=?): _"(no quote)"_
- `get a flavorful drink without sugar consequences → grabbing a sugar-free can from the break room fridge` [drives] (t=?): _"(no quote)"_
### Chain 3 [surface]
**Path**: `regular sodas feeling too heavy or sweet` (pain_point, t=3) → `get a flavorful drink without sugar consequences` (job_statement, t=?) → `grabbing a sugar-free can from the break room fridge` (solution_approach, t=?)

**Evidence**:
- `regular sodas feeling too heavy or sweet → get a flavorful drink without sugar consequences` [implies] (t=3): _"(no quote)"_
- `get a flavorful drink without sugar consequences → grabbing a sugar-free can from the break room fridge` [drives] (t=?): _"(no quote)"_
### Chain 4 [surface]
**Path**: `avoid guilt about drinking soda` (emotional_job, t=3) → `grabbing a sugar-free can from the break room fridge` (solution_approach, t=3)

**Evidence**:
- `avoid guilt about drinking soda → grabbing a sugar-free can from the break room fridge` [drives] (t=3): _"(no quote)"_
## Advanced chains — near-terminal

_No advanced chains found._

## Developing chains — mid-level progression

_No developing chains found._

## Started chains — lower-level only

### Chain 1 [surface]
**Path**: `reaching for soda out of muscle memory` (job_trigger, t=2) → `having to consciously decide what to drink instead` (pain_point, t=2)

**Evidence**:
- `reaching for soda out of muscle memory → having to consciously decide what to drink instead` [triggers] (t=2): _"(no quote)"_
## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `at my desk for a few hours at work` (job_context) — _"i mostly grab them at work when i need something to sip on that's not just water. like, i'll be at my desk for a few hours"_
- `refreshing drink that doesn't leave you feeling guilty` (gain_point) — _"it's refreshing but doesn't leave you feeling guilty about it"_
- `reduced energy crash severity compared to regular soda` (gain_point) — _"I don't crash as hard as I used to with regular soda"_
- `afternoon hours at work` (job_context) — _"I notice it more in the afternoon when I'm kind of hitting that slump around 3 or 4"_
- `refreshing effect may be placebo or psychological` (pain_point) — _"even if it's probably all in my head"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
