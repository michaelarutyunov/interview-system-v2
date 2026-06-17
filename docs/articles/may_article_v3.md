# AI Moderation Isn't Missing "Spark". It's Missing a Relational Model.

"The formulas are there, but the spark isn't. The problem is that humans break structure in ways that feel alive. AI does not. At least not yet."
— Daniel Berkal, SVP, The Palmerston Group (quoted in Nexxt Intelligence, 2026)

Berkal's diagnosis is spot on. But can AI moderators bring the spark? <not sure about it>

What human moderators bring isn't "spark" in the mystical sense. It's something more concrete: an evolving explanatory model of the respondent's world — a live sense of what connects to what, what doesn't fit yet, and what still needs resolving.
Most AI-moderated interview systems don't operate with that kind of model. They operate with something closer to topic tracking.
And that difference matters.

# What the experts say

Two recent papers by the leading agencies in the field present a candid perspective on the current limits of AI-moderated qualitative research.

The Nexxt Intelligence paper (based on 15 senior industry interviews) reports a consistent pattern: AI performs well in a large share of "standard" qual — comparisons, preference articulation, rapid reasoning, concept feedback. But there remains a stubborn band of work where depth, nuance, and adaptive probing still require a person.

The McCluskey/Glaut evaluation of 167 AI-moderated sessions makes the ceiling even clearer. Its conclusion is uncomfortable but hard to ignore: depth is often participant-driven, not probe-driven. The AI's probing was consistent, but it did not reliably elevate responses. When rich insight appeared, it came from respondents who brought it with them.

This doesn't mean AI moderation is "bad". It means the current paradigm has limits.

To me those limits seem architectural.

# What Qual Moderation Is Actually Doing

Good qualitative moderation isn't just about asking good questions. It's about sensemaking in real time. Not just cataloguing what has been said, but assembling a structure that accounts for how the beliefs connect, what supports what, what leads to what, and what sits in tension.

A skilled moderator is continuously building a working model of the respondent's reasoning:  
what they believe  
what motivates them  
what tensions sit beneath the surface  

A transcript preserves what was said, in sequence.
But it doesn't explicitly represent the explanatory logic that ties statements together.

And it contains no record of what wasn't said: what was avoided, presupposed, glossed over, or treated as too obvious to mention.
That "negative space" is often where the real insight lives.

# Why Today's AI Moderators Struggle (Even When They Sound Fluent)

Most AI-moderated interview systems do maintain some kinf of internal state: summaries, topic coverage, memory objects.
But this is surface-level memory: what has been mentioned.

What they don't maintain is relational memory:  
which beliefs reinforce or contradict each other  
which motivations are doing the heavy lifting  
which explanations feel fragile or inconsistent  

Without relational memory, probing defaults to what the industry often calls "structured feedback": consistent execution of a guide, standardised follow-ups, clean coverage.

But human moderator doesn't probe because the topic is next in the guide. They probe because the they sense an emerging story in respondent's narrative and their questions help bringing this story to surface, carefully, bracketing out own assumptions and letting respondent say it in their own words. <this needs to be improved because of confusing coreference>

TThis is why the McCluskey/Glaut finding matters so much. <i want to avoid word "fail" here> AI probing didn't fail because the questions were awkward. It failed because the system had no explicit model of what it was trying to discover.

# A different angle to look at the conversation

There multiple way to represent the data collected during the interview.

A typical qualitative transcript is a Q&A sequence that enables linguistic analysis — sentiment, keyword frequency, discourse patterns. Useful, and limited to the surface of language.
Thematic codes add a layer: theme frequencies, co-occurrence, comparison across respondents. More useful, but the structure between themes remains implicit.

Looking at a conversation as a belief-and-motivation network — concepts as nodes, relationships as edges — surfaces what moderators implicitly track:
causal chains  
tensions and contradictions  
missing links   

Graph representation enables a different kind of interviewing that goes beyond topic coverage.

