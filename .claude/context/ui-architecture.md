# UI Architecture

> **Purpose**: Component structure, state management, styling conventions, and API integration for the Streamlit demo UI.
> For the visual identity rationale (font choices, color palette), see `docs/archive/plans-root/UI/visual_identity.md`.

---

## Key Files

| File | Role |
|------|------|
| `ui/streamlit_app.py` | Main app — page config, CSS injection, state init, layout, tab routing |
| `ui/api_client.py` | HTTP client with dual sync/async interface to FastAPI backend |
| `ui/components/chat.py` | ChatInterface — message history, input, avatars |
| `ui/components/controls.py` | *(removed Apr 2026 — was vestigial, no live imports)* |
| `ui/components/graph.py` | GraphVisualizer — NetworkX + Plotly 2D/3D graph rendering |
| `ui/components/metrics.py` | MetricsPanel — turn count, coverage, strategy display |
| `ui/components/scoring.py` | ScoringTab — signal grouping, strategy ranking, legacy fallback |
| `.streamlit/config.toml` | Theme (teal accent `#14B8A6`, `#FAFAFA` bg, `#111111` text) |

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Header Bar: // interview_engine_demo | Concept ▼ | ▶ Start │
├──────────┬──────────────────────────────────────────────────┤
│ Sidebar  │ Main Content (radio-driven tabs)                 │
│ (160px)  │                                                  │
│ ┌──────┐ │ Interview: Chat input + message history          │
│ │Tab ▸ │ │ Graph:      Plotly graph + layout/dimension ctrl │
│ │Phase │ │ Export:     Format selector + download button    │
│ │Turn  │ │                                                  │
│ │Nodes │ │                                                  │
│ │Canon │ │                                                  │
│ │Orphan│ │                                                  │
│ │Edges │ │                                                  │
│ └──────┘ │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

