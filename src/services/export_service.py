"""
Export service for converting session data to various formats.

Supports export to:
- JSON: Full session data with all metadata
- Markdown: Human-readable interview summary
- CSV: Spreadsheet-compatible format for analysis
"""

import json
import csv
from io import StringIO
from typing import Any, Dict, List
from datetime import datetime, timezone

import structlog


log = structlog.get_logger(__name__)


def _calculate_phase(turn_number: int) -> str:
    """
    Calculate interview phase based on turn number (deterministic).

    Phase transition rules:
    - exploratory: turns 0 to exploratory.n_turns (exclusive)
    - focused: turns exploratory.n_turns to exploratory+focused.n_turns (exclusive)
    - closing: turns exploratory+focused.n_turns onwards

    Args:
        turn_number: Current turn number (0-indexed)

    Returns:
        Phase string: 'exploratory', 'focused', or 'closing'
    """
    from src.core.config import interview_config

    exploratory_end = interview_config.phases.exploratory.n_turns or 10
    focused_end = exploratory_end + (interview_config.phases.focused.n_turns or 10)

    if turn_number < exploratory_end:
        return "exploratory"
    elif turn_number < focused_end:
        return "focused"
    else:
        return "closing"


class ExportService:
    """
    Service for exporting session data to various formats.

    Usage:
        service = ExportService()
        json_str = await service.export_session(session_id, "json")
        md_str = await service.export_session(session_id, "markdown")
    """

    def __init__(
        self,
        session_repo=None,
        graph_repo=None,
    ):
        """
        Initialize export service.

        Args:
            session_repo: Optional session repository (injected for testing)
            graph_repo: Optional graph repository (injected for testing)
        """
        # Lazy import to avoid circular dependencies
        from src.persistence.repositories.session_repo import SessionRepository
        from src.core.config import settings

        if session_repo is None:
            self.session_repo = SessionRepository(db_path=str(settings.database_path))
        else:
            self.session_repo = session_repo

        # graph_repo must be provided for now (it requires a connection)
        # In production, this would be injected via FastAPI dependency
        self.graph_repo = graph_repo

    async def export_session(
        self,
        session_id: str,
        format: str = "json",
    ) -> str:
        """
        Export session data to specified format.

        Args:
            session_id: Session ID to export
            format: One of "json", "markdown", "csv"

        Returns:
            Exported data as string

        Raises:
            ValueError: If format is not supported
            SessionNotFoundError: If session doesn't exist
        """
        bound_log = log.bind(session_id=session_id, format=format)
        bound_log.info("export_session_started")

        # Validate format first before collecting data
        if format.lower() not in ("json", "markdown", "md", "csv"):
            raise ValueError(f"Unsupported export format: {format}")

        # Gather all session data
        session_data = await self._collect_session_data(session_id)

        # Export to requested format
        if format.lower() in ("json",):
            result = self._export_json(session_data)
        elif format.lower() in ("markdown", "md"):
            result = self._export_markdown(session_data)
        else:  # csv
            result = self._export_csv(session_data)

        bound_log.info(
            "export_session_complete",
            format=format,
            output_length=len(result),
        )

        return result

    async def _collect_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Collect all session data for export.

        Args:
            session_id: Session ID

        Returns:
            Dict with all session data
        """
        # Get session metadata
        session = await self.session_repo.get(session_id)
        if not session:
            from src.core.exceptions import SessionNotFoundError

            raise SessionNotFoundError(f"Session {session_id} not found")

        # Check graph_repo is available
        if self.graph_repo is None:
            raise ValueError("graph_repo is required for export")

        # Get utterances
        utterances = await self.session_repo.get_utterances(session_id)

        # Get graph data
        nodes = await self.graph_repo.get_nodes_by_session(session_id)
        edges = await self.graph_repo.get_edges_by_session(session_id)

        # Get scoring history
        scoring_history = await self.session_repo.get_scoring_history(session_id)

        # Get all qualitative signals for diagnostics
        all_signals = await self.session_repo.get_all_qualitative_signals(session_id)

        return {
            "metadata": {
                "session_id": session.id,
                "concept_id": session.concept_id,
                "methodology": session.methodology,
                "status": session.status,
                "created_at": session.created_at.isoformat()
                if session.created_at
                else None,
                "completed_at": None,  # Session model doesn't have completed_at
                "config": {},  # Session model doesn't have config
                "exported_at": datetime.now(timezone.utc).isoformat(),
            },
            "utterances": [
                {
                    "id": u.id,
                    "turn_number": u.turn_number,
                    "speaker": u.speaker,
                    "text": u.text,
                    "phase": _calculate_phase(u.turn_number),
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in utterances
            ],
            "graph": {
                "nodes": [
                    {
                        "id": n.id,
                        "label": n.label,
                        "node_type": n.node_type,
                        "confidence": n.confidence,
                        "properties": n.properties,
                        "source_utterance_ids": n.source_utterance_ids,
                        "recorded_at": n.recorded_at.isoformat()
                        if n.recorded_at
                        else None,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "id": e.id,
                        "source_node_id": e.source_node_id,
                        "target_node_id": e.target_node_id,
                        "edge_type": e.edge_type,
                        "confidence": e.confidence,
                        "properties": e.properties,
                        "source_utterance_ids": e.source_utterance_ids,
                        "recorded_at": e.recorded_at.isoformat()
                        if e.recorded_at
                        else None,
                    }
                    for e in edges
                ],
            },
            "scoring_history": scoring_history,
            "diagnostics": {
                "scoring_history": scoring_history,  # Already fetched above
                "llm_signals": {
                    f"turn_{turn}": signals
                    for turn, signals in sorted(all_signals.items())
                },
            },
        }

    def _export_json(self, data: Dict[str, Any]) -> str:
        """Export to JSON format."""
        return json.dumps(data, indent=2, default=str)

    def _export_markdown(self, data: Dict[str, Any]) -> str:
        """Export to human-readable Markdown format."""
        lines = []

        # Header
        meta = data["metadata"]
        lines.append("# Interview Session Export")
        lines.append("")
        lines.append(f"**Session ID:** `{meta['session_id']}`")
        lines.append(f"**Concept:** {meta['concept_id']}")
        lines.append(f"**Methodology:** {meta['methodology']}")
        lines.append(f"**Status:** {meta['status']}")
        lines.append(f"**Created:** {meta.get('created_at', 'N/A')}")
        if meta.get("completed_at"):
            lines.append(f"**Completed:** {meta['completed_at']}")
        lines.append("")

        # Statistics
        utterances = data["utterances"]
        nodes = data["graph"]["nodes"]
        edges = data["graph"]["edges"]

        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Turns:** {len(utterances)}")
        lines.append(f"- **Concepts Extracted:** {len(nodes)}")
        lines.append(f"- **Relationships:** {len(edges)}")
        lines.append("")

        # Conversation
        lines.append("## Conversation")
        lines.append("")
        for utt in utterances:
            speaker = utt["speaker"]
            text = utt["text"]
            emoji = "👤" if speaker == "user" else "🤖"
            lines.append(f"### {emoji} {speaker.title()} (Turn {utt['turn_number']})")
            lines.append("")
            lines.append(text)
            lines.append("")

        # Knowledge Graph
        lines.append("## Knowledge Graph")
        lines.append("")

        # Group nodes by type
        nodes_by_type: Dict[str, List[Dict]] = {}
        for node in nodes:
            node_type = node["node_type"]
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append(node)

        for node_type, type_nodes in sorted(nodes_by_type.items()):
            lines.append(
                f"### {node_type.replace('_', ' ').title()} ({len(type_nodes)})"
            )
            lines.append("")
            for node in type_nodes:
                label = node["label"]
                confidence = node["confidence"]
                lines.append(f"- **{label}** (confidence: {confidence:.2f})")
            lines.append("")

        # Relationships
        if edges:
            lines.append("### Relationships")
            lines.append("")

            # Build node label lookup
            node_labels = {n["id"]: n["label"] for n in nodes}

            for edge in edges:
                source_label = node_labels.get(
                    edge["source_node_id"], edge["source_node_id"]
                )
                target_label = node_labels.get(
                    edge["target_node_id"], edge["target_node_id"]
                )
                edge_type = edge["edge_type"]
                confidence = edge["confidence"]

                lines.append(
                    f"- {source_label} → **{edge_type}** → {target_label} (confidence: {confidence:.2f})"
                )
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Exported on {meta['exported_at']}*")
        lines.append("")

        return "\n".join(lines)

    def _export_csv(self, data: Dict[str, Any]) -> str:
        """Export to CSV format with multiple sections."""
        output = StringIO()

        # Nodes section
        nodes = data["graph"]["nodes"]
        output.write("## NODES\n")
        if nodes:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "label",
                    "node_type",
                    "confidence",
                    "source_utterance_ids",
                ],
            )
            writer.writeheader()
            for node in nodes:
                writer.writerow(
                    {
                        "id": node["id"],
                        "label": node["label"],
                        "node_type": node["node_type"],
                        "confidence": node["confidence"],
                        "source_utterance_ids": json.dumps(
                            node["source_utterance_ids"]
                        ),
                    }
                )
        output.write("\n\n")

        # Edges section
        edges = data["graph"]["edges"]
        output.write("## EDGES\n")
        if edges:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "source_node_id",
                    "target_node_id",
                    "edge_type",
                    "confidence",
                ],
            )
            writer.writeheader()
            for edge in edges:
                writer.writerow(
                    {
                        "id": edge["id"],
                        "source_node_id": edge["source_node_id"],
                        "target_node_id": edge["target_node_id"],
                        "edge_type": edge["edge_type"],
                        "confidence": edge["confidence"],
                    }
                )
        output.write("\n\n")

        # Utterances section
        utterances = data["utterances"]
        output.write("## UTTERANCES\n")
        if utterances:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "turn_number",
                    "speaker",
                    "text",
                    "phase",
                    "created_at",
                ],
            )
            writer.writeheader()
            for utt in utterances:
                writer.writerow(
                    {
                        "id": utt["id"],
                        "turn_number": utt["turn_number"],
                        "speaker": utt["speaker"],
                        "text": utt["text"],
                        "phase": utt.get("phase", ""),
                        "created_at": utt.get("created_at", ""),
                    }
                )

        return output.getvalue()
