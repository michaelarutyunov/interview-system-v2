

# AI Moderation Isn’t Missing “Spark”. It’s Missing a Relational Model.

> *"The formulas are there, but the spark isn't. The problem is that humans break structure in ways that feel alive. AI does not. At least not yet."*
> — Daniel Berkal, SVP, The Palmerston Group (quoted in Nexxt Intelligence, 2026)

Berkal’s diagnosis is right — but “spark” is the wrong word for what human moderators actually contribute.

What experienced moderators bring is not charisma. It’s **live sensemaking**: a running model of what the respondent believes, what motivates them, what doesn’t quite add up yet, and what still needs explaining.

Most AI moderation systems don’t operate with that kind of model. They operate closer to **topic tracking**.

And that difference matters.

---

# What the Recent Evaluations Actually Say

Two recent industry publications offer a surprisingly consistent picture of where AI-moderated qual performs well — and where it still hits a ceiling.

The Nexxt Intelligence paper (based on 15 senior interviews) suggests AI performs strongly in structured qualitative work: rapid comparisons, preference articulation, concept feedback, and consistent guide execution. But it struggles in the kind of work where the value comes from adaptive probing and deeper interpretation.

The McCluskey/Glaut evaluation of 167 AI-moderated sessions makes the same point more sharply. Their finding is uncomfortable but clear: when interviews produced depth, it was often **respondent-driven**, not probe-driven. The AI asked sensible follow-ups, but it did not reliably *lift* the conversation into insight.

This doesn’t mean AI moderation is poor.

It means the current paradigm has structural limits.

---

# What Good Moderation Is Actually Doing

A strong qualitative interview isn’t just a sequence of questions. It’s a process of building explanations in real time.

A skilled moderator listens for:

* what the respondent claims
* what that claim implies
* what is missing for the story to make sense
* where contradictions or tensions sit underneath the surface

They are constantly assembling a working theory of the respondent’s world: not just *what was said*, but **what connects to what**.

A transcript preserves the conversation in sequence.

But it does not explicitly represent the logic that ties statements together — and it doesn’t capture what the respondent *didn’t* say: what they avoided, assumed, glossed over, or treated as obvious.

That “negative space” is often where the real insight lives.

---

# Why Today’s AI Moderators Stay Shallow (Even When They Sound Fluent)

Most AI-moderated interview systems do maintain internal state: summaries, topic coverage trackers, structured memory objects.

But that is mostly **surface memory**: what has been mentioned.

What they usually don’t maintain is **relational memory**:

* which beliefs support each other
* which motivations are driving the behaviour
* which explanations are incomplete
* which parts of the narrative are in tension

Without that relational model, probing becomes procedural: consistent follow-ups, predictable depth prompts, and balanced time allocation across guide topics.

A human moderator doesn’t probe because the next topic is due.

They probe because something in the respondent’s explanation is structurally unfinished — a causal link is missing, a motivation is implied but not stated, or two parts of the story don’t yet fit together.

This is why the McCluskey/Glaut result matters. The limitation wasn’t that AI asked awkward questions.

It’s that the system had no explicit model of what it was trying to *resolve*.

---

# A Different Way to Represent an Interview

There are multiple ways to represent what happens in a qualitative conversation.

A transcript represents an interview as a sequence. This enables linguistic analysis — sentiment, phrasing, tone, repetition — but it treats meaning as something embedded in text.

Thematic coding adds another layer: themes, frequencies, co-occurrence patterns. Useful, but the relationships between themes remain mostly implicit.

A third representation is possible: treating an interview as a network of beliefs and motivations.

In this view:

* concepts become nodes
* relationships become edges
* the interview becomes a structure that can be inspected

This makes visible what human moderators track intuitively:

* causal chains
* contradictions and tensions
* missing links
* explanations assembled across conversational distance

To be clear: a graph is not a “truer” representation of an interview. It is a chosen representation, shaped by modelling decisions (what counts as a node, what counts as causality, what relationship types exist).

That is not a minor detail — it’s the main risk.

But it is also the main advantage: unlike a moderator’s mental model, a graph is explicit. It can be examined, challenged, corrected, and audited.

---

# What Relational Modelling Makes Visible (Simple Example)

Consider a common pattern in interviews: respondents rarely explain their reasoning in a neat ladder.

They reveal parts of the causal story out of order.

A respondent might first say:
*“I usually grab something sugar-free in the afternoon so I don’t crash.”*

Later, when asked about what their afternoons look like, they might add:
*“Honestly it’s the slide-heavy meetings. I just zone out by 3pm.”*

A transcript treats these as two separate remarks.

A relational model can treat them as one explanatory chain assembled across turns:

**slide-heavy meetings → mental fatigue → afternoon crash risk → sugar-free drink choice**

