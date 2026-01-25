# Interview System v2 - API Documentation

Complete API reference for the Interview System v2.

## Base URL

```
http://localhost:8000
```

Interactive API documentation (Swagger UI) is available at:
```
http://localhost:8000/docs
```

## Response Format

All endpoints return JSON responses. Successful responses follow the schema defined for each endpoint.

### Error Response Format

Errors return HTTP status codes with JSON bodies:

```json
{
  "detail": "Error message describing what went wrong",
  "error_type": "Optional error type identifier"
}
```

Common HTTP status codes:
- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Sessions Endpoints

### Create Session

Creates a new interview session.

**Endpoint:** `POST /sessions`

**Request Body:**
```json
{
  "methodology": "means_end_chain",
  "concept_id": "yogurt_consumption",
  "config": {
    "concept_name": "Yogurt Consumption"
  }
}
```

**Parameters:**
- `methodology` (string, required): Research methodology to use (e.g., "means_end_chain")
- `concept_id` (string, required): Identifier for the concept being studied
- `config` (object, optional): Additional configuration options
  - `concept_name` (string): Human-readable concept name

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "methodology": "means_end_chain",
  "concept_id": "yogurt_consumption",
  "status": "active",
  "config": {
    "concept_name": "Yogurt Consumption"
  },
  "turn_count": 0,
  "created_at": "2026-01-21T12:00:00Z",
  "updated_at": "2026-01-21T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "methodology": "means_end_chain",
    "concept_id": "yogurt_consumption",
    "config": {"concept_name": "Yogurt Consumption"}
  }'
```

---

### List Sessions

Lists all active sessions.

**Endpoint:** `GET /sessions`

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "methodology": "means_end_chain",
      "concept_id": "yogurt_consumption",
      "status": "active",
      "config": {},
      "turn_count": 5,
      "created_at": "2026-01-21T12:00:00Z",
      "updated_at": "2026-01-21T12:05:00Z"
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl http://localhost:8000/sessions
```

---

### Get Session

Retrieves details of a specific session.

**Endpoint:** `GET /sessions/{session_id}`

**Parameters:**
- `session_id` (string, path parameter): Session UUID

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "methodology": "means_end_chain",
  "concept_id": "yogurt_consumption",
  "status": "active",
  "config": {},
  "turn_count": 5,
  "created_at": "2026-01-21T12:00:00Z",
  "updated_at": "2026-01-21T12:05:00Z"
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": "Session 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**
```bash
curl http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000
```

---

### Delete Session

Deletes/closes a session.

**Endpoint:** `DELETE /sessions/{session_id}`

**Parameters:**
- `session_id` (string, path parameter): Session UUID

**Response:** `204 No Content`

**Error Response:** `404 Not Found`
```json
{
  "detail": "Session 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000
```

---

### Start Session

Starts an interview session and generates the opening question. Must be called before processing turns.

**Endpoint:** `POST /sessions/{session_id}/start`

