"""
Graph visualization component for Streamlit demo UI.

Displays the knowledge graph using Plotly for interactive visualization.
Supports node filtering, layout algorithms, and 2D/3D views.
"""

from typing import Optional, List, Dict, Any
import streamlit as st

import networkx as nx
import plotly.graph_objects as go


class GraphVisualizer:
    """
    Knowledge graph visualization using Plotly and NetworkX.

    Features:
    - Interactive node/edge hover information
    - Color-coded node types
    - Multiple layout algorithms
    - Node type filtering
    - 2D and 3D views
    """

    # Node type colors (MEC methodology)
    NODE_COLORS = {
        "attribute": "#FF6B6B",  # Red
        "functional_consequence": "#4ECDC4",  # Teal
        "psychosocial_consequence": "#95E1D3",  # Mint
        "instrumental_value": "#FFE66D",  # Yellow
        "terminal_value": "#6C5CE7",  # Purple
        "unknown": "#DFE6E9",  # Gray
    }

    NODE_SIZE_DEFAULT = 30
    EDGE_WIDTH_DEFAULT = 2

    def __init__(self):
        """Initialize graph visualizer."""
        self.layout_algorithms = {
            "Spring": nx.spring_layout,
            "Kamada-Kawai": nx.kamada_kawai_layout,
            "Circular": nx.circular_layout,
            "Random": nx.random_layout,
            "Spectral": nx.spectral_layout,
        }

    def render_controls(self) -> Dict[str, Any]:
        """
        Render graph control sidebar.

        Returns:
            Dict with selected options:
                - layout: str (layout algorithm)
                - dimensions: str ("2D" or "3D")
                - show_labels: bool
                - node_filter: list of str (node types to show)
        """
        st.sidebar.subheader("🕸️ Graph Controls")

        # Layout algorithm
        layout = st.sidebar.selectbox(
            "Layout Algorithm",
            options=list(self.layout_algorithms.keys()),
            index=0,
        )

        # Dimensions
        dimensions = st.sidebar.radio(
            "View",
            options=["2D", "3D"],
            horizontal=True,
        )

        # Show labels
        show_labels = st.sidebar.checkbox("Show Node Labels", value=True)

        # Node type filter
        all_node_types = list(self.NODE_COLORS.keys())
        node_filter = st.sidebar.multiselect(
            "Filter by Node Type",
            options=all_node_types,
            default=all_node_types,
        )

        return {
            "layout": layout,
            "dimensions": dimensions,
            "show_labels": show_labels,
            "node_filter": node_filter,
        }

    def render(
        self,
        graph_data: Dict[str, Any],
        controls: Dict[str, Any],
    ) -> Optional[go.Figure]:
        """
        Render the knowledge graph visualization.

        Args:
            graph_data: Graph data from API with 'nodes' and 'edges'
            controls: Control options from render_controls()

        Returns:
            Plotly figure object, or None if no data
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            st.info(
                "📊 No nodes to display yet. Start the interview to extract concepts."
            )
            return None

        # Filter nodes by type
        if controls["node_filter"]:
            nodes = [n for n in nodes if n.get("node_type") in controls["node_filter"]]
            node_ids = {n["id"] for n in nodes}
            edges = [
                e
                for e in edges
                if e.get("source_node_id") in node_ids
                and e.get("target_node_id") in node_ids
            ]

        # Build NetworkX graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node["id"], **node)

        for edge in edges:
            G.add_edge(
                edge["source_node_id"],
                edge["target_node_id"],
                edge_type=edge.get("edge_type", "leads_to"),
                **edge,
            )

        # Compute layout
        layout_func = self.layout_algorithms[controls["layout"]]
        pos = layout_func(G)

        # Create Plotly figure
        if controls["dimensions"] == "3D":
            fig = self._create_3d_plot(G, pos, nodes, edges, controls)
        else:
            fig = self._create_2d_plot(G, pos, nodes, edges, controls)

        # Update layout
        fig.update_layout(
            title=f"Knowledge Graph ({len(nodes)} nodes, {len(edges)} edges)",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=40),
            height=500,
        )

        return fig

    def _create_2d_plot(
        self,
        G: nx.Graph,
        pos: Dict[str, tuple],
        nodes: List[Dict],
        edges: List[Dict],
        controls: Dict,
    ) -> go.Figure:
        """Create 2D plotly figure."""
        fig = go.Figure()

        # Prepare edge traces
        edge_x = []
        edge_y = []

        for edge in edges:
            x0, y0 = pos[edge["source_node_id"]]
            x1, y1 = pos[edge["target_node_id"]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                line=dict(width=self.EDGE_WIDTH_DEFAULT, color="#888"),
                hoverinfo="none",
                mode="lines",
                name="edges",
            )
        )

        # Prepare node traces
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        node_sizes = []
        hover_texts = []

        for node in nodes:
            node_id = node["id"]
            x, y = pos[node_id]
            node_x.append(x)
            node_y.append(y)

            # Node color by type
            node_type = node.get("node_type", "unknown")
            node_colors.append(self.NODE_COLORS.get(node_type, "#888888"))

            # Node size by confidence
            confidence = node.get("confidence", 0.8)
            node_sizes.append(self.NODE_SIZE_DEFAULT * (0.5 + confidence))

            # Labels
            if controls["show_labels"]:
                node_text.append(node.get("label", node_id))

            # Hover text
            hover = f"<b>{node.get('label', node_id)}</b><br>"
            hover += f"Type: {node_type}<br>"
            hover += f"Confidence: {confidence:.2f}"
            hover_texts.append(hover)

        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text" if controls["show_labels"] else "markers",
                marker=dict(
                    size=node_sizes,
                    color=node_colors,
                    line=dict(width=2, color="white"),
                ),
                text=node_text if controls["show_labels"] else None,
                textposition="middle center",
                hovertext=hover_texts,
                hoverinfo="text",
                name="nodes",
            )
        )

        return fig

    def _create_3d_plot(
        self,
        G: nx.Graph,
        pos: Dict[str, tuple],
        nodes: List[Dict],
        edges: List[Dict],
        controls: Dict,
    ) -> go.Figure:
        """Create 3D plotly figure."""
        # Convert 2D positions to 3D (add z=0 for all)
        pos_3d = {node: (x, y, 0) for node, (x, y) in pos.items()}

        fig = go.Figure()

        # Edge traces
        edge_x = []
        edge_y = []
        edge_z = []

        for edge in edges:
            x0, y0, z0 = pos_3d[edge["source_node_id"]]
            x1, y1, z1 = pos_3d[edge["target_node_id"]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_z.extend([z0, z1, None])

        fig.add_trace(
            go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode="lines",
                line=dict(width=self.EDGE_WIDTH_DEFAULT, color="#888"),
                hoverinfo="none",
                name="edges",
            )
        )

        # Node traces
        node_x = []
        node_y = []
        node_z = []
        node_colors = []
        node_sizes = []
        hover_texts = []

        for node in nodes:
            node_id = node["id"]
            x, y, z = pos_3d[node_id]
            node_x.append(x)
            node_y.append(y)
            node_z.append(z)

            node_type = node.get("node_type", "unknown")
            node_colors.append(self.NODE_COLORS.get(node_type, "#888888"))

            confidence = node.get("confidence", 0.8)
            node_sizes.append(self.NODE_SIZE_DEFAULT * (0.5 + confidence) * 2)

            hover = f"<b>{node.get('label', node_id)}</b><br>"
            hover += f"Type: {node_type}<br>"
            hover += f"Confidence: {confidence:.2f}"
            hover_texts.append(hover)

        fig.add_trace(
            go.Scatter3d(
                x=node_x,
                y=node_y,
                z=node_z,
                mode="markers",
                marker=dict(
                    size=node_sizes,
                    color=node_colors,
                    line=dict(width=1, color="white"),
                ),
                hovertext=hover_texts,
                hoverinfo="text",
                name="nodes",
            )
        )

        fig.update_layout(
            scene=dict(
                xaxis=dict(showgrid=False, showticklabels=False, visible=False),
                yaxis=dict(showgrid=False, showticklabels=False, visible=False),
                zaxis=dict(showgrid=False, showticklabels=False, visible=False),
            )
        )

        return fig


def render_graph_stats(graph_data: Dict[str, Any]):
    """
    Render graph statistics in sidebar.

    Args:
        graph_data: Graph data from API
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    st.sidebar.subheader("📈 Graph Stats")

    # Count nodes by type
    node_types = {}
    for node in nodes:
        node_type = node.get("node_type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    st.sidebar.metric("Total Nodes", len(nodes))
    st.sidebar.metric("Total Edges", len(edges))

    if node_types:
        st.sidebar.write("**Nodes by Type:**")
        for node_type, count in sorted(node_types.items()):
            st.sidebar.write(f"• {node_type}: {count}")
