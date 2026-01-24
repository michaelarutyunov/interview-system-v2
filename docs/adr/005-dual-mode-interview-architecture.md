# ADR-005: Adopt Dual-Mode Interview Architecture

## Status
**Deprecated** (2025-01-24)

## Deprecation Notice

This ADR has been deprecated in favor of the current single-mode approach with YAML-driven phasing:

- **Phasing** (exploratory → focused → closing) already provides temporal strategy modulation
- **Single mode** (coverage_driven) with configurable phase multipliers is sufficient for current use cases
- The dual-mode architecture (coverage_driven vs graph_driven) would add ~15% codebase complexity for a use case (graph-driven emergent discovery) that is not currently needed

**Decision:** The system will continue with a single `coverage_driven` mode supported by phase-based strategy modulation. Future work may revisit dual-mode if graph-driven exploratory research becomes a priority.

---

## Original Context (Archived)

**Problem Statement (Archived):**

### The Problem: Architectural Contradiction

The current interview system attempts to simultaneously optimize for two **fundamentally opposed** paradigms:

**Position A: Coverage-Driven (Systematic Exploration)**
- Researcher has predefined topics that must be explored
- Interview guide is directive (semi-structured)
- Success = completeness (all topics covered with sufficient depth)
- Methodological alignment: Semi-structured interviews, MEC laddering, concept testing

**Position B: Graph-Driven (Emergent Discovery)**
- Respondent's natural associations guide conversation
- Interview is minimally directive (conversational/unstructured)
- Success = richness (dense, well-connected graph revealing emergent themes)
- Methodological alignment: Grounded theory, in-depth interviews, narrative inquiry

### Current State: "Schizophrenic" Behavior

The system tries to be both systematic AND emergent, resulting in contradictory scoring:

```python
# Current scorer priorities encode this contradiction:

ElementCoverageScorer:   weight=1.0, boost=2.5x  # Coverage-first
NoveltyScorer:           weight=1.0, boost=2.0x  # Graph-first
DepthScorer:             weight=1.0, boost=1.8x  # Graph-first
```

This creates jarring transitions:
- **Early interview**: "Must cover topics!"
- **Mid interview**: "Follow interesting chains!"
- **Late interview**: "Back to uncovered topics!"

### Why You Must Choose

These paradigms have fundamentally opposed decision-making criteria:

| Decision Point | Coverage-Driven | Graph-Driven |
|---------------|-----------------|--------------|
| **Next topic** | First uncovered topic | Most interesting thread |
| **When to switch** | Topic exhausted or covered | Respondent changes direction |
| **Depth vs breadth** | Ensure breadth first | Follow depth naturally |
| **Success** | All topics addressed | Rich emergent themes |
| **Respondent role** | Answer researcher questions | Lead the exploration |

**You cannot optimize for both simultaneously.**

### Methodological Foundation

Coverage-driven interviewing aligns with established qualitative research practices:

> "To achieve optimum use of interview time, interview guides serve the useful purpose of exploring many respondents more systematically and **comprehensively** as well as to keep the interview focused" (Kallio et al. 2016)

The MEC/laddering technique explicitly requires connected chains:

> "The ladder obtained from an interview only reveals aspects of cognitive structure if it forms an **inter-related network of associations**" (Veludo-de-Oliveira et al. 2006)

**Incomplete ladders** (attributes without consequences) are considered **methodological failures** in the MEC tradition.

---

## Decision

**Adopt explicit dual-mode architecture** that allows users to choose between:

1. **Coverage-Driven Mode** - Systematic topic exploration for concept testing
2. **Graph-Driven Mode** - Emergent discovery for exploratory research

**Implementation:**
- Add `InterviewMode` enum to session creation
- Create abstract `InterviewState` base class with mode-specific implementations
- Mode-aware strategy and scorer configuration loading
- User selects mode at session creation via UI

---

## Rationale

### 1. Methodological Alignment

| Mode | Matches | Does Not Match |
|------|---------|----------------|
| **Coverage-Driven** | Semi-structured interviews, MEC laddering, concept testing | Grounded theory, narrative inquiry |
| **Graph-Driven** | Grounded theory, in-depth interviews, narrative inquiry | Concept testing, systematic evaluation |

Each mode aligns with established qualitative methodology. Trying to be both creates methodological incoherence.

### 2. Clear Product Positioning

**Before:** "Adaptive interviews that feel natural"
**After:** "Choose your interview style: systematic coverage OR exploratory discovery"

This creates clear value propositions:
- **Coverage mode**: "Ensure all topics are covered systematically"
- **Graph mode**: "Follow respondent's natural associations"

