# Turn Diagnostics — 20260507_124611

- **Session**: `5fea41b9-791e-45b1-b760-63361e1dbd3d`
- **Methodology**: `jobs_to_be_done_v2`
- **Concept**: ZeroFizz Sugar-Free Carbonated Beverage - Jobs to be Done
- **Total turns**: 15

## Turn 0 — —

> **system**: I'd love to hear about your experience with drinks — specifically, think back to…
> **user**: I grabbed a Coke Zero the other day when I was at my desk working, probably mid-…

## Turn 1 — ascend

> **system**: Why does having that energy boost without the extra calories matter to you?
> **user**: Honestly, I just don't want to feel like I'm making a bad choice when I grab a d…

### Nodes extracted (7)

| ID | Label | Type |
|----|-------|------|
| `f30b5ef7` | working at desk mid-afternoon | `job_context` |
| `ede76614` | feeling low energy and needing a boost | `job_trigger` |
| `9e4762b8` | having already consumed too much plain water | `pain_point` |
| `02d67bd8` | get a mid-afternoon energy and focus boost | `job_statement` |
| `b6d79f4e` | enjoy a cold, fizzy sensory experience | `gain_point` |
| `b8f87e66` | get a caffeine lift without extra calories | `gain_point` |
| `f8353cb2` | drinking Coke Zero at the desk | `solution_approach` |

### Edges confirmed (17)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| working at desk mid-afternoon | t=1 | → | feeling low energy and needing a boost | t=1 | `triggers` | high | explicit | clear | respondent |
| working at desk mid-afternoon | t=1 | → | having already consumed too much plain water | t=1 | `occurs_in` | high | explicit | clear | respondent |
| working at desk mid-afternoon | t=1 | → | drinking Coke Zero at the desk | t=1 | `occurs_in` | high | explicit | clear | respondent |
| feeling low energy and needing a boost | t=1 | → | having already consumed too much plain water | t=1 | `implies` | medium | implicit | clear | respondent |
| feeling low energy and needing a boost | t=1 | → | get a mid-afternoon energy and focus boost | t=1 | `implies` | high | explicit | clear | respondent |
| feeling low energy and needing a boost | t=1 | → | enjoy a cold, fizzy sensory experience | t=1 | `supports` | medium | implicit | clear | respondent |
| feeling low energy and needing a boost | t=1 | → | get a caffeine lift without extra calories | t=1 | `supports` | medium | implicit | clear | respondent |
| feeling low energy and needing a boost | t=1 | → | drinking Coke Zero at the desk | t=1 | `drives` | high | explicit | clear | respondent |
| having already consumed too much plain water | t=1 | → | get a mid-afternoon energy and focus boost | t=1 | `implies` | medium | implicit | clear | respondent |
| having already consumed too much plain water | t=1 | → | enjoy a cold, fizzy sensory experience | t=1 | `implies` | high | explicit | clear | respondent |
| having already consumed too much plain water | t=1 | → | get a caffeine lift without extra calories | t=1 | `implies` | medium | implicit | clear | respondent |
| having already consumed too much plain water | t=1 | → | drinking Coke Zero at the desk | t=1 | `drives` | high | explicit | clear | respondent |
| get a mid-afternoon energy and focus boost | t=1 | → | enjoy a cold, fizzy sensory experience | t=1 | `supports` | medium | implicit | uncertain | respondent |
| get a mid-afternoon energy and focus boost | t=1 | → | get a caffeine lift without extra calories | t=1 | `supports` | medium | implicit | clear | respondent |
| get a mid-afternoon energy and focus boost | t=1 | → | drinking Coke Zero at the desk | t=1 | `drives` | high | explicit | clear | respondent |
| enjoy a cold, fizzy sensory experience | t=1 | → | drinking Coke Zero at the desk | t=1 | `achieves` | high | explicit | clear | respondent |
| get a caffeine lift without extra calories | t=1 | → | drinking Coke Zero at the desk | t=1 | `achieves` | high | explicit | clear | respondent |

### Rejected candidates (4)

| Reason | Count |
|--------|-------|
| `type_constraint_violation` | 4 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| working at desk mid-afternoon | → | get a mid-afternoon energy and focus boost | `type_constraint_violation` |
| working at desk mid-afternoon | → | enjoy a cold, fizzy sensory experience | `type_constraint_violation` |
| working at desk mid-afternoon | → | get a caffeine lift without extra calories | `type_constraint_violation` |
| enjoy a cold, fizzy sensory experience | → | get a caffeine lift without extra calories | `type_constraint_violation` |

</details>

## Turn 2 — anchor

> **system**: When you reach for a Coke Zero instead, what changes about how you feel compared…
> **user**: Honestly, it's mostly just not feeling guilty after. Like with regular Coke I kn…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `3b2e6913` | feel good about drink choices without guilt | `emotional_job` |
| `f39800e2` | awareness that sugary drinks are unhealthy | `job_trigger` |
| `23871f5e` | post-consumption guilt from unhealthy drink choices | `pain_point` |

