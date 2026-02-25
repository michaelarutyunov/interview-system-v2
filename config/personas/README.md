# Personas Configuration

This directory contains persona definitions for synthetic respondent generation.

## Persona File Format

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

To see available personas, use the API:

```
GET /synthetic/personas
```

Or load programmatically:

```python
from src.core.persona_loader import load_persona, list_personas

# List all personas
personas = list_personas()

# Load specific persona
persona = load_persona("1_health_conscious")
```
