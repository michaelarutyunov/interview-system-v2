# LLM Signals Architecture Design

**Status:** Design Proposal
**Epic:** `kf7s` - LLM Signals - Replace heuristics with real LLM analysis
**Author:** Design discussion with user
**Created:** 2025-02-11

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Architectural Tension](#architectural-tension)
3. [Design Options Considered](#design-options-considered)
4. [Recommended Design: Hybrid Pattern](#recommended-design-hybrid-pattern)
5. [Implementation Plan](#implementation-plan)
6. [Open Questions](#open-questions)

---

## Problem Statement

### Current State

The LLM signal pool (in `src/methodologies/signals/llm/`) currently uses **heuristic implementations** that mirror keyword-based formulas:

```python
# Current implementation (PoC heuristics)
class UncertaintySignal(BaseLLMSignal):
    async def _analyze_with_llm(self, response_text: str) -> dict:
        uncertainty_words = ["maybe", "perhaps", "possibly", "might", ...]
        uncertainty_count = sum(1 for w in uncertainty_words if w in text_lower.split())
        return {self.signal_name: uncertainty_count / max(word_count, 1)}
```

This has several issues:
1. **English-only**: Keyword lists lock the system to English language
2. ** brittle**: Doesn't capture semantic nuances (e.g., "I'm not entirely certain" vs "maybe")
3. **Not真正的 LLM analysis**: The signal is named after LLM analysis but uses heuristics

### Goal

Replace heuristics with **actual LLM-based semantic analysis** while:
- Supporting **multilingual** interviews (not English-keyword dependent)
- Maintaining **clean separation of concerns** between signal definition and detection
- Enabling **batch detection** (single LLM call for all signals) for cost/latency optimization
- Keeping signal classes **self-contained** (formula lives with signal)

---

## Architectural Tension

### Node Signals: Formula = Implementation

```python
class NodeExhaustedSignal(NodeSignalDetector):
    signal_name = "graph.node.exhausted"

    def _is_exhausted(self, state) -> bool:
        # Formula AND implementation are ONE thing
        if state.focus_count == 0: return False
        if state.turns_since_last_yield < 3: return False
        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        return shallow_ratio >= 0.66
```

For node signals, the "formula" (the logic) and the "implementation" (how it's applied) are **tightly coupled** in the same method. No separation needed.

### LLM Signals: Prompt ≠ Call

```
Prompt (formula)           │  LLM call (implementation)
───────────────────────────┼─────────────────────────────
"What constitutes hedging? │  - Shared across signals
 How to score 0-1?"        │  - Batching optimization
                          │  - JSON parsing
                          │  - Error handling
                          │  - LLM client management
```

For LLM signals:
- The **prompt** IS the formula (what we want computed)
- The **LLM call** is the implementation (how we get the result)
- **Batch detection** means multiple signals share one LLM call

**Question:** How do we keep signals self-contained while sharing the batch LLM call?

---

## Design Options Considered

### Option 1: Extractor Pattern

Each signal provides prompt spec and knows how to extract its value from batch result.

```python
class ResponseDepthSignal(BaseLLMSignal):
    @classmethod
    def get_prompt_spec(cls) -> str:
        return "## Response Depth\n- surface: ...\n- moderate: ...\n- deep: ..."

    @classmethod
    def extract_from_batch_result(cls, batch_result: dict) -> dict:
        return {cls.signal_name: batch_result[cls.signal_name]}
```

**Pros:**
- Signals own their prompt spec (formula)
- Signals own their extraction logic
- Batch detector is pure orchestration

**Cons:**
- More complex (3-way collaboration)
- Batch detector needs to know all signal classes upfront

---

### Option 2: Service Pattern

Service owns all prompts and makes batch calls. Signals are lightweight extraction wrappers.

```python
class LLMSignalService:
    @staticmethod
    def get_system_prompt() -> str:
        return """## Response Depth\n[spec]\n## Sentiment\n[spec]..."""

    async def detect_all(self, response_text: str) -> dict:
        # Single LLM call

class ResponseDepthSignal(BaseLLMSignal):
    async def detect(self, context, graph_state, response_text):
        batch_result = await LLMSignalService().detect_all(response_text)
        return {self.signal_name: batch_result[self.signal_name]}
```

**Pros:**
- Simple signal classes
- All prompts in one file (easy to edit)
- Clear ownership: Service owns LLM concern

**Cons:**
- Signal doesn't own its prompt (formula separate from signal)
- Service becomes god class
- Tight coupling: signal needs to know service

---

### Option 3: Spec Object Pattern

Separate spec objects from signal implementations.

```python
class ResponseDepthSignalSpec:
    signal_name = "llm.response_depth"
    @staticmethod
    def get_prompt_instructions() -> str: ...
    @staticmethod
    def get_output_schema() -> dict: ...

class ResponseDepthSignal(BaseLLMSignal):
    spec = ResponseDepthSignalSpec
```

**Pros:**
- Clean separation: spec vs implementation
- Specs can be reused elsewhere

**Cons:**
- More files (spec + signal for each)
- Verbose - lots of boilerplate

---

### Option 4: Hybrid Pattern (RECOMMENDED)

Signal provides prompt spec via class methods. Base class handles batch orchestration. Auto-registration via `__init_subclass__`.

```python
# Base class provides infrastructure
class BaseLLMSignal(SignalDetector):
    _signal_registry: dict[str, type["BaseLLMSignal"]] = {}

    def __init_subclass__(cls) -> None:
        if hasattr(cls, 'signal_name'):
            cls._signal_registry[cls.signal_name] = cls

    @classmethod
    def _get_prompt_spec(cls) -> str:
        raise NotImplementedError

    @classmethod
    def _get_output_schema(cls) -> dict:
        raise NotImplementedError

    async def detect(self, context, graph_state, response_text):
        detector = self._get_batch_detector()
        batch_result = await detector.detect(response_text)
        return {self.signal_name: batch_result.get(self.signal_name)}

# Signal provides spec
class ResponseDepthSignal(BaseLLMSignal):
    signal_name = "llm.response_depth"

    @classmethod
    def _get_prompt_spec(cls) -> str:
        return "## Response Depth\n..."  # Signal's formula

    @classmethod
    def _get_output_schema(cls) -> dict:
        return {"type": "string", "enum": ["surface", "moderate", "deep"]}
```

**Pros:**
- ✅ Signal owns its formula (`_get_prompt_spec()`)
- ✅ Batch detection centralized in base class
- ✅ Auto-registration via `__init_subclass__`
- ✅ Signals are self-contained files
- ✅ Clean separation: WHAT (spec) vs HOW (LLM call)

**Cons:**
- More complex base class
- Relies on Python magic (`__init_subclass__`)

---

## Recommended Design: Hybrid Pattern

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SIGNAL CLASSES                                 │
│  (Self-contained: name + description + prompt spec + schema)            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ResponseDepthSignal          SentimentSignal          UncertaintySignal │
│  ├─ signal_name               ├─ signal_name           ├─ signal_name    │
│  ├─ description               ├─ description           ├─ description    │
│  ├─ _get_prompt_spec()        ├─ _get_prompt_spec()    ├─ _get_prompt_spec() │
│  └─ _get_output_schema()      └─ _get_output_schema()  └─ _get_output_schema() │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ inherits
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BaseLLMSignal                                    │
│  (Infrastructure: batch detection orchestration)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  • _signal_registry (auto-populated via __init_subclass__)              │
│  • detect() → orchestrates via batch detector                          │
│  • _get_batch_detector() → creates/reuses LLMBatchDetector             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ uses
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LLMBatchDetector                                 │
│  (Orchestrator: single LLM call for all signals)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  • __init__(signal_classes)                                            │
│  • detect(response_text) → dict with all signal values                 │
│  • _build_system_prompt() → assembles from signal specs                │
│  • _parse_response() → robust JSON parsing                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
src/methodologies/signals/llm/
├── __init__.py                    # Exports all signal classes
├── llm_signal_base.py             # BaseLLMSignal with batch detection
├── llm_batch_detector.py          # LLMBatchDetector orchestrator
├── depth.py                       # ResponseDepthSignal
├── quality.py                     # SentimentSignal, UncertaintySignal, AmbiguitySignal
└── hedging_language.py            # HedgingLanguageSignal

src/llm/prompts/
└── llm_signals.py                 # Optional: shared prompt constants, examples
```

### Key Design Decisions

#### 1. Signal Self-Containment

Each signal file contains:
- `signal_name`: Namespaced identifier
- `description`: Human-readable explanation
- `_get_prompt_spec()`: The "formula" - what to analyze and how
- `_get_output_schema()`: Expected output structure

This makes signals **self-documenting** and **easy to modify**.

#### 2. Batch Detection Transparency

From the signal author's perspective, batch detection is transparent:
```python
async def detect(self, context, graph_state, response_text):
    detector = self._get_batch_detector()  # Handled by base class
    batch_result = await detector.detect(response_text)
    return {self.signal_name: batch_result.get(self.signal_name)}
```

The base class handles:
- Collecting all registered signals
- Building the combined prompt
- Making the single LLM call
- Parsing and distributing results

#### 3. Auto-Registration

Using `__init_subclass__` ensures all LLM signals are automatically discovered:
```python
def __init_subclass__(cls) -> None:
    if hasattr(cls, 'signal_name'):
        cls._signal_registry[cls.signal_name] = cls
```

When `ResponseDepthSignal` is defined, it's automatically added to the registry. No manual registration needed.

---

## Prompt Design Strategy

### Rejection of Keyword-Based Prompts

**Problem:** Current examples use English keyword lists:
```
- Positive: "love", "like", "great", "good", ...
- Uncertainty: "maybe", "perhaps", "possibly", ...
```

This locks the system to English and fails for semantic equivalents.

### Alternative: Semantic Description + Scoring

Instead of keywords, use **semantic descriptions** and ask LLM to score based on meaning:

```python
@classmethod
def _get_prompt_spec(cls) -> str:
    return """
## Response Depth (llm.response_depth)

Assess the elaboration level of the response based on semantic content:

**surface** (1/10):
- Brief statement without elaboration
- Single concept mentioned, no connections
- No examples or reasoning provided
- Direct answer to question with minimal detail

**moderate** (5/10):
- Some elaboration provided
- May include 1-2 examples or brief explanation
- Concepts connected with simple relationships
- Respondent provides more than yes/no but not extensive

**deep** (10/10):
- Substantial elaboration with reasoning
- Multiple examples or detailed explanation
- Complex relationships between concepts articulated
- Respondent explains WHY or HOW, not just WHAT
- May include abstractions, principles, or nuanced distinctions

Score the response 1-10 and map to category:
- 1-3: "surface"
- 4-7: "moderate"
- 8-10: "deep"
"""
```

This approach:
- ✅ Works in any language (LLM understands semantic meaning)
- ✅ Captures nuance (not binary keyword matching)
- ✅ Allows for gray areas (scoring 1-10, then mapping)

### Structured Output Format

The prompt always specifies the exact output format:

```python
@classmethod
def _get_output_schema(cls) -> dict:
    return {
        "type": "string",
        "enum": ["surface", "moderate", "deep"],
        "description": "Response elaboration level based on semantic content analysis"
    }
```

The batch detector combines all schemas into a single JSON schema for the LLM.

---

## Implementation Plan

### Phase 1: Infrastructure (Bead mrmn)

1. **Create `llm_signal_base.py`**
   - `BaseLLMSignal` with `_signal_registry`
   - `__init_subclass__` auto-registration
   - `_get_batch_detector()` class method
   - Abstract methods: `_get_prompt_spec()`, `_get_output_schema()`

2. **Create `llm_batch_detector.py`**
   - `LLMBatchDetector` class
   - `detect()` method for single LLM call
   - `_build_system_prompt()` assembles from signal specs
   - `_parse_response()` with robust JSON handling

3. **Refactor existing signals**
   - Update `ResponseDepthSignal`, `SentimentSignal`, etc.
   - Replace `_analyze_with_llm()` with `_get_prompt_spec()`
   - Add `_get_output_schema()` class methods
   - Implement semantic (non-keyword) prompt specs

### Phase 2: Signal Enhancement

4. **Rewrite prompts with semantic descriptions**
   - Remove English keyword lists
   - Use scoring-based approaches (1-10 → category mapping)
   - Add examples for clarity (can be multilingual)

5. **Add validation and testing**
   - Test with non-English responses
   - Compare LLM results vs heuristics
   - Measure latency/quality tradeoff

### Phase 3: Integration

6. **Update signal registry**
   - Ensure LLM signals work with existing `MethodologyStrategyService`
   - No changes to YAML config needed (signals already registered)

7. **Documentation**
   - Update `docs/pipeline_contracts.md`
   - Document LLM signal pattern for future signal authors

---

## Open Questions

1. **Scoring granularity**: Should signals output raw scores (1-10) or mapped categories? Currently using categories for compatibility with existing YAML configs.

2. **Multilingual validation**: How do we validate that LLM signals work correctly in languages other than English? Need multilingual test cases.

3. **Prompt versioning**: Prompts may evolve. Should we track prompt versions in signal metadata for observability?

4. **Fallback behavior**: If LLM call fails, should we fall back to heuristics or fail fast? Current bias: fail fast (ADR-009).

5. **Cost monitoring**: Need to track token usage and latency for batch vs individual calls to validate optimization.

---

## References

- ADR-009: Fail-Fast Error Handling (MVP)
- ADR-010: Three-Client LLM Architecture
- ADR-014: Signal Pools Architecture
- `docs/pipeline_contracts.md`: Stage contracts
- `docs/data_flow_paths.md`: Data flow through pipeline

---

---

## LLM Signal Specifications

### Signal Boundaries and Distinctions

To ensure signals are orthogonal and capture distinct aspects of responses:

| Signal | Measures | Key Question | Independent From |
|--------|----------|--------------|------------------|
| **ResponseDepth** | Elaboration quantity | HOW MUCH detail is provided? | Sentiment, certainty, specificity |
| **Sentiment** | Emotional tone | What is the attitude? | Depth, certainty, specificity |
| **Uncertainty** | Epistemic confidence | How certain is the respondent in their KNOWLEDGE? | Sentiment, depth, hedging (distinct) |
| **Ambiguity** | Referential specificity | How precise/concrete is the language? | Sentiment, certainty, elaboration |
| **HedgingLanguage** | Linguistic softening | How much does the respondent soften their statements? | Knowledge certainty (distinct), sentiment |

**Key Distinctions:**
- **Uncertainty ≠ Hedging**: Uncertainty is about knowledge state ("I don't know"). Hedging is about communication style ("kind of", "somewhat"). You can be certain but still hedge, or uncertain without hedging.
- **Ambiguity ≠ Depth**: Depth measures elaboration quantity. Ambiguity measures specificity. You can provide extensive vague detail (deep but ambiguous) or brief precise detail (shallow but unambiguous).
- **Sentiment** is orthogonal to all other signals - any emotional tone can coexist with any depth, certainty, specificity, or hedging level.

---

### Signal 1: ResponseDepthSignal

```python
class ResponseDepthSignal(BaseLLMSignal):
    signal_name = "llm.response_depth"
    description = "Assesses the quantity of elaboration in the response - how much detail, reasoning, and examples are provided, independent of content or sentiment. Output: 1-5 integer scale."

    @classmethod
    def _get_prompt_spec(cls) -> str:
        return """
## Response Depth (llm.response_depth)

**Your task:** Assess how much elaboration the respondent provided on a 1-5 scale.

Focus on the QUANTITY of elaboration, not the quality or correctness.
This signal measures HOW MUCH was said, not WHAT was said or HOW it was said.

**Evaluation criteria:**
1. Does the response explain WHY or just state WHAT?
2. Are examples or details provided?
3. Does the respondent connect concepts or just list them?
4. Is there reasoning, assertion, or both?

**Depth scale (1-5):**

**1 - Minimal elaboration (surface):**
- Direct answer without explanation
- No examples provided
- Single concept mentioned, no connections
- Typical of yes/no or brief factual statements

**2 - Little elaboration:**
- Brief statement with minimal detail
- Maybe 1 example mentioned but not explained
- Concepts listed but not connected
- Slightly more than "yes/no" but still shallow

**3 - Moderate elaboration:**
- Brief explanation or 1-2 examples included
- Some connection between ideas expressed
- Respondent provides more than one-word answer
- May include simple reasoning or basic clarification

**4 - Substantial elaboration:**
- Clear explanation with reasoning
- 2-3 examples or detailed points
- Concepts are connected thoughtfully
- Respondent explains WHY or HOW to some extent
- Good elaboration but not exhaustive

**5 - Extensive elaboration (deep):**
- Substantial reasoning or explanation provided
- Multiple examples or detailed explanation
- Complex relationships between concepts articulated
- Respondent explains WHY and HOW thoroughly
- May include abstractions, principles, nuanced distinctions, or causal chains

**Important:**
- Evaluate based on semantic content in ANY language
- Do not count words - assess elaboration quality
- Use the full 1-5 range, don't default to 3
- A long repetitive response is not "5" - look for substantive elaboration
- A short insightful response can be "5" if it explains reasoning well

**Output:** Integer 1-5
"""

    @classmethod
    def _get_output_schema(cls) -> dict:
        return {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Elaboration level: 1=minimal/surface, 3=moderate, 5=extensive/deep"
        }
```

---

### Signal 2: SentimentSignal

```python
class SentimentSignal(BaseLLMSignal):
    signal_name = "llm.sentiment"
    description = "Assesses the emotional tone of the response - favorable or unfavorable attitude. Independent of depth, certainty, or specificity. Output: 1-5 integer scale."

    @classmethod
    def _get_prompt_spec(cls) -> str:
        return """
## Sentiment (llm.sentiment)

**Your task:** Assess the emotional tone or attitude of the response on a 1-5 scale.

Focus on the respondent's attitude, not the content.
This signal measures HOW THE RESPONDENT FEELS, not what they know or how much they say.

**Evaluation criteria:**
1. Does the language indicate favorable or unfavorable attitude?
2. Is there enthusiasm, interest, engagement (positive)?
3. Is there dislike, skepticism, discomfort (negative)?
4. Is the tone neutral/factual without emotional coloring?

**Sentiment scale (1-5):**

**1 - Very negative:**
- Strong dislike, disapproval, or hostility expressed
- Clear aversion, resistance, or rejection
- Negative emotional language is prominent
- Respondent appears strongly negatively disposed

**2 - Somewhat negative:**
- Dislike, skepticism, doubt, or discomfort expressed
- Lack of enthusiasm or engagement
- Unfavorable attitude but not strongly hostile
- Hesitation or reluctance evident

**3 - Neutral:**
- Factual, informational tone
- Neither favorable nor unfavorable attitude
- Calm, objective expression without emotional coloring
- Respondent is simply providing information

**4 - Somewhat positive:**
- Mild enthusiasm, interest, or engagement
- Expressions of liking or preference (not strong)
- Generally favorable attitude
- Respondent appears positively inclined but not excited

**5 - Very positive:**
- Strong enthusiasm, interest, or engagement expressed
- Clear expressions of liking, enjoyment, or approval
- Energy and warmth in language
- Respondent appears strongly positively disposed

**Important:**
- Evaluate based on semantic content in ANY language
- Do not look for specific words - assess the overall attitude
- Short responses can still have clear sentiment
- A factual statement about something disliked is "negative" sentiment
- Use the full 1-5 range, don't default to 3

**Output:** Integer 1-5
"""

    @classmethod
    def _get_output_schema(cls) -> dict:
        return {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Emotional tone: 1=very negative, 3=neutral, 5=very positive"
        }
```

---

### Signal 3: UncertaintySignal

```python
class UncertaintySignal(BaseLLMSignal):
    signal_name = "llm.uncertainty"
    description = "Assesses epistemic confidence - how certain the respondent is in their knowledge. DISTINCT from hedging: uncertainty is about KNOWLEDGE STATE, not communication style. Output: 1-5 integer scale."

    @classmethod
    def _get_prompt_spec(cls) -> str:
        return """
## Uncertainty (llm.uncertainty)

**Your task:** Assess how certain or confident the respondent is in their knowledge on a 1-5 scale.

Focus on EPISTEMIC CERTAINTY - what the respondent KNOWS.
This signal measures confidence in KNOWLEDGE, not how it's expressed.

**Critical distinction:** Uncertainty ≠ Hedging
- Uncertainty: "I don't know if this is true" (knowledge state)
- Hedging: "This is kind of true" (communication style, may be fully confident)
- You can be uncertain without hedging: "I'm not sure"
- You can hedge while being certain: "It's kind of expensive" (you know the price, just softening)

**Evaluation criteria:**
1. Does the respondent express doubt about what they know?
2. Are there knowledge gaps acknowledged?
3. Is the respondent confident or tentative in their assertions?
4. Are probabilistic expressions about knowledge used?

**Uncertainty scale (1-5):**

**1 - Very Confident:**
- Declarative statements without qualification of knowledge
- Direct assertions: "X is true", "I know that X"
- No expressions of doubt or lack of knowledge
- Respondent speaks with certainty about their knowledge

**2 - Somewhat Confident:**
- Mostly confident, occasional mild qualification
- May express "general" or "typical" knowledge
- Qualified assertions but overall confident in what they know

**3 - Mixed Certainty:**
- Mix of confident and uncertain statements
- Some knowledge claims are qualified
- Respondent shows some confidence but also acknowledges limits

**4 - Uncertain:**
- Explicit expressions of doubt about knowledge
- Phrases indicating lack of knowledge: "I'm not sure", "I don't know"
- Acknowledges limits of what they know
- Probabilistic knowledge claims: "probably", "might be", "could be"

**5 - Very Uncertain:**
- Extensive expressions of not knowing
- Multiple uncertainty markers about knowledge in single response
- Respondent appears to have little knowledge on the topic
- Language suggesting complete lack of knowledge or understanding

**Important:**
- Evaluate based on semantic content in ANY language
- Focus on KNOWLEDGE certainty, not linguistic softening
- "I don't know" = high uncertainty (5); "It's kind of..." = NOT uncertainty (that's hedging)
- Use the full 1-5 range, don't default to 3

**Output:** Integer 1-5
"""

    @classmethod
    def _get_output_schema(cls) -> dict:
        return {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Epistemic uncertainty: 1=very confident in knowledge, 5=very uncertain"
        }
```

---

### Signal 4: AmbiguitySignal

```python
class AmbiguitySignal(BaseLLMSignal):
    signal_name = "llm.ambiguity"
    description = "Assesses referential specificity - how precise or vague the language is. DISTINCT from depth: ambiguity measures specificity, not elaboration quantity. Output: 1-5 integer scale."

    @classmethod
    def _get_prompt_spec(cls) -> str:
        return """
## Ambiguity (llm.ambiguity)

**Your task:** Assess how specific or vague the response is on a 1-5 scale.

Focus on REFERENTIAL SPECIFICITY - how precisely the respondent refers to things.
This signal measures CLARITY OF REFERENCE, not how much is said.

**Critical distinction:** Ambiguity ≠ Depth
- Depth: HOW MUCH elaboration (quantity of detail)
- Ambiguity: HOW PRECISE the references (specificity)
- You can have deep but ambiguous: lots of vague, unclear detail
- You can have shallow but unambiguous: brief, precise reference

**Evaluation criteria:**
1. Are concepts named specifically or referred to vaguely?
2. Could a reader/listener identify exactly what is being discussed?
3. Are concrete details provided or vague generalities?
4. Are there undefined pronouns or placeholders?

**Ambiguity scale (1-5):**

**1 - Very Specific:**
- Concrete, tangible concepts are named explicitly
- Specific details provided (names, numbers, clear descriptions)
- No vague or undefined references
- Clear exactly what is being discussed
- No reliance on pronouns without antecedents

**2 - Somewhat Specific:**
- Mostly specific with occasional vague elements
- Some generalizations but context provides clarity
- Generally clear references with 1-2 ambiguous terms

**3 - Mixed Specificity:**
- Mix of specific and vague language
- Some concepts named specifically, others vaguely
- Context helps but some references remain unclear

**4 - Somewhat Ambiguous:**
- Frequent use of vague pronouns: "it", "that", "this thing"
- Non-specific references: "something", "anything", "stuff", "things"
- Generalizations without specific examples
- Reader/listener would struggle to know exactly what is meant without context

**5 - Highly Ambiguous:**
- Dominated by vague, non-specific language
- Multiple undefined references
- Respondent speaks in generalities without specifics
- Very difficult to determine exactly what is being discussed

**Important:**
- Evaluate based on semantic content in ANY language
- Focus on reference clarity, not word choice
- A response can be long (deep) but highly ambiguous
- Technical jargon is NOT ambiguous if it precisely names concepts
- Use the full 1-5 range, don't default to 3

**Output:** Integer 1-5
"""

    @classmethod
    def _get_output_schema(cls) -> dict:
        return {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Referential ambiguity: 1=very specific, 5=highly ambiguous"
        }
```

---

### Signal 5: HedgingLanguageSignal

```python
class HedgingLanguageSignal(BaseLLMSignal):
    signal_name = "llm.hedging_language"
    description = "Assesses linguistic softening - qualifiers that reduce commitment. DISTINCT from uncertainty: hedging is communication style, not knowledge state. Output: 1-5 integer scale."

    @classmethod
    def _get_prompt_spec(cls) -> str:
        return """
## Hedging Language (llm.hedging_language)

**Your task:** Assess the extent of linguistic softening in the response on a 1-5 scale.

Focus on COMMUNICATION STYLE - how the respondent qualifies their statements.
This signal measures LINGUISTIC SOFTENING, not what the respondent knows.

**Critical distinction:** Hedging ≠ Uncertainty
- Hedging: Softening commitment in HOW something is said
- Uncertainty: Doubt about WHAT is known
- "It's kind of expensive" = hedging (respondent knows the price, just softening)
- "I'm not sure of the price" = uncertainty (knowledge gap, not hedging)

**What is hedging?**
Hedging is linguistic softening that reduces the strength or commitment of a statement.
It's about HOW something is communicated, not whether the communicator knows it to be true.

**Semantic indicators (language-agnostic):**
- Intensity modifiers: "quite", "rather", "relatively", "somewhat", "a bit"
- Approximations: "around", "approximately", "roughly", "about"
- Attribution to opinion: "I think", "I feel", "in my opinion", "from my perspective"
- Probability/possibility: "probably", "likely", "possibly", "may be"
- Tentative constructions: "kind of", "sort of", "type of"

**Hedging intensity scale (1-5):**

**1 - No Hedging:**
- Direct, unqualified statements
- No linguistic softening
- Clear, assertive language
- Respondent speaks without modifiers or qualifiers

**2 - Light Hedging:**
- Occasional mild qualifiers or softeners (1-2 instances)
- Some approximation or opinion attribution
- Mostly direct language with occasional softening

**3 - Moderate Hedging:**
- Noticeable use of qualifiers and softeners (3-4 instances)
- Many statements are qualified or tentative
- Respondent noticeably softens their language

**4 - Heavy Hedging:**
- Frequent use of qualifiers and softeners (5+ instances)
- Most statements are qualified or tentative
- Respondent consistently softens their language

**5 - Very Heavy Hedging:**
- Dominated by hedging and softening language
- Most statements are heavily qualified
- Respondent rarely makes direct, unqualified assertions

**Important:**
- Evaluate based on semantic content in ANY language
- Focus on linguistic softening, NOT knowledge certainty
- "I think" with a strong assertion = hedging, not uncertainty
- "I don't know" = uncertainty, NOT hedging
- Use the full 1-5 range, don't default to 3

**Output:** Integer 1-5
"""

    @classmethod
    def _get_output_schema(cls) -> dict:
        return {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Hedging intensity: 1=none, 3=moderate, 5=very heavy"
        }
```

---

### Summary Table

| Signal | Type | Range | Measures | Distinct From |
|--------|------|-------|----------|---------------|
| `llm.response_depth` | Integer | 1-5 | Elaboration quantity (1=surface, 5=deep) | Sentiment, certainty, specificity |
| `llm.sentiment` | Integer | 1-5 | Emotional tone (1=very negative, 5=very positive) | Depth, knowledge, style |
| `llm.uncertainty` | Integer | 1-5 | Epistemic confidence (1=very confident, 5=very uncertain) | Hedging (communication style), sentiment |
| `llm.ambiguity` | Integer | 1-5 | Referential specificity (1=very specific, 5=very ambiguous) | Depth (elaboration quantity), certainty |
| `llm.hedging_language` | Integer | 1-5 | Linguistic softening (1=none, 5=heavy) | Uncertainty (knowledge state), sentiment |

---

## Appendix A: Prompt Design Strategies - Rejected Options

### Strategy 1: Keyword-Based Lists (REJECTED)

**Description:** Provide lists of English keywords for each signal category.
```
Positive: "love", "like", "great", "good", "enjoy"
Uncertainty: "maybe", "perhaps", "possibly", "might"
```

**Reason for rejection:**
- English-only - fails for non-English responses
- Brittle - doesn't capture semantic equivalents or phrases
- Not真正的 LLM analysis - just keyword counting dressed up as LLM
- Misses nuance - "I'm not entirely certain" ≠ "maybe" but both express uncertainty

---

### Strategy 2: True/False + Score (CONSIDERED, NOT PRIMARY)

**Description:** First ask if the signal is present, then score intensity.
```
1. Is hedging present? (true/false)
2. If true, score 0-1 based on prevalence
```

**Reason for secondary preference:**
- Adds complexity to prompt without significant benefit
- Direct scoring rubric is clearer and more efficient
- Binary presence is often a gradient anyway - score captures it better

---

### Strategy 3: Multilingual Examples (SUPPLEMENTARY, NOT PRIMARY)

**Description:** Provide examples in multiple languages to guide the LLM.
```
| English | Spanish | French | German |
| "I love" | "Me encanta" | "J'adore" | "Ich liebe" |
```

**Reason for supplementary use only:**
- Can be helpful for disambiguation
- But relies on examples which the LLM might overfit to
- Semantic description is more robust and language-agnostic
- Examples should illustrate the principle, not define the pattern

---

### Selected Strategy: Semantic Description + Scoring Rubric

**Why this approach:**
- ✅ Language-agnostic - describes the CONCEPT, not keywords
- ✅ Captures nuance - allows for gray areas in scoring
- ✅ Leverages LLM understanding - trusts the LLM to detect semantics
- ✅ Clear boundaries - each signal has distinct focus area
- ✅ Testable - can validate across languages without keyword matching

---

## Appendix B: Comparison Matrix

| Aspect | Option 1: Extractor | Option 2: Service | Option 3: Spec Object | Option 4: Hybrid ✓ |
|--------|---------------------|-------------------|----------------------|-------------------|
| Signal owns prompt | ✅ Yes (method) | ❌ No (service) | ✅ Yes (separate obj) | ✅ Yes (method) |
| Batch detection | ✅ Separate class | ✅ Service | ✅ Separate class | ✅ Base class |
| Signal file complexity | Medium | Simple | High (2 files) | Medium |
| Formula-implementation coupling | ✅ Clean | ❌ Separated | ⚠️ Over-separated | ✅ Clean |
| Auto-discovery | ❌ Manual | ❌ Manual | ❌ Manual | ✅ `__init_subclass__` |
| Files per signal | 1 | 1 | 2 | 1 |
| Output format | ✅ 5-point scale | ✅ 5-point scale | ✅ 5-point scale | ✅ 5-point scale |
| Multilingual support | ✅ Semantic prompts | ✅ Semantic prompts | ✅ Semantic prompts | ✅ Semantic prompts |

---

## Appendix C: Critical Review and Recommendations

**Reviewer:** Claude Code (Opus 4.6)
**Date:** 2025-02-11
**Scope:** Analysis of proposed Hybrid Pattern against existing codebase infrastructure

---

### What Works Well

**1. Prompt Design Strategy is Excellent**

The rejection of keyword-based prompts in favor of semantic description + scoring rubrics is the single most important decision in this document. The prompt specs (Appendix signals 1-5) are well-crafted:
- Language-agnostic by design
- Clear scoring rubrics with concrete behavioral anchors
- Explicit boundary statements between similar signals (uncertainty ≠ hedging, ambiguity ≠ depth)

**2. Signal Orthogonality is Well-Reasoned**

The Signal Boundaries table (Section "Signal Specifications") correctly identifies the key confusion pairs and provides clear distinctions. This prevents the common mistake of overlapping signals that inflate each other.

**3. Self-Contained Signal Files**

Having each signal own its prompt spec via `_get_prompt_spec()` keeps the "formula" colocated with the signal — important for maintainability. When someone changes the hedging rubric, they change it in `hedging_language.py`, not in a distant prompt file.

**4. `__init_subclass__` Auto-Registration**

This eliminates a class of bugs where someone creates a signal but forgets to register it. However, see Issue #4 below for a conflict.

---

### Critical Issues

#### Issue #1: Unused Qualitative Signal Prompt Scaffolding

**Severity: Low — Design overlap, not runtime conflict**

The codebase contains prompt templates for a qualitative signal extraction system that was **designed but never implemented**:

```
src/llm/prompts/qualitative_signals.py  →  Prompt templates only (no consumer class)
```

`QualitativeSignalExtractor` appears in ADR-010 and the Phase 2.2 spec as a planned class, but **no actual implementation exists** — only the prompt functions (`get_qualitative_signals_system_prompt()`, `parse_qualitative_signals_response()`). The prompts define 6 rich signals:

| Qualitative Signal Prompt | Overlaps With Proposed Signal |
|---|---|
| `uncertainty_signal` (knowledge_gap, epistemic_humility, apathy) | `llm.uncertainty` |
| `emotional_signal` (high_positive → high_negative) | `llm.sentiment` |
| `concept_depth_signal` (abstraction_level 0-1, suggestion) | `llm.response_depth` |
| `reasoning_signal` (causal, counterfactual, associative) | No direct overlap |
| `contradiction_signal` (stance reversal, inconsistent detail) | No direct overlap |
| `knowledge_ceiling_signal` (terminal, exploratory) | No direct overlap |

Since these prompts are unused scaffolding, the new LLM signal system **replaces this intent entirely**. The unused prompt templates can be archived or deleted during implementation.

**Note:** The qualitative prompts were designed for **multi-turn analysis** (last 3-5 turns), while the proposed LLM signals analyze a **single response**. The `reasoning_signal`, `contradiction_signal`, and `knowledge_ceiling_signal` have no proposed replacements and are inherently multi-turn. These could be added as future LLM signals if needed, or implemented separately as a multi-turn analysis pass.

---

#### Issue #2: Output Type Breaking Change for Hedging

**Severity: High — Breaks all 5 methodology YAMLs**

The design proposes changing `llm.hedging_language` output from **categorical** (`none`/`low`/`medium`/`high`) to **float** (`0.0-1.0`).

All methodology YAML configs currently use compound keys that depend on categorical matching:

```yaml
# means_end_chain.yaml, jobs_to_be_done.yaml, etc.
signal_weights:
  llm.hedging_language.high: 1.0    # Matches when value == "high"
  llm.hedging_language.medium: 0.7  # Matches when value == "medium"
```

The scoring engine (`src/methodologies/scoring.py:_get_signal_value()`) handles this via compound key matching:

```python
# "llm.hedging_language.high" → checks if signals["llm.hedging_language"] == "high"
# This breaks when the value is 0.85 instead of "high"
```

If `llm.hedging_language` becomes a float, the YAML weights must change to:

```yaml
signal_weights:
  llm.hedging_language: 0.7  # Direct numeric multiplication
```

This changes the **scoring semantics** (from "if high, add 1.0" to "multiply 0.7 by hedging_score") and requires retuning all 5 methodology configs.

**Updated Recommendation:** Move **all signals to float outputs** (0.0-1.0). The argument for floats is compelling: float signals enable **trajectory tracking over time** — by accumulating per-response float values, `GlobalResponseTrendSignal` (and future trend signals) can compute meaningful running averages, deltas, and slopes. Categorical signals lose this granularity — you can't meaningfully average "medium" and "high".

This requires a **YAML migration** for signals currently using compound keys:

```yaml
# BEFORE (categorical compound key):
signal_weights:
  llm.hedging_language.high: 1.0    # Boolean match: value == "high"
  llm.hedging_language.medium: 0.7

# AFTER (direct float multiplication):
signal_weights:
  llm.hedging_language: 0.8         # weight * hedging_score (0.0-1.0)
```

**Migration scope:**
- `llm.hedging_language` — currently categorical in YAMLs (`means_end_chain`, `jobs_to_be_done`). Must migrate compound keys.
- `llm.response_depth` — currently categorical in YAMLs (`.surface`, `.moderate`, `.deep`). Must migrate compound keys.
- `llm.sentiment` — currently categorical in YAMLs (`.positive`, `.neutral`, `.negative`). Must migrate compound keys.
- `llm.uncertainty` — **already used as float** in YAMLs (`llm.uncertainty: 0.4`). No migration needed.
- `llm.ambiguity` — not currently in any YAML signal_weights. No migration needed.

**For `llm.response_depth` and `llm.sentiment`:** These are currently categorical signals where strategies trigger on specific values (e.g., "if depth is surface, prefer deepen strategy"). Converting to float changes the scoring semantics from "if-then" to "proportional weighting." This is a better model — a depth score of 0.3 should contribute more than 0.1, not be treated identically as "surface."

**`GlobalResponseTrendSignal` impact:** Currently depends on categorical depth values. Must be updated to work with float values (e.g., track running average of depth scores instead of counting "deep" vs "shallow" categories). This is straightforward and produces a better trend signal.

---

#### Issue #3: Batch Detection Conflicts with ComposedSignalDetector

**Severity: Medium — Requires architectural change**

The current detection flow:

```
ComposedSignalDetector.detect()
  → for detector in self.detectors:
      → detector.detect(context, graph_state, response_text)  # One call per signal
```

Each signal's `detect()` is called individually. The design proposes:

```python
async def detect(self, context, graph_state, response_text):
    detector = self._get_batch_detector()           # Shared across signals
    batch_result = await detector.detect(response_text)  # Single LLM call
    return {self.signal_name: batch_result.get(self.signal_name)}
```

**Problem:** When `ComposedSignalDetector` iterates 5 LLM signals, each calls `self._get_batch_detector()`. If the batch detector is shared (class-level singleton), the first signal triggers the LLM call and subsequent signals reuse the result — but this requires careful synchronization:

1. **Who triggers the actual call?** If signal A calls `detector.detect()` first, signals B-E must wait for A's call to complete and share the result.
2. **Cache invalidation:** The batch result must be invalidated between turns. With `ComposedSignalDetector` creating fresh instances per detection round, this is tricky.
3. **Result sharing:** The batch detector must return ALL signal values, not just the requesting signal's value.

**Recommendation:** Don't hide batch detection behind individual signal `detect()` calls. Instead, make it explicit at the `ComposedSignalDetector` level:

```python
class ComposedSignalDetector:
    async def detect(self, context, graph_state, response_text):
        # Separate LLM signals from non-LLM signals
        llm_signals = [d for d in self.detectors if isinstance(d, BaseLLMSignal)]
        other_signals = [d for d in self.detectors if not isinstance(d, BaseLLMSignal)]

        # Detect non-LLM signals individually (they're cheap)
        for detector in other_signals:
            signals = await detector.detect(...)
            all_signals.update(signals)

        # Detect LLM signals in one batch call
        if llm_signals:
            batch_result = await LLMBatchDetector(llm_signals).detect(response_text)
            all_signals.update(batch_result)
```

This keeps signals simple (they just provide specs) and puts batch orchestration where it belongs — in the composed detector.

**Confirmed:** With this approach, all 5 LLM signals are extracted in a **single API call**. The `LLMBatchDetector`:
1. Collects `_get_prompt_spec()` from each registered `BaseLLMSignal`
2. Assembles them into one combined system prompt
3. Makes **one** call to the scoring LLM client (Kimi K2.5)
4. Parses the JSON response and distributes values back to individual signal keys
5. Returns a flat dict: `{"llm.response_depth": 0.7, "llm.sentiment": 0.2, "llm.uncertainty": 0.4, ...}`

---

#### Issue #4: Dual Registration Systems

**Severity: Low — Confusing but not broken**

The design proposes `__init_subclass__` auto-registration on `BaseLLMSignal._signal_registry`. But `ComposedSignalDetector` already has its own `_signal_registry` populated by `_register_signals()` with explicit imports.

Two registries for the same signals creates confusion:
- Which is authoritative?
- If a signal is in one but not the other, what happens?
- Both are class-level dicts — initialization order matters.

**Recommendation:** Use only `ComposedSignalDetector._signal_registry`. The `__init_subclass__` pattern is elegant but adds complexity without real benefit here — signals are already explicitly imported and registered. The existing explicit registration is more debuggable and Python-conventional for this codebase.

If auto-discovery is truly desired, use it to **populate** `ComposedSignalDetector._signal_registry` instead of maintaining a separate one.

---

### Additional Suggestions

#### Suggestion 1: LLM Client — Kimi K2.5 (Confirmed)

The `LLMBatchDetector` will use **Kimi K2.5** via the scoring LLM client slot (ADR-010). This is the appropriate choice for signal extraction — fast, low cost, and sufficient reasoning capability for semantic signal scoring.

The scoring client parameters (currently 512 max tokens, 15s timeout) may need adjustment for K2.5:
- **Output budget:** A JSON response with 5 float signals fits well within 512 tokens
- **System prompt size:** The combined prompt (all 5 signal specs assembled) will be substantial — measure total token count and verify K2.5 context window accommodates it
- **Timeout:** 15s should be sufficient for a single-response analysis; verify with K2.5 latency benchmarks

#### Suggestion 2: Structured Output Over Free-Form JSON

The `_get_output_schema()` method returns JSON Schema fragments. Consider using the LLM provider's native structured output / tool use features instead of hoping the model produces valid JSON. The existing `parse_qualitative_signals_response()` already handles markdown-wrapped JSON as a fallback — this shouldn't be needed with proper structured output.

#### Suggestion 3: GlobalResponseTrendSignal Must Migrate to Float

`GlobalResponseTrendSignal` currently depends on `llm.response_depth` outputting categorical values (`"deep"`, `"moderate"`, `"surface"`) and counts occurrences. With the move to all-float signals, this must be updated:

```python
# BEFORE: Count categorical labels
deep_count = sum(1 for d in recent if d in ["deep", "moderate"])

# AFTER: Track float scores, compute trend via running average or slope
recent_scores = self.depth_history[-5:]  # [0.8, 0.7, 0.3, 0.2, 0.1]
avg = sum(recent_scores) / len(recent_scores)
slope = recent_scores[-1] - recent_scores[0]  # Negative = shallowing
```

This is straightforward and produces a **better** trend signal — float trajectory tracking captures gradual decline that categorical counting misses (e.g., depth dropping from 0.9 → 0.6 → 0.4 is invisible if all three map to "moderate").

#### Suggestion 4: Float Signals Enable Trajectory Tracking

A key advantage of all-float outputs: **per-response float signals can be accumulated to derive trajectories without a separate multi-turn LLM call.** Each float signal naturally forms a time series:

```
Turn 1: {depth: 0.8, uncertainty: 0.2, hedging: 0.1, sentiment: 0.7, ambiguity: 0.3}
Turn 2: {depth: 0.6, uncertainty: 0.3, hedging: 0.2, sentiment: 0.5, ambiguity: 0.4}
Turn 3: {depth: 0.3, uncertainty: 0.6, hedging: 0.5, sentiment: 0.3, ambiguity: 0.6}
→ Trajectory: depth declining, uncertainty rising, engagement fading
```

This replaces the need for the planned (but never implemented) `QualitativeSignalExtractor` multi-turn analysis for most use cases. The existing `GlobalResponseTrendSignal` pattern generalizes: any signal can have a corresponding trend signal that tracks its float values over a sliding window.

**Categorical signals cannot do this** — you can't compute a meaningful slope from `["moderate", "moderate", "surface"]`. Float signals make trajectory detection a natural byproduct of the signal pool architecture, with zero additional LLM calls.

**Future opportunity:** A generic `SignalTrendTracker` that wraps any float signal and computes running average, slope, and volatility — all derived from accumulated per-response values.

---

### Outstanding Questions — RESOLVED

1. **Kimi K2.5 context window:** ✅ **RESOLVED: Test first.** Add Phase 0 to verify K2.5 handles 2000+ token prompts within acceptable latency before full implementation.

2. **Prompt spec format for output:** ✅ **RESOLVED: 5-point scale (1-5).** All LLM signals output integers 1-5 instead of floats 0.0-1.0. This is cleaner and maps directly to Likert-style scoring. Existing rubric descriptions serve as anchoring points (1=minimal, 3=moderate, 5=maximal).

3. **Sentiment scale:** ✅ **RESOLVED: 5-point scale (1-5).** Sentiment uses same 5-point scale: 1=very negative, 2=negative, 3=neutral, 4=positive, 5=very positive. No special handling needed — same as other signals.

4. **JSON parsing robustness:** ✅ **RESOLVED: Fail fast.** No retry on malformed JSON. ADR-009 applies — fail immediately to surface issues early.

5. **Unused qualitative prompt cleanup:** ✅ **RESOLVED: Delete.** Remove `src/llm/prompts/qualitative_signals.py` as part of Phase 1 cleanup.

6. **Signal value persistence:** ✅ **RESOLVED: Update.** Update `ScoringPersistenceStage` and `qualitative_signals` table schema for 5-point integer outputs in Phase 1.

---

### High-Level Implementation Plan

#### Phase 0: K2.5 Latency Validation

**Scope:** Verify Kimi K2.5 can handle combined 2000+ token prompts within acceptable latency (<200ms) before committing to full implementation.

| Task | Description |
|------|-------------|
| 0.1 | Create test script with combined prompt (5 signal specs + instructions + output schema) |
| 0.2 | Run 10 test calls to K2.5, measure p50/p95 latency |
| 0.3 | If latency >200ms, consider alternative: split into 2 batches (depth/sentiment + uncertainty/ambiguity/hedging) |

**Exit criteria:** K2.5 p95 latency <200ms for full batch, OR approved alternative approach.

---

#### Phase 1: Infrastructure — `LLMBatchDetector` + `ComposedSignalDetector` Integration

**Scope:** Create the batch detection mechanism, wire into existing signal detection flow. Update persistence for 5-point integer outputs.

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Create `LLMBatchDetector` class with 5-point integer output schema | `src/methodologies/signals/llm/llm_batch_detector.py` (new) |
| 1.2 | Add `_get_prompt_spec()` and `_get_output_schema()` abstract methods to `BaseLLMSignal` | `src/methodologies/signals/llm/llm_signal_base.py` |
| 1.3 | Modify `ComposedSignalDetector.detect()` to batch LLM signals | `src/methodologies/signals/registry.py` |
| 1.4 | Wire Kimi K2.5 scoring client into `LLMBatchDetector` | `src/llm/client.py` (update model), `llm_batch_detector.py` |
| 1.5 | Add integration test: batch detector returns all 5 signals from single call | `tests/` |
| 1.6 | Delete unused qualitative prompt templates | `src/llm/prompts/qualitative_signals.py` (delete) |
| 1.7 | Update `ScoringPersistenceStage` for 5-point integer outputs | `src/services/turn_pipeline/stages/scoring_persistence_stage.py` |
| 1.8 | Update `qualitative_signals` table schema for integer values | `migrations/` (new migration) |

**Key design:** `LLMBatchDetector` receives list of `BaseLLMSignal` instances, assembles their specs into one prompt, makes one K2.5 call, returns flat dict of 5-point integer values.

---

#### Phase 2: Signal Migration — Replace Heuristics with Prompt Specs (5-Point Scale)

**Scope:** Rewrite each signal's implementation from heuristic to prompt spec. All outputs become integers 1-5.

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | `ResponseDepthSignal` — add `_get_prompt_spec()`, 5-point output (1=surface, 3=moderate, 5=deep) | `src/methodologies/signals/llm/signals.py` |
| 2.2 | `SentimentSignal` — add `_get_prompt_spec()`, 5-point output (1=very negative, 3=neutral, 5=very positive) | `src/methodologies/signals/llm/signals.py` |
| 2.3 | `UncertaintySignal` — add `_get_prompt_spec()`, 5-point output (1=very confident, 5=very uncertain) | `src/methodologies/signals/llm/signals.py` |
| 2.4 | `AmbiguitySignal` — add `_get_prompt_spec()`, 5-point output (1=very specific, 5=very ambiguous) | `src/methodologies/signals/llm/signals.py` |
| 2.5 | `HedgingLanguageSignal` — add `_get_prompt_spec()`, 5-point output (1=none, 5=heavy) | `src/methodologies/signals/llm/signals.py` |
| 2.6 | Remove heuristic code from all 5 signals (delete `_analyze_with_llm()` heuristic bodies) | `src/methodologies/signals/llm/signals.py` |

---

#### Phase 3: YAML Migration — Update All Methodology Configs for 5-Point Signals

**Scope:** Migrate compound categorical keys to direct 1-5 signal weights in all 5 methodology YAMLs.

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Migrate `means_end_chain.yaml` signal_weights for 1-5 scale | `config/methodologies/means_end_chain.yaml` |
| 3.2 | Migrate `jobs_to_be_done.yaml` signal_weights for 1-5 scale | `config/methodologies/jobs_to_be_done.yaml` |
| 3.3 | Migrate `customer_journey_mapping.yaml` signal_weights for 1-5 scale | `config/methodologies/customer_journey_mapping.yaml` |
| 3.4 | Migrate `critical_incident.yaml` signal_weights for 1-5 scale | `config/methodologies/critical_incident.yaml` |
| 3.5 | Migrate `repertory_grid.yaml` signal_weights for 1-5 scale | `config/methodologies/repertory_grid.yaml` |

**Migration pattern:**
```yaml
# BEFORE (categorical compound key):
signal_weights:
  llm.hedging_language.high: 1.0
  llm.hedging_language.medium: 0.7
  llm.hedging_language.low: 0.3

# AFTER (direct 1-5 multiplication):
signal_weights:
  llm.hedging_language: 0.25  # Normalizes 1-5 to ~0.25-1.25 range
```

---

#### Phase 4: Trend Signal Migration — Update `GlobalResponseTrendSignal` for 5-Point Input

**Scope:** Update the trend signal to work with 5-point depth values instead of categorical.

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | Refactor `GlobalResponseTrendSignal` to track 1-5 scores | `src/methodologies/signals/session/llm_response_trend.py` |
| 4.2 | Update `GlobalSignalDetectionService` to pass 1-5 depth values | `src/services/global_signal_detection_service.py` |

**Trend computation:** Average recent 1-5 scores, compute slope (negative = shallowing).

---

#### Phase 5: Validation

**Scope:** End-to-end testing with real K2.5 calls.

| Task | Description |
|------|-------------|
| 5.1 | Run simulation: compare signal values before (heuristic) and after (K2.5) |
| 5.2 | Measure K2.5 batch call latency (confirm <200ms p95) |
| 5.3 | Verify all 5 methodology YAMLs produce reasonable strategy rankings with 1-5 signals |
| 5.4 | Test edge cases: empty response, very long response, non-English response |
| 5.5 | Verify 5-point signal distribution (should use full range, not cluster at 3) |

---

### Model Recommendation per Phase

| Phase | Recommended Model | Rationale |
|-------|-------------------|-----------|
| Phase 0 (Validation) | **Sonnet** | Simple test script creation and execution. K2.5 latency measurement. |
| Phase 1 (Infrastructure) | **Sonnet** | Mechanical wiring: new class, method signatures, import changes. Well-defined interfaces. |
| Phase 2 (Signal Migration) | **Sonnet** | Straightforward per-signal refactoring. Prompt specs already written in this design doc. |
| Phase 3 (YAML Migration) | **Sonnet** | Simple config changes across 5 files. Low ambiguity. |
| Phase 4 (Trend Signal) | **Sonnet** | Small scope, clear requirements. Integer math replacing categorical counting. |
| Phase 5 (Validation) | **Opus** | Requires judgment: evaluating signal quality, comparing heuristic vs LLM outputs, tuning. |

**Overall complexity:** Medium. Most phases are well-defined mechanical work (Sonnet). The creative/judgment work was front-loaded in this design document.

**Key change from original design:** 5-point integer scale instead of floats. This is cleaner and maps directly to Likert-style scoring, eliminating the need for bipolar sentiment handling (negative↔positive now fits naturally on 1-5 scale).

---

### Summary Scorecard (Updated)

| Aspect | Assessment |
|--------|------------|
| Overall design direction | ✅ Strong — semantic prompts over keywords is correct |
| Hybrid Pattern choice | ✅ Good — best of the 4 options |
| Prompt spec quality | ✅ Excellent — clear rubrics, good boundaries |
| Signal orthogonality | ✅ Well-reasoned distinctions |
| Batch detection mechanism | ✅ Resolved — single API call via `ComposedSignalDetector` batching |
| Output types | ✅ **5-point integer scale (1-5)** — clean Likert-style scoring, enables trajectory tracking |
| Qualitative signal scaffolding | ✅ Delete — unused prompts removed in Phase 1 |
| Registration mechanism | ⚠️ Prefer existing `ComposedSignalDetector` registry over `__init_subclass__` |
| LLM client | ✅ Kimi K2.5 via scoring client slot (validated in Phase 0) |
| Error handling | ✅ Fail-fast — no retry on malformed JSON (ADR-009) |
| Persistence | ✅ Update — `qualitative_signals` table migrated for integer values |
