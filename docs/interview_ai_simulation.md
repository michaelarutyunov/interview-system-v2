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

Personas are organized into two directories under `config/personas/`:
- `domains/` — topic-specific personas for realistic interviews
- `edge_cases/` — behavioral stress-test personas for validating strategy logic

### Domain Personas

| Persona ID | File | Description |
|------------|------|-------------|
| `baseline_cooperative` | `domains/baseline_cooperative.yaml` | Standard respondent — answers directly, follows conversational flow |
| `glp1_user` | `domains/glp1_user.yaml` | Person with lived GLP-1 medication experience — realistic domain vocabulary |

### Edge-Case Personas (Testing)

| Persona ID | File | Purpose |
|------------|------|---------|
| `brief_responder` | `edge_cases/brief_responder.yaml` | Tests `anchor` trigger on short answers |
| `verbose_tangential` | `edge_cases/verbose_tangential.yaml` | Tests noise handling and `bridge` firing on low specificity |
| `emotionally_reactive` | `edge_cases/emotionally_reactive.yaml` | Tests charge safety gates and `ground` strategy |
| `fatiguing_responder` | `edge_cases/fatiguing_responder.yaml` | Tests `revitalize` mechanism mid-interview |
| `single_topic_fixator` | `edge_cases/single_topic_fixator.yaml` | Tests node exhaustion and rotation penalties |
| `skeptical_analyst` | `edge_cases/skeptical_analyst.yaml` | Tests challenging engagement and evidence demands |
| `uncertain_hedger` | `edge_cases/uncertain_hedger.yaml` | Tests `explore_constructs` and `validate` on hedging |
| `retrospective_rationalizer` | `edge_cases/retrospective_rationalizer.yaml` | Tests post-hoc justification and consistency probing |

## Usage

### Method 1: Simulation API (Recommended for Full Interviews)

The simulation service orchestrates a complete AI-to-AI interview:

```bash
curl -X POST "http://localhost:8000/simulation/interview" \
  -H "Content-Type: application/json" \
  -d '{
    "concept_id": "glp1_food_mec",
    "persona_id": "baseline_cooperative",
    "max_turns": 10
  }'
```

**Response:**
```json
{
  "concept_id": "glp1_food_mec",
  "concept_name": "GLP-1 Medication and Food Choices",
  "product_name": "GLP-1 Medication",
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
        "convgraph.state.max_depth": 0.5,
        "response.semantic.llm.response_depth": "moderate",
        "response.semantic.llm.engagement": 0.8,
        "response.semantic.llm.certainty": 0.7
      },
      "node_signals": {...},
      "score_decomposition": [...],
      "strategy_selected": "ascend",
      "focus_node_id": "abc-123",
      "strategy_alternatives": [
        {"strategy": "ascend", "score": 0.85},
        {"strategy": "branch", "score": 0.62}
      ],
      "should_continue": true,
      "latency_ms": 1250
    }
  ],
  "status": "completed"
}
```

**Parameters:**
- `concept_id`: Concept to use from `config/concepts/` (e.g., `glp1_food_mec`, `coffee_jtbd_v2`, `zerofizz_beverage_jtbd`)
- `persona_id`: Persona from available personas (e.g., `baseline_cooperative`)
- `max_turns`: Maximum turns before forcing stop (default: from concept config)
- `export_format`: Export format - `json`, `markdown`, or `csv` (default: `json`)

**Output:** Results are **automatically saved** to `synthetic_interviews/` as JSON files with naming pattern: `{timestamp}_{concept_id}_{persona_id}.json`

**Key Features:**
- **Full Score Decomposition**: Each turn includes `score_decomposition` with joint (strategy, node) scoring breakdown
- **Signal Contributions**: Per-strategy signal contribution tracking with phase multipliers and bonuses
- **Strategy Alternatives**: Complete ranking of alternative strategies with scores
- **Node Signals**: Per-node signal values for convgraph.node.*, meta.node.*, including per-concept LLM quality signals (elaboration, charge)
- **CSV Export**: Use `generate_scoring_csv.py` script to export live score decomposition to CSV format

### Score Decomposition Format

Each turn in the simulation JSON includes a `score_decomposition` array with detailed scoring breakdown:

