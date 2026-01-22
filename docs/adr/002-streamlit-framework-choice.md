# ADR-002: Streamlit Framework Choice for Demo UI

## Status
Accepted

## Context
Phase 5 requires a demo UI for the interview system. We need to select a framework that:
1. Does not interfere with FastAPI's async event loop
2. Enables rapid development for demo purposes
3. Supports chat interfaces, graph visualization, and metrics
4. Integrates cleanly with HTTP REST API
5. Can run separately from the backend

## Options Considered

### Gradio
- ✅ Quick setup, good chat components
- ❌ v1 had event loop issues with async operations
- ❌ Less customization control
- **Verdict**: Risk of repeating v1 problems

### Streamlit (Selected)
- ✅ Pure Python, fast development
- ✅ Good data viz components (Plotly, Altair)
- ✅ Separate process - no event loop conflicts
- ✅ Synchronous HTTP API calls to backend
- ⚠️ Rerun model can be slow for frequent updates
- **Verdict**: Best fit for demo UI MVP

### htmx
- ✅ Lightweight, no JS needed
- ❌ More manual work for components
- ❌ Slower development for demo
- **Verdict**: Good for production, overkill for demo

### React
- ✅ Full control, modern
- ❌ Requires JS expertise
- ❌ Separate frontend build step
- **Verdict**: Overkill for demo purposes

## Decision
**Use Streamlit for the demo UI.**

The synchronous execution model and separate process architecture provide clean separation from the async FastAPI backend, enabling rapid development without event loop conflicts.

## Architecture

```
User Browser
    │
    ▼
Streamlit (localhost:8501)
    │ HTTP REST API calls
    ▼
FastAPI (localhost:8000)
    │
    ▼
Services + Database
```

## Consequences

### Positive
- **Fast development**: Pure Python, no build step
- **Clean separation**: No event loop conflicts with backend
- **Good components**: Built-in chat, charts, metrics
- **Easy deployment**: Runs alongside backend

### Negative
- **Execution model**: Rerun model can be slow for frequent updates
- **Limitation**: Not suitable for production-scale applications
- **Future migration**: Would need change for production UI

## Migration Path

If the UI framework needs to change in the future:

1. **To Gradio**: Resolve event loop issues, use sync wrapper for API calls
2. **To React**: Separate frontend build pipeline, REST API alignment
3. **To htmx**: Server-side rendering templates, HTMX attributes

Current Streamlit approach provides clean separation with minimal overhead for demo purposes.

## References
- [Original Decision Document](../ui-framework-decision.md)
- Phase 5 Specification
