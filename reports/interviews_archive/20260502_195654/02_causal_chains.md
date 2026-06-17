# Causal Chain Extraction — 20260502_195654_zerofizz_beverage_jtbd_baseline_cooperative.json

## Source specs
- **Session ID**: 1eaf8a07-0bcd-4056-be22-aca62c381005
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 6
- **Status**: all_nodes_exhausted
- **Saved at**: 2026-05-02T19:56:54.416329+00:00

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
- **Revises edges excluded from traversal**: 1

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 15 | 3 |
| Chain edges traversed | 20 | 17 |
| Edges (revises) | 1 | 0 |
| Node types | emotional_job, gain_point, job_context, job_statement, job_trigger, pain_point, solution_approach | emotional_job, pain_point |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches solution_approach — complete chain, no missing levels | 2 | 0 |
| Advanced | Reaches solution_approach (with one gap) or emotional_job / social_job | 2 | 0 |
| Developing | Mid-level progression, terminal not reached | 0 | 0 |
| Started | Incomplete — fewer than 3 nodes | 4 | 1 |
| Lateral (excluded) | Same-type only chains | 0 | 0 |

---

## Full chains — complete, no missing levels

### Chain 1 [surface]
**Path**: `working at desk in the afternoon` (job_context, t=1) → `stomach heaviness blocking productivity` (pain_point, t=1) → `get a satisfying, flavorful drink without heaviness` (job_statement, t=?) → `choosing LaCroix as afternoon desk drink` (solution_approach, t=?)

**Evidence**:
- `working at desk in the afternoon → stomach heaviness blocking productivity` [triggers] (t=1): _"I was at my desk working, probably around 3pm"_
- `stomach heaviness blocking productivity → get a satisfying, flavorful drink without heaviness` [implies] (t=1): _"my stomach gets this heavy feeling and then i'm just sitting there waiting for it to wear off before i can do anything else"_
- `get a satisfying, flavorful drink without heaviness → choosing LaCroix as afternoon desk drink` [drives] (t=?): _"I needed something to drink that wasn't just water... I just like the taste and it feels less heavy than regular soda"_

### Chain 2 [surface]
**Path**: `already had morning coffee, avoiding more caffeine` (job_trigger, t=?) → `needing something more interesting than plain water` (pain_point, t=?) → `get a satisfying, flavorful drink without heaviness` (job_statement, t=?) → `choosing LaCroix as afternoon desk drink` (solution_approach, t=?)

**Evidence**:
- `already had morning coffee, avoiding more caffeine → needing something more interesting than plain water` [triggers] (t=?): _"I'd already had coffee that morning and didn't want more caffeine"_
- `needing something more interesting than plain water → get a satisfying, flavorful drink without heaviness` [implies] (t=?): _"I needed something to drink that wasn't just water"_
- `get a satisfying, flavorful drink without heaviness → choosing LaCroix as afternoon desk drink` [drives] (t=?): _"I needed something to drink that wasn't just water... I just like the taste and it feels less heavy than regular soda"_

## Advanced chains — near-complete (one gap) or near-terminal

### Chain 1 [surface]
**Path**: `feeling too heavy or weighed down by regular soda` (pain_point, t=?) → `get a satisfying, flavorful drink without heaviness` (job_statement, t=?) → `choosing LaCroix as afternoon desk drink` (solution_approach, t=?)

**Evidence**:
- `feeling too heavy or weighed down by regular soda → get a satisfying, flavorful drink without heaviness` [implies] (t=?): _"it feels less heavy than regular soda"_
- `get a satisfying, flavorful drink without heaviness → choosing LaCroix as afternoon desk drink` [drives] (t=?): _"I needed something to drink that wasn't just water... I just like the taste and it feels less heavy than regular soda"_

### Chain 2 [surface]
**Path**: `taking excessive breaks and phone scrolling instead of working` (pain_point, t=2) → `get a satisfying, flavorful drink without heaviness` (job_statement, t=?) → `choosing LaCroix as afternoon desk drink` (solution_approach, t=?)

**Evidence**:
- `taking excessive breaks and phone scrolling instead of working → get a satisfying, flavorful drink without heaviness` [implies] (t=2): _"I end up taking more breaks or scrolling through my phone more than I probably should"_
- `get a satisfying, flavorful drink without heaviness → choosing LaCroix as afternoon desk drink` [drives] (t=?): _"I needed something to drink that wasn't just water... I just like the taste and it feels less heavy than regular soda"_

## Developing chains — mid-level progression

_No developing chains found._

## Started — fewer than 3 nodes

### Chain 1 [surface]
**Path**: `feeling too heavy or weighed down by regular soda` (pain_point, t=?) → `choosing LaCroix as afternoon desk drink` (solution_approach, t=?)

**Evidence**:
- `feeling too heavy or weighed down by regular soda → choosing LaCroix as afternoon desk drink` [addresses (reversed)] (t=?): _"it feels less heavy than regular soda"_

### Chain 2 [surface]
**Path**: `light, enjoyable taste without caffeine or heaviness` (gain_point, t=?) → `choosing LaCroix as afternoon desk drink` (solution_approach, t=?)

**Evidence**:
- `light, enjoyable taste without caffeine or heaviness → choosing LaCroix as afternoon desk drink` [achieves (reversed)] (t=?): _"I just like the taste and it feels less heavy than regular soda"_

### Chain 3 [surface]
**Path**: `light, enjoyable taste without caffeine or heaviness` (gain_point, t=3) → `choosing ZeroFizz as afternoon drink` (solution_approach, t=3)

**Evidence**:
- `light, enjoyable taste without caffeine or heaviness → choosing ZeroFizz as afternoon drink` [achieves (reversed)] (t=3): _"I just like the taste and it feels less heavy than regular soda"_

### Chain 4 [surface]
**Path**: `avoid guilt about drinking soda` (emotional_job, t=3) → `choosing ZeroFizz as afternoon drink` (solution_approach, t=3)

**Evidence**:
- `avoid guilt about drinking soda → choosing ZeroFizz as afternoon drink` [drives] (t=3): _"I'll grab it because it's less guilt than regular soda"_

### Chain 1 [canonical]
**Path**: `focus_impairment` (pain_point, t=?) → `guilt_avoidance` (emotional_job, t=?)

**Evidence**:
- `focus_impairment → guilt_avoidance` [triggers] (t=?): _"it makes it harder to focus. Like, I'll be sitting there trying to work and just feel kind of sluggish"_

## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `drink choice does not change phone scrolling habit` (pain_point) — _"The drink itself doesn't really change that habit, you know?"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
