
# 0. new baseclass:

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class ScorerOutput(BaseModel):
    """Output from a single scorer.

    Contains the score and provenance for debugging.
    """
    scorer_name: str = Field(description="Name of the scorer")
    raw_score: float = Field(default=1.0, ge=0.0, le=2.0, description="Raw score 0-2")
    weight: float = Field(default=1.0, ge=0.1, le=5.0, description="Scorer weight")
    phase_multiplier: float = Field(default=1.0, ge=0.0, le=5.0, description="Phase-specific multiplier")
    weighted_score: float = Field(description="Score after weighting and phase multiplier")
    signals: Dict[str, Any] = Field(default_factory=dict, description="State signals used")
    reasoning: str = Field(default="", description="Human-readable explanation")
    vetoed: bool = Field(default=False, description="True if scorer triggered a veto / Tier-1 block")

    model_config = {"from_attributes": True}


class ScorerBase(ABC):
    """
    Abstract base class for all strategy scorers.

    Design constraints:
    - Pure functions of state (no side effects)
    - Single orthogonal dimension per scorer
    - All thresholds from config (no hardcoding)
    - Return multipliers or scores (phase-agnostic)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scorer with configuration.

        Args:
            config: Scorer configuration with optional:
                - enabled: bool (default: True)
                - weight: float (default: 1.0)
                - veto_threshold: float (default: 0.1)
                - params: dict of scorer-specific params
        """
        self.config = config or {}
        self.enabled: bool = self.config.get("enabled", True)
        self.weight: float = self.config.get("weight", 1.0)
        self.veto_threshold: float = self.config.get("veto_threshold", 0.1)
        self.params: Dict[str, Any] = self.config.get("params", {})

    @abstractmethod
    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: Any,  # Replace with actual GraphState type
        recent_nodes: List[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score a strategy/focus combination.

        Returns a phase-agnostic raw_score; phase weighting applied later.
        """
        pass

    def make_output(
        self,
        raw_score: float,
        signals: Dict[str, Any],
        reasoning: str,
        phase_multiplier: float = 1.0,
        vetoed: bool = False,
    ) -> ScorerOutput:
        """
        Construct ScorerOutput with proper validation.

        Args:
            raw_score: Raw score (0.0-2.0)
            signals: State signals used
            reasoning: Human-readable explanation
            phase_multiplier: Multiplier to adjust score for current phase
            vetoed: True if this scorer triggered a Tier-1 veto

        Returns:
            ScorerOutput with all fields populated
        """
        clamped = max(0.0, min(2.0, raw_score))
        weighted = (clamped ** self.weight) * phase_multiplier

        return ScorerOutput(
            scorer_name=self.__class__.__name__,
            raw_score=clamped,
            weight=self.weight,
            phase_multiplier=phase_multiplier,
            weighted_score=weighted,
            signals=signals,
            reasoning=reasoning,
            vetoed=vetoed,
        )

    def check_veto(self, raw_score: float) -> bool:
        """
        Check if the score is below the configured veto threshold.

        Returns True if scorer should veto the strategy (Tier-1 block)
        """
        return raw_score < self.veto_threshold

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"weight={self.weight}, "
            f"veto_threshold={self.veto_threshold})"
        )


# 0.5 for reference - pipeline integration pseudo code
phase_multiplier = PHASE_PROFILES[current_phase][strategy["id"]]
scorer_out = await scorer.score(strategy, focus, graph_state, recent_nodes)
scorer_out = scorer.make_output(
    raw_score=scorer_out.raw_score,
    signals=scorer_out.signals,
    reasoning=scorer_out.reasoning,
    phase_multiplier=phase_multiplier,
    vetoed=scorer_out.raw_score < scorer.veto_threshold,
)


---
# 1. AmbiguityScorer
---

Human rule  
“If the participant hedges (‘maybe’, ‘sort of’) or the prior turn is fuzzy, ask a clarifying follow-up before you move on.”

Canon source
- Briggs 1986 – “meta-pragmatic directives” to resolve communicative ambiguity.
- Kvale 1996 – “What do you mean by…?” as standard probing technique.

Quality criterion served  
Credibility / dependability – ensures interviewer’s interpretation is grounded in shared meaning, not noise.

Assessment  
✓ Directly operationalises a move every textbook recommends; weight 0.15-0.20 is appropriate because clarification is secondary to coverage but still essential.

def ambiguity_signals(focus_node, recent_turn_text):
    # 1. extraction confidence (already stored in node during NLP parse)
    extraction_conf = focus_node.get('extraction_confidence', 1.0)

    # 2. hedge / uncertainty density in last respondent utterance
    hedge_words = {'maybe', 'sort of', 'kind of', 'perhaps', 'possibly',
                   'i think', 'i guess', 'might', 'could be'}
    tokens = tokenize(recent_turn_text.lower())
    hedge_ratio = len([t for t in tokens if t in hedge_words]) / max(1, len(tokens))

    # 3. explicit uncertainty markers
    uncertainty_regex = re.compile(r'\b(not sure|don’t know|unclear|unsure)\b')
    uncert_bin = 1 if uncertainty_regex.search(recent_turn_text) else 0

    # --- composite clarity score 0-1 (1 = crystal clear) -----------------
    clarity = 1.0
    clarity -= 0.4 * hedge_ratio        # 0-0.4 penalty
    clarity -= 0.3 * uncert_bin         # 0 or 0.3 penalty
    clarity -= 0.2 * (1 - extraction_conf)  # 0-0.2 penalty
    clarity = max(0.0, clarity)

    signals = {
        'extraction_confidence': round(extraction_conf, 2),
        'hedge_ratio': round(hedge_ratio, 2),
        'uncertainty_marker': uncert_bin,
        'clarity': round(clarity, 2)
    }
    return signals

Scoring logic used by AmbiguityScorer
clarity ≥ 0.8 → no clarification needed (score 0.9 neutral)
0.5 ≤ clarity < 0.8 → mild boost (score 1.2)
clarity < 0.5 → strong boost (score 1.5)

---
# 2. CoverageGapScorer
---

Human rule  
“Track which stimulus elements (or topics) have never been mentioned, or mentioned but not elaborated, and prioritise those.”

Canon source
- Guest 2013 / Namey 2020 coverage-checklist approach in applied ethnography.
- Patton 2015 – “deductive topic list” that must be exhausted before closure.

Quality criterion served  
Completeness of the interview guide = analytic adequacy.

Assessment  
✓ Mirrors the moderator’s mental checklist; highest weight (0.20-0.25) is correct because coverage is a primary objective in semi-structured interviewing.

def coverage_gaps(focus_element, graph_state, conversation_history):
    """
    Returns dict of boolean flags for the four gap types.
    focus_element is the stimulus node/element we are evaluating.
    """
    gid = focus_element.id
    gaps = {
        "unmentioned": False,
        "no_reaction": False,
        "no_comprehension": False,
        "unconnected": False
    }

    # 1. unmentioned -------------------------------------------------
    if gid not in graph_state.mentioned_elements:
        gaps["unmentioned"] = True
        return gaps   # other gaps irrelevant if never spoken

    # 2. no_reaction -------------------------------------------------
    # element spoken but respondent never elaborated (only interviewer)
    turns = conversation_history.last_respondent_turns(since_element_mention=gid)
    elaboration_markers = {"because", "example", "specifically", "like", "feel"}
    has_elaboration = any(m in t.lower() for m in elaboration_markers for t in turns)
    if not has_elaboration:
        gaps["no_reaction"] = True

    # 3. no_comprehension -------------------------------------------
    # clarity of respondent utterance that referenced element < 0.6
    clarity_scores = [turn.clarity for turn in turns if turn.speaker == "respondent"]
    if clarity_scores and max(clarity_scores) < 0.6:
        gaps["no_comprehension"] = True

    # 4. unconnected -------------------------------------------------
    # element node has degree 0 in the respondent subgraph
    degree = graph_state.respondent_subgraph.degree(gid)
    if degree == 0:
        gaps["unconnected"] = True

    return gaps

Scoring multiplier used by CoverageGapScorer
0 gaps → 0.8 (slight penalty, already covered)
1–2 gaps → 1.2
3+ gaps → 1.5

---
# 3. DepthBreadthBalanceScorer
---

Human rule  
“Don’t let the interview become only stories (depth) or only shopping-list answers (breadth); alternate as needed.”

Canon source
- Spradley 1979 – oscillate between “structural” (breadth) and “contrast” (depth) questions.
- Rubin & Rubin 2012 – “funnelling and riffling” metaphor.

Quality criterion served  
Ensures richness (thick description) plus range (diversity of topics).

Assessment  
✓ Captures the classic funnel–rifflle rhythm; weight 0.20-0.25 is warranted because monotonic style is a common interviewer failure.

---
# 4. EngagementScorer
---

Human rule  
“If the respondent gives short, flat answers, simplify the question or switch to an easier topic; if energetic, you can go complex or abstract.”

Canon source
- Gorden 1987 – “rapport and energy matching” in field interviewing.
- Seidman 2013 – adjust question abstraction level to participant fatigue.

Quality criterion served  
Ethical / rapport maintenance; also reduces social-desirability dropout.

Assessment  
✓ Well-established adaptive tactic; however, weight 0.10-0.15 is correctly placed lower because engagement adaptation is supportive, not a primary analytic goal.

---
# 5. NoveltyScorer
---

Human rule  
“Don’t keep asking about the same sub-topic turn after turn – the respondent will feel hounded and start repeating.”

Canon source
- Kvale 1996 – “avoid redundancy fatigue.”
- Charmaz 2014 – constant comparative method implies moving to the _next_ comparison, not the same one.

Quality criterion served  
Maintains conversational naturalness and reduces reactivity threat.

Assessment  
✓ Valid heuristic; low weight (0.10-0.15) is appropriate because novelty is a secondary courtesy, not a scientific requirement.

---
# 6. StrategyDiversityScorer
---

Human rule  
“Vary question form so the interview doesn’t sound like a robot reading a script.”

Canon source
- Warren 2002 – stylistic variety keeps qualitative interviews lively.
- Gubrium & Holstein 2002 – “active interviewing” stresses discursive variety.

Quality criterion served  
Reduces method artefact (responses shaped by repetitive form).

Assessment  
✓ Sound, but rightly given the lowest weight (0.10-0.15) because it is aesthetic rather than analytic.

---
# 7. PeripheralReadinessScorer → “lateral probing / convergent interview expansion”
---

Canon source
- Spradley 1979 _The Ethnographic Interview_ – “expanding the taxonomy” once a ‘domain’ is saturated.    
- Kvale 1996 _InterViews_ – “probing towards new themes when the present theme is exhausted.”    
- Rubin & Rubin 2012 – “ripple-out technique”: start in the centre, move outward in concentric circles only when inner circle is ‘thick’.

Human moderator cue  
“Once the respondent can repeat the story with no new subtleties, gently pivot: ‘Have you ever… ?’ ‘What about people who… ?’”

Graph translation  
local_edge_density high + credible un-linked candidates nearby ⇒ scorer peaks.  
That is exactly the numeric mirror of “no new subtleties” + “untouched but plausible topic exists”.

pseudo-code:

'''python
"""
Peripheral readiness scorer (Tier 2).

Measures how 'ripe' the graph is for a lateral jump to an
unvisited but topically-relevant node.
Boosts bridge strategy when current cluster is saturated
and credible peripheral candidates exist.
Weight: 0.20  (same order as CoverageGap)
"""

def score(strategy, focus, graph_state, recent_nodes, conversation_history):
    # --- signals ----------------------------------------------------------
    local_edge_density  = _local_cluster_density(focus, graph_state)
    largest_ratio       = _largest_cluster_ratio(graph_state)
    cand_count, max_rel = _peripheral_candidates(focus, graph_state, max_hop=3)
    turns_since_jump    = _turns_since_last_cluster_jump(conversation_history)

    # --- raw score (0.5-1.8 range) ----------------------------------------
    if strategy.id != "bridge":
        return Tier2Output(1.0, {}, "not bridge strategy")

    # boost when current cluster is dense AND peripherals exist
    density_term  = 0.7 + 0.6 * local_edge_density            # 0.7-1.3
    peripheral_term = 0.8 + 0.7 * (cand_count / max(1, len(graph_state.nodes)))
    novelty_term = min(1.4, 1.0 + 0.04 * turns_since_jump)    # encourage after 8-10 turns
    raw = density_term * peripheral_term * novelty_term
    raw = max(0.5, min(1.8, raw))

    signals = {
        "local_edge_density": round(local_edge_density, 2),
        "peripheral_candidates": cand_count,
        "max_peripheral_relevance": round(max_rel, 2),
        "turns_since_cluster_jump": turns_since_jump
    }
    reasoning = (f"Cluster density {local_edge_density:.2f}, "
                f"{cand_count} peripherals ready, score = {raw:.2f}")
    return Tier2Output(raw, signals, reasoning)
'''

---
# 8. ContrastOpportunityScorer → “devil’s advocate / comparative probe”
---

Canon source
- Patton 2015 _Qualitative Research & Evaluation Methods_ – “extreme-case and discrepancy probes” to surface assumptions.
- Seidman 2013 _Interviewing as Qualitative Research_ – “What-if-the-opposite” technique to test boundaries of the participant’s meaning structure.
    

Human moderator cue  
“You’re saying X is always the case – can you think of a time when the opposite happened?”

Graph translation  
has_opposite_stance = TRUE and local cluster coherent ⇒ scorer high.  
We literally look for an “extreme-case node” that is semantically opposite and still unvisited, and only offer it after the participant’s position is solid (high density).

pseudo-code:

'''python
"""
Contrast-opportunity scorer (Tier 2).

Scores whether a credible opposite-view node is available
and the current cluster is solid enough to withstand contrast.
Weight: 0.18
"""

def score(strategy, focus, graph_state, recent_nodes, conversation_history):
    if strategy.id != "contrast":
        return Tier2Output(1.0, {}, "not contrast strategy")

    local_density   = _local_cluster_density(focus, graph_state)
    has_opposite    = _has_opposite_stance_node(focus, graph_state)
    largest_ratio   = _largest_cluster_ratio(graph_state)

    # only offer contrast when cluster is coherent
    density_term = 0.5 + 0.8 * local_density                 # 0.5-1.3
    opposite_term = 1.5 if has_opposite else 0.7
    balance_term = 1.0 + 0.4 * (1 - largest_ratio)           # favour when graph lopsided
    raw = density_term * opposite_term * balance_term
    raw = max(0.5, min(1.8, raw))

    signals = {
        "local_density": round(local_density, 2),
        "has_opposite_stance": has_opposite,
        "largest_cluster_ratio": round(largest_ratio, 2)
    }
    reasoning = (f"Opposite stance available: {has_opposite}, "
                f"local density {local_density:.2f}, score = {raw:.2f}")
    return Tier2Output(raw, signals, reasoning)
'''


---
# 9. ClusterSaturationScorer → “summary + member-check / transition cue
---

Canon source
- Charmaz 2014 _Constructing Grounded Theory_ – “iterative summarising” to confirm with participant before leaving a category.    
- Guba & Lincoln 1989 – “member check” as credibility step: “Have I got that right?” before moving on.    

Human moderator cue  
“Let me see if I’ve understood – you feel … Is that a fair summary? Anything to add before we move on?”

Graph translation  
local_density & median_degree high + respondent calm (low sentiment variance) ⇒ scorer high.  
The scorer fires when the subgraph is internally well connected and the emotional signal shows the speaker is comfortable enough to endorse a wrap-up.

pseudo-code:

'''python
"""
Cluster-saturation scorer (Tier 2).

Detects when the current topical island is 'complete'
and a summarising / transition question is optimal.
Weight: 0.15
"""

def score(strategy, focus, graph_state, recent_nodes, conversation_history):
    if strategy.id != "synthesis":
        return Tier2Output(1.0, {}, "not synthesis strategy")

    median_degree = _median_degree_inside(focus, graph_state)
    local_density = _local_cluster_density(focus, graph_state)
    sentiment_var = _recent_sentiment_variance(conversation_history, window=3)
    nodes_in_cluster = _cluster_size(focus, graph_state)

    saturation = min(1.0, local_density * median_degree / 3.0)
    size_term = min(1.2, 1.0 + 0.02 * nodes_in_cluster)   # reward bigger clusters
    calm_term = 1.0 + 0.4 * (1 - sentiment_var)            # prefer calm respondent
    raw = 0.7 + 0.7 * saturation * size_term * calm_term
    raw = max(0.5, min(1.8, raw))

    signals = {
        "local_density": round(local_density, 2),
        "median_degree": round(median_degree, 1),
        "sentiment_variance": round(sentiment_var, 2),
        "cluster_node_count": nodes_in_cluster
    }
    reasoning = (f"Saturation {saturation:.2f}, "
                f"cluster size {nodes_in_cluster}, score = {raw:.2f}")
    return Tier2Output(raw, signals, reasoning)
'''
