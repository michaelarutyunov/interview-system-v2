# Causal Chain Extraction — 20260501_150342_zerofizz_beverage_mec_baseline_cooperative.json

## Source specs
- **Session ID**: abd74971-703d-4d8e-886a-eeeed97a6469
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Means-End Chain (`zerofizz_beverage_mec`)
- **Methodology**: `means_end_chain_v2_strict`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 12
- **Status**: Closing strategy selected
- **Saved at**: 2026-05-01T15:03:42.593763+00:00

## Extraction config
- **Chain rules source**: `config/chain_rules/means_end_chain_v2_strict.yaml`
- **Chain edge types**: leads_to
- **Permitted connections**:
  - `leads_to`: unconstrained
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 3

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 31 | 6 |
| Chain edges traversed | 40 | 27 |
| Edges (revises) | 2 | 1 |
| Node types | attribute, functional_consequence, psychosocial_consequence | attribute, functional_consequence, psychosocial_consequence |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|------------------|
| Full | Reaches terminal_value — complete chain, no missing levels | 0 | 0 |
| Advanced | Reaches terminal_value (with one gap) or instrumental_value | 0 | 0 |
| Developing | Mid-level progression, terminal not reached | 18 | 16 |
| Started | Incomplete — fewer than 3 nodes | 0 | 0 |
| Lateral (excluded) | Same-type only chains | 3 | 0 |

---

## Full chains — complete, no missing levels

_No full chains found._

## Advanced chains — near-complete (one gap) or near-terminal

_No advanced chains found._

## Developing chains — mid-level progression

### Chain 1 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=2) → `carbonation level` (attribute, t=4) → `taste expectations specific to soda category` (functional_consequence, t=5) → `authentic soda experience` (functional_consequence, t=5) → `not overcomplicating or over-healthifying the product` (functional_consequence, t=5) → `understanding what consumers want from soda` (psychosocial_consequence, t=5) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=5)

**Evidence**:
- `acceptable taste despite no sugar → carbonation level` [leads_to] (t=2): _"if I can find it that doesn't taste completely awful"_
- `carbonation level → taste expectations specific to soda category` [leads_to] (t=4): _"the carbonation level is probably the biggest thing"_
- `taste expectations specific to soda category → authentic soda experience` [leads_to] (t=5): _"The taste thing is pretty specific to what I expect from a soda, you know?"_
- `authentic soda experience → not overcomplicating or over-healthifying the product` [leads_to] (t=5): _"It's a soda that tastes like a soda"_
- `not overcomplicating or over-healthifying the product → understanding what consumers want from soda` [leads_to] (t=5): _"they're not trying to be something weird or health-obsessed about it"_
- `understanding what consumers want from soda → brand trustworthiness and consumer understanding` [leads_to] (t=5): _"it just means they actually get what people want from a soda"_

### Chain 2 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=?) → `zero sugar formulation` (attribute, t=1) → `absence of artificial sweetener aftertaste` (attribute, t=7) → `taste quality achieved without chemical flavor` (functional_consequence, t=7) → `inference that product was tested with real consumers` (psychosocial_consequence, t=8) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=8)

**Evidence**:
- `acceptable taste despite no sugar → zero sugar formulation` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `zero sugar formulation → absence of artificial sweetener aftertaste` [leads_to] (t=1): _"it's usually something with zero sugar"_
- `absence of artificial sweetener aftertaste → taste quality achieved without chemical flavor` [leads_to] (t=7): _"ZeroFizz doesn't really have that artificial sweetener aftertaste"_
- `taste quality achieved without chemical flavor → inference that product was tested with real consumers` [leads_to] (t=7): _"they made it actually taste okay... a lot of sugar-free drinks taste like chemicals or whatever, but this one doesn't have that weird aftertaste"_
- `inference that product was tested with real consumers → brand trustworthiness and consumer understanding` [leads_to] (t=8): _"That feels like they actually tested it with real people instead of just checking a box."_

### Chain 3 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=?) → `zero sugar formulation` (attribute, t=1) → `absence of artificial sweetener aftertaste` (attribute, t=7) → `taste quality achieved without chemical flavor` (functional_consequence, t=7) → `brand prioritizing what people actually want over mere product existence` (functional_consequence, t=6) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=6)

