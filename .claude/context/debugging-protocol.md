# Root Cause Analysis Protocol
## Current Version: 1.0

**Before fixing any bug, trace the complete data flow back to the domain model. Never fix at the symptom site without understanding where the data was originally produced.**

## Key Source Files

This protocol applies across the pipeline. The primary artifacts to trace through:

| Artifact | Path |
|----------|------|
| PipelineContext (accumulator) | `src/services/turn_pipeline/context.py` |
| Stage contracts (Pydantic models) | `src/domain/models/pipeline_contracts.py` |
| TurnResult (API output) | `src/services/turn_pipeline/result.py` |
| Extraction models | `src/domain/models/extraction.py` |
| Knowledge graph models | `src/domain/models/knowledge_graph.py` |
| Session model | `src/domain/models/session.py` |
| NodeStateTracker | `src/services/node_state_tracker.py` |
| NodeState model | `src/domain/models/node_state.py` |
| Stage implementations | `src/services/turn_pipeline/stages/*.py` |
| DB repositories | `src/persistence/repositories/*.py` |

## Type Mismatch Issues (e.g., `'dict' object has no attribute 'x'`)

1. **Identify the consumption site** — Where the error surfaces
2. **Check the type annotation** — Look at the variable's declared type in function signature or class
3. **Trace upstream to the domain model** — Don't stop at the first producer; keep going until you reach the Pydantic model or dataclass that defines the canonical shape (`src/domain/models/*.py`).
4. **Audit every transformation in the chain**:
   - What fields does the domain model have?
   - What fields does each serialization step actually include?
   - Where is information silently dropped?
5. **Fix at the information loss point** — The bug lives where fields are dropped or types are narrowed, not where the absence is noticed:
   - Consumption code is wrong → fix access pattern
   - A transformation silently drops fields → fix the transformation
   - Contract annotation is wrong → fix the annotation

## The `.get()` / fallback test
If a fix uses `.get("key", default)` or `getattr(obj, "attr", default)` to paper over a missing field, **it is not the root cause fix** — it is masking data loss upstream. Ask: why is the field absent? Trace back to find where it was dropped.

## Data Flow Tracing Template

```
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌─────────────┐
│ Domain Model │──▶│ Serialization(s) │──▶│ Contract     │──▶│ Consumption │
│ (Pydantic)   │   │ (intermediate)   │   │ (TurnResult) │   │ (error site)│
└──────────────┘   └──────────────────┘   └──────────────┘   └─────────────┘
       │                   │                     │                   │
  All fields?        Which fields          Which fields         Which fields
                     included?             documented?          accessed?
                   ← root cause likely here if mismatch
```

## Red Flags (always investigate deeper)
- [ ] Type annotation says `Dict` but code uses `.attr` access
- [ ] Type annotation says `List[Class]` but code uses `["key"]` access
- [ ] `Any` types in the chain — trace through these carefully
- [ ] Multiple assignments with same variable name across files
- [ ] `hasattr()` checks or `isinstance()` guards masking type confusion
- [ ] `.get(key, default)` used as a fix — default value was fabricated, not derived

## Stale Specs

Context documents (`.claude/context/*.md`) are reference material for agents — agents trust them absolutely. When a spec is out of date, correct-looking code produces wrong results because it's built on wrong assumptions.

Before debugging deeply, verify the spec you're consulting matches the source:
1. Check `uv run python scripts/check_doc_drift.py` for known drift
2. Compare spec claims against the actual source file it references (listed under `## Key Files`)
3. If a spec's `## Key Files` section lists paths that no longer exist, the entire doc is suspect
4. When a spec contradicts observed behavior, trust the source code and flag the spec for update

## Known Failure Modes

_No entries yet. Add failure patterns as they are discovered in this subsystem — each entry should describe the incorrect behavior, its consequence, and the correct approach._

