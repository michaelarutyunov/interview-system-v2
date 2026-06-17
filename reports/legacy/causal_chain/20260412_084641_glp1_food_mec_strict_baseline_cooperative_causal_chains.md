# Causal Chain Extraction — 20260412_084641_glp1_food_mec_strict_baseline_cooperative.json

## Source specs
- **Session ID**: a659ff79-76ba-42ae-a37d-8fe4112f91ba
- **Concept**: GLP-1 Medication and Food Choices - Means-End Chain (Strict) (`glp1_food_mec_strict`)
- **Methodology**: `means_end_chain_v2_strict`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 16
- **Status**: Maximum turns reached
- **Saved at**: 2026-04-12T08:46:41.542060+00:00

## Extraction config
- **Constraint source**: yaml
- **Permitted connections** (leads_to):
  - attribute → attribute
  - attribute → functional_consequence
  - functional_consequence → functional_consequence
  - functional_consequence → psychosocial_consequence
  - psychosocial_consequence → psychosocial_consequence
  - psychosocial_consequence → instrumental_value
  - instrumental_value → instrumental_value
  - instrumental_value → terminal_value
- **Superseded nodes excluded**: 0
- **Revises edges excluded from traversal**: 4 (3 surface, 1 canonical)

## Graph summary
| | Surface | Canonical |
|--|--|--|
| Nodes | 85 | 13 |
| Edges (leads_to) | 101 | 62 |
| Edges (revises) | 3 | 1 |
| Node types | attribute, functional_consequence, instrumental_value, psychosocial_consequence, terminal_value | functional_consequence, instrumental_value, psychosocial_consequence, terminal_value |

## Chain completeness summary
| Tier | Description | Surface Count | Canonical Count |
|------|-------------|---------------|-----------------|
| Full | attribute → functional_consequence → psychosocial_consequence → instrumental_value → terminal_value | 0 | 0 |
| Advanced | Reaches instrumental_value or terminal_value, but incomplete | 67 | 16 |
| Developing | Reaches psychosocial_consequence but not values | 15 | 4 |
| Started | attribute → functional_consequence only | 6 | 0 |
| Lateral (excluded) | Same-type only chains | 4 | 0 |

---

## Full chains — complete laddering
_No full chains found._

## Advanced chains — value-reaching but incomplete

### Chain 1 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 2 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 3 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 4 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 5 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 6 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
### Chain 7 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 8 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 9 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 10 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 11 [surface]
**Path**: `medication only works when actually taken` (attribute, t=11) → `consistent medication adherence` (functional_consequence, t=11) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `medication only works when actually taken → consistent medication adherence` (t=11): _"(no quote)"_
- `consistent medication adherence → concrete measurable results` (t=11): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 12 [surface]
**Path**: `medication only works when actually taken` (attribute, t=11) → `consistent medication adherence` (functional_consequence, t=11) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=?)

