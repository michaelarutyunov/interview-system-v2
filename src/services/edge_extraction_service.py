"""Edge extraction service for Stage 4.5B.

Provides focus-derived utterance assembly for edge extraction input construction.
The helper assembles the relevant utterance set from focus node + direct neighbours,
excluding ungrounded nodes (those with source_utterance_ids == ["unknown"]).
"""

from typing import List

import structlog

from src.domain.models.utterance import Utterance

log = structlog.get_logger(__name__)

# Sentinel value used in production data when a node has no known source utterance.
# Nodes with this value cannot provide evidence-grounded context for edge extraction
# and must be excluded from the candidate utterance set (per D6).
_UNKNOWN_SENTINEL = "unknown"


async def assemble_focus_derived_utterances(
    graph_repo,
    utterance_repo,
    focus_node_id: str,
    current_turn: int,
    previous_question_utterance_id: str,
) -> List[Utterance]:
    """Assemble the utterance set for edge extraction from focus node context.

    Collects source utterances from the focus node and its direct graph neighbours,
    adds the current turn's user utterance and the previous interviewer question,
    and returns them deduplicated via UtteranceRepository.get_by_ids.

    Per D6: nodes with source_utterance_ids == ["unknown"] are excluded from the
    candidate set because they cannot provide evidence-grounded context.

    Args:
        graph_repo: GraphRepository instance for node and edge queries.
        utterance_repo: UtteranceRepository instance for utterance retrieval.
        focus_node_id: The strategy-selected focus node ID.
        current_turn: Current turn number (used to find the current user utterance).
        previous_question_utterance_id: ID of the previous interviewer question
            utterance (for frame contamination detection surface).

    Returns:
        List of Utterance objects, deduplicated by ID, in stable order.
    """
    # 1. Get focus node
    focus_node = await graph_repo.get_node(focus_node_id)
    if focus_node is None:
        log.warning(
            "focus_node_not_found",
            focus_node_id=focus_node_id,
        )
        return []

    session_id = focus_node.session_id

    # 2. Find direct neighbours via edge traversal
    all_edges = await graph_repo.get_edges_by_session(session_id)
    neighbor_ids: List[str] = []
    for edge in all_edges:
        if edge.source_node_id == focus_node_id:
            neighbor_ids.append(edge.target_node_id)
        elif edge.target_node_id == focus_node_id:
            neighbor_ids.append(edge.source_node_id)

    # 3. Collect utterance IDs from focus node + neighbours
    utterance_ids: List[str] = []

    def _collect_from_node(node) -> None:
        """Collect source_utterance_ids from a node, excluding 'unknown' sentinel."""
        if node is None:
            return
        source_ids = getattr(node, "source_utterance_ids", []) or []
        for uid in source_ids:
            if uid != _UNKNOWN_SENTINEL and uid not in utterance_ids:
                utterance_ids.append(uid)

    _collect_from_node(focus_node)

    for nid in neighbor_ids:
        node = await graph_repo.get_node(nid)
        _collect_from_node(node)

    # 4. Add current turn's user utterance
    current_turn_utterances = await utterance_repo.get_by_turn(session_id, current_turn)
    for utt in current_turn_utterances:
        if utt.speaker == "user" and utt.id not in utterance_ids:
            utterance_ids.append(utt.id)
            break  # Only need one user utterance per turn

    # 5. Add previous interviewer question utterance
    if (
        previous_question_utterance_id
        and previous_question_utterance_id not in utterance_ids
    ):
        utterance_ids.append(previous_question_utterance_id)

    # 6. Fetch and return
    if not utterance_ids:
        return []

    return await utterance_repo.get_by_ids(utterance_ids)