That’s not just a nicer visualisation. It changes what the interviewer can do next.

Because now the system can see what is unresolved:
Is this about blood sugar? boredom? social norms? caffeine? self-control? identity?

A guide-following system moves on.

A relational system has a reason to stay.

---

# Why You Can’t Just Reconstruct This Afterwards

In theory, you can build these networks after the interview.

In practice, post-hoc reconstruction is expensive, interpretive, and limited by what the respondent happened to say unprompted.

The deeper value of qualitative moderation is not in *mapping what was said*. It is in **eliciting what wasn’t said yet**, by noticing gaps while the respondent is still present.

That requires the system to know, in real time:

* what links have already been established
* what is implied but unsupported
* what contradictions exist
* what causal chain is incomplete

Without that live structure, the interview optimises for coverage rather than explanation. It becomes “clean execution” instead of sensemaking.

Real-time relational modelling changes the incentive structure of the interview.

Instead of distributing time evenly across topics, the system can allocate attention to what is structurally informative: gaps, tensions, missing causes, missing motivations.

At that point, the interview starts to behave less like script execution and more like iterative hypothesis testing — which is much closer to what strong qualitative work already does.

---

# The Trade-Off: Better Depth, Different Risks

This approach doesn’t eliminate error. It changes the type of error you need to manage.

Current AI moderation tends to produce **safe incompleteness**: coherent conversations that stay shallow.

Relational modelling risks producing **false coherence**: systems may confidently connect ideas that the respondent never actually connected, or impose causality where the respondent is speculating, rationalising, or speaking metaphorically.

So the governance problem changes.

The key question becomes less *“did we ask the right questions?”*
and more *“is this structure actually supported by evidence?”*

That means edge-level auditing, confidence scoring, and transparency about what was inferred versus what was directly stated.

Even with a perfect graph, interpretation still remains a human task. The structure may be accurate, but its meaning is not automatic. Cultural codes, identity performance, and context-dependent subtext are not solved by better representation.

The graph can map reasoning structure.

It cannot replace interpretation.

---

# The Real Limit Isn’t AI. It’s the Model of the Interview.

The current industry consensus is sensible: AI delivers consistency and scale, but struggles with nuance and still requires human oversight.

But the limiting factor may not be AI capability itself.

It may be that most systems still treat interviews as text streams rather than evolving explanatory models.

A relational model is not just a visualisation layer. It is a form of structural memory: an explicit representation of what has been established, what remains unresolved, and what the most informative next probe might be.

If that framing is right, then the researcher’s role doesn’t disappear.

It shifts:

* less time scripting discussion guides
* more time defining modelling objectives and constraints
* more time auditing whether the structure is warranted
* more time interpreting meaning that no representation can fully capture

Which, in practice, is closer to what the best qualitative research has always been doing.

---

# Appendix: What Graph-Based Moderation Looks Like in Practice

This appendix shows what “relational modelling” means operationally.
The core idea is simple: instead of treating an interview as a text stream, the system treats it as a **growing network of concepts**. Each new respondent statement either adds a new concept, strengthens an existing one, or adds a relationship between concepts. Over time, the interview becomes a structured model of the respondent’s reasoning.

---

## A Qualitative Method as a Structural Model

One way to operationalise qualitative methods is to treat them as **structural completeness rules**: definitions of what kinds of relationships a “good interview” should uncover.

A discussion guide is a sequence of questions.
A structural model is different: it specifies what the interview should produce, regardless of the order in which it emerges.

This matters because in real conversations, respondents do not explain themselves linearly. They reveal causes, motivations, and constraints out of order. A structural model allows the system to keep partial explanations open until missing links are found.

In Jobs-to-be-Done (JTBD), a complete explanation usually contains multiple layers:

* **context** (when and where the situation happens)
* **trigger** (what initiates the need)
* **pain/gain** (what feels problematic or desirable)
* **functional job** (what they are trying to accomplish)
* **emotional/social motivation** (why it matters)
* **solution** (what they currently “hire”)

In the implementation used for this case study, these are represented as five levels:

**L0 — Context / Trigger**
**L1 — Pain / Gain**
**L2 — Functional Job Statement**
**L3 — Emotional / Social Job**
**L4 — Solution Approach**

The goal of moderation is not to “fill every box”. It is to build enough structure that the respondent’s behaviour becomes explainable.

---

## Relationship Types (Edges)

The model uses a small set of relationship types to represent how concepts connect.

Some edges represent the main JTBD chain:

* **triggers**: a context or trigger initiates a need
* **implies**: a pain/gain reveals what the job is
* **supports**: a functional job is reinforced by emotional/social drivers
* **drives**: motivations shape the solution that gets hired

Other edges represent secondary structure:

* **addresses**: a solution resolves a pain point
* **achieves**: a solution delivers a gain point
* **conflicts_with**: one factor undermines another
* **revises**: a newer belief replaces an older one