The sidebar is fixed at 160px via CSS override in `streamlit_app.py`. Tab selection uses a horizontal radio (not Streamlit's native tabs) in the sidebar.

---

## Session State Management

Streamlit's `st.session_state` holds all runtime state. Initialized once in `_init_state()`:

| Key | Type | Purpose |
|-----|------|---------|
| `api_url` | `str` | Backend URL from `API_URL` env var, default `http://localhost:8000` |
| `api_client` | `APIClient` | HTTP client instance (created once) |
| `current_session` | `SessionInfo \| None` | Active session; `None` = no interview running |
| `concepts` | `list \| None` | Cached concept list from API; `None` = not loaded |
| `chat_history` | `list[dict]` | Message list, each with `role`, `content`, optional `caption`, `extraction`, `alternatives` |
| `opening_displayed` | `bool` | Prevents re-displaying opening question on rerun |
| `interview_complete` | `bool` | Disables chat input when interview ends |
| `last_turn_result` | `dict` | Most recent API response (strategy, latency, etc.) |

### State lifecycle

1. **Session start**: `current_session` set, `chat_history` cleared, `opening_displayed` = False
2. **Opening question**: Assistant message added to `chat_history`, `opening_displayed` = True
3. **Each turn**: User input appended → `submit_turn()` → assistant message appended → `st.rerun()`
4. **Interview end**: `interview_complete` = True, closing message added
5. **New session**: All state reset, concepts reloaded

### Rerun pattern

Almost every user action triggers `st.rerun()` to refresh the UI with updated state. This is the standard Streamlit pattern — state persists across reruns, but the script re-executes top-to-bottom each time.

**Important**: Chat history is capped at 100 messages (`ChatInterface.max_history`). Older messages are silently trimmed.

---

## API Client

`ui/api_client.py` provides a dual sync/async interface:

- **Sync methods** (for Streamlit): `create_session()`, `submit_turn()`, `get_session_status()`, `get_session_graph()`, `list_sessions()`, `list_concepts()`, `start_session()`, `get_turn_scoring()`, `get_all_scoring()`
- **Async methods** (for agents): Same names with `_async` suffix

Each sync method creates a short-lived `httpx.Client` context manager — there's no persistent connection. Timeout defaults to `settings.ui_timeout` (30s).

### Graceful degradation

`get_session_status()` and `get_session_graph()` catch `HTTPStatusError` and return default empty data instead of crashing. This lets the UI render even when the backend is partially unavailable.

### SessionInfo dataclass

```python
@dataclass
class SessionInfo:
    id: str
    concept_id: str
    status: str
    opening_question: Optional[str] = None
    created_at: Optional[str] = None
```

---

## Styling Conventions

### Font injection

CSS is injected via `st.markdown(..., unsafe_allow_html=True)` in `streamlit_app.py` (lines 32-163). Two font families:

- **Inter** (`{INTER}`): Body text, chat messages, paragraphs
- **JetBrains Mono** (`{MONO}`): Labels, selectboxes, buttons, header title, stat values, tab names

Loaded from Google Fonts CDN.

### Color palette

| Token | Hex | Usage |
|-------|-----|-------|
| Accent | `#14B8A6` | Primary actions, selectbox border, stat values |
| Accent bright | `#00D4AA` | Header title text |
| Background | `#FAFAFA` | Page background |
| Surface | `#FFFFFF` | Sidebar, cards |
| Text | `#111111` | Primary text |
| Muted | `#94A3B8` | Stat labels, radio labels |
| Dark bg | `#1A1A2E → #0F3460` | Header bar gradient |
| Border | `#1E293B` | Stat dividers |

### CSS class conventions

- `.header-bar` / `.header-title` — Dark gradient header
- `.stat-block` / `.stat-label` / `.stat-value` — Sidebar metrics
- `.stat-divider` — Horizontal rule between sidebar sections

All CSS is inline in `streamlit_app.py` — no external CSS files.

---

## Component Details

### ChatInterface (`ui/components/chat.py`)

- Renders message history with role-based avatars: `:material/help:` (assistant), `:material/person:` (user)
- Caption metadata on assistant messages: `strategy:name · focus:label · 1.2s`
- Input via `st.chat_input("Your response...")`
- History trimmed to 100 messages

### GraphVisualizer (`ui/components/graph.py`)

- Builds a NetworkX graph from API node/edge data
- Layout algorithms: Spring, Kamada-Kawai, Circular
- 2D and 3D Plotly rendering
- Node colors by `node_type` (MEC palette: attribute=red, consequence=teal, value=purple, unknown=gray)
- Node size scaled by `confidence` field
- Hover shows label, type, confidence
- Controls: layout selector, 2D/3D toggle, label toggle, node type filter

### MetricsPanel (`ui/components/metrics.py`)

- Turn count with progress bar (clamped to [0, 1])
- Coverage with emoji bar (10 segments)
- Status indicator with emoji
- Signal display (first 10, dynamic types)
- Strategy description lookup (includes legacy strategy names)
- Graph stats with pie chart of node types
- Methodology-specific metrics: `_render_mec_metrics()`, `_render_jtbd_metrics()`

### ScoringTab (`ui/components/scoring.py`)

- Dual-mode: methodology-centric (new) and legacy two-tier (fallback)
- Signal grouping by prefix: `graph.node.*`, `graph.*`, `llm.*`, `temporal.*`, `meta.*`
- Strategy ranking with progress bars
- Legacy mode: turn selector, tier 1 vetoes, tier 2 weighted scoring breakdown

### SessionControls (`ui/components/controls.py`) — REMOVED

This component was removed in Apr 2026. It was from an earlier UI iteration where session management lived in the sidebar. The main app (`streamlit_app.py`) handles all session creation, loading, and export inline in the header row and export tab. No code imported from this module.

---

## Backend API Endpoints Used

| Endpoint | Method | Used by |
|----------|--------|---------|
| `/sessions` | POST | Create session |
| `/sessions/{id}/start` | POST | Get opening question |
| `/sessions/{id}/turns` | POST | Submit user input |
| `/sessions/{id}/status` | GET | Turn count, phase, coverage, signals |
| `/sessions/{id}/graph` | GET | Nodes and edges for visualization |
| `/sessions/{id}/scoring` | GET | All scoring history |
| `/sessions/{id}/scoring/{turn}` | GET | Single turn scoring |
| `/sessions/{id}/export?format=` | GET | JSON/Markdown/CSV export |
| `/sessions` | GET | List sessions |
| `/concepts` | GET | List available concept configs |

---

## Known Quirks

- **`st.rerun()` after every turn**: The entire script re-executes on each rerun. State changes that happen *after* the rerun trigger won't be visible until the *next* rerun. This is why the main app fetches status/graph at the top of the script.
- **LLM question leaking**: The backend sometimes includes candidate questions in the response. The main app strips markers like `"Selected question:"` from `next_question` before display (lines 367-378).
- **Focus node resolution**: The turn result returns `focus_node_id` (a UUID), not a label. The main app resolves it to a human-readable label by fetching the graph and building a lookup map.
- **`controls.py` removed (Apr 2026)**: Was vestigial — no code imported it. Main app handles sessions inline.
- **No multi-page architecture**: The entire UI is a single Streamlit script. Navigation is via sidebar radio, not Streamlit's native multi-page system.

---

## API Contract Audit (2026-04-27)

Systematic comparison of frontend field access against backend response schemas (`src/api/schemas.py`).

### POST `/sessions` — Create Session

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `id` | `id: str` | Match |
| `concept_id` | `concept_id: str` | Match |
| `status` | `status: str` | Match |
| `opening_question` (optional) | *(not in schema)* | Match — comes from `/start` |
| `created_at` (optional) | `created_at: datetime` | Match |

Unused: `methodology`, `config`, `turn_count`, `updated_at`, `mode`

### POST `/sessions/{id}/start` — Start Session

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `opening_question` | `opening_question: str` | Match |

Unused: `session_id`

### POST `/sessions/{id}/turns` — Submit Turn

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `next_question` | `next_question: str` | Match |
| `should_continue` | `should_continue: bool` | Match |
| `strategy_selected` | `strategy_selected: str` | Match |
| `latency_ms` | `latency_ms: int` | Match |
| `focus_node_id` | `focus_node_id: str\|None` | Match |

Unused: `turn_number`, `extracted`, `graph_state`, `scoring`, `signals`, `strategy_alternatives`

*Apr 2026 update*: `extracted` (concepts found this turn) and `strategy_alternatives` (top 3 with scores) are now surfaced in the chat history via expandable "Turn details" sections on each assistant message.

### GET `/sessions/{id}/status` — Session Status

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `turn_number` | `turn_number: int` | Match |
| `phase` | `phase: str` | Match |
| `canonical_node_count` | `canonical_node_count: int` | Match |

Unused: `status`, `should_continue`, `strategy_selected`, `strategy_reasoning`, `focus_tracing`

*Apr 2026 update*: `max_turns` is now used in the sidebar Turn stat (`turn_num/max_turns`).

### GET `/sessions/{id}/graph` — Session Graph

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `nodes[].id` | `id: str` | Match |
| `nodes[].label` | `label: str` | Match |
| `nodes[].node_type` | `node_type: str` | Match |
| `edges[].source_id` | `source_id: str` | Match |
| `edges[].target_id` | `target_id: str` | Match |

Unused: `nodes[].confidence`, `nodes[].properties`, `edges[].edge_type`, `edges[].confidence`, `edges[].properties`, `node_count`, `edge_count`

### GET `/sessions` — List Sessions

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `sessions` | `sessions: list[SessionResponse]` | Match |
| `total` | `total: int` | Match |

### GET `/concepts` — List Concepts

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `[].id` | `id: str` | Match |
| `[].name` | `name: str` | Match |
| `[].methodology` | `methodology: str` | Match |
| `[].element_count` | `element_count: int` | Match |

### GET `/sessions/{id}/export?format=` — Export

| Frontend reads | Backend provides | Status |
|---------------|-----------------|--------|
| `response.text` | Raw text (JSON/MD/CSV) | Match |

### Result

**Zero breakages.** All 8 endpoints return every field the frontend depends on, with matching types. No renames or type changes detected.