But this needs a qualification: a graph is not a more accurate representation of a conversation. It is a different one. Someone must decide what counts as a node, what relationship types are valid, what directionality means. That is not a minor implementation detail — it is the primary epistemic risk <i do not want word epistemic>

The argument for graphs is not that they are "truer." It is that they are inspectable. A human moderator's mental model is implicit — invisible to the client, the analyst, and often the moderator herself. A graph externalises that model. It can be audited, challenged, corrected.

# What a Relational Model Makes Visible

In a simulated 15-turn interview using a Jobs-to-be-Done framework, a relational model surfaced structures that a transcript reader would likely miss. (Full transcript and chain illustrations are available in the Appendix.)

Early in the interview, the respondent mentions avoiding the afternoon "rollercoaster" crash by drinking something sugar-free. Two turns later, a ground probe about what happens right before the energy dip surfaces something that initially looks like a separate topic: sitting passively through slide-based presentations causes mental fatigue and "checking out" by afternoon. The graph links these into one causal chain:

<picture>
slide-heavy presentations → mental fatigue → struggling to stay present in afternoon meetings → choosing a sugar-free drink to avoid the crash

The respondent didn't deliver this as a neat ladder in one answer. The antecedent appeared in turn 3; the consequence was stated in turn 1. The system held the partial explanation open and connected the pieces when the missing half arrived. A transcript reader would see two separate remarks about different topics. The graph shows they're one structure assembled across conversational distance.

Later in the same interview, the graph assembles a chain in reverse temporal order. The respondent describes grabbing a drink before meetings and feeling annoyed when they miss the chance (turn 8). Only afterwards do they explain that thirst becomes distracting (turn 9) and that some meetings are high-stakes (turn 10). The causal logic runs backward: the context revealed last explains the behavior reported first. Sequential transcripts cannot represent this at all. A relational model can.

These aren't edge cases. They illustrate the operational difference between tracking what was mentioned and tracking what remains unresolved. [See Appendix for full chain walkthroughs]

# Why You Can't Just Build This After the Interview

You can reconstruct these networks post-hoc.
The depth of human moderation allows eliciting the networks of meaningful relationships.

But most current AI-moderated systems optimise for consistency, safety, and repeatability — which makes them excellent at coverage. The cost is reduced adaptiveness: fewer opportunities to stay with contradictions, follow emerging threads, and build complete causal explanations across turns. The result is that there is a less chance for a causal connections to emerge, they remain fragmented, because AI's strict adherence to the guide limits its ability to follow through. <improve wording>

Real-time graph modelling can change that.
Contradictions can be resolved while the respondent is still present. Missing links can be probed immediately. Time can be allocated to what is structurally informative, rather than distributed evenly across guide topics.
At that point, the interview stops being "script execution" and starts behaving more like iterative hypothesis testing.
Which is a step closer to what real qualitative research is.


# New Architecture, New Failure Modes <i do not understand what architecture means here, some different title is needed and i am not sure about "failure mode">

This approach doesn't eliminate error. It changes the type of error.
<can it be removed?>

<below - i understand the idea, but "fail by omission/commission" is not really how i speak.. I am not that sophisticated>
Current AI moderation tends to fail by omission: it stays shallow.
Graph-based systems risk failing by commission: confidently inventing links the transcript doesn't support, or imposing causality where the respondent is rationalising, performing, or speaking metaphorically.

<I am not sure this is accurate - graph based systems also govern input - methodology yamls, as well as auditing the outputs. So in some way it is not about shift but change of the nature of governance? not sure.. >
That means governance shifts. Instead of only governing the input (tight guides), researchers increasingly govern the output: auditing whether edges are evidence-based, where confidence is inflated, and where hallucinated coherence creeps in.

In other words: less "did we ask the right questions?". More "is this model actually warranted?"

It also helps to be precise about what graphs can and cannot represent. Three classes of "not said" matter here:

<is this an academically accepted classification?>
**Structural absence** — implied but unreached nodes, incomplete chains — is what graphs make inspectable.

**Interactional absence** — hesitation, avoidance, tonal shift — hardly accessible to text systems and only partially accessible even in voice.

