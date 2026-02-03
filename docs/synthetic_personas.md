# Synthetic Personas System

The Synthetic Personas system enables AI-to-AI interview simulations for testing and validation. It orchestrates an AI interviewer with AI-powered synthetic respondents to generate complete interview transcripts.

## Overview

- **Purpose**: Generate realistic interview transcripts for testing without requiring human respondents
- **Use Cases**:
  - Test interview methodology implementation
  - Validate questioning strategies
  - Benchmark system performance
  - Generate training data for evaluation models

## Available Personas

The system includes 5 pre-configured personas located in `config/personas/*.yaml`:

| Persona ID | Name | Description |
|------------|------|-------------|
| `health_conscious` | Health-Conscious Millennial | Prioritizes health and wellness, reads nutrition labels, values organic ingredients |
| `price_sensitive` | Budget-Conscious Shopper | Compares prices, looks for sales, seeks cost-effective alternatives |
| `convenience_seeker` | Busy Professional | Values time over cost, prioritizes convenience and ease of use |
| `quality_focused` | Quality Enthusiast | Appreciates premium quality, seeks the best products regardless of price |
| `sustainability_minded` | Environmentally Conscious Consumer | Prioritizes environmental impact, values sustainable packaging and sourcing |

## Usage

### Method 1: Simulation API (Recommended for Full Interviews)

The simulation service orchestrates a complete AI-to-AI interview:

```bash
curl -X POST "http://localhost:8000/simulation/interview" \
  -H "Content-Type: application/json" \
  -d '{
    "concept_id": "oat_milk_v2",
    "persona_id": "health_conscious",
    "max_turns": 10
  }'
```

**Response:**
```json
{
  "concept_id": "oat_milk_v2",
  "concept_name": "Oat Milk",
  "product_name": "Oat Milk",
  "objective": "Explore how consumers make decisions...",
  "methodology": "means_end_chain",
  "persona_id": "health_conscious",
  "persona_name": "Health-Conscious Millennial",
  "session_id": "uuid",
  "total_turns": 10,
  "turns": [
    {
      "turn_number": 0,
      "question": "Opening question...",
      "response": "I really like the creamy texture...",
      "strategy_selected": null,
      "should_continue": true,
      "latency_ms": 1250
    }
  ],
  "status": "completed"
}
```

**Parameters:**
- `concept_id`: Concept to use (e.g., `oat_milk_v2`, `coffee_jtbd_v2`)
- `persona_id`: Persona from available personas
- `max_turns`: Maximum turns before forcing stop (default: 10)
- `session_id`: Optional session ID (generates new if not provided)

**Output:** Results are **automatically saved** to `synthetic_interviews/` as JSON files with naming pattern: `{timestamp}_{concept_id}_{persona_id}.json`

---

### Method 2: Single Synthetic Response

Generate a single synthetic response to a specific question:

```bash
curl -X POST "http://localhost:8000/synthetic/respond" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why is creamy texture important to you?",
    "session_id": "test-session-123",
    "persona": "health_conscious",
    "interview_context": {
      "product_name": "Oat Milk",
      "turn_number": 3
    }
  }'
```

**Response:**
```json
{
  "response": "I really like the creamy texture because it feels satisfying and reminds me of dairy milk without the heaviness.",
  "persona": "health_conscious",
  "persona_name": "Health-Conscious Millennial",
  "question": "Why is creamy texture important to you?",
  "latency_ms": 1100,
  "tokens_used": {"prompt_tokens": 150, "completion_tokens": 45},
  "used_deflection": false
}
```

**Parameters:**
- `question`: The interviewer's question
- `session_id`: Session identifier for context tracking
- `persona`: Persona ID (default: `health_conscious`)
- `interview_context`: Optional context with product_name, turn_number
- `use_deflection`: Override deflection behavior (null = use 20% chance)

---

### Method 3: Multi-Persona Response

Generate responses from multiple personas simultaneously:

```bash
curl -X POST "http://localhost:8000/synthetic/multi" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What matters most to you when choosing oat milk?",
    "session_id": "test-session-456",
    "personas": ["health_conscious", "price_sensitive", "sustainability_minded"]
  }'
```

---

## Response Patterns

The synthetic service generates varied response patterns to simulate authentic respondent behavior:

| Pattern | Frequency | Description |
|---------|-----------|-------------|
| Detailed | 40% | 2-3 sentences sharing thoughts and reasons |
| Medium | 40% | 1-2 sentences with some explanation |
| Brief | 15% | Short phrases or simple answers |
| Acknowledgment | 5% | "Okay", "I see", "That makes sense" |

**Deflection:** ~20% of responses include deflection patterns where the respondent redirects the conversation:
- "That's okay, but what really matters to me is..."
- "I guess, but I'm more focused on..."
- "That's not really my main concern..."

## Creating Custom Personas

Add new personas by creating YAML files in `config/personas/`:

```yaml
id: my_custom_persona
name: "My Custom Persona"
description: "A brief description of this persona"

traits:
  - "trait 1"
  - "trait 2"
  - "trait 3"

speech_pattern: |
  Description of how this persona speaks,
  including terminology, tone, and focus areas.

response_patterns:
  detailed: 0.45
  medium: 0.4
  brief: 0.1
  acknowledgment: 0.05

deflection_patterns:
  - "Deflection phrase 1"
  - "Deflection phrase 2"
```

**Fields:**
- `id`: Unique identifier used in API calls
- `name`: Human-readable name
- `description`: Brief description
- `traits`: List of behavioral traits
- `speech_pattern`: Speaking style description
- `response_patterns`: Optional response distribution
- `deflection_patterns`: Optional deflection phrases

## Output Directory

Simulation results are automatically saved to `synthetic_interviews/`:

```
synthetic_interviews/
├── 20260129_123456_oat_milk_v2_health_conscious.json
├── 20260129_123507_oat_milk_v2_price_sensitive.json
└── 20260129_124015_coffee_jtbd_v2_quality_focused.json
```

**Filename format:** `{timestamp}_{concept_id}_{persona_id}.json`

**File contents:**
- Complete simulation result (questions, responses, strategies)
- Metadata (concept, methodology, persona, total turns)
- Turn-by-turn analysis (questions, responses, strategies, latencies)

## Python API Usage

```python
from src.services.simulation_service import get_simulation_service
import asyncio
from src.persistence.repositories.graph_repo import GraphRepository
import aiosqlite

async def run_simulation():
    # Get database connection
    db = await aiosqlite.connect("data/interviews.db")
    graph_repo = GraphRepository(db)

    # Create simulation service
    sim_service = get_simulation_service(graph_repo=graph_repo)

    # Run simulation
    result = await sim_service.simulate_interview(
        concept_id="oat_milk_v2",
        persona_id="health_conscious",
        max_turns=10
    )

    print(f"Simulation complete: {result.total_turns} turns")

    # Output is automatically saved to synthetic_interviews/
    await db.close()

# Run
asyncio.run(run_simulation())
```

## Troubleshooting

**Error: Unknown persona**
- Check `config/personas/` for available persona IDs
- Verify YAML file exists and is valid

**Error: Concept not found**
- Check `config/concepts/` for available concept IDs
- Verify concept YAML is valid and includes `objective` field

**Simulation stops early**
- Check `max_turns` parameter in request
- Review session config in database for turn limits
- Strategy "close" will terminate the interview

**Responses are generic**
- Verify persona configuration has specific traits and speech patterns
- Check that `interview_context` includes product_name and turn_number
- Consider increasing `temperature` in LLM client for more variety