**Parameters:**
- `session_id` (string, path parameter): Session UUID

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "opening_question": "To get started, could you tell me about the last time you purchased yogurt? What was going through your mind?"
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": "Session not found"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000/start
```

---

### Submit Turn

Processes a respondent turn (answer). Extracts concepts, updates the knowledge graph, calculates scores, and generates the next question.

**Endpoint:** `POST /sessions/{session_id}/turns`

**Parameters:**
- `session_id` (string, path parameter): Session UUID

**Request Body:**
```json
{
  "text": "I usually look for yogurt that's high in protein and low in sugar. The creamy texture is really important to me too."
}
```

**Fields:**
- `text` (string, required): Respondent's response text (1-5000 characters)

**Response:** `200 OK`
```json
{
  "turn_number": 3,
  "extracted": {
    "concepts": [
      {
        "text": "high in protein",
        "type": "attribute",
        "confidence": 0.95
      },
      {
        "text": "low in sugar",
        "type": "attribute",
        "confidence": 0.92
      },
      {
        "text": "creamy texture",
        "type": "attribute",
        "confidence": 0.98
      },
      {
        "text": "feels satisfying",
        "type": "functional_consequence",
        "confidence": 0.88
      }
    ],
    "relationships": [
      {
        "source": "high in protein",
        "target": "feels satisfying",
        "type": "leads_to"
      },
      {
        "source": "creamy texture",
        "target": "feels satisfying",
        "type": "leads_to"
      }
    ]
  },
  "graph_state": {
    "node_count": 8,
    "edge_count": 5,
    "nodes_by_type": {
      "attribute": 4,
      "functional_consequence": 3,
      "psychosocial_consequence": 1
    },
    "coverage_state": {
      "elements": {
        "1": {
          "covered": true,
          "linked_node_ids": ["node-123", "node-456"],
          "types_found": ["attribute", "psychosocial_consequence"],
          "depth_score": 0.5
        },
        "2": {
          "covered": false,
          "linked_node_ids": [],
          "types_found": [],
          "depth_score": 0.0
        }
      },
      "elements_covered": 1,
      "elements_total": 6,
      "overall_depth": 0.25
    }
  },
  "scoring": {
    "coverage": 0.35,
    "depth": 0.25,
    "saturation": 0.05
  },
  "strategy_selected": "deepen",
  "next_question": "You mentioned that the creamy texture feels satisfying. Why is that feeling important to you?",
  "should_continue": true,
  "latency_ms": 1250
}
```

**Response Fields:**
- `turn_number` (integer): Current turn number
- `extracted` (object): Extraction results
  - `concepts` (array): Extracted concepts with text, type, confidence, and linked_elements
  - `relationships` (array): Extracted relationships between concepts
- `graph_state` (object): Current knowledge graph state
  - `node_count` (integer): Total nodes in graph
  - `edge_count` (integer): Total edges in graph
  - `nodes_by_type` (object): Node count by type
  - `coverage_state` (object): Per-element coverage tracking (see below)
- `scoring` (object): Multi-dimensional scoring
  - `coverage` (float): Coverage score (0-1)
  - `depth` (float): Depth score (0-1)
  - `saturation` (float): Saturation score (0-1)
- `strategy_selected` (string): Questioning strategy used (broaden, deepen, bridge, pivot, cover_element)
- `next_question` (string): Next question to ask respondent
- `should_continue` (boolean): Whether interview should continue
- `latency_ms` (integer): Processing time in milliseconds

**Coverage State Structure:**
The `coverage_state` field provides detailed element-level coverage tracking:

```json
{
  "elements": {
    "1": {
      "covered": true,
      "linked_node_ids": ["node-123", "node-456"],
      "types_found": ["attribute", "psychosocial_consequence"],
      "depth_score": 0.5
    }
  },
  "elements_covered": 1,
  "elements_total": 6,
  "overall_depth": 0.25
}
```

Fields:
- `elements` (object): Map of element_id → coverage data
  - `covered` (boolean): Whether any nodes are linked to this element
  - `linked_node_ids` (array): IDs of nodes linked to this element
  - `types_found` (array): Node types discovered for this element
  - `depth_score` (float): Chain validation depth (0-1)
- `elements_covered` (integer): Count of elements with at least one linked node
- `elements_total` (integer): Total number of elements in concept
- `overall_depth` (float): Average depth score across all elements

**Error Responses:**
- `400 Bad Request` - Session already completed
- `404 Not Found` - Session not found
- `500 Internal Server Error` - Processing failed

**Example:**
```bash
curl -X POST http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000/turns \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I usually look for yogurt that'\''s high in protein and low in sugar. The creamy texture is really important to me too."
  }'
```

---

### Export Session

Exports session data in various formats.

**Endpoint:** `GET /sessions/{session_id}/export`

**Parameters:**
- `session_id` (string, path parameter): Session UUID
- `format` (string, query parameter): Export format - `json`, `markdown`, or `csv` (default: `json`)

**Response:** `200 OK`

The response content-type varies by format:
- `application/json` for JSON format
- `text/markdown` for Markdown format
- `text/csv` for CSV format

The response includes a `Content-Disposition` header with the filename.

**JSON Format Example:**
```json
{
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "methodology": "means_end_chain",
    "concept_id": "yogurt_consumption",
    "concept_name": "Yogurt Consumption",
    "status": "completed",
    "turn_count": 12,
    "created_at": "2026-01-21T12:00:00Z",
    "updated_at": "2026-01-21T12:15:00Z"
  },
  "turns": [
    {
      "turn_number": 1,
      "question": "To get started, could you tell me about the last time you purchased yogurt?",
      "response": "I buy yogurt every week for breakfast...",
      "extracted_concepts": [...],
      "extracted_relationships": [...]
    }
  ],
  "knowledge_graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Markdown Format Example:**
