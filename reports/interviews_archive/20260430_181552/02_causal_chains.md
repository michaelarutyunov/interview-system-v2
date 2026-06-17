# Causal Chain Extraction — 20260430_181552_zerofizz_beverage_jtbd_brief_responder.json

## Source specs
- **Session ID**: 4dd4c408-5dc3-4542-8a01-b8586c590625
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Brief Responder (`brief_responder`)
- **Total turns**: 7
- **Status**: quality_degraded
- **Saved at**: 2026-04-30T18:15:52.071527+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/jobs_to_be_done_v2.yaml`
- **Chain edge types**: triggers, implies, supports, drives, addresses, achieves
- **Permitted connections**:
  - `triggers`: upward
  - `implies`: upward
  - `supports`: upward_or_lateral
  - `drives`: upward
  - `addresses`: reverse
  - `achieves`: reverse
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 2

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 12 | 1 |
| Chain edges traversed | 16 | 14 |
| Edges (revises) | 1 | 1 |
| Node types | gain_point, job_context, job_statement, job_trigger, pain_point, solution_approach | pain_point |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches solution_approach — complete chain, no missing levels | 0 | 0 |
| Advanced | Reaches solution_approach (with one gap) or emotional_job / social_job | 0 | 0 |
| Developing | Mid-level progression, terminal not reached | 2 | 0 |
| Started | Incomplete — fewer than 3 nodes | 4 | 0 |
| Lateral (excluded) | Same-type only chains | 0 | 0 |

---

## Full chains — complete, no missing levels

_No full chains found._

## Advanced chains — near-complete (one gap) or near-terminal

_No advanced chains found._

## Developing chains — mid-level progression

### Chain 1 [surface]
**Path**: `Tuesday afternoon at work` (job_context, t=1) → `avoid energy crash after drinking` (gain_point, t=1) → `choosing ZeroFizz` (solution_approach, t=1)

**Evidence**:
- `Tuesday afternoon at work → avoid energy crash after drinking` [triggers] (t=1): _"last Tuesday afternoon at work"_
- `avoid energy crash after drinking → choosing ZeroFizz` [achieves (reversed)] (t=1): _"Just need something that doesn't crash, you know?"_
### Chain 2 [surface]
**Path**: `3 o'clock slump hitting` (job_trigger, t=?) → `needing something cold and caffeinated` (job_statement, t=?) → `choosing ZeroFizz` (solution_approach, t=?)

**Evidence**:
- `3 o'clock slump hitting → needing something cold and caffeinated` [triggers] (t=?): _"Was hitting that 3 o'clock slump"_
- `needing something cold and caffeinated → choosing ZeroFizz` [drives] (t=?): _"needed something cold and caffeinated"_
## Started — fewer than 3 nodes

### Chain 1 [surface]
**Path**: `stay focused through the afternoon` (gain_point, t=4) → `get things done in the afternoon` (job_statement, t=4)

**Evidence**:
- `stay focused through the afternoon → get things done in the afternoon` [supports] (t=4): _"Stay focused, I guess."_
### Chain 2 [surface]
**Path**: `everything falling apart after lunch when dragging` (pain_point, t=4) → `get things done in the afternoon` (job_statement, t=4)

**Evidence**:
- `everything falling apart after lunch when dragging → get things done in the afternoon` [implies] (t=4): _"everything falls apart after lunch if I'm dragging"_
### Chain 3 [surface]
**Path**: `skipping or under-eating lunch` (job_trigger, t=5) → `blood sugar dropping` (pain_point, t=5)

**Evidence**:
- `skipping or under-eating lunch → blood sugar dropping` [triggers] (t=5): _"Usually just skipped lunch or didn't eat enough earlier."_
### Chain 4 [surface]
**Path**: `skipping or under-eating lunch` (job_trigger, t=5) → `experiencing a mild crash later in the afternoon` (pain_point, t=5)

**Evidence**:
- `skipping or under-eating lunch → experiencing a mild crash later in the afternoon` [triggers] (t=5): _"Usually just skipped lunch or didn't eat enough earlier."_
## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

_No orphan nodes found._


## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
