"""
Main Streamlit application for the interview system demo UI.

Title + concept selector + start on one row.
Sidebar for counters/phase (column).
3 tabs: Interview, Graph, Export.
Run with: streamlit run ui/streamlit_app.py
"""

import os
import httpx
from typing import Dict, Any

import streamlit as st

from src.core.config import settings
from ui.api_client import APIClient
from ui.components.chat import ChatInterface, initialize_chat_state
from ui.components.graph import GraphVisualizer

# --- Page config ---
st.set_page_config(
    page_title="Adaptive Interview System",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

MONO = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Courier New', monospace"
INTER = "'Inter', system-ui, -apple-system, sans-serif"

st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap');

    /* Inter for chat/readable text */
    p, li, .stMarkdown {{
        font-family: {INTER} !important;
        font-size: 15px !important;
    }}

    /* Monospace for form controls */
    label, [data-testid="stTextInput"] input,
    [data-testid="stSelectbox"] span[data-baseweb="select"] {{
        font-family: {MONO} !important;
    }}

    /* Compact top spacing */
    .block-container {{ padding-top: 3rem !important; }}

    /* Narrower sidebar */
    [data-testid="stSidebar"] {{ min-width: 160px !important; max-width: 160px !important; width: 160px !important; }}
    [data-testid="stSidebar"] > div:first-child {{ width: 160px !important; }}

    /* Dark header bar */
    .header-bar {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: #e0e0e0;
        padding: 8px 16px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 8px;
        height: 44px;
    }}
    .header-title {{
        color: #00d4aa;
        font-family: {MONO};
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        white-space: nowrap;
        margin: 0;
    }}

    /* Sidebar stat rows */
    .stat-block {{
        font-family: {MONO};
        margin-bottom: 14px;
    }}
    .stat-label {{
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
    }}
    .stat-value {{
        color: #00d4aa;
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.2;
    }}
    .stat-value.phase-val {{
        font-size: 0.95rem;
        letter-spacing: 0.05em;
    }}
    .stat-divider {{
        border: none;
        border-top: 1px solid #1e293b;
        margin: 8px 0;
    }}

    /* Tabs: monospace + uppercase + match sidebar label size */
    [data-testid="stTabs"] button {{
        font-family: {MONO} !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-weight: 600 !important;
    }}

    /* Header row: dropdown + button font size matching title */
    [data-testid="stSelectbox"] * {{
        font-family: {MONO} !important;
        font-size: 0.95rem !important;
    }}
    /* Teal border on dropdown to match start button */
    [data-testid="stSelectbox"] > div > div {{
        border: 2px solid #14B8A6 !important;
        border-radius: 6px !important;
        height: 44px !important;
        display: flex !important;
        align-items: center !important;
    }}
    .stButton > button {{
        font-family: {MONO} !important;
        font-size: 0.95rem !important;
        height: 44px !important;
    }}

    /* "Interview Chat" subheader — match header row */
    h3 {{
        font-family: {MONO} !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}

    /* Sidebar tab-selector radio: match stat-label style */
    /* Target the <p> inside label to beat the global p font rule */
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        font-family: {MONO} !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-weight: 400 !important;
        color: #94a3b8 !important;
    }}
    /* Align label text vertically with the radio circle */
    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        display: flex !important;
        align-items: center !important;
        padding-top: 2px !important;
    }}

