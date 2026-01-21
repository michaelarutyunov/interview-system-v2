# UI Framework Decision for Phase 5

## Decision: Streamlit

Date: 2025-01-21
Status: Approved

## Evaluation Criteria

1. **Async Safety**: Must not interfere with FastAPI event loop
2. **Development Speed**: Quick iteration for demo purposes
3. **Component Support**: Chat, graphs, metrics display
4. **API Integration**: Clean HTTP client to FastAPI backend
5. **Deployment**: Can run separately or alongside API

## Options Considered

### Gradio
- ✅ Quick setup, good chat components
- ❌ v1 had event loop issues with async operations
- ❌ Less customization control
- Verdict: Risk of repeating v1 problems

### Streamlit (Selected)
- ✅ Pure Python, fast development
- ✅ Good data viz components (Plotly, Altair)
- ✅ Separate process - no event loop conflicts
- ✅ Synchronous HTTP API calls to backend
- ⚠️ Rerun model can be slow for frequent updates
- Verdict: Best fit for demo UI MVP

### htmx
- ✅ Lightweight, no JS needed
- ❌ More manual work for components
- ❌ Slower development for demo
- Verdict: Good for production, overkill for demo

### React
- ✅ Full control, modern
- ❌ Requires JS expertise
- ❌ Separate frontend build step
- Verdict: Overkill for demo purposes

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

## Dependencies

```
streamlit>=1.31.0
plotly>=5.18.0
networkx>=3.2
httpx>=0.26.0
```

## Implementation Plan

1. **Streamlit app** (`ui/streamlit_app.py`)
   - Chat interface using `st.chat_message`
   - Graph visualization using `st.plotly_chart`
   - Metrics panel using `st.metrics`
   - Session controls using `st.sidebar`

2. **API client** (`ui/api_client.py`)
   - HTTP client using `httpx`
   - Session management
   - Error handling

3. **Components** (`ui/components/`)
   - `chat.py` - Chat interface
   - `graph.py` - Graph visualization
   - `metrics.py` - Metrics display
   - `controls.py` - Session controls

## Migration Path

If the UI framework needs to change in the future:

1. **To Gradio**: Would need to resolve event loop issues by:
   - Running Gradio in separate process (already planned)
   - Using sync wrapper for async API calls
   - Potential architectural changes

2. **To React**: Would require:
   - Separate frontend build pipeline
   - REST API alignment for all operations
   - Authentication/CSRF considerations

3. **To htmx**: Would require:
   - Server-side rendering templates
   - HTMX attribute integration
   - More manual UI state management

Current Streamlit approach provides clean separation with minimal overhead for demo purposes.

## Next Steps

1. **Install dependencies:**
   ```bash
   uv pip install streamlit plotly networkx httpx
   ```

2. **Create basic app:**
   ```bash
   mkdir -p ui/components
   touch ui/__init__.py ui/components/__init__.py
   ```

3. **Test Streamlit:**
   ```bash
   echo "import streamlit as st; st.write('Hello')" > test_app.py && streamlit run test_app.py
   ```

## Verification

```bash
# Verify decision document exists
cat docs/ui-framework-decision.md

# Verify Streamlit can be imported
python3 -c "import streamlit as st; print(st.__version__)"

# Verify basic app can run
echo "import streamlit as st; st.write('Test')" > test_app.py && streamlit run test_app.py
```
