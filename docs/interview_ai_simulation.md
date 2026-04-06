# Interview AI Simulation System

The Interview AI Simulation system enables AI-to-AI interview simulations for testing and validation. It orchestrates an AI interviewer with AI-powered synthetic respondents to generate complete interview transcripts.

## Overview

- **Purpose**: Generate realistic interview transcripts for testing without requiring human respondents
- **Use Cases**:
  - Test interview methodology implementation
  - Validate questioning strategies
  - Benchmark system performance
  - Generate training data for evaluation models

## Available Personas

### Standard Personas

| Persona ID | Name | Description |
|------------|------|-------------|
| `baseline_cooperative` | Baseline Cooperative | Standard respondent — answers directly, follows conversational flow |

### Edge-Case Personas (Testing)

| Persona ID | Name | Purpose |
|------------|------|---------|
| `brief_responder` | Brief Responder | Tests `dig_motivation` trigger on short answers |
| `verbose_tangential` | Verbose Tangential | Tests noise handling and `clarify` firing on low specificity |
| `emotionally_reactive` | Emotionally Reactive | Tests `explore_emotions` and valence safety gates |
| `fatiguing_responder` | Fatiguing Responder | Tests `revitalize` mechanism mid-interview |
| `single_topic_fixator` | Single Topic Fixator | Tests node exhaustion and rotation penalties |
| `skeptical_analyst` | Skeptical Analyst | Tests `probe_attributions` with challenging engagement |
| `uncertain_hedger` | Uncertain Hedger | Tests `explore_constructs` and `validate` on hedging |
| `social_conscious` | Social Conscious | Tests peer influence and trend-based decision patterns |
| `minimalist` | Minimalist | Tests preference for simplicity and feature avoidance |

### Legacy Consumer Personas (Deprecated)

> **Note:** The following personas are retained for backward compatibility but are not recommended for new simulations. Use `baseline_cooperative` for standard testing.

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
    "concept_id": "headphones_mec",
    "persona_id": "baseline_cooperative",
    "max_turns": 10
  }'
```

**Response:**
```json
{
  "concept_id": "headphones_mec",
  "concept_name": "Headphones",
  "product_name": "Headphones",
  "objective": "Explore how consumers make decisions...",
  "methodology": "means_end_chain",
  "persona_id": "baseline_cooperative",
  "persona_name": "Baseline Cooperative",
  "session_id": "uuid",
  "total_turns": 10,
  "turns": [
    {
      "turn_number": 1,
      "question": "Opening question...",
      "response": "I really like the sound quality...",
      "signals": {
        "graph.max_depth": 0.5,
        "llm.response_depth": "moderate",
        "llm.engagement": 0.8
      },
      "node_signals": {...},
      "score_decomposition": [...],
      "strategy_selected": "deepen",
      "focus_node_id": "abc-123",
      "strategy_alternatives": [
        {"strategy": "deepen", "score": 0.85},
        {"strategy": "clarify", "score": 0.62}
      ],
      "should_continue": true,
      "latency_ms": 1250
    }
  ],
  "status": "completed"
}
```

**Parameters:**
- `concept_id`: Concept to use from `config/concepts/` (e.g., `headphones_mec`, `oatmilk_mec`)
- `persona_id`: Persona from available personas (e.g., `baseline_cooperative`)
- `max_turns`: Maximum turns before forcing stop (default: from concept config)
- `export_format`: Export format - `json`, `markdown`, or `csv` (default: `json`)

**Output:** Results are **automatically saved** to `synthetic_interviews/` as JSON files with naming pattern: `{timestamp}_{concept_id}_{persona_id}.json`

**Key Features:**
- **Full Score Decomposition**: Each turn includes `score_decomposition` with Stage 1 (strategy-level) and Stage 2 (node-level) scoring breakdown
- **Signal Contributions**: Per-strategy signal contribution tracking with phase multipliers and bonuses
- **Strategy Alternatives**: Complete ranking of alternative strategies with scores
- **Node Signals**: Per-node signal values for graph.node.*, technique.node.*, meta.node.*
- **CSV Export**: Use `generate_scoring_csv.py` script to export live score decomposition to CSV format

### Score Decomposition Format

Each turn in the simulation JSON includes a `score_decomposition` array with detailed scoring breakdown:

```json
{
  "turn_number": 3,
  "score_decomposition": [
    {
      "strategy": "deepen",
      "node_id": "",
      "signal_contributions": {
        "llm.response_depth.shallow": 0.8,
        "graph.max_depth": -0.3,
        "llm.engagement.high": 0.7
      },
      "base_score": 1.2,
      "phase_multiplier": 1.3,
      "phase_bonus": 0.3,
      "final_score": 1.86,
      "rank": 1,
      "selected": true
    },
    {
      "strategy": "deepen",
      "node_id": "abc-123-def",
      "signal_contributions": {
        "graph.node.exhaustion_score.low": 1.0,
        "graph.node.focus_streak.low": 0.5
      },
      "base_score": 1.5,
      "phase_multiplier": 1.3,
      "phase_bonus": 0.0,
      "final_score": 1.95,
      "rank": 1,
      "selected": true
    }
  ]
}
```

**Fields:**
- `strategy`: Strategy name
- `node_id`: Empty string for Stage 1 (strategy-level), UUID for Stage 2 (node-level)
- `signal_contributions`: Per-signal weight × value contributions
- `base_score`: Sum of signal contributions before phase adjustments
- `phase_multiplier`: Multiplicative phase weight (e.g., 1.3x for mid-phase deepen)
- `phase_bonus`: Additive phase bonus (e.g., +0.3 for mid-phase deepen)
- `final_score`: (base_score × phase_multiplier) + phase_bonus
- `rank`: Ranking position (1 = highest score)
- `selected`: Whether this strategy-node pair was selected

---

### Method 2: Single Synthetic Response

Generate a single synthetic response to a specific question:

```bash
curl -X POST "http://localhost:8000/synthetic/respond" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why is creamy texture important to you?",
    "session_id": "test-session-123",
    "persona": "baseline_cooperative",
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
  "persona": "baseline_cooperative",
  "persona_name": "Baseline Cooperative",
  "question": "Why is creamy texture important to you?",
  "latency_ms": 1100,
  "tokens_used": {"prompt_tokens": 150, "completion_tokens": 45},
  "used_deflection": false
}
```

**Parameters:**
- `question`: The interviewer's question
- `session_id`: Session identifier for context tracking
- `persona`: Persona ID (default: `baseline_cooperative`)
- `interview_context`: Optional context with product_name, turn_number
- `use_deflection`: Override deflection behavior (null = use 20% chance)

---

### Method 3: Multi-Persona Response

Generate responses from multiple personas simultaneously:

```bash
curl -X POST "http://localhost:8000/synthetic/respond/multi" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What matters most to you when choosing oat milk?",
    "session_id": "test-session-456",
    "personas": ["baseline_cooperative", "brief_responder", "verbose_tangential"]
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

