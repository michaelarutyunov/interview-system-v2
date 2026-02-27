"""
Metrics panel component for Streamlit demo UI.

Displays interview statistics, scoring information, and diagnostics.
Uses Streamlit's metrics and visualization components.
"""

from typing import Dict, Any, Optional
import streamlit as st

import plotly.graph_objects as go


class MetricsPanel:
    """
    Displays interview metrics and diagnostics.

    Shows:
    - Coverage progress with visual bar
    - Turn count
    - Scoring breakdown
    - Strategy selection with reasoning
    - Graph statistics
    """

    def __init__(self):
        """Initialize metrics panel."""
        self.coverage_emoji = ["⬜", "🟩"]  # Empty, Filled

    def render(self, status_data: Dict[str, Any], graph_data: Optional[Dict] = None):
        """
        Render the complete metrics panel.

        Args:
            status_data: Session status from /sessions/{id}/status
            graph_data: Optional graph data from /sessions/{id}/graph
        """
        st.subheader("📊 Interview Metrics")

        # Main metrics row
        col1, col2, col3 = st.columns(3)

        with col1:
            self._render_turn_count(status_data)

        with col2:
            self._render_coverage(status_data)

        with col3:
            self._render_status(status_data)

        st.divider()

        # Scoring breakdown
        self._render_scoring(status_data)

        # Strategy info
        self._render_strategy(status_data)

        # Graph stats
        if graph_data:
            self._render_graph_stats(graph_data)

    def _render_turn_count(self, status_data: Dict[str, Any]):
        """Render turn count metric."""
        turn_number = status_data.get("turn_number", 0)
        max_turns = status_data.get("max_turns", 20)

        st.metric(
            label="Turns",
            value=f"{turn_number} / {max_turns}",
            delta=None,
        )

        # Progress bar (clamp to [0, 1] to handle edge case where turn_number exceeds max_turns)
        if max_turns > 0:
            progress = min(turn_number / max_turns, 1.0)
            st.progress(progress)

    def _render_coverage(self, status_data: Dict[str, Any]):
        """Render coverage metric with visual bar."""
        coverage = status_data.get("coverage", 0.0)
        target = status_data.get("target_coverage", 0.8)

        # Determine color based on achievement
        if coverage >= target:
            delta_color = "normal"
        else:
            delta_color = "inverse"

        st.metric(
            label="Coverage",
            value=f"{coverage * 100:.1f}%",
            delta=f"Target: {target * 100:.0f}%",
            delta_color=delta_color,
        )

        # Visual coverage bar (10 segments)
        filled = int(coverage * 10)
        bar = "".join(
            [self.coverage_emoji[1]] * filled + [self.coverage_emoji[0]] * (10 - filled)
        )
        st.markdown(
            f"<p style='font-size: 24px; letter-spacing: 2px;'>{bar}</p>",
            unsafe_allow_html=True,
        )

    def _render_status(self, status_data: Dict[str, Any]):
        """Render session status."""
        session_status = status_data.get("status", "unknown")
        should_continue = status_data.get("should_continue", True)

        # Status indicator
        status_emoji = {
            "active": "🔄",
            "completed": "✅",
            "coverage_met": "🎯",
            "max_turns_reached": "📊",
            "saturated": "🔒",
        }.get(session_status, "❓")

        st.metric(
            label="Status",
            value=f"{status_emoji} {session_status.replace('_', ' ').title()}",
        )

        if not should_continue and session_status == "active":
            st.caption("Interview should end soon")

    def _render_scoring(self, status_data: Dict[str, Any]):
        """Render scoring breakdown.

        Note: Legacy two-tier scoring gauges removed in Phase 6.
        This now shows methodology-specific signals if available.
        """
        # Phase 4 methodology-centric signals
        signals = status_data.get("signals", {})

        if not signals:
            st.info("No signal data available yet.")
            return

        st.write("**Current Signals:**")

        # Show top signals dynamically (don't hardcode)
        signal_items = list(signals.items())[:10]
        for key, value in signal_items:
            if isinstance(value, bool):
                icon = "✓" if value else "✗"
                st.markdown(f"- **{key}**: {icon}")
            elif isinstance(value, float):
                st.markdown(f"- **{key}**: `{value:.2f}`")
            elif isinstance(value, int):
                st.markdown(f"- **{key}**: `{value}`")
            else:
                st.markdown(f"- **{key}**: {value}")

        if len(signals) > 10:
            st.caption(f"... and {len(signals) - 10} more signals")

    def _render_strategy(self, status_data: Dict[str, Any]):
        """Render strategy selection info."""
        strategy = status_data.get("strategy_selected", "unknown")
        reasoning = status_data.get("strategy_reasoning", "")

        st.write("**Current Strategy:**")

        # Phase 4 strategy descriptions (methodology-centric architecture)
        strategy_descriptions = {
            # MEC strategies
            "deepen": "🔍 Deepen - Build depth using laddering technique",
            "clarify": "🔎 Clarify - Probe for relationships and clarity",
            "explore": "🔍 Explore - Expand on recent topics",
            "reflect": "🤔 Reflect - Validate understanding and confirm",
            "revitalize": "⚡ Revitalize - Re-engage when fatigued",
            # JTBD strategies (for reference)
            "explore_situation": "📍 Explore Situation - Understand context",
            "probe_alternatives": "🔀 Probe Alternatives - Find other options",
            "dig_motivation": "💎 Dig Motivation - Uncover drivers",
            "validate_outcome": "✓ Validate Outcome - Confirm goals",
            "uncover_obstacles": "🚧 Uncover Obstacles - Find barriers",
            # Legacy (for backward compatibility)
            "broaden": "🌐 Broaden - Find new topic branches (legacy)",
            "cover_element": "🎯 Cover - Introduce unexplored elements (legacy)",
            "closing": "✅ Closing - Wrap up the interview",
        }

        st.info(strategy_descriptions.get(strategy, f"Strategy: {strategy}"))

        if reasoning:
            with st.expander("See strategy reasoning"):
                st.write(reasoning)

    def _render_graph_stats(self, graph_data: Dict[str, Any]):
        """Render graph statistics."""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        st.write("**Knowledge Graph:**")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nodes", len(nodes))
        with col2:
            st.metric("Edges", len(edges))

        # Node type distribution
        if nodes:
            node_types = {}
            for node in nodes:
                node_type = node.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

            if node_types:
                st.write("**Node Types:**")
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(node_types.keys()),
                            values=list(node_types.values()),
                            hole=0.3,
                        )
                    ]
                )
                fig.update_layout(
                    height=250,
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)