**Evidence**:
- `medication only works when actually taken → consistent medication adherence` (t=11): _"(no quote)"_
- `consistent medication adherence → concrete measurable results` (t=11): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
### Chain 13 [surface]
**Path**: `medication only works when actually taken` (attribute, t=11) → `consistent medication adherence` (functional_consequence, t=11) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `medication only works when actually taken → consistent medication adherence` (t=11): _"(no quote)"_
- `consistent medication adherence → concrete measurable results` (t=11): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 14 [surface]
**Path**: `medication only works when actually taken` (attribute, t=11) → `consistent medication adherence` (functional_consequence, t=11) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `medication only works when actually taken → consistent medication adherence` (t=11): _"(no quote)"_
- `consistent medication adherence → concrete measurable results` (t=11): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 15 [surface]
**Path**: `peace of mind` (psychosocial_consequence, t=13) → `feeling comfortable and at ease around others` (psychosocial_consequence, t=13) → `being present without overthinking` (psychosocial_consequence, t=14) → `sense of authenticity` (psychosocial_consequence, t=14) → `being a better version of myself` (psychosocial_consequence, t=14) → `seeing myself as a better friend and parent` (psychosocial_consequence, t=14) → `being the person I want to be in relationships` (instrumental_value, t=14) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `peace of mind → feeling comfortable and at ease around others` (t=13): _"(no quote)"_
- `feeling comfortable and at ease around others → being present without overthinking` (t=13): _"(no quote)"_
- `being present without overthinking → sense of authenticity` (t=14): _"(no quote)"_
- `sense of authenticity → being a better version of myself` (t=14): _"(no quote)"_
- `being a better version of myself → seeing myself as a better friend and parent` (t=14): _"(no quote)"_
- `seeing myself as a better friend and parent → being the person I want to be in relationships` (t=14): _"(no quote)"_
- `being the person I want to be in relationships → sense of authentic personal progress` (t=14): _"(no quote)"_
### Chain 16 [surface]
**Path**: `loved ones feeling secure around me` (psychosocial_consequence, t=13) → `feeling comfortable and at ease around others` (psychosocial_consequence, t=13) → `being present without overthinking` (psychosocial_consequence, t=14) → `sense of authenticity` (psychosocial_consequence, t=14) → `being a better version of myself` (psychosocial_consequence, t=14) → `seeing myself as a better friend and parent` (psychosocial_consequence, t=14) → `being the person I want to be in relationships` (instrumental_value, t=14) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `loved ones feeling secure around me → feeling comfortable and at ease around others` (t=13): _"(no quote)"_
- `feeling comfortable and at ease around others → being present without overthinking` (t=13): _"(no quote)"_
- `being present without overthinking → sense of authenticity` (t=14): _"(no quote)"_
- `sense of authenticity → being a better version of myself` (t=14): _"(no quote)"_
- `being a better version of myself → seeing myself as a better friend and parent` (t=14): _"(no quote)"_
- `seeing myself as a better friend and parent → being the person I want to be in relationships` (t=14): _"(no quote)"_
- `being the person I want to be in relationships → sense of authentic personal progress` (t=14): _"(no quote)"_
### Chain 17 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `feeling in control → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 18 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 19 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 20 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 21 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `changes actually making a difference → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 22 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=?)

**Evidence**:
- `changes actually making a difference → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
### Chain 23 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `changes actually making a difference → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 24 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `changes actually making a difference → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 25 [surface]
**Path**: `visible progress on the scale` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `visible progress on the scale → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 26 [surface]
**Path**: `visible progress on the scale` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=?)

**Evidence**:
- `visible progress on the scale → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
### Chain 27 [surface]
**Path**: `visible progress on the scale` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `visible progress on the scale → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 28 [surface]
**Path**: `visible progress on the scale` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `visible progress on the scale → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 29 [surface]
**Path**: `clothes fitting differently` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `clothes fitting differently → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 30 [surface]
**Path**: `clothes fitting differently` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=?)

