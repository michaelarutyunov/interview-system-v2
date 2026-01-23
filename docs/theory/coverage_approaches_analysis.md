# Coverage vs. Emergence in Adaptive Interview Systems

## Executive Summary

This document analyzes the fundamental tension between **coverage-driven** (systematic topic exploration) and **graph-driven** (emergent discovery) approaches in adaptive interview systems for qualitative research. It provides:

1. Literature review establishing methodological precedents
2. Analysis of the architectural tension between these two paradigms
3. Technical recommendations for implementing a dual-mode system
4. Example configurations for both approaches

**Key Finding:** The current system architecture already supports both paradigms with ~85% shared infrastructure. The primary difference lies in configuration and state management, not fundamental code structure.

---

## Part 1: Literature Review - Coverage in Qualitative Research

### 1.1 Interview Guide Coverage (Semi-Structured Interviews)

**Standard Practice:** Qualitative researchers use interview guides to ensure systematic coverage of predetermined topics.

> "To achieve optimum use of interview time, interview guides serve the useful purpose of exploring many respondents more systematically and **comprehensively** as well as to keep the interview focused" (Kallio et al. 2016)

**Key Principle:** The interview guide acts as a mental checklist ensuring all planned topics are addressed, though order and wording remain flexible.

**Parallel to System:** The concept of "interview guide completeness" directly maps to the system's `unmentioned` gap type - tracking whether predetermined topics have been addressed.

### 1.2 Probing Techniques (Depth and Clarification)

**Methodological Framework:** Researchers distinguish between multiple types of probes to ensure data quality:

| Probe Type | Purpose | System Gap Equivalent |
|------------|---------|---------------------|
| **Follow-up probes** | "Tell me more about..." | Addresses shallow coverage |
| **Clarifying probes** | "What do you mean by..." | `no_comprehension` gap |
| **Specifying probes** | "How did X make you feel?" | `no_reaction` gap (affect) |
| **Elaboration probes** | "Can you give an example?" | Adds depth/richness |

**Critical Distinction:** Qualitative methodology explicitly separates:
- **Breadth**: Mentioning the topic (coverage)
- **Depth**: Understanding meaning + affect (comprehension + reaction)

**Parallel to System:** The multi-dimensional gap framework (mention, reaction, comprehension, connection) operationalizes these established probing practices.

### 1.3 Means-End Chain Laddering (Connected Chains Requirement)

**Methodological Foundation:** The MEC/laddering technique explicitly requires connected attribute-consequence-value chains.

> "Laddering refers to an in-depth, one-on-one interviewing technique used to develop an understanding of how consumers translate the attributes of products into meaningful associations with respect to self, following means-end theory" (Reynolds & Gutman 1988)

**Critical Requirement:** 

> "The ladder obtained from an interview only reveals aspects of cognitive structure if it forms an **inter-related network of associations**" (Veludo-de-Oliveira et al. 2006)

**Incomplete ladders** (attributes without consequences, or consequences without values) are considered **methodological failures** in the MEC tradition.

**Parallel to System:** The `unconnected` gap type has the strongest theoretical grounding - isolated nodes without edges represent incomplete data collection in laddering methodology.

**Key Quote on Laddering Process:**

> "The general notion is to get the respondent to respond and then to react to that response. Thus, laddering consists of a series of directed probes based on mentioned distinctions" (Reynolds & Gutman 1988)

**Practical Reality:**

> "This form of technique can very be tiring and or boring for the interviewee as the same questions are asked over and over again" (Wikipedia: Ladder Interview, noting common criticism)

### 1.4 What Qualitative Research Does NOT Have

**Critical Gap:** No qualitative methodology literature describes:
- Real-time algorithmic coverage tracking
- Multi-dimensional gap closure criteria
- Automated exhaustion detection (3-attempt threshold)
- Systematic topic-to-data-element mapping during interviews

**Traditional Practice:** These are implemented through:
- Interviewer expertise and judgment
- Post-interview reflection and memos
- Iterative guide refinement between interviews

**System Innovation:** The 4-gap-type coverage framework represents **methodological innovation**, not established practice. It operationalizes interviewer expertise into algorithmic form.

### 1.5 Saturation (Cross-Interview Concept)

**Definition:** Point at which no new themes emerge from additional interviews.

**Types of Saturation:**
- **Code saturation**: No new codes emerging (~9-16 interviews, Hennink et al. 2017)
- **Meaning saturation**: Depth of understanding achieved  
- **Theoretical saturation**: Theory completeness (often 2x interviews needed)

