# Beyond the Guide: How Graph Representation Changes What AI Moderation Can Do

"The formulas are there, but the spark isn't. The problem is that humans break structure in ways that feel alive. AI does not. At least not yet." — Daniel Berkal, SVP, The Palmerston Group (quoted in Nexxt Intelligence, 2026)

Berkal’s diagnosis is right. But “spark” is the wrong word for what human moderators actually contribute.

What experienced moderators bring is not charisma. It’s live sensemaking: a running model of what the respondent believes, what motivates them, what doesn’t quite add up yet, and what still needs explaining.

Most AI moderation systems don’t operate with that kind of model. They operate closer to topic tracking.

And that difference matters.

# What the Recent Evaluations Actually Say

Two recent industry publications offer a consistent picture of where AI-moderated qual performs well and where it still hits a ceiling.

Kathy Cheng (Nexxt Intelligence) conducted 15 interviews with senior leaders across brands, agencies, and research technology providers. Her analysis suggests that AI performs strongly in structured qualitative work: rapid comparisons, preference articulation, concept feedback, and consistent guide execution. But it struggles in the kind of work where the value comes from adaptive probing and deeper interpretation.

Lauren McCluskey's (Glaut) evaluation of 167 AI-moderated sessions makes the same point more sharply. Their finding is uncomfortable but clear: when interviews produced depth, it was often respondent-driven, not probe-driven. The AI asked sensible follow-ups, but it did not reliably lift the conversation into insight.

This doesn’t mean AI moderation is poor. It means the current paradigm has structural limits.

# What Good Moderation Is Actually Doing

A strong qualitative interview isn’t just a sequence of questions. It’s a process of building explanations in real time.

A skilled moderator listens for:
- what the respondent claims
- what that claim implies
- what is missing for the story to make sense
- where contradictions or tensions sit underneath the surface

They are constantly assembling a working theory of the respondent’s world: not just what was said, but what connects to what.

A transcript preserves the conversation in sequence. But it does not explicitly represent the logic that ties statements together and it doesn’t capture what the respondent didn’t say: what they avoided, assumed, or treated as obvious.

That “negative space” is often where the real insight lives.

# Why Today’s AI Moderators Stay Shallow (Even When They Sound Fluent)

Most AI-moderated interview systems do maintain internal state: summaries, topic coverage trackers, structured memory objects.

But that is mostly surface memory: what has been mentioned.

What they usually don’t maintain is relational memory:
- which beliefs support each other
- which motivations are driving the behaviour
- which explanations are incomplete
- which parts of the narrative are in tension

Without that relational model, probing becomes procedural: consistent follow-ups, predictable depth prompts, and balanced time allocation across guide topics.

A human moderator doesn’t probe because the next topic is due. They probe because something in the respondent’s explanation is structurally unfinished - a causal link is missing, a motivation is implied but not stated, or two parts of the story don’t yet fit together.

This is why the McCluskey/Glaut result matters. The limitation wasn’t that AI asked awkward questions. It’s that the system had no explicit model of what it was trying to resolve.

# A Different Way to Represent an Interview

There are multiple ways to represent the content of a qualitative conversation.

- A transcript represents an interview as a sequence. This enables linguistic analysis, e.g. sentiment, phrasing, tone, repetition, but it treats meaning as something embedded in text.
- Thematic coding adds another layer: themes, frequencies, co-occurrence patterns. Useful, but the relationships between themes remain mostly implicit.
- A third representation is possible: treating an interview as a network of beliefs and motivations.

In such network:
- concepts become nodes
- relationships become edges
- the interview becomes a structure that can be inspected

This makes visible what human moderators track intuitively:
- causal chains
- contradictions and tensions
- missing links
- explanations assembled across conversational distance

But graph is not a “truer” representation of an interview. It is a chosen representation, shaped by modelling decisions: what counts as a node, what counts as causality, what relationship types exist. Getting these details wrong is the main risk.

The main advantage: unlike a moderator’s mental model, a graph is explicit. It can be examined, challenged, corrected, and audited.

# What Relational Modelling Makes Visible

