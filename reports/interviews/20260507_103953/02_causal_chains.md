# Causal Chain Extraction — 20260507_103953_zerofizz_beverage_jtbd_baseline_cooperative.json

## Source specs
- **Session ID**: d911a98c-4e26-46c7-83aa-b05ce43fe447
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done (`zerofizz_beverage_jtbd`)
- **Methodology**: `jobs_to_be_done_v2`
- **Persona**: Baseline Cooperative Respondent (`baseline_cooperative`)
- **Total turns**: 15
- **Status**: Closing strategy selected
- **Saved at**: 2026-05-07T10:39:53.305612+00:00

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
- **Conversation nodes**: 53
- **Themes (canonical slots)**: 7
- **Chain edges traversed**: 98
- **Edges (revises)**: 0

## Chain completeness summary
| Tier | Description | Count |
|------|-------------|-------|
| Full | Reaches solution_approach — complete chain, no missing levels | 6 |
| Advanced | Reaches solution_approach (with one gap) or emotional_job / social_job | 54 |
| Developing | Mid-level progression, terminal not reached | 3 |
| Lateral (excluded) | Same-type only chains | 0 |

---

## Full chains — complete, no missing levels

### Chain 1
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=?)  
  → `not wanting to think or search when grabbing a drink` (pain_point, L1, t=3)  
  → `feel unburdened by trivial consumption decisions` (emotional_job, L3, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → not wanting to think or search when grabbing a drink` [triggers] (t=?): _"If I'm thirsty and there's something cold in the fridge"_
- `not wanting to think or search when grabbing a drink → feel unburdened by trivial consumption decisions` [implies] (t=3): _"I don't want to have to think about it or hunt around for a specific brand"_
- `feel unburdened by trivial consumption decisions → any available sugar-free option will do as a substitute` [drives] (t=2): _"I don't want to have to think about it or hunt around for a specific brand. Grab and go, that's it."_

### Chain 2
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=?)  
  → `effortless, frictionless drink retrieval` (gain_point, L1, t=3)  
  → `feel unburdened by trivial consumption decisions` (emotional_job, L3, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → effortless, frictionless drink retrieval` [triggers] (t=?): _"If I'm thirsty and there's something cold in the fridge"_
- `effortless, frictionless drink retrieval → feel unburdened by trivial consumption decisions` [supports] (t=3): _"Grab and go, that's it."_
- `feel unburdened by trivial consumption decisions → any available sugar-free option will do as a substitute` [drives] (t=2): _"I don't want to have to think about it or hunt around for a specific brand. Grab and go, that's it."_

### Chain 3
**Path**:

  → `being thirsty and wanting immediate drink access` (job_trigger, L0, t=10)  
  → `standing in front of the fridge deliberating over drink options` (pain_point, L1, t=10)  
  → `eliminate the moment of choosing between drink options` (job_statement, L2, t=10)  
  → `drink pre-chilled and stored in fridge for instant access` (solution_approach, L4, t=10)  

**Evidence**:
- `being thirsty and wanting immediate drink access → standing in front of the fridge deliberating over drink options` [triggers] (t=10): _"when I'm thirsty I don't want to stand in front of the fridge for five minutes weighing options"_
- `standing in front of the fridge deliberating over drink options → eliminate the moment of choosing between drink options` [implies] (t=10): _"I don't want to stand in front of the fridge for five minutes weighing options"_
- `eliminate the moment of choosing between drink options → drink pre-chilled and stored in fridge for instant access` [achieves (reversed)] (t=10): _"it's just about not having to make a decision, you know?"_

### Chain 4
**Path**:

  → `being thirsty and wanting immediate drink access` (job_trigger, L0, t=10)  
  → `standing in front of the fridge deliberating over drink options` (pain_point, L1, t=10)  
  → `feel instantly resolved without deliberation` (emotional_job, L3, t=10)  
  → `drink being already open or easy to open at point of thirst` (solution_approach, L4, t=10)  

**Evidence**:
- `being thirsty and wanting immediate drink access → standing in front of the fridge deliberating over drink options` [triggers] (t=10): _"when I'm thirsty I don't want to stand in front of the fridge for five minutes weighing options"_
- `standing in front of the fridge deliberating over drink options → feel instantly resolved without deliberation` [implies] (t=10): _"I don't want to stand in front of the fridge for five minutes weighing options"_
- `feel instantly resolved without deliberation → drink being already open or easy to open at point of thirst` [achieves (reversed)] (t=10): _"Something cold that's already open or easy to open is just... done."_

### Chain 5
**Path**:

  → `being thirsty and wanting immediate drink access` (job_trigger, L0, t=10)  
  → `standing in front of the fridge deliberating over drink options` (pain_point, L1, t=10)  
  → `feel instantly resolved without deliberation` (emotional_job, L3, t=10)  
  → `drink pre-chilled and stored in fridge for instant access` (solution_approach, L4, t=10)  

**Evidence**:
- `being thirsty and wanting immediate drink access → standing in front of the fridge deliberating over drink options` [triggers] (t=10): _"when I'm thirsty I don't want to stand in front of the fridge for five minutes weighing options"_
- `standing in front of the fridge deliberating over drink options → feel instantly resolved without deliberation` [implies] (t=10): _"I don't want to stand in front of the fridge for five minutes weighing options"_
- `feel instantly resolved without deliberation → drink pre-chilled and stored in fridge for instant access` [achieves (reversed)] (t=10): _"Something cold that's already open or easy to open is just... done."_

### Chain 6
**Path**:

  → `being thirsty and wanting immediate drink access` (job_trigger, L0, t=10)  
  → `standing in front of the fridge deliberating over drink options` (pain_point, L1, t=10)  
  → `feel instantly resolved without deliberation` (emotional_job, L3, t=10)  
  → `grabbing whatever is physically present in the fridge` (solution_approach, L4, t=10)  

**Evidence**:
- `being thirsty and wanting immediate drink access → standing in front of the fridge deliberating over drink options` [triggers] (t=10): _"when I'm thirsty I don't want to stand in front of the fridge for five minutes weighing options"_
- `standing in front of the fridge deliberating over drink options → feel instantly resolved without deliberation` [implies] (t=10): _"I don't want to stand in front of the fridge for five minutes weighing options"_
- `feel instantly resolved without deliberation → grabbing whatever is physically present in the fridge` [achieves (reversed)] (t=10): _"Something cold that's already open or easy to open is just... done."_

## Advanced chains — near-complete (one gap) or near-terminal

### Chain 1
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=?)  
  → `not wanting to think or search when grabbing a drink` (pain_point, L1, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → not wanting to think or search when grabbing a drink` [triggers] (t=?): _"If I'm thirsty and there's something cold in the fridge"_
- `not wanting to think or search when grabbing a drink → any available sugar-free option will do as a substitute` [drives] (t=2): _"I don't want to have to think about it or hunt around for a specific brand"_

### Chain 2
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=?)  
  → `effortless, frictionless drink retrieval` (gain_point, L1, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → effortless, frictionless drink retrieval` [triggers] (t=?): _"If I'm thirsty and there's something cold in the fridge"_
- `effortless, frictionless drink retrieval → any available sugar-free option will do as a substitute` [drives] (t=2): _"Grab and go, that's it."_

### Chain 3
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=?)  
  → `feel unburdened by trivial consumption decisions` (emotional_job, L3, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → feel unburdened by trivial consumption decisions` [triggers] (t=?): _"If I'm thirsty and there's something cold in the fridge"_
- `feel unburdened by trivial consumption decisions → any available sugar-free option will do as a substitute` [drives] (t=2): _"I don't want to have to think about it or hunt around for a specific brand. Grab and go, that's it."_

### Chain 4
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=2)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=2): _"If I'm thirsty and there's something cold in the fridge"_
- `decent taste as minimum threshold for a sugar-free drink → any available sugar-free option will do as a substitute` [drives] (t=2): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 5
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=2)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=2)  
  → `grabbing a regular Coke or Sprite when not watching sugar` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=2): _"If I'm thirsty and there's something cold in the fridge"_
- `decent taste as minimum threshold for a sugar-free drink → grabbing a regular Coke or Sprite when not watching sugar` [achieves (reversed)] (t=2): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 6
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=2)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=2)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=2)  

**Evidence**:
- `being thirsty with a cold drink nearby → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=2): _"If I'm thirsty and there's something cold in the fridge"_
- `decent taste as minimum threshold for a sugar-free drink → switching to Diet Coke or similar when being careful about sugar` [achieves (reversed)] (t=2): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 7
**Path**:

  → `being thirsty with a cold drink nearby` (job_trigger, L0, t=2)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `being thirsty with a cold drink nearby → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=2): _"If I'm thirsty and there's something cold in the fridge"_
- `decent taste as minimum threshold for a sugar-free drink → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 8
**Path**:

  → `feeling bloated after drinking something sugary` (pain_point, L1, t=5)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `feeling bloated after drinking something sugary → feel light and comfortable after drinking` [implies] (t=5): _"when I do grab something sugary I feel kind of bloated after"_
