# AI Moderation Isn’t Missing “Spark”. It’s Missing a Relational Model.

"The formulas are there, but the spark isn't. The problem is that humans break structure in ways that feel alive. AI does not. At least not yet."
— Daniel Berkal, SVP, The Palmerston Group (quoted in Nexxt Intelligence, 2026)

Berkal is right about the diagnosis. But I’d frame the gap differently.

What human moderators bring isn’t “spark” in the mystical sense. It’s something more concrete: an evolving explanatory model of the respondent’s world — a live sense of what connects to what, what doesn’t fit yet, and what still needs resolving.
Most AI-moderated interview systems don’t operate with that kind of model. They operate with something closer to topic tracking.
And that difference matters.

# The Ceiling Is Real (and the Field Is Now Acknowledging It)

Two recent papers have been candid about the current limits of AI-moderated qualitative research.

The Nexxt Intelligence paper (based on 15 senior industry interviews) reports a consistent pattern: AI performs well in a large share of “standard” qual — comparisons, preference articulation, rapid reasoning, concept feedback. But there remains a stubborn band of work where depth, nuance, and adaptive probing still require a person.

The McCluskey/Glaut evaluation of 167 AI-moderated sessions makes the ceiling even clearer. Its conclusion is uncomfortable but hard to ignore: depth is often participant-driven, not probe-driven. The AI’s probing was consistent, but it did not reliably elevate responses. When rich insight appeared, it came from respondents who brought it with them.

This doesn’t mean AI moderation is “bad”. It means the current paradigm has limits.

To me those limits seem architectural.

# What Qual Moderation Is Actually Doing

Good qualitative moderation isn’t just about asking good questions. It’s about sensemaking in real time. Not just cataloguing what they say, but assembling a structure that accounts for how their beliefs connect, what supports what, what leads to what, and what sits in tension.

A skilled moderator is continuously building a working model of the respondent’s reasoning:
what they believe
what motivates them
what assumptions they take for granted
what tensions sit beneath the surface
what causal links are implied but not yet stated

This is why transcripts are deceptive. A transcript preserves what was said, in sequence.
But it doesn’t explicitly represent the explanatory logic that ties statements together.

And it contains no record of what wasn’t said: what was avoided, presupposed, glossed over, or treated as too obvious to mention.
That “negative space” is often where the real insight lives.

# Why Today’s AI Moderators Struggle (Even When They Sound Fluent)

Most AI-moderated interview systems do maintain internal state: summaries, topic coverage, memory objects.
But this is surface-level memory: what has been mentioned.

What they don’t maintain is relational memory:
which beliefs reinforce or contradict each other
which causal chains remain incomplete
which motivations are doing the heavy lifting
which explanations feel fragile or inconsistent

Without relational memory, probing defaults to what the industry often calls “structured feedback”: consistent questioning, standardised follow-ups, clean coverage.
And this is exactly where the word “structured” becomes misleading.

The term “structured” often refers to a consistent execution of a guide.
But in qualitative research, the valuable kind of structure is almost the opposite: adaptive coherence-building.

A good moderator doesn’t probe because the topic is next.
They probe because the respondent’s model doesn’t yet hang together.

This is why the McCluskey/Glaut finding matters so much. AI probing didn’t fail because the questions were awkward. It failed because the system had no explicit model of what it was trying to resolve.

# The Real Constraint Is Representation

A different way of representing the conversation opens up new possibilities.

A qualitative transcript, represented as sequential text, enables linguistic analysis - sentiment, keyword frequency, discourse patterns. Useful, and limited to the surface of language.
Thematic codes add a layer: theme frequencies, co-occurrence, comparison across respondents. More useful, but the structure between themes remains implicit.

But if you represent the interview as a belief-and-motivation network — concepts as nodes, relationships as edges — you can begin to model what moderators implicitly track:
causal chains
tensions and contradictions
missing links
“load-bearing” beliefs that support downstream reasoning
patterns that emerge across conversational distance