This distinction matters because the interview can contain many valid associations, but only some form the backbone of an explanatory chain.

---

## Why This Changes the Interview Process

In a guide-based interview, the system tries to ensure “coverage”.
In a graph-based interview, the system tries to ensure “resolution”.

At any moment, the system can ask:

* What part of the chain is missing?
* Which nodes are disconnected?
* Which explanations are implied but unsupported?
* Which motivations have been named but not grounded in behaviour?
* Which behaviours have been described but not explained?

The interview becomes less about moving forward and more about closing gaps in an evolving explanatory structure.

---

# Appendix: Example Chains from the Simulated Interview

The chains below are drawn from a simulated 15-turn JTBD interview with a synthetic persona (beverage decision context). The system dynamically selects follow-up questions based on which parts of the evolving graph remain incomplete.

The important point is not that the chains are “correct”.

It is that they become **inspectable**: the structure can be checked against transcript evidence, rather than living only in the moderator’s head.

---

## Chain 5 — Cross-Turn Assembly

A common phenomenon in interviews is that respondents reveal causes and consequences out of order.

Early in the interview, the respondent describes avoiding an afternoon “rollercoaster crash” by choosing a sugar-free drink (turn 1). Later, a grounding probe surfaces a seemingly separate remark: slide-heavy presentations cause mental fatigue and “checking out” by afternoon (turn 3).

A transcript reader would likely treat these as unrelated.

A relational model links them into a single causal chain assembled across turns:

**Path**

* slide-heavy presentations *(context, turn 3)*
  → mental fatigue *(pain point, turn 3)*
  → struggling to stay present in afternoon meetings *(job statement, turn 1)*
  → choosing a sugar-free drink *(solution, turn 1)*

**Evidence excerpts**

* “Usually I’m just sitting there listening to someone talk through slides…” *(turn 3)*
* “My brain’s kind of checked out by that point…” *(turn 3)*
* “I can actually get through afternoon meetings without feeling like I need a nap…” *(turn 1)*

The key point is structural: the respondent did not state the chain in one answer. The antecedent appeared later than the consequence. The model kept the partial explanation open until the missing link arrived.

This is the kind of sensemaking humans do naturally, but sequential transcripts obscure.

---

## Chain 17 — Reverse Temporal Order

Respondents often describe a behaviour first, and only later supply the context that explains it.

In this case, the respondent describes grabbing a drink before meetings and feeling annoyed when they miss the chance (turn 8). Only afterwards do they explain that thirst becomes distracting (turn 9), and that some meetings are high-stakes (turn 10).

The model reconstructs the logic backwards:

**Path**

* high-stakes meeting *(context, turn 10)*
  → thirst becomes distracting *(pain point, turn 9)*
  → annoyance at missing the opportunity *(emotional job, turn 8)*
  → grabbing a drink before meetings *(solution, turn 8)*

**Evidence excerpts**

* “If it’s something I actually need to focus on, it’s pretty distracting…” *(turn 10)*
* “It’s easier to focus instead of being distracted by being thirsty…” *(turn 9)*
* “By then I’m already annoyed I didn’t grab something at the start.” *(turn 8)*

This is another example of structure emerging across distance. The explanatory foundation arrives after the behaviour has already been stated.

A transcript can preserve the order. A relational model can preserve the logic.

---

## Chain 1 — Social Normalisation (Single-Turn, Hidden Driver)

In turn 13, a grounding probe about why the break room becomes the fallback drink source surfaces a motivation that a standard beverage guide would rarely reach:

**Path**

* walking past the break room *(context, turn 13)*
  → avoiding the effort of backtracking *(pain point, turn 13)*
  → avoiding the feeling of taking a solitary break *(emotional job, turn 13)*
  → other people being present makes it feel socially normal *(social job, turn 13)*
  → break room becomes fallback drink source *(solution, turn 13)*

**Evidence excerpt**

* “Plus there’s usually other people in there so it doesn’t feel like I’m taking a break alone.” *(turn 13)*

This is structurally important because it is not a “nice detail”. It is a hidden driver: without it, the break-room choice looks like pure convenience. With it, the choice becomes partly about social framing and identity.

That kind of insight is often visible in transcripts only in hindsight. The advantage of a relational model is that it makes it explicit while the respondent is still present.

---

# Appendix: What This Demonstrates

These examples illustrate the core mechanism behind graph-based moderation:

* explanations are often distributed across turns
* causes and motivations appear out of order
* the valuable work is connecting fragments into coherent structure
* once structure is explicit, the system can probe what is missing

This does not eliminate interpretation. It makes the underlying reasoning model visible, inspectable, and contestable — which is exactly what standard transcripts and thematic codes do not provide.

---