Consider a common pattern in interviews: respondents rarely explain their reasoning in a neat ladder. They reveal parts of the causal story out of order.

A respondent might first say: “I usually grab something sugar-free in the afternoon so I don’t crash.”
Later, when asked about what their afternoons look like, they might add: “Honestly it’s the slide-heavy meetings. I just zone out by 3pm.”

A transcript treats these as two separate remarks. A relational model can treat them as one explanatory chain assembled across turns:

slide-heavy meetings → mental fatigue → afternoon crash risk → sugar-free drink choice

That’s not just a nicer visualisation. It changes what the interviewer can do next. Because now the system can see what is unresolved: Is this about blood sugar? boredom? social norms? caffeine? self-control? identity?

A guide-following system moves on, but a relational system has a reason to stay.

# Why You Can’t Just Reconstruct This Afterwards

In theory, you can build these networks after the interview. In practice, post-hoc reconstruction is expensive, interpretive, and limited by what the respondent happened to say unprompted.

The deeper value of qualitative moderation is not in mapping what was said. It is in eliciting what wasn’t said yet, by noticing gaps while the respondent is still present. That requires the system to know, in real time:
- what links have already been established
- what is implied but unsupported
- what contradictions exist
- what causal chain is incomplete

Without that live structure, the interview optimises for coverage rather than explanation. It becomes “clean execution” instead of sensemaking. 

Real-time relational modelling changes the incentive structure of the interview. Instead of distributing time evenly across topics, the system can allocate attention to what is structurally informative: gaps, tensions, missing causes, missing motivations.

At that point, the interview starts to behave less like script execution and more like iterative hypothesis testing, which is much closer to what strong qualitative work already does.

# The Trade-Off: Better Depth, Different Risks

This approach doesn’t eliminate error. It changes the type of error you need to manage.

Current AI moderation tends to produce safe incompleteness: coherent conversations that stay shallow.
Relational modelling risks producing false coherence: systems may confidently connect ideas that the respondent never actually connected, or impose causality where the respondent is speculating, rationalising, or speaking metaphorically.

So the governance problem changes. The key question becomes less “did we ask the right questions?” and more “is this structure actually supported by evidence?”

That means edge-level auditing, confidence scoring, and transparency about what was inferred versus what was directly stated.

But it doesn’t eliminate the most human part of qualitative work: reading the negative space of an interview. Hesitations, missing links, unspoken constraints, and “obvious” presuppositions often carry more meaning than explicit answers. A graph can make some of these absences inspectable, for example by highlighting incomplete causal chains. But it cannot interpret what the absence signifies.

The structure may be accurate, but its meaning is not automatic. Cultural codes, identity performance, and context-dependent subtext are not solved by better representation.

The graph can map reasoning structure, but it cannot replace interpretation.

# Graphs Don’t Solve Qual. But They Change What’s Possible.

The current industry consensus is sensible: AI delivers consistency and scale, but struggles with nuance and still requires human oversight. But the limiting factor may not be AI capability itself. It may be that most systems still treat interviews as text streams rather than evolving explanatory models.

A relational model isn’t just a visualisation layer. It’s a form of structural memory: an explicit representation of what has been established and what remains unresolved.

If that framing is right, then the researcher’s role doesn’t disappear, but shifts:
- less time scripting discussion guides
- more time defining modelling objectives and constraints
- more time auditing whether the structure is warranted
- more time interpreting meaning that no representation can fully capture

Which, in practice, is closer to what the best qualitative research has always been doing.

# Sources:

Cheng, K. (2026, March 25). Reclaiming conversation in the age of AI. Nexxt Intelligence. https://www.nexxt.in/perspectives/reclaiming-conversation-in-the-age-of-ai

McCluskey, L. (2026, April). AI-moderated qualitative research: An empirical evaluation [White paper]. Glaut Inc. https://www.glaut.com/glaut-research/does-sample-source-matter-in-ai-moderated-research

# Appendix

## What Graph-Based Moderation Looks Like in Practice