**Evidence**:
- `clothes fitting differently → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
### Chain 31 [surface]
**Path**: `clothes fitting differently` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `clothes fitting differently → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 32 [surface]
**Path**: `clothes fitting differently` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `clothes fitting differently → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 33 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 34 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 35 [surface]
**Path**: `medication only works when actually taken` (attribute, t=11) → `consistent medication adherence` (functional_consequence, t=11) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `medication only works when actually taken → consistent medication adherence` (t=11): _"(no quote)"_
- `consistent medication adherence → concrete measurable results` (t=11): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 36 [surface]
**Path**: `medication only works when actually taken` (attribute, t=11) → `consistent medication adherence` (functional_consequence, t=11) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `medication only works when actually taken → consistent medication adherence` (t=11): _"(no quote)"_
- `consistent medication adherence → concrete measurable results` (t=11): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 37 [surface]
**Path**: `not distracted by physical discomfort or food preoccupation` (functional_consequence, t=14) → `being present without overthinking` (psychosocial_consequence, t=14) → `sense of authenticity` (psychosocial_consequence, t=14) → `being a better version of myself` (psychosocial_consequence, t=14) → `seeing myself as a better friend and parent` (psychosocial_consequence, t=14) → `being the person I want to be in relationships` (instrumental_value, t=14) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `not distracted by physical discomfort or food preoccupation → being present without overthinking` (t=14): _"(no quote)"_
- `being present without overthinking → sense of authenticity` (t=14): _"(no quote)"_
- `sense of authenticity → being a better version of myself` (t=14): _"(no quote)"_
- `being a better version of myself → seeing myself as a better friend and parent` (t=14): _"(no quote)"_
- `seeing myself as a better friend and parent → being the person I want to be in relationships` (t=14): _"(no quote)"_
- `being the person I want to be in relationships → sense of authentic personal progress` (t=14): _"(no quote)"_
### Chain 38 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `not thinking about food constantly` (functional_consequence, t=4) → `not feeling compelled to snack during leisure time` (functional_consequence, t=4) → `more quality time with partner` (psychosocial_consequence, t=4) → `being present and engaged in relationships` (instrumental_value, t=4) → `sense of inner peace and mental quiet` (terminal_value, t=?)

**Evidence**:
- `appetite suppression signal → not thinking about food constantly` (t=?): _"(no quote)"_
- `not thinking about food constantly → not feeling compelled to snack during leisure time` (t=4): _"(no quote)"_
- `not feeling compelled to snack during leisure time → more quality time with partner` (t=4): _"(no quote)"_
- `more quality time with partner → being present and engaged in relationships` (t=4): _"(no quote)"_
- `being present and engaged in relationships → sense of inner peace and mental quiet` (t=4): _"(no quote)"_
### Chain 39 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 40 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=7) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
- `taking active agency over one's life → following through on things` (t=7): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 41 [surface]
**Path**: `being respected by family` (psychosocial_consequence, t=8) → `validation from those who know you deeply` (psychosocial_consequence, t=8) → `meaningful recognition of personal effort` (psychosocial_consequence, t=9) → `working toward something real and meaningful` (psychosocial_consequence, t=9) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `being respected by family → validation from those who know you deeply` (t=8): _"(no quote)"_
- `validation from those who know you deeply → meaningful recognition of personal effort` (t=8): _"(no quote)"_
- `meaningful recognition of personal effort → working toward something real and meaningful` (t=9): _"(no quote)"_
- `working toward something real and meaningful → not just going through the motions to impress others` (t=9): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 42 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `changes actually making a difference → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 43 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `changes actually making a difference → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 44 [surface]
**Path**: `visible progress on the scale` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `visible progress on the scale → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 45 [surface]
**Path**: `visible progress on the scale` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `visible progress on the scale → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 46 [surface]
**Path**: `clothes fitting differently` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `clothes fitting differently → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 47 [surface]
**Path**: `clothes fitting differently` (functional_consequence, t=10) → `concrete measurable results` (functional_consequence, t=10) → `actual accountability through visible results` (psychosocial_consequence, t=10) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `clothes fitting differently → concrete measurable results` (t=10): _"(no quote)"_
- `concrete measurable results → actual accountability through visible results` (t=10): _"(no quote)"_
- `actual accountability through visible results → following through on things` (t=10): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 48 [surface]
**Path**: `loved ones feeling secure around me` (psychosocial_consequence, t=13) → `deeper, more open conversations` (psychosocial_consequence, t=14) → `being a better version of myself` (psychosocial_consequence, t=14) → `seeing myself as a better friend and parent` (psychosocial_consequence, t=14) → `being the person I want to be in relationships` (instrumental_value, t=14) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `loved ones feeling secure around me → deeper, more open conversations` (t=13): _"(no quote)"_
- `deeper, more open conversations → being a better version of myself` (t=14): _"(no quote)"_
- `being a better version of myself → seeing myself as a better friend and parent` (t=14): _"(no quote)"_
- `seeing myself as a better friend and parent → being the person I want to be in relationships` (t=14): _"(no quote)"_
- `being the person I want to be in relationships → sense of authentic personal progress` (t=14): _"(no quote)"_
### Chain 49 [surface]
**Path**: `focusing on listening and enjoying time together` (functional_consequence, t=13) → `deeper, more open conversations` (psychosocial_consequence, t=14) → `being a better version of myself` (psychosocial_consequence, t=14) → `seeing myself as a better friend and parent` (psychosocial_consequence, t=14) → `being the person I want to be in relationships` (instrumental_value, t=14) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `focusing on listening and enjoying time together → deeper, more open conversations` (t=13): _"(no quote)"_
- `deeper, more open conversations → being a better version of myself` (t=14): _"(no quote)"_
- `being a better version of myself → seeing myself as a better friend and parent` (t=14): _"(no quote)"_
- `seeing myself as a better friend and parent → being the person I want to be in relationships` (t=14): _"(no quote)"_
- `being the person I want to be in relationships → sense of authentic personal progress` (t=14): _"(no quote)"_
### Chain 50 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 51 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `feeling in control → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not just going through the motions to impress others` (t=10): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 52 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=7) → `taking active agency over one's life` (instrumental_value, t=?)

