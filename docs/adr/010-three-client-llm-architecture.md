# ADR-010: Three-Client LLM Architecture

## Status
Accepted

## Context

The original LLM client design used a dual-client architecture:
- **Main LLM**: For question generation and extraction (high quality)
- **Light LLM**: For scoring tasks (faster, cheaper)

This design had several limitations:
1. **Wrong task allocation**: Extraction (critical for graph quality) used same expensive model as generation
2. **No provider flexibility**: Hardcoded to Anthropic only
3. **Configuration bloat**: All model/temperature/max_tokens settings in `.env`

## Decision

**Implement a three-client architecture with provider-agnostic design:**

| Client Type | Purpose | Default Provider | Rationale |
|-------------|---------|------------------|-----------|
| `extraction` | Extract nodes/edges/stance | Anthropic | Critical for graph quality, needs high accuracy |
| `scoring` | Extract diagnostic signals | Kimi | High-volume, lower cost, faster response |
| `generation` | Generate interview questions | Anthropic | Creative, needs quality |

**Key design principles:**

1. **Hardcoded defaults in code** - All model/temperature/max_tokens defaults defined in `src/llm/client.py`
2. **Minimal `.env`** - Only API keys required, optional provider overrides
3. **Provider-agnostic** - Abstract `LLMClient` base class with provider-specific implementations
4. **OpenAI-compatible** - Kimi and DeepSeek use standard `/chat/completions` format

## Implementation

### Factory Functions
```python
def get_extraction_llm_client() -> LLMClient:
    return get_llm_client("extraction")

def get_scoring_llm_client() -> LLMClient:
    return get_llm_client("scoring")

def get_generation_llm_client() -> LLMClient:
    return get_llm_client("generation")
```

### Provider Classes
```python
class AnthropicClient(LLMClient):
    # Native Claude API

class KimiClient(OpenAICompatibleClient):
    # OpenAI-compatible /chat/completions

class DeepSeekClient(OpenAICompatibleClient):
    # OpenAI-compatible /chat/completions
```

### Configuration (`.env`)
```bash
# Required: API keys only
ANTHROPIC_API_KEY=sk-xxx
KIMI_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx

# Optional: Override defaults
# LLM_EXTRACTION_PROVIDER=kimi
# LLM_SCORING_PROVIDER=deepseek
# LLM_GENERATION_PROVIDER=anthropic
```

### Hardcoded Defaults
```python
EXTRACTION_DEFAULTS = dict(
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",
    temperature=0.3,  # Lower for structured extraction
    max_tokens=2048,
)

SCORING_DEFAULTS = dict(
    provider="kimi",
    model="moonshot-v1-8k",
    temperature=0.3,
    max_tokens=512,
)

GENERATION_DEFAULTS = dict(
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,  # Higher for creative questions
    max_tokens=1024,
)
```

## Consequences

### Positive
- **Better allocation**: Extraction uses high-quality model, scoring uses fast/cheap model
- **Cost optimization**: Kimi for scoring reduces costs significantly vs Anthropic
- **Provider flexibility**: Easy to swap providers per task type
- **Self-documenting**: Defaults visible in code, no hunting through `.env`
- **Easy updates**: Change model in one place (code) vs updating user configs

### Negative
- **Code changes required** for model/parameter updates (vs `.env` edits)
- **Requires deployment** to change defaults (users can override via `.env`)
- **More complex factory** with multiple client types

### Risks
- **Kimi availability**: If Kimi API is down, scoring fails (mitigation: can override to Anthropic)
- **Model compatibility**: Different providers may have different behavior (same task may yield different results)
- **API rate limits**: Different providers have different rate limits

## Alternatives Considered

### 1. Keep dual-client with `.env` configuration
**Rejected**: Too much configuration complexity, hard to see what's actually configured

### 2. Single client for all tasks
**Rejected**: Over-provisioning (using Sonnet for scoring) or under-provisioning (using Haiku for extraction)

### 3. Configuration file for defaults
**Rejected**: Adds complexity, harder to maintain than code-based defaults

## Usage Examples

### Default configuration (`.env` with API keys only)
```python
from src.llm.client import get_extraction_llm_client

extraction = get_extraction_llm_client()  # Anthropic Sonnet, temp=0.3
```

### Override provider for scoring
```bash
# .env
LLM_SCORING_PROVIDER=deepseek
```
```python
from src.llm.client import get_scoring_llm_client

scoring = get_scoring_llm_client()  # DeepSeek, temp=0.3
```

### Service integration
```python
# ExtractionService - uses get_extraction_llm_client()
class ExtractionService:
    def __init__(self, llm_client = None):
        self.llm = llm_client or get_extraction_llm_client()

# QualitativeSignalExtractor - uses get_scoring_llm_client()
class QualitativeSignalExtractor:
    def __init__(self, llm_client = None):
        self.llm = llm_client or get_scoring_llm_client()

# QuestionService - uses get_generation_llm_client()
class QuestionService:
    def __init__(self, llm_client = None):
        self.llm = llm_client or get_generation_llm_client()
```

### Per-Call Timeout Override

The `complete()` method supports per-call timeout overrides for operations that need more time than the default:

```python
# Default timeout (30s for most clients)
response = await llm.complete(prompt="...")

# Extended timeout for complex operations
response = await llm.complete(
    prompt="...",
    timeout=60.0,  # Override default timeout
)
```

**Use case:** Slot discovery uses the scoring client (Kimi) with extended timeout (60s) because:
- Complex reasoning: Grouping nodes into canonical slots
- JSON generation: Structured output with multiple fields
- Variable API latency: Kimi API occasionally slower than 30s default

## References
- Spec: `specs/phase-2/2.2-llm-client.md`
- Implementation: `src/llm/client.py`
- Configuration: `src/core/config.py`
- Services: `src/services/extraction_service.py`, `src/services/question_service.py`, `src/services/scoring/llm_signals.py`
