# Intro
"The formulas are there, but the spark isn't. The problem is that humans break structure in ways that feel alive. AI does not. At least not yet." - Daniel Berkal, SVP, The Palmerston Group, quoted in Nexxt Intelligence (2026)

Berkal is right about the diagnosis.
But "spark" is not quite the right explanation <i do not like this phrase>

# The State of AI Moderation
Two recent papers from leading AI moderation agencies have done the field a service by being honest about what current AI-moderated interviews do and don't deliver.

The Nexxt Intelligence paper, drawing on 15 interviews with senior industry leaders, identifies a consistent pattern in AI-moderated qual: Berkal estimates that roughly 70% of standard qual projects sit in a zone where AI performs adequately - simple comparison, preference, rapid reasoning. The other 30%, the "deeper, messier human work," still requires a person. The paper surfaces this ceiling clearly but doesn't fully explain what causes it, or what would need to change architecturally for AI to reach it.

The McCluskey/Glaut evaluation of 167 interview sessions across three respondent cohorts reaches a quieter but more uncomfortable conclusion: depth is participant-driven, not probe-driven. The AI's probing "maintained consistency but did not reliably unlock or elevate responses." When rich data appeared in AI-moderated interviews, it came from articulate respondents who brought it with them - not from an AI that drew it out.

These are honest findings from serious practitioners. But they also suggest the industry has reached a ceiling - not a permanent one, but a ceiling specific to the current architectural paradigm.


# What Qual Research Is Actually Doing
Before diagnosing the problem, it's worth being precise about what qualitative research is actually doing - because in practice the industry often operationalises it as something thinner than its own best traditions support.

Qual covers a wide range of epistemological traditions: phenomenological, narrative, interpretive, identity-focused. But across most of them, a common cognitive act sits at the centre of the moderator's work: building an explanatory model of why someone does or believes what they do. Not just cataloguing what they say, but assembling a structure that accounts for how their beliefs connect, what supports what, what leads to what, and what sits in tension.

There is another dimension to this: the moderator is also reading negative space. What the respondent avoids. What goes unsaid. What is presupposed as so obvious it doesn't need stating. The hesitation before a sensitive node. The topic that gets approached and then redirected. The framing conspicuously absent when every other respondent uses it. Susan Fader, one of the practitioners quoted in the Nexxt paper, calls this "contextual intelligence" - the automatic behaviours and taken-for-granted assumptions that respondents haven't consciously articulated, and often can't. A skilled moderator develops a feel for the shape of what isn't being said, and that negative space can be more diagnostic than what the respondent volunteers.

The transcript is evidence of what was said. It is not the structure. And it contains no record of what wasn't.

This distinction matters more than it might seem. A belief can be extracted from a single answer. A structure has to be inferred from a pattern across the whole conversation - assembled, tested, revised, and eventually stabilised into something that explains not just the surface of what was said but the reasoning architecture underneath it. The great qualitative moderator is doing something closer to explanatory model-building than question-asking, while simultaneously tracking what is conspicuously absent from that model. The guide is her field notes, not her methodology.


# Why Current AIMIs Can't Do This
The guide is a coverage instrument, not a map.

An experienced moderator uses the guide to orient herself, but she is simultaneously tracking something else: the emerging shape of the respondent's reasoning. Moderator probes into gaps in that shape and follows a thread because it is structurally important, not because it is next on the list.

Current AI moderation systems maintain some internal state - topic coverage, response summaries, memory objects. But this is surface-level state: what has been mentioned. What they don't maintain is relational state: which beliefs are in tension, which causal chains remain incomplete, which nodes are isolated and therefore under-explored. Without relational state, the AI cannot see structural gaps. So probing defaults to coverage completion: follow-ups that sound relevant but are structurally blind.

This is why the Glaut evaluation's finding cuts so deep. AI probing "did not reliably unlock or elevate responses" not because the questions were poorly phrased, but because the probing had no model of what structure it was trying to complete. Put plainly: today's AI moderation systems fail not because they can't generate good questions, but because they lack an explicit model of what the interview is trying to structurally resolve.

