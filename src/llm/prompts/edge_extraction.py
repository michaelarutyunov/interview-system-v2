"""
Prompts for Stage 4.5B edge extraction.

Separates edge identification and typing from node extraction (Stage 3).
Operates on already-resolved nodes with structured input and enforced
chain-of-thought output.

Architecture:
- Universal section: task definition, chain-of-thought structure, XML output schema,
  rejection reason taxonomy (5 codes per D7)
- Methodology section: rendered via MethodologySchema accessors
  - get_edge_descriptions_with_connections() -- edge types, valid source/target types
  - get_chain_relevant_edge_types() -- for prompt-time emphasis on chain-forming edges
- Turn-specific input: formatted utterances with node spans, candidate node list
  with [FOCUS]/[NEIGHBOR]/[CURRENT]/[RECENT] tags, existing edges on focus node
- Response parser: XML -> EdgeExtractionOutput

All prompts produce XML for structured parsing with mandatory chain-of-thought.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Optional

from src.core.schema_loader import load_methodology
from src.domain.models.edge_extraction import (
    ConfidenceLevel,
    ConfirmedEdge,
    EdgeExtractionOutput,
    RejectedEdgeCandidate,
)

# XML output schema (universal)

_XML_OUTPUT_SCHEMA = """<edge_analysis>
  <candidate pair="source_id,target_id">
    <evidence>Verbatim text from the utterance that supports or refutes the relationship</evidence>
    <verdict>confirmed</verdict>
    <edge_type>methodology_edge_type</edge_type>
    <source>source_id</source>
    <target>target_id</target>
    <confidence>high</confidence>
    <supporting_span>[start_char, end_char]</supporting_span>
    <utterance_id>utt_xxx</utterance_id>
    <reasoning assertion="explicit" direction="clear" frame="respondent"/>
  </candidate>

  <candidate pair="source_id,target_id">
    <evidence>Verbatim text from the utterance</evidence>
    <verdict>rejected</verdict>
    <rejection_reason>insufficient_evidence</rejection_reason>
  </candidate>
</edge_analysis>"""

# Rejection reason taxonomy

_REJECTION_TAXONOMY_TEXT = """## Rejection Reason Taxonomy:
When rejecting a candidate pair, use one of these standardised codes:

- **type_constraint_violation**: The edge type you considered is not permitted for this
  source/target node-type pair. Check the edge type definitions for valid connections.
- **insufficient_evidence**: No transcript span provides clear support for this relationship.
  Includes cases of circular evidence (span already used for source node) and purely
  associative connections lacking directionality.
- **duplicate_edge**: A relationship of the same type already exists between these two
  nodes. Do not create redundant edges.
- **semantic_irrelevance**: The source and target nodes refer to unrelated topics or
  domains. No meaningful connection can be established.
- **question_frame_contamination**: The causal frame or relationship direction is supplied
  by the interviewer's question, not asserted by the respondent. The respondent's answer
  confirms a topic but does not independently establish the relationship."""


def get_edge_extraction_system_prompt(methodology: str = "means_end_chain") -> str:
    """Get system prompt for edge extraction.

    Args:
        methodology: Methodology schema name (e.g., "means_end_chain_v2_strict")

    Returns:
        System prompt string for LLM
    """
    schema = load_methodology(methodology)
    edge_descriptions = schema.get_edge_descriptions_with_connections()
    chain_relevant_types = schema.get_chain_relevant_edge_types()

    # Methodology name for display
    method_name = methodology.replace("_", " ").title()

    # Edge types section
    edge_types_lines = []
    for name, desc in edge_descriptions.items():
        chain_marker = (
            " [CHAIN-FORMING -- requires explicit respondent assertion]"
            if name in chain_relevant_types
            else ""
        )
        edge_types_lines.append(f"  - **{name}**: {desc}{chain_marker}")

    edge_types_str = (
        "\n".join(edge_types_lines) if edge_types_lines else "  (none defined)"
    )

    # Chain-relevant emphasis section
    chain_emphasis = ""
    if chain_relevant_types:
        cr_list = ", ".join(f"**{t}**" for t in chain_relevant_types)
        chain_emphasis = f"""