### Rejected candidates (24)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 24 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| feel good about drink choices without guilt | → | get a caffeine lift without extra calories | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | get a caffeine lift without extra calories | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | get a caffeine lift without extra calories | `insufficient_evidence` |
| feel good about drink choices without guilt | → | drinking Coke Zero at the desk | `insufficient_evidence` |
| feel good about drink choices without guilt | → | feeling low energy and needing a boost | `insufficient_evidence` |
| feel good about drink choices without guilt | → | having already consumed too much plain water | `insufficient_evidence` |
| feel good about drink choices without guilt | → | get a mid-afternoon energy and focus boost | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | drinking Coke Zero at the desk | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | feeling low energy and needing a boost | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | having already consumed too much plain water | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | get a mid-afternoon energy and focus boost | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | drinking Coke Zero at the desk | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | feeling low energy and needing a boost | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | having already consumed too much plain water | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | get a mid-afternoon energy and focus boost | `insufficient_evidence` |
| feel good about drink choices without guilt | → | awareness that sugary drinks are unhealthy | `insufficient_evidence` |
| feel good about drink choices without guilt | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| feel good about drink choices without guilt | → | working at desk mid-afternoon | `insufficient_evidence` |
| feel good about drink choices without guilt | → | enjoy a cold, fizzy sensory experience | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | working at desk mid-afternoon | `insufficient_evidence` |
| awareness that sugary drinks are unhealthy | → | enjoy a cold, fizzy sensory experience | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | working at desk mid-afternoon | `insufficient_evidence` |
| post-consumption guilt from unhealthy drink choices | → | enjoy a cold, fizzy sensory experience | `insufficient_evidence` |

</details>

## Turn 3 — anchor

> **system**: Where did that awareness about sugar being unhealthy come from for you?
> **user**: Honestly, I don't remember a specific moment. It's just been around forever — li…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `1ed1475f` | awareness of high sugar content in regular Coke | `pain_point` |
| `a8bc77f9` | persistent mental nagging about unhealthy drink choices | `pain_point` |
| `3b2e6913` | feel good about drink choices without guilt | `emotional_job` |

### Edges confirmed (5)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| awareness of high sugar content in regular Coke | t=3 | → | feel good about drink choices without guilt | t=3 | `implies` | high | explicit | clear | respondent |
| persistent mental nagging about unhealthy drink choices | t=3 | → | feel good about drink choices without guilt | t=3 | `implies` | high | explicit | clear | respondent |
| awareness of high sugar content in regular Coke | t=3 | → | persistent mental nagging about unhealthy drink choices | t=3 | `supports` | medium | implicit | clear | respondent |
| awareness of high sugar content in regular Coke | t=3 | → | post-consumption guilt from unhealthy drink choices | t=2 | `triggers` | high | explicit | clear | respondent |
| persistent mental nagging about unhealthy drink choices | t=3 | → | post-consumption guilt from unhealthy drink choices | t=2 | `supports` | medium | implicit | clear | respondent |

### Rejected candidates (2)

| Reason | Count |
|--------|-------|
| `semantic_irrelevance` | 2 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| awareness of high sugar content in regular Coke | → | awareness that sugary drinks are unhealthy | `semantic_irrelevance` |
| persistent mental nagging about unhealthy drink choices | → | awareness that sugary drinks are unhealthy | `semantic_irrelevance` |

</details>

## Turn 4 — ground

> **system**: What is it about knowing you're putting sugar in that makes you feel that little…
> **user**: Honestly, it's more like... guilt I guess? Like I know it's not great for me, es…

### Nodes extracted (2)

| ID | Label | Type |
|----|-------|------|
| `f81ea48a` | growing up in a health-conscious family environment | `job_context` |
| `48143854` | pervasive cultural and media messaging that sugar is unhealt… | `job_context` |

### Edges confirmed (2)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| growing up in a health-conscious family environment | t=4 | → | awareness that sugary drinks are unhealthy | t=2 | `triggers` | medium | implicit | clear | respondent |
| pervasive cultural and media messaging that sugar is unhealthy | t=4 | → | awareness that sugary drinks are unhealthy | t=2 | `triggers` | medium | implicit | clear | respondent |

### Rejected candidates (7)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 7 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| growing up in a health-conscious family environment | → | pervasive cultural and media messaging that sugar is unhealthy | `insufficient_evidence` |
| growing up in a health-conscious family environment | → | feel good about drink choices without guilt | `insufficient_evidence` |
| growing up in a health-conscious family environment | → | awareness of high sugar content in regular Coke | `insufficient_evidence` |
| growing up in a health-conscious family environment | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| pervasive cultural and media messaging that sugar is unhealthy | → | feel good about drink choices without guilt | `insufficient_evidence` |
| pervasive cultural and media messaging that sugar is unhealthy | → | awareness of high sugar content in regular Coke | `insufficient_evidence` |
| pervasive cultural and media messaging that sugar is unhealthy | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |

</details>

## Turn 5 — ascend

> **system**: When you reach for a Zero instead of regular Coke, does that actually change how…
> **user**: I think it does, yeah. Like with regular Coke I kind of feel like I'm making a b…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `d4ae8dab` | making choices that undermine personal health goals | `pain_point` |
| `fc401949` | drinking sugary drinks regularly amplifies health concern | `job_context` |
| `eb092427` | feel aligned with personal health standards | `emotional_job` |

