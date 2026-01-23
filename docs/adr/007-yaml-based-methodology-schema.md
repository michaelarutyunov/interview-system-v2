# ADR-007: YAML-Based Methodology Schema Externalization

## Status
Proposed

## Context

### The Problem: Schema Fragmentation

The extraction schema (node types, edge types, connection rules) is currently **hardcoded across 3 locations** without enforcement:

1. **Enums** in `src/domain/models/knowledge_graph.py`:
   ```python
   class NodeType(str, Enum):
       ATTRIBUTE = "attribute"
       FUNCTIONAL_CONSEQUENCE = "functional_consequence"
       # ... (5 types total)
   ```

2. **Descriptions** in `src/llm/prompts/extraction.py`:
   ```python
   NODE_TYPE_DESCRIPTIONS = {
       "attribute": "Concrete product feature...",
       # ... (manually maintained, can diverge from enums)
   }
   ```

3. **Data models** with no validation:
   ```python
   class ExtractedConcept(BaseModel):
       node_type: str  # ❌ Accepts any string, no schema validation
   ```

**Result**: The LLM is instructed on valid types via prompt text, but the code doesn't enforce them. Invalid node types and edge connections are silently accepted.

### Robustness Issues Discovered

Analysis revealed multiple validation gaps:
- Invalid `node_type` values accepted (e.g., `"bogus_type"`)
- Invalid `relationship_type` values accepted
- Invalid edge connections accepted (e.g., `terminal_value → attribute`)
- Confidence values outside [0, 1] not validated before Pydantic
- No validation that edge type allows specific source-target pairs

### Extensibility Limitations

The current hardcoded approach prevents:
- Adding new methodologies (ZMET, grounded theory) without code changes
- Testing with different schemas without redeployment
- Experimenting with schema variations
- Non-developers editing schema definitions

## Decision

**Externalize methodology schema into YAML configuration files** with dynamic loading and validation.

### Architecture

```
config/methodologies/
├── means_end_chain.yaml    # MEC schema (50 lines)
├── zmet.yaml               # Future: ZMET schema
└── grounded_theory.yaml    # Future: Open coding schema

Components:
- MethodologySchema (Pydantic model)
- load_methodology() (YAML loader with cache)
- Validation at extraction time (reject invalid types/connections)
```

### Schema Format

```yaml
name: means_end_chain
version: "2.0"
description: "Laddering: attributes → consequences → values"

node_types:
  - name: attribute
    description: "Concrete product feature"
    examples: ["creamy texture", "plant-based"]

edge_types:
  - name: leads_to
    description: "Causal relationship"

valid_connections:
  leads_to:
    - [attribute, attribute]              # Same-level allowed
    - [attribute, functional_consequence] # Adjacent upward
    # ... (no skip-level connections)

  revises:
    - ["*", "*"]  # Any node can revise any node
```

