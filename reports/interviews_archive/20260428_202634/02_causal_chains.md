# Causal Chain Extraction — 20260428_202634_zerofizz_beverage_jtbd_baseline_cooperative.json

## Source specs
- **Session ID**: c36972fc-9f64-4449-8d0e-359eada8150c
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 10
- **Status**: Closing strategy selected
- **Saved at**: 2026-04-28T20:26:34.217761+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/jobs_to_be_done_v2.yaml`
- **Chain edge types**: triggers, implies, supports, drives
- **Permitted connections**:
  - `triggers`: 6 permitted pairs
  - `implies`: 2 permitted pairs
  - `supports`: 6 permitted pairs
  - `drives`: 3 permitted pairs
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 3

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 27 | 3 |
| Chain edges traversed | 23 | 21 |
| Edges (revises) | 2 | 1 |
| Node types | emotional_job, gain_point, job_context, job_statement, pain_point, social_job, solution_approach | emotional_job, pain_point, solution_approach |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches solution_approach | 1 | 0 |
| Advanced | Reaches emotional_job / social_job, not terminal | 2 | 0 |
| Developing | Reaches job_statement | 1 | 0 |
| Started | Lower-level nodes only, terminal not reached | 1 | 0 |
| Lateral (excluded) | Same-type only chains | 4 | 0 |

---

## Full chains — complete narrative arc

### Chain 1 [surface]
**Path**: `participate in break-time ritual without compromising health` (social_job, t=5) → `choosing ZeroFizz as break-time ritual substitute` (solution_approach, t=5)

**Evidence**:
- `participate in break-time ritual without compromising health → choosing ZeroFizz as break-time ritual substitute` [drives] (t=5): _"(no quote)"_
## Advanced chains — near-terminal

### Chain 1 [surface]
**Path**: `coffee causes intense wired-then-crash cycle` (pain_point, t=1) → `maintain steady energy through the afternoon` (job_statement, t=4) → `avoid feeling like the day was a total waste` (emotional_job, t=4)

**Evidence**:
- `coffee causes intense wired-then-crash cycle → maintain steady energy through the afternoon` [implies] (t=1): _"(no quote)"_
- `maintain steady energy through the afternoon → avoid feeling like the day was a total waste` [supports] (t=4): _"(no quote)"_
### Chain 2 [surface]
**Path**: `actually enjoy time with people during social moments` (emotional_job, t=8) → `feel genuinely connected to the people around me` (social_job, t=8)

**Evidence**:
- `actually enjoy time with people during social moments → feel genuinely connected to the people around me` [supports] (t=8): _"(no quote)"_
## Developing chains — mid-level progression

### Chain 1 [surface]
**Path**: `slow down and be intentional for a moment` (gain_point, t=7) → `avoid mindless multitasking during breaks` (job_statement, t=7)

**Evidence**:
- `slow down and be intentional for a moment → avoid mindless multitasking during breaks` [implies] (t=7): _"(no quote)"_
## Started chains — lower-level only

### Chain 1 [surface]
**Path**: `infrequent carbonated drink consumption` (job_context, t=?) → `difficulty recalling specific sugar-free drink occasions` (pain_point, t=?)

**Evidence**:
- `infrequent carbonated drink consumption → difficulty recalling specific sugar-free drink occasions` [triggers] (t=?): _"(no quote)"_
## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `focus on work without anticipating energy crash` (gain_point) — _"I can actually focus on work stuff without feeling that crash coming"_
- `push through productive work until 5 or 6pm` (gain_point) — _"with it I can push through til 5 or 6 without getting completely useless"_
- `ability to work around lacking a fizzy drink option` (gain_point) — _"but i could work around it"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