- `feel light and comfortable after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 9
**Path**:

  → `feeling bloated after drinking something sugary` (pain_point, L1, t=5)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `feeling bloated after drinking something sugary → feel light and comfortable after drinking` [implies] (t=5): _"when I do grab something sugary I feel kind of bloated after"_
- `feel light and comfortable after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 10
**Path**:

  → `feeling bloated after drinking something sugary` (pain_point, L1, t=5)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `feeling bloated after drinking something sugary → feel light and comfortable after drinking` [implies] (t=5): _"when I do grab something sugary I feel kind of bloated after"_
- `feel light and comfortable after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 11
**Path**:

  → `bloating is worse later in the day` (job_context, L0, t=5)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `bloating is worse later in the day → avoiding that heavy, bloated feeling after drinking` [triggers] (t=5): _"especially if it's later in the day"_
- `avoiding that heavy, bloated feeling after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 12
**Path**:

  → `bloating is worse later in the day` (job_context, L0, t=5)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `bloating is worse later in the day → avoiding that heavy, bloated feeling after drinking` [triggers] (t=5): _"especially if it's later in the day"_
- `avoiding that heavy, bloated feeling after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 13
**Path**:

  → `bloating is worse later in the day` (job_context, L0, t=5)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `bloating is worse later in the day → avoiding that heavy, bloated feeling after drinking` [triggers] (t=5): _"especially if it's later in the day"_
- `avoiding that heavy, bloated feeling after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 14
**Path**:

  → `bloating is worse later in the day` (job_context, L0, t=5)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `bloating is worse later in the day → feel light and comfortable after drinking` [triggers] (t=5): _"especially if it's later in the day"_
