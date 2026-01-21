"""
Main Streamlit application for the interview system demo UI.

Integrates all UI components:
- Chat interface for interview conversation
- Graph visualization for knowledge graph
- Metrics panel for statistics and diagnostics
- Session controls for managing sessions

Run with: streamlit run ui/streamlit_app.py
"""

import asyncio
from typing import Optional, Dict, Any
import streamlit as st

from ui.api_client import APIClient
from ui.components.chat import ChatInterface, initialize_chat_state
from ui.components.graph import GraphVisualizer, render_graph_stats
from ui.components.metrics import MetricsPanel, render_turn_diagnostics, render_coverage_details
from ui.components.controls import (
    SessionControls,
    initialize_session_state,
    get_current_session,
)


# Page configuration
st.set_page_config(
    page_title="Interview System Demo",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .stProgress > div > div > div > div {
        background-color: #6C5CE7;
    }
</style>
""", unsafe_allow_html=True)


def initialize_api_client() -> APIClient:
    """Initialize or get existing API client from session state."""
    if "api_client" not in st.session_state:
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        st.session_state.api_client = APIClient(base_url=api_url)
    return st.session_state.api_client


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()
    initialize_chat_state()

    # Initialize API client
    api_client = initialize_api_client()
    st.session_state.api_client = api_client

    # Title and header
    st.title("🎙️ Adaptive Interview System")
    st.markdown("Demo UI for automated qualitative research interviews")

    # Sidebar - Session Controls
    session_controls = SessionControls(api_client)
    current_session = session_controls.render()

    # API connection status
    st.sidebar.divider()
    api_url = st.sidebar.text_input(
        "API URL",
        value=st.session_state.get("api_url", "http://localhost:8000"),
        help="FastAPI backend URL"
    )

    if st.sidebar.button("🔄 Reconnect"):
        st.session_state.api_url = api_url
        st.session_state.api_client = APIClient(base_url=api_url)
        st.sidebar.success("Reconnected!")

    # Main content area
    if not current_session:
        _render_welcome_screen()
    else:
        _render_interview_screen(api_client, current_session)


def _render_welcome_screen():
    """Render welcome screen when no session is active."""
    st.info("👋 Welcome! Create a new session or select an existing one from the sidebar to begin.")

    st.markdown("""
    ## About This System

    The **Adaptive Interview System** conducts automated qualitative research interviews using:

    - **Natural Language Processing** to extract concepts and relationships
    - **Knowledge Graphs** to build respondent mental models in real-time
    - **Adaptive Questioning** that responds to what respondents actually say

    ### How It Works

    1. **Create a session** with a concept configuration (e.g., "Oat Milk")
    2. **Conduct the interview** by responding to system questions
    3. **Watch in real-time** as the knowledge graph builds
    4. **Review metrics** showing coverage, depth, and strategy selection

    ### Features

    - 📊 **Real-time visualization** of the knowledge graph
    - 🎯 **Coverage tracking** for stimulus concept elements
    - 🔍 **Adaptive strategies** (deepen, broaden, cover, close)
    - 📈 **Diagnostics panel** with scoring breakdown
    - 📥 **Export** interviews to JSON/Markdown
    """)


def _render_interview_screen(api_client: APIClient, current_session):
    """Render the main interview interface."""
    # Create tabs for main content
    tab1, tab2, tab3 = st.tabs(["💬 Interview", "🕸️ Knowledge Graph", "📊 Metrics"])

    # Get current data
    status_data = _get_session_status(api_client, current_session.id)
    graph_data = _get_session_graph(api_client, current_session.id)

    # Tab 1: Interview
    with tab1:
        _render_interview_tab(api_client, current_session, status_data, graph_data)

    # Tab 2: Knowledge Graph
    with tab2:
        _render_graph_tab(graph_data)

    # Tab 3: Metrics
    with tab3:
        _render_metrics_tab(status_data, graph_data)


def _render_interview_tab(
    api_client: APIClient,
    current_session,
    status_data: Dict[str, Any],
    graph_data: Optional[Dict[str, Any]],
):
    """Render the interview chat tab."""
    # Create columns for layout
    left_col, right_col = st.columns([2, 1])

    with left_col:
        # Chat interface
        chat_interface = ChatInterface(api_client)
        user_input = chat_interface.render(current_session)

        # Process user input
        if user_input:
            _process_turn(api_client, current_session.id, user_input, chat_interface)

    with right_col:
        # Quick stats
        st.subheader("Quick Stats")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Turns", status_data.get("turn_number", 0))
        with col2:
            coverage = status_data.get("coverage", 0.0)
            st.metric("Coverage", f"{coverage*100:.0f}%")

        # Strategy indicator
        strategy = status_data.get("strategy_selected", "unknown")
        st.info(f"Strategy: {strategy.upper()}")

        # Show last turn diagnostics
        if "last_turn_result" in st.session_state:
            with st.expander("Last Turn"):
                render_turn_diagnostics(st.session_state.last_turn_result)


def _process_turn(
    api_client: APIClient,
    session_id: str,
    user_input: str,
    chat_interface: ChatInterface,
):
    """Process a user turn through the API."""
    with st.spinner("Processing..."):
        try:
            result = asyncio.run(api_client.submit_turn(session_id, user_input))

            # Store result for diagnostics
            st.session_state.last_turn_result = result

            # Add assistant response to chat
            next_question = result.get("next_question")
            if next_question:
                chat_interface.add_assistant_message(next_question)

            # Check if interview should continue
            should_continue = result.get("should_continue", True)
            if not should_continue:
                st.success("🎉 Interview complete!")

            st.rerun()

        except Exception as e:
            st.error(f"Error processing turn: {str(e)}")


def _render_graph_tab(graph_data: Dict[str, Any]):
    """Render the knowledge graph visualization tab."""
    # Graph visualizer
    visualizer = GraphVisualizer()

    # Render controls in sidebar
    controls = visualizer.render_controls()

    # Render graph
    fig = visualizer.render(graph_data, controls)

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No graph data to display yet.")

    # Render stats in sidebar
    render_graph_stats(graph_data)


def _render_metrics_tab(status_data: Dict[str, Any], graph_data: Optional[Dict]):
    """Render the metrics and diagnostics tab."""
    metrics_panel = MetricsPanel()
    metrics_panel.render(status_data, graph_data)

    # Coverage details
    if "elements" in status_data:
        render_coverage_details(status_data)


def _get_session_status(api_client: APIClient, session_id: str) -> Dict[str, Any]:
    """Get current session status from API."""
    try:
        return asyncio.run(api_client.get_session_status(session_id))
    except Exception as e:
        st.error(f"Failed to get session status: {str(e)}")
        return {}


def _get_session_graph(api_client: APIClient, session_id: str) -> Dict[str, Any]:
    """Get session knowledge graph from API."""
    try:
        return asyncio.run(api_client.get_session_graph(session_id))
    except Exception as e:
        st.error(f"Failed to get graph data: {str(e)}")
        return {}


if __name__ == "__main__":
    main()