```markdown
# Interview Session: Yogurt Consumption

**Session ID:** 550e8400-e29b-41d4-a716-446655440000
**Methodology:** Means-End Chain
**Status:** Completed
**Turns:** 12

## Interview Transcript

### Turn 1

**Interviewer:** To get started, could you tell me about the last time you purchased yogurt?

**Respondent:** I buy yogurt every week for breakfast...

---

## Knowledge Graph Summary

- **Total Concepts:** 24
- **Total Relationships:** 18
- **Coverage:** 65%
```

**CSV Format Example:**
```csv
turn_number,question,response,concept_count,relationship_count,coverage_score
1,"To get started...","I buy yogurt every week...",5,3,0.15
2,"What motivated that choice?","I wanted something healthy...",7,4,0.25
```

**Error Responses:**
- `404 Not Found` - Session not found
- `400 Bad Request` - Invalid format

**Examples:**
```bash
# Export as JSON
curl http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000/export?format=json \
  -o session.json

# Export as Markdown
curl http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000/export?format=markdown \
  -o session.md

# Export as CSV
curl http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000/export?format=csv \
  -o session.csv
```

---

## Synthetic Respondent Endpoints

Generate synthetic responses for testing interviews.

### Generate Synthetic Response

Generates a single synthetic respondent response.

**Endpoint:** `POST /synthetic/respond`

**Request Body:**
```json
{
  "question": "What do you look for when buying yogurt?",
  "session_id": "test-session-123",
  "persona": "health_conscious",
  "interview_context": {
    "product_name": "yogurt",
    "turn_number": 3,
    "coverage_achieved": 0.35
  },
  "use_deflection": null
}
```

**Parameters:**
- `question` (string, required): The interviewer's question
- `session_id` (string, required): Session identifier for context tracking
- `persona` (string, optional): Persona ID (default: "health_conscious")
- `interview_context` (object, optional): Interview context
  - `product_name` (string): Product being discussed
  - `turn_number` (integer): Current turn number
  - `coverage_achieved` (float): Current coverage score
- `use_deflection` (boolean, optional): Override deflection behavior (null = use chance)

**Response:** `200 OK`
```json
{
  "response": "Well, I always check the nutrition label first. I want something with at least 15g of protein and less than 10g of sugar. Organic is important to me too, because I don't want artificial hormones or antibiotics.",
  "persona": "health_conscious",
  "persona_name": "Health-Conscious Professional",
  "question": "What do you look for when buying yogurt?",
  "latency_ms": 1850.5,
  "tokens_used": {
    "prompt_tokens": 150,
    "completion_tokens": 45,
    "total_tokens": 195
  },
  "used_deflection": false
}
```

**Error Responses:**
- `400 Bad Request` - Invalid persona
- `500 Internal Server Error` - Generation failed

**Example:**
```bash
curl -X POST http://localhost:8000/synthetic/respond \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What do you look for when buying yogurt?",
    "session_id": "test-session-123",
    "persona": "health_conscious"
  }'
```

---

### Generate Multiple Responses

Generates multiple synthetic responses (one per available persona).

**Endpoint:** `POST /synthetic/respond/multi`

**Request Body:**
```json
{
  "question": "What do you look for when buying yogurt?",
  "session_id": "test-session-123",
  "personas": null,
  "interview_context": {
    "product_name": "yogurt"
  }
}
```

**Parameters:**
- `question` (string, required): The interviewer's question
- `session_id` (string, required): Session identifier
- `personas` (array, optional): List of persona IDs (null = all available)
- `interview_context` (object, optional): Interview context

**Response:** `200 OK`
```json
[
  {
    "response": "Well, I always check the nutrition label first...",
    "persona": "health_conscious",
    "persona_name": "Health-Conscious Professional",
    "question": "What do you look for when buying yogurt?",
    "latency_ms": 1850.5,
    "tokens_used": {...},
    "used_deflection": false
  },
  {
    "response": "Honestly, I just grab whatever looks good...",
    "persona": "budget_shopper",
    "persona_name": "Budget Shopper",
    "question": "What do you look for when buying yogurt?",
    "latency_ms": 1620.3,
    "tokens_used": {...},
    "used_deflection": false
  }
]
```

