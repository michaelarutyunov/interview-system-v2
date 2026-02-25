response_depth: How many distinct pieces of information does the response contribute?
    1 = Single phrase or restated fact only; nothing new introduced
        (includes all closing pleasantries: "you're welcome", "glad I could help", "thanks")
    2 = One main point stated plainly; no supporting context, reasoning, or consequences
    3 = Two to three distinct informational propositions
        (e.g., a goal + a constraint, or a behaviour + a reason why)
    4 = Four or more distinct propositions, or a chain of reasoning with intermediate steps,
        or concrete examples that add new content beyond what was asked
    5 = Multiple independent threads of content, each contributing new extractable concepts;
        introduces angles not implied by the question

    Score the NUMBER OF DISTINCT CONCEPTS introduced, not the word count or verbal style.
    A terse 20-word answer with three distinct propositions scores 3, not 1.
    A 100-word answer that repeats one idea in many ways scores 2, not 4.

specificity: How concrete and specific is the response?
    1 = Entirely abstract or generic ("it's just better")
    2 = Mostly vague with one minor concrete element
    3 = Mix of abstract and concrete, some situational detail
    4 = Mostly concrete with named examples, situations, or behaviours
    5 = Highly specific with precise details: times, places, actions, quantities, or named entities

    Score the CONCRETENESS of language, not the length.
    "I switched last Tuesday after checkout crashed three times" is 5.
    "I just felt like the experience could be improved overall" is 1.

certainty: How confident does the respondent appear in their statement?
    1 = Highly uncertain, explicitly unsure ("I don't know", "maybe")
    2 = Tentative, multiple qualifications, hedged throughout
    3 = Moderate confidence, some qualifications but generally committed
    4 = Confident with minor caveats
    5 = Fully committed, unqualified, no hedging or doubt expressed

    Score the respondent's EXPRESSED confidence, not whether their
    claim is objectively true. Distinguish genuine uncertainty from
    social softeners: "mostly", "kind of", "I guess", "sort of" are
    genuine hedges that reduce the score; "I think" or "I feel" used
    as sentence openers in otherwise assertive statements are not.

  Calibration examples:
  - "Work, mostly" → 2 (explicit hedge "mostly" limits commitment)
  - "It's kind of good, I guess" → 1-2 (multiple hedges)
  - "I think it's pretty good" → 4 (social softener, otherwise assertive)
  - "That's exactly what I need" → 5 (unqualified assertion)
  - "Honestly, I'm not sure I ever get there completely. Maybe X, I feel less Y, I guess." → 2
    (multiple genuine hedges mid-sentence override the assertive opener; score by the hedges, not the opener)
  - "Consistency, mainly. I can actually measure it." → 4
    ("mainly" is a genuine qualification that caps the score; "I can actually" is assertive — balance at 4)

emotional_valence: What is the emotional tone of the response?
    1 = Strongly negative (frustration, anger, disappointment)
    2 = Mildly negative or critical
    3 = Neutral, factual, no discernible emotional charge
    4 = Mildly positive (satisfaction, mild enthusiasm)
    5 = Strongly positive (excitement, delight, strong advocacy)

    Score the EMOTIONAL TONE, not the factual content. A calm
    description of a negative event is 3, not 1. A frustrated
    description of a positive outcome is 2, not 4. Mixed emotions
    should be scored by the dominant tone.

intellectual_engagement: How analytically invested is the respondent — do they express reasoning, values, tradeoffs, or motivations rather than bare facts?
    1 = No reasoning offered: bare assertions, single-word answers, or restated facts with no "why" or "because"
    2 = Minimal reasoning: one motivation or qualifier stated, but no causal chain or value expression
    3 = Moderate analytical investment: some reasoning or value language ("I care about X because Y"), but incomplete or underdeveloped
    4 = Clear reasoning chains: explicit motivations, stated tradeoffs, goal-oriented language, or "because" constructions that reveal underlying values
    5 = Dense motivational structure: multiple interlinked reasons, value hierarchies, self-aware tradeoffs, or causal explanations that reveal why something matters at a deeper level

    Score the PRESENCE OF REASONING AND MOTIVATION STRUCTURE, not the word count or domain vocabulary.
    A terse "I won't trust it unless I can verify the source — that's just how I make decisions" is 4 (clear stated value chain).
    A lengthy but purely descriptive response ("I use it on Tuesdays, sometimes Wednesdays, mostly for meetings") is 1-2.
    "It matters because consistency compounds over time, and that's the actual job I'm trying to hire for" is 5.

engagement: How willing is the respondent to engage with this topic?
    1 = Minimal effort: single words, "I don't know", deflection,
        or restating the question back
    2 = Compliant but passive: answers the literal question with
        no voluntary extension
    3 = Adequate engagement: answers fully but does not volunteer
        additional information
    4 = Active engagement: extends beyond the question, offers
        unsolicited detail or examples
    5 = High engagement: enthusiastic elaboration, introduces new
        related points, or signals wanting to say more

    Score the respondent's WILLINGNESS to engage, not their
    articulateness. A poorly worded but effortful answer is 4-5.
    A polished but minimal answer is 2.