- `feel light and comfortable after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 15
**Path**:

  → `bloating is worse later in the day` (job_context, L0, t=5)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `bloating is worse later in the day → feel light and comfortable after drinking` [triggers] (t=5): _"especially if it's later in the day"_
- `feel light and comfortable after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 16
**Path**:

  → `bloating is worse later in the day` (job_context, L0, t=5)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `bloating is worse later in the day → feel light and comfortable after drinking` [triggers] (t=5): _"especially if it's later in the day"_
- `feel light and comfortable after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 17
**Path**:

  → `being active or going to the gym` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `sugar avoidance is automatic when in a fitness mindset, not deliberate` (solution_approach, L4, t=6)  

**Evidence**:
- `being active or going to the gym → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"if I'm being more active or going to the gym, I'm already in that headspace so I just naturally avoid it"_
- `feel aligned and consistent with an active, health-conscious identity → sugar avoidance is automatic when in a fitness mindset, not deliberate` [drives] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 18
**Path**:

  → `being active or going to the gym` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=6)  

**Evidence**:
- `being active or going to the gym → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"if I'm being more active or going to the gym, I'm already in that headspace so I just naturally avoid it"_
- `feel aligned and consistent with an active, health-conscious identity → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 19
**Path**:

  → `being active or going to the gym` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `being active or going to the gym → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"if I'm being more active or going to the gym, I'm already in that headspace so I just naturally avoid it"_
- `feel aligned and consistent with an active, health-conscious identity → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 20
**Path**:

  → `working from home with low activity` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `sugar avoidance is automatic when in a fitness mindset, not deliberate` (solution_approach, L4, t=6)  