**Evidence**:
- `acceptable taste despite no sugar → zero sugar formulation` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `zero sugar formulation → absence of artificial sweetener aftertaste` [leads_to] (t=1): _"it's usually something with zero sugar"_
- `absence of artificial sweetener aftertaste → taste quality achieved without chemical flavor` [leads_to] (t=7): _"ZeroFizz doesn't really have that artificial sweetener aftertaste"_
- `taste quality achieved without chemical flavor → brand prioritizing what people actually want over mere product existence` [leads_to] (t=7): _"they made it actually taste okay... a lot of sugar-free drinks taste like chemicals or whatever, but this one doesn't have that weird aftertaste"_
- `brand prioritizing what people actually want over mere product existence → brand trustworthiness and consumer understanding` [leads_to] (t=6): _"it shows they're thinking about what people actually want rather than just making a product exist"_

### Chain 4 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=2) → `carbonation level` (attribute, t=2) → `drink feeling pointless or unsatisfying` (functional_consequence, t=3) → `inference that corners were cut in production` (functional_consequence, t=3) → `perception of cheap or low-quality product` (psychosocial_consequence, t=3) → `vibe of a product not made right` (psychosocial_consequence, t=3)

**Evidence**:
- `acceptable taste despite no sugar → carbonation level` [leads_to] (t=2): _"if I can find it that doesn't taste completely awful"_
- `carbonation level → drink feeling pointless or unsatisfying` [leads_to] (t=2): _"the carbonation level is probably the biggest thing"_
- `drink feeling pointless or unsatisfying → inference that corners were cut in production` [leads_to] (t=3): _"if it's flat or too weak it just tastes kind of... pointless? Might as well drink juice."_
- `inference that corners were cut in production → perception of cheap or low-quality product` [leads_to] (t=3): _"it makes me think they cut corners somewhere else too"_
- `perception of cheap or low-quality product → vibe of a product not made right` [leads_to] (t=3): _"the whole thing just feels cheap"_

### Chain 5 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=8) → `cap opens without getting stuck` (attribute, t=8) → `ease of physical handling during use` (functional_consequence, t=8) → `inference that packaging was designed from real use experience` (psychosocial_consequence, t=8) → `inference that product was tested with real consumers` (psychosocial_consequence, t=8) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=8)

**Evidence**:
- `acceptable taste despite no sugar → cap opens without getting stuck` [leads_to] (t=8): _"if I can find it that doesn't taste completely awful"_
- `cap opens without getting stuck → ease of physical handling during use` [leads_to] (t=8): _"the cap doesn't do that weird thing where it gets stuck"_
- `ease of physical handling during use → inference that packaging was designed from real use experience` [leads_to] (t=8): _"you can actually grip it without your hand sliding around"_
- `inference that packaging was designed from real use experience → inference that product was tested with real consumers` [leads_to] (t=8): _"the packaging feels like they actually used it"_
- `inference that product was tested with real consumers → brand trustworthiness and consumer understanding` [leads_to] (t=8): _"That feels like they actually tested it with real people instead of just checking a box."_

### Chain 6 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=8) → `cap opens without getting stuck` (attribute, t=8) → `ease of physical handling during use` (functional_consequence, t=8) → `inference that packaging was designed from real use experience` (psychosocial_consequence, t=9) → `inference that product was developed through regular personal use` (psychosocial_consequence, t=9) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=9)

**Evidence**:
- `acceptable taste despite no sugar → cap opens without getting stuck` [leads_to] (t=8): _"if I can find it that doesn't taste completely awful"_
- `cap opens without getting stuck → ease of physical handling during use` [leads_to] (t=8): _"the cap doesn't do that weird thing where it gets stuck"_
- `ease of physical handling during use → inference that packaging was designed from real use experience` [leads_to] (t=8): _"you can actually grip it without your hand sliding around"_
- `inference that packaging was designed from real use experience → inference that product was developed through regular personal use` [leads_to] (t=9): _"the packaging feels like they actually used it"_
- `inference that product was developed through regular personal use → brand trustworthiness and consumer understanding` [leads_to] (t=9): _"That's the kind of thing you'd only notice if you actually drank your own product regularly instead of just... I dunno, checking boxes in a focus group or whatever."_

