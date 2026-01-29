# Adaptive Interview System v2: Product Requirements Document

**Status:** Draft  
**Version:** 2.0  
**Date:** January 2026

---

## 1. Problem Statement

### 1.1 Background

Qualitative consumer research relies on skilled human interviewers to elicit mental models—the beliefs, values, and decision criteria consumers use when evaluating products. Traditional approaches are expensive, inconsistent, and don't scale.

### 1.2 v1 Failure Analysis

The previous implementation (v1) failed due to fundamental architectural issues:

**Critical Error:**
```
RuntimeError: Task... got Future... attached to a different loop
asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress
```

**Root Cause:** Gradio UI (sync callbacks) + asyncpg/async LLM clients (bound to initialization loop) + `asyncio.run()` in adapter (creates new loop) = event loop mismatch.

**v1 Complexity Issues:**
- 14 scorers for strategy selection (tuning nightmare)
- 7 strategies with interaction effects
- PostgreSQL + Redis (deployment overhead for single-user)
- Full bi-temporal versioning (4 timestamps per record)
- Multiple LLM providers with fallback chains

### 1.3 v2 Approach

Start simple. Single-user, SQLite, 5 scorers, FastAPI (single event loop). Prove the core works, then scale.

---

## 2. Goals

### 2.1 Primary Goals

1. **Conduct adaptive interviews** that respond to what respondents actually say
2. **Build knowledge graphs** representing consumer mental models in real-time
3. **Achieve coverage** of stimulus concept elements systematically
4. **Enable rapid testing** via synthetic respondent for development iteration

### 2.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Interview completion rate | ≥90% | Sessions reaching natural close |
| Element coverage | ≥80% | Stimulus elements explored |
| Response latency | <5s p95 | Time from user input to system response |
| Extraction accuracy | ≥80% | Concepts correctly identified (sampled review) |
| Graph coherence | <10% orphan nodes | Nodes without relationships |

### 2.3 Non-Goals (v2 Scope)

- Multi-user concurrent access
- Voice/speech processing
- Cross-interview aggregation
- Production respondent UI (demo UI only)
- Multi-language support (architecture enables, not implemented)

---

## 3. User Personas

### 3.1 Marketing Researcher (Primary)

**Context:** Runs consumer studies to understand product perception
**Needs:** 
- Upload concept descriptions
- Configure interview parameters
- Review completed interviews and extracted insights
- Export results for reporting

### 3.2 Developer (Secondary)

**Context:** Building and testing the system
**Needs:**
- Run automated test interviews
- Inspect system diagnostics (scores, strategy selection, graph state)
- Debug extraction and generation quality

---

## 4. Core Capabilities

### 4.1 Interview Conduction

The system conducts text-based interviews following configurable methodologies (initially Means-End Chain). Each turn:

1. Receives respondent text input
2. Extracts concepts and relationships
3. Updates knowledge graph
4. Evaluates graph state (coverage, depth, saturation)
5. Selects questioning strategy
6. Generates natural follow-up question

### 4.2 Knowledge Graph Construction

**Dual Graph Architecture:**

| Graph | Purpose | Persistence |
|-------|---------|-------------|
| **Conversational** | Dialogue flow, discourse markers, coreference context | In-memory + SQLite backup |
| **Knowledge** | Extracted mental model (concepts, relationships) | SQLite (persists beyond session) |

**Knowledge Graph Schema (Means-End Chain):**

```
Nodes:
- Attribute (concrete product features)
- Functional Consequence (tangible outcomes)
- Psychosocial Consequence (emotional/social outcomes)
- Instrumental Value (preferred behaviors)
- Terminal Value (end-states of existence)

Edges:
- LEADS_TO (causal/enabling relationship)
- REVISES (contradiction - newer belief supersedes older)
```

**Provenance:** Every knowledge node links to source utterance(s) via `source_utterance_ids`.

### 4.3 Coverage Tracking

Track which stimulus concept elements have been explored:

```yaml
concept:
  elements:
    - id: creamy_texture
      label: "Creamy texture"
      type: attribute
      priority: high
      covered: false  # Updated when extracted
```

Coverage score = weighted sum of covered elements / total weighted elements.

### 4.4 Adaptive Strategy Selection

**Strategies (4 total):**

| Strategy | When to Use | Action |
|----------|-------------|--------|
| DEEPEN | Shallow chain, more to explore | "Why is that important to you?" |
| BROADEN | Deep chain, find new branches | "What else matters about this?" |
| COVER | Untouched stimulus elements | Introduce new element |
| CLOSE | Coverage met, saturated | Wrap up interview |

