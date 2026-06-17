# Causal Chain Extraction — 20260505_225354_zerofizz_beverage_jtbd_baseline_cooperative.json

## Source specs
- **Session ID**: 0924bcf4-9343-479e-acf5-98bb552c0bdf
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 10
- **Status**: Closing strategy selected
- **Saved at**: 2026-05-05T22:53:54.914314+00:00

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
- **Revises edges excluded from traversal**: 0

## Graph summary
- **Conversation nodes**: 32
- **Themes (canonical slots)**: 3
- **Chain edges traversed**: 47
- **Edges (revises)**: 0

## Chain completeness summary
| Tier | Description | Count |
|------|-------------|-------|
| Full | Reaches solution_approach — complete chain, no missing levels | 3 |
| Advanced | Reaches solution_approach (with one gap) or emotional_job / social_job | 24 |
| Developing | Mid-level progression, terminal not reached | 0 |
| Lateral (excluded) | Same-type only chains | 1 |

---

## Full chains — complete, no missing levels

### Chain 1
**Path**:

  → `navigating decision fatigue across food and drink choices daily` (job_context, L0, t=5)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=7)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `navigating decision fatigue across food and drink choices daily → absence of nagging doubt during consumption` [triggers] (t=5): _"I'm already making a ton of decisions every day, you know? Like, with food and drinks I just want to grab something and not have to think about whether it's the right call or whatever."_
- `absence of nagging doubt during consumption → feel like progress toward health goals isn't being undone by a drink choice` [achieves (reversed)] (t=7): _"one less thing nagging at me while I'm drinking it"_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 2
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=7)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `wanting something fizzy in the afternoon → absence of nagging doubt during consumption` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `absence of nagging doubt during consumption → feel like progress toward health goals isn't being undone by a drink choice` [achieves (reversed)] (t=7): _"one less thing nagging at me while I'm drinking it"_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 3
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=7)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → absence of nagging doubt during consumption` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `absence of nagging doubt during consumption → feel like progress toward health goals isn't being undone by a drink choice` [achieves (reversed)] (t=7): _"one less thing nagging at me while I'm drinking it"_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

## Advanced chains — near-complete (one gap) or near-terminal

### Chain 1
**Path**:

  → `self-doubt about drink choice persists beyond the physical experience` (pain_point, L1, t=?)  
  → `sugar crash is temporary and finite compared to lingering regret` (pain_point, L1, t=?)  
  → `escape persistent post-consumption regret about drink choices` (emotional_job, L3, t=?)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `self-doubt about drink choice persists beyond the physical experience → sugar crash is temporary and finite compared to lingering regret` [supports] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers."_
- `sugar crash is temporary and finite compared to lingering regret → escape persistent post-consumption regret about drink choices` [implies] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_
- `escape persistent post-consumption regret about drink choices → feel like progress toward health goals isn't being undone by a drink choice` [supports] (t=?): _"the self-doubt thing is more like... it's in my head the whole time... the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 2
**Path**:

  → `self-doubt about drink choice persists beyond the physical experience` (pain_point, L1, t=?)  
  → `sugar crash is temporary and finite compared to lingering regret` (pain_point, L1, t=?)  
  → `escape persistent post-consumption regret about drink choices` (emotional_job, L3, t=?)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=?)  

**Evidence**:
- `self-doubt about drink choice persists beyond the physical experience → sugar crash is temporary and finite compared to lingering regret` [supports] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers."_
- `sugar crash is temporary and finite compared to lingering regret → escape persistent post-consumption regret about drink choices` [implies] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_
- `escape persistent post-consumption regret about drink choices → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=?): _"the self-doubt thing is more like... it's in my head the whole time... the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_

### Chain 3
**Path**:

  → `self-doubt about drink choice persists beyond the physical experience` (pain_point, L1, t=?)  
  → `sugar crash is temporary and finite compared to lingering regret` (pain_point, L1, t=?)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `self-doubt about drink choice persists beyond the physical experience → sugar crash is temporary and finite compared to lingering regret` [supports] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers."_
- `sugar crash is temporary and finite compared to lingering regret → feel like progress toward health goals isn't being undone by a drink choice` [implies] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 4
**Path**:

  → `self-doubt about drink choice persists beyond the physical experience` (pain_point, L1, t=?)  
  → `escape persistent post-consumption regret about drink choices` (emotional_job, L3, t=?)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `self-doubt about drink choice persists beyond the physical experience → escape persistent post-consumption regret about drink choices` [implies] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers."_
- `escape persistent post-consumption regret about drink choices → feel like progress toward health goals isn't being undone by a drink choice` [supports] (t=?): _"the self-doubt thing is more like... it's in my head the whole time... the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 5
**Path**:

  → `avoiding a sugar crash during long sedentary work sessions` (gain_point, L1, t=?)  
  → `enjoy the drink without mental load` (gain_point, L1, t=3)  
  → `feel at ease and guilt-free while consuming a drink` (emotional_job, L3, t=3)  