**Example:**
```bash
curl -X POST http://localhost:8000/synthetic/respond/multi \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What do you look for when buying yogurt?",
    "session_id": "test-session-123"
  }'
```

---

### Generate Interview Sequence

Generates synthetic responses for an entire interview sequence.

**Endpoint:** `POST /synthetic/respond/sequence`

**Request Body:**
```json
{
  "questions": [
    "Tell me about the last time you bought yogurt",
    "What motivated that choice?",
    "How did that make you feel?"
  ],
  "session_id": "test-session-123",
  "persona": "health_conscious",
  "product_name": "yogurt"
}
```

**Parameters:**
- `questions` (array, required): List of interview questions
- `session_id` (string, required): Session identifier
- `persona` (string, optional): Persona ID (default: "health_conscious")
- `product_name` (string, optional): Product name for context (default: "the product")

**Response:** `200 OK`
```json
[
  {
    "response": "I bought some Greek yogurt yesterday...",
    "persona": "health_conscious",
    "persona_name": "Health-Conscious Professional",
    "question": "Tell me about the last time you bought yogurt",
    "latency_ms": 1750.2,
    "tokens_used": {...},
    "used_deflection": false
  },
  {
    "response": "I wanted something high in protein...",
    "persona": "health_conscious",
    "persona_name": "Health-Conscious Professional",
    "question": "What motivated that choice?",
    "latency_ms": 1820.8,
    "tokens_used": {...},
    "used_deflection": false
  },
  {
    "response": "It makes me feel good about my health...",
    "persona": "health_conscious",
    "persona_name": "Health-Conscious Professional",
    "question": "How did that make you feel?",
    "latency_ms": 1690.4,
    "tokens_used": {...},
    "used_deflection": false
  }
]
```

**Example:**
```bash
curl -X POST http://localhost:8000/synthetic/respond/sequence \
  -H "Content-Type: application/json" \
  -d '{
    "questions": [
      "Tell me about the last time you bought yogurt",
      "What motivated that choice?"
    ],
    "session_id": "test-session-123",
    "persona": "health_conscious",
    "product_name": "yogurt"
  }'
```

---

### List Personas

Lists all available synthetic respondent personas.

**Endpoint:** `GET /synthetic/personas`

**Response:** `200 OK`
```json
{
  "health_conscious": "Health-Conscious Professional",
  "budget_shopper": "Budget Shopper",
  "convenience_seeker": "Convenience Seeker",
  "gourmet_enthusiast": "Gourmet Enthusiast",
  "brand_loyal": "Brand Loyal Customer"
}
```

**Example:**
```bash
curl http://localhost:8000/synthetic/personas
```

---

## Concepts Endpoints

Manage concept configurations for interviews.

### List Concepts

Lists all available concept configurations.

**Endpoint:** `GET /concepts`

**Response:** `200 OK`
```json
[
  {
    "id": "yogurt_consumption",
    "name": "Yogurt Consumption",
    "methodology": "means_end_chain",
    "element_count": 15
  },
  {
    "id": "sneaker_purchase",
    "name": "Sneaker Purchase Decision",
    "methodology": "means_end_chain",
    "element_count": 20
  }
]
```

**Example:**
```bash
curl http://localhost:8000/concepts
```

---

### Get Concept Details

Retrieves full configuration for a specific concept.

**Endpoint:** `GET /concepts/{concept_id}`

**Parameters:**
- `concept_id` (string, path parameter): Concept identifier

**Response:** `200 OK`
```json
{
  "id": "yogurt_consumption",
  "name": "Yogurt Consumption",
  "description": "Understanding consumer motivations for yogurt purchases",
  "methodology": "means_end_chain",
  "elements": [
    {
      "id": "attribute_1",
      "label": "High protein",
      "type": "attribute",
      "priority": "high"
    },
    {
      "id": "consequence_1",
      "label": "Feel satisfied longer",
      "type": "functional_consequence",
      "priority": "high"
    }
  ],
  "completion": {
    "target_coverage": 0.70,
    "max_turns": 15,
    "saturation_threshold": 0.80
  }
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": "Concept 'invalid_id' not found"
}
```

**Example:**
```bash
curl http://localhost:8000/concepts/yogurt_consumption
```