### Edges confirmed (10)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| drinking sugary drinks regularly amplifies health concern | t=5 | → | awareness of high sugar content in regular Coke | t=3 | `triggers` | medium | implicit | clear | respondent |
| making choices that undermine personal health goals | t=5 | → | post-consumption guilt from unhealthy drink choices | t=2 | `triggers` | high | explicit | clear | respondent |
| making choices that undermine personal health goals | t=5 | → | feel good about drink choices without guilt | t=3 | `drives` | high | explicit | clear | respondent |
| making choices that undermine personal health goals | t=5 | → | persistent mental nagging about unhealthy drink choices | t=3 | `triggers` | high | explicit | clear | respondent |
| drinking sugary drinks regularly amplifies health concern | t=5 | → | post-consumption guilt from unhealthy drink choices | t=2 | `triggers` | medium | implicit | clear | respondent |
| drinking sugary drinks regularly amplifies health concern | t=5 | → | feel good about drink choices without guilt | t=3 | `drives` | medium | implicit | clear | respondent |
| drinking sugary drinks regularly amplifies health concern | t=5 | → | persistent mental nagging about unhealthy drink choices | t=3 | `triggers` | medium | implicit | clear | respondent |
| making choices that undermine personal health goals | t=5 | → | feel aligned with personal health standards | t=5 | `drives` | high | explicit | clear | respondent |
| drinking sugary drinks regularly amplifies health concern | t=5 | → | feel aligned with personal health standards | t=5 | `drives` | medium | implicit | clear | respondent |
| drinking sugary drinks regularly amplifies health concern | t=5 | → | pervasive cultural and media messaging that sugar is unhealthy | t=4 | `occurs_in` | medium | implicit | clear | respondent |

### Rejected candidates (10)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 5 |
| `semantic_irrelevance` | 4 |
| `duplicate_edge` | 1 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| making choices that undermine personal health goals | → | awareness of high sugar content in regular Coke | `semantic_irrelevance` |
| feel aligned with personal health standards | → | awareness of high sugar content in regular Coke | `semantic_irrelevance` |
| feel aligned with personal health standards | → | post-consumption guilt from unhealthy drink choices | `semantic_irrelevance` |
| feel aligned with personal health standards | → | feel good about drink choices without guilt | `duplicate_edge` |
| feel aligned with personal health standards | → | persistent mental nagging about unhealthy drink choices | `semantic_irrelevance` |
| making choices that undermine personal health goals | → | drinking sugary drinks regularly amplifies health concern | `insufficient_evidence` |
| making choices that undermine personal health goals | → | pervasive cultural and media messaging that sugar is unhealthy | `insufficient_evidence` |
| drinking sugary drinks regularly amplifies health concern | → | growing up in a health-conscious family environment | `insufficient_evidence` |
| feel aligned with personal health standards | → | growing up in a health-conscious family environment | `insufficient_evidence` |
| feel aligned with personal health standards | → | pervasive cultural and media messaging that sugar is unhealthy | `insufficient_evidence` |

</details>

## Turn 6 — ground

> **system**: What is it about drinking Zero instead that actually removes that nagging feelin…
> **user**: Honestly it's just knowing I'm not dumping a bunch of sugar into my system. Like…

### Nodes extracted (2)

| ID | Label | Type |
|----|-------|------|
| `94562ad3` | drinking Coke Zero removes the nagging guilt of a bad choice | `gain_point` |
| `611ff04d` | feel less conflicted rather than virtuous about drink choice… | `emotional_job` |

### Edges confirmed (2)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| drinking Coke Zero removes the nagging guilt of a bad choice | t=6 | → | feel aligned with personal health standards | t=5 | `achieves` | high | explicit | clear | respondent |
| feel less conflicted rather than virtuous about drink choices | t=6 | → | feel aligned with personal health standards | t=5 | `achieves` | medium | implicit | clear | respondent |

### Rejected candidates (5)

| Reason | Count |
|--------|-------|
| `semantic_irrelevance` | 4 |
| `duplicate_edge` | 1 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| drinking Coke Zero removes the nagging guilt of a bad choice | → | making choices that undermine personal health goals | `semantic_irrelevance` |
| drinking Coke Zero removes the nagging guilt of a bad choice | → | drinking sugary drinks regularly amplifies health concern | `semantic_irrelevance` |
| feel less conflicted rather than virtuous about drink choices | → | making choices that undermine personal health goals | `semantic_irrelevance` |
| feel less conflicted rather than virtuous about drink choices | → | drinking sugary drinks regularly amplifies health concern | `semantic_irrelevance` |
| drinking Coke Zero removes the nagging guilt of a bad choice | → | feel less conflicted rather than virtuous about drink choices | `duplicate_edge` |

</details>

## Turn 7 — ground