**Evidence**:
- `avoiding a sugar crash during long sedentary work sessions → enjoy the drink without mental load` [supports] (t=?): _"the main thing is just not wanting the sugar crash later if I'm gonna be sitting at my desk for hours"_
- `enjoy the drink without mental load → feel at ease and guilt-free while consuming a drink` [supports] (t=3): _"I can just... enjoy the drink without the mental load"_

### Chain 6
**Path**:

  → `navigating high cognitive demands throughout the day` (job_context, L0, t=2)  
  → `relief from nagging self-doubt while drinking` (emotional_job, L3, t=4)  
  → `feel at ease and guilt-free while consuming a drink` (emotional_job, L3, t=4)  

**Evidence**:
- `navigating high cognitive demands throughout the day → relief from nagging self-doubt while drinking` [triggers] (t=2): _"there's already so much stuff to think about during the day, you know?"_
- `relief from nagging self-doubt while drinking → feel at ease and guilt-free while consuming a drink` [supports] (t=4): _"it's kind of a relief. Like I can just enjoy it without that nagging feeling in the back of my head"_

### Chain 7
**Path**:

  → `navigating decision fatigue across food and drink choices daily` (job_context, L0, t=5)  
  → `avoiding self-judgment about health-related drink choices` (pain_point, L1, t=5)  
  → `feel in control of health goals without active deliberation` (emotional_job, L3, t=5)  

**Evidence**:
- `navigating decision fatigue across food and drink choices daily → avoiding self-judgment about health-related drink choices` [triggers] (t=5): _"I'm already making a ton of decisions every day, you know? Like, with food and drinks I just want to grab something and not have to think about whether it's the right call or whatever."_
- `avoiding self-judgment about health-related drink choices → feel in control of health goals without active deliberation` [supports] (t=5): _"I don't have to think about whether I'm making a stupid choice health-wise"_

