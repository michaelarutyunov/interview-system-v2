# Causal Chain Extraction — 20260502_002525_zerofizz_beverage_mec_baseline_cooperative.json

## Source specs
- **Session ID**: e5edcc2d-ec09-43bd-b342-137711265acc
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Means-End Chain (`zerofizz_beverage_mec`)
- **Methodology**: `means_end_chain_v2_strict`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 12
- **Status**: Closing strategy selected
- **Saved at**: 2026-05-02T00:25:25.105199+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/means_end_chain_v2_strict.yaml`
- **Chain edge types**: leads_to
- **Permitted connections**:
  - `leads_to`: unconstrained
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 0

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 32 | 3 |
| Chain edges traversed | 37 | 26 |
| Edges (revises) | 0 | 0 |
| Node types | attribute, functional_consequence, instrumental_value, psychosocial_consequence | functional_consequence, instrumental_value, psychosocial_consequence |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches terminal_value — complete chain, no missing levels | 0 | 0 |
| Advanced | Reaches terminal_value (with one gap) or instrumental_value | 9 | 1 |
| Developing | Mid-level progression, terminal not reached | 8 | 0 |
| Started | Incomplete — fewer than 3 nodes | 3 | 0 |
| Lateral (excluded) | Same-type only chains | 0 | 0 |

---

## Full chains — complete, no missing levels

_No full chains found._

## Advanced chains — near-complete (one gap) or near-terminal

### Chain 1 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=7) → `sticky film on teeth after regular soda` (functional_consequence, t=8) → `not being constantly aware of oral discomfort` (functional_consequence, t=8) → `moving on without lingering annoyance` (functional_consequence, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `no guilt attached to drinking ZeroFizz` (psychosocial_consequence, t=9) → `feeling guilt-free about consumption` (psychosocial_consequence, t=3) → `keeping things reasonable / not overindulging` (instrumental_value, t=3) → `not allowing oneself to have it too easy / not cheating` (instrumental_value, t=3)

**Evidence**:
- `light / non-heavy formulation → sticky film on teeth after regular soda` [leads_to] (t=7): _"it's just not as heavy as regular soda"_
- `sticky film on teeth after regular soda → not being constantly aware of oral discomfort` [leads_to] (t=8): _"after regular soda there's that sticky film"_
- `not being constantly aware of oral discomfort → moving on without lingering annoyance` [leads_to] (t=8): _"I'm not constantly aware of my teeth feeling gross"_
- `moving on without lingering annoyance → not having to question whether one is making a bad choice` [leads_to] (t=9): _"I can just drink something and move on instead of being annoyed by that film coating everything"_
- `not having to question whether one is making a bad choice → no guilt attached to drinking ZeroFizz` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `no guilt attached to drinking ZeroFizz → feeling guilt-free about consumption` [leads_to] (t=9): _"With ZeroFizz it's just a drink, no guilt attached to it."_
- `feeling guilt-free about consumption → keeping things reasonable / not overindulging` [leads_to] (t=3): _"without feeling guilty about it, which honestly I do appreciate"_
- `keeping things reasonable / not overindulging → not allowing oneself to have it too easy / not cheating` [leads_to] (t=3): _"when I'm trying to keep things reasonable"_

### Chain 2 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=7) → `sticky film on teeth after regular soda` (functional_consequence, t=8) → `not being constantly aware of oral discomfort` (functional_consequence, t=8) → `moving on without lingering annoyance` (functional_consequence, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `no guilt attached to drinking ZeroFizz` (psychosocial_consequence, t=10) → `not pretending it is healthy / no self-deception about the choice` (psychosocial_consequence, t=10) → `making a reasonable decision without being preachy` (instrumental_value, t=10) → `making choices I can stand behind` (instrumental_value, t=10)

**Evidence**:
- `light / non-heavy formulation → sticky film on teeth after regular soda` [leads_to] (t=7): _"it's just not as heavy as regular soda"_
- `sticky film on teeth after regular soda → not being constantly aware of oral discomfort` [leads_to] (t=8): _"after regular soda there's that sticky film"_
- `not being constantly aware of oral discomfort → moving on without lingering annoyance` [leads_to] (t=8): _"I'm not constantly aware of my teeth feeling gross"_
- `moving on without lingering annoyance → not having to question whether one is making a bad choice` [leads_to] (t=9): _"I can just drink something and move on instead of being annoyed by that film coating everything"_
- `not having to question whether one is making a bad choice → no guilt attached to drinking ZeroFizz` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `no guilt attached to drinking ZeroFizz → not pretending it is healthy / no self-deception about the choice` [leads_to] (t=10): _"With ZeroFizz it's just a drink, no guilt attached to it."_
- `not pretending it is healthy / no self-deception about the choice → making a reasonable decision without being preachy` [leads_to] (t=10): _"it's not some guilty thing where I'm pretending it's healthy or whatever"_
- `making a reasonable decision without being preachy → making choices I can stand behind` [leads_to] (t=10): _"that feels like a reasonable decision without being preachy about it"_

### Chain 3 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=4) → `does not sit heavily in stomach` (functional_consequence, t=4) → `avoiding bloating after drinking` (functional_consequence, t=4) → `consuming multiple cans without guilt` (functional_consequence, t=3) → `feeling guilt-free about consumption` (psychosocial_consequence, t=3) → `keeping things reasonable / not overindulging` (instrumental_value, t=3) → `not allowing oneself to have it too easy / not cheating` (instrumental_value, t=3)

**Evidence**:
- `light / non-heavy formulation → does not sit heavily in stomach` [leads_to] (t=4): _"it's just not as heavy as regular soda"_
- `does not sit heavily in stomach → avoiding bloating after drinking` [leads_to] (t=4): _"you can drink a couple and it doesn't sit in your stomach the same way"_
- `avoiding bloating after drinking → consuming multiple cans without guilt` [leads_to] (t=4): _"you're not like... bloated or whatever after"_
- `consuming multiple cans without guilt → feeling guilt-free about consumption` [leads_to] (t=3): _"I can have a few of these without feeling guilty about it"_
- `feeling guilt-free about consumption → keeping things reasonable / not overindulging` [leads_to] (t=3): _"without feeling guilty about it, which honestly I do appreciate"_
- `keeping things reasonable / not overindulging → not allowing oneself to have it too easy / not cheating` [leads_to] (t=3): _"when I'm trying to keep things reasonable"_

### Chain 4 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=7) → `sticky film on teeth after regular soda` (functional_consequence, t=8) → `not being constantly aware of oral discomfort` (functional_consequence, t=8) → `moving on without lingering annoyance` (functional_consequence, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `no guilt attached to drinking ZeroFizz` (psychosocial_consequence, t=9) → `making choices I can stand behind` (instrumental_value, t=9)

**Evidence**:
- `light / non-heavy formulation → sticky film on teeth after regular soda` [leads_to] (t=7): _"it's just not as heavy as regular soda"_
- `sticky film on teeth after regular soda → not being constantly aware of oral discomfort` [leads_to] (t=8): _"after regular soda there's that sticky film"_
- `not being constantly aware of oral discomfort → moving on without lingering annoyance` [leads_to] (t=8): _"I'm not constantly aware of my teeth feeling gross"_
- `moving on without lingering annoyance → not having to question whether one is making a bad choice` [leads_to] (t=9): _"I can just drink something and move on instead of being annoyed by that film coating everything"_
- `not having to question whether one is making a bad choice → no guilt attached to drinking ZeroFizz` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `no guilt attached to drinking ZeroFizz → making choices I can stand behind` [leads_to] (t=9): _"With ZeroFizz it's just a drink, no guilt attached to it."_

### Chain 5 [surface]
**Path**: `zero sugar and calorie content` (attribute, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `no guilt attached to drinking ZeroFizz` (psychosocial_consequence, t=9) → `feeling guilt-free about consumption` (psychosocial_consequence, t=3) → `keeping things reasonable / not overindulging` (instrumental_value, t=3) → `not allowing oneself to have it too easy / not cheating` (instrumental_value, t=3)

**Evidence**:
- `zero sugar and calorie content → not having to question whether one is making a bad choice` [leads_to] (t=9): _"knowing I'm not loading up on sugar and calories"_
- `not having to question whether one is making a bad choice → no guilt attached to drinking ZeroFizz` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `no guilt attached to drinking ZeroFizz → feeling guilt-free about consumption` [leads_to] (t=9): _"With ZeroFizz it's just a drink, no guilt attached to it."_
- `feeling guilt-free about consumption → keeping things reasonable / not overindulging` [leads_to] (t=3): _"without feeling guilty about it, which honestly I do appreciate"_
- `keeping things reasonable / not overindulging → not allowing oneself to have it too easy / not cheating` [leads_to] (t=3): _"when I'm trying to keep things reasonable"_

### Chain 6 [surface]
**Path**: `zero sugar and calorie content` (attribute, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `no guilt attached to drinking ZeroFizz` (psychosocial_consequence, t=10) → `not pretending it is healthy / no self-deception about the choice` (psychosocial_consequence, t=10) → `making a reasonable decision without being preachy` (instrumental_value, t=10) → `making choices I can stand behind` (instrumental_value, t=10)

**Evidence**:
- `zero sugar and calorie content → not having to question whether one is making a bad choice` [leads_to] (t=9): _"knowing I'm not loading up on sugar and calories"_
- `not having to question whether one is making a bad choice → no guilt attached to drinking ZeroFizz` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `no guilt attached to drinking ZeroFizz → not pretending it is healthy / no self-deception about the choice` [leads_to] (t=10): _"With ZeroFizz it's just a drink, no guilt attached to it."_
- `not pretending it is healthy / no self-deception about the choice → making a reasonable decision without being preachy` [leads_to] (t=10): _"it's not some guilty thing where I'm pretending it's healthy or whatever"_
- `making a reasonable decision without being preachy → making choices I can stand behind` [leads_to] (t=10): _"that feels like a reasonable decision without being preachy about it"_

### Chain 7 [surface]
**Path**: `zero sugar and calorie content` (attribute, t=3) → `consuming multiple cans without guilt` (functional_consequence, t=3) → `feeling guilt-free about consumption` (psychosocial_consequence, t=3) → `keeping things reasonable / not overindulging` (instrumental_value, t=3) → `not allowing oneself to have it too easy / not cheating` (instrumental_value, t=3)

**Evidence**:
- `zero sugar and calorie content → consuming multiple cans without guilt` [leads_to] (t=3): _"knowing I'm not loading up on sugar and calories"_
- `consuming multiple cans without guilt → feeling guilt-free about consumption` [leads_to] (t=3): _"I can have a few of these without feeling guilty about it"_
- `feeling guilt-free about consumption → keeping things reasonable / not overindulging` [leads_to] (t=3): _"without feeling guilty about it, which honestly I do appreciate"_
- `keeping things reasonable / not overindulging → not allowing oneself to have it too easy / not cheating` [leads_to] (t=3): _"when I'm trying to keep things reasonable"_

### Chain 8 [surface]
**Path**: `zero sugar and calorie content` (attribute, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `no guilt attached to drinking ZeroFizz` (psychosocial_consequence, t=9) → `making choices I can stand behind` (instrumental_value, t=9)

**Evidence**:
- `zero sugar and calorie content → not having to question whether one is making a bad choice` [leads_to] (t=9): _"knowing I'm not loading up on sugar and calories"_
- `not having to question whether one is making a bad choice → no guilt attached to drinking ZeroFizz` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `no guilt attached to drinking ZeroFizz → making choices I can stand behind` [leads_to] (t=9): _"With ZeroFizz it's just a drink, no guilt attached to it."_

### Chain 9 [surface]
**Path**: `weird chemical taste as proof of difference from regular soda` (functional_consequence, t=2) → `feeling like cheating if diet soda tastes too good` (psychosocial_consequence, t=2) → `not allowing oneself to have it too easy / not cheating` (instrumental_value, t=2)

**Evidence**:
- `weird chemical taste as proof of difference from regular soda → feeling like cheating if diet soda tastes too good` [leads_to] (t=2): _"the weird chemical taste is basically proof that it's actually different, you know?"_
- `feeling like cheating if diet soda tastes too good → not allowing oneself to have it too easy / not cheating` [leads_to] (t=2): _"like if it tasted exactly like regular soda i'd feel like i was cheating or something"_

### Chain 1 [canonical]
**Path**: `consumption_behavior` (functional_consequence, t=?) → `guilt_reduction` (psychosocial_consequence, t=?) → `choice_integrity` (instrumental_value, t=?)

**Evidence**:
- `consumption_behavior → guilt_reduction` [leads_to] (t=?): _"I grabbed a diet cola from the break room"_
- `guilt_reduction → choice_integrity` [leads_to] (t=?): _"without feeling guilty about it, which honestly I do appreciate"_

## Developing chains — mid-level progression

### Chain 1 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=7) → `sticky film on teeth after regular soda` (functional_consequence, t=8) → `not being constantly aware of oral discomfort` (functional_consequence, t=8) → `moving on without lingering annoyance` (functional_consequence, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `reduced mental load throughout the day` (psychosocial_consequence, t=8) → `reduced oral discomfort awareness throughout the day` (psychosocial_consequence, t=7) → `feeling drained in the afternoon` (psychosocial_consequence, t=7)

**Evidence**:
- `light / non-heavy formulation → sticky film on teeth after regular soda` [leads_to] (t=7): _"it's just not as heavy as regular soda"_
- `sticky film on teeth after regular soda → not being constantly aware of oral discomfort` [leads_to] (t=8): _"after regular soda there's that sticky film"_
- `not being constantly aware of oral discomfort → moving on without lingering annoyance` [leads_to] (t=8): _"I'm not constantly aware of my teeth feeling gross"_
- `moving on without lingering annoyance → not having to question whether one is making a bad choice` [leads_to] (t=9): _"I can just drink something and move on instead of being annoyed by that film coating everything"_
- `not having to question whether one is making a bad choice → reduced mental load throughout the day` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `reduced mental load throughout the day → reduced oral discomfort awareness throughout the day` [leads_to] (t=8): _"It's less of a mental thing to deal with throughout the day"_
- `reduced oral discomfort awareness throughout the day → feeling drained in the afternoon` [leads_to] (t=7): _"less aware of it being stuck on my teeth or whatever... that matters for how I feel throughout the day"_

### Chain 2 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=4) → `does not sit heavily in stomach` (functional_consequence, t=4) → `avoiding bloating after drinking` (functional_consequence, t=5) → `uncomfortable heavy feeling after drinking` (functional_consequence, t=6) → `feeling sluggish at work` (functional_consequence, t=?) → `need for an energy boost` (functional_consequence, t=?) → `grabbing a diet cola` (functional_consequence, t=?)

**Evidence**:
- `light / non-heavy formulation → does not sit heavily in stomach` [leads_to] (t=4): _"it's just not as heavy as regular soda"_
- `does not sit heavily in stomach → avoiding bloating after drinking` [leads_to] (t=4): _"you can drink a couple and it doesn't sit in your stomach the same way"_
- `avoiding bloating after drinking → uncomfortable heavy feeling after drinking` [leads_to] (t=5): _"you're not like... bloated or whatever after"_
- `uncomfortable heavy feeling after drinking → feeling sluggish at work` [leads_to] (t=6): _"you want to enjoy a drink but then you're stuck feeling uncomfortable for the next hour or whatever"_
- `feeling sluggish at work → need for an energy boost` [leads_to] (t=?): _"I was sitting at my desk feeling kind of sluggish"_
- `need for an energy boost → grabbing a diet cola` [leads_to] (t=?): _"needed something to wake me up a bit"_

### Chain 3 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=4) → `does not sit heavily in stomach` (functional_consequence, t=4) → `avoiding bloating after drinking` (functional_consequence, t=5) → `uncomfortable heavy feeling after drinking` (functional_consequence, t=6) → `feeling sluggish at work` (functional_consequence, t=6) → `difficulty focusing on work` (functional_consequence, t=6) → `feeling drained in the afternoon` (psychosocial_consequence, t=6)

**Evidence**:
- `light / non-heavy formulation → does not sit heavily in stomach` [leads_to] (t=4): _"it's just not as heavy as regular soda"_
- `does not sit heavily in stomach → avoiding bloating after drinking` [leads_to] (t=4): _"you can drink a couple and it doesn't sit in your stomach the same way"_
- `avoiding bloating after drinking → uncomfortable heavy feeling after drinking` [leads_to] (t=5): _"you're not like... bloated or whatever after"_
- `uncomfortable heavy feeling after drinking → feeling sluggish at work` [leads_to] (t=6): _"you want to enjoy a drink but then you're stuck feeling uncomfortable for the next hour or whatever"_
- `feeling sluggish at work → difficulty focusing on work` [leads_to] (t=6): _"I was sitting at my desk feeling kind of sluggish"_
- `difficulty focusing on work → feeling drained in the afternoon` [leads_to] (t=6): _"I can't focus as well on work stuff"_

### Chain 4 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=7) → `sticky film on teeth after regular soda` (functional_consequence, t=8) → `not being constantly aware of oral discomfort` (functional_consequence, t=8) → `moving on without lingering annoyance` (functional_consequence, t=8) → `reduced mental load throughout the day` (psychosocial_consequence, t=8) → `reduced oral discomfort awareness throughout the day` (psychosocial_consequence, t=7) → `feeling drained in the afternoon` (psychosocial_consequence, t=7)

**Evidence**:
- `light / non-heavy formulation → sticky film on teeth after regular soda` [leads_to] (t=7): _"it's just not as heavy as regular soda"_
- `sticky film on teeth after regular soda → not being constantly aware of oral discomfort` [leads_to] (t=8): _"after regular soda there's that sticky film"_
- `not being constantly aware of oral discomfort → moving on without lingering annoyance` [leads_to] (t=8): _"I'm not constantly aware of my teeth feeling gross"_
- `moving on without lingering annoyance → reduced mental load throughout the day` [leads_to] (t=8): _"I can just drink something and move on instead of being annoyed by that film coating everything"_
- `reduced mental load throughout the day → reduced oral discomfort awareness throughout the day` [leads_to] (t=8): _"It's less of a mental thing to deal with throughout the day"_
- `reduced oral discomfort awareness throughout the day → feeling drained in the afternoon` [leads_to] (t=7): _"less aware of it being stuck on my teeth or whatever... that matters for how I feel throughout the day"_

### Chain 5 [surface]
**Path**: `zero sugar and calorie content` (attribute, t=9) → `not having to question whether one is making a bad choice` (functional_consequence, t=9) → `reduced mental load throughout the day` (psychosocial_consequence, t=8) → `reduced oral discomfort awareness throughout the day` (psychosocial_consequence, t=7) → `feeling drained in the afternoon` (psychosocial_consequence, t=7)

**Evidence**:
- `zero sugar and calorie content → not having to question whether one is making a bad choice` [leads_to] (t=9): _"knowing I'm not loading up on sugar and calories"_
- `not having to question whether one is making a bad choice → reduced mental load throughout the day` [leads_to] (t=9): _"I don't have to think about whether I'm making a bad choice, you know?"_
- `reduced mental load throughout the day → reduced oral discomfort awareness throughout the day` [leads_to] (t=8): _"It's less of a mental thing to deal with throughout the day"_
- `reduced oral discomfort awareness throughout the day → feeling drained in the afternoon` [leads_to] (t=7): _"less aware of it being stuck on my teeth or whatever... that matters for how I feel throughout the day"_

### Chain 6 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=4) → `does not sit heavily in stomach` (functional_consequence, t=4) → `avoiding bloating after drinking` (functional_consequence, t=5) → `uncomfortable heavy feeling after drinking` (functional_consequence, t=5) → `disruption to the rest of the day` (psychosocial_consequence, t=5)

**Evidence**:
- `light / non-heavy formulation → does not sit heavily in stomach` [leads_to] (t=4): _"it's just not as heavy as regular soda"_
- `does not sit heavily in stomach → avoiding bloating after drinking` [leads_to] (t=4): _"you can drink a couple and it doesn't sit in your stomach the same way"_
- `avoiding bloating after drinking → uncomfortable heavy feeling after drinking` [leads_to] (t=5): _"you're not like... bloated or whatever after"_
- `uncomfortable heavy feeling after drinking → disruption to the rest of the day` [leads_to] (t=5): _"you want to enjoy a drink but then you're stuck feeling uncomfortable for the next hour or whatever"_

### Chain 7 [surface]
**Path**: `light / non-heavy formulation` (attribute, t=7) → `sticky film on teeth after regular soda` (functional_consequence, t=7) → `reduced oral discomfort awareness throughout the day` (psychosocial_consequence, t=7) → `feeling drained in the afternoon` (psychosocial_consequence, t=7)

**Evidence**:
- `light / non-heavy formulation → sticky film on teeth after regular soda` [leads_to] (t=7): _"it's just not as heavy as regular soda"_
- `sticky film on teeth after regular soda → reduced oral discomfort awareness throughout the day` [leads_to] (t=7): _"after regular soda there's that sticky film"_
- `reduced oral discomfort awareness throughout the day → feeling drained in the afternoon` [leads_to] (t=7): _"less aware of it being stuck on my teeth or whatever... that matters for how I feel throughout the day"_

### Chain 8 [surface]
**Path**: `absence of weird aftertaste` (attribute, t=1) → `actually drinkable / pleasant taste experience` (functional_consequence, t=1) → `not feeling like doing a health thing` (psychosocial_consequence, t=1)

**Evidence**:
- `absence of weird aftertaste → actually drinkable / pleasant taste experience` [leads_to] (t=1): _"I like that it doesn't have the weird aftertaste some diet sodas have"_
- `actually drinkable / pleasant taste experience → not feeling like doing a health thing` [leads_to] (t=1): _"so it's actually drinkable without feeling like I'm doing some health thing"_

## Started — fewer than 3 nodes

### Chain 1 [surface]
**Path**: `availability in break room` (attribute, t=?) → `grabbing a diet cola` (functional_consequence, t=?)

**Evidence**:
- `availability in break room → grabbing a diet cola` [leads_to] (t=?): _"it was just there"_

### Chain 2 [surface]
**Path**: `ease of access` (attribute, t=?) → `grabbing a diet cola` (functional_consequence, t=?)

**Evidence**:
- `ease of access → grabbing a diet cola` [leads_to] (t=?): _"seemed like the easiest option"_

### Chain 3 [surface]
**Path**: `weird chemical taste as proof of difference from regular soda` (functional_consequence, t=2) → `not feeling like doing a health thing` (psychosocial_consequence, t=2)

**Evidence**:
- `weird chemical taste as proof of difference from regular soda → not feeling like doing a health thing` [leads_to] (t=2): _"the weird chemical taste is basically proof that it's actually different, you know?"_

## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

_No orphan nodes found._


## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/means_end_chain_v2_strict.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