**Evidence**:
- `working from home with low activity → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"if I'm sitting around working from home or something, I don't really think about it"_
- `feel aligned and consistent with an active, health-conscious identity → sugar avoidance is automatic when in a fitness mindset, not deliberate` [drives] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 21
**Path**:

  → `working from home with low activity` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=6)  

**Evidence**:
- `working from home with low activity → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"if I'm sitting around working from home or something, I don't really think about it"_
- `feel aligned and consistent with an active, health-conscious identity → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 22
**Path**:

  → `working from home with low activity` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `working from home with low activity → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"if I'm sitting around working from home or something, I don't really think about it"_
- `feel aligned and consistent with an active, health-conscious identity → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 23
**Path**:

  → `health-conscious mindset triggered by physical activity` (job_trigger, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `sugar avoidance is automatic when in a fitness mindset, not deliberate` (solution_approach, L4, t=6)  

**Evidence**:
- `health-conscious mindset triggered by physical activity → feel aligned and consistent with an active, health-conscious identity` [supports] (t=6): _"if I'm being more active or going to the gym, I'm already in that headspace so I just naturally avoid it"_
- `feel aligned and consistent with an active, health-conscious identity → sugar avoidance is automatic when in a fitness mindset, not deliberate` [drives] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 24
**Path**:

  → `health-conscious mindset triggered by physical activity` (job_trigger, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=6)  

**Evidence**:
- `health-conscious mindset triggered by physical activity → feel aligned and consistent with an active, health-conscious identity` [supports] (t=6): _"if I'm being more active or going to the gym, I'm already in that headspace so I just naturally avoid it"_
- `feel aligned and consistent with an active, health-conscious identity → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 25
**Path**:

  → `health-conscious mindset triggered by physical activity` (job_trigger, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `health-conscious mindset triggered by physical activity → feel aligned and consistent with an active, health-conscious identity` [supports] (t=6): _"if I'm being more active or going to the gym, I'm already in that headspace so I just naturally avoid it"_
- `feel aligned and consistent with an active, health-conscious identity → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 26
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → feel light and comfortable after drinking` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `feel light and comfortable after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 27
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → feel light and comfortable after drinking` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `feel light and comfortable after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 28
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → feel light and comfortable after drinking` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `feel light and comfortable after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 29
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `sugar avoidance is automatic when in a fitness mindset, not deliberate` (solution_approach, L4, t=6)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → feel aligned and consistent with an active, health-conscious identity` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `feel aligned and consistent with an active, health-conscious identity → sugar avoidance is automatic when in a fitness mindset, not deliberate` [drives] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 30
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=6)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → feel aligned and consistent with an active, health-conscious identity` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `feel aligned and consistent with an active, health-conscious identity → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 31
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → feel aligned and consistent with an active, health-conscious identity` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `feel aligned and consistent with an active, health-conscious identity → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 32
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → feel light and comfortable after drinking` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `feel light and comfortable after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 33
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → feel light and comfortable after drinking` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `feel light and comfortable after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 34
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `feel light and comfortable after drinking` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → feel light and comfortable after drinking` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `feel light and comfortable after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 35
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → avoiding that heavy, bloated feeling after drinking` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `avoiding that heavy, bloated feeling after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 36
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → avoiding that heavy, bloated feeling after drinking` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `avoiding that heavy, bloated feeling after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 37
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → avoiding that heavy, bloated feeling after drinking` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `avoiding that heavy, bloated feeling after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 38
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=2)  
  → `any available sugar-free option will do as a substitute` (solution_approach, L4, t=2)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `decent taste as minimum threshold for a sugar-free drink → any available sugar-free option will do as a substitute` [drives] (t=2): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 39
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=2)  
  → `grabbing a regular Coke or Sprite when not watching sugar` (solution_approach, L4, t=2)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `decent taste as minimum threshold for a sugar-free drink → grabbing a regular Coke or Sprite when not watching sugar` [achieves (reversed)] (t=2): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 40
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=2)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=2)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `decent taste as minimum threshold for a sugar-free drink → switching to Diet Coke or similar when being careful about sugar` [achieves (reversed)] (t=2): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 41
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `decent taste as minimum threshold for a sugar-free drink` (gain_point, L1, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → decent taste as minimum threshold for a sugar-free drink` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `decent taste as minimum threshold for a sugar-free drink → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"If there's a sugar-free option that tastes decent, that's good enough for me."_

### Chain 42
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `sugar avoidance is automatic when in a fitness mindset, not deliberate` (solution_approach, L4, t=6)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `feel aligned and consistent with an active, health-conscious identity → sugar avoidance is automatic when in a fitness mindset, not deliberate` [drives] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 43
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=6)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=6)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `feel aligned and consistent with an active, health-conscious identity → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=6): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 44
**Path**:

  → `zero-sugar drink choice embedded in pre-activity routine` (job_context, L0, t=6)  
  → `feel aligned and consistent with an active, health-conscious identity` (emotional_job, L3, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `zero-sugar drink choice embedded in pre-activity routine → feel aligned and consistent with an active, health-conscious identity` [triggers] (t=6): _"it's just become part of the routine at that point. Like I've done it enough times that grabbing one before I head out is as automatic as putting on my shoes."_
- `feel aligned and consistent with an active, health-conscious identity → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"I'm already in that headspace so I just naturally avoid it"_