### Chain 8
**Path**:

  → `navigating decision fatigue across food and drink choices daily` (job_context, L0, t=5)  
  → `avoiding self-judgment about health-related drink choices` (pain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `navigating decision fatigue across food and drink choices daily → avoiding self-judgment about health-related drink choices` [triggers] (t=5): _"I'm already making a ton of decisions every day, you know? Like, with food and drinks I just want to grab something and not have to think about whether it's the right call or whatever."_
- `avoiding self-judgment about health-related drink choices → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [addresses (reversed)] (t=7): _"I don't have to think about whether I'm making a stupid choice health-wise"_

### Chain 9
**Path**:

  → `navigating decision fatigue across food and drink choices daily` (job_context, L0, t=5)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=6)  
  → `feel in control of health goals without active deliberation` (emotional_job, L3, t=6)  

**Evidence**:
- `navigating decision fatigue across food and drink choices daily → absence of nagging doubt during consumption` [triggers] (t=5): _"I'm already making a ton of decisions every day, you know? Like, with food and drinks I just want to grab something and not have to think about whether it's the right call or whatever."_
- `absence of nagging doubt during consumption → feel in control of health goals without active deliberation` [supports] (t=6): _"one less thing nagging at me while I'm drinking it"_

### Chain 10
**Path**:

  → `navigating decision fatigue across food and drink choices daily` (job_context, L0, t=5)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `navigating decision fatigue across food and drink choices daily → absence of nagging doubt during consumption` [triggers] (t=5): _"I'm already making a ton of decisions every day, you know? Like, with food and drinks I just want to grab something and not have to think about whether it's the right call or whatever."_
- `absence of nagging doubt during consumption → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [achieves (reversed)] (t=7): _"one less thing nagging at me while I'm drinking it"_

### Chain 11
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `wanting something fizzy in the afternoon → feel like progress toward health goals isn't being undone by a drink choice` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 12
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `avoiding a sugar crash in the afternoon` (pain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `wanting something fizzy in the afternoon → avoiding a sugar crash in the afternoon` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `avoiding a sugar crash in the afternoon → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"don't want all the sugar crash."_

### Chain 13
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `avoiding self-judgment about health-related drink choices` (pain_point, L1, t=5)  
  → `feel in control of health goals without active deliberation` (emotional_job, L3, t=5)  

**Evidence**:
- `wanting something fizzy in the afternoon → avoiding self-judgment about health-related drink choices` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `avoiding self-judgment about health-related drink choices → feel in control of health goals without active deliberation` [supports] (t=5): _"I don't have to think about whether I'm making a stupid choice health-wise"_

### Chain 14
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `avoiding self-judgment about health-related drink choices` (pain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `wanting something fizzy in the afternoon → avoiding self-judgment about health-related drink choices` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `avoiding self-judgment about health-related drink choices → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [addresses (reversed)] (t=7): _"I don't have to think about whether I'm making a stupid choice health-wise"_

### Chain 15
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=6)  
  → `feel in control of health goals without active deliberation` (emotional_job, L3, t=6)  

**Evidence**:
- `wanting something fizzy in the afternoon → absence of nagging doubt during consumption` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `absence of nagging doubt during consumption → feel in control of health goals without active deliberation` [supports] (t=6): _"one less thing nagging at me while I'm drinking it"_

### Chain 16
**Path**:

  → `wanting something fizzy in the afternoon` (job_trigger, L0, t=7)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `wanting something fizzy in the afternoon → absence of nagging doubt during consumption` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `absence of nagging doubt during consumption → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [achieves (reversed)] (t=7): _"one less thing nagging at me while I'm drinking it"_

### Chain 17
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → feel like progress toward health goals isn't being undone by a drink choice` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

### Chain 18
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `avoiding a sugar crash in the afternoon` (pain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → avoiding a sugar crash in the afternoon` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `avoiding a sugar crash in the afternoon → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"don't want all the sugar crash."_

### Chain 19
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `avoiding self-judgment about health-related drink choices` (pain_point, L1, t=5)  
  → `feel in control of health goals without active deliberation` (emotional_job, L3, t=5)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → avoiding self-judgment about health-related drink choices` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `avoiding self-judgment about health-related drink choices → feel in control of health goals without active deliberation` [supports] (t=5): _"I don't have to think about whether I'm making a stupid choice health-wise"_

### Chain 20
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `avoiding self-judgment about health-related drink choices` (pain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → avoiding self-judgment about health-related drink choices` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `avoiding self-judgment about health-related drink choices → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [addresses (reversed)] (t=7): _"I don't have to think about whether I'm making a stupid choice health-wise"_

### Chain 21
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=6)  
  → `feel in control of health goals without active deliberation` (emotional_job, L3, t=6)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → absence of nagging doubt during consumption` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `absence of nagging doubt during consumption → feel in control of health goals without active deliberation` [supports] (t=6): _"one less thing nagging at me while I'm drinking it"_

### Chain 22
**Path**:

  → `afternoon slump as context for seeking a fizzy drink` (job_context, L0, t=7)  
  → `absence of nagging doubt during consumption` (gain_point, L1, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `afternoon slump as context for seeking a fizzy drink → absence of nagging doubt during consumption` [triggers] (t=7): _"Especially in the afternoon when I want something fizzy but don't want all the sugar crash."_
- `absence of nagging doubt during consumption → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [achieves (reversed)] (t=7): _"one less thing nagging at me while I'm drinking it"_

### Chain 23
**Path**:

  → `self-doubt about drink choice persists beyond the physical experience` (pain_point, L1, t=?)  
  → `escape persistent post-consumption regret about drink choices` (emotional_job, L3, t=?)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=?)  

**Evidence**:
- `self-doubt about drink choice persists beyond the physical experience → escape persistent post-consumption regret about drink choices` [implies] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers."_
- `escape persistent post-consumption regret about drink choices → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=?): _"the self-doubt thing is more like... it's in my head the whole time... the feeling of like, 'why did I just do that to myself' lingers. It's annoying."_

### Chain 24
**Path**:

  → `self-doubt about drink choice persists beyond the physical experience` (pain_point, L1, t=?)  
  → `feel like progress toward health goals isn't being undone by a drink choice` (emotional_job, L3, t=7)  
  → `choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` (solution_approach, L4, t=7)  

**Evidence**:
- `self-doubt about drink choice persists beyond the physical experience → feel like progress toward health goals isn't being undone by a drink choice` [implies] (t=?): _"The sugar crash happens and then it's over, but the feeling of like, 'why did I just do that to myself' lingers."_
- `feel like progress toward health goals isn't being undone by a drink choice → choosing ZeroFizz as a fizzy drink that avoids sugar crash and self-doubt` [drives] (t=7): _"I can just grab it without feeling like I'm undoing whatever I'm trying to do."_

## Developing chains — mid-level progression

_No developing chains found._

## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `grabbing whatever drink is available in the fridge` (solution_approach, L4, t=0) — _"I grab whatever's in the fridge most days, and if there's a sugar-free option there I'll take it"_
- `opportunistic availability of sugar-free option prompts selection` (job_trigger, L0, t=0) — _"if there's a sugar-free option there I'll take it"_
- `low intentionality in choosing sugar-free over alternatives` (pain_point, L1, t=0) — _"it's not like I'm choosing it over something else with a lot of intention"_
- `sitting at desk for extended hours during the workday` (job_context, L0, t=0) — _"if I'm gonna be sitting at my desk for hours"_
- `maintain steady energy and focus through long desk-based work` (job_statement, L2, t=0) — _"the main thing is just not wanting the sugar crash later if I'm gonna be sitting at my desk for hours"_
- `minimising decision effort when grabbing a drink` (job_statement, L2, t=1) — _"it's more about not having to think about it"_
- `drink is immediately accessible without a separate store trip` (gain_point, L1, t=1) — _"I want it to just be there instead of having to go to a different store or whatever"_
- `having to go to a different store to find a suitable drink` (pain_point, L1, t=1) — _"instead of having to go to a different store or whatever"_
- `feel less guilty about drink choice without strict dieting` (emotional_job, L3, t=1) — _"just feels less guilty I guess? I know that sounds dumb but I'm not trying to be super strict about it or anything"_
- `reduce mental load around food and drink decisions` (emotional_job, L3, t=1) — _"it's just... easier on my head"_
- `being at the store and choosing a drink` (job_context, L0, t=2) — _"when I'm at the store or whatever, I don't want to stand there weighing pros and cons of every drink"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