That representation enables a different kind of interviewing. Not just coverage, but coherence-seeking.

# Why You Can’t Just Build This After the Interview

You can reconstruct these networks post-hoc.
The depth of human moderation allows eliciting the networks of meaningful relationships.

But most current AI-moderated systems deliberately trade conversational freedom for scalability. They optimise for consistency, safety, and repeatability — which makes them excellent at coverage. The cost is reduced adaptiveness: fewer opportunities to stay with contradictions, follow emerging threads, and build complete causal explanations across turns.
The result is that causal chains remain fragmented, becuase AI's strict adherence to the guide limits its ability to follow through.

Real-time modelling changes that.
Contradictions can be resolved while the respondent is still present. Missing links can be probed immediately. Time can be allocated to what is structurally informative, rather than distributed evenly across guide topics.
At that point, the interview stops being “script execution” and starts behaving more like iterative hypothesis testing.

Which is a step closer to what good qualitative research already is.



# New Architecture, New Failure Modes

This approach doesn’t eliminate error. It changes the type of error.

Current AI moderation tends to fail by omission: it stays shallow.
Relational modelling systems risk failing by commission: confidently inventing links the transcript doesn’t support, or imposing causality where the respondent is rationalising, performing, or speaking metaphorically.

So governance shifts. Instead of only governing the input (tight guides), researchers increasingly govern the output: auditing whether edges are evidence-based, where confidence is inflated, and where hallucinated coherence creeps in.

In other words: less “did we ask the right questions?”
More “is this model actually warranted?”

# A Different Ceiling

The industry consensus is sensible: AI is strong on scale and consistency, weaker on nuance, and needs human oversight.

But the ceiling we’re describing may not be fundamental.
It may be specific to systems that treat interviews as text streams rather than evolving explanatory models.

A graph isn’t just a visualisation layer. It’s a form of structural memory: an explicit representation of what has been established, what remains unresolved, and what the most informative next probe might be.

If that’s right, the researcher’s role doesn’t shrink. It changes: less scripting, more defining modelling objectives, auditing integrity, and interpreting meaning that no representation can fully capture.

Which, arguably, is closer to what the best qualitative work has always been doing.

Source
Nexxt Intelligence: Reclaiming Conversation in the Age of AI
https://www.nexxt.in/perspectives/reclaiming-conversation-in-the-age-of-ai


# Case-study: What a Relational Model Makes Visible

Below is an example of a simulated 15-turns interview with a synthetic persona where the system prioritises the focus of the next question through the analysis of an evolving conversation graph.
Job-to-be-done was used as a framework that defines the nodes and edges of the conversation graph.

Full transcript: <link to Github>

## Example 1: a causal chain assembled across conversational distance (Chain 5)

Early in the interview, the respondent talks about avoiding the afternoon “rollercoaster” crash.
Later, a separate probe surfaces something that initially looks unrelated: sitting through slide-based presentations creates mental fatigue and “checking out” by afternoon.
A transcript reader would likely treat these as separate remarks.
A relational model links them into one coherent explanation:

<picture>
slide-heavy presentations → mental fatigue → struggle staying present in afternoon meetings → choosing a sugar-free fizzy drink to avoid the crash

The key point is that the respondent didn’t deliver this as a neat ladder in one answer. It emerged across turns. The system has to hold partial explanations open and connect them later.

That’s exactly the kind of sensemaking humans do automatically.

## Example 2: a chain assembled in reverse order (Chain 17)

Later, the respondent describes grabbing a drink before meetings, and feeling annoyed when they miss the chance.
Only afterwards do they explain that thirst becomes distracting, and that some meetings are high-stakes.

The system can reconstruct the causal logic backwards:

<picture>
high-stakes meetings → thirst becomes distracting → annoyance at missing the opportunity → grabbing a drink before meetings

Humans frequently explain causes after behaviours. Sequential transcripts don’t represent this well. Relational models do.