def render_methodology_metrics(
    methodology_name: str,
    graph_data: Dict[str, Any],
    status_data: Optional[Dict[str, Any]] = None,
):
    """
    Render methodology-specific metrics.

    Args:
        methodology_name: Name of the methodology (e.g., "means_end_chain", "jobs_to_be_done")
        graph_data: Graph state with nodes and edges
        status_data: Optional status data for additional metrics
    """
    st.subheader(f"📈 {methodology_name.replace('_', ' ').title()} Metrics")

    if methodology_name == "means_end_chain":
        _render_mec_metrics(graph_data)
    elif methodology_name == "jobs_to_be_done":
        _render_jtbd_metrics(graph_data)
    else:
        st.info(f"No custom metrics for {methodology_name}")


def _render_mec_metrics(graph_data: Dict[str, Any]):
    """Render MEC-specific metrics."""
    nodes = graph_data.get("nodes", [])

    # Count by type
    type_counts = {}
    for node in nodes:
        t = node.get("node_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Attributes", type_counts.get("attribute", 0))
        st.metric(
            "Functional Consequences", type_counts.get("functional_consequence", 0)
        )
        st.metric(
            "Psychosocial Consequences", type_counts.get("psychosocial_consequence", 0)
        )

    with col2:
        st.metric("Instrumental Values", type_counts.get("instrumental_value", 0))
        st.metric("Terminal Values", type_counts.get("terminal_value", 0))

        # Chain completeness
        has_attr = type_counts.get("attribute", 0) > 0
        has_cons = (
            type_counts.get("functional_consequence", 0)
            + type_counts.get("psychosocial_consequence", 0)
        ) > 0
        has_val = (
            type_counts.get("instrumental_value", 0)
            + type_counts.get("terminal_value", 0)
        ) > 0

        completeness = (has_attr + has_cons + has_val) / 3
        st.metric("Chain Completeness", f"{completeness:.0%}")


def _render_jtbd_metrics(graph_data: Dict[str, Any]):
    """Render JTBD-specific metrics."""
    nodes = graph_data.get("nodes", [])

    # Dimension coverage (simplified)
    dimensions = {
        "Situation": ["context", "trigger"],
        "Motivation": ["motivation", "desired_outcome"],
        "Alternatives": ["alternative", "competing_solution"],
        "Obstacles": ["obstacle", "barrier"],
        "Outcome": ["outcome", "benefit"],
    }

    coverage = {}
    for dim, types in dimensions.items():
        count = sum(1 for n in nodes if n.get("node_type") in types)
        coverage[dim] = min(count / 2, 1.0)  # 2 nodes = 100% coverage

    for dim, cov in coverage.items():
        st.progress(cov, text=f"{dim}: {cov:.0%}")


def render_turn_diagnostics(turn_result: Dict[str, Any]):
    """
    Render diagnostics for a single turn.

    Args:
        turn_result: Turn result from submit_turn API call
    """
    with st.expander("🔍 Turn Diagnostics"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Extraction:**")
            extracted = turn_result.get("extracted", {})
            st.write(f"- Concepts: {len(extracted.get('concepts', []))}")
            st.write(f"- Relationships: {len(extracted.get('relationships', []))}")

        with col2:
            st.write("**Timing:**")
            latency = turn_result.get("latency_ms", 0)
            st.write(f"- Latency: {latency:.0f}ms")

        # Show extracted concepts
        extracted = turn_result.get("extracted", {})
        concepts = extracted.get("concepts", [])
        if concepts:
            st.write("**Extracted Concepts:**")
            for concept in concepts[:5]:  # Show first 5
                st.write(
                    f"- {concept.get('text', 'N/A')} ({concept.get('node_type', 'N/A')})"
                )

            if len(concepts) > 5:
                st.caption(f"... and {len(concepts) - 5} more")


def render_coverage_details(coverage_data: Dict[str, Any]):
    """
    Render detailed coverage information.

    Args:
        coverage_data: Coverage data from API
    """
    with st.expander("📋 Coverage Details"):
        elements = coverage_data.get("elements", [])

        if not elements:
            st.info("No element coverage data available.")
            return

        # Group by status
        covered = [e for e in elements if e.get("covered", False)]
        uncovered = [e for e in elements if not e.get("covered", False)]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Covered", len(covered))
            if covered:
                for elem in covered[:5]:
                    st.write(f"✅ {elem.get('label', 'N/A')}")

        with col2:
            st.metric("Remaining", len(uncovered))
            if uncovered:
                for elem in uncovered[:5]:
                    st.write(f"⬜ {elem.get('label', 'N/A')}")
