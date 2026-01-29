"""
Scoring transparency component for Streamlit demo UI.

Updated for methodology-centric architecture:
- Displays methodology-specific signals
- Shows strategy ranking with signal-based scoring
- Supports backward compatibility with two-tier scoring
"""

from typing import Any, Dict, Optional
import streamlit as st


class ScoringTab:
    """
    Displays scoring transparency data.

    Shows:
    - Methodology-specific signals (MEC, JTBD, etc.)
    - Signal grouping (graph, response, history)
    - Strategy ranking with scores
    - Backward compatible with two-tier scoring
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

        # Try new methodology-centric scoring first
        methodology_data = self._get_methodology_scoring(api_client, current_session)

        if methodology_data:
            self._render_methodology_scoring(methodology_data, current_session)
        else:
            # Fall back to legacy two-tier scoring
            self._render_legacy_scoring(api_client, current_session)

    def _get_methodology_scoring(
        self, api_client, current_session
    ) -> Optional[Dict[str, Any]]:
        """
        Try to get methodology-centric scoring data.

        Returns None if backend doesn't support new architecture yet.
        """
        try:
            # Try to get session status which should include methodology signals
            status = api_client.get_session_status(current_session.id)

            # Check if new methodology signals are present
            if "signals" in status or "strategy_alternatives" in status:
                return {
                    "methodology": status.get("methodology", "means_end_chain"),
                    "signals": status.get("signals", {}),
                    "strategy_alternatives": status.get("strategy_alternatives", []),
                    "turn_number": status.get("turn_number", 0),
                }
        except Exception:
            pass

        return None

    def _render_methodology_scoring(self, data: Dict[str, Any], current_session):
        """Render methodology-centric scoring display."""
        methodology = data.get("methodology", "means_end_chain")
        signals = data.get("signals", {})
        alternatives = data.get("strategy_alternatives", [])

        st.subheader(f"🎯 Strategy Selection ({methodology.replace('_', ' ').title()})")

        # Signals section
        with st.expander("📊 Detected Signals", expanded=True):
            if signals:
                self._render_signals_by_category(signals, methodology)
            else:
                st.info("No signals detected yet")

        # Strategy ranking section
        with st.expander("🏆 Strategy Ranking", expanded=True):
            if alternatives:
                self._render_strategy_ranking(alternatives)
            else:
                st.info("No strategy alternatives available")

    def _render_signals_by_category(self, signals: Dict[str, Any], methodology: str):
        """Render signals grouped by category using dynamic discovery.

        Phase 4: Uses namespaced signal prefixes to group dynamically
        instead of hardcoded signal lists.
        """
        # Node-level signals (Phase 2) - per-node metrics
        node_signals = {
            k: v
            for k, v in signals.items()
            if k.startswith("graph.node.") or k.startswith("technique.node.")
        }

        # Graph signals (global state metrics)
        graph_signals = {
            k: v
            for k, v in signals.items()
            if k.startswith("graph.") and not k.startswith("graph.node.")
        }

        # LLM signals (response analysis)
        llm_signals = {
            k: v
            for k, v in signals.items()
            if k.startswith("llm.")
        }

        # Temporal signals (history tracking)
        temporal_signals = {
            k: v
            for k, v in signals.items()
            if k.startswith("temporal.")
        }

        # Meta signals (derived/composite signals)
        meta_signals = {
            k: v
            for k, v in signals.items()
            if k.startswith("meta.")
        }

        # Dynamic layout based on available signal types
        has_signals = [
            ("Node-Level", node_signals),
            ("Graph/State", graph_signals),
            ("Response/LLM", llm_signals),
            ("History", temporal_signals),
            ("Meta", meta_signals),
        ]

        # Filter to only show sections with signals
        active_sections = [(name, sigs) for name, sigs in has_signals if sigs]

        if not active_sections:
            st.info("No signals detected yet")
            return

        # Create columns for available signal types
        num_cols = min(len(active_sections), 3)
        cols = st.columns(num_cols)

        for idx, (section_name, section_signals) in enumerate(active_sections):
            with cols[idx % num_cols]:
                st.markdown(f"**{section_name}**")
                for k, v in section_signals.items():
                    self._render_signal(k, v)

    def _render_signal(self, name: str, value: Any):
        """Render a single signal value."""
        # Format based on type
        if isinstance(value, bool):
            icon = "✓" if value else "✗"
            st.markdown(f"- {name}: {icon}")
        elif isinstance(value, float):
            st.markdown(f"- {name}: `{value:.2f}`")
        elif isinstance(value, int):
            st.markdown(f"- {name}: `{value}`")
        else:
            st.markdown(f"- {name}: {value}")

    def _render_strategy_ranking(self, alternatives: list):
        """Render strategy ranking with scores.

        Handles both dict format (legacy) and tuple format (Phase 3+).
        Dict format: [{"strategy": str, "score": float}, ...]
        Tuple format: [(strategy, score)] or [(strategy, node_id, score)]
        """
        for i, alt in enumerate(alternatives[:5]):
            # Handle both dict (legacy) and tuple (Phase 3+) formats
            if isinstance(alt, dict):
                score = alt.get("score", 0)
                name = alt.get("strategy", "unknown")
            else:
                # Phase 3+ format: tuple[str, float] or tuple[str, str, float]
                if len(alt) == 2:
                    name, score = alt
                elif len(alt) == 3:
                    name, node_id, score = alt  # node_id available but not displayed
                else:
                    continue

            # Highlight selected (first)
            if i == 0:
                st.markdown(f"**→ {name}** `{score:.2f}` ✓")
            else:
                st.markdown(f"  {name} `{score:.2f}`")

            # Progress bar for score
            st.progress(min(max(score, 0.0), 1.0))

    def _render_legacy_scoring(self, api_client, current_session):
        """Render legacy two-tier scoring display."""
        # Load all scoring data
        all_scoring = api_client.get_all_scoring(current_session.id)

        if not all_scoring:
            st.info(
                "No scoring data available yet. Complete some interview turns first."
            )
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
        sorted_candidates = sorted(
            candidates, key=lambda c: c["final_score"], reverse=True
        )

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
                                st.error(
                                    f"❌ {t1['scorer_id']}: **VETO** - {t1['reasoning']}"
                                )
                            else:
                                st.success(f"✓ {t1['scorer_id']}: Pass")

                # Tier 2 scoring breakdown
                if candidate.get("tier2_results"):
                    with st.expander(
                        f"📈 Tier 2: Weighted Scoring (Score: {candidate['final_score']:.2f})"
                    ):
                        # Calculate score contribution
                        total_contribution = sum(
                            t2["contribution"] for t2 in candidate["tier2_results"]
                        )

                        # Show each scorer
                        for t2 in candidate["tier2_results"]:
                            # Progress bar for contribution
                            pct_of_total = (
                                (t2["contribution"] / total_contribution * 100)
                                if total_contribution > 0
                                else 0
                            )

                            cols = st.columns([3, 2, 1])
                            with cols[0]:
                                st.write(f"**{t2['scorer_id']}**")

                            with cols[1]:
                                st.caption(
                                    f"Raw: {t2['raw_score']:.2f} × {t2['weight']:.2f} = {t2['contribution']:.3f}"
                                )

                            with cols[2]:
                                st.caption(f"{pct_of_total:.0f}%")

                            # Reasoning
                            if t2.get("reasoning"):
                                st.caption(t2["reasoning"])

                            # Contribution bar
                            st.progress(
                                t2["contribution"] / 2.0
                            )  # Max contribution is weight × 2.0

                        st.write(
                            f"**Total Score:** 1.0 (base) + Σ(contributions) = {candidate['final_score']:.2f}"
                        )

                # Reasoning trace
                if candidate.get("reasoning"):
                    with st.expander("💭 Reasoning Trace"):
                        st.write(candidate["reasoning"])

                # Tier 1 vetoes
                if candidate.get("tier1_results"):
                    with st.expander("🔍 Tier 1: Hard Constraints (Vetoes)"):
                        for t1 in candidate["tier1_results"]:
                            if t1["is_veto"]:
                                st.error(
                                    f"❌ {t1['scorer_id']}: **VETO** - {t1['reasoning']}"
                                )
                            else:
                                st.success(f"✓ {t1['scorer_id']}: Pass")

                # Tier 2 scoring breakdown
                if candidate.get("tier2_results"):
                    with st.expander(
                        f"📈 Tier 2: Weighted Scoring (Score: {candidate['final_score']:.2f})"
                    ):
                        # Calculate score contribution
                        total_contribution = sum(
                            t2["contribution"] for t2 in candidate["tier2_results"]
                        )

                        # Show each scorer
                        for t2 in candidate["tier2_results"]:
                            # Progress bar for contribution
                            pct_of_total = (
                                (t2["contribution"] / total_contribution * 100)
                                if total_contribution > 0
                                else 0
                            )

                            cols = st.columns([3, 2, 1])
                            with cols[0]:
                                st.write(f"**{t2['scorer_id']}**")

                            with cols[1]:
                                st.caption(
                                    f"Raw: {t2['raw_score']:.2f} × {t2['weight']:.2f} = {t2['contribution']:.3f}"
                                )

                            with cols[2]:
                                st.caption(f"{pct_of_total:.0f}%")

                            # Reasoning
                            if t2.get("reasoning"):
                                st.caption(t2["reasoning"])

                            # Contribution bar
                            st.progress(
                                t2["contribution"] / 2.0
                            )  # Max contribution is weight × 2.0

                        st.write(
                            f"**Total Score:** 1.0 (base) + Σ(contributions) = {candidate['final_score']:.2f}"
                        )

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