### Chain 7 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=?) → `zero sugar formulation` (attribute, t=1) → `absence of artificial sweetener aftertaste` (attribute, t=1) → `avoiding unpleasant taste experience` (functional_consequence, t=5) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=5)

**Evidence**:
- `acceptable taste despite no sugar → zero sugar formulation` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `zero sugar formulation → absence of artificial sweetener aftertaste` [leads_to] (t=1): _"it's usually something with zero sugar"_
- `absence of artificial sweetener aftertaste → avoiding unpleasant taste experience` [leads_to] (t=1): _"ZeroFizz doesn't really have that artificial sweetener aftertaste"_
- `avoiding unpleasant taste experience → brand trustworthiness and consumer understanding` [leads_to] (t=5): _"I've had other diet drinks that taste kind of off, and ZeroFizz doesn't really have that artificial sweetener aftertaste that bugs me"_

### Chain 8 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=2) → `carbonation level` (attribute, t=2) → `strong fizz sensation in the mouth` (functional_consequence, t=2) → `avoiding unpleasant taste experience` (functional_consequence, t=5) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=5)

**Evidence**:
- `acceptable taste despite no sugar → carbonation level` [leads_to] (t=2): _"if I can find it that doesn't taste completely awful"_
- `carbonation level → strong fizz sensation in the mouth` [leads_to] (t=2): _"the carbonation level is probably the biggest thing"_
- `strong fizz sensation in the mouth → avoiding unpleasant taste experience` [leads_to] (t=2): _"I want that actual fizz when it hits your mouth"_
- `avoiding unpleasant taste experience → brand trustworthiness and consumer understanding` [leads_to] (t=5): _"I've had other diet drinks that taste kind of off, and ZeroFizz doesn't really have that artificial sweetener aftertaste that bugs me"_

### Chain 9 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=2) → `carbonation level` (attribute, t=3) → `inference that corners were cut in production` (functional_consequence, t=3) → `perception of cheap or low-quality product` (psychosocial_consequence, t=3) → `vibe of a product not made right` (psychosocial_consequence, t=3)

**Evidence**:
- `acceptable taste despite no sugar → carbonation level` [leads_to] (t=2): _"if I can find it that doesn't taste completely awful"_
- `carbonation level → inference that corners were cut in production` [leads_to] (t=3): _"the carbonation level is probably the biggest thing"_
- `inference that corners were cut in production → perception of cheap or low-quality product` [leads_to] (t=3): _"it makes me think they cut corners somewhere else too"_
- `perception of cheap or low-quality product → vibe of a product not made right` [leads_to] (t=3): _"the whole thing just feels cheap"_

### Chain 10 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=2) → `carbonation level` (attribute, t=4) → `taste expectations specific to soda category` (functional_consequence, t=5) → `authentic soda experience` (functional_consequence, t=6) → `feeling that brand paid attention to consumer needs` (psychosocial_consequence, t=6)

**Evidence**:
- `acceptable taste despite no sugar → carbonation level` [leads_to] (t=2): _"if I can find it that doesn't taste completely awful"_
- `carbonation level → taste expectations specific to soda category` [leads_to] (t=4): _"the carbonation level is probably the biggest thing"_
- `taste expectations specific to soda category → authentic soda experience` [leads_to] (t=5): _"The taste thing is pretty specific to what I expect from a soda, you know?"_
- `authentic soda experience → feeling that brand paid attention to consumer needs` [leads_to] (t=6): _"It's a soda that tastes like a soda"_

### Chain 11 [surface]
**Path**: `bottle shape designed for grip` (attribute, t=8) → `ease of physical handling during use` (functional_consequence, t=8) → `inference that packaging was designed from real use experience` (psychosocial_consequence, t=8) → `inference that product was tested with real consumers` (psychosocial_consequence, t=8) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=8)

**Evidence**:
- `bottle shape designed for grip → ease of physical handling during use` [leads_to] (t=8): _"the bottle's shaped so you can actually grip it without your hand sliding around"_
- `ease of physical handling during use → inference that packaging was designed from real use experience` [leads_to] (t=8): _"you can actually grip it without your hand sliding around"_
- `inference that packaging was designed from real use experience → inference that product was tested with real consumers` [leads_to] (t=8): _"the packaging feels like they actually used it"_
- `inference that product was tested with real consumers → brand trustworthiness and consumer understanding` [leads_to] (t=8): _"That feels like they actually tested it with real people instead of just checking a box."_