## Chain-Relevant Edge Types:
The following edge types represent chain progression (causal/sequential relationships
that connect nodes across hierarchy levels). These edges carry a **higher evidentiary
standard** -- only confirm them when the respondent's own language supports the connection:

{cr_list}

For chain-relevant edges, the respondent must explicitly or strongly implicitly assert
the relationship. Thematic association is not sufficient."""

    return f"""You are an expert qualitative researcher evaluating potential relationships
between concepts in an interview knowledge graph.

## Task:
For each candidate node pair listed in the input, determine whether a methodology-specific
relationship exists. You must:

1. **Examine the evidence** -- find the specific transcript span that supports or refutes
   the relationship.
2. **Reach a verdict** -- confirm the edge with type, confidence, and structured reasoning,
   or reject it with a standardised reason code (no reasoning needed for rejections).
3. **For confirmed edges, classify the reasoning** along three axes:
   - **assertion**: How the respondent asserted the relationship
     - `explicit` — directly stated by respondent
     - `implicit` — strongly implied or inferred from respondent's language
     - `inferred` — deduced across turns, or from weak signals
   - **direction**: Whether the causal direction is unambiguous
     - `clear` — source→target is the only plausible direction
     - `uncertain` — relationship could flow either way
   - **frame**: Whether the interviewer's question supplied the causal frame
     - `respondent` — respondent asserted the relationship independently
     - `minor_influence` — slight interviewer framing present, but respondent confirmed
     - `contaminated` — interviewer supplied the causal frame (use confidence=low or reject)
4. **Assign confidence** -- derived from the three axes above:
   - **high**: assertion=explicit, direction=clear, frame=respondent
   - **medium**: assertion=implicit or direction=uncertain or frame=minor_influence
   - **low**: assertion=inferred or direction=uncertain or frame=contaminated

**For rejected candidates**, only the rejection_reason code is required — no reasoning
element is needed. The 5-code taxonomy captures the rationale:
{_REJECTION_TAXONOMY_TEXT}

## Universal Principles:
- **Evidence first**: Every confirmed edge must cite a specific utterance span. If no span
  supports the relationship, reject with `insufficient_evidence`.
- **Direction awareness**: The source node must be the cause/trigger/antecedent, and the
  target node must be the effect/outcome/consequent. If the direction is unclear, use
  `confidence=low` or reject.
- **Frame contamination vigilance**: When the interviewer's question suggests a causal
  connection ("Why does X lead to Y?") and the respondent merely elaborates on Y without
  asserting X->Y, the relationship is frame-contaminated. Reject with
  `question_frame_contamination`.
- **Deduplication**: Check the existing edges list. If the same (source, target, type)
  combination already exists, reject with `duplicate_edge`.
- **Relevance check**: If the two nodes discuss unrelated topics, reject with
  `semantic_irrelevance`.

## Methodology: {method_name}
### Valid Edge Types:
{edge_types_str}
{chain_emphasis}
## Output Format:
Return valid XML with this exact structure:

{_XML_OUTPUT_SCHEMA}

Rules:
- Each candidate pair listed in the input MUST appear as a <candidate> element
- For **confirmed** edges: include <edge_type>, <source>, <target>, <confidence>,
  <supporting_span>, <utterance_id>, and <reasoning> with the three axis attributes
- For **rejected** candidates: include <rejection_reason> with one of the 5
  standardised codes. Do NOT include a <reasoning> element — the code suffices.
- <evidence> for confirmed edges: a short key phrase (3-8 words) from the utterance
  that best captures the relationship. For rejected edges: brief note or "none".
  Do NOT copy long verbatim passages — the span reference is sufficient.
