[
    {
        "id": "deepen",
        "name": "Deepen Understanding",
        "human_description": "Ask focused follow-ups to elicit more concrete details or examples on the current topic.",
        "prompt_hint": "Ask a focused follow-up that invites concrete detail or example. Stay on the same topic.",
        "type_category": "depth"
    },
    {
        "id": "broaden",
        "name": "Explore Breadth",
        "human_description": "Invite the respondent to mention other relevant aspects or experiences without going deep yet.",
        "prompt_hint": "Invite the respondent to mention other relevant aspects or experiences, without probing deeply into any one.",
        "type_category": "breadth"
    },
    {
        "id": "cover_element",
        "name": "Cover Stimulus Element",
        "human_description": "Ensure specific pre-defined topics or stimulus elements are addressed.",
        "prompt_hint": "Ask a question that ensures the respondent addresses this specific topic or element.",
        "type_category": "coverage"
    },
    {
        "id": "bridge",
        "name": "Lateral Bridge to Peripheral",
        "human_description": "Move to a related but distinct area while linking back to the previous discussion.",
        "prompt_hint": "Explicitly link to what was just said, then gently shift to a related but distinct area.",
        "type_category": "peripheral"
    },
    {
        "id": "contrast",
        "name": "Introduce Counter-Example",
        "human_description": "Politely introduce an opposite or exceptional case to test boundaries and assumptions.",
        "prompt_hint": "Politely introduce a counter-example or opposite case to test boundaries, without sounding confrontational.",
        "type_category": "contrast"
    },
    {
        "id": "clarify",
        "name": "Clarify Meaning",
        "human_description": "Request clarification to remove ambiguity before proceeding.",
        "prompt_hint": "Ask for clarification of a specific term or meaning before moving on.",
        "type_category": "clarification"
    },
    {
        "id": "ease",
        "name": "Ease / Rapport Repair",
        "human_description": "Reduce social friction, simplify questions, or encourage participation when engagement drops.",
        "prompt_hint": "Simplify or soften the question, encourage participation, and maintain rapport without pushing.",
        "type_category": "interaction"
    },
    {
        "id": "synthesis",
        "name": "Summarise & Invite Extension",
        "human_description": "Summarise the current cluster of discussion and invite corrections or additions before moving on.",
        "prompt_hint": "Briefly summarise what you’ve heard and invite correction or addition before transitioning.",
        "type_category": "transition"
    },
    {
        "id": "reflection",
        "name": "Reflection / Meta-Question",
        "human_description": "Prompt the respondent to step back and reflect on meaning or implications.",
        "prompt_hint": "Invite the respondent to reflect on broader meaning or implications, not details.",
        "type_category": "reflection"
    },
    {
        "id": "closing",
        "name": "Closing Interview",
        "human_description": "Signal interview wrap-up and ask for any final thoughts.",
        "prompt_hint": "Signal that the interview is wrapping up and ask for any final thoughts.",
        "type_category": "closing"
    }
]


PHASE_PROFILES = {
    "exploratory": {
        "deepen": 0.8,
        "broaden": 1.2,
        "cover_element": 1.1,
        "clarify": 1.2,
        "pivot": 0.2,
        "contrast": 0.0,
        "reflection": 0.3,
        "closing": 0.0,
    },
    "focused": {
        "deepen": 1.3,
        "broaden": 0.4,
        "cover_element": 1.1,
        "clarify": 0.8,
        "pivot": 1.0,
        "contrast": 1.2,
        "reflection": 0.7,
        "closing": 0.3,
    },
}

Tier 1 

| Strategy      | Candidate Tier-1 signals                                            | Why                                                   |
| ------------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| deepen        | none                                                                | Always safe to ask follow-ups, no hard requirement    |
| broaden       | none                                                                | Same, can always explore islands                      |
| cover_element | CoverageGapScorer (gap == 0 → veto)                                 | If the element is fully covered, do not trigger again |
| bridge        | PeripheralReadinessScorer (if no ready neighbor → veto)             | Cannot bridge if there’s nothing peripheral ready     |
| contrast      | ContrastOpportunityScorer (if no extreme/contradictory node → veto) | Cannot challenge if no valid counter-example exists   |
| clarify       | AmbiguityScorer (if clarity ≥ 0.8 → skip)                           | Don’t ask clarification if there’s nothing ambiguous  |
| ease          | none                                                                | Can always use interaction, low-risk                  |
| synthesis     | ClusterSaturationScorer (if cluster not saturated → skip)           | Only summarise when cluster is complete               |
| reflection    | StrategyDiversityScorer / EngagementScorer → soft only              | Never a hard blocker; soft fallback is enough         |
| closing       | turn-count                                                          | Cannot close until min_turns reached                  |


Final score for a candidate =
[ Σ (tier-scorer-weight × scorer_output) ] × phase_profile[strategy]