### 3. Architectural Efficiency

The current system already supports both paradigms with ~85% shared infrastructure:

| Component | Shared | Changes Required |
|-----------|--------|------------------|
| Graph models | ✅ Identical | None |
| LLM integration | ✅ Identical | None |
| Extraction pipeline | ✅ Identical | None |
| Database layer | ✅ Identical | None |
| State models | ❌ | Add abstraction layer |
| Scoring configs | ❌ | Split by mode |
| Strategy configs | ❌ | Split by mode |

**Total refactor estimate: ~15% of codebase**

### 4. Enables Research Opportunities

Dual-mode architecture enables empirical comparison:
- Coverage-driven vs graph-driven: which produces richer graphs?
- Same concept, both modes: do they reveal different insights?
- Respondent experience: which mode feels more natural?

### 5. Future Flexibility

Starting with dual modes enables:
- A/B testing capability
- Addition of hybrid modes based on learning
- Clear migration path as methodology evolves

---

## Consequences

### Positive

1. **Coherent Interview Behavior** - Each mode has consistent philosophy
2. **Methodological Honesty** - Acknowledges the tradeoffs explicitly
3. **User Choice** - Researchers select approach aligned with goals
4. **Research Opportunities** - Can empirically compare modes
5. **Testing Clarity** - Each mode has clear success criteria

### Negative

1. **Development Effort** - ~15% codebase refactor required
2. **Configuration Complexity** - More YAML files to maintain
3. **User Confusion** - Need clear explanations of mode differences
4. **Testing Burden** - Must validate both modes separately

### Neutral

1. **Performance** - No significant impact (same infrastructure)
2. **Database** - No schema changes (existing tables work)
3. **API** - Mode field added to session creation (backward compatible)

---

## Implementation

### Phase Sequence

**Phase 1: Abstraction Layer** (5%)
- Create `InterviewState` abstract base class
- Implement `CoverageState` for systematic exploration
- Implement `EmergenceState` for emergent discovery

**Phase 2: Domain Model Updates** (2%)
- Add `InterviewMode` enum to Session
- Update Session to use abstract InterviewState

**Phase 3: Service Layer** (5%)
- Mode-aware session initialization
- Mode-aware strategy/scorer loading
- Concept validation per mode

**Phase 4: Configuration** (3%)
- Create coverage-driven YAML configs
- Create graph-driven YAML configs
- Update concept schemas with topics

**Phase 5: API & UI** (2%)
- Add mode to SessionCreate schema
- Mode selector in UI
- Documentation updates

### File Structure

```
src/
├── domain/
│   └── models/
│       ├── interview_state.py      # NEW: Abstract base + implementations
│       ├── session.py              # MODIFY: Add mode field
│       └── ...
├── services/
│   ├── session_service.py          # MODIFY: Mode-aware initialization
│   ├── strategy_service.py         # MODIFY: Mode-aware config loading
│   └── ...
└── config/
    ├── strategies/
    │   ├── coverage_driven.yaml    # NEW
    │   └── graph_driven.yaml       # NEW
    ├── scoring/
    │   ├── coverage_driven.yaml    # NEW
    │   └── graph_driven.yaml       # NEW
    └── concepts/
        └── *.yaml                  # MODIFY: Add topics section
```

---

## Alternatives Considered

### Alternative 1: Single Hybrid Mode

**Approach:** Continue with current hybrid approach, tune weights to balance coverage vs emergence.

**Rejected because:**
- Fundamental philosophical contradiction remains
- No way to "tune away" the core tension
- Creates confusing, unpredictable behavior
- Cannot align with specific methodologies

### Alternative 2: Coverage Only

**Approach:** Drop graph-driven approach entirely, focus on systematic coverage.

**Rejected because:**
- Eliminates valid use case (exploratory research)
- Removes research opportunity
- Limits product market
- Grounded theory researchers need different approach

### Alternative 3: Graph Only

**Approach:** Drop coverage-driven approach, focus purely on emergence.

**Rejected because:**
- Concept testing requires systematic evaluation
- Stakeholder expectations include coverage metrics
- MEC laddering requires systematic chain completion
- Primary use case is concept testing for marketing

---

## References

- **docs/theory/coverage_approaches_analysis.md** - Complete analysis of coverage vs emergence tension
- **ADR-003**: Adopt Phase 3 Adaptive Strategy Selection - Initial strategy system
- **Kallio et al. (2016)**: "Semi-structured interview" - Establishes interview guide methodology
- **Reynolds & Gutman (1988)**: "Laddering" - MEC technique requirements
- **Veludo-de-Oliveira et al. (2006)**: MEC validity requirements for connected chains