---

### Get Concept Elements

Retrieves elements for a specific concept.

**Endpoint:** `GET /concepts/{concept_id}/elements`

**Parameters:**
- `concept_id` (string, path parameter): Concept identifier

**Response:** `200 OK`
```json
[
  {
    "id": "attribute_1",
    "label": "High protein",
    "type": "attribute",
    "priority": "high"
  },
  {
    "id": "attribute_2",
    "label": "Low sugar",
    "type": "attribute",
    "priority": "high"
  },
  {
    "id": "consequence_1",
    "label": "Feel satisfied longer",
    "type": "functional_consequence",
    "priority": "high"
  }
]
```

**Error Response:** `404 Not Found`
```json
{
  "detail": "Concept 'invalid_id' not found"
}
```

**Example:**
```bash
curl http://localhost:8000/concepts/yogurt_consumption/elements
```

---

## System Endpoints

### Health Check

Checks system health and database status.

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "0.1.0"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### Root Endpoint

Returns basic system information.

**Endpoint:** `GET /`

**Response:** `200 OK`
```json
{
  "name": "Interview System v2",
  "version": "0.1.0",
  "status": "running"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

---

## Common Patterns

### Complete Interview Flow

```python
import httpx

async def complete_interview_flow():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. Create session
        response = await client.post(
            f"{base_url}/sessions",
            json={
                "methodology": "means_end_chain",
                "concept_id": "yogurt_consumption",
                "config": {"concept_name": "Yogurt"}
            }
        )
        session = response.json()
        session_id = session["id"]

        # 2. Start session
        response = await client.post(f"{base_url}/sessions/{session_id}/start")
        start_data = response.json()
        question = start_data["opening_question"]

        # 3. Process turns
        while True:
            print(f"Question: {question}")

            # Get user input (in real app, from UI)
            user_text = input("Your answer: ")

            # Submit turn
            response = await client.post(
                f"{base_url}/sessions/{session_id}/turns",
                json={"text": user_text}
            )
            result = response.json()

            print(f"Coverage: {result['scoring']['coverage']:.2%}")
            print(f"Strategy: {result['strategy_selected']}")

            if not result["should_continue"]:
                break

            question = result["next_question"]

        # 4. Export session
        response = await client.get(
            f"{base_url}/sessions/{session_id}/export",
            params={"format": "markdown"}
        )
        print(response.text)
```

### Testing with Synthetic Respondents

```python
import httpx

async def test_with_synthetic():
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Create and start session
        response = await client.post(
            f"{base_url}/sessions",
            json={
                "methodology": "means_end_chain",
                "concept_id": "yogurt_consumption"
            }
        )
        session_id = response.json()["id"]

        response = await client.post(f"{base_url}/sessions/{session_id}/start")
        question = response.json()["opening_question"]

        # Process turns with synthetic respondent
        for turn in range(5):
            # Get synthetic response
            response = await client.post(
                f"{base_url}/synthetic/respond",
                json={
                    "question": question,
                    "session_id": session_id,
                    "persona": "health_conscious"
                }
            )
            synthetic_data = response.json()
            synthetic_answer = synthetic_data["response"]

            print(f"Question: {question}")
            print(f"Synthetic Answer: {synthetic_answer}")

            # Process turn
            response = await client.post(
                f"{base_url}/sessions/{session_id}/turns",
                json={"text": synthetic_answer}
            )
            result = response.json()

            if not result["should_continue"]:
                break

            question = result["next_question"]
```

---

## Error Handling

Always handle potential errors in your API client code:

```python
import httpx

async def safe_api_call():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/sessions",
                json={"concept_id": "yogurt_consumption"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code}")
        print(f"Detail: {e.response.json().get('detail')}")

    except httpx.TimeoutError:
        print("Request timed out")

    except httpx.RequestError as e:
        print(f"Request error: {e}")
```

---

## Rate Limiting

Currently, there are no enforced rate limits on the API. However, consider:

- Anthropic API rate limits apply for LLM calls
- Database performance may degrade under high load
- Consider implementing client-side rate limiting for production use

---

## Versioning

The API is currently at version `0.1.0` and may change. Future versions will include:

- API versioning in the URL path (e.g., `/v1/sessions`)
- Deprecation notices for breaking changes
- Backward compatibility guarantees where possible