> **system**: What situations make it easier for you to just drink Zero without that mental ch…
> **user**: Honestly when I'm just thirsty and grab something cold, I don't really think abo…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `4f440b4f` | avoiding loading body with excess sugar | `gain_point` |
| `83e25cad` | concern about sugar's effect on dental health | `pain_point` |
| `56dbf699` | drink without mentally tracking health consequences | `gain_point` |

### Edges confirmed (9)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| avoiding loading body with excess sugar | t=7 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | high | explicit | clear | respondent |
| concern about sugar's effect on dental health | t=7 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | high | explicit | clear | respondent |
| drink without mentally tracking health consequences | t=7 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | high | explicit | clear | respondent |
| avoiding loading body with excess sugar | t=7 | → | feel aligned with personal health standards | t=5 | `implies` | medium | implicit | clear | respondent |
| concern about sugar's effect on dental health | t=7 | → | feel aligned with personal health standards | t=5 | `implies` | medium | implicit | clear | respondent |
| drink without mentally tracking health consequences | t=7 | → | feel aligned with personal health standards | t=5 | `supports` | medium | implicit | clear | respondent |
| concern about sugar's effect on dental health | t=7 | → | drink without mentally tracking health consequences | t=7 | `triggers` | medium | implicit | clear | respondent |
| avoiding loading body with excess sugar | t=7 | → | drinking Coke Zero removes the nagging guilt of a bad choice | t=6 | `supports` | high | explicit | clear | respondent |
| concern about sugar's effect on dental health | t=7 | → | drinking Coke Zero removes the nagging guilt of a bad choice | t=6 | `triggers` | high | explicit | clear | respondent |

### Rejected candidates (3)

| Reason | Count |
|--------|-------|
| `duplicate_edge` | 2 |
| `semantic_irrelevance` | 1 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| avoiding loading body with excess sugar | → | concern about sugar's effect on dental health | `semantic_irrelevance` |
| avoiding loading body with excess sugar | → | drink without mentally tracking health consequences | `duplicate_edge` |
| drink without mentally tracking health consequences | → | drinking Coke Zero removes the nagging guilt of a bad choice | `duplicate_edge` |

</details>

## Turn 8 — ascend

> **system**: When you're back home later and have time to think, does that health stuff creep…
> **user**: Honestly it kind of comes and goes. Like if I'm scrolling and see something abou…

### Nodes extracted (4)

| ID | Label | Type |
|----|-------|------|
| `a7c6f1aa` | feeling thirsty and wanting something cold | `job_trigger` |
| `0c6cedf2` | being out somewhere or at work and wanting a drink | `job_context` |
| `94b50550` | find a drink that simply tastes good | `job_statement` |
| `6f6f3bdb` | health considerations fade when not actively worrying | `gain_point` |

### Edges confirmed (12)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| find a drink that simply tastes good | t=8 | → | feel good about drink choices without guilt | t=3 | `implies` | medium | implicit | clear | respondent |
| find a drink that simply tastes good | t=8 | → | feel aligned with personal health standards | t=5 | `implies` | medium | implicit | clear | respondent |
| health considerations fade when not actively worrying | t=8 | → | feel good about drink choices without guilt | t=3 | `supports` | high | explicit | clear | respondent |
| health considerations fade when not actively worrying | t=8 | → | feel aligned with personal health standards | t=5 | `supports` | high | explicit | clear | respondent |
| feeling thirsty and wanting something cold | t=8 | → | find a drink that simply tastes good | t=8 | `triggers` | high | explicit | clear | respondent |
| feeling thirsty and wanting something cold | t=8 | → | health considerations fade when not actively worrying | t=8 | `triggers` | high | explicit | clear | respondent |
| being out somewhere or at work and wanting a drink | t=8 | → | find a drink that simply tastes good | t=8 | `triggers` | high | explicit | clear | respondent |
| being out somewhere or at work and wanting a drink | t=8 | → | health considerations fade when not actively worrying | t=8 | `triggers` | high | explicit | clear | respondent |
| feeling thirsty and wanting something cold | t=8 | → | drink without mentally tracking health consequences | t=7 | `triggers` | high | explicit | clear | respondent |
| being out somewhere or at work and wanting a drink | t=8 | → | drink without mentally tracking health consequences | t=7 | `triggers` | high | explicit | clear | respondent |
| find a drink that simply tastes good | t=8 | → | drink without mentally tracking health consequences | t=7 | `implies` | medium | implicit | clear | respondent |
| health considerations fade when not actively worrying | t=8 | → | drink without mentally tracking health consequences | t=7 | `supports` | high | explicit | clear | respondent |

