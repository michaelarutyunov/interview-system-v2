# LLM Extraction Issues Analysis

> **Date**: 2026-02-04
> **Status**: Analysis complete, no implementation planned

## Problem Statement

The interview system's extraction pipeline is producing significantly fewer edges than expected:

| Metric | Actual | Target | Gap |
|--------|--------|-------|-----|
| Edge-to-node ratio | 0.35-0.53 | 2-3 | ~85% below target |

A well-structured Means-End Chain (MEC) interview should have 2-3x more edges than nodes for proper chain representation. Current simulations show only 0.3-0.5x.

## Investigation Summary

### What We Checked

1. **Schema validation** - Found that strict MEC ontology was rejecting valid cross-level relationships
   - `attribute → psychosocial_consequence` (rejected)
   - `functional_consequence → instrumental_value` (rejected)
   - `instrumental_value → functional_consequence` (rejected)

2. **Extraction prompt structure** - Reviewed the full extraction prompt in `src/llm/prompts/extraction.py`
   - MEC guidelines ARE being passed to the LLM
   - "Conversational Implicit Relationships" section exists
   - Multiple relationship examples provided
   - Target 2-3x edges guideline included

3. **Context formatting** - Verified the context builder in `extraction_stage.py`
   - Last 5 utterances included with speaker labels
   - Special "Most recent question" highlight with explicit task instruction
   - Q&A relationship extraction explicitly requested

4. **LLM configuration** - Checked extraction service settings
   - Temperature: 0.3 (conservative)
   - Max tokens: 2000
   - Model: claude-sonnet-4-5-20250929

### Root Cause Analysis

The extraction system has **multiple compounding issues**:

#### 1. LLM Prioritization of Concepts over Relationships

Even with explicit instructions, the LLM consistently extracts more concepts than relationships:

| Turn | Concepts | Relationships | Ratio |
|------|----------|---------------|-------|
| 1 | 7 | 0 | 0.00 |
| 2 | 4 | 2 | 0.50 |
| 3 | 5 | 4 | 0.80 |
| 4 | 5 | 4 | 0.80 |

**Why**: Concepts are easier/safer to extract. Relationships require:
- Identifying two concepts
- Validating the connection type
- Checking permitted_connections in schema
- Inferring directionality

#### 2. Conservative Temperature (0.3)

Low temperature makes the LLM risk-averse, missing:
- Implicit causal connections
- Cross-level jumps (attribute → psychosocial without intermediate)
- Conversational Q&A relationships

#### 3. Prompt Length and Complexity

The extraction prompt is lengthy (~150+ lines):
- Universal extraction principles
- All node/edge type definitions
- All MEC extraction guidelines
- All relationship examples
- Phase-specific guidelines
- Element linking instructions
- Context + user prompt

Relationship extraction instructions get "lost in the noise."

#### 4. No Explicit Relationship Quota

The prompt says "Target 2-3x more edges" but doesn't enforce:
- No minimum relationship requirement
- No validation rule that rejects low edge extractions
- LLM may interpret "target" as aspirational, not required

#### 5. Schema Validation Rejections

Even when the LLM tries to extract cross-level relationships, they get rejected:

```
invalid_connection: edge_type=leads_to, source_type=attribute, target_type=psychosocial_consequence
invalid_connection: edge_type=leads_to, source_type=functional_consequence, target_type=instrumental_value
```

**Decision**: Schema validation is intentional (MEC chain integrity), not a bug.

## Recommendations

If extraction improvement is needed in the future, consider these approaches in order of impact:

### High Impact, Low Effort

1. **Add explicit relationship quota** to prompt:
   ```
   CRITICAL REQUIREMENT: For N concepts extracted, you MUST extract at least 2N-3N relationships.
   - Minimum 2 relationships per concept
   - Prefer over-extraction to under-extraction
   - Disconnected concepts indicate incomplete extraction
   ```

2. **Increase extraction temperature**: 0.3 → 0.5
   - Makes LLM more willing to infer implicit connections
   - Tradeoff: Slightly lower precision, higher recall

### Medium Impact, Medium Effort

3. **Simplify prompt structure**:
   - Move relationship examples to focused section at the end
   - Reduce MEC guidelines to key points only
   - Remove or minimize element linking (rarely used)

4. **Add relationship-focused prompt variant**:
   - Two-pass extraction: concepts first, then relationships
   - Or: separate relationship-only prompt that includes all extracted concepts

### Low Impact, High Effort

5. **Fine-tune extraction model** on MEC interview transcripts
6. **Implement relationship inference** as post-processing step
7. **Add explicit relationship completion** after extraction

## Known Limitations

### Schema Restrictions (By Design)

The MEC schema intentionally permits only sequential level connections:
```
attribute → functional_consequence → psychosocial_consequence → instrumental_value → terminal_value
```

Cross-level jumps are rejected to maintain chain integrity. This is **intentional** and **not a bug**.

### LLM Behavior

Current LLM (claude-sonnet-4-5) shows:
- Good concept extraction accuracy
- Poor relationship recall even with explicit instructions
- Conservative inference on implicit connections

This may be fundamental to the model or require different prompting strategies.

## Test Data

### Simulation Results (2026-02-04)

| Run | Nodes | Edges | Ratio | Status |
|-----|-------|-------|-------|--------|
| Before phase fix | 66 | 23 | 0.35 | Maximum turns (11) |
| After phase fix | 62 | 33 | 0.53 | depth_plateau (10) |
| With wildcards | 62 | 33 | 0.53 | depth_plateau (10) |

Even with wildcard schema permissions (later reverted), edge extraction remained poor.

### Extraction Logs Sample

```
extraction_complete: concept_count=7, relationship_count=0, latency_ms=9334
extraction_complete: concept_count=4, relationship_count=2, latency_ms=8470
extraction_complete: concept_count=5, relationship_count=4, latency_ms=9259
```

First turn had 7 concepts but **0 relationships** - a clear indication the LLM is not prioritizing relationship extraction.

## Related Files

- `src/llm/prompts/extraction.py` - Extraction prompt construction
- `src/services/extraction_service.py` - Extraction service logic
- `src/services/turn_pipeline/stages/extraction_stage.py` - Context formatting with Q&A highlight
- `config/methodologies/means_end_chain.yaml` - MEC extraction guidelines and examples

## Next Steps

If extraction improvement becomes a priority:

1. Start with explicit relationship quota (highest impact, lowest risk)
2. Test with increased temperature (0.3 → 0.5)
3. Consider two-pass extraction if single-pass remains insufficient

For now, the current extraction quality is **acceptable for synthetic testing** but may need improvement before production use with real respondents.