**Measurement Approach (Guest et al. 2020):**
```
New information rate = new_codes_in_window / total_codes_discovered
Saturation when: new_info_rate < 5% for N consecutive interviews
```

**Critical Difference:** Saturation measures emergent themes **across interviews**, not systematic element coverage **within** single interviews. These are orthogonal concepts.

---

## Part 2: The Fundamental Tension

### 2.1 Two Incompatible Philosophies

#### **Position A: Coverage-Driven (Systematic Exploration)**

**Philosophy:**
- Researcher has **predefined topics** that must be explored
- Interview guide is **directive** (semi-structured)
- Success = **completeness** (all topics covered with sufficient depth)
- Graph is **documentation** of what was learned

**Methodological Alignment:**
- ✅ Semi-structured interviews (Kallio et al. 2016)
- ✅ MEC laddering technique (Reynolds & Gutman 1988)
- ✅ Concept testing research (systematic claim evaluation)
- ❌ NOT grounded theory (which is emergent, not predetermined)

**Interview Flow:**
```
1. Opening: Broad impression
2. Systematic topic coverage:
   - Topic 1 → deepen → saturate
   - Topic 2 → deepen → saturate
   - Topic 3 → deepen → saturate
3. Close when coverage threshold met
```

**Graph Role:** By-product of topic exploration (documentation)

**Success Metrics:**
- Coverage ratio (% topics completed)
- Average depth per topic
- Interview completeness

---

#### **Position B: Graph-Driven (Emergent Discovery)**

**Philosophy:**
- Respondent's **natural associations** guide conversation
- Interview is **minimally directive** (conversational/unstructured)
- Success = **richness** (dense, well-connected graph revealing emergent themes)
- Topics are **discovered**, not predetermined

**Methodological Alignment:**
- ✅ Grounded theory (themes emerge from data)
- ✅ In-depth interviews (conversational, respondent-led)
- ✅ Narrative inquiry (follow story threads)
- ❌ NOT concept testing (which needs systematic evaluation)

**Interview Flow:**
```
1. Opening: "Tell me your first impressions"
2. Follow respondent's lead:
   - If they mention health → explore deeply
   - If they mention taste → explore deeply
   - If they mention environment → explore (even if unplanned)
3. Gentle nudges only for major omissions
4. Close when saturation across active themes
```

