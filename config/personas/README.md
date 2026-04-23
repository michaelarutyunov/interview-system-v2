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

Personas are organized into three axes. The **failure-mode axis** is the methodology-agnostic stress-test axis used by the evaluation harness. **Domain fixtures** pair with matching concepts to validate content extraction. **Methodology fixtures** are tied to a specific methodology's mechanics and are not agnostic.

### Failure-Mode Axis (methodology-agnostic, N=8)

Each persona owns a distinct failure mode that no other persona in this set triggers.

| Persona ID | Name | Failure mode triggered | Primary signals/strategies stressed |
|------------|------|------------------------|--------------------------------------|
| `baseline_cooperative` | Baseline Cooperative | None (control) | Calibration reference |
| `brief_responder` | Brief Responder | Signal starvation — terse answers force harder elicitation | `response_depth`, `elaboration`, deepen-family |
| `verbose_tangential` | Verbose Tangential | Extraction under noise + topic drift | extraction/dedup, `anchor`, `revitalize` |
| `fatiguing_responder` | Fatiguing Responder | Temporal signal decay | `llm_response_trend`, `revitalize`, phase dynamics |
| `single_topic_fixator` | Single Topic Fixator | Node exhaustion / focus lock | `focus_streak`, `node_exhaustion`, rotation |
| `uncertain_hedger` | Uncertain Hedger | Low certainty + self-contradiction | `certainty`, `validate`, `clarify`, revises-edges |
| `skeptical_analyst` | Skeptical Analyst | Adversarial engagement with low certainty ceiling | `certainty`, `engagement` gates, probe/validate |
| `disengaged_responder` | Disengaged Respondent | Flat affect + refusal to elaborate from turn 1 | deepen-suppression (engagement × valence), continuation stop triggers |

### Domain Fixtures (content-specific, pair with matching concepts)

| Persona ID | Name | Intended pairing |
|------------|------|------------------|
| `glp1_user` | GLP-1 Medication User | GLP-1 concepts (e.g., `glp1_food_mec`, `glp1_food_jtbd`) |

### Methodology Fixtures (not methodology-agnostic)

| Persona ID | Name | Methodology | Why excluded from agnostic axis |
|------------|------|-------------|----------------------------------|
| `retrospective_rationalizer` | Retrospective Rationalizer | JTBD | Designed around JTBD's functional→emotional→social ladder; conflates persona with methodology mechanic when used with others |

### Excluded from Eval Axis

- `emotionally_reactive` — file retained on disk but not included in the eval harness axis. Valence-swing coverage was de-prioritized in the current eval design.

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