### Chain 45
**Path**:

  → `leaving the house while managing multiple competing tasks` (job_context, L0, t=9)  
  → `cognitive overload at departure moment crowds out drink intention` (pain_point, L1, t=9)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=9)  

**Evidence**:
- `leaving the house while managing multiple competing tasks → cognitive overload at departure moment crowds out drink intention` [triggers] (t=9): _"I'm already juggling a bunch of stuff when I leave the house"_
- `cognitive overload at departure moment crowds out drink intention → drink already placed on the counter before leaving` [implies] (t=9): _"I'm already juggling a bunch of stuff when I leave the house. Like if it's not just... there, ready to go, I won't think about it."_

### Chain 46
**Path**:

  → `leaving the house while managing multiple competing tasks` (job_context, L0, t=9)  
  → `drink not being readily available at point of departure` (pain_point, L1, t=8)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=8)  

**Evidence**:
- `leaving the house while managing multiple competing tasks → drink not being readily available at point of departure` [triggers] (t=9): _"I'm already juggling a bunch of stuff when I leave the house"_
- `drink not being readily available at point of departure → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [triggers] (t=8): _"if I have to decide what to bring or remember to pack it, I probably won't"_

### Chain 47
**Path**:

  → `leaving the house while managing multiple competing tasks` (job_context, L0, t=9)  
  → `drink not being readily available at point of departure` (pain_point, L1, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `leaving the house while managing multiple competing tasks → drink not being readily available at point of departure` [triggers] (t=9): _"I'm already juggling a bunch of stuff when I leave the house"_
- `drink not being readily available at point of departure → drink already placed on the counter before leaving` [triggers] (t=8): _"if I have to decide what to bring or remember to pack it, I probably won't"_

### Chain 48
**Path**:

  → `leaving the house while managing multiple competing tasks` (job_context, L0, t=9)  
  → `drink not being readily available at point of departure` (pain_point, L1, t=9)  
  → `defaulting to whatever is convenient when preferred option isn't ready` (solution_approach, L4, t=9)  

**Evidence**:
- `leaving the house while managing multiple competing tasks → drink not being readily available at point of departure` [triggers] (t=9): _"I'm already juggling a bunch of stuff when I leave the house"_
- `drink not being readily available at point of departure → defaulting to whatever is convenient when preferred option isn't ready` [addresses (reversed)] (t=9): _"if I have to decide what to bring or remember to pack it, I probably won't"_