**Graph Role:** Primary output (reveals respondent's mental model)

**Success Metrics:**
- Graph density (nodes per edge ratio)
- Theme diversity (emergent clusters)
- Novel connection discovery

---

### 2.2 The Architectural Contradiction

**Current System Tension:**

```python
# Scorer priorities encode this contradiction:

ElementCoverageScorer:   weight=1.0, boost=2.5x  # Coverage-first
NoveltyScorer:           weight=1.0, boost=2.0x  # Graph-first
DepthScorer:             weight=1.0, boost=1.8x  # Graph-first
```

**The Problem:** The system is trying to be both:
- **Systematic** (ensure topics covered) 
- **Emergent** (follow natural flow)

**Result:** Schizophrenic behavior
- Early interview: "Must cover topics!" 
- Mid interview: "Follow interesting chains!"
- Late interview: "Back to uncovered topics!"

**This creates jarring transitions that feel mechanical.**

### 2.3 Why You Must Choose

These paradigms have **fundamentally opposed** decision-making criteria:

| Decision Point | Coverage-Driven | Graph-Driven |
|---------------|-----------------|--------------|
| **Next topic** | First uncovered topic | Most interesting thread |
| **When to switch** | Topic exhausted or covered | Respondent changes direction |
| **Depth vs breadth** | Ensure breadth first | Follow depth naturally |
| **Success** | All topics addressed | Rich emergent themes |
| **Respondent role** | Answer researcher questions | Lead the exploration |

**You cannot optimize for both simultaneously.**

---

## Part 3: Architectural Analysis

### 3.1 Shared Infrastructure (70% - No Changes)

Both positions share identical components:

```python
# Domain models - IDENTICAL
class Node(BaseModel): ...
class Edge(BaseModel): ...
class Graph: ...
class History: ...

# LLM integration - IDENTICAL  
class LLMClient: ...
class Extractor:
    def extract_nodes_edges(...) -> ExtractionResult: ...

# Question generation - IDENTICAL
class QuestionGenerator:
    def generate(strategy, focus, context) -> str: ...

# Database - IDENTICAL
class GraphRepository: ...
class SessionRepository: ...

# API layer - IDENTICAL
@router.post("/sessions/{id}/respond")
async def respond(...): ...
```

**Why Identical?**
- Graph data structure doesn't care about philosophy
- Extraction always creates nodes/edges from text
- Question generation always takes (strategy, focus, context)
- Database stores graph regardless of approach

### 3.2 Key Differences (30% - Changes Required)

#### **State Models (5% of codebase)**

**Coverage-Driven:**
```python
class CoverageState:
    topics: Dict[str, TopicState]
    
    @dataclass
    class TopicState:
        topic_id: str
        mentioned: bool
        depth_score: float
        saturation: float
        node_ids: List[str]
        
        def is_complete(self) -> bool:
            return (
                self.mentioned and
                self.depth_score > threshold and
                self.saturation > threshold
            )
```

**Graph-Driven:**
```python
class EmergenceState:
    themes: Dict[str, ThemeState]
    
    @dataclass
    class ThemeState:
        theme_id: str  # Auto-generated from clustering
        label: str
        node_ids: List[str]
        saturation: float
        first_seen_turn: int
        
        def is_saturated(self) -> bool:
            return self.saturation > threshold
```

#### **Scoring Configuration (2% of codebase - YAML only)**

**Coverage-Driven:**
```yaml
scorers:
  topic_coverage:
    weight: 1.2  # HIGH - must cover topics
  depth_within_topic:
    weight: 1.0
  novelty:
    weight: 0.6  # LOW - only when coverage satisfied
```

**Graph-Driven:**
```yaml
scorers:
  # NO coverage scorer
  novelty:
    weight: 1.5  # HIGH - follow interesting threads
  depth_on_thread:
    weight: 1.3
  emergent_connection:
    weight: 1.2
```

#### **Strategy Priorities (3% of codebase - YAML + logic)**

**Coverage-Driven:**
```yaml
strategies:
  cover_new_topic:
    priority: 1.0  # HIGH
  deepen_current_topic:
    priority: 0.8
  explore_emergent:
    priority: 0.3  # LOW - only when coverage satisfied
```

**Graph-Driven:**
```yaml
strategies:
  follow_novel_branch:
    priority: 1.0  # HIGH
  deepen_current_thread:
    priority: 0.9
  nudge_missing_area:
    priority: 0.2  # LOW - safety net only
```

### 3.3 Total Refactor Estimate

| Component | Refactor Effort |
|-----------|-----------------|
| Shared infrastructure | 0% (no changes) |
| State models | 5% |
| Scorer configs | 2% |
| Strategy configs | 3% |
| Session initialization | 2% |
| Completion criteria | 1% |
| **Total** | **~13-15%** |

---

## Part 4: Implementation Recommendations

### 4.1 Design Pattern: Session Profile Configuration

**Recommendation:** Make interview mode a **session initialization parameter** rather than hardcoded behavior.

**Architecture:**

```python
# Enum for interview modes
class InterviewMode(str, Enum):
    COVERAGE_DRIVEN = "coverage_driven"
    GRAPH_DRIVEN = "graph_driven"
    # Future: HYBRID = "hybrid"

# Session creation
session = await session_service.create(
    concept_id="oat_milk",
    methodology="means_end_chain",
    mode=InterviewMode.COVERAGE_DRIVEN  # or GRAPH_DRIVEN
)
```

**Benefits:**
1. Single codebase supports both modes
2. A/B testing capability (same concept, different modes)
3. Clear user choice ("Select interview style...")
4. Future extensibility (add hybrid modes)

### 4.2 State Model Abstraction

**Create abstract base class:**

```python
# src/domain/models/interview_state.py

from abc import ABC, abstractmethod
from typing import Protocol

class InterviewState(ABC):
    """Abstract base for interview state tracking."""
    
    @abstractmethod
    def completion_ratio(self) -> float:
        """Return 0-1 completion score."""
        pass
    
    @abstractmethod
    def should_close(self, turn_count: int, config: Config) -> bool:
        """Determine if interview should end."""
        pass
    
    @abstractmethod
    def get_focus_candidates(self, graph: Graph) -> List[FocusCandidate]:
        """Return potential focus items for next question."""
        pass

# Coverage-driven implementation
class CoverageState(InterviewState):
    topics: Dict[str, TopicState]
    
    def completion_ratio(self) -> float:
        complete = sum(1 for t in self.topics.values() if t.is_complete())
        return complete / len(self.topics)
    
    def should_close(self, turn_count: int, config: Config) -> bool:
        return (
            self.completion_ratio() >= config.target_coverage and
            turn_count >= config.min_turns
        )
    
    def get_focus_candidates(self, graph: Graph) -> List[FocusCandidate]:
        # Return uncovered topics as candidates
        return [
            FocusCandidate(
                type="topic",
                id=topic_id,
                priority=topic.priority,
                reason="uncovered"
            )
            for topic_id, topic in self.topics.items()
            if not topic.is_complete()
        ]

# Graph-driven implementation
class EmergenceState(InterviewState):
    themes: Dict[str, ThemeState]
    auto_discovery: bool = True
    
    def completion_ratio(self) -> float:
        if not self.themes:
            return 0.0
        saturated = sum(1 for t in self.themes.values() if t.is_saturated())
        return saturated / len(self.themes)
    
    def should_close(self, turn_count: int, config: Config) -> bool:
        return (
            all(t.is_saturated() for t in self.themes.values()) and
            turn_count >= config.min_turns
        )
    
    def get_focus_candidates(self, graph: Graph) -> List[FocusCandidate]:
        # Return novel nodes and unsaturated themes
        novel_nodes = [n for n in graph.nodes if n.is_novel()]
        return [
            FocusCandidate(
                type="node",
                id=node.id,
                priority="high" if node.connection_count < 2 else "medium",
                reason="novel"
            )
            for node in novel_nodes
        ]
```

### 4.3 Strategy Selection Dispatch

**Mode-aware strategy loading:**

```python
# src/services/strategy_service.py

class StrategyService:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
    
    def load_strategies(self, mode: InterviewMode) -> List[Strategy]:
        """Load mode-specific strategy configurations."""
        
        if mode == InterviewMode.COVERAGE_DRIVEN:
            config = self.config_loader.load("strategies/coverage_driven.yaml")
        elif mode == InterviewMode.GRAPH_DRIVEN:
            config = self.config_loader.load("strategies/graph_driven.yaml")
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        return [
            Strategy.from_config(strategy_config)
            for strategy_config in config["strategies"]
        ]
    
    def load_scorers(self, mode: InterviewMode) -> List[StrategyScorer]:
        """Load mode-specific scorer configurations."""
        
        if mode == InterviewMode.COVERAGE_DRIVEN:
            config = self.config_loader.load("scoring/coverage_driven.yaml")
        elif mode == InterviewMode.GRAPH_DRIVEN:
            config = self.config_loader.load("scoring/graph_driven.yaml")
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        return self._instantiate_scorers(config["scorers"])
```

### 4.4 Concept Schema Validation

**Mode-aware concept validation:**

```python
# src/services/concept_service.py

class ConceptService:
    async def load(
        self, 
        concept_id: str, 
        mode: InterviewMode
    ) -> Concept:
        """Load and validate concept for specified mode."""
        
        concept = await self.repository.get(concept_id)
        
        # Validate concept has required fields for mode
        if mode == InterviewMode.COVERAGE_DRIVEN:
            if not concept.topics:
                raise ValueError(
                    f"Concept {concept_id} requires 'topics' for "
                    f"coverage-driven mode"
                )
        
        # Graph-driven mode doesn't require topics
        # (they'll be discovered)
        
        return concept
```

### 4.5 Session Initialization

**Mode-specific initialization:**

```python
# src/services/session_service.py

class SessionService:
    async def create(
        self,
        concept_id: str,
        methodology: str,
        mode: InterviewMode
    ) -> Session:
        """Create new interview session with specified mode."""
        
        # Load concept (validated for mode)
        concept = await self.concept_service.load(concept_id, mode)
        
        # Load methodology schema
        schema = await self.schema_service.load(methodology)
        
        # Initialize mode-specific state
        if mode == InterviewMode.COVERAGE_DRIVEN:
            interview_state = CoverageState(
                topics={
                    topic.id: TopicState(
                        topic_id=topic.id,
                        mentioned=False,
                        depth_score=0.0,
                        saturation=0.0,
                        node_ids=[]
                    )
                    for topic in concept.topics
                }
            )
        else:  # GRAPH_DRIVEN
            interview_state = EmergenceState(
                themes={},
                auto_discovery=True
            )
        
        # Initialize session
        session = Session(
            id=generate_id(),
            concept=concept,
            methodology=schema,
            mode=mode,
            state=interview_state,
            graph=Graph(),
            history=History()
        )
        
        # Seed graph with stimulus nodes (common to both modes)
        seed_nodes = await self.extractor.extract_seed_nodes(
            concept.description
        )
        for node in seed_nodes:
            session.graph.add_node(node)
        
        return session
```

### 4.6 File Structure

```
src/
├── domain/
│   └── models/
│       ├── interview_state.py      # NEW: Abstract base + implementations
│       │   ├── class InterviewState (ABC)
│       │   ├── class CoverageState
│       │   └── class EmergenceState
│       ├── session.py              # MODIFIED: Add mode field
│       └── ...
│
├── services/
│   ├── session_service.py          # MODIFIED: Mode-aware initialization
│   ├── strategy_service.py         # MODIFIED: Mode-aware config loading
│   ├── concept_service.py          # MODIFIED: Mode-aware validation
│   └── ...
│
└── config/
    ├── strategies/
    │   ├── coverage_driven.yaml    # NEW
    │   └── graph_driven.yaml       # NEW
    │
    ├── scoring/
    │   ├── coverage_driven.yaml    # NEW
    │   └── graph_driven.yaml       # NEW
    │
    └── concepts/
        └── [concept_name].yaml     # MODIFIED: Add topics section
```

---

## Part 5: Configuration Examples

### 5.1 Concept Schema (Coverage-Driven Mode)

```yaml
# config/concepts/oat_milk_v1.yaml

# Metadata
id: oat_milk_v1
name: "Oat Milk Concept"
created_date: "2026-01-22"

# Stimulus (what respondent sees/reads)
stimulus:
  format: text  # Options: text | image | video | prototype
  content: |
    Introducing a new oat-based milk alternative made with an 
    enzyme process that creates natural creaminess from 
    Scandinavian oats, without any added thickeners.

# Topics to cover (researcher-defined for coverage-driven mode)
# NOTE: For graph-driven mode, this section can be omitted
topics:
  - id: plant_based_positioning
    label: "Plant-based category perception"
    description: "How respondent perceives plant-based alternatives generally"
    priority: high  # high | medium | low
    
  - id: creaminess_claim
    label: "Creaminess claim"
    description: "Reaction to and believability of creaminess claim"
    priority: high
    
  - id: enzyme_technology
    label: "Enzyme process RTB"
    description: "Understanding and reaction to enzyme technology"
    priority: medium
    
  - id: no_thickeners_claim
    label: "No thickeners positioning"
    description: "Ingredient consciousness and clean label importance"
    priority: medium
    
  - id: scandinavian_origin
    label: "Geographic origin cue"
    description: "Perception of Scandinavian oats (quality, authenticity)"
    priority: low

# Default completion criteria (can be overridden at session creation)
completion:
  target_coverage: 0.8  # 80% of topics must be complete
  min_turns: 10
  max_turns: 25
```

### 5.2 Concept Schema (Graph-Driven Mode)

```yaml
# config/concepts/oat_milk_exploratory.yaml

# Metadata
id: oat_milk_exploratory
name: "Oat Milk Concept (Exploratory)"
created_date: "2026-01-22"

# Stimulus (what respondent sees/reads)
stimulus:
  format: text
  content: |
    Introducing a new oat-based milk alternative made with an 
    enzyme process that creates natural creaminess from 
    Scandinavian oats, without any added thickeners.

# NO topics section - themes will emerge from conversation

# Completion criteria for emergence mode
completion:
  min_turns: 15
  max_turns: 30
  theme_saturation_threshold: 0.05  # Stop when themes saturated
```

### 5.3 Coverage-Driven Scoring Configuration

```yaml
# config/scoring/coverage_driven.yaml

# Coverage-driven mode: prioritize systematic topic exploration

scorers:
  
  # HIGH PRIORITY: Ensure topics are covered
  topic_coverage:
    enabled: true
    weight: 1.2
    veto_threshold: 0.1
    params:
      first_mention_boost: 2.5  # Strong boost for uncovered topics
      priority_multipliers:
        high: 1.5
        medium: 1.0
        low: 0.5
      incomplete_boost: 1.8  # Boost topics mentioned but not deep
      exhaustion_penalty: 0.1  # After 3 attempts, move on
      exhaustion_threshold: 3
  
  # MEDIUM PRIORITY: Depth within current topic
  depth_within_topic:
    enabled: true
    weight: 1.0
    params:
      target_depth_per_topic: 0.7  # Aim for 70% depth per topic
      abstraction_scores:
        low: 0.1
        medium: 0.3
        medium_high: 0.5
        high: 0.7
        highest: 1.0
      terminal_bonus: 0.2
      diminishing_returns_after: 0.9  # Avoid over-exploration
  
  # MEDIUM PRIORITY: Saturation per topic
  topic_saturation:
    enabled: true
    weight: 1.1
    params:
      window_size: 3
      threshold: 0.05  # <5% new info = saturated
      saturated_penalty: 0.3  # Push to next topic when saturated
      unsaturated_boost: 1.2
  
  # LOW PRIORITY: Novelty (only when coverage satisfied)
  novelty:
    enabled: true
    weight: 0.6  # Downweighted in coverage mode
    params:
      recency_window: 3
      novel_boost: 1.5
      repetition_penalty: 0.5
  
  # UTILITY: Avoid redundancy
  redundancy:
    enabled: true
    weight: 1.0
    veto_threshold: 0.2
    params:
      recent_window: 5
      semantic_threshold: 0.85
      exact_match_penalty: 0.1
      similar_penalty: 0.4
  
  # UTILITY: Respond to engagement
  momentum_alignment:
    enabled: true
    weight: 0.9
    params:
      high_momentum_boost: 1.3
      low_momentum_penalty: 0.7
      disengaged_veto: 0.1

# Global arbitration settings
arbitration:
  min_applicable_strategies: 1
  score_precision: 4
  alternatives_count: 3
```

### 5.4 Graph-Driven Scoring Configuration

```yaml
# config/scoring/graph_driven.yaml

# Graph-driven mode: prioritize emergent discovery and natural flow

scorers:
  
  # NO topic_coverage scorer - no predetermined topics
  
  # HIGH PRIORITY: Follow novel branches
  novelty:
    enabled: true
    weight: 1.5  # Upweighted in graph mode
    params:
      recency_window: 5
      novel_boost: 2.0  # Strong preference for unexplored areas
      repetition_penalty: 0.4
      semantic_threshold: 0.85
  
  # HIGH PRIORITY: Depth on current thread
  depth_on_thread:
    enabled: true
    weight: 1.3
    params:
      continuation_boost: 1.8  # Prefer staying on thread
      switch_penalty: 0.5  # Penalize jumping around
      terminal_bonus: 0.3
      abstraction_scores:
        low: 0.1
        medium: 0.3
        medium_high: 0.5
        high: 0.7
        highest: 1.0
  
  # MEDIUM PRIORITY: Connect emerging themes
  emergent_connection:
    enabled: true
    weight: 1.2
    params:
      cross_theme_boost: 1.8  # Reward connecting themes
      surprise_factor_boost: 1.5  # Reward unexpected links
      isolated_node_priority: 1.4
  
  # MEDIUM PRIORITY: Theme saturation
  theme_saturation:
    enabled: true
    weight: 1.0
    params:
      auto_discover: true  # Automatically identify themes
      window_size: 5
      threshold: 0.05
      saturated_penalty: 0.4
      discovery_boost: 1.6  # Boost exploration of new themes
  
  # LOW PRIORITY: Safety net for major omissions
  safety_nudge:
    enabled: true
    weight: 0.3  # Very low weight
    params:
      # Only triggers if major stimulus element completely unmentioned
      # after many turns
      min_turns_before_nudge: 15
      major_omission_boost: 1.5
  
  # UTILITY: Avoid redundancy
  redundancy:
    enabled: true
    weight: 1.0
    veto_threshold: 0.2
    params:
      recent_window: 5
      semantic_threshold: 0.85
      exact_match_penalty: 0.1
  
  # UTILITY: Respond to engagement
  momentum_alignment:
    enabled: true
    weight: 1.0
    params:
      high_momentum_boost: 1.4
      low_momentum_penalty: 0.6
      disengaged_veto: 0.1

# Global arbitration settings
arbitration:
  min_applicable_strategies: 1
  score_precision: 4
  alternatives_count: 5  # More alternatives in exploratory mode
```

### 5.5 Coverage-Driven Strategy Configuration

```yaml
# config/strategies/coverage_driven.yaml

strategies:
  
  # HIGH PRIORITY: Cover uncovered topics
  cover_new_topic:
    name: "Cover New Topic"
    type_category: "coverage"
    priority: 1.0
    enabled: true
    
    applies_when:
      - "uncovered topics exist"
      - "current topic not active OR current topic saturated"
    
    focus_selection: "highest_priority_uncovered_topic"
    
    llm_guidance:
      system_prompt: |
        You are exploring a new topic from the concept.
        Topic: {topic_label}
        Description: {topic_description}
        
        Ask an open-ended question that:
        - Introduces the topic naturally
        - References the concept description
        - Encourages elaboration
      
      user_template: |
        Topic to explore: {topic_id}
        Priority: {topic_priority}
        Concept: {concept_description}
        Recent turns: {recent_context}
        
        Generate a natural question.
  
  # MEDIUM PRIORITY: Deepen current topic
  deepen_current_topic:
    name: "Deepen Current Topic"
    type_category: "depth"
    priority: 0.8
    enabled: true
    
    applies_when:
      - "current topic mentioned but depth < 0.7"
      - "current topic not saturated"
    
    focus_selection: "current_topic_deepest_node"
    
    llm_guidance:
      system_prompt: |
        You are exploring {topic_label} in depth.
        The respondent mentioned: {node_label}
        
        Ask a follow-up that:
        - Probes consequences or reasons (for MEC)
        - Asks for examples or elaboration
        - Moves toward higher abstraction
  
  # MEDIUM PRIORITY: Switch to incomplete topic
  switch_incomplete_topic:
    name: "Switch to Incomplete Topic"
    type_category: "coverage"
    priority: 0.7
    enabled: true
    
    applies_when:
      - "current topic saturated OR exhausted"
      - "other topics incomplete"
    
    focus_selection: "next_highest_priority_incomplete"
    
    llm_guidance:
      system_prompt: |
        You are transitioning to a new topic: {topic_label}
        
        Create a smooth transition that:
        - Acknowledges previous topic briefly
        - Introduces new topic naturally
        - Doesn't feel abrupt
  
  # LOW PRIORITY: Explore emergent theme (only when coverage satisfied)
  explore_emergent:
    name: "Explore Emergent Theme"
    type_category: "emergence"
    priority: 0.3
    enabled: true
    
    applies_when:
      - "coverage_ratio >= 0.8"
      - "respondent introduces novel concept"
    
    focus_selection: "novel_node_not_mapped_to_topic"
    
    llm_guidance:
      system_prompt: |
        The respondent mentioned something unexpected: {node_label}
        Coverage is satisfied, so you can explore this.
        
        Ask an open question about this emergent theme.
  
  # HIGH PRIORITY: Close interview
  close_interview:
    name: "Close Interview"
    type_category: "meta"
    priority: 1.0
    enabled: true
    
    applies_when:
      - "coverage_ratio >= 0.8"
      - "turn_count >= min_turns"
      - "all active topics saturated OR exhausted"
    
    llm_guidance:
      system_prompt: |
        The interview is complete.
        Generate a warm closing that:
        - Thanks the respondent
        - Summarizes key themes briefly
        - Asks if they have final thoughts
```

### 5.6 Graph-Driven Strategy Configuration

```yaml
# config/strategies/graph_driven.yaml

strategies:
  
  # HIGH PRIORITY: Follow novel branches
  follow_novel_branch:
    name: "Follow Novel Branch"
    type_category: "exploration"
    priority: 1.0
    enabled: true
    
    applies_when:
      - "novel nodes exist in graph"
      - "current thread not active OR current thread saturated"
    
    focus_selection: "most_novel_node"
    
    llm_guidance:
      system_prompt: |
        The respondent mentioned: {node_label}
        This is a new area they brought up.
        
        Ask an open-ended question that:
        - Explores this new concept
        - Lets them elaborate freely
        - Follows their train of thought
  
  # HIGH PRIORITY: Deepen current thread
  deepen_current_thread:
    name: "Deepen Current Thread"
    type_category: "depth"
    priority: 0.9
    enabled: true
    
    applies_when:
      - "current thread active"
      - "current thread not saturated"
      - "depth potential exists"
    
    focus_selection: "current_thread_head_node"
    
    llm_guidance:
      system_prompt: |
        Continue exploring: {node_label}
        
        Probe deeper by asking:
        - Why that matters to them
        - How it connects to other things
        - For concrete examples
  
  # MEDIUM PRIORITY: Connect themes
  connect_themes:
    name: "Connect Themes"
    type_category: "integration"
    priority: 0.7
    enabled: true
    
    applies_when:
      - "multiple themes identified"
      - "potential cross-theme connection exists"
    
    focus_selection: "node_from_theme_A_near_theme_B"
    
    llm_guidance:
      system_prompt: |
        The respondent has mentioned both:
        - Theme A: {theme_a_label}
        - Theme B: {theme_b_label}
        
        Ask how these connect or relate.
  
  # MEDIUM PRIORITY: Resolve ambiguity
  resolve_ambiguity:
    name: "Resolve Ambiguity"
    type_category: "validation"
    priority: 0.6
    enabled: true
    
    applies_when:
      - "ambiguous nodes exist"
    
    focus_selection: "most_ambiguous_node"
    
    llm_guidance:
      system_prompt: |
        The respondent said: {node_label}
        But it's unclear what they meant.
        
        Ask a clarifying question.
  
  # LOW PRIORITY: Gentle nudge for major omissions
  nudge_missing_area:
    name: "Nudge Missing Area"
    type_category: "safety"
    priority: 0.2
    enabled: true
    
    applies_when:
      - "turn_count >= 15"
      - "major stimulus element completely unmentioned"
    
    focus_selection: "major_unmentioned_stimulus_element"
    
    llm_guidance:
      system_prompt: |
        The concept mentioned: {element_description}
        The respondent hasn't brought this up at all.
        
        Gently ask about it:
        - "We haven't talked much about X..."
        - "What do you make of Y..."
  
  # HIGH PRIORITY: Close interview
  close_interview:
    name: "Close Interview"
    type_category: "meta"
    priority: 1.0
    enabled: true
    
    applies_when:
      - "all active themes saturated"
      - "turn_count >= min_turns"
      - "no novel branches for 5+ turns"
    
    llm_guidance:
      system_prompt: |
        The conversation has naturally concluded.
        Generate a warm closing.
```

---

## Part 6: Recommendations Summary

### 6.1 For MVP Development

**Recommendation:** Start with **Coverage-Driven (Position A)** as primary mode.

**Rationale:**
1. Matches stated use case (concept testing for marketing)
2. Stronger methodological precedent (semi-structured interviews)
3. Clearer success criteria (coverage %)
4. Stakeholder expectations (systematic evaluation)

**Architecture:** Implement dual-mode infrastructure from start (adds ~15% to initial development) to enable future experimentation.

### 6.2 Development Sequence

**Phase 1:** Core infrastructure (shared components)
- Graph models
- Extraction pipeline
- LLM integration
- Database layer

**Phase 2:** Coverage-driven mode (primary)
- CoverageState implementation
- Topic-based scorers
- Coverage-first strategies
- Concept YAML with topics

**Phase 3:** Graph-driven mode (experimental)
- EmergenceState implementation
- Novelty-first scorers
- Exploration-first strategies
- Theme discovery algorithms

**Phase 4:** Validation & tuning
- A/B testing framework
- Quality metrics comparison
- User preference studies

### 6.3 Documentation Strategy

**For users:**
- Clear explanation of two modes
- Guidance on which mode for which research goal
- Example concepts for each mode

**For developers:**
- Abstract InterviewState interface
- Mode-specific configuration examples
- Testing strategies for dual-mode system

### 6.4 Research Opportunities

**Empirical questions:**
1. Coverage-driven vs graph-driven: which produces richer graphs?
2. Same concept, both modes: do they reveal different insights?
3. Respondent experience: which mode feels more natural?
4. Analyst satisfaction: which outputs are more useful?

**Methodology:**
- Run parallel pilots (same concepts, both modes)
- Compare graph metrics (density, diversity, depth)
- Survey respondents and analysts
- Publish findings to establish methodological precedent

---

## Conclusion

The tension between coverage-driven and graph-driven interviewing reflects a fundamental divide in qualitative research methodology:
- **Structured** (predetermined agenda) vs. **Emergent** (follow the data)
- **Breadth-first** (ensure completeness) vs. **Depth-first** (follow interest)
- **Researcher-led** (systematic evaluation) vs. **Respondent-led** (natural exploration)

The good news: your architecture already supports both with ~85% shared code. The key is making the difference **explicit** through configuration and treating it as a **deliberate methodological choice** rather than trying to be both things simultaneously.

By implementing dual-mode support from the start, you create:
1. **Clear product positioning** ("Choose your interview style")
2. **Research opportunity** (empirically compare approaches)
3. **Future flexibility** (add hybrid modes based on learning)
4. **Methodological honesty** (acknowledge the tradeoffs)

The system should not be "coverage with natural feel" (incoherent) but rather "coverage mode OR exploration mode" (coherent, user's choice).
