"""
Session controls component for Streamlit demo UI.

Provides sidebar controls for:
- Creating new sessions
- Selecting existing sessions
- Viewing session list
- Deleting sessions
- Exporting session data
"""

from typing import Optional, Dict, Any
import streamlit as st

from ui.api_client import APIClient, SessionInfo


class SessionControls:
    """
    Manages session-related UI controls in the sidebar.

    Provides:
    - New session creation
    - Session selection from list
    - Session details display
    - Export functionality
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize session controls.

        Args:
            api_client: API client for backend communication
        """
        self.api_client = api_client

    def render(self) -> Optional[SessionInfo]:
        """
        Render session controls in sidebar.

        Returns:
            Currently selected SessionInfo, or None
        """
        st.sidebar.title("🎙️ Interview System")
        st.sidebar.divider()

        # Tab navigation for session controls
        tab1, tab2, tab3 = st.sidebar.tabs(["New", "Sessions", "Export"])

        with tab1:
            self._render_new_session()

        with tab2:
            self._render_session_list()

        with tab3:
            self._render_export()

        # Return current session from state
        return st.session_state.get("current_session")

    def _render_new_session(self):
        """Render new session creation form."""
        st.subheader("Create New Session")

        # Load concepts from API
        if st.session_state.get("concepts") is None:
            self._load_concepts()

        concepts = st.session_state.get("concepts", [])

        if not concepts:
            st.warning("No concepts available. Check if the API is running.")
            return

        # Concept selection - map concept name/id for display
        concept_options = {
            f"{c.get('name', c['id'])} ({c['id']})": c["id"] for c in concepts
        }
        concept_display_id = st.selectbox(
            "Concept",
            options=list(concept_options.keys()),
            label_visibility="collapsed",
        )
        concept_id = concept_options[concept_display_id]

        # Methodology selection
        methodology = st.selectbox(
            "Methodology",
            options=[
                "means_end_chain",
                "jobs_to_be_done",
                "critical_incident",
                "repertory_grid",
            ],
            label_visibility="collapsed",
        )

        # Create button
        if st.button("🚀 Start Interview", type="primary", use_container_width=True):
            self._create_session(concept_id, methodology)

    def _create_session(self, concept_id: str, methodology: str):
        """Create a new session."""
        with st.spinner("Creating session..."):
            try:
                session_info = st.session_state.api_client.create_session(
                    concept_id=concept_id,
                    methodology=methodology,
                    config={},  # Use default max_turns from config/interview_config.yaml
                )

                # Start the session to get opening question
                opening_question = st.session_state.api_client.start_session(
                    session_info.id
                )

                # Store in session state
                st.session_state.current_session = session_info
                st.session_state.chat_history = []
                st.session_state.opening_displayed = False

                # Add opening question to chat
                if opening_question:
                    from ui.components.chat import ChatInterface

                    chat = ChatInterface(st.session_state.api_client)
                    chat.add_assistant_message(opening_question)
                    st.session_state.opening_displayed = True

                # Invalidate sessions cache so it reloads with new session
                st.session_state.sessions = None

                st.success(f"Session {session_info.id[:8]} created!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to create session: {str(e)}")

    def _render_session_list(self) -> Optional[SessionInfo]:
        """Render session list and selection."""
        st.subheader("Sessions")

        # Load sessions
        if st.session_state.get("sessions") is None:
            self._load_sessions()

        sessions = st.session_state.get("sessions", [])

        # Validate sessions format (detect bad cached data from before fix)
        if sessions and isinstance(sessions, dict):
            # Old format: {"sessions": [...], "total": N}
            if "sessions" in sessions:
                sessions = sessions["sessions"]
                st.session_state.sessions = sessions
            else:
                # Bad data, clear and reload
                st.session_state.sessions = None
                self._load_sessions()
                sessions = st.session_state.get("sessions", [])

        if not sessions:
            st.info("No sessions found.")
            return None

        # Session selection
        session_options = {
            f"{s['id'][:8]} ({s.get('status', 'unknown')})": s for s in sessions
        }

        selected = st.selectbox(
            "Select Session",
            options=list(session_options.keys()),
            label_visibility="collapsed",
        )

        if selected:
            session = session_options[selected]

            # Display session details
            self._display_session_details(session)

            # Action buttons
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📂 Load", use_container_width=True):
                    self._load_session(session)

            with col2:
                if st.button("🗑️ Delete", use_container_width=True):
                    self._delete_session(session["id"])

            # Set as current if loaded
            current = st.session_state.get("current_session")
            if current and current.id == session["id"]:
                return current

        return None

    def _display_session_details(self, session: Dict[str, Any]):
        """Display details for a session."""
        with st.expander("Session Details"):
            st.write(f"**ID:** {session['id']}")
            st.write(f"**Status:** {session.get('status', 'unknown')}")
            st.write(f"**Concept:** {session.get('concept_id', 'N/A')}")

            created = session.get("created_at", "N/A")
            if created != "N/A":
                st.write(f"**Created:** {created}")

            if session.get("completed_at"):
                st.write(f"**Completed:** {session['completed_at']}")

    def _load_session(self, session: Dict[str, Any]):
        """Load an existing session."""
        session_id = session["id"]

        with st.spinner(f"Loading session {session_id[:8]}..."):
            try:
                # Get full session info
                status = st.session_state.api_client.get_session_status(session_id)

                # Create SessionInfo
                session_info = SessionInfo(
                    id=session_id,
                    concept_id=session.get("concept_id", ""),
                    status=status.get("status", "unknown"),
                    created_at=session.get("created_at"),
                )

                st.session_state.current_session = session_info
                st.session_state.chat_history = []
                st.session_state.opening_displayed = False

                st.success(f"Session {session_id[:8]} loaded!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to load session: {str(e)}")

    def _delete_session(self, session_id: str):
        """Delete a session."""
        if not st.session_state.get("confirm_delete", False):
            st.session_state.confirm_delete = True
            st.warning("Click again to confirm deletion")
            return

        st.session_state.confirm_delete = False

        with st.spinner("Deleting session..."):
            try:
                client = st.session_state.api_client._get_client()
                client.delete(
                    f"{st.session_state.api_client.base_url}/sessions/{session_id}"
                )

                # Clear from state if it was current
                current = st.session_state.get("current_session")
                if current and current.id == session_id:
                    st.session_state.current_session = None
                    st.session_state.chat_history = []

                # Reload session list
                self._load_sessions()

                st.success("Session deleted!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to delete session: {str(e)}")

    def _load_sessions(self):
        """Load sessions from API."""
        try:
            response = st.session_state.api_client.list_sessions()
            st.session_state.sessions = response.get("sessions", [])
        except Exception as e:
            st.error(f"Failed to load sessions: {str(e)}")
            st.session_state.sessions = []

    def _load_concepts(self):
        """Load available concepts from API."""
        try:
            concepts = self.api_client.list_concepts()
            st.session_state.concepts = concepts
        except Exception as e:
            st.error(f"Failed to load concepts: {str(e)}")
            st.session_state.concepts = []

    def _render_export(self):
        """Render export options."""
        st.subheader("Export Session")

        current = st.session_state.get("current_session")

        if not current:
            st.info("No session selected.")
            return

        st.write(f"Session: {current.id[:8]}")

        # Export format
        export_format = st.selectbox(
            "Format",
            options=["JSON", "Markdown"],
        )

        # Export button
        if st.button("📥 Export", use_container_width=True):
            self._export_session(current.id, export_format)

    def _export_session(self, session_id: str, format: str):
        """Export session data."""
        with st.spinner("Exporting..."):
            try:
                import httpx

                with httpx.Client(timeout=30.0) as client:
                    # Call export endpoint
                    params = {"format": format.lower()}
                    response = client.get(
                        f"{st.session_state.api_client.base_url}/sessions/{session_id}/export",
                        params=params,
                    )
                    response.raise_for_status()

                    data = response.text

                    # Display download button
                    st.download_button(
                        label=f"Download {format}",
                        data=data,
                        file_name=f"session_{session_id[:8]}.{format.lower()}",
                        mime=f"application/{format.lower()}",
                        type="primary",
                    )

            except Exception as e:
                st.error(f"Export failed: {str(e)}")


def initialize_session_state():
    """Initialize session-related state variables."""
    if "current_session" not in st.session_state:
        st.session_state.current_session = None
    if "sessions" not in st.session_state:
        st.session_state.sessions = None
    if "concepts" not in st.session_state:
        st.session_state.concepts = None
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = False


def get_current_session() -> Optional[SessionInfo]:
    """Get the current active session."""
    return st.session_state.get("current_session")


def clear_current_session():
    """Clear the current session."""
    st.session_state.current_session = None
    st.session_state.chat_history = []
    if "opening_displayed" in st.session_state:
        del st.session_state.opening_displayed