</style>
""",
    unsafe_allow_html=True,
)


# --- State init ---
def _init_state():
    if "api_url" not in st.session_state:
        st.session_state.api_url = os.environ.get("API_URL", "http://localhost:8000")
    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient(
            base_url=st.session_state.api_url, timeout=settings.ui_timeout
        )
    if "current_session" not in st.session_state:
        st.session_state.current_session = None
    if "concepts" not in st.session_state:
        st.session_state.concepts = None
    initialize_chat_state()


_init_state()
api_client: APIClient = st.session_state.api_client


# --- Load concepts ---
def _load_concepts():
    try:
        st.session_state.concepts = api_client.list_concepts()
    except Exception:
        st.session_state.concepts = []


if st.session_state.concepts is None:
    _load_concepts()

concepts = st.session_state.concepts or []


def _concept_label(c: dict) -> str:
    name = c.get("name", c["id"])
    method = c.get("methodology", "")
    if method:
        # Humanize methodology id: "means_end_chain" → "Means End Chain"
        method_label = method.replace("_", " ").title()
        return f"{name}  /  {method_label}"
    return name


concept_map = {_concept_label(c): c for c in concepts}


# --- Fetch live data ---
def _get_status() -> Dict[str, Any]:
    session = st.session_state.current_session
    if not session:
        return {}
    try:
        return api_client.get_session_status(session.id)
    except Exception:
        return {}


def _get_graph() -> Dict[str, Any]:
    session = st.session_state.current_session
    if not session:
        return {"nodes": [], "edges": []}
    try:
        return api_client.get_session_graph(session.id)
    except Exception:
        return {"nodes": [], "edges": []}


status_data = _get_status()
graph_data = _get_graph()

nodes = graph_data.get("nodes", [])
edges = graph_data.get("edges", [])
connected_ids = set()
for e in edges:
    connected_ids.add(e.get("source_id"))
    connected_ids.add(e.get("target_id"))
orphan_count = sum(1 for n in nodes if n.get("id") not in connected_ids)

canonical_count = status_data.get("canonical_node_count", 0)

turn_num = status_data.get("turn_number", 0)
phase = status_data.get("phase", "—")
phase_str = phase.upper() if isinstance(phase, str) and phase != "—" else phase


# =============================================================================
# SIDEBAR: Tab selector + Phase + counters
# =============================================================================
with st.sidebar:
    tab_sel = st.radio(
        "view",
        options=["Interview", "Graph", "Export"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown(
        f"""
<hr class="stat-divider"/>
<div class="stat-block">
  <div class="stat-label">Phase</div>
  <div class="stat-value phase-val">{phase_str}</div>
</div>
<hr class="stat-divider"/>
<div class="stat-block">
  <div class="stat-label">Turn</div>
  <div class="stat-value">{turn_num}</div>
</div>
<div class="stat-block">
  <div class="stat-label">Nodes</div>
  <div class="stat-value">{len(nodes)}</div>
</div>
<div class="stat-block">
  <div class="stat-label">Canonical</div>
  <div class="stat-value">{canonical_count}</div>
</div>
<div class="stat-block">
  <div class="stat-label">Orphans</div>
  <div class="stat-value">{orphan_count}</div>