### Chain 49
**Path**:

  → `leaving the house while managing multiple competing tasks` (job_context, L0, t=9)  
  → `mental overhead of remembering to pack a drink kills follow-through` (pain_point, L1, t=8)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=8)  

**Evidence**:
- `leaving the house while managing multiple competing tasks → mental overhead of remembering to pack a drink kills follow-through` [triggers] (t=9): _"I'm already juggling a bunch of stuff when I leave the house"_
- `mental overhead of remembering to pack a drink kills follow-through → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [triggers] (t=8): _"if I have to decide what to bring or remember to pack it, I probably won't"_

### Chain 50
**Path**:

  → `leaving the house while managing multiple competing tasks` (job_context, L0, t=9)  
  → `mental overhead of remembering to pack a drink kills follow-through` (pain_point, L1, t=9)  
  → `defaulting to whatever is convenient when preferred option isn't ready` (solution_approach, L4, t=9)  

**Evidence**:
- `leaving the house while managing multiple competing tasks → mental overhead of remembering to pack a drink kills follow-through` [triggers] (t=9): _"I'm already juggling a bunch of stuff when I leave the house"_
- `mental overhead of remembering to pack a drink kills follow-through → defaulting to whatever is convenient when preferred option isn't ready` [addresses (reversed)] (t=9): _"if I have to decide what to bring or remember to pack it, I probably won't"_

### Chain 51
**Path**:

  → `being thirsty and wanting immediate drink access` (job_trigger, L0, t=10)  
  → `standing in front of the fridge deliberating over drink options` (pain_point, L1, t=10)  
  → `drink pre-chilled and stored in fridge for instant access` (solution_approach, L4, t=10)  

**Evidence**:
- `being thirsty and wanting immediate drink access → standing in front of the fridge deliberating over drink options` [triggers] (t=10): _"when I'm thirsty I don't want to stand in front of the fridge for five minutes weighing options"_
- `standing in front of the fridge deliberating over drink options → drink pre-chilled and stored in fridge for instant access` [addresses (reversed)] (t=10): _"I don't want to stand in front of the fridge for five minutes weighing options"_

### Chain 52
**Path**:

  → `being thirsty and wanting immediate drink access` (job_trigger, L0, t=10)  
  → `standing in front of the fridge deliberating over drink options` (pain_point, L1, t=10)  
  → `grabbing whatever is physically present in the fridge` (solution_approach, L4, t=10)  

**Evidence**:
- `being thirsty and wanting immediate drink access → standing in front of the fridge deliberating over drink options` [triggers] (t=10): _"when I'm thirsty I don't want to stand in front of the fridge for five minutes weighing options"_
- `standing in front of the fridge deliberating over drink options → grabbing whatever is physically present in the fridge` [addresses (reversed)] (t=10): _"I don't want to stand in front of the fridge for five minutes weighing options"_

### Chain 53
**Path**:

  → `cold carbonated drink delivers more alertness than coffee` (gain_point, L1, t=13)  
  → `feel alert and ready to start the day without relying on coffee` (emotional_job, L3, t=13)  
  → `grabbing whatever is physically present in the fridge` (solution_approach, L4, t=13)  

**Evidence**:
- `cold carbonated drink delivers more alertness than coffee → feel alert and ready to start the day without relying on coffee` [supports] (t=13): _"Gets me more alert than coffee sometimes, which sounds weird but it does."_
- `feel alert and ready to start the day without relying on coffee → grabbing whatever is physically present in the fridge` [drives] (t=13): _"Gets me more alert than coffee sometimes, which sounds weird but it does."_

### Chain 54
**Path**:

  → `cold carbonated drink delivers more alertness than coffee` (gain_point, L1, t=13)  
  → `feel alert and ready to start the day without relying on coffee` (emotional_job, L3, t=13)  
  → `reaching for a soda when thirsty during the day` (solution_approach, L4, t=13)  