### Chain 12 [surface]
**Path**: `bottle shape designed for grip` (attribute, t=8) → `ease of physical handling during use` (functional_consequence, t=8) → `inference that packaging was designed from real use experience` (psychosocial_consequence, t=9) → `inference that product was developed through regular personal use` (psychosocial_consequence, t=9) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=9)

**Evidence**:
- `bottle shape designed for grip → ease of physical handling during use` [leads_to] (t=8): _"the bottle's shaped so you can actually grip it without your hand sliding around"_
- `ease of physical handling during use → inference that packaging was designed from real use experience` [leads_to] (t=8): _"you can actually grip it without your hand sliding around"_
- `inference that packaging was designed from real use experience → inference that product was developed through regular personal use` [leads_to] (t=9): _"the packaging feels like they actually used it"_
- `inference that product was developed through regular personal use → brand trustworthiness and consumer understanding` [leads_to] (t=9): _"That's the kind of thing you'd only notice if you actually drank your own product regularly instead of just... I dunno, checking boxes in a focus group or whatever."_

### Chain 13 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=?) → `zero sugar formulation` (attribute, t=?) → `avoiding energy crash after consumption` (functional_consequence, t=?) → `deliberate beverage choice-making` (functional_consequence, t=?)

**Evidence**:
- `acceptable taste despite no sugar → zero sugar formulation` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `zero sugar formulation → avoiding energy crash after consumption` [leads_to] (t=?): _"it's usually something with zero sugar"_
- `avoiding energy crash after consumption → deliberate beverage choice-making` [leads_to] (t=?): _"not wanting the crash after, you know?"_

### Chain 14 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=2) → `carbonation level` (attribute, t=4) → `taste expectations specific to soda category` (functional_consequence, t=4) → `vibe of a product not made right` (psychosocial_consequence, t=4)

**Evidence**:
- `acceptable taste despite no sugar → carbonation level` [leads_to] (t=2): _"if I can find it that doesn't taste completely awful"_
- `carbonation level → taste expectations specific to soda category` [leads_to] (t=4): _"the carbonation level is probably the biggest thing"_
- `taste expectations specific to soda category → vibe of a product not made right` [leads_to] (t=4): _"The taste thing is pretty specific to what I expect from a soda, you know?"_

### Chain 15 [surface]
**Path**: `acceptable taste despite no sugar` (attribute, t=8) → `cap opens without getting stuck` (attribute, t=8) → `ease of physical handling during use` (functional_consequence, t=10) → `product feels physically sturdy and reliable during use` (functional_consequence, t=10)

**Evidence**:
- `acceptable taste despite no sugar → cap opens without getting stuck` [leads_to] (t=8): _"if I can find it that doesn't taste completely awful"_
- `cap opens without getting stuck → ease of physical handling during use` [leads_to] (t=8): _"the cap doesn't do that weird thing where it gets stuck"_
- `ease of physical handling during use → product feels physically sturdy and reliable during use` [leads_to] (t=10): _"you can actually grip it without your hand sliding around"_

### Chain 16 [surface]
**Path**: `noticing when companies skip usability details` (functional_consequence, t=8) → `inference that packaging was designed from real use experience` (psychosocial_consequence, t=8) → `inference that product was tested with real consumers` (psychosocial_consequence, t=8) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=8)

**Evidence**:
- `noticing when companies skip usability details → inference that packaging was designed from real use experience` [leads_to] (t=8): _"Small stuff but you notice when companies skip that part"_
- `inference that packaging was designed from real use experience → inference that product was tested with real consumers` [leads_to] (t=8): _"the packaging feels like they actually used it"_
- `inference that product was tested with real consumers → brand trustworthiness and consumer understanding` [leads_to] (t=8): _"That feels like they actually tested it with real people instead of just checking a box."_

### Chain 17 [surface]
**Path**: `noticing when companies skip usability details` (functional_consequence, t=8) → `inference that packaging was designed from real use experience` (psychosocial_consequence, t=9) → `inference that product was developed through regular personal use` (psychosocial_consequence, t=9) → `brand trustworthiness and consumer understanding` (psychosocial_consequence, t=9)