**Scoring (5 scorers, multiplicative):**

```
final_score = base × coverage × depth × saturation × novelty × richness
```

### 4.5 Session Persistence

Sessions can be paused and resumed:
- All state persisted to SQLite
- Load session by ID to continue
- Export completed sessions to JSON/Markdown

### 4.6 Synthetic Respondent

For automated testing, the system can generate plausible respondent answers:

```
POST /synthetic/respond
{
  "question": "Why is creamy texture important?",
  "context": { ... },
  "persona": "health_conscious_millennial"
}
```

Enables rapid iteration without manual testing.

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Demo UI                                   │
│                  (Chat + Diagnostics Panel)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  /sessions  │  │  /concepts  │  │  /synthetic             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Service Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Session      │  │ Extraction   │  │ Strategy           │    │
│  │ Service      │  │ Service      │  │ Service            │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Graph        │  │ Question     │  │ Synthetic          │    │
│  │ Service      │  │ Service      │  │ Service            │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Persistence Layer                              │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐ │
│  │        SQLite            │  │     LLM Client              │ │
│  │  • Sessions              │  │  • Anthropic API            │ │
│  │  • Knowledge Graph       │  │  • Extraction tasks         │ │
│  │  • Utterances            │  │  • Generation tasks         │ │
│  └──────────────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web Framework | FastAPI | Async-native, single event loop, OpenAPI |
| Database | SQLite | Zero config, sufficient for single-user |
| Session State | SQLite (no Redis) | Simplicity, persistence |
| LLM Provider | Anthropic (single) | Reduce complexity, add others later |
| Event Loop | Single (uvicorn) | Eliminates v1's fatal flaw |

---

## 6. User Flows

### 6.1 Flow 1: Conduct Interview (Demo UI)

```
1. Researcher opens Demo UI
2. Selects/uploads concept configuration
3. Configures: methodology, max turns, target coverage
4. Clicks "Start Interview"
5. System displays opening question
6. Loop:
   a. Researcher (acting as respondent) types response
   b. System extracts concepts → updates graph
   c. Diagnostics panel shows: graph viz, coverage %, strategy reasoning
   d. System generates follow-up question
   e. Repeat until coverage met or max turns
7. System displays completion summary
8. Researcher exports results
```

### 6.2 Flow 2: Automated Testing (Synthetic)

```
1. Test script calls POST /sessions with concept config
2. Loop:
   a. Script calls POST /synthetic/respond with current question
   b. Synthetic service generates plausible answer
   c. Script calls POST /sessions/{id}/turns with answer
   d. System processes turn, returns next question
   e. Script logs diagnostics
   f. Repeat until should_continue=false
3. Script validates: coverage achieved, no errors, graph coherent
```

### 6.3 Flow 3: Resume Session

```
1. Call GET /sessions to list previous sessions
2. Select session with status="active"
3. Call GET /sessions/{id} to load state
4. Continue from last turn
```

---

## 7. Dual Graph Architecture

### 7.1 Why Two Graphs?

| Conversational Graph | Knowledge Graph |
|---------------------|-----------------|
| Tracks dialogue flow | Tracks extracted mental model |
| Session-scoped | Persists beyond session |
| Enables coreference resolution | Enables coverage analysis |
| Discourse markers signal edge types | Provenance links to source utterances |

### 7.2 Conversational Graph (In-Memory + Backup)

```python
class ConversationalGraph:
    utterances: List[Utterance]  # All turns
    discourse_markers: Dict[str, List[str]]  # "because" → causation signals
    topic_threads: List[TopicThread]  # Conversation segments
```

Stored in session object, backed up to SQLite `utterances` table.

### 7.3 Knowledge Graph (SQLite Persisted)

```sql
-- Nodes
CREATE TABLE kg_nodes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    label TEXT NOT NULL,
    node_type TEXT NOT NULL,  -- attribute, consequence, value
    confidence REAL DEFAULT 0.8,
    source_utterance_ids JSON NOT NULL,  -- Provenance
    recorded_at TEXT NOT NULL,
    superseded_by TEXT  -- For contradictions (REVISES)
);

-- Edges
CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,  -- leads_to, revises
    confidence REAL DEFAULT 0.8,
    source_utterance_ids JSON NOT NULL
);
```

### 7.4 Contradiction Handling

When a newer statement contradicts an earlier one:

```
Old: "I avoid sugar" (node n1)
New: "Actually I don't mind sugar in coffee" (node n2)

Result:
- n1.superseded_by = n2.id
- Edge: n1 ←REVISES─ n2
```

