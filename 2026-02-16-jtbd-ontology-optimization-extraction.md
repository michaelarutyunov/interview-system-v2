---
created: 2026-02-16
conversation_type: multi-phase
phases: [methodology, implementation, architecture, code-tracing]
primary_focus: methodology
topics: [JTBD ontology optimization, extraction edge/node ratio, ontology simplification, schema field tracing, permitted connections]
tags: [ml/knowledge-graphs, systems/ontology-design, methodology/jtbd-optimization, architecture/schema-simplification, project/interview-system-v2]
type: claude-discussion
conversation_date: 2026-02-16
---

# JTBD Ontology Optimization: Fixing Edge Under-Detection and Schema Simplification

## Context
The JTBD (Jobs-to-be-Done) methodology in the interview system was producing too many orphan nodes and too few edges (edge/node ratio ~0.42). This session diagnosed the root causes, implemented fixes to the extraction pipeline, designed a simplified ontology variant, evaluated an external theoretical critique, and traced all schema fields to their downstream code consumers.

## Discovery Path
How this conversation evolved:
1. **Initial problem**: JTBD extraction produces too many nodes, not enough edges — graph is sparse and poorly connected
2. **Root cause**: The extraction LLM prompt includes node/edge type names but **never shows `permitted_connections`** — the LLM generates edges blindly, then `is_valid_connection()` silently rejects ~40% of them
3. **Insight**: The ontology has 3 near-synonym positive edge types (`addresses`, `enables`, `supports`) that confuse classification, and critical paths are missing (e.g., `solution_approach -> emotional_job` requires 3 hops)
4. **Implementation**: Added permitted_connections to the extraction prompt + expanded 10 missing connections in the YAML (27->37 connections)
5. **Architecture redesign**: Created simplified ontology variant: 8->5 node types, 7->4 edge types, achieving 80% coverage density vs 58%
6. **External critique evaluation**: Analyzed a JTBD theory critique suggesting Job Stories as atomic units — partially valid but impractical for turn-by-turn extraction
7. **Code tracing**: Mapped every YAML schema field to its downstream code consumer, documented in `schema_tracing.md`

**Key pivot point**: Discovering that the extraction prompt never included `permitted_connections` — the LLM was essentially generating edges with a ~60% chance of hitting a valid type pair, then the validator silently dropped the rest.

## Methodological Insight
**Previous approach**: The ontology modeled JTBD as entity-relationship with 8 fine-grained node types (treating emotional_job and social_job as separate terminal node types at level 1) and 7 edge types with 3 near-synonyms for positive relationships.

**Revised approach**: Two variants created:
- **Enhanced original** (`jobs_to_be_done.yaml`): Same structure but with permitted_connections visible to LLM + 10 new connection paths
- **Simplified** (`jobs_to_be_done_simple.yaml`): 5 node types (job, circumstance, pain_point, gain_point, solution) and 4 edge types (leads_to, conflicts_with, occurs_in, revises)

**Implications**: The simplified ontology eliminates three key classification ambiguities:
1. `emotional_job` vs `social_job` vs `job_statement` -> single `job` type
2. `job_context` vs `job_trigger` -> single `circumstance` type
3. `addresses` vs `enables` vs `supports` -> single `leads_to` type