**Evidence**:
- `noticing when companies skip usability details → inference that packaging was designed from real use experience` [leads_to] (t=8): _"Small stuff but you notice when companies skip that part"_
- `inference that packaging was designed from real use experience → inference that product was developed through regular personal use` [leads_to] (t=9): _"the packaging feels like they actually used it"_
- `inference that product was developed through regular personal use → brand trustworthiness and consumer understanding` [leads_to] (t=9): _"That's the kind of thing you'd only notice if you actually drank your own product regularly instead of just... I dunno, checking boxes in a focus group or whatever."_

### Chain 18 [surface]
**Path**: `bottle shape designed for grip` (attribute, t=8) → `ease of physical handling during use` (functional_consequence, t=10) → `product feels physically sturdy and reliable during use` (functional_consequence, t=10)

**Evidence**:
- `bottle shape designed for grip → ease of physical handling during use` [leads_to] (t=8): _"the bottle's shaped so you can actually grip it without your hand sliding around"_
- `ease of physical handling during use → product feels physically sturdy and reliable during use` [leads_to] (t=10): _"you can actually grip it without your hand sliding around"_

### Chain 1 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `sensory_experience` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → conscious_consumption` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `conscious_consumption → sensory_experience` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `sensory_experience → consumer_preference_alignment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 2 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `conscious_consumption` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → sensory_experience` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `sensory_experience → conscious_consumption` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `conscious_consumption → consumer_preference_alignment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 3 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `sensory_experience` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → conscious_consumption` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `conscious_consumption → sensory_experience` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `sensory_experience → consumer_preference_alignment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 4 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → conscious_consumption` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `conscious_consumption → consumer_preference_alignment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 5 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `sensory_experience` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → conscious_consumption` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `conscious_consumption → sensory_experience` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `sensory_experience → perceive_quality_judgment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_

### Chain 6 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `conscious_consumption` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → sensory_experience` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `sensory_experience → conscious_consumption` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `conscious_consumption → perceive_quality_judgment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_

### Chain 7 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → sensory_experience` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `sensory_experience → consumer_preference_alignment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 8 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `conscious_consumption` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → sensory_experience` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `sensory_experience → conscious_consumption` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `conscious_consumption → consumer_preference_alignment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 9 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → conscious_consumption` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `conscious_consumption → consumer_preference_alignment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 10 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `sensory_experience` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → conscious_consumption` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `conscious_consumption → sensory_experience` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_
- `sensory_experience → perceive_quality_judgment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_

### Chain 11 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → conscious_consumption` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `conscious_consumption → perceive_quality_judgment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_

### Chain 12 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `carbonation_intensity` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → carbonation_intensity` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `carbonation_intensity → sensory_experience` [leads_to] (t=?): _"the carbonation level is probably the biggest thing"_
- `sensory_experience → perceive_quality_judgment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_

### Chain 13 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `conscious_consumption` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → sensory_experience` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `sensory_experience → conscious_consumption` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `conscious_consumption → perceive_quality_judgment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_

### Chain 14 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `consumer_preference_alignment` (psychosocial_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → sensory_experience` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `sensory_experience → consumer_preference_alignment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_
- `consumer_preference_alignment → perceive_quality_judgment` [leads_to] (t=?): _"it just means they actually get what people want from a soda"_

### Chain 15 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `conscious_consumption` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → conscious_consumption` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `conscious_consumption → perceive_quality_judgment` [leads_to] (t=?): _"I started thinking more about like, not wanting the crash after"_

### Chain 16 [canonical]
**Path**: `taste_quality` (attribute, t=?) → `sensory_experience` (functional_consequence, t=?) → `perceive_quality_judgment` (psychosocial_consequence, t=?)

**Evidence**:
- `taste_quality → sensory_experience` [leads_to] (t=?): _"if I can find it that doesn't taste completely awful"_
- `sensory_experience → perceive_quality_judgment` [leads_to] (t=?): _"I want that actual fizz when it hits your mouth"_

## Started — fewer than 3 nodes

_No started chains found._

## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `packaging appearance` (attribute) — _"if the packaging was plain or whatever that wouldn't really get to me the same"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/means_end_chain_v2_strict.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