### Rejected candidates (26)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 26 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| feeling thirsty and wanting something cold | → | making choices that undermine personal health goals | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | making choices that undermine personal health goals | `insufficient_evidence` |
| find a drink that simply tastes good | → | making choices that undermine personal health goals | `insufficient_evidence` |
| health considerations fade when not actively worrying | → | making choices that undermine personal health goals | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | feel good about drink choices without guilt | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | feel aligned with personal health standards | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | feel good about drink choices without guilt | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | feel aligned with personal health standards | `insufficient_evidence` |
| find a drink that simply tastes good | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| find a drink that simply tastes good | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| health considerations fade when not actively worrying | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| health considerations fade when not actively worrying | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | being out somewhere or at work and wanting a drink | `insufficient_evidence` |
| find a drink that simply tastes good | → | health considerations fade when not actively worrying | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | avoiding loading body with excess sugar | `insufficient_evidence` |
| feeling thirsty and wanting something cold | → | concern about sugar's effect on dental health | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | avoiding loading body with excess sugar | `insufficient_evidence` |
| being out somewhere or at work and wanting a drink | → | concern about sugar's effect on dental health | `insufficient_evidence` |
| find a drink that simply tastes good | → | avoiding loading body with excess sugar | `insufficient_evidence` |
| find a drink that simply tastes good | → | concern about sugar's effect on dental health | `insufficient_evidence` |
| health considerations fade when not actively worrying | → | avoiding loading body with excess sugar | `insufficient_evidence` |
| health considerations fade when not actively worrying | → | concern about sugar's effect on dental health | `insufficient_evidence` |

</details>

## Turn 9 — ascend

> **system**: When you're busy with something else and that worry fades, what does that feel l…
> **user**: Honestly it's pretty different. When I'm distracted by work or whatever, it just…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `8a4caebc` | encountering content about artificial sweeteners while scrol… | `job_trigger` |
| `8c20de16` | intermittent concern about artificial sweeteners in sugar-fr… | `pain_point` |
| `3d0048e0` | being occupied with other tasks dissolves health concern qui… | `gain_point` |

### Edges confirmed (9)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| being occupied with other tasks dissolves health concern quickly | t=9 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | medium | implicit | clear | respondent |
| being occupied with other tasks dissolves health concern quickly | t=9 | → | feel aligned with personal health standards | t=5 | `implies` | medium | implicit | clear | respondent |
| being occupied with other tasks dissolves health concern quickly | t=9 | → | avoiding loading body with excess sugar | t=7 | `implies` | medium | implicit | clear | respondent |
| being occupied with other tasks dissolves health concern quickly | t=9 | → | concern about sugar's effect on dental health | t=7 | `implies` | medium | implicit | clear | respondent |
| being occupied with other tasks dissolves health concern quickly | t=9 | → | drink without mentally tracking health consequences | t=7 | `implies` | medium | implicit | clear | respondent |
| encountering content about artificial sweeteners while scrolling | t=9 | → | intermittent concern about artificial sweeteners in sugar-free drinks | t=9 | `triggers` | high | explicit | clear | respondent |
| intermittent concern about artificial sweeteners in sugar-free drinks | t=9 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `triggers` | medium | implicit | clear | respondent |
| intermittent concern about artificial sweeteners in sugar-free drinks | t=9 | → | health considerations fade when not actively worrying | t=8 | `triggers` | medium | implicit | clear | respondent |
| being occupied with other tasks dissolves health concern quickly | t=9 | → | health considerations fade when not actively worrying | t=8 | `triggers` | high | explicit | clear | respondent |

### Rejected candidates (21)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 11 |
| `semantic_irrelevance` | 10 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| encountering content about artificial sweeteners while scrolling | → | feel less conflicted rather than virtuous about drink choices | `insufficient_evidence` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | feel less conflicted rather than virtuous about drink choices | `insufficient_evidence` |
| encountering content about artificial sweeteners while scrolling | → | feel aligned with personal health standards | `insufficient_evidence` |
| encountering content about artificial sweeteners while scrolling | → | avoiding loading body with excess sugar | `insufficient_evidence` |
| encountering content about artificial sweeteners while scrolling | → | concern about sugar's effect on dental health | `insufficient_evidence` |
| encountering content about artificial sweeteners while scrolling | → | drink without mentally tracking health consequences | `insufficient_evidence` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | feel aligned with personal health standards | `insufficient_evidence` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | avoiding loading body with excess sugar | `insufficient_evidence` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | concern about sugar's effect on dental health | `semantic_irrelevance` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | drink without mentally tracking health consequences | `insufficient_evidence` |
| encountering content about artificial sweeteners while scrolling | → | being occupied with other tasks dissolves health concern quickly | `insufficient_evidence` |
| encountering content about artificial sweeteners while scrolling | → | feeling thirsty and wanting something cold | `semantic_irrelevance` |
| encountering content about artificial sweeteners while scrolling | → | being out somewhere or at work and wanting a drink | `semantic_irrelevance` |
| encountering content about artificial sweeteners while scrolling | → | find a drink that simply tastes good | `semantic_irrelevance` |
| encountering content about artificial sweeteners while scrolling | → | health considerations fade when not actively worrying | `insufficient_evidence` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | feeling thirsty and wanting something cold | `semantic_irrelevance` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | being out somewhere or at work and wanting a drink | `semantic_irrelevance` |
| intermittent concern about artificial sweeteners in sugar-free drinks | → | find a drink that simply tastes good | `semantic_irrelevance` |
| being occupied with other tasks dissolves health concern quickly | → | feeling thirsty and wanting something cold | `semantic_irrelevance` |
| being occupied with other tasks dissolves health concern quickly | → | being out somewhere or at work and wanting a drink | `semantic_irrelevance` |
| being occupied with other tasks dissolves health concern quickly | → | find a drink that simply tastes good | `semantic_irrelevance` |

