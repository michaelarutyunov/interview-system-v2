# Phase 4: Synthetic Testing Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build automated testing capability using synthetic respondent for rapid development iteration.

**Architecture:**
- LLM-based synthetic respondent generates contextually appropriate answers
- Persona system for varied response patterns (health_conscious, price_sensitive, etc.)
- Service layer (SyntheticService) orchestrates prompt generation and LLM calls
- FastAPI endpoints expose synthetic generation for test scripts
- Standalone test script runs end-to-end interviews with validation

**Tech Stack:**
- Python 3.14, asyncio for async operations
- FastAPI for API endpoints
- httpx for HTTP client calls
- pytest-asyncio for integration tests
- Phase 2 LLM client for prompt completion

---

## File Organization

```
src/
  llm/prompts/
    synthetic.py          # NEW - Synthetic respondent prompts
  services/
    synthetic_service.py  # NEW - Synthetic service layer
  api/routes/
    synthetic.py          # NEW - Synthetic API endpoints
  api/
    schemas.py            # MODIFY - Add synthetic schemas
  main.py                # MODIFY - Register synthetic router
scripts/
  run_synthetic_interview.py  # NEW - Automated test script
  README.md              # NEW - Scripts documentation
tests/
  unit/
    test_synthetic_prompts.py   # NEW - Prompt unit tests
    test_synthetic_service.py   # NEW - Service unit tests
  integration/
    test_synthetic_api.py       # NEW - API integration tests
    test_synthetic.py           # NEW - End-to-end synthetic tests
```

## Context Notes

**Persona System:** 5 predefined personas (health_conscious, price_sensitive, convenience_seeker, quality_focused, sustainability_minded) with traits and speech patterns.

**Deflection Pattern:** ~20% of responses should include deflections ("That's okay, but what really matters to me is...") to simulate authentic respondent behavior.

**Graph Awareness:** Synthetic responses should reference previously mentioned concepts from graph state (extracted from GraphState.recent_nodes).

**Temperature:** Use 0.8 for synthetic responses (higher than default) for variety in responses.

---

### Task 1: Synthetic Prompts (Spec 4.1)

**Files:**
- Create: `src/llm/prompts/synthetic.py`
- Test: `tests/unit/test_synthetic_prompts.py`

**Step 1: Write failing test**

```python
# tests/unit/test_synthetic_prompts.py
def test_base_system_prompt_exists():
    prompt = get_synthetic_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_synthetic_prompts.py::test_base_system_prompt_exists -v`
Expected: FAIL with "get_synthetic_system_prompt not defined"

**Step 3: Write minimal implementation**

```python
# src/llm/prompts/synthetic.py
PERSONAS = {
    "health_conscious": {
        "name": "Health-Conscious Millennial",
        "traits": ["prioritizes health", "reads labels", "values organic"],
        "speech_pattern": "Uses health-related terminology"
    },
    # ... other 4 personas
}

def get_synthetic_system_prompt() -> str:
    return """You are a synthetic respondent for testing an adaptive interview system.
Generate natural, realistic responses to interview questions."""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_synthetic_prompts.py::test_base_system_prompt_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_synthetic_prompts.py src/llm/prompts/synthetic.py
git commit -m "feat(synthetic): add base prompt and personas"
```

**Repeat for all prompt functions** (get_synthetic_user_prompt, get_synthetic_system_prompt_with_deflection, parse_synthetic_response, get_available_personas)

---

### Task 2: Synthetic Service (Spec 4.2)

**Files:**
- Create: `src/services/synthetic_service.py`
- Test: `tests/unit/test_synthetic_service.py`

**Step 1: Write failing test**

```python
# tests/unit/test_synthetic_service.py
@pytest.mark.asyncio
async def test_generate_response_success():
    mock_llm = AsyncMock()
    mock_llm.complete.return_value = LLMResponse(
        content="I like the creamy texture.",
        model="claude-sonnet-4-20250514",
        usage={"input_tokens": 100, "output_tokens": 20},
        latency_ms=150.0,
    )
    service = SyntheticService(llm_client=mock_llm)
    result = await service.generate_response(
        question="Why is creamy texture important?",
        session_id="test-session",
        persona="health_conscious",
    )
    assert result["response"] == "I like the creamy texture."
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_synthetic_service.py::test_generate_response_success -v`
Expected: FAIL with "SyntheticService not defined"

**Step 3: Write minimal implementation**

