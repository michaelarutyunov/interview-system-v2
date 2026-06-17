# Causal Chain Extraction — 20260428_143220_zerofizz_beverage_jtbd_baseline_cooperative.json

## Source specs
- **Session ID**: e7d651da-791b-465e-a83e-ea3c39a4531a
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 10
- **Status**: Closing strategy selected
- **Saved at**: 2026-04-28T14:32:20.975540+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/jobs_to_be_done_v2.yaml`
- **Chain edge types**: triggers, implies, supports, drives
- **Permitted connections**:
  - `triggers`: 6 permitted pairs
  - `implies`: 2 permitted pairs
  - `supports`: 6 permitted pairs
  - `drives`: 3 permitted pairs
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 5

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 25 | 4 |
| Chain edges traversed | 25 | 16 |
| Edges (revises) | 3 | 2 |
| Node types | emotional_job, gain_point, job_context, job_statement, job_trigger, pain_point, solution_approach | gain_point, job_trigger, pain_point |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches solution_approach | 0 | 0 |
| Advanced | Reaches emotional_job / social_job, not terminal | 0 | 0 |
| Developing | Reaches job_statement | 6 | 0 |
| Started | Lower-level nodes only, terminal not reached | 0 | 1 |
| Lateral (excluded) | Same-type only chains | 1 | 0 |

---

## Full chains — complete narrative arc

_No full chains found._

## Advanced chains — near-terminal

_No advanced chains found._

## Developing chains — mid-level progression

### Chain 1 [surface]
**Path**: `mid-afternoon energy wall` (job_trigger, t=1) → `short-lived energy spike followed by hard crash` (pain_point, t=1) → `inability to focus on work after sugar crash` (pain_point, t=2) → `zoning out in afternoon meetings` (pain_point, t=2) → `appearing engaged while mentally absent` (pain_point, t=2) → `stay alert and functional through afternoon meetings` (job_statement, t=2)

**Evidence**:
- `mid-afternoon energy wall → short-lived energy spike followed by hard crash` [triggers] (t=1): _"(no quote)"_
- `short-lived energy spike followed by hard crash → inability to focus on work after sugar crash` [triggers] (t=1): _"(no quote)"_
- `inability to focus on work after sugar crash → zoning out in afternoon meetings` [triggers] (t=2): _"(no quote)"_
- `zoning out in afternoon meetings → appearing engaged while mentally absent` [triggers] (t=2): _"(no quote)"_
- `appearing engaged while mentally absent → stay alert and functional through afternoon meetings` [implies] (t=2): _"(no quote)"_
### Chain 2 [surface]
**Path**: `mid-afternoon energy wall` (job_trigger, t=1) → `inability to focus on work after sugar crash` (pain_point, t=2) → `zoning out in afternoon meetings` (pain_point, t=2) → `appearing engaged while mentally absent` (pain_point, t=2) → `stay alert and functional through afternoon meetings` (job_statement, t=2)

**Evidence**:
- `mid-afternoon energy wall → inability to focus on work after sugar crash` [triggers] (t=1): _"(no quote)"_
- `inability to focus on work after sugar crash → zoning out in afternoon meetings` [triggers] (t=2): _"(no quote)"_
- `zoning out in afternoon meetings → appearing engaged while mentally absent` [triggers] (t=2): _"(no quote)"_
- `appearing engaged while mentally absent → stay alert and functional through afternoon meetings` [implies] (t=2): _"(no quote)"_
### Chain 3 [surface]
**Path**: `mid-afternoon energy wall` (job_trigger, t=1) → `short-lived energy spike followed by hard crash` (pain_point, t=1) → `inability to focus on work after sugar crash` (pain_point, t=1) → `stay alert and functional through afternoon meetings` (job_statement, t=1)

**Evidence**:
- `mid-afternoon energy wall → short-lived energy spike followed by hard crash` [triggers] (t=1): _"(no quote)"_
- `short-lived energy spike followed by hard crash → inability to focus on work after sugar crash` [triggers] (t=1): _"(no quote)"_
- `inability to focus on work after sugar crash → stay alert and functional through afternoon meetings` [implies] (t=1): _"(no quote)"_
### Chain 4 [surface]
**Path**: `energy tanks by 2-3pm` (job_trigger, t=2) → `zoning out in afternoon meetings` (pain_point, t=2) → `appearing engaged while mentally absent` (pain_point, t=2) → `stay alert and functional through afternoon meetings` (job_statement, t=2)

**Evidence**:
- `energy tanks by 2-3pm → zoning out in afternoon meetings` [triggers] (t=2): _"(no quote)"_
- `zoning out in afternoon meetings → appearing engaged while mentally absent` [triggers] (t=2): _"(no quote)"_
- `appearing engaged while mentally absent → stay alert and functional through afternoon meetings` [implies] (t=2): _"(no quote)"_
### Chain 5 [surface]
**Path**: `afternoon meetings coming up` (job_trigger, t=?) → `avoid sugar crash before meetings` (pain_point, t=?) → `stay alert and functional through afternoon meetings` (job_statement, t=?)

**Evidence**:
- `afternoon meetings coming up → avoid sugar crash before meetings` [triggers] (t=?): _"(no quote)"_
- `avoid sugar crash before meetings → stay alert and functional through afternoon meetings` [implies] (t=?): _"(no quote)"_
### Chain 6 [surface]
**Path**: `mid-afternoon energy wall` (job_trigger, t=1) → `inability to focus on work after sugar crash` (pain_point, t=1) → `stay alert and functional through afternoon meetings` (job_statement, t=1)

**Evidence**:
- `mid-afternoon energy wall → inability to focus on work after sugar crash` [triggers] (t=1): _"(no quote)"_
- `inability to focus on work after sugar crash → stay alert and functional through afternoon meetings` [implies] (t=1): _"(no quote)"_
## Started chains — lower-level only

### Chain 1 [canonical]
**Path**: `circadian_energy_dip` (job_trigger, t=?) → `energy_crash_prevention` (pain_point, t=?)

**Evidence**:
- `circadian_energy_dip → energy_crash_prevention` [triggers] (t=?): _"(no quote)"_
## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `caffeine providing modest alertness boost` (gain_point) — _"the caffeine probably helped a bit"_
- `ZeroFizz feels lighter and less syrupy than Diet Coke` (gain_point) — _"ZeroFizz does feel lighter somehow, like less syrupy"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