</div>
<div class="stat-block">
  <div class="stat-label">Edges</div>
  <div class="stat-value">{len(edges)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# =============================================================================
# HEADER ROW: Title + concept dropdown + start button
# =============================================================================
h_title, h_concept, h_start = st.columns([2, 3, 1])

with h_title:
    st.markdown(
        '<div class="header-bar"><span class="header-title">// interview_engine_demo</span></div>',
        unsafe_allow_html=True,
    )

with h_concept:
    if concepts:
        selected_name = st.selectbox(
            "Concept",
            options=list(concept_map.keys()),
            label_visibility="collapsed",
            disabled=st.session_state.current_session is not None,
        )
        selected_concept = concept_map.get(selected_name, {})
        methodology = selected_concept.get("methodology", "—")
    else:
        st.warning("No concepts available — is the API running?")
        selected_concept = {}
        methodology = "—"

with h_start:
    start_disabled = (
        not selected_concept or st.session_state.current_session is not None
    )
    if st.button("▶ Start", type="primary", width="stretch", disabled=start_disabled):
        concept_id = selected_concept["id"]
        with st.spinner("Starting..."):
            try:
                session_info = api_client.create_session(
                    concept_id=concept_id,
                    methodology=methodology,
                )
                opening = api_client.start_session(session_info.id)
                st.session_state.current_session = session_info
                st.session_state.chat_history = []
                st.session_state.opening_displayed = False
                st.session_state.interview_complete = False
                if opening:
                    chat = ChatInterface(api_client)
                    chat.add_assistant_message(opening)
                    st.session_state.opening_displayed = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")


# =============================================================================
# MAIN CONTENT: driven by sidebar tab selector
# =============================================================================
current_session = st.session_state.current_session

# --- Interview Tab ---
if tab_sel == "Interview":
    if not current_session:
        st.info("Select a concept and click ▶ Start to begin.")
    else:
        chat_interface = ChatInterface(api_client)
        user_input = chat_interface.render(current_session)

        if user_input:
            with st.spinner("Processing..."):
                try:
                    result = api_client.submit_turn(current_session.id, user_input)
                    st.session_state.last_turn_result = result
                    next_q = result.get("next_question", "")
                    if next_q:
                        # Strip candidate questions if LLM leaked them
                        for marker in ["Selected question:", "Selected Question:", "Final question:"]:
                            if marker in next_q:
                                next_q = next_q.split(marker, 1)[1].strip().strip('"').strip("'")
                                break
                        strat = result.get("strategy_selected", "")
                        latency = result.get("latency_ms", 0)
                        latency_s = f"{latency/1000:.1f}s" if latency else "—"
                        # Focus node: top strategy_alternative node_id resolved to label
                        focus_label = ""
                        nid = result.get("focus_node_id", "")
                        if nid:
                            g = _get_graph()
                            node_map = {n["id"]: n.get("label", "") for n in g.get("nodes", [])}
                            focus_label = node_map.get(nid, "")
                        parts = []
                        if strat:
                            parts.append(f"strategy:{strat}")
                        if focus_label:
                            parts.append(f"focus:{focus_label}")
                        if latency_s:
                            parts.append(latency_s)
                        caption = " · ".join(parts)
                        chat_interface.add_assistant_message(next_q, caption=caption)
                    if not result.get("should_continue", True):
                        st.session_state.interview_complete = True
                        chat_interface.add_assistant_message(
                            "Thank you — this has been really insightful. "
                            "We'll wrap up here."
                        )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# --- Graph Tab ---
elif tab_sel == "Graph":
    if not current_session:
        st.info("Start an interview to see the conversation graph.")
    else:
        # Re-fetch graph fresh inside the tab
        fresh_graph = _get_graph()
        visualizer = GraphVisualizer()

        ctrl1, ctrl2 = st.columns([1, 2])
        with ctrl1:
            layout_algo = st.selectbox("Layout", options=list(visualizer.layout_algorithms.keys()), index=0)
        with ctrl2:
            d_col, l_col = st.columns([1, 1])
            with d_col:
                dimensions = st.radio("View", options=["2D", "3D"], horizontal=True)
            with l_col:
                show_labels = st.checkbox("Show Labels", value=True)

        # Use actual node types from data, not hardcoded MEC types
        actual_types = list({n.get("node_type", "unknown") for n in fresh_graph.get("nodes", [])})
        controls = {
            "layout": layout_algo,
            "dimensions": dimensions,
            "show_labels": show_labels,
            "node_filter": actual_types,
        }

        fig = visualizer.render(fresh_graph, controls)
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No graph data yet — complete at least one turn.")


# --- Export Tab ---
elif tab_sel == "Export":
    if not current_session:
        st.info("Start an interview to enable export.")
    else:
        st.write(f"Session: `{current_session.id[:8]}`")
        st.markdown("""
<style>
table { width: 100%; }
td:first-child { white-space: nowrap; width: 1%; padding-right: 1rem; }
td:last-child { width: 99%; }
</style>

| Format | Contents |
|--------|----------|
| **JSON** | Full raw data: utterances, KG nodes/edges, signals, scoring per turn. Upload to [observablehq.com/d/7c8f49e0dec320fd](https://observablehq.com/d/7c8f49e0dec320fd) for detailed visualisation. |
| **Markdown** | Human-readable transcript + interview summary |
| **CSV** | One row per turn: turn, phase, strategy, question, response |
""", unsafe_allow_html=True)
        export_format = st.selectbox("Format", options=["JSON", "Markdown", "CSV"])

        if st.button("Export", type="primary"):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(
                        f"{api_client.base_url}/sessions/{current_session.id}/export",
                        params={"format": export_format.lower()},
                    )
                    response.raise_for_status()
                    ext = "md" if export_format == "Markdown" else export_format.lower()
                    mime = {"json": "application/json", "markdown": "text/markdown", "csv": "text/csv"}
                    st.download_button(
                        label=f"Download {export_format}",
                        data=response.text,
                        file_name=f"session_{current_session.id[:8]}.{ext}",
                        mime=mime.get(export_format.lower(), "text/plain"),
                        type="primary",
                    )
            except Exception as e:
                st.error(f"Export failed: {e}")