```python
# src/services/synthetic_service.py
class SyntheticService:
    DEFAULT_PERSONA = "health_conscious"
    DEFLECTION_CHANCE = 0.2

    def __init__(self, llm_client: Optional[LLMClient] = None, deflection_chance: float = DEFLECTION_CHANCE):
        self.llm_client = llm_client or get_llm_client()
        self.deflection_chance = deflection_chance

    async def generate_response(self, question: str, session_id: str, persona: str = DEFAULT_PERSONA, **kwargs) -> Dict[str, Any]:
        # Validate persona
        available = get_available_personas()
        if persona not in available:
            raise ValueError(f"Unknown persona: {persona}")

        # Build prompts
        system_prompt = get_synthetic_system_prompt()
        user_prompt = get_synthetic_user_prompt(question=question, persona=persona)

        # Call LLM
        llm_response = await self.llm_client.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.8,
            max_tokens=256,
        )

        clean_response = parse_synthetic_response(llm_response.content)
        return {
            "response": clean_response,
            "persona": persona,
            "question": question,
            "latency_ms": llm_response.latency_ms,
            "tokens_used": llm_response.usage,
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_synthetic_service.py::test_generate_response_success -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_synthetic_service.py src/services/synthetic_service.py
git commit -m "feat(synthetic): add service layer"
```

**Repeat for all service methods** (generate_multi_response, generate_interview_sequence, _extract_previous_concepts)

---

### Task 3: Synthetic Endpoint (Spec 4.3)

**Files:**
- Create: `src/api/routes/synthetic.py`
- Modify: `src/main.py` (register router)
- Test: `tests/integration/test_synthetic_api.py`

**Step 1: Write failing test**

```python
# tests/integration/test_synthetic_api.py
@pytest.mark.asyncio
async def test_generate_synthetic_response_success():
    with patch("src.services.synthetic_service.get_llm_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.complete.return_value = LLMResponse(
            content="I like the creamy texture.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )
        mock_get_client.return_value = mock_client

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/synthetic/respond",
                json={
                    "question": "Why is creamy texture important?",
                    "session_id": "test-session",
                    "persona": "health_conscious",
                },
            )
        assert response.status_code == 200
        assert response.json()["response"] == "I like the creamy texture."
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_synthetic_api.py::test_generate_synthetic_response_success -v`
Expected: FAIL with "404 Not Found" (router not registered)

**Step 3: Write minimal implementation**

```python
# src/api/routes/synthetic.py
router = APIRouter(prefix="/synthetic", tags=["synthetic"])

class SyntheticRespondRequest(BaseModel):
    question: str
    session_id: str
    persona: str = "health_conscious"

class SyntheticRespondResponse(BaseModel):
    response: str
    persona: str
    question: str
    latency_ms: float

@router.post("/respond", response_model=SyntheticRespondResponse)
async def generate_synthetic_response(
    request: SyntheticRespondRequest,
    service: SyntheticService = Depends(get_synthetic_service_dep),
):
    result = await service.generate_response(
        question=request.question,
        session_id=request.session_id,
        persona=request.persona,
    )
    return SyntheticRespondResponse(**result)
```

**Step 4: Register router in main.py**

```python
# src/main.py
from src.api.routes import synthetic
app.include_router(synthetic.router)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/integration/test_synthetic_api.py::test_generate_synthetic_response_success -v`
Expected: PASS

**Step 6: Commit**

```bash
git add tests/integration/test_synthetic_api.py src/api/routes/synthetic.py src/main.py
git commit -m "feat(synthetic): add API endpoints"
```

**Repeat for all endpoints** (/respond/multi, /respond/sequence, GET /personas)

---

### Task 4: Test Script (Spec 4.4)

**Files:**
- Create: `scripts/run_synthetic_interview.py`
- Create: `scripts/README.md`

**Step 1: Write script structure**

```python
# scripts/run_synthetic_interview.py
#!/usr/bin/env python3
import asyncio
import argparse
import httpx

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PERSONA = "health_conscious"

async def create_session(client, api_url, concept_id):
    response = await client.post(f"{api_url}/sessions", json={"concept_id": concept_id})
    return response.json()

async def get_synthetic_response(client, api_url, question, session_id, persona):
    response = await client.post(f"{api_url}/synthetic/respond", json={
        "question": question,
        "session_id": session_id,
        "persona": persona,
    })
    return response.json()

async def submit_turn(client, api_url, session_id, user_input):
    response = await client.post(f"{api_url}/sessions/{session_id}/turns", json={"user_input": user_input})
    return response.json()

async def run_interview(api_url, persona, concept_id, max_turns, verbose):
    async with httpx.AsyncClient(timeout=60.0) as client:
        session = await create_session(client, api_url, concept_id)
        session_id = session["id"]
        # ... run turns loop

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", default=DEFAULT_PERSONA)
    parser.add_argument("--max-turns", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(run_interview(DEFAULT_API_URL, args.persona, "oat_milk_v1", args.max_turns, False))

if __name__ == "__main__":
    main()
```

**Step 2: Make executable and test**

```bash
chmod +x scripts/run_synthetic_interview.py
python scripts/run_synthetic_interview.py --help
```

