"""
Scoring transparency component for Streamlit demo UI.

Displays detailed scoring breakdown for each turn:
- All (strategy, focus) candidates considered
- Tier 1 veto results
- Tier 2 scorer breakdown
- Final ranking and winner selection
"""

from typing import Any, Dict
import streamlit as st


class ScoringTab:
    """
    Displays scoring transparency data.

    Shows:
    - Turn selector to view different turns
    - Candidates table with scores and vetoes
    - Expandable Tier 1 veto details
    - Expandable Tier 2 scorer breakdown
    """

    def __init__(self):
        """Initialize scoring tab."""
        self.emoji = {
            "selected": "✅",
            "vetoed": "🚫",
            "pass": "✓",
        }

    def render(self, api_client, current_session):
        """
        Render the scoring tab.

        Args:
            api_client: API client for backend communication
            current_session: Current session info
        """
        st.subheader("📊 Scoring Transparency")

        if not current_session:
            st.info("No session selected.")
            return

        # Load all scoring data
        all_scoring = api_client.get_all_scoring(current_session.id)

        if not all_scoring:
            st.info("No scoring data available yet. Complete some interview turns first.")
            return

        # Turn selector
        turn_numbers = [t["turn_number"] for t in all_scoring]
        if not turn_numbers:
            st.info("No scoring data available yet.")
            return

        selected_turn_idx = len(turn_numbers) - 1  # Default to latest turn
        selected_turn = st.selectbox(
            "Select Turn",
            options=range(len(turn_numbers)),
            format_func=lambda i: f"Turn {turn_numbers[i]}",
            index=selected_turn_idx,
        )

        turn_data = all_scoring[selected_turn]

        # Display turn summary
        self._render_turn_summary(turn_data)

        # Display candidates table
        self._render_candidates_table(turn_data)

    def _render_turn_summary(self, turn_data: Dict[str, Any]):
        """Render turn summary with winner info."""
        turn_number = turn_data["turn_number"]
        candidates = turn_data["candidates"]
        turn_data.get("winner_strategy_id")

        # Find winner
        winner = next((c for c in candidates if c["is_selected"]), None)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Turn", str(turn_number))

        with col2:
            total_candidates = len(candidates)
            vetoed_count = sum(1 for c in candidates if c.get("vetoed_by"))
            st.metric("Candidates", f"{total_candidates} total, {vetoed_count} vetoed")

        with col3:
            if winner:
                st.metric("Winner", f"{winner['strategy_name']}")
            else:
                st.metric("Winner", "None")

    def _render_candidates_table(self, turn_data: Dict[str, Any]):
        """Render the candidates table with expandable details."""
        candidates = turn_data["candidates"]

        if not candidates:
            st.info("No candidates for this turn.")
            return

        # Sort by final score (descending)
        sorted_candidates = sorted(candidates, key=lambda c: c["final_score"], reverse=True)

        for idx, candidate in enumerate(sorted_candidates):
            # Status indicator
            if candidate["is_selected"]:
                status_icon = "✅ **SELECTED**"
            elif candidate.get("vetoed_by"):
                status_icon = f"🚫 Vetoed by {candidate['vetoed_by']}"
            else:
                status_icon = "📊 Runner-up"

            # Main candidate row
            with st.expander(
                f"{status_icon} | **{candidate['strategy_name']}** (Score: {candidate['final_score']:.2f})"
            ):
                # Focus info
                st.write(f"**Focus Type:** {candidate['focus_type']}")
                if candidate.get("focus_description"):
                    st.write(f"**Focus:** {candidate['focus_description']}")

                # Tier 1 vetoes
                if candidate.get("tier1_results"):
                    with st.expander("🔍 Tier 1: Hard Constraints (Vetoes)"):
                        for t1 in candidate["tier1_results"]:
                            if t1["is_veto"]:
                                st.error(f"❌ {t1['scorer_id']}: **VETO** - {t1['reasoning']}")
                            else:
                                st.success(f"✓ {t1['scorer_id']}: Pass")

                # Tier 2 scoring breakdown
                if candidate.get("tier2_results"):
                    with st.expander(f"📈 Tier 2: Weighted Scoring (Score: {candidate['final_score']:.2f})"):
                        # Calculate score contribution
                        total_contribution = sum(t2["contribution"] for t2 in candidate["tier2_results"])

                        # Show each scorer
                        for t2 in candidate["tier2_results"]:
                            # Progress bar for contribution
                            pct_of_total = (t2["contribution"] / total_contribution * 100) if total_contribution > 0 else 0

                            cols = st.columns([3, 2, 1])
                            with cols[0]:
                                st.write(f"**{t2['scorer_id']}**")

                            with cols[1]:
                                st.caption(f"Raw: {t2['raw_score']:.2f} × {t2['weight']:.2f} = {t2['contribution']:.3f}")

                            with cols[2]:
                                st.caption(f"{pct_of_total:.0f}%")

                            # Reasoning
                            if t2.get("reasoning"):
                                st.caption(t2["reasoning"])

                            # Contribution bar
                            st.progress(t2["contribution"] / 2.0)  # Max contribution is weight × 2.0

                        st.write(f"**Total Score:** 1.0 (base) + Σ(contributions) = {candidate['final_score']:.2f}")

                # Reasoning trace
                if candidate.get("reasoning"):
                    with st.expander("💭 Reasoning Trace"):
                        st.write(candidate["reasoning"])

            st.divider()


def render_scoring_tab(api_client, current_session):
    """
    Convenience function to render scoring tab.

    Args:
        api_client: API client
        current_session: Current session info
    """
    scoring_tab = ScoringTab()
    scoring_tab.render(api_client, current_session)
