# Concept-Driven Coverage System

This document describes the concept-driven coverage and depth tracking system implemented in ADR-008.

## Overview

The interview system uses **concepts** to define WHAT to explore (semantic targets) and **methodologies** to define HOW to explore (node types, ladder, opening style). This two-layer architecture keeps concepts methodology-agnostic while enabling precise coverage tracking.

## Core Components

### 1. Concepts (`config/concepts/*.yaml`)

Concepts define the semantic elements to explore during an interview.

**Example: `oat_milk_v2.yaml`**
```yaml
id: oat_milk_v2
name: "Oat Milk"
methodology: means_end_chain

context:
  topic: "Oat milk consumption and preference drivers"
  insight: "When choosing plant-based milk, consumers weigh sensory experience against values"
  promise: "A plant-based milk that delivers café-quality texture"
  rtb: "Made with specially processed oats for creamy consistency"

elements:
  - id: 1
    label: "Creamy texture"
    aliases: ["silky", "smooth", "foam", "froth", "mouthfeel"]

  - id: 2
    label: "Plant-based"
    aliases: ["dairy-free", "no dairy", "vegan", "lactose-free"]

  - id: 3
    label: "Sustainability"
    aliases: ["eco-friendly", "planet", "environment", "carbon", "green"]
```

**Key Fields:**
- `id`: Unique concept identifier
- `methodology`: Which methodology to use (means_end_chain, jobs_to_be_done, etc.)
- `context`: Research brief for LLM prompts (topic, insight, promise, rtb)
- `elements`: Semantic elements to explore
  - `id`: Integer element ID (1, 2, 3...)
  - `label`: Human-readable name (used for substring matching)
  - `aliases`: Additional terms for fuzzy matching

### 2. Element Linking

When concepts are extracted during an interview, the system links them to concept elements using two approaches:

#### LLM-Based Linking (Primary)
The extraction prompt includes concept elements, and the LLM returns element IDs:

```python
# Extraction prompt includes:
## Concept Elements (Oat Milk):
  - Element 1: Creamy texture (aliases: silky, smooth, foam, froth, mouthfeel)
  - Element 2: Plant-based (aliases: dairy-free, vegan, lactose-free)

# LLM response includes:
{
  "concepts": [
    {
      "text": "silky foam",
      "node_type": "attribute",
      "linked_elements": [1]  # Linked to element 1
    }
  ]
}
```

#### Fallback Alias Matching
If LLM linking returns empty, the system uses substring matching on labels and aliases:

```python
# "silky foam" contains "foam" → linked to element 1
# "no stomach issues" contains "dairy" → linked to element 2
```

### 3. Coverage State

The system tracks coverage at the element level with depth validation:

```python
coverage_state = {
    "elements": {
        1: {  # "Creamy texture"
            "covered": True,
            "linked_node_ids": ["node_123", "node_456"],
            "types_found": ["attribute", "psychosocial_consequence"],
            "depth_score": 0.5,  # 2/4 levels (chain validation)
        },
        2: {  # "Plant-based"
            "covered": False,
            "linked_node_ids": [],
            "types_found": [],
            "depth_score": 0.0,
        },
    },
    "elements_covered": 1,
    "elements_total": 6,
    "overall_depth": 0.25,
}
```

### 4. Depth Tracking (Chain Validation)

Depth is calculated via **chain validation** - finding the longest connected path of node types among linked nodes.

**Algorithm:**
1. Get all nodes linked to an element
2. Get edges connecting these nodes (treat as undirected)
3. Build adjacency graph
4. Find longest connected path
5. `depth_score = longest_chain_length / methodology_ladder_length`

**Example:**
```
Element 1 has nodes: [A (attribute), B (psychosocial)]
Edges connecting them: [] (none)
→ longest_chain = 1 (each isolated)
→ depth_score = 1/4 = 0.25

Element 1 has nodes: [A (attribute), C (functional), B (psychosocial)]
Edges: [A→C, C→B]
→ longest_chain = 3 (A→C→B connected)
→ depth_score = 3/4 = 0.75
```

**Why chain validation matters:**
- Simply counting types (2/4 = 0.5) doesn't validate connection
- attribute + psychosocial with no functional might be unrelated thoughts
- Chain validation confirms actual laddering occurred

### 5. Depth-Aware Scoring

Scorers use the coverage state to drive strategy selection:

**CoverageGapScorer:**
```python
if not element_coverage.get("covered"):
    priority += 2  # Uncovered = high priority
elif element_coverage.get("depth_score", 0) < 0.5:
    priority += 1  # Shallow = medium priority
```

**StrategyService:**
Generates two types of coverage-focused strategies:
- `coverage_gap`: For uncovered elements
- `deepen_coverage`: For covered but shallow elements (depth < 0.5)

## File Structure

```
config/concepts/
├── oat_milk_v2.yaml          # Enhanced concept format
├── coffee_jtbd_v2.yaml       # Jobs-to-be-done concept
└── ...

src/
├── core/
│   └── concept_loader.py     # Load concepts with caching
├── domain/models/
│   └── concept.py            # Concept, ConceptElement, CoverageState
├── services/
│   └── depth_calculator.py   # Chain validation algorithm
└── persistence/repositories/
    └── graph_repo.py         # Coverage state building
```

## API Integration

### Session Creation
```bash
POST /sessions
{
  "concept_id": "oat_milk_v2"
}
```

### Turn Response
```json
{
  "graph_state": {
    "coverage_state": {
      "elements": {
        "1": {
          "covered": true,
          "depth_score": 0.5
        }
      },
      "elements_covered": 1,
      "elements_total": 6,
      "overall_depth": 0.25
    }
  }
}
```

## Adding New Concepts

1. Create YAML file in `config/concepts/`
2. Define elements with integer IDs, labels, and aliases
3. Add context (topic, insight, promise, rtb)
4. Test with `uv run pytest tests/unit/test_graph_repo.py`

## Backward Compatibility

- v1 concepts (string element IDs) still work via fallback parsing
- v1 concepts without aliases use label-only matching
- Empty `linked_elements` from LLM triggers alias matching

## References

- ADR-008: Concept Element Coverage System
- Plan: `~/.claude/plans/playful-questing-pizza.md`
