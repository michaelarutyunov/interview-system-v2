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

| Persona ID | Name | Description |
|------------|------|-------------|
| `health_conscious` | Health-Conscious Millennial | Prioritizes health and wellness, reads nutrition labels, values organic ingredients |
| `price_sensitive` | Budget-Conscious Shopper | Compares prices, looks for sales, seeks cost-effective alternatives |
| `convenience_seeker` | Busy Professional | Values time over cost, prioritizes convenience and ease of use |
| `quality_focused` | Quality Enthusiast | Appreciates premium quality, seeks the best products regardless of price |
| `sustainability_minded` | Environmentally Conscious Consumer | Prioritizes environmental impact, values sustainable packaging and sourcing |
| `skeptical_analyst` | Skeptical Analyst | Questions marketing claims, demands evidence, researches extensively |
| `social_conscious` | Socially Conscious Consumer | Influenced by peers, follows trends, cares about social values and identity |
| `minimalist` | Minimalist Pragmatist | Values simplicity, avoids unnecessary complexity, wants essential features only |

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
persona = load_persona("health_conscious")
```