**Step 3: Commit**

```bash
git add scripts/run_synthetic_interview.py scripts/README.md
git commit -m "feat(synthetic): add automated test script"
```

---

### Task 5: Regression Tests (Spec 4.5)

**Files:**
- Create: `tests/integration/test_synthetic.py`

**Step 1: Write failing test**

```python
# tests/integration/test_synthetic.py
@pytest.mark.asyncio
async def test_synthetic_interview_completes():
    with patch("src.services.synthetic_service.get_llm_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.complete.return_value = LLMResponse(content="Response", ...)
        mock_get_client.return_value = mock_client

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create session, run synthetic turns, verify completion
            ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_synthetic.py::test_synthetic_interview_completes -v`
Expected: FAIL (test not written yet)

**Step 3: Implement test**

Write the complete end-to-end test with session creation, synthetic response generation, turn submission, and validation.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_synthetic.py::test_synthetic_interview_completes -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_synthetic.py
git commit -m "test(synthetic): add regression integration tests"
```

---

### Task 6: Package Exports

**Files:**
- Modify: `src/services/__init__.py`
- Modify: `src/llm/prompts/__init__.py` (if exists)

**Step 1: Update service exports**

```python
# src/services/__init__.py
from src.services.synthetic_service import SyntheticService, get_synthetic_service

__all__ = ["SessionService", "StrategyService", "SyntheticService", "get_synthetic_service"]
```

**Step 2: Update prompts exports**

```python
# src/llm/prompts/__init__.py
from src.llm.prompts.synthetic import (
    get_synthetic_system_prompt,
    get_synthetic_user_prompt,
    get_available_personas,
)

__all__ = [
    "get_extraction_system_prompt",
    "get_extraction_user_prompt",
    "get_synthetic_system_prompt",
    "get_synthetic_user_prompt",
    "get_available_personas",
]
```

**Step 3: Verify imports**

```bash
python3 -c "from src.services import SyntheticService; from src.llm.prompts.synthetic import get_available_personas; print('OK')"
```

**Step 4: Commit**

```bash
git add src/services/__init__.py src/llm/prompts/__init__.py
git commit -m "feat(synthetic): update package exports"
```

---

### Task 7: Final Integration Tests

**Step 1: Run all Phase 4 tests**

```bash
pytest tests/unit/test_synthetic_prompts.py tests/unit/test_synthetic_service.py tests/integration/test_synthetic_api.py tests/integration/test_synthetic.py -v
```

**Step 2: Verify package imports**

```bash
python3 -c "
from src.services import SyntheticService, get_synthetic_service
from src.llm.prompts.synthetic import get_available_personas, get_synthetic_user_prompt
print('All imports successful')
print('Personas:', list(get_available_personas().keys()))
"
```

**Step 3: Run test script (requires server running)**

```bash
# Terminal 1: Start server
uvicorn src.main:app --reload

# Terminal 2: Run test script
python scripts/run_synthetic_interview.py --max-turns 3 --verbose
```

**Step 4: Verify API endpoints**

```bash
curl http://localhost:8000/synthetic/personas
curl -X POST http://localhost:8000/synthetic/respond \
  -H "Content-Type: application/json" \
  -d '{"question": "Why is texture important?", "session_id": "test", "persona": "health_conscious"}'
```

**Step 5: Final commit**

```bash
git add .
git commit -m "feat(phase-4): complete synthetic testing infrastructure

- Synthetic prompts with 5 personas
- SyntheticService for LLM-based response generation
- FastAPI endpoints for synthetic API
- Automated test script for regression testing
- Integration tests validating end-to-end flow

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Verification Checklist

Phase 4 is complete when:
- [ ] All 5 personas defined with traits and speech patterns
- [ ] `get_synthetic_user_prompt()` accepts question, persona, previous_concepts, interview_context
- [ ] `SyntheticService.generate_response()` validates personas and calls LLM with temperature=0.8
- [ ] `POST /synthetic/respond` returns 200 with synthetic response
- [ ] `POST /synthetic/respond/multi` returns multiple persona responses
- [ ] `POST /synthetic/respond/sequence` returns full interview sequence
- [ ] `GET /synthetic/personas` lists available personas
- [ ] `scripts/run_synthetic_interview.py` runs complete interview with validation
- [ ] All unit tests pass (test_synthetic_prompts.py, test_synthetic_service.py)
- [ ] All integration tests pass (test_synthetic_api.py, test_synthetic.py)
- [ ] Package exports include synthetic service and prompts
- [ ] Test script validates coverage ≥80%, 5+ turns, 10+ concepts extracted

## Success Metrics

From PRD Section 2.2:
- Automated interview completes without errors
- Coverage ≥80% achieved
- Graph state updates correctly
- All personas generate varied responses
- Test script exit code 0 (all validations pass)