## Persona File Format Reference

Each persona YAML file should follow this structure:

```yaml
id: health_conscious
name: "Health-Conscious Millennial"
description: "A millennial who prioritizes health and wellness in purchasing decisions"

traits:
  - "prioritizes health and wellness"
  - "reads nutrition labels carefully"
  - "values organic and natural ingredients"
  - "avoids artificial additives and preservatives"
  - "willing to pay more for health benefits"

speech_pattern: |
  Uses health-related terminology (nutrients, ingredients, wellness),
  focuses on how products affect their body and long-term health,
  mentions specific health concerns or goals

response_patterns:
  detailed: 0.4    # 40% detailed responses (2-3 sentences)
  medium: 0.4      # 40% medium responses (1-2 sentences)
  brief: 0.15       # 15% brief responses (short phrases)
  acknowledgment: 0.05  # 5% acknowledgments ("Okay", "I see")

deflection_patterns:
  - "That's okay, but what really matters to me is..."
  - "I guess, but I'm more focused on..."
  - "That's not really my main concern..."
```

To see available personas programmatically:

```python
from src.core.persona_loader import load_persona, list_personas

# List all personas
personas = list_personas()

# Load specific persona
persona = load_persona("health_conscious")
```

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
from src.services.simulation_service import SimulationService
import asyncio
from src.persistence.repositories.graph_repo import GraphRepository
import aiosqlite

async def run_simulation():
    # Get database connection
    db = await aiosqlite.connect("data/interview.db")
    graph_repo = GraphRepository(db)
    
    # Create simulation service
    sim_service = SimulationService(graph_repo=graph_repo)
    
    # Run simulation
    result = await sim_service.simulate_interview(
        concept_id="headphones_mec",
        persona_id="baseline_cooperative",
        max_turns=10
    )
    
    print(f"Simulation complete: {result.total_turns} turns")
    
    # Output is automatically saved to synthetic_interviews/
    await db.close()

# Run
asyncio.run(run_simulation())
```

## Batch Simulation with Script

For running multiple simulations efficiently, use the provided script:

```bash
# Run single simulation
uv run python scripts/run_simulation.py headphones_mec baseline_cooperative 10

# Output files:
# - synthetic_interviews/TIMESTAMP_headphones_mec_baseline_cooperative.json
# - synthetic_interviews/TIMESTAMP_headphones_mec_baseline_cooperative_scoring.csv
```

The CSV export contains live `score_decomposition` data from the simulation JSON, providing per-turn scoring breakdown with signal contributions, phase multipliers, and strategy rankings.

## Troubleshooting

**Error: Unknown persona**
- Check `config/personas/` for available persona IDs
- Verify YAML file exists and is valid
- Use `baseline_cooperative` for standard testing

**Error: Concept not found**
- Check `config/concepts/` for available concept IDs
- Verify concept YAML is valid and includes `objective` field
- Common concepts: `headphones_mec`, `oatmilk_mec`, `coffee_jtbd`

**Simulation stops early**
- Check `max_turns` parameter in request
- Review session config in database for turn limits
- Strategy with `generates_closing_question: true` will terminate the interview
- Check `should_continue: false` in last turn response

**Responses are generic**
- Verify persona configuration has specific traits and speech patterns
- Check that `interview_context` includes product_name and turn_number
- Consider increasing `temperature` in LLM client for more variety

**Score decomposition missing**
- Ensure simulation completed successfully (check `status: "completed"`)
- Verify JSON file was saved to `synthetic_interviews/` directory
- Use `generate_scoring_csv.py` to export scoring data if present

**CSV export empty or missing data**
- Verify simulation JSON contains `score_decomposition` field in each turn
- Check that `generate_scoring_csv.py` is using correct input file path
- Ensure simulation ran with D2 architecture (not legacy format)