**Presuppositional absence** — what is treated as self-evident — cannot be reliably inferred without explicit probing.

And even where the graph is accurate, it does not tell you what the structure signifies. Cultural code, identity performance, social scripts — the interpretive layer is where the most valuable insight often lives. The graph maps reasoning architecture; it does not interpret meaning.

Reading negative space and interpreting significance is where the researcher remains not merely a governor but an irreplaceable analyst. Those skills do not yet have structural equivalents.

# A Different Ceiling <i do not like the word ceiling - can you propose alternative subtitle?>

The industry consensus is sensible: AI is strong on scale and consistency, weaker on nuance, and needs human oversight.
<But the reason is not in AI as such, but in how the conversation is seen and the type of control researchers are comfortable with>
<mayme remove or replace> But the ceiling we're describing may not be fundamental.
It may be specific to systems that treat interviews as text streams rather than evolving explanatory models.

A graph isn't just a visualisation layer. It's a form of structural memory: an explicit representation of what has been established, what remains unresolved, and what the most informative next probe might be.

If that's right, the researcher's role doesn't shrink. It changes: less scripting, more defining modelling objectives, auditing integrity, and interpreting meaning that no representation can fully capture.

Which, arguably, is closer to what the best qualitative work has always been doing.

---

Sources:

Nexxt Intelligence: Reclaiming Conversation in the Age of AI
https://www.nexxt.in/perspectives/reclaiming-conversation-in-the-age-of-ai

McCluskey/Glaut: AI-Moderated Qualitative Research — An Empirical Evaluation
https://www.glaut.com/glaut-research/does-sample-source-matter-in-ai-moderated-research

---

# Appendix: Examples

## Qualitative Methods as Graph Schemas

The deeper implication is that qualitative methodologies can be reframed as graph constraints: specifications of which structures a complete interview should produce.

Jobs-to-Be-Done specifies a two-layer structure. The first is the job chain: a trigger (contextual cue) initiates a job (functional goal), which drives an outcome (desired state), resolved by a solution (hiring a product). The second is the forces field: push forces (dissatisfaction with current state), pull forces (attraction to new solution), anxiety (barriers to switching), and habit (inertia of existing behavior). A structurally complete JTBD graph requires both layers — the job chain alone explains what someone is trying to accomplish, but the forces explain why they switch or don't.

In the case study above, the slide-fatigue chain traces the job layer: slide-passive listening (trigger) → avoid energy crash (job) → get through afternoon meetings (outcome) → drink ZeroFizz (solution). But the interview also surfaces a force the respondent never stated directly: the anxiety of appearing to take a solitary break, which the presence of others in the break room resolves (see Chain 1 in the Appendix). This force — invisible to topic coverage — is structurally load-bearing: without it, the break-room-as-fallback behavior doesn't fully make sense.

The methodology becomes, in this framing, a grammar: a definition of what structural completeness looks like. The guide is no longer a sequence of questions — it's a schema that the system navigates.

The following chains are drawn from a simulated 15-turn interview with a synthetic persona using the Jobs-to-be-Done framework. The system prioritises the focus of each next question through analysis of an evolving conversation graph. Full transcript available on GitHub.

## Chain 5 — Cross-Turn Assembly

Early in the interview, the respondent talks about avoiding the afternoon "rollercoaster" crash (turn 1). Later, a ground probe surfaces something that initially looks unrelated: sitting through slide-based presentations creates mental fatigue and "checking out" by afternoon (turn 3). A transcript reader would likely treat these as separate remarks. A relational model links them into one coherent explanation across conversational distance:

**Path:**

→ `sitting passively through slide-based presentations` (job_context, L0, t=3)
→ `mental fatigue causing brain to check out by afternoon` (pain_point, L1, t=3)
→ `getting through afternoon meetings without struggling` (job_statement, L2, t=1)
→ `drinking ZeroFizz sugar-free beverage to avoid the rollercoaster effect` (solution_approach, L4, t=1)