**Evidence**:
- `feeling in control → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → taking active agency over one's life` (t=7): _"(no quote)"_
### Chain 53 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=10) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being a responsible person` (t=10): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 54 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 55 [surface]
**Path**: `peace of mind` (psychosocial_consequence, t=13) → `feeling comfortable and at ease around others` (psychosocial_consequence, t=13) → `being present without overthinking` (psychosocial_consequence, t=13) → `authentic self-expression in relationships` (instrumental_value, t=13) → `integrity and authenticity in relationships` (terminal_value, t=?)

**Evidence**:
- `peace of mind → feeling comfortable and at ease around others` (t=13): _"(no quote)"_
- `feeling comfortable and at ease around others → being present without overthinking` (t=13): _"(no quote)"_
- `being present without overthinking → authentic self-expression in relationships` (t=13): _"(no quote)"_
- `authentic self-expression in relationships → integrity and authenticity in relationships` (t=13): _"(no quote)"_
### Chain 56 [surface]
**Path**: `loved ones feeling secure around me` (psychosocial_consequence, t=13) → `feeling comfortable and at ease around others` (psychosocial_consequence, t=13) → `being present without overthinking` (psychosocial_consequence, t=13) → `authentic self-expression in relationships` (instrumental_value, t=13) → `integrity and authenticity in relationships` (terminal_value, t=?)

**Evidence**:
- `loved ones feeling secure around me → feeling comfortable and at ease around others` (t=13): _"(no quote)"_
- `feeling comfortable and at ease around others → being present without overthinking` (t=13): _"(no quote)"_
- `being present without overthinking → authentic self-expression in relationships` (t=13): _"(no quote)"_
- `authentic self-expression in relationships → integrity and authenticity in relationships` (t=13): _"(no quote)"_
### Chain 57 [surface]
**Path**: `more time to relax in the evening` (functional_consequence, t=4) → `more quality time with partner` (psychosocial_consequence, t=4) → `being present and engaged in relationships` (instrumental_value, t=4) → `sense of inner peace and mental quiet` (terminal_value, t=?)

**Evidence**:
- `more time to relax in the evening → more quality time with partner` (t=4): _"(no quote)"_
- `more quality time with partner → being present and engaged in relationships` (t=4): _"(no quote)"_
- `being present and engaged in relationships → sense of inner peace and mental quiet` (t=4): _"(no quote)"_
### Chain 58 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=6) → `self-respect and self-care` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → self-respect and self-care` (t=6): _"(no quote)"_
### Chain 59 [surface]
**Path**: `being attuned to body's needs` (instrumental_value, t=6) → `not ignoring yourself` (instrumental_value, t=6) → `respecting yourself` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `being attuned to body's needs → not ignoring yourself` (t=6): _"(no quote)"_
- `not ignoring yourself → respecting yourself` (t=6): _"(no quote)"_
- `respecting yourself → being someone I can count on` (t=11): _"(no quote)"_
### Chain 60 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `following through on things` (instrumental_value, t=10) → `living with integrity — doing not just talking` (instrumental_value, t=12) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → following through on things` (t=7): _"(no quote)"_
- `following through on things → living with integrity — doing not just talking` (t=10): _"(no quote)"_
- `living with integrity — doing not just talking → being someone I can count on` (t=12): _"(no quote)"_
### Chain 61 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `following through on things` (instrumental_value, t=11) → `not being all talk — aligning words with actions` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → following through on things` (t=7): _"(no quote)"_
- `following through on things → not being all talk — aligning words with actions` (t=11): _"(no quote)"_
- `not being all talk — aligning words with actions → being someone I can count on` (t=11): _"(no quote)"_
### Chain 62 [surface]
**Path**: `changes actually making a difference` (functional_consequence, t=9) → `working toward something real and meaningful` (psychosocial_consequence, t=9) → `not just going through the motions to impress others` (instrumental_value, t=9) → `sense of authentic personal progress` (terminal_value, t=?)

**Evidence**:
- `changes actually making a difference → working toward something real and meaningful` (t=9): _"(no quote)"_
- `working toward something real and meaningful → not just going through the motions to impress others` (t=9): _"(no quote)"_
- `not just going through the motions to impress others → sense of authentic personal progress` (t=9): _"(no quote)"_
### Chain 63 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=7) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 64 [surface]
**Path**: `not distracted by physical discomfort or food preoccupation` (functional_consequence, t=14) → `being present without overthinking` (psychosocial_consequence, t=13) → `authentic self-expression in relationships` (instrumental_value, t=13) → `integrity and authenticity in relationships` (terminal_value, t=?)

