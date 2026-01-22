# ADR-001: Dual Sync/Async API for APIClient

## Status
Accepted

## Context

The interview system has two primary use cases with different execution models:

1. **Streamlit Demo UI**: Synchronous execution model, blocking I/O required
2. **Agent Orchestration**: Async execution model, needs to manage multiple concurrent interview sessions efficiently

The original `APIClient` was implemented as async-only using `httpx.AsyncClient`. This works perfectly for:
- FastAPI backend (async-native)
- Agent orchestration (async frameworks)

However, integrating with Streamlit revealed a fundamental incompatibility:
- Streamlit's execution model is synchronous
- Using `asyncio.run()` to call async methods creates/destroys event loops
- httpx.AsyncClient transports become invalid when their event loop closes
- This results in "TCPTransport closed" errors

## Decision

**Implement dual sync/async API in `APIClient`:**

- **Synchronous methods** (default): Use `httpx.Client` for Streamlit and blocking contexts
- **Async methods** (`_async` suffix): Use `httpx.AsyncClient` for agents and async frameworks

```python
class APIClient:
    # Sync methods for Streamlit UI
    def create_session(self, concept_id, max_turns, target_coverage): ...

    # Async methods for agent orchestration
    async def create_session_async(self, concept_id, max_turns, target_coverage): ...
```

## Implementation

### Sync Methods
```python
def create_session(self, ...) -> SessionInfo:
    with httpx.Client(timeout=self.timeout) as client:
        response = client.post(f"{self.base_url}/sessions", json={...})
        response.raise_for_status()
        return SessionInfo(...)
```

### Async Methods
```python
async def create_session_async(self, ...) -> SessionInfo:
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.post(f"{self.base_url}/sessions", json={...})
        response.raise_for_status()
        return SessionInfo(...)
```

## Consequences

### Positive
- **Enables both use cases**: Streamlit UI works, agent orchestration works
- **Native implementations**: No `asyncio.run()` wrapper hacks
- **Clean separation**: Each context uses appropriate HTTP client
- **Backwards compatible**: Existing async code only needs method rename (add `_async`)
- **Future-proof**: When Streamlit is deprecated, sync methods can be removed

### Negative
- **Larger API surface**: Two methods per operation instead of one
- **Code duplication**: Sync and async implementations are similar but separate
- **Maintenance burden**: Changes need to be made in both implementations
- **Naming convention**: Developers need to know when to use `_async` suffix

## Alternatives Considered

### 1. Wrapper Class (SyncAPIClient wraps AsyncAPIClient)
```python
class SyncAPIClient:
    def __init__(self):
        self._async_client = APIClient()

    def create_session(self, ...):
        return asyncio.run(self._async_client.create_session(...))
```
**Rejected**: Still has `asyncio.run()` event loop issues

### 2. Keep async-only, fix Streamlit integration
Use `nest_asyncio` or persistent event loop across Streamlit reruns.
**Rejected**: Hacky, fragile, fights Streamlit's execution model

### 3. Convert everything to sync
**Rejected**: Loses async benefits for agent orchestration (concurrency, efficiency)

## Usage Examples

### Streamlit UI (sync)
```python
from ui.api_client import APIClient

client = APIClient()
session = client.create_session(concept_id="oat_milk_v1")
```

### Agent Orchestration (async)
```python
from ui.api_client import APIClient

async def run_concurrent_sessions():
    client = APIClient()

    # Run 10 sessions in parallel
    results = await asyncio.gather(*[
        client.create_session_async(concept_id="oat_milk_v1")
        for _ in range(10)
    ])
    return results
```

## Semantic Versioning Impact

This is a **MINOR** version bump (0.1.0 → 0.2.0):
- New public API methods added
- No breaking changes to existing functionality
- Async methods need rename (`create_session` → `create_session_async`)

## References
- Related to [ADR-002: Streamlit Framework Choice](002-streamlit-framework-choice.md)
- Bug fix: interview-system-v2-0v4 (async/await bug in UI controls)