**Evidence**:
- `cold carbonated drink delivers more alertness than coffee → feel alert and ready to start the day without relying on coffee` [supports] (t=13): _"Gets me more alert than coffee sometimes, which sounds weird but it does."_
- `feel alert and ready to start the day without relying on coffee → reaching for a soda when thirsty during the day` [drives] (t=13): _"Gets me more alert than coffee sometimes, which sounds weird but it does."_

## Developing chains — mid-level progression

### Chain 1
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=5)  
  → `switching to Diet Coke or similar when being careful about sugar` (solution_approach, L4, t=5)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → avoiding that heavy, bloated feeling after drinking` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `avoiding that heavy, bloated feeling after drinking → switching to Diet Coke or similar when being careful about sugar` [drives] (t=5): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 2
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=7)  
  → `zero-sugar drink grab is a pre-gym ritual, like putting on shoes` (solution_approach, L4, t=7)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → avoiding that heavy, bloated feeling after drinking` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `avoiding that heavy, bloated feeling after drinking → zero-sugar drink grab is a pre-gym ritual, like putting on shoes` [achieves (reversed)] (t=7): _"With the zero sugar stuff I don't get that heavy feeling."_

### Chain 3
**Path**:

  → `habitual repetition eliminates active decision-making at point of choice` (gain_point, L1, t=7)  
  → `avoiding that heavy, bloated feeling after drinking` (gain_point, L1, t=8)  
  → `drink already placed on the counter before leaving` (solution_approach, L4, t=8)  

**Evidence**:
- `habitual repetition eliminates active decision-making at point of choice → avoiding that heavy, bloated feeling after drinking` [supports] (t=7): _"I don't really weigh options anymore, it's just what I reach for."_
- `avoiding that heavy, bloated feeling after drinking → drink already placed on the counter before leaving` [achieves (reversed)] (t=8): _"With the zero sugar stuff I don't get that heavy feeling."_

## Revisions (positive validation signal)

_No revisions found._

## Orphan nodes (no incoming or outgoing chain edges)

- `mid-afternoon energy slump at work` (job_trigger, L0, t=0) — _"mid-afternoon slump kind of thing"_
- `when at work during the afternoon` (job_context, L0, t=0) — _"I was at work, just mid-afternoon slump kind of thing"_
- `get a refreshing energy boost to power through the afternoon` (job_statement, L2, t=0) — _"Needed something cold and carbonated I guess, just to like... wake up a bit without the crash later."_
- `avoiding sugar-induced energy crash later` (pain_point, L1, t=0) — _"wake up a bit without the crash later"_
- `not wanting sugar in a drink` (pain_point, L1, t=0) — _"didn't want coffee or anything with actual sugar"_
- `feeling alert and awake without a crash` (gain_point, L1, t=0) — _"wake up a bit without the crash later"_
- `cold and carbonated sensation as a pick-me-up` (gain_point, L1, t=0) — _"Needed something cold and carbonated I guess, just to like... wake up a bit"_
- `grabbing whatever sugar-free fizzy drink is available nearby` (solution_approach, L4, t=0) — _"I just grabbed whatever was in the break room fridge. Honestly can't even remember the brand, but it was one of those diet ones."_
- `low brand loyalty or awareness for sugar-free drinks` (pain_point, L1, t=0) — _"Honestly can't even remember the brand"_
- `sugar consciousness varies day to day rather than being a fixed rule` (job_context, L0, t=4) — _"Depends on the day I guess."_
- `morning thirst or routine as context for coffee choice` (job_context, L0, t=12) — _"Usually it's like a coffee in the morning"_

## Retracted chains (dropped due to supersession)
- **Count**: 0
- **Not printed in full** — these chains passed through nodes later marked as superseded.

## Methodology notes
- Chain rules: `config/chain_rules/jobs_to_be_done_v2.yaml`
- Tiers derived from 5 distinct ontology levels (num_tiers=4)
- Known limitations: Canonical slot layer may hide language variation relevant to chain validity.
