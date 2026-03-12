# ui/components/chat.py
"""Chat interface component for Streamlit demo UI."""

from typing import List, Dict, Optional
import streamlit as st

from ui.api_client import APIClient, SessionInfo


class ChatInterface:
    """Manages the chat interface for interview conversations."""

    def __init__(self, api_client: APIClient):
        """Initialize chat interface."""
        self.api_client = api_client
        self.max_history = 100

    def render(self, session_info: Optional[SessionInfo]) -> Optional[str]:
        """Render the chat interface."""
        if not session_info:
            st.info("👋 Create or select a session to start the interview.")
            return None

        # Display opening question if available
        if session_info.opening_question:
            self._display_opening_question(session_info.opening_question)

        # Display chat history
        self._display_chat_history()

        # Don't show input if interview is complete
        if st.session_state.get("interview_complete"):
            st.info("Interview complete. Start a new session to continue.")
            return None

        # Chat input
        user_input = st.chat_input("Your response...")

        if user_input:
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            st.session_state.chat_history.append(
                {"role": "user", "content": user_input}
            )

        return user_input if user_input else None

    def _display_opening_question(self, question: str):
        """Display the opening question."""
        if "opening_displayed" not in st.session_state:
            with st.chat_message("assistant", avatar=":material/help:"):
                st.write(question)
            st.session_state.opening_displayed = True
            st.session_state.chat_history = [{"role": "assistant", "content": question}]

    def _display_chat_history(self):
        """Display the chat history."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for message in st.session_state.chat_history:
            avatar = ":material/help:" if message["role"] == "assistant" else ":material/person:"
            with st.chat_message(message["role"], avatar=avatar):
                st.write(message["content"])
                if message.get("caption"):
                    st.caption(message["caption"])

    def add_assistant_message(self, content: str, caption: str = ""):
        """Add an assistant message to the chat history."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        msg: Dict[str, str] = {"role": "assistant", "content": content}
        if caption:
            msg["caption"] = caption
        st.session_state.chat_history.append(msg)

        # Trim history if needed
        if len(st.session_state.chat_history) > self.max_history:
            st.session_state.chat_history = st.session_state.chat_history[
                -self.max_history :
            ]

    def clear_history(self):
        """Clear the chat history."""
        st.session_state.chat_history = []
        if "opening_displayed" in st.session_state:
            del st.session_state.opening_displayed

    def get_history(self) -> List[Dict[str, str]]:
        """Get the current chat history."""
        return st.session_state.get("chat_history", [])


def initialize_chat_state():
    """Initialize chat-related session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "opening_displayed" not in st.session_state:
        st.session_state.opening_displayed = False