This is what Berkal is describing when he says "the formulas are there, but the spark isn't." The missing spark is not mystical intuition. It's the moderator's implicit structural model - the map she carries of what has been established, what is implied, where tension sits, and where the gaps are. That map tells her when a tangent is worth following and when it isn't. Without it, the only safe option is to constrain the AI's freedom - which is exactly what the industry has done. The guardrail substitutes for judgment. But the judgment gap isn't intrinsic. It is a consequence of representing the conversation as a flat transcript rather than a relational structure.


# Data, Representation, and What Becomes Thinkable
The choice of representation isn't a formatting decision. It's an epistemological one: it determines what analyses become possible.

A qualitative transcript, represented as sequential text, enables linguistic analysis - sentiment, keyword frequency, discourse patterns. Useful, and limited to the surface of language.

Thematic codes add a layer: theme frequencies, co-occurrence, comparison across respondents. More useful. Still flat - the structure between themes remains implicit.

A knowledge graph - nodes representing concepts, beliefs, emotions, and behaviours, with typed edges representing relationships - enables something categorically different. You can trace causal paths, detect structural gaps, compare the shape of one respondent's mental model against another's, identify load-bearing beliefs, and run similarity metrics across interviews without relying on shared vocabulary.

Minimize image
Edit image
Delete image

Figure 1
But this needs a qualification: a graph is not a more accurate representation of a conversation. It is a different one. Someone must decide what counts as a node, what relationship types are valid, what directionality means. That is not a minor implementation detail — it is the primary epistemic risk.

The argument for graphs is not that they are "truer." It is that they are inspectable. A human moderator's mental model is implicit - invisible to the client, the analyst, and often the moderator herself. A graph externalises that model. It can be audited, challenged, corrected. The bias remains; it is simply no longer hidden.


# What a Conversation Looks Like as a Graph
The following is drawn from a simulated interview - a consumer discussing a sugar-free carbonated drink (ZeroFizz) in a jobs-to-be-done context. Twelve turns, roughly the length of a standard AI-moderated session.

Example 1: resolving a contradiction in real time

In turns 1 and 2, the respondent establishes fizz as valuable: "the fizz kind of wakes you up", "it's more of a pick-me-up." The graph registers gain nodes tied to carbonation.

In turn 3, the respondent reverses: "Honestly I don't think the fizz itself does much for me."

This is a structural conflict. A guide-executing system would move on - fizz had been "covered." A graph-aware system holds both claims and probes the contradiction: "What would actually change if it had no fizz at all?" The respondent resolves it: "The fizz is like half the point - it's refreshing, gives you that little kick."

What emerges is not a simple answer but a useful distinction: fizz matters as sensory ritual, not functional alertness. That only becomes visible because the system held the tension open long enough to resolve it.

Example 2: structure that only becomes visible late

The interview begins with a practical trigger: afternoon energy slump, coffee fatigue, grabbing whatever is in the fridge. Standard JTBD territory.

By turn 9, something deeper surfaces: "I'm getting older and I figure I should probably care about that stuff before it becomes an actual problem."

And then: "There's kind of a... small sense of not completely sabotaging myself. It's more about not feeling guilty after I drink it."

Across these turns, the graph connects a chain: physical discomfort from sugar → protect long-term health → take care of future self → avoid self-sabotage → feel like I'm making a better choice effortlessly

These examples are simulated to make specific structural events legible - contradiction, late chain emergence, gap detection. Real interviews are messier. But the events themselves are routine in real qualitative data.

Minimize image
Edit image
Delete image

Fig. 1: Conversation graph illustration. Check GitHub for the page
A sceptic might ask: why not build the graph afterward from the transcript? Because real-time construction changes what the interview can do. Contradictions can be resolved while the respondent is still present. Competing interpretations can be tested immediately. Time can be allocated toward structurally important nodes rather than distributed uniformly across guide topics.

