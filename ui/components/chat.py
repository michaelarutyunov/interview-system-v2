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
        st.subheader("💬 Interview Chat")

        if not session_info:
            st.info("👋 Create or select a session to start the interview.")
            return None

        # Display opening question if available
        if session_info.opening_question:
            self._display_opening_question(session_info.opening_question)

        # Display chat history
        self._display_chat_history()

        # Chat input
        user_input = st.chat_input("Your response...")

        if user_input:
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })

        return user_input if user_input else None

    def _display_opening_question(self, question: str):
        """Display the opening question."""
        if "opening_displayed" not in st.session_state:
            with st.chat_message("assistant"):
                st.write(question)
            st.session_state.opening_displayed = True
            st.session_state.chat_history = [{
                "role": "assistant",
                "content": question
            }]

    def _display_chat_history(self):
        """Display the chat history."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    def add_assistant_message(self, content: str):
        """Add an assistant message to the chat history."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": content
        })

        # Trim history if needed
        if len(st.session_state.chat_history) > self.max_history:
            st.session_state.chat_history = st.session_state.chat_history[-self.max_history:]

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