**Key Properties:**
- ~50 lines total (vs. scattered across 3+ files)
- No mode configuration (belongs in mode-specific configs)
- No LLM prompts (generated from schema in code)
- No unused validation rules (only what's actually enforced)

### Implementation Components

**1. Schema Model** (`src/domain/models/methodology_schema.py`):
```python
class MethodologySchema(BaseModel):
    name: str
    node_types: List[NodeTypeSpec]
    edge_types: List[EdgeTypeSpec]
    valid_connections: Dict[str, List[List[str]]]

    def is_valid_node_type(name: str) -> bool
    def is_valid_edge_type(name: str) -> bool
    def is_valid_connection(edge, source, target) -> bool
```

**2. Loader** (`src/core/schema_loader.py`):
```python
# Module-level cache (singleton)
_cache: dict[str, MethodologySchema] = {}

def load_methodology(name: str) -> MethodologySchema:
    # Load from config/methodologies/{name}.yaml
    # Cache on first load
```

**3. Validation in ExtractionService**:
```python
class ExtractionService:
    def __init__(self, methodology: str = "means_end_chain"):
        self.schema = load_methodology(methodology)

    def _parse_concepts(self, raw_concepts):
        # Validate node_type against schema
        if not self.schema.is_valid_node_type(concept.node_type):
            log.warning("invalid_node_type")
            continue  # Skip invalid

    def _parse_relationships(self, raw_rels, concept_types):
        # Validate edge type and connection
        if not self.schema.is_valid_connection(rel.type, src_type, tgt_type):
            log.warning("invalid_connection")
            continue  # Skip invalid
```

**4. Prompt Generation**:
```python
def get_extraction_system_prompt(methodology: str):
    schema = load_methodology(methodology)

    # Generate descriptions from schema
    node_types_str = schema.get_node_descriptions()  # "attr: desc (e.g., ex1, ex2)"
    edge_types_str = schema.get_edge_descriptions()

    # Build prompt dynamically
```

## Rationale

### Benefits

1. **Single Source of Truth**: Schema defined once in YAML, not scattered across Python files
2. **Validation Enforcement**: Invalid types/connections rejected at extraction time
3. **Extensibility**: Add new methodologies by creating YAML files (no code changes)
4. **Testing**: Easier to test with different schemas without redeployment
5. **Documentation**: YAML serves as human-readable methodology documentation
6. **Separation of Concerns**: Ontology (schema) separated from behavior (code)
7. **Methodology-Agnostic**: Core extraction logic doesn't hardcode MEC assumptions

### Costs

1. **Schema Validation Overhead**: Adds ~5-10ms per extraction (mitigated by caching schema)
2. **YAML Complexity**: Non-developers may find YAML harder to edit than Python
3. **Breaking Changes Risk**: Changing schema can invalidate historical data (future: versioning)
4. **Development Effort**: ~3 days to implement vs. continuing with hardcoded approach

### Why Not Alternatives?

| Alternative | Rejected Because |
|-------------|------------------|
| **Status quo (hardcoded)** | Fragmented definitions, no validation, not extensible, methodology-specific code |
| **JSON instead of YAML** | YAML more human-readable for configuration; JSON fine but offers no advantage here |
| **Database storage** | Overkill for static ontology that doesn't change at runtime; YAML is version-controlled |
| **Python dataclasses** | Still hardcoded; doesn't allow non-developers to edit; no hot-reload capability |
| **Keep enums + add validation** | Doesn't solve fragmentation or extensibility; still methodology-specific code |

## Consequences

### Positive

1. **Robust Validation**: LLM-generated invalid data caught and rejected immediately
2. **Clear Error Messages**: Log warnings explain exactly what's invalid and why
3. **Extensible to Other Methodologies**: ZMET, grounded theory, etc. via new YAML files
4. **Version Control**: Schema changes tracked in git like any other config
5. **Testing Flexibility**: Can test with custom schemas without code changes
6. **Documentation**: YAML file documents the methodology ontology clearly

### Negative

1. **Migration Effort**: Requires updating extraction service, prompt generation, tests
2. **Schema Synchronization**: Must ensure YAML and code stay aligned (Pydantic helps)
3. **Historical Data**: Old sessions with invalid data may need migration (future work)
4. **Validation Overhead**: Small performance cost per extraction (~5-10ms)

### Neutral

1. **Enums Kept for IDE**: Can keep NodeType/EdgeType enums for IDE autocomplete but mark as deprecated
2. **Backward Compatibility**: Existing sessions continue working (validation is opt-in per session)
3. **Cache Performance**: Schema cached on first load, no repeated YAML parsing

## Implementation Plan

### Phase 1: Schema Infrastructure
- Create `config/methodologies/means_end_chain.yaml`
- Create `src/domain/models/methodology_schema.py` (Pydantic models)
- Create `src/core/schema_loader.py` (load + cache function)
- Unit tests for schema loading

### Phase 2: Extraction Validation
- Modify `ExtractionService.__init__()` to load schema
- Update `_parse_concepts()` to validate node types
- Update `_parse_relationships()` to validate edge types and connections
- Unit tests for validation logic

### Phase 3: Prompt Generation
- Update `get_extraction_system_prompt()` to use schema
- Remove hardcoded `NODE_TYPE_DESCRIPTIONS` and `EDGE_TYPE_DESCRIPTIONS`
- Tests for prompt generation from schema

### Phase 4: Cleanup
- Mark `NodeType` and `EdgeType` enums as deprecated (or remove if not needed for IDE)
- Update documentation to reference YAML as source of truth
- Integration tests with full extraction pipeline

## Verification

```bash
# 1. Schema loading
pytest tests/unit/test_schema.py -v

# 2. Validation rejects invalid data
# - node_type="bogus" → concept skipped, warning logged
# - terminal_value → attribute edge → rejected, warning logged

# 3. Existing tests still pass
pytest tests/unit/test_extraction_service.py -v
pytest tests/unit/test_extraction_prompts.py -v

# 4. Integration test with real session
# - Verify prompts contain schema descriptions
# - Verify invalid extractions are rejected
```

## Future Enhancements

1. **Schema Versioning**: Track schema changes over time, support v1/v2 migrations
2. **Multi-Methodology Sessions**: Load different schemas per session
3. **Schema Validation UI**: Web interface for editing and validating schemas
4. **Custom Validation Rules**: User-defined validation logic in YAML
5. **Graph Visualization Config**: Node/edge styling from schema metadata

## Related Decisions

- **ADR-004**: Two-Tier Scoring System - Unaffected (scoring config separate)
- **ADR-005**: Dual-Mode Interview Architecture - Unaffected (mode config separate)
- **ADR-006**: Enhanced Scoring Architecture - Unaffected (scoring logic separate)

## References

- **v1 schema**: `/home/mikhailarutyunov/projects/graph-enabled-ai-interviewer/config/schemas/means_end_chain.yaml`
- **Extraction robustness analysis**: Session discussion on validation gaps
- **Reynolds & Gutman (1988)**: Laddering methodology foundation
- **Pydantic**: Schema validation via Python type hints
