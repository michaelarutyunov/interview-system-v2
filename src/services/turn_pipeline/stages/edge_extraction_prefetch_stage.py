"""Stage 4.5B-prefetch: Fire edge extraction LLM call asynchronously.

Creates an asyncio.Task for the edge extraction call and stores it on
PipelineContext._edge_extraction_task. The task is NOT awaited here —
EdgeExtractionBridgeStage (Stage 4.6) awaits it after graph state is ready.

Fires BEFORE SlotDiscoveryStage (4.5) so the edge extraction Haiku call
overlaps with SlotDiscovery's ~3s Haiku call. Both depend only on Stage 4.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog  # type: ignore[import-untyped]

from ..base import TurnStage
from src.llm.client import get_llm_client
from src.llm.prompts.edge_extraction import (
    format_candidate_node_for_edge_extraction,
    format_candidate_pair_for_edge_extraction,
    format_existing_edge_for_prompt,
    format_utterance_for_edge_extraction,
    get_edge_extraction_system_prompt,
    get_edge_extraction_user_prompt,
    parse_edge_extraction_response,
)

if TYPE_CHECKING:
    from ..context import PipelineContext

log = structlog.get_logger(__name__)


class EdgeExtractionPrefetchStage(TurnStage):
    """Fire edge extraction LLM call as asyncio.Task after Stage 4.

    Dependencies (available after Stage 4 / GraphUpdateStage):
    - graph_update_output.concept_to_node_id: CURRENT nodes from this turn
    - _evolving_node_tracker.previous_focus: FOCUS surface UUID from previous turn
    - graph_repo.get_neighbours(): NEIGHBOR nodes
    - graph_repo.get_nodes_by_turn(): RECENT nodes

    When the feature flag is OFF, this stage is a no-op.
    """

    def __init__(self, graph_repo, utterance_repo):
        self._graph_repo = graph_repo
        self._utterance_repo = utterance_repo

    async def process(self, context: "PipelineContext") -> "PipelineContext":

        # Stage 4 must have completed (D3: runs after GraphUpdateStage)
        if context.graph_update_output is None:
            log.warning(
                "edge_extraction_prefetch_skipped_no_graph_update",
                session_id=context.session_id,
            )
            context._edge_extraction_task = None
            return context

        session_id = context.session_id
        turn_number = context.turn_number

        # Assemble candidate nodes with category tags
        candidate_nodes, focus_node_id = await self._assemble_candidate_nodes(
            context, session_id, turn_number
        )

        if not candidate_nodes:
            log.debug(
                "edge_extraction_prefetch_no_candidates",
                session_id=session_id,
            )
            context._edge_extraction_task = None
            return context

        # Full conversation history — gives Haiku the connective tissue it needs
        # to find cross-turn causal relationships (e.g. L0 trigger → L1 pain point
        # stated across two consecutive turns). Limit 30 covers a full 15-turn
        # interview (2 utterances/turn) without approaching token limits.
        utterances = await self._utterance_repo.get_recent(session_id, limit=30)

        # Build prompt sections
        utterances_text = self._build_utterances_section(utterances)
        candidate_nodes_text = self._build_candidate_section(candidate_nodes)
        # Generate pairs in priority order (FOCUS > NEIGHBOR > CURRENT > RECENT),
        # capped at 40 to keep LLM call within the 30s timeout budget.
        candidate_pairs_text = self._build_candidate_pairs_section(candidate_nodes)
        existing_edges_text = ""
        if focus_node_id:
            existing_edges_text = await self._build_existing_edges_section(
                session_id, focus_node_id
            )

        system_prompt = get_edge_extraction_system_prompt(context.methodology)
        user_prompt = get_edge_extraction_user_prompt(
            utterances_text=utterances_text,
            candidate_nodes_text=candidate_nodes_text,
            candidate_pairs_text=candidate_pairs_text,
            existing_edges_text=existing_edges_text,
        )

        # Get LLM client
        try:
            llm_client = get_llm_client("edge_extraction")
        except Exception as e:
            log.error(
                "edge_extraction_client_setup_failed",
                session_id=session_id,
                error=str(e),
            )
            context._edge_extraction_task = None
            return context

        candidate_count = len(candidate_nodes)
        # Actual pair count after priority ordering and cap — matches what the LLM sees.
        pair_count = candidate_pairs_text.count("pair=") if candidate_pairs_text else 0

        # Fire as asyncio.Task — not awaited here.
        # Runs concurrently with SlotDiscoveryStage (4.5) which runs next.
        async def _run_prefetched():
            structlog.contextvars.bind_contextvars(call_concurrency="prefetch")
            try:
                response = await llm_client.complete(
                    prompt=user_prompt,
                    system=system_prompt,
                )
                return parse_edge_extraction_response(response.content)
            finally:
                structlog.contextvars.unbind_contextvars("call_concurrency")

        context._edge_extraction_task = asyncio.create_task(_run_prefetched())

        log.info(
            "edge_extraction_prefetch_fired",
            session_id=session_id,
            methodology=context.methodology,
            candidate_count=candidate_count,
            pair_count=pair_count,
            utterance_count=len(utterances),
            has_focus=focus_node_id is not None,
            prompt_length=len(user_prompt),
            system_prompt_length=len(system_prompt),
        )

        return context

    async def _assemble_candidate_nodes(
        self, context: "PipelineContext", session_id: str, turn_number: int
    ) -> tuple[list[dict], str | None]:
        """Build the deduplicated candidate node list with category tags.

        Returns (candidate_nodes_list, focus_node_id).
        Each candidate is a dict with: tag, node_id, label, node_type, turn.
        """
        seen_ids: set[str] = set()
        candidates: list[dict] = []
        focus_node_id: str | None = None

        tracker = context._evolving_node_tracker

        # 1. FOCUS: previous turn's selected focus node, looked up by surface UUID.
        focus_node = None
        if tracker and tracker.previous_focus:
            surface_id = tracker.previous_focus
            focus_node = await self._graph_repo.get_node(surface_id)
            if focus_node:
                focus_node_id = focus_node.id
                candidates.append(
                    {
                        "tag": "FOCUS",
                        "node_id": focus_node.id,
                        "label": focus_node.label,
                        "node_type": focus_node.node_type,
                        "turn": None,
                    }
                )
                seen_ids.add(focus_node.id)

        # 2. CURRENT: nodes from this turn's extraction (via concept_to_node_id)
        # graph_update_output is guaranteed non-None by caller guard
        graph_update_output = context.graph_update_output
        assert graph_update_output is not None
        for node_id in graph_update_output.concept_to_node_id.values():
            if node_id in seen_ids:
                continue
            node = await self._graph_repo.get_node(node_id)
            if node is None:
                continue
            candidates.append(
                {
                    "tag": "CURRENT",
                    "node_id": node.id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "turn": turn_number,
                }
            )
            seen_ids.add(node.id)

        # 3. NEIGHBOR: graph neighbours of FOCUS
        if focus_node_id:
            neighbour_ids = await self._graph_repo.get_neighbours(focus_node_id)
            for nid in neighbour_ids:
                if nid in seen_ids:
                    continue
                node = await self._graph_repo.get_node(nid)
                if node is None:
                    continue
                candidates.append(
                    {
                        "tag": "NEIGHBOR",
                        "node_id": node.id,
                        "label": node.label,
                        "node_type": node.node_type,
                        "turn": None,
                    }
                )
                seen_ids.add(node.id)

        # 4. RECENT: nodes from previous turn (cross-turn context)
        if turn_number > 0:
            recent_nodes = await self._graph_repo.get_nodes_by_turn(
                session_id, turn_number - 1
            )
            for node in recent_nodes:
                if node.id in seen_ids:
                    continue
                candidates.append(
                    {
                        "tag": "RECENT",
                        "node_id": node.id,
                        "label": node.label,
                        "node_type": node.node_type,
                        "turn": turn_number - 1,
                    }
                )
                seen_ids.add(node.id)

        return candidates, focus_node_id

    def _build_utterances_section(self, utterances) -> str:
        """Format utterances with their node spans for the prompt."""
        if not utterances:
            return ""

        parts: list[str] = ["## Utterances:"]
        for utt in utterances:
            # For v1, no per-utterance node back-resolution.
            # Render each utterance with its text and ID only.
            parts.append(
                format_utterance_for_edge_extraction(
                    utterance_id=utt.id,
                    text=utt.text,
                    nodes=[],
                )
            )
        return "\n\n".join(parts)

    def _build_candidate_section(self, candidates: list[dict]) -> str:
        """Format candidate nodes with category tags for the prompt."""
        if not candidates:
            return ""

        lines: list[str] = ["## Candidate Nodes:"]
        for c in candidates:
            lines.append(
                format_candidate_node_for_edge_extraction(
                    tag=c["tag"],
                    node_id=c["node_id"],
                    label=c["label"],
                    node_type=c["node_type"],
                    turn=c.get("turn"),
                )
            )
        return "\n".join(lines)

    @staticmethod
    def _build_candidate_pairs_section(
        candidates: list[dict], max_pairs: int = 40
    ) -> str:
        """Format candidate pairs where at least one endpoint is a CURRENT node.

        Edges between two pre-existing nodes (FOCUS, NEIGHBOR, RECENT) would
        have been extractable in earlier turns; only pairs touching a newly-
        introduced CURRENT node carry novel information this turn.

        Pairs are emitted in priority order to ensure the cap preserves the
        highest-evidence candidates when total pairs exceed max_pairs:
          1. CURRENT × FOCUS   — focus node's utterances are in the assembled context
          2. CURRENT × NEIGHBOR — direct graph neighbours of FOCUS
          3. CURRENT × CURRENT  — share the same current utterance by definition
          4. CURRENT × RECENT   — weakest evidence, different-turn utterance context
        """
        if len(candidates) < 2:
            return ""

        by_tag: dict[str, list[dict]] = {}
        for c in candidates:
            by_tag.setdefault(c["tag"], []).append(c)

        current_nodes = by_tag.get("CURRENT", [])
        if not current_nodes:
            return ""

        focus_nodes = by_tag.get("FOCUS", [])
        neighbor_nodes = by_tag.get("NEIGHBOR", [])
        recent_nodes = by_tag.get("RECENT", [])

        def _make_pair(src: dict, tgt: dict) -> str:
            return format_candidate_pair_for_edge_extraction(
                source_id=src["node_id"],
                source_type=src.get("node_type", ""),
                target_id=tgt["node_id"],
                target_type=tgt.get("node_type", ""),
            )

        # Build priority buckets
        seen: set[frozenset] = set()
        buckets: list[list[str]] = [[], [], [], []]  # focus, neighbor, current, recent

        def _add(bucket_idx: int, a: dict, b: dict) -> None:
            key = frozenset([a["node_id"], b["node_id"]])
            if key not in seen:
                seen.add(key)
                buckets[bucket_idx].append(_make_pair(a, b))

        for curr in current_nodes:
            for focus in focus_nodes:
                _add(0, curr, focus)
            for nbr in neighbor_nodes:
                _add(1, curr, nbr)
            for recent in recent_nodes:
                _add(3, curr, recent)

        # intra-CURRENT pairs
        for i, a in enumerate(current_nodes):
            for b in current_nodes[i + 1 :]:
                _add(2, a, b)

        pairs: list[str] = []
        for bucket in buckets:
            for pair in bucket:
                if len(pairs) >= max_pairs:
                    break
                pairs.append(pair)
            if len(pairs) >= max_pairs:
                break

        if not pairs:
            return ""
        return "## Candidate Pairs:\n" + "\n".join(pairs)

    async def _build_existing_edges_section(
        self, session_id: str, focus_node_id: str
    ) -> str:
        """Format existing edges on the focus node for dedup awareness."""
        all_edges = await self._graph_repo.get_edges_by_session(session_id)
        focus_edges = [
            e
            for e in all_edges
            if e.source_node_id == focus_node_id or e.target_node_id == focus_node_id
        ]
        if not focus_edges:
            return ""

        lines: list[str] = ["## Existing Edges on Focus Node:"]
        for edge in focus_edges:
            src_node = await self._graph_repo.get_node(edge.source_node_id)
            tgt_node = await self._graph_repo.get_node(edge.target_node_id)
            lines.append(
                format_existing_edge_for_prompt(
                    source_id=edge.source_node_id,
                    target_id=edge.target_node_id,
                    edge_type=edge.edge_type,
                    source_label=src_node.label if src_node else "",
                    target_label=tgt_node.label if tgt_node else "",
                )
            )
        return "\n".join(lines)