</details>

## Turn 10 — ascend

> **system**: When that concern feels heavier and more present, what would it mean for you to …
> **user**: Honestly, it'd just mean I could grab something without the guilt loop, you know…

### Nodes extracted (2)

| ID | Label | Type |
|----|-------|------|
| `3ffeea51` | distraction from work dissolves health concern entirely | `gain_point` |
| `310cb7a0` | sitting with health concern makes it feel heavier and more p… | `pain_point` |

### Edges confirmed (2)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| distraction from work dissolves health concern entirely | t=10 | → | sitting with health concern makes it feel heavier and more present | t=10 | `conflicts_with` | high | explicit | clear | respondent |
| sitting with health concern makes it feel heavier and more present | t=10 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `conflicts_with` | high | explicit | clear | respondent |

### Rejected candidates (15)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 14 |
| `duplicate_edge` | 1 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| distraction from work dissolves health concern entirely | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| sitting with health concern makes it feel heavier and more present | → | post-consumption guilt from unhealthy drink choices | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | awareness of high sugar content in regular Coke | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | making choices that undermine personal health goals | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | drinking sugary drinks regularly amplifies health concern | `insufficient_evidence` |
| sitting with health concern makes it feel heavier and more present | → | awareness of high sugar content in regular Coke | `insufficient_evidence` |
| sitting with health concern makes it feel heavier and more present | → | persistent mental nagging about unhealthy drink choices | `insufficient_evidence` |
| sitting with health concern makes it feel heavier and more present | → | making choices that undermine personal health goals | `insufficient_evidence` |
| sitting with health concern makes it feel heavier and more present | → | drinking sugary drinks regularly amplifies health concern | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | encountering content about artificial sweeteners while scrolling | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | intermittent concern about artificial sweeteners in sugar-free drinks | `insufficient_evidence` |
| distraction from work dissolves health concern entirely | → | being occupied with other tasks dissolves health concern quickly | `duplicate_edge` |
| sitting with health concern makes it feel heavier and more present | → | encountering content about artificial sweeteners while scrolling | `insufficient_evidence` |
| sitting with health concern makes it feel heavier and more present | → | intermittent concern about artificial sweeteners in sugar-free drinks | `insufficient_evidence` |

</details>

## Turn 11 — ground

> **system**: What usually happens right before you hit that moment where you're stuck between…
> **user**: Honestly I'm usually just thirsty or want something with flavor that isn't water…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `11324c39` | choosing between sugar guilt and going without a desired dri… | `pain_point` |
| `c043eb34` | grab a drink without triggering a guilt loop | `gain_point` |
| `60e50c99` | drink without having to think about health trade-offs at all | `gain_point` |

### Edges confirmed (22)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| choosing between sugar guilt and going without a desired drink | t=11 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | high | explicit | clear | respondent |
| grab a drink without triggering a guilt loop | t=11 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | high | explicit | clear | respondent |
| drink without having to think about health trade-offs at all | t=11 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `implies` | high | explicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | feel aligned with personal health standards | t=5 | `implies` | medium | implicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | avoiding loading body with excess sugar | t=7 | `implies` | high | explicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | concern about sugar's effect on dental health | t=7 | `supports` | medium | implicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | drink without mentally tracking health consequences | t=7 | `implies` | high | explicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `implies` | high | explicit | clear | respondent |
| grab a drink without triggering a guilt loop | t=11 | → | feel aligned with personal health standards | t=5 | `achieves` | high | explicit | clear | respondent |
| grab a drink without triggering a guilt loop | t=11 | → | avoiding loading body with excess sugar | t=7 | `supports` | medium | implicit | clear | respondent |
| grab a drink without triggering a guilt loop | t=11 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `supports` | medium | implicit | clear | respondent |
| drink without having to think about health trade-offs at all | t=11 | → | feel aligned with personal health standards | t=5 | `achieves` | high | explicit | clear | respondent |
| drink without having to think about health trade-offs at all | t=11 | → | avoiding loading body with excess sugar | t=7 | `supports` | medium | implicit | clear | respondent |
| drink without having to think about health trade-offs at all | t=11 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `supports` | medium | implicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | grab a drink without triggering a guilt loop | t=11 | `implies` | high | explicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | drink without having to think about health trade-offs at all | t=11 | `implies` | high | explicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | distraction from work dissolves health concern entirely | t=10 | `implies` | high | explicit | clear | respondent |
| choosing between sugar guilt and going without a desired drink | t=11 | → | sitting with health concern makes it feel heavier and more present | t=10 | `implies` | high | explicit | clear | respondent |
| grab a drink without triggering a guilt loop | t=11 | → | distraction from work dissolves health concern entirely | t=10 | `supports` | medium | implicit | clear | respondent |
| grab a drink without triggering a guilt loop | t=11 | → | sitting with health concern makes it feel heavier and more present | t=10 | `conflicts_with` | medium | implicit | clear | respondent |
| drink without having to think about health trade-offs at all | t=11 | → | distraction from work dissolves health concern entirely | t=10 | `supports` | medium | implicit | clear | respondent |
| drink without having to think about health trade-offs at all | t=11 | → | sitting with health concern makes it feel heavier and more present | t=10 | `conflicts_with` | medium | implicit | clear | respondent |

