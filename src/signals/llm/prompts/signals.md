response_depth: How much elaboration does the response provide?
    1 = Minimal or single-word answer, no development
    2 = Brief statement with no supporting detail
    3 = Moderate elaboration with some explanation or context
    4 = Detailed response with reasoning, examples, or multiple facets
    5 = Rich, layered response exploring the topic from multiple angles

    Score the QUANTITY of elaboration, not its quality or accuracy.
    A long but repetitive response is 2-3, not 4-5.

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
  claim is objectively true. Distinguish from politeness — "I think" 
  used as a social softener in an otherwise assertive statement is 
  still 4, not 2.

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


# Comments:
The "distinguish from" guidance is embedded implicitly. Rather than a separate "Distinct From" field, each signal's anchor definitions contain boundary-setting language (e.g., depth says "quantity of elaboration, not quality"; valence says "emotional tone, not factual content"; engagement says "willingness, not articulateness"). This is more effective than explicit "this is not X" statements because it operates at the point of decision.

The certainty prompt handles the hedging-as-politeness problem. The explicit instruction about "I think" as a social softener addresses the main case where certainty and hedging would diverge — without requiring a separate hedging signal. If you later add the hedging module, you'd want to remove that line from certainty and let the two signals capture the distinction independently.