This appendix shows what “relational modelling” means operationally. The core idea is simple: instead of treating an interview as a text stream, the system treats it as a growing network of concepts. Each new respondent statement either adds a new concept, strengthens an existing one, or adds a relationship between concepts. Over time, the interview becomes a structured model of the respondent’s reasoning.

## Qualitative Method as a Structural Model
One way to operationalise qualitative methods is to treat them as structural completeness rules: definitions of what kinds of relationships a “good interview” should uncover.

A discussion guide is a sequence of questions. A structural model is different: it specifies what the interview should produce, regardless of the order in which it emerges.

This matters because in real conversations, respondents do not explain themselves linearly. They reveal causes, motivations, and constraints out of order. A structural model allows the system to keep partial explanations open until missing links are found.

For example, in Jobs-to-be-Done (JTBD), a complete explanation usually contains multiple layers:
- context (when and where the situation happens)
- trigger (what initiates the need)
- pain/gain (what feels problematic or desirable)
- functional job (what they are trying to accomplish)
- emotional/social motivation (why it matters)
- solution (what they currently “hire”)

In the implementation used for this case study, these layers are represented as five levels with a set of predefined relationship types.

[image](reports/artefacts/may-2026/jtbd_ontology_illustration.html)

The goal of moderation is not to “fill every box”. It is to build enough structure that the respondent’s behaviour becomes explainable.

## Why This Changes the Interview Process
In a guide-based interview, the system tries to ensure “coverage” of the topics listed in the guide.

In a graph-based interview, the system tries to ensure “resolution”. At any moment, the interview engine is "aware" of the conversation context:
- What part of the chain is missing?
- Which nodes are disconnected?
- Which explanations are implied but unsupported?
- Which motivations have been named but not grounded in behaviour?
- Which behaviours have been described but not explained?

The interview becomes less about moving forward and more about closing gaps in an evolving explanatory structure.

## Simulated Interview
The transcript below is a simulated 15-turn interview with a synthetic persona and an imaginary product (‘ZeroFizz’). The interview engine dynamically extracts the nodes and edges according to the methodology schema (JTBD) and generates the next question based on range of parameters (e.g. graph topology, response valence, interview phase, etc.).

[image](reports/artefacts/may-2026/transcript_illustration.html)

## Causal chains
The analytical layer uses the conversation graph built during the interview to extract causal chains.  

The important point is not that the chains are “correct”. It is that they become inspectable: the structure can be checked against transcript evidence, rather than living only in the moderator’s head.

### Example #1

A common phenomenon in interviews is that respondents reveal causes and consequences out of order.

Early in the interview, the respondent describes avoiding an afternoon “rollercoaster crash” by choosing a sugar-free drink (turn 1). Later, a grounding probe surfaces a seemingly separate remark: slide-heavy presentations cause mental fatigue and “checking out” by afternoon (turn 3). A transcript reader would likely treat these as unrelated. A relational model links them into a single causal chain assembled across turns:

[image](reports/artefacts/may-2026/chain_05_illustration.html)

The key point is structural: the respondent did not state the chain in one answer. The antecedent appeared later than the consequence. The model kept the partial explanation open until the missing link arrived.

### Example #2

Respondents often describe a behaviour first, and only later supply the context that explains it.

In this case, the respondent describes grabbing a drink before meetings and feeling annoyed when they miss the chance (turn 8). Only afterwards do they explain that thirst becomes distracting (turn 9), and that some meetings are high-stakes (turn 10). The model reconstructs the logic backwards:

[image](reports/artefacts/may-2026/chain_17_illustration.html)

This is another example of structure emerging across conversation turns. The explanatory foundation arrives after the behaviour has already been stated.

A transcript can preserve the order. A relational model can preserve the logic.

## What This Demonstrates

These examples illustrate the core mechanism behind graph-based moderation system:
- explanations are often distributed across turns
- causes and motivations appear out of order
- the valuable work is connecting fragments into coherent structure
- once structure is explicit, the system can probe what is missing

This is the kind of sensemaking humans do naturally, but sequential transcripts might obscure.

Graph modelling does not eliminate interpretation. But it makes the underlying reasoning model visible, inspectable, and contestable, which is exactly what standard transcripts and thematic codes do not provide.