**Evidence:**

- slide presentations → mental fatigue: *"Usually I'm just sitting there listening to someone talk through slides or whatever."* [triggers, t=3]
- mental fatigue → struggling through meetings: *"Like, my brain's kind of checked out by that point, especially if it's been back-to-back meetings since morning."* [implies, t=3]
- struggling through meetings → ZeroFizz: *"I can actually get through afternoon meetings without feeling like I need a nap or another caffeine hit to survive them."* [drives, t=1]

The key point: the respondent didn't deliver this as a neat ladder in one answer. The antecedent (slide fatigue) was surfaced in turn 3 via a `ground` probe, but it connects to a consequence the respondent stated in turn 1. The graph assembled the causal chain retroactively — two halves of the same structure, separated by two turns and two strategy selections. That's exactly the kind of sensemaking humans do automatically, and that sequential representations obscure.

*Interactive illustration: [Chain 5 — Causal Chain Diagram](https://github.com/michaelarutyunov/interview-system-v2/blob/master/docs/artefacts/chain_05_illustration.html)*

## Chain 17 — Reverse Temporal Order

Later in the interview, the respondent describes grabbing a drink before meetings and feeling annoyed when they miss the chance (turn 8). Only afterwards do they explain that thirst becomes distracting (turn 9), and that some meetings are high-stakes (turn 10). The graph reconstructs the causal logic backwards:

**Path:**

→ `high-stakes meetings requiring focused attention` (job_context, L0, t=10)
→ `thirst distracting from focus during meetings` (pain_point, L1, t=8)
→ `feeling annoyed at missing the opportunity to grab a drink` (emotional_job, L3, t=8)
→ `grabbing a drink before meetings start to stay ahead of thirst` (solution_approach, L4, t=8)

**Evidence:**

- high-stakes meetings → thirst distraction: *"if it's something I actually need to focus on, it's pretty distracting"* [triggers, t=10]
- thirst distraction → annoyance: *"if I've got a drink it's easier to focus instead of being distracted by being thirsty or whatever."* [implies, t=8]
- annoyance → pre-meeting drink grab: *"By then I'm already annoyed I didn't grab something at the start."* [drives, t=8]

Three different turns, all high-confidence, all respondent-attributed. The causal structure runs from t=10 context backward through t=8. Humans frequently explain causes after behaviours — sequential transcripts don't represent this well. Relational models do.

## Chain 1 — Social Normalisation (Single-Turn with Surprising Depth)

In turn 13, a ground probe about why the break room becomes the fallback drink source surfaces a motivational layer no standard beverage research guide would reach:

**Path:**

→ `walking past the break room making a drink grab effortless` (job_context, L0, t=13)
→ `avoiding the effort of backtracking to desk while thirsty` (pain_point, L1, t=13)
→ `avoid feeling like taking a solitary break` (emotional_job, L3, t=13)
→ `other people being in the break room making the stop feel socially normal` (social_job, L3, t=13)
→ `break room being the fallback source when drinks aren't near the meeting room` (solution_approach, L4, t=13)

**Evidence:**

- break room proximity → avoid backtracking: *"If I'm already walking past it, might as well grab something instead of going back to my desk thirsty."* [triggers, t=13]
- avoid backtracking → avoid solitary break: *"might as well grab something instead of going back to my desk thirsty"* [implies, t=13]
- avoid solitary break → social normalisation: *"so it doesn't feel like I'm taking a break alone"* [supports, t=13]
- social normalisation → break room as fallback: *"Plus there's usually other people in there so it doesn't feel like I'm taking a break alone."* [supports, t=13]

A standard beverage research guide would ask about taste, caffeine, sugar content, convenience. It would not surface "avoid feeling like taking a break alone" as a driver of drink location choice. The respondent's casual aside — *"Plus there's usually other people in there so it doesn't feel like I'm taking a break alone"* — is what the graph captures and a topic checklist would skip. This demonstrates the article's core claim: the graph makes inspectable what a transcript hides in plain sight.