**Evidence**:
- `not distracted by physical discomfort or food preoccupation → being present without overthinking` (t=14): _"(no quote)"_
- `being present without overthinking → authentic self-expression in relationships` (t=13): _"(no quote)"_
- `authentic self-expression in relationships → integrity and authenticity in relationships` (t=13): _"(no quote)"_
### Chain 65 [surface]
**Path**: `feeling in control` (psychosocial_consequence, t=7) → `being a responsible person` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `feeling in control → being a responsible person` (t=7): _"(no quote)"_
- `being a responsible person → being someone I can count on` (t=11): _"(no quote)"_
### Chain 66 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=6) → `self-respect and self-care` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → self-respect and self-care` (t=6): _"(no quote)"_
### Chain 67 [surface]
**Path**: `eroding self-belief from repeated non-follow-through` (psychosocial_consequence, t=11) → `respecting yourself` (instrumental_value, t=11) → `being someone I can count on` (terminal_value, t=?)

**Evidence**:
- `eroding self-belief from repeated non-follow-through → respecting yourself` (t=11): _"(no quote)"_
- `respecting yourself → being someone I can count on` (t=11): _"(no quote)"_
### Chain 1 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `digestive_comfort` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → digestive_comfort` (t=?): _"(no quote)"_
- `digestive_comfort → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 2 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `sustain_energy` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → sustain_energy` (t=?): _"(no quote)"_
- `sustain_energy → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 3 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `digestive_comfort` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → digestive_comfort` (t=?): _"(no quote)"_
- `digestive_comfort → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 4 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `sustain_energy` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → sustain_energy` (t=?): _"(no quote)"_
- `sustain_energy → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 5 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 6 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 7 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 8 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 9 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `digestive_comfort` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → digestive_comfort` (t=?): _"(no quote)"_
- `digestive_comfort → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 10 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 11 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 12 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `digestive_comfort` (functional_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `portion_control → digestive_comfort` (t=?): _"(no quote)"_
- `digestive_comfort → emotional_stability` (t=?): _"(no quote)"_
- `emotional_stability → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 13 [canonical]
**Path**: `relationship_smoothness` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `relationship_smoothness → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 14 [canonical]
**Path**: `leisure_time_availability` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `leisure_time_availability → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 15 [canonical]
**Path**: `relationship_smoothness` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `relationship_smoothness → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
### Chain 16 [canonical]
**Path**: `leisure_time_availability` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `authentic_behavior` (instrumental_value, t=None) → `authentic_progress` (terminal_value, t=?)

**Evidence**:
- `leisure_time_availability → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → authentic_behavior` (t=?): _"(no quote)"_
- `authentic_behavior → authentic_progress` (t=?): _"(no quote)"_
## Developing chains — consequence-level progression

### Chain 1 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `reduced appetite in the morning` (functional_consequence, t=0) → `delaying breakfast until mid-morning` (functional_consequence, t=1) → `stable energy levels throughout morning` (functional_consequence, t=1) → `no mid-morning energy crash` (functional_consequence, t=1) → `reduced irritability from hunger` (psychosocial_consequence, t=1) → `feeling steady and settled throughout the day` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced appetite in the morning` (t=?): _"(no quote)"_
- `reduced appetite in the morning → delaying breakfast until mid-morning` (t=?): _"(no quote)"_
- `delaying breakfast until mid-morning → stable energy levels throughout morning` (t=1): _"(no quote)"_
- `stable energy levels throughout morning → no mid-morning energy crash` (t=1): _"(no quote)"_
- `no mid-morning energy crash → reduced irritability from hunger` (t=1): _"(no quote)"_
- `reduced irritability from hunger → feeling steady and settled throughout the day` (t=1): _"(no quote)"_
### Chain 2 [surface]
**Path**: `appetite suppression signal` (attribute, t=5) → `reduced constant hunger waves` (attribute, t=5) → `no longer snacking between meals` (functional_consequence, t=2) → `not overeating before bed` (functional_consequence, t=3) → `reduced bloating after meals` (functional_consequence, t=3) → `improved sleep quality` (functional_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced constant hunger waves` (t=5): _"(no quote)"_
- `reduced constant hunger waves → no longer snacking between meals` (t=5): _"(no quote)"_
- `no longer snacking between meals → not overeating before bed` (t=2): _"(no quote)"_
- `not overeating before bed → reduced bloating after meals` (t=3): _"(no quote)"_
- `reduced bloating after meals → improved sleep quality` (t=3): _"(no quote)"_
- `improved sleep quality → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 3 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `reduced appetite in the morning` (functional_consequence, t=0) → `delaying breakfast until mid-morning` (functional_consequence, t=1) → `stable energy levels throughout morning` (functional_consequence, t=2) → `no afternoon energy slump` (functional_consequence, t=2) → `feeling steady and settled throughout the day` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced appetite in the morning` (t=?): _"(no quote)"_
- `reduced appetite in the morning → delaying breakfast until mid-morning` (t=?): _"(no quote)"_
- `delaying breakfast until mid-morning → stable energy levels throughout morning` (t=1): _"(no quote)"_
- `stable energy levels throughout morning → no afternoon energy slump` (t=2): _"(no quote)"_
- `no afternoon energy slump → feeling steady and settled throughout the day` (t=2): _"(no quote)"_
### Chain 4 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `reduced appetite in the morning` (functional_consequence, t=1) → `stable energy levels throughout morning` (functional_consequence, t=1) → `no mid-morning energy crash` (functional_consequence, t=1) → `reduced irritability from hunger` (psychosocial_consequence, t=1) → `feeling steady and settled throughout the day` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced appetite in the morning` (t=?): _"(no quote)"_
- `reduced appetite in the morning → stable energy levels throughout morning` (t=1): _"(no quote)"_
- `stable energy levels throughout morning → no mid-morning energy crash` (t=1): _"(no quote)"_
- `no mid-morning energy crash → reduced irritability from hunger` (t=1): _"(no quote)"_
- `reduced irritability from hunger → feeling steady and settled throughout the day` (t=1): _"(no quote)"_
### Chain 5 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `stopping eating mid-meal` (functional_consequence, t=0) → `eating smaller portions` (functional_consequence, t=2) → `reduced bloating after meals` (functional_consequence, t=3) → `improved sleep quality` (functional_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → stopping eating mid-meal` (t=?): _"(no quote)"_
- `stopping eating mid-meal → eating smaller portions` (t=?): _"(no quote)"_
- `eating smaller portions → reduced bloating after meals` (t=2): _"(no quote)"_
- `reduced bloating after meals → improved sleep quality` (t=3): _"(no quote)"_
- `improved sleep quality → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 6 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `no longer snacking between meals` (functional_consequence, t=2) → `not overeating before bed` (functional_consequence, t=3) → `reduced bloating after meals` (functional_consequence, t=3) → `improved sleep quality` (functional_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → no longer snacking between meals` (t=?): _"(no quote)"_
- `no longer snacking between meals → not overeating before bed` (t=2): _"(no quote)"_
- `not overeating before bed → reduced bloating after meals` (t=3): _"(no quote)"_
- `reduced bloating after meals → improved sleep quality` (t=3): _"(no quote)"_
- `improved sleep quality → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 7 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `not thinking about food constantly` (functional_consequence, t=3) → `not obsessing over food in the evening` (functional_consequence, t=3) → `freed-up mental space` (psychosocial_consequence, t=4) → `reduced background anxiety about food` (psychosocial_consequence, t=4) → `sense of freedom from food preoccupation` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → not thinking about food constantly` (t=?): _"(no quote)"_
- `not thinking about food constantly → not obsessing over food in the evening` (t=3): _"(no quote)"_
- `not obsessing over food in the evening → freed-up mental space` (t=3): _"(no quote)"_
- `freed-up mental space → reduced background anxiety about food` (t=4): _"(no quote)"_
- `reduced background anxiety about food → sense of freedom from food preoccupation` (t=4): _"(no quote)"_
### Chain 8 [surface]
**Path**: `appetite suppression signal` (attribute, t=5) → `reduced constant hunger waves` (attribute, t=5) → `no longer snacking between meals` (functional_consequence, t=2) → `not overeating before bed` (functional_consequence, t=2) → `improved sleep quality` (functional_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced constant hunger waves` (t=5): _"(no quote)"_
- `reduced constant hunger waves → no longer snacking between meals` (t=5): _"(no quote)"_
- `no longer snacking between meals → not overeating before bed` (t=2): _"(no quote)"_
- `not overeating before bed → improved sleep quality` (t=2): _"(no quote)"_
- `improved sleep quality → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 9 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `reduced appetite in the morning` (functional_consequence, t=1) → `stable energy levels throughout morning` (functional_consequence, t=2) → `no afternoon energy slump` (functional_consequence, t=2) → `feeling steady and settled throughout the day` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced appetite in the morning` (t=?): _"(no quote)"_
- `reduced appetite in the morning → stable energy levels throughout morning` (t=1): _"(no quote)"_
- `stable energy levels throughout morning → no afternoon energy slump` (t=2): _"(no quote)"_
- `no afternoon energy slump → feeling steady and settled throughout the day` (t=2): _"(no quote)"_
### Chain 10 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `no longer snacking between meals` (functional_consequence, t=2) → `not overeating before bed` (functional_consequence, t=2) → `improved sleep quality` (functional_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → no longer snacking between meals` (t=?): _"(no quote)"_
- `no longer snacking between meals → not overeating before bed` (t=2): _"(no quote)"_
- `not overeating before bed → improved sleep quality` (t=2): _"(no quote)"_
- `improved sleep quality → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 11 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `not thinking about food constantly` (functional_consequence, t=3) → `not obsessing over food in the evening` (functional_consequence, t=3) → `freed-up mental space` (psychosocial_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → not thinking about food constantly` (t=?): _"(no quote)"_
- `not thinking about food constantly → not obsessing over food in the evening` (t=3): _"(no quote)"_
- `not obsessing over food in the evening → freed-up mental space` (t=3): _"(no quote)"_
- `freed-up mental space → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 12 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `not thinking about food constantly` (functional_consequence, t=3) → `not obsessing over food in the evening` (functional_consequence, t=3) → `feeling lighter in the evening` (functional_consequence, t=3) → `evening feels less hectic` (psychosocial_consequence, t=?)

**Evidence**:
- `appetite suppression signal → not thinking about food constantly` (t=?): _"(no quote)"_
- `not thinking about food constantly → not obsessing over food in the evening` (t=3): _"(no quote)"_
- `not obsessing over food in the evening → feeling lighter in the evening` (t=3): _"(no quote)"_
- `feeling lighter in the evening → evening feels less hectic` (t=3): _"(no quote)"_
### Chain 13 [surface]
**Path**: `family support during lifestyle changes` (functional_consequence, t=8) → `avoiding social awkwardness around food choices` (functional_consequence, t=8) → `not feeling like hiding habits or being dishonest` (psychosocial_consequence, t=?)

**Evidence**:
- `family support during lifestyle changes → avoiding social awkwardness around food choices` (t=8): _"(no quote)"_
- `avoiding social awkwardness around food choices → not feeling like hiding habits or being dishonest` (t=8): _"(no quote)"_
### Chain 14 [surface]
**Path**: `smoother relationships without awkward let-downs` (functional_consequence, t=12) → `avoiding social awkwardness around food choices` (functional_consequence, t=8) → `not feeling like hiding habits or being dishonest` (psychosocial_consequence, t=?)

**Evidence**:
- `smoother relationships without awkward let-downs → avoiding social awkwardness around food choices` (t=12): _"(no quote)"_
- `avoiding social awkwardness around food choices → not feeling like hiding habits or being dishonest` (t=8): _"(no quote)"_
### Chain 15 [surface]
**Path**: `avoiding making yourself sick or uncomfortable` (functional_consequence, t=6) → `feeling better overall` (psychosocial_consequence, t=?)

**Evidence**:
- `avoiding making yourself sick or uncomfortable → feeling better overall` (t=6): _"(no quote)"_
### Chain 1 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → emotional_stability` (t=?): _"(no quote)"_
### Chain 2 [canonical]
**Path**: `portion_control` (functional_consequence, t=None) → `satiety_awareness` (functional_consequence, t=None) → `appetite_suppression` (functional_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=?)

**Evidence**:
- `portion_control → satiety_awareness` (t=?): _"(no quote)"_
- `satiety_awareness → appetite_suppression` (t=?): _"(no quote)"_
- `appetite_suppression → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → emotional_stability` (t=?): _"(no quote)"_
### Chain 3 [canonical]
**Path**: `relationship_smoothness` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=?)

**Evidence**:
- `relationship_smoothness → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → emotional_stability` (t=?): _"(no quote)"_
### Chain 4 [canonical]
**Path**: `leisure_time_availability` (functional_consequence, t=None) → `relationship_quality` (psychosocial_consequence, t=None) → `mental_clarity` (psychosocial_consequence, t=None) → `emotional_stability` (psychosocial_consequence, t=?)

**Evidence**:
- `leisure_time_availability → relationship_quality` (t=?): _"(no quote)"_
- `relationship_quality → mental_clarity` (t=?): _"(no quote)"_
- `mental_clarity → emotional_stability` (t=?): _"(no quote)"_
## Started chains — attribute-to-functional only

### Chain 1 [surface]
**Path**: `initial nausea side effect` (attribute, t=5) → `increased mindfulness about what to eat` (functional_consequence, t=5) → `body actively communicating signals` (functional_consequence, t=5) → `listening to body's fullness cues` (functional_consequence, t=0) → `eating only when genuinely hungry` (functional_consequence, t=?)

**Evidence**:
- `initial nausea side effect → increased mindfulness about what to eat` (t=5): _"(no quote)"_
- `increased mindfulness about what to eat → body actively communicating signals` (t=5): _"(no quote)"_
- `body actively communicating signals → listening to body's fullness cues` (t=5): _"(no quote)"_
- `listening to body's fullness cues → eating only when genuinely hungry` (t=?): _"(no quote)"_
### Chain 2 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `stopping eating mid-meal` (functional_consequence, t=0) → `eating smaller portions` (functional_consequence, t=0) → `feeling satisfied after meals` (functional_consequence, t=?)

**Evidence**:
- `appetite suppression signal → stopping eating mid-meal` (t=?): _"(no quote)"_
- `stopping eating mid-meal → eating smaller portions` (t=?): _"(no quote)"_
- `eating smaller portions → feeling satisfied after meals` (t=?): _"(no quote)"_
### Chain 3 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `stopping eating mid-meal` (functional_consequence, t=0) → `listening to body's fullness cues` (functional_consequence, t=0) → `eating only when genuinely hungry` (functional_consequence, t=?)

**Evidence**:
- `appetite suppression signal → stopping eating mid-meal` (t=?): _"(no quote)"_
- `stopping eating mid-meal → listening to body's fullness cues` (t=?): _"(no quote)"_
- `listening to body's fullness cues → eating only when genuinely hungry` (t=?): _"(no quote)"_
### Chain 4 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `not thinking about food constantly` (functional_consequence, t=3) → `not obsessing over food in the evening` (functional_consequence, t=4) → `no longer scrolling food apps to decide what to eat` (functional_consequence, t=?)

**Evidence**:
- `appetite suppression signal → not thinking about food constantly` (t=?): _"(no quote)"_
- `not thinking about food constantly → not obsessing over food in the evening` (t=3): _"(no quote)"_
- `not obsessing over food in the evening → no longer scrolling food apps to decide what to eat` (t=4): _"(no quote)"_
### Chain 5 [surface]
**Path**: `appetite suppression signal` (attribute, t=0) → `not thinking about food constantly` (functional_consequence, t=0) → `eating only when genuinely hungry` (functional_consequence, t=?)

**Evidence**:
- `appetite suppression signal → not thinking about food constantly` (t=?): _"(no quote)"_
- `not thinking about food constantly → eating only when genuinely hungry` (t=?): _"(no quote)"_
### Chain 6 [surface]
**Path**: `appetite suppression signal` (attribute, t=5) → `reduced constant hunger waves` (attribute, t=5) → `not fighting food urges` (functional_consequence, t=?)

**Evidence**:
- `appetite suppression signal → reduced constant hunger waves` (t=5): _"(no quote)"_
- `reduced constant hunger waves → not fighting food urges` (t=5): _"(no quote)"_
## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing leads_to edges)

- `eating on autopilot without awareness` (functional_consequence) — _"I used to kind of push through it or just eat whatever was in front of me without really paying attention."_
- `family security and belonging` (terminal_value) — _"I can be the kind of person my family respects"_
- `things actually shifting and changing` (functional_consequence) — _"you can tell it matters because something actually shifts."_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Constraints from: `yaml`
- Overrides applied: no
- Known limitations: Canonical slot layer may hide language variation relevant to laddering validity.