### Rejected candidates (5)

| Reason | Count |
|--------|-------|
| `duplicate_edge` | 3 |
| `semantic_irrelevance` | 2 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| grab a drink without triggering a guilt loop | → | concern about sugar's effect on dental health | `semantic_irrelevance` |
| grab a drink without triggering a guilt loop | → | drink without mentally tracking health consequences | `duplicate_edge` |
| drink without having to think about health trade-offs at all | → | concern about sugar's effect on dental health | `semantic_irrelevance` |
| drink without having to think about health trade-offs at all | → | drink without mentally tracking health consequences | `duplicate_edge` |
| grab a drink without triggering a guilt loop | → | drink without having to think about health trade-offs at all | `duplicate_edge` |

</details>

## Turn 12 — ascend

> **system**: When you're scanning what's available, what matters most about having ZeroFizz a…
> **user**: Honestly, it's just nice to have something that doesn't feel like a compromise. …

### Nodes extracted (2)

| ID | Label | Type |
|----|-------|------|
| `bbb52175` | wanting a drink with flavor as an alternative to water | `job_trigger` |
| `045f2d76` | scanning available drink options at work or home | `solution_approach` |

### Edges confirmed (23)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| wanting a drink with flavor as an alternative to water | t=12 | → | choosing between sugar guilt and going without a desired drink | t=11 | `triggers` | high | explicit | clear | respondent |
| scanning available drink options at work or home | t=12 | → | choosing between sugar guilt and going without a desired drink | t=11 | `triggers` | medium | implicit | clear | respondent |
| wanting a drink with flavor as an alternative to water | t=12 | → | sitting with health concern makes it feel heavier and more present | t=10 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | distraction from work dissolves health concern entirely | t=10 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | avoiding loading body with excess sugar | t=7 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | drink without mentally tracking health consequences | t=7 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | drink without having to think about health trade-offs at all | t=11 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | concern about sugar's effect on dental health | t=7 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | grab a drink without triggering a guilt loop | t=11 | `triggers` | medium | implicit | clear | minor_influence |
| wanting a drink with flavor as an alternative to water | t=12 | → | feel aligned with personal health standards | t=5 | `triggers` | medium | implicit | clear | minor_influence |
| scanning available drink options at work or home | t=12 | → | sitting with health concern makes it feel heavier and more present | t=10 | `triggers` | medium | implicit | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | being occupied with other tasks dissolves health concern quickly | t=9 | `triggers` | medium | implicit | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | distraction from work dissolves health concern entirely | t=10 | `triggers` | medium | implicit | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | avoiding loading body with excess sugar | t=7 | `triggers` | low | inferred | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | drink without mentally tracking health consequences | t=7 | `triggers` | low | inferred | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | drink without having to think about health trade-offs at all | t=11 | `triggers` | low | inferred | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | feel less conflicted rather than virtuous about drink choices | t=6 | `triggers` | low | inferred | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | concern about sugar's effect on dental health | t=7 | `triggers` | low | inferred | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | grab a drink without triggering a guilt loop | t=11 | `triggers` | low | inferred | clear | contaminated |
| scanning available drink options at work or home | t=12 | → | feel aligned with personal health standards | t=5 | `triggers` | low | inferred | clear | contaminated |
| wanting a drink with flavor as an alternative to water | t=12 | → | scanning available drink options at work or home | t=12 | `triggers` | high | explicit | clear | respondent |

## Turn 13 — ground

> **system**: What specifically about ZeroFizz makes it feel like you're not giving something …
> **user**: I think it's just that it actually tastes pretty close to the regular thing. Lik…

### Nodes extracted (3)

| ID | Label | Type |
|----|-------|------|
| `d20660b6` | having a drink option that feels like no compromise | `gain_point` |
| `e0a562c0` | taste good enough to drink willingly without forcing it | `gain_point` |
| `c741f9ce` | choosing ZeroFizz as the available drink option | `solution_approach` |

### Edges confirmed (2)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| choosing ZeroFizz as the available drink option | t=13 | → | grab a drink without triggering a guilt loop | t=11 | `achieves` | high | explicit | clear | respondent |
| choosing ZeroFizz as the available drink option | t=13 | → | drink without having to think about health trade-offs at all | t=11 | `achieves` | high | explicit | clear | respondent |

### Rejected candidates (22)