No deletion, full audit trail preserved.

---

## 8. API Specification

### 8.1 Session Management

```
POST   /sessions                    Create new session
GET    /sessions                    List all sessions
GET    /sessions/{id}               Get session details
POST   /sessions/{id}/turns         Process respondent turn
DELETE /sessions/{id}               Close/abandon session
```

### 8.2 Monitoring & Export

```
GET    /sessions/{id}/status        Current scores, strategy, phase
GET    /sessions/{id}/coverage      Element coverage details
GET    /sessions/{id}/graph         Full knowledge graph
GET    /sessions/{id}/export        Export to JSON/Markdown
```

### 8.3 Concepts

```
GET    /concepts                    List available concepts
POST   /concepts                    Upload new concept config
GET    /concepts/{id}               Get concept details
```

### 8.4 Synthetic Respondent

```
POST   /synthetic/respond           Generate synthetic response
```

### 8.5 System

```
GET    /health                      Health check
```

### 8.6 Key Response Structures

**POST /sessions/{id}/turns Response:**

```json
{
  "turn_number": 3,
  "extracted": {
    "concepts": [
      {"text": "creamy texture", "type": "attribute", "confidence": 0.9}
    ],
    "relationships": [
      {"source": "creamy texture", "target": "satisfying", "type": "leads_to"}
    ]
  },
  "graph_state": {
    "node_count": 5,
    "edge_count": 3,
    "depth_achieved": {"attribute": 3, "consequence": 2, "value": 0}
  },
  "scoring": {
    "coverage": 0.25,
    "depth": 0.15,
    "saturation": 0.0
  },
  "strategy_selected": "deepen",
  "next_question": "You mentioned the creamy texture feels satisfying. Why is that feeling important to you?",
  "should_continue": true
}
```

---

## 9. Configuration

### 9.1 Concept Configuration

```yaml
# config/concepts/oat_milk.yaml
id: oat_milk_v1
name: "Oat Milk"
methodology: means_end_chain

elements:
  - id: creamy_texture
    label: "Creamy texture"
    type: attribute
    priority: high
    
  - id: plant_based
    label: "Plant-based / dairy-free"
    type: attribute
    priority: high

completion:
  target_coverage: 0.8
  max_turns: 20
  saturation_threshold: 0.05
```

### 9.2 Methodology Configuration

```yaml
# config/methodologies/means_end_chain.yaml
id: means_end_chain
name: "Means-End Chain Analysis"

node_types:
  - id: attribute
    abstraction_level: low
  - id: functional_consequence
    abstraction_level: medium
  - id: psychosocial_consequence
    abstraction_level: medium_high
  - id: instrumental_value
    abstraction_level: high
  - id: terminal_value
    abstraction_level: highest
    is_terminal: true

edge_types:
  - id: leads_to
  - id: revises
```

---

## 10. Technical Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Python version | 3.11.x | Stable async, avoid 3.14 edge cases |
| Database | SQLite 3.40+ | JSON1 extension required |
| Response latency | <5s p95 | Conversational pace |
| Max turns | 30 | Prevent runaway sessions |
| Max concepts per session | 20 | Memory/complexity bounds |

---

## 11. Out of Scope (Future)

| Feature | Why Deferred |
|---------|--------------|
| Multi-user | Requires PostgreSQL, auth system |
| Voice | Separate complexity domain |
| Cross-interview aggregation | Requires graph merging algorithms |
| WebSocket updates | API polling sufficient for demo |
| Cloud deployment | Local-first for MVP |
| Multiple LLM providers | Single provider reduces failure modes |

---

## 12. Open Questions

1. **Frontend framework:** Gradio vs Streamlit vs htmx for Demo UI?
2. **Extraction granularity:** Process per-turn or batch at end?
3. **Coreference window:** How many previous utterances to consider?
4. **Strategy selection:** Pure scoring or LLM-assisted arbitration?

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Means-End Chain** | Theory linking product Attributes → Consequences → Values |
| **Laddering** | Interview technique to climb abstraction levels |
| **Stimulus concept** | Product/idea being explored in interview |
| **Coverage** | Proportion of stimulus elements explored |
| **Saturation** | Point where new responses yield no new information |
| **Provenance** | Link from extracted knowledge to source utterance |

## Appendix B: v1 Reference

The original v1 design document (11K lines) is available at:
`docs/adaptive_interview_system_design_document_complete.md`

Use for reference on prompts, extraction logic, and scoring details. Do not treat as requirements—the mixed concerns caused v1's failure.