Mechanically: each turn is parsed for candidate nodes and relationships; candidates are scored against the existing graph; every edge is anchored to transcript spans; low-confidence edges and contradictions are flagged for follow-up. The graph is not a record. It is a running hypothesis that the conversation progressively tests.


# The New Failure Modes
It is worth being direct about what this architecture gets wrong, because it gets things wrong differently from current tools.

Current AI moderation fails by being shallow. The error is omission: missing structure, missing depth, missing the reasoning beneath the surface answer.

A graph-based system fails by being confidently wrong. It may invent edges the transcript doesn't support, or impose causal structure on what is actually analogy, habit, or social performance. A respondent saying "it makes me feel healthy" might be reporting a belief, rationalising a behaviour, or performing the expected answer. The graph can collapse these unless the system is sophisticated enough to distinguish them - and it often won't be.

This shifts governance. Today, researchers govern the input: write the guide, set boundaries, keep the AI on track. In a graph-aware system, the guide becomes a schema, and governance shifts toward auditing output integrity: checking whether edges are supported, where claims are overconfident, and where hallucinated structure has entered at scale.

One further risk is obvious: if depth is measured by chain length and connection density, the system will optimise graph fullness rather than accuracy. Completeness metrics must remain heuristics, not objectives.

It also helps to be precise about what graphs can and cannot represent. Three classes of "not said" matter here:

Structural absence - implied but unreached nodes, incomplete chains - is what graphs make inspectable.

Interactional absence - hesitation, avoidance, tonal shift - remains mostly inaccessible to text systems and only partially accessible even in voice.

Presuppositional absence - what is treated as self-evident - cannot be reliably inferred without explicit probing.

Even where the graph is accurate, it does not tell you what the structure signifies. Cultural code, identity performance, social scripts - the interpretive layer is where the most valuable insight often lives. The graph maps reasoning architecture; it does not interpret meaning.

Reading negative space and interpreting significance is where the researcher remains not merely a governor but an irreplaceable analyst. Those skills do not yet have structural equivalents.


# Qualitative Methods as Graph Schemas
The deeper implication is that qualitative methodologies can be reframed as graph constraints: specifications of which structures a complete interview should produce.

Means-End Chain specifies a hierarchical ladder: attributes → functional consequences → psychosocial consequences → terminal values. Probing means climbing upward. Coverage is measured by whether value nodes have been reached.

Jobs-to-Be-Done specifies a two-layer structure: the job chain (trigger → job → outcome → solution) and the forces field (push, pull, anxiety, habit). A complete JTBD graph requires both layers, because the job alone doesn't explain switching.

Concept testing maps a stimulus onto an existing belief graph. Gaps reveal what the concept leaves unexplained. Conflicts reveal dissonance between claims and prior structure.

Each methodology becomes, in this framing, a grammar: a definition of what structural completeness looks like.


# A Different Kind of Ceiling
The industry's current consensus is reasonable: AI is good for scale, speed, and consistency; it struggles with depth, nuance, and adaptive probing; human governance is the solution. Keep the AI on a tight guide, interpret outputs carefully, don't expect the AI to do the meaning-making.

The argument here is not that this consensus is wrong. It is that the ceiling it describes is architectural rather than fundamental -— specific to systems that represent the conversation as flat transcript rather than relational structure.

The graph is not a visualisation feature. It is structural memory: an explicit, queryable representation of what has been established, what remains open, what is implied, and what the most structurally informative next probe would be. It is what makes the difference between an AI that executes a guide and an AI that navigates a reasoning space.

In that shift, the researcher's role changes - not diminishes: moving from scripting questions to defining structural objectives, reviewing graph outputs, auditing integrity, and interpreting meaning the graph cannot. It is also, I would argue, closer to what the best qualitative work has always aimed to do.


Sources:

https://www.nexxt.in/perspectives/reclaiming-conversation-in-the-age-of-ai