```json
{
  "turn_number": 3,
  "score_decomposition": [
    {
      "strategy": "ascend",
      "node_id": "",
      "signal_contributions": {
        "response.semantic.llm.response_depth.shallow": 0.8,
        "convgraph.state.max_depth": -0.3,
        "response.semantic.llm.engagement.high": 0.7
      },
      "base_score": 1.2,
      "phase_multiplier": 1.3,
      "phase_bonus": 0.3,
      "final_score": 1.86,
      "rank": 1,
      "selected": true
    },
    {
      "strategy": "ascend",
      "node_id": "abc-123-def",
      "signal_contributions": {
        "convgraph.node.exhaustion.low": 1.0,
        "convgraph.node.focus.streak.low": 0.5
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
- `node_id`: UUID for the scored node (empty string for `node_binding: none` strategies like `revitalize`)
- `signal_contributions`: Per-signal weight × value contributions
- `base_score`: Sum of signal contributions before phase adjustments
- `phase_multiplier`: Multiplicative phase weight (e.g., 1.3x for mid-phase ascend)
- `phase_bonus`: Additive phase bonus (e.g., +0.3 for mid-phase ascend)
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

The synthetic service generates varied response patterns to simulate authentic respondent behavior in a text-only chat format. Responses are calibrated to be conversational, not essay-like.

### Response Length Distribution

| Pattern | Default | Description |
|---------|---------|-------------|
| Brief | 15% | 10–25 words. One fragment or short statement. No explanation. |
| Medium | 40% | 25–60 words. One idea, maybe a quick example. |
| Detailed | 40% | 60–100 words. Two ideas at most. Never a structured paragraph. |
| Acknowledgment | 5% | 2–8 words. "Yeah", "not really", "I guess so", "hmm not sure". |

Per-persona distributions can override these defaults (e.g., `baseline_cooperative` uses detailed: 0.20, medium: 0.50, brief: 0.25).

### Chat-Style Response Rules

The system prompt enforces realistic chat behavior:

- **No stage directions** — never write `*pauses*`, `*thinks*`, `*shifts*`, or any asterisk actions
- **No structured paragraphs** — chat messages are flat, just sentences
- **Max 2 distinct ideas per response** — circling one idea in different words is fine and realistic
- **No summaries at the end** — just stop when the thought is done
- **Trailing off is fine** — "I don't know, it's just kind of..." is a complete response
- **Avoid textbook-complete answers** that cover every angle of the question
- **Avoid restating the interviewer's words** back at them

### Deflection

~20% of responses include deflection patterns where the respondent redirects the conversation:
- "That's okay, but what really matters to me is..."
- "I guess, but I'm more focused on..."
- "That's not really my main concern..."
- "I'd say it's more about..."
- "Not so much that, but I do care about..."

Per-persona deflection patterns are defined in persona YAML under `deflection_patterns:`.

## Creating Custom Personas

Add new personas by creating YAML files in `config/personas/domains/` (topic-specific) or `config/personas/edge_cases/` (behavioral stress-test):

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
persona = load_persona("baseline_cooperative")
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
        concept_id="glp1_food_mec",
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
uv run python scripts/run_simulation.py --concept glp1_food_mec --persona baseline_cooperative --max-turns 10

# Run with explicit phase control (4 early, 4 mid, 2 late = 10 total)
uv run python scripts/run_simulation.py --concept glp1_food_mec --persona baseline_cooperative --phase-turns 4-4-2

# Output files:
# - synthetic_interviews/TIMESTAMP_glp1_food_mec_baseline_cooperative.json
# - synthetic_interviews/TIMESTAMP_glp1_food_mec_baseline_cooperative_scoring.csv
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--concept` | yes | Concept ID from `config/concepts/` |
| `--persona` | yes | Persona ID from `config/personas/` |
| `--max-turns` | no | Max turns (default: 10, or derived from `--phase-turns`) |
| `--phase-turns` | no | Phase allocation as `N-N-N` (e.g. `4-4-2`). Overrides `--max-turns` (sum). Overrides `interview_config.yaml` phase proportions. |

The CSV export contains live `score_decomposition` data from the simulation JSON, providing per-turn scoring breakdown with signal contributions, phase multipliers, and strategy rankings.

## Post-Simulation Analysis

After generating simulation JSONs, several scripts produce derived outputs:

### Individual Generators

| Script | Location | Output |
|--------|----------|--------|
| `generate_transcript.py` | `scripts/reporting/` | Human-readable markdown transcript |
| `generate_causal_chains.py` | `scripts/reporting/` | Causal chain extraction (surface + canonical, tier-classified, methodology-agnostic with `chain_rules` config) |
| `generate_mermaid_graph.py` | `scripts/reporting/` | Visual graph diagram (.mmd + .png) |
| `generate_scoring_csv.py` | `scripts/reporting/` | Flat CSV from `score_decomposition` |
| `generate_scoring_summary.md` | `scripts/reporting/` | Aggregated markdown tables (firing rates, dead signals, budget decomposition) |
| `generate_latency_report.py` | `scripts/reporting/` | Pipeline timing + LLM cost analysis from session log |
| `generate_reviews.py` | `scripts/reporting/` | Markdown review with strategy distribution, graph health, signal diagnostics |
| `extract_simulation_data.py` | `scripts/diagnostics/` | Parquet tables (turns, scoring, interviews) for analytical queries |
| `analyze_signal_redundancy.py` | `scripts/diagnostics/` | Signal activity/decisiveness audit |
| `edge_extraction_diff.py` | `scripts/diagnostics/` | Per-turn edge extraction diagnostics (confirmed vs rejected, confidence distribution) |

### Unified Export (Recommended)

Run all individual generators at once into a single timestamped folder:

```bash
uv run python scripts/reporting/export_interview.py synthetic_interviews/20260424_*.json
```

Produces `reports/interviews/<timestamp>/` with:

```
reports/interviews/<timestamp>/
├── 00_meta.yaml              # Interview metadata
├── 01_transcript.md          # Q&A transcript
├── 02_causal_chains.md       # Causal chain analysis
├── 03_graph.mmd              # Mermaid graph source
├── 03_graph.png              # Rendered graph diagram
├── 04_scoring.csv            # Raw scoring decomposition
├── 04_scoring_summary.md     # Aggregated scoring tables
├── 05_latency/               # Pipeline timing & cost analysis
│   ├── summary.md
│   ├── llm_calls.csv
│   └── stages.csv
├── 06_insights.md            # Placeholder for qualitative review
└── 99_session.log            # Copied session log
```

All scripts use the current signal taxonomy (`convgraph.*`, `response.semantic.llm.*`, `meta.saturation.*`, `interview.*`). See `.claude/context/simulation-export-schema.md` for the stable field contract.

## Troubleshooting

**Error: Unknown persona**
- Check `config/personas/` for available persona IDs
- Verify YAML file exists and is valid
- Use `baseline_cooperative` for standard testing

**Error: Concept not found**
- Check `config/concepts/` for available concept IDs
- Verify concept YAML is valid and includes `objective` field
- Common concepts: `glp1_food_mec`, `glp1_food_mec_strict`, `coffee_jtbd_v2`, `zerofizz_beverage_jtbd`, `zerofizz_beverage_mec`

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