- <confidence> must be one of: high, medium, low
- <supporting_span> is a character offset range like [0, 104]
- <utterance_id> must match an utterance ID from the input
- <reasoning> attributes: assertion ∈ {{explicit, implicit, inferred}}, direction ∈ {{clear, uncertain}}, frame ∈ {{respondent, minor_influence, contaminated}}
- **Critical**: If no utterance text is provided in the input, reject ALL candidate pairs
  with `insufficient_evidence`. Produce only valid XML — do NOT write explanatory prose
  outside the XML tags. The output must start with `<edge_analysis>`.

If no candidate pairs are provided in the input, return:
```xml
<edge_analysis>
  <!-- No candidate pairs to evaluate -->
</edge_analysis>
```"""


def get_edge_extraction_user_prompt(
    utterances_text: str = "",
    candidate_nodes_text: str = "",
    candidate_pairs_text: str = "",
    existing_edges_text: str = "",
) -> str:
    """Get user prompt for edge extraction with turn-specific input.

    Args:
        utterances_text: Formatted utterances section
        candidate_nodes_text: Candidate node list with tags (for node reference)
        candidate_pairs_text: Specific candidate pairs to evaluate
        existing_edges_text: Existing edges on the focus node

    Returns:
        User prompt string
    """
    parts: list[str] = []

    if utterances_text:
        parts.append(utterances_text)

    if candidate_nodes_text:
        parts.append(candidate_nodes_text)

    if candidate_pairs_text:
        parts.append(candidate_pairs_text)

    if existing_edges_text:
        parts.append(existing_edges_text)

    if not parts:
        return "No candidate pairs to evaluate."

    prompt = "\n\n".join(parts)
    if candidate_pairs_text:
        prompt += (
            "\n\nEvaluate each candidate pair listed above and return your analysis "
            "in the XML format specified. Only evaluate the pairs listed — do not "
            "invent additional pairs."
        )
    else:
        prompt += (
            "\n\nEvaluate each candidate node pair and return your analysis "
            "in the XML format specified."
        )

    return prompt


# Input formatting helpers


def format_utterance_for_edge_extraction(
    utterance_id: str,
    text: str,
    nodes: list[dict],
) -> str:
    """Format a single utterance with its node spans for edge extraction input."""
    node_lines = []
    for node in nodes:
        node_id = node.get("id", "?")
        node_type = node.get("type", "?")
        span = node.get("span", (0, 0))
        label = node.get("label", "?")
        node_lines.append(
            f"    - id: {node_id}\n"
            f"      type: {node_type}\n"
            f"      span: [{span[0]}, {span[1]}]\n"
            f'      label: "{label}"'
        )

    nodes_block = "\n".join(node_lines) if node_lines else "    (none)"

    return (
        f"utterance_id: {utterance_id}\n"
        f'text: "{text}"\n'
        f"nodes_in_utterance:\n"
        f"{nodes_block}"
    )


def format_candidate_node_for_edge_extraction(
    tag: str,
    node_id: str,
    label: str,
    node_type: str = "",
    turn: Optional[int] = None,
) -> str:
    """Format a single candidate node with a tag for the edge extraction prompt."""
    parts = [f"[{tag}]", f"{node_id}:", f'"{label}"']
    if node_type:
        if turn is not None:
            parts.append(f"({node_type}, t={turn})")
        else:
            parts.append(f"({node_type})")
    elif turn is not None:
        parts.append(f"(t={turn})")
    return " ".join(parts)


def format_candidate_pair_for_edge_extraction(
    source_id: str,
    source_type: str,
    target_id: str,
    target_type: str,
) -> str:
    """Format a candidate node pair for the edge extraction prompt.

    Node labels are intentionally omitted — they are already present in the
    Candidate Nodes section above, and repeating them per-pair causes O(n*m)
    prompt bloat when nodes appear in multiple pairs.
    """
    return (
        f"  - pair=\"{source_id},{target_id}\""
        f"  ({source_type} -> {target_type})"
    )


def format_existing_edge_for_prompt(
    source_id: str,
    target_id: str,
    edge_type: str,
    source_label: str = "",
    target_label: str = "",
) -> str:
    """Format a single existing edge for the edge extraction prompt."""
    if source_label and target_label:
        return (
            f"  - {source_id} --[{edge_type}]--> {target_id}"
            f'  ("{source_label}" -> "{target_label}")'
        )
    return f"  - {source_id} --[{edge_type}]--> {target_id}"


# Response parser


def parse_edge_extraction_response(response_text: str) -> EdgeExtractionOutput:
    """Parse LLM edge extraction XML response into structured data.

    Handles confirmed edges, rejected candidates, and malformed XML.

    Args:
        response_text: XML string from LLM

    Returns:
        EdgeExtractionOutput with confirmed edges and rejected candidates

    Raises:
        ValueError: If XML is malformed or has unexpected structure
    """
    # Strip markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```xml"):
        text = text[6:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Handle empty response
    if not text or "No candidate pairs" in text:
        return EdgeExtractionOutput()

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"Malformed XML in edge extraction response: {e}") from e

    if root.tag != "edge_analysis":
        raise ValueError(f"Expected root tag <edge_analysis>, got <{root.tag}>")

    confirmed_edges: list[ConfirmedEdge] = []
    rejected_candidates: list[RejectedEdgeCandidate] = []
    low_confidence_count = 0
    errors: list[str] = []

    for candidate in root.findall("candidate"):
        pair_attr = candidate.get("pair", "")
        source_id, target_id = _parse_pair_attr(pair_attr)

        verdict_el = candidate.find("verdict")
        if verdict_el is None or not verdict_el.text:
            errors.append(f"Missing <verdict> in candidate pair='{pair_attr}'")
            continue

        verdict = verdict_el.text.strip().lower()

        if verdict == "confirmed":
            try:
                edge = _parse_confirmed_candidate(candidate, source_id, target_id)
                confirmed_edges.append(edge)
                if edge.confidence == "low":
                    low_confidence_count += 1
            except ValueError as e:
                errors.append(str(e))
        elif verdict == "rejected":
            try:
                rejected = _parse_rejected_candidate(candidate, source_id, target_id)
                rejected_candidates.append(rejected)
            except ValueError as e:
                errors.append(str(e))
        else:
            errors.append(
                f"Invalid verdict '{verdict}' in candidate pair='{pair_attr}'"
            )

    if errors and not confirmed_edges and not rejected_candidates:
        error_list = "\n  - ".join(errors)
        raise ValueError(
            f"All candidates failed to parse in edge extraction response:\n  - {error_list}"
        )

    return EdgeExtractionOutput(
        confirmed_edges=confirmed_edges,
        rejected_candidates=rejected_candidates,
        low_confidence_count=low_confidence_count,
    )


def _parse_pair_attr(pair_attr: str) -> tuple[str, str]:
    """Parse the pair attribute 'source_id,target_id' into a tuple."""
    pair_attr = pair_attr.strip()
    if "," not in pair_attr:
        raise ValueError(
            f"Invalid pair attribute format: '{pair_attr}'. "
            f"Expected 'source_id,target_id'"
        )
    parts = pair_attr.split(",", 1)
    return parts[0].strip(), parts[1].strip()


def _parse_confirmed_candidate(
    candidate: ET.Element, source_id: str, target_id: str
) -> ConfirmedEdge:
    """Parse a confirmed <candidate> element into a ConfirmedEdge."""
    pair_attr = candidate.get("pair", f"{source_id},{target_id}")

    def _required_text(tag: str) -> str:
        el = candidate.find(tag)
        if el is None or el.text is None:
            raise ValueError(
                f"Missing required <{tag}> in confirmed candidate pair='{pair_attr}'"
            )
        return el.text.strip()

    edge_type = _required_text("edge_type")
    confidence_raw = _required_text("confidence")
    supporting_span_raw = _required_text("supporting_span")
    utterance_id = _required_text("utterance_id")

    # Parse structured reasoning: <reasoning assertion="..." direction="..." frame="..."/>
    # Backward compat: if reasoning has text content (old format), use it as-is.
    reasoning_el = candidate.find("reasoning")
    assertion: Optional[str] = None
    direction: Optional[str] = None
    frame: Optional[str] = None
    reasoning_summary = ""

    if reasoning_el is not None:
        # New format: structured attributes
        raw_assertion = reasoning_el.get("assertion")
        raw_direction = reasoning_el.get("direction")
        raw_frame = reasoning_el.get("frame")

        if raw_assertion and raw_direction and raw_frame:
            assertion = raw_assertion.strip()
            direction = raw_direction.strip()
            frame = raw_frame.strip()
            reasoning_summary = (
                f"assertion={assertion}, direction={direction}, frame={frame}"
            )
        elif reasoning_el.text and reasoning_el.text.strip():
            # Old format: free-text reasoning
            reasoning_summary = reasoning_el.text.strip()
        else:
            raise ValueError(
                f"<reasoning> in confirmed candidate pair='{pair_attr}' "
                f"must have assertion/direction/frame attributes or text content"
            )
    else:
        raise ValueError(
            f"Missing required <reasoning> in confirmed candidate pair='{pair_attr}'"
        )

    # Validate confidence
    valid_confidence: set[str] = {"high", "medium", "low"}
    if confidence_raw not in valid_confidence:
        raise ValueError(
            f"Invalid confidence '{confidence_raw}' in candidate "
            f"pair='{pair_attr}'. Must be one of: high, medium, low"
        )

    confidence: ConfidenceLevel = confidence_raw  # type: ignore[assignment]

    # Parse supporting span [start, end]
    span_match = re.match(r"\[(\d+),\s*(\d+)\]", supporting_span_raw)
    if not span_match:
        raise ValueError(
            f"Invalid supporting_span format '{supporting_span_raw}' "
            f"in candidate pair='{pair_attr}'. Expected '[start, end]'"
        )
    supporting_span = (int(span_match.group(1)), int(span_match.group(2)))

    # Trust <source>/<target> elements if present, otherwise use pair attr
    source_el = candidate.find("source")
    if source_el is not None and source_el.text:
        source_id = source_el.text.strip()
    target_el = candidate.find("target")
    if target_el is not None and target_el.text:
        target_id = target_el.text.strip()

    return ConfirmedEdge(
        source_node_id=source_id,
        target_node_id=target_id,
        edge_type=edge_type,
        confidence=confidence,
        supporting_span=supporting_span,
        utterance_id=utterance_id,
        reasoning_summary=reasoning_summary,
        assertion=assertion,
        direction=direction,
        frame=frame,
    )


def _parse_rejected_candidate(
    candidate: ET.Element, source_id: str, target_id: str
) -> RejectedEdgeCandidate:
    """Parse a rejected <candidate> element into a RejectedEdgeCandidate."""
    pair_attr = candidate.get("pair", f"{source_id},{target_id}")

    rejection_reason_el = candidate.find("rejection_reason")
    if rejection_reason_el is None or not rejection_reason_el.text:
        raise ValueError(
            f"Missing required <rejection_reason> in rejected candidate "
            f"pair='{pair_attr}'"
        )
    rejection_reason = rejection_reason_el.text.strip()

    reasoning_el = candidate.find("reasoning")
    reasoning_summary = (
        reasoning_el.text.strip()
        if reasoning_el is not None and reasoning_el.text
        else ""
    )

    return RejectedEdgeCandidate(
        source_node_id=source_id,
        target_node_id=target_id,
        rejection_reason=rejection_reason,
        reasoning_summary=reasoning_summary,
    )