**Assumptions challenged**:
- Terminal nodes (`terminal: true`) are vestigial in JTBD — they serve MEC's `ChainCompletionSignal` but JTBD never reads that signal
- `gain_point` as separate from job is arguably MEC, not JTBD (Ulwick's "desired outcomes" are success criteria for jobs, not standalone entities)

## Architecture Decision
**Context**: Edge/node ratio too low (~0.42), causing sparse graphs that provide insufficient signal for strategy selection.

**Options considered**:
- **Option A: Include permitted_connections in prompt** - Low effort, high impact. Makes the LLM aware of valid type pairs.
- **Option B: Simplify ontology** - Medium effort, highest impact. Reduces classification ambiguity at the source.
- **Option C: Expand missing connections** - Low effort, medium impact. Opens natural paths that were blocked.
- **Option D: A + C combined** - Applied first as quick win.
- **Job Stories approach (external)**: Replace fragmented nodes with composite `job_story` nodes containing circumstance/motivation/outcome. Theoretically elegant but impractical — job stories emerge across multiple turns, composite nodes are harder to extract, and fewer fat nodes provide less signal for strategy selection.

**Decision**: Implemented Option D (prompt fix + expanded connections) as immediate fix. Created Option B (simplified ontology) as `jobs_to_be_done_simple.yaml` for A/B testing.

**Rationale**: Option D is non-breaking and addresses the primary cause (silent edge rejection). The simplified ontology can be tested in parallel without affecting existing sessions.

**Constraints**: Can't remove `terminal: true` from MEC ontology (breaks `ChainCompletionSignal`). Safe to remove from JTBD since that signal is not referenced.

## Key Decisions
- **Include permitted_connections in extraction prompt**: One-line change with highest expected impact — LLM now sees valid type pairs instead of guessing
- **Keep `gain_point` as separate type in simplified ontology**: Despite theoretical argument to merge with `job`, the LLM can reliably distinguish "what I want to accomplish" from "what benefit I get" — worth testing empirically
- **Merge all three positive edge types into `leads_to`**: The distinction between `addresses`, `enables`, and `supports` is not reliably extractable by LLM
- **Dead fields identified**: `method.description` and `method.version` are defined in YAML but never consumed by code

## Methodology Insights

### Root Causes of Edge Under-Detection (5 identified)
1. **Permitted connections invisible to LLM** (PRIMARY) — extraction prompt showed edge names/descriptions but not valid type pairs
2. **Edge type semantic overlap** — 3 near-synonym positive edges (`addresses`, `enables`, `supports`) cause misclassification
3. **Missing natural connections** — `solution_approach -> emotional_job` required 3 hops through `job_statement`
4. **Directional strictness** — `triggered_by` expects `[job_statement, job_trigger]` but LLM may write trigger->job (causal direction); silent rejection
5. **8 node types = classification ambiguity** — "feeling tired" could be `job_trigger` or `job_context`; misclassification cascades to edge rejection

### Coverage Density as Quality Metric
With $N$ node types, there are $N^2$ possible ordered type pairs. Coverage density = valid connections / $N^2$:
- Original (8 types): 37/64 = **58%**
- Simplified (5 types): 20/25 = **80%**

Higher density means fewer blind spots for the LLM — any reasonable edge it generates is more likely to be valid.

### JTBD Theory Evaluation
Evaluated external critique arguing the ontology fights JTBD theory:
- **Valid**: emotional/social jobs should be dimensions of a job, not separate terminal types (Christensen view)
- **Valid**: `job_context`/`job_trigger` distinction is too subtle for reliable extraction
- **Overstated**: `gain_point` isn't "pure MEC" — Ulwick's desired outcomes ARE gain points
- **Impractical**: Job Stories as atomic composite nodes don't work for turn-by-turn extraction (emerge across multiple turns, fewer nodes = less strategy signal)

## Technical Details

### Code Changes Made

**1. New method on `MethodologySchema`** (`src/domain/models/methodology_schema.py`):
```python
def get_edge_descriptions_with_connections(self) -> Dict[str, str]:
    """Includes permitted connections so the LLM knows valid type pairs."""
    result = {}
    if self.ontology:
        for et in self.ontology.edges:
            connections = []
            if et.permitted_connections:
                for conn in et.permitted_connections:
                    if isinstance(conn, EdgeConnectionSpec):
                        connections.append(f"{conn.from_}->{conn.to}")
                    elif isinstance(conn, list):
                        connections.append(f"{conn[0]}->{conn[1]}")
            conn_str = f" (valid: {', '.join(connections)})" if connections else ""
            result[et.name] = f"{et.description}{conn_str}"
    return result
```

**2. Extraction prompt** (`src/llm/prompts/extraction.py:40`):
```python
# Changed from:
edge_descriptions = schema.get_edge_descriptions()
# To:
edge_descriptions = schema.get_edge_descriptions_with_connections()
```

**3. YAML changes** (`config/methodologies/jobs_to_be_done.yaml`):
Added 10 new permitted connections across 5 edge types (27->37 total).

**4. Simplified YAML** (`config/methodologies/jobs_to_be_done_simple.yaml`):
Complete rewrite with 5 node types, 4 edge types, updated extraction guidelines and relationship examples.

### Schema Field Tracing
Full tracing documented in `config/methodologies/schema_tracing.md`:

| Field | Consumer | Used? |
|---|---|---|
| `method.name` | `question.py:346` | YES |
| `method.goal` | `question.py:347` | YES |
| `method.opening_bias` | `question.py:348-361` | YES |
| `method.description` | — | **NO (dead)** |
| `method.version` | — | **NO (dead)** |
| `nodes[].terminal` | `graph_signals.py:197` (ChainCompletionSignal) | YES but only for MEC |
| `extraction_guidelines` | `extraction.py:93` | YES |
| `relationship_examples` | `extraction.py:94` | YES |
| `extractability_criteria` | `extraction.py:228` | YES |

### `terminal` Field Dependency Chain
```
YAML terminal: true
  -> schema.is_terminal_node_type()           # methodology_schema.py:152
  -> schema.get_terminal_node_types()          # methodology_schema.py:125
  -> ChainCompletionSignal.detect()            # graph_signals.py:197
  -> extraction_service: concept.is_terminal   # extraction_service.py:406
  -> node_state_tracker: is_terminal           # node_state_tracker.py:140
```
Only `means_end_chain.yaml` references `graph.chain_completion`. Safe to remove `terminal: true` from JTBD.

## Key Insights & Learnings
1. **Silent validation is the enemy of graph density** — when `is_valid_connection()` drops edges without the LLM knowing the constraints, you get systematically sparse graphs. Making constraints visible in the prompt is the highest-leverage fix.
2. **Coverage density matters more than total connections** — 20 connections over 5 types (80% coverage) beats 37 over 8 types (58%) because the LLM has fewer classification decisions and each one is more likely valid.
3. **Near-synonym edge types cause cascading failures** — the LLM picks one of `addresses`/`enables`/`supports` based on vibes; if the permitted_connections differ, the edge is silently dropped. Merging near-synonyms eliminates this failure mode entirely.
4. **Theoretical purity vs extraction practicality** — Job Stories are cleaner JTBD theory but don't work for turn-by-turn extraction. Composite nodes require cross-turn assembly and provide fewer signals for strategy selection.
5. **Dead fields accumulate** — `method.description` and `method.version` are defined in every YAML but consumed nowhere. Schema tracing catches this.

## Related Concepts
- Consider creating: [[Knowledge Graph Extraction Optimization]]
- Consider creating: [[JTBD Theory vs Implementation Tradeoffs]]
- Consider creating: [[Ontology Design for LLM Extraction]]

## Follow-up Questions
- What edge/node ratio does the simplified ontology actually achieve? Need to run `test_extraction.py` and full simulation comparisons.
- Should `gain_point` be merged into `job` in the simplified ontology? Theoretical argument exists but needs empirical validation.
- Should dead fields (`method.description`, `method.version`) be removed from YAML or kept for documentation value?
- How does the MEC ontology compare? Does it have the same edge under-detection issues?

## References
- Christensen, C. (2016). Competing Against Luck — JTBD as functional/emotional/social dimensions
- Ulwick, A. (2016). Jobs to be Done — ODI framework with desired outcomes as measurable statements
- Moesta, B. & Klement, A. — Switch Interview methodology (hires/fires vocabulary)
- `config/methodologies/schema_tracing.md` — Full field-to-consumer tracing table

---
*Conversation preserved from Claude Code session 2026-02-16*