| Reason | Count |
|--------|-------|
| `insufficient_evidence` | 22 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| having a drink option that feels like no compromise | → | distraction from work dissolves health concern entirely | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | distraction from work dissolves health concern entirely | `insufficient_evidence` |
| choosing ZeroFizz as the available drink option | → | distraction from work dissolves health concern entirely | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | sitting with health concern makes it feel heavier and more present | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | choosing between sugar guilt and going without a desired drink | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | grab a drink without triggering a guilt loop | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | drink without having to think about health trade-offs at all | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | wanting a drink with flavor as an alternative to water | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | scanning available drink options at work or home | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | sitting with health concern makes it feel heavier and more present | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | choosing between sugar guilt and going without a desired drink | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | grab a drink without triggering a guilt loop | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | drink without having to think about health trade-offs at all | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | wanting a drink with flavor as an alternative to water | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | scanning available drink options at work or home | `insufficient_evidence` |
| choosing ZeroFizz as the available drink option | → | sitting with health concern makes it feel heavier and more present | `insufficient_evidence` |
| choosing ZeroFizz as the available drink option | → | choosing between sugar guilt and going without a desired drink | `insufficient_evidence` |
| choosing ZeroFizz as the available drink option | → | wanting a drink with flavor as an alternative to water | `insufficient_evidence` |
| choosing ZeroFizz as the available drink option | → | scanning available drink options at work or home | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | taste good enough to drink willingly without forcing it | `insufficient_evidence` |
| having a drink option that feels like no compromise | → | choosing ZeroFizz as the available drink option | `insufficient_evidence` |
| taste good enough to drink willingly without forcing it | → | choosing ZeroFizz as the available drink option | `insufficient_evidence` |

</details>

## Turn 14 — close

> **system**: So it sounds like the main thing is having a drink that satisfies your thirst an…
> **user**: I mean, that's pretty much it. Maybe just... convenience? Like I don't want to h…

### Nodes extracted (4)

| ID | Label | Type |
|----|-------|------|
| `a9d6f0c8` | taste closely matching regular (non-diet) drinks | `gain_point` |
| `e7012cc7` | noticeable off-taste in other diet drinks | `pain_point` |
| `be0e218c` | absence of weird aftertaste in ZeroFizz | `gain_point` |
| `d1d36d0c` | taste difference small enough to avoid feeling like a compro… | `gain_point` |

### Edges confirmed (16)

| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |
|--------|---|---|--------|---|------|------|-----------|-----------|-------|
| taste closely matching regular (non-diet) drinks | t=14 | → | having a drink option that feels like no compromise | t=13 | `supports` | high | explicit | clear | respondent |
| noticeable off-taste in other diet drinks | t=14 | → | having a drink option that feels like no compromise | t=13 | `supports` | high | explicit | clear | respondent |
| absence of weird aftertaste in ZeroFizz | t=14 | → | having a drink option that feels like no compromise | t=13 | `supports` | high | explicit | clear | respondent |
| taste difference small enough to avoid feeling like a compromise | t=14 | → | having a drink option that feels like no compromise | t=13 | `supports` | high | explicit | clear | respondent |
| taste closely matching regular (non-diet) drinks | t=14 | → | absence of weird aftertaste in ZeroFizz | t=14 | `supports` | medium | implicit | clear | respondent |
| noticeable off-taste in other diet drinks | t=14 | → | absence of weird aftertaste in ZeroFizz | t=14 | `supports` | high | explicit | clear | respondent |
| noticeable off-taste in other diet drinks | t=14 | → | taste difference small enough to avoid feeling like a compromise | t=14 | `supports` | high | explicit | clear | respondent |
| absence of weird aftertaste in ZeroFizz | t=14 | → | taste difference small enough to avoid feeling like a compromise | t=14 | `supports` | high | explicit | clear | respondent |
| taste closely matching regular (non-diet) drinks | t=14 | → | taste good enough to drink willingly without forcing it | t=13 | `supports` | high | explicit | clear | respondent |
| taste closely matching regular (non-diet) drinks | t=14 | → | choosing ZeroFizz as the available drink option | t=13 | `drives` | high | explicit | clear | respondent |
| noticeable off-taste in other diet drinks | t=14 | → | taste good enough to drink willingly without forcing it | t=13 | `supports` | medium | implicit | clear | respondent |
| noticeable off-taste in other diet drinks | t=14 | → | choosing ZeroFizz as the available drink option | t=13 | `drives` | high | explicit | clear | respondent |
| absence of weird aftertaste in ZeroFizz | t=14 | → | taste good enough to drink willingly without forcing it | t=13 | `supports` | high | explicit | clear | respondent |
| absence of weird aftertaste in ZeroFizz | t=14 | → | choosing ZeroFizz as the available drink option | t=13 | `drives` | high | explicit | clear | respondent |
| taste difference small enough to avoid feeling like a compromise | t=14 | → | taste good enough to drink willingly without forcing it | t=13 | `supports` | high | explicit | clear | respondent |
| taste difference small enough to avoid feeling like a compromise | t=14 | → | choosing ZeroFizz as the available drink option | t=13 | `drives` | high | explicit | clear | respondent |

### Rejected candidates (2)

| Reason | Count |
|--------|-------|
| `semantic_irrelevance` | 1 |
| `duplicate_edge` | 1 |

<details>
<summary>Per-pair details</summary>

| Source | → | Target | Reason |
|--------|---|--------|--------|
| taste closely matching regular (non-diet) drinks | → | noticeable off-taste in other diet drinks | `semantic_irrelevance` |
| taste closely matching regular (non-diet) drinks | → | taste difference small enough to avoid feeling like a compromise | `duplicate_edge` |

</details>
