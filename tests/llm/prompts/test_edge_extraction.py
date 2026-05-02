"""Tests for the edge extraction prompt module (Stage 4.5B)."""

import pytest

from src.llm.prompts.edge_extraction import (
    get_edge_extraction_system_prompt,
    get_edge_extraction_user_prompt,
    parse_edge_extraction_response,
    format_utterance_for_edge_extraction,
    format_candidate_node_for_edge_extraction,
    format_existing_edge_for_prompt,
)
from src.domain.models.edge_extraction import (
    is_valid_rejection_reason,
    VALID_REJECTION_REASONS,
)


# ── Rejection taxonomy ──────────────────────────────────────────────────────


def test_valid_rejection_reasons():
    """All 5 D7 taxonomy codes are recognised."""
    for code in VALID_REJECTION_REASONS:
        assert is_valid_rejection_reason(code), f"Expected {code} to be valid"


def test_invalid_rejection_reason():
    """Codes not in the taxonomy are rejected."""
    assert not is_valid_rejection_reason("made_up_reason")
    assert not is_valid_rejection_reason("")
    assert not is_valid_rejection_reason("associative_only")


# ── System prompt rendering ─────────────────────────────────────────────────

ACTIVE_METHODOLOGIES = [
    "means_end_chain_v2_strict",
    "means_end_chain_v2_flex",
    "jobs_to_be_done_v2",
    "critical_incident_v2",
    "customer_journey_mapping_v2",
    "repertory_grid_v2",
]


@pytest.mark.parametrize("methodology", ACTIVE_METHODOLOGIES)
def test_system_prompt_renders_for_methodology(methodology: str):
    """System prompt renders without error for all 6 active methodologies."""
    prompt = get_edge_extraction_system_prompt(methodology)
    assert isinstance(prompt, str)
    assert len(prompt) > 500, (
        f"Prompt for {methodology} is too short ({len(prompt)} chars)"
    )


@pytest.mark.parametrize("methodology", ACTIVE_METHODOLOGIES)
def test_system_prompt_contains_rejection_taxonomy(methodology: str):
    """Every methodology prompt includes the 5-code rejection taxonomy."""
    prompt = get_edge_extraction_system_prompt(methodology)
    for code in VALID_REJECTION_REASONS:
        assert code in prompt, (
            f"Methodology {methodology}: missing rejection code '{code}'"
        )


@pytest.mark.parametrize("methodology", ACTIVE_METHODOLOGIES)
def test_system_prompt_contains_xml_output_schema(methodology: str):
    """Every methodology prompt includes the XML output schema."""
    prompt = get_edge_extraction_system_prompt(methodology)
    assert "<edge_analysis>" in prompt
    assert "<candidate " in prompt
    assert "<verdict>" in prompt


@pytest.mark.parametrize("methodology", ACTIVE_METHODOLOGIES)
def test_system_prompt_contains_edge_types(methodology: str):
    """Prompt includes the methodology's edge type descriptions."""
    prompt = get_edge_extraction_system_prompt(methodology)
    assert "Valid Edge Types:" in prompt


def test_mec_strict_prompt_includes_chain_relevant_section():
    """MEC strict has chain_relevant edges (leads_to)."""
    prompt = get_edge_extraction_system_prompt("means_end_chain_v2_strict")
    assert "Chain-Relevant Edge Types:" in prompt
    assert "leads_to" in prompt
    assert "CHAIN-FORMING" in prompt


def test_rg_prompt_includes_chain_relevant_edges():
    """Repertory Grid has one chain-relevant edge (implies) -- section appears."""
    prompt = get_edge_extraction_system_prompt("repertory_grid_v2")
    assert "Chain-Relevant Edge Types:" in prompt
    assert "implies" in prompt


def test_jtbd_prompt_includes_multiple_chain_relevant_edges():
    """JTBD has multiple chain-relevant edges -- all appear with markers."""
    prompt = get_edge_extraction_system_prompt("jobs_to_be_done_v2")
    assert "Chain-Relevant Edge Types:" in prompt
    assert "triggers" in prompt
    assert "CHAIN-FORMING" in prompt
    # Each chain-relevant edge should be marked
    assert prompt.count("CHAIN-FORMING") >= 4  # JTBD has 4 chain-relevant edges


def test_mec_strict_includes_permitted_connections():
    """MEC strict edge descriptions include valid source->target pairs."""
    prompt = get_edge_extraction_system_prompt("means_end_chain_v2_strict")
    assert "attribute->attribute" in prompt.lower() or "(valid:" in prompt


# ── User prompt rendering ───────────────────────────────────────────────────


def test_user_prompt_empty():
    """Empty inputs produce a no-candidates message."""
    prompt = get_edge_extraction_user_prompt()
    assert "No candidate pairs to evaluate" in prompt


def test_user_prompt_with_utterances():
    """Utterances section is included."""
    prompt = get_edge_extraction_user_prompt(
        utterances_text=(
            'utterance_id: utt_001\ntext: "hello"\nnodes_in_utterance:\n    (none)'
        ),
    )
    assert "utt_001" in prompt
    assert "hello" in prompt


def test_user_prompt_with_candidates():
    """Candidate nodes section is included."""
    prompt = get_edge_extraction_user_prompt(
        candidate_nodes_text='[FOCUS] n_001: "test node" (attribute, t=1)',
    )
    assert "[FOCUS]" in prompt
    assert "n_001" in prompt


def test_user_prompt_with_existing_edges():
    """Existing edges section is included."""
    prompt = get_edge_extraction_user_prompt(
        existing_edges_text="  - n_001 --[leads_to]--> n_002",
    )
    assert "leads_to" in prompt


def test_user_prompt_combined():
    """All three sections combine correctly."""
    prompt = get_edge_extraction_user_prompt(
        utterances_text="## Utterances",
        candidate_nodes_text="## Candidate Nodes",
        existing_edges_text="## Existing Edges",
    )
    assert "## Utterances" in prompt
    assert "## Candidate Nodes" in prompt
    assert "## Existing Edges" in prompt
    assert "return your analysis" in prompt


# ── Input formatting helpers ────────────────────────────────────────────────


def test_format_utterance():
    """Utterance formatting includes text and node spans."""
    result = format_utterance_for_edge_extraction(
        utterance_id="utt_007",
        text="I drink coffee every morning.",
        nodes=[
            {
                "id": "n_019",
                "type": "pain_point",
                "span": (0, 27),
                "label": "drinking coffee daily",
            },
        ],
    )
    assert "utt_007" in result
    assert "I drink coffee every morning" in result
    assert "n_019" in result
    assert "pain_point" in result
    assert "[0, 27]" in result
    assert "drinking coffee daily" in result


def test_format_utterance_no_nodes():
    """Utterance with no nodes shows (none)."""
    result = format_utterance_for_edge_extraction(
        utterance_id="utt_001",
        text="ok",
        nodes=[],
    )
    assert "(none)" in result


def test_format_candidate_node():
    """Candidate node formatting includes all fields."""
    result = format_candidate_node_for_edge_extraction(
        tag="FOCUS",
        node_id="n_008",
        label="choosing ZeroFizz",
        node_type="solution_approach",
        turn=7,
    )
    assert "[FOCUS]" in result
    assert "n_008" in result
    assert "choosing ZeroFizz" in result
    assert "solution_approach" in result
    assert "t=7" in result


def test_format_candidate_node_minimal():
    """Candidate node with minimal fields."""
    result = format_candidate_node_for_edge_extraction(
        tag="CURRENT",
        node_id="n_019",
        label="feeling tired",
    )
    assert "[CURRENT]" in result
    assert "n_019" in result
    assert "feeling tired" in result


def test_format_existing_edge():
    """Existing edge formatting."""
    result = format_existing_edge_for_prompt(
        source_id="n_001",
        target_id="n_002",
        edge_type="leads_to",
        source_label="morning coffee",
        target_label="feeling awake",
    )
    assert "n_001" in result
    assert "n_002" in result
    assert "leads_to" in result
    assert "morning coffee" in result
    assert "feeling awake" in result


def test_format_existing_edge_no_labels():
    """Existing edge without labels."""
    result = format_existing_edge_for_prompt(
        source_id="n_001",
        target_id="n_002",
        edge_type="triggers",
    )
    assert "n_001" in result
    assert "n_002" in result
    assert "triggers" in result


# ── Parser: confirmed edges ─────────────────────────────────────────────────


def test_parse_confirmed_edge():
    """Parser extracts a confirmed edge from valid XML."""
    xml = """<edge_analysis>
  <candidate pair="n_019,n_020">
    <evidence>"but ZeroFizz doesn't do that to me"</evidence>
    <reasoning>The respondent directly contrasts the pain with the solution.</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>implies</edge_type>
    <source>n_019</source>
    <target>n_020</target>
    <confidence>high</confidence>
    <supporting_span>[0, 104]</supporting_span>
    <utterance_id>utt_007</utterance_id>
  </candidate>
</edge_analysis>"""
    output = parse_edge_extraction_response(xml)
    assert len(output.confirmed_edges) == 1
    assert len(output.rejected_candidates) == 0
    edge = output.confirmed_edges[0]
    assert edge.source_node_id == "n_019"
    assert edge.target_node_id == "n_020"
    assert edge.edge_type == "implies"
    assert edge.confidence == "high"
    assert edge.supporting_span == (0, 104)
    assert edge.utterance_id == "utt_007"
    assert "contrasts" in edge.reasoning_summary


def test_parse_multiple_mixed_candidates():
    """Parser handles a mix of confirmed and rejected candidates."""
    xml = """<edge_analysis>
  <candidate pair="n_001,n_002">
    <evidence>"this leads to that"</evidence>
    <reasoning>Clear causal link.</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>n_001</source>
    <target>n_002</target>
    <confidence>medium</confidence>
    <supporting_span>[5, 25]</supporting_span>
    <utterance_id>utt_001</utterance_id>
  </candidate>
  <candidate pair="n_003,n_004">
    <evidence>"unrelated topics"</evidence>
    <reasoning>No connection between these concepts.</reasoning>
    <verdict>rejected</verdict>
    <rejection_reason>semantic_irrelevance</rejection_reason>
  </candidate>
</edge_analysis>"""
    output = parse_edge_extraction_response(xml)
    assert len(output.confirmed_edges) == 1
    assert len(output.rejected_candidates) == 1
    assert output.confirmed_edges[0].confidence == "medium"
    assert output.rejected_candidates[0].rejection_reason == "semantic_irrelevance"


def test_parse_all_confidence_levels():
    """Parser validates confidence literal (high, medium, low)."""
    for level in ("high", "medium", "low"):
        xml = f"""<edge_analysis>
  <candidate pair="a,b">
    <evidence>test</evidence>
    <reasoning>test</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>a</source>
    <target>b</target>
    <confidence>{level}</confidence>
    <supporting_span>[0, 10]</supporting_span>
    <utterance_id>u1</utterance_id>
  </candidate>
</edge_analysis>"""
        output = parse_edge_extraction_response(xml)
        assert output.confirmed_edges[0].confidence == level


def test_low_confidence_count():
    """Parser tracks low_confidence_count correctly."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e1</evidence>
    <reasoning>r1</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>a</source>
    <target>b</target>
    <confidence>low</confidence>
    <supporting_span>[0,5]</supporting_span>
    <utterance_id>u1</utterance_id>
  </candidate>
  <candidate pair="c,d">
    <evidence>e2</evidence>
    <reasoning>r2</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>c</source>
    <target>d</target>
    <confidence>high</confidence>
    <supporting_span>[5,10]</supporting_span>
    <utterance_id>u2</utterance_id>
  </candidate>
  <candidate pair="e,f">
    <evidence>e3</evidence>
    <reasoning>r3</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>e</source>
    <target>f</target>
    <confidence>low</confidence>
    <supporting_span>[10,15]</supporting_span>
    <utterance_id>u3</utterance_id>
  </candidate>
</edge_analysis>"""
    output = parse_edge_extraction_response(xml)
    assert output.low_confidence_count == 2


# ── Parser: rejected candidates ─────────────────────────────────────────────


def test_parse_rejected_candidate():
    """Parser extracts a rejected candidate from XML."""
    xml = """<edge_analysis>
  <candidate pair="n_006,n_019">
    <evidence>"but ZeroFizz doesn't do that"</evidence>
    <reasoning>The implication was from the interviewer's question.</reasoning>
    <verdict>rejected</verdict>
    <rejection_reason>question_frame_contamination</rejection_reason>
  </candidate>
</edge_analysis>"""
    output = parse_edge_extraction_response(xml)
    assert len(output.confirmed_edges) == 0
    assert len(output.rejected_candidates) == 1
    rejected = output.rejected_candidates[0]
    assert rejected.source_node_id == "n_006"
    assert rejected.target_node_id == "n_019"
    assert rejected.rejection_reason == "question_frame_contamination"


# ── Parser: error handling ──────────────────────────────────────────────────


def test_parse_malformed_xml_raises():
    """Malformed XML raises ValueError with clear message."""
    with pytest.raises(ValueError, match="Malformed XML"):
        parse_edge_extraction_response("not xml at all")


def test_parse_wrong_root_tag_raises():
    """Wrong root tag raises ValueError."""
    with pytest.raises(ValueError, match="Expected root tag"):
        parse_edge_extraction_response("<wrong><candidate/></wrong>")


def test_parse_missing_verdict():
    """Missing verdict is tolerated if other candidates have it."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
  </candidate>
  <candidate pair="c,d">
    <evidence>e2</evidence>
    <reasoning>r2</reasoning>
    <verdict>rejected</verdict>
    <rejection_reason>insufficient_evidence</rejection_reason>
  </candidate>
</edge_analysis>"""
    output = parse_edge_extraction_response(xml)
    assert len(output.rejected_candidates) == 1


def test_parse_all_fail_raises():
    """If ALL candidates fail to parse, raise ValueError."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
  </candidate>
</edge_analysis>"""
    with pytest.raises(ValueError, match="All candidates failed"):
        parse_edge_extraction_response(xml)


def test_parse_invalid_confidence_raises():
    """Invalid confidence value raises ValueError."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>a</source>
    <target>b</target>
    <confidence>very_high</confidence>
    <supporting_span>[0,10]</supporting_span>
    <utterance_id>u1</utterance_id>
  </candidate>
</edge_analysis>"""
    with pytest.raises(ValueError, match="All candidates failed"):
        parse_edge_extraction_response(xml)


def test_parse_invalid_span_format_raises():
    """Invalid span format raises ValueError."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>a</source>
    <target>b</target>
    <confidence>high</confidence>
    <supporting_span>not-a-span</supporting_span>
    <utterance_id>u1</utterance_id>
  </candidate>
</edge_analysis>"""
    with pytest.raises(ValueError, match="All candidates failed"):
        parse_edge_extraction_response(xml)


def test_parse_invalid_verdict():
    """Invalid verdict value raises ValueError."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
    <verdict>maybe</verdict>
  </candidate>
</edge_analysis>"""
    with pytest.raises(ValueError, match="All candidates failed"):
        parse_edge_extraction_response(xml)


def test_parse_empty_response():
    """Empty response returns empty EdgeExtractionOutput."""
    output = parse_edge_extraction_response("")
    assert output.confirmed_edges == []
    assert output.rejected_candidates == []
    assert output.low_confidence_count == 0


def test_parse_no_candidates_response():
    """No-candidates XML returns empty output."""
    output = parse_edge_extraction_response(
        """<edge_analysis>
  <!-- No candidate pairs to evaluate -->
</edge_analysis>"""
    )
    assert output.confirmed_edges == []
    assert output.rejected_candidates == []


def test_parse_markdown_code_block():
    """Parser strips markdown ```xml fences."""
    xml_content = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
    <verdict>confirmed</verdict>
    <edge_type>leads_to</edge_type>
    <source>a</source>
    <target>b</target>
    <confidence>high</confidence>
    <supporting_span>[0,10]</supporting_span>
    <utterance_id>u1</utterance_id>
  </candidate>
</edge_analysis>"""
    output = parse_edge_extraction_response(f"```xml\n{xml_content}\n```")
    assert len(output.confirmed_edges) == 1


def test_parse_missing_rejection_reason():
    """Rejected candidate without rejection_reason raises."""
    xml = """<edge_analysis>
  <candidate pair="a,b">
    <evidence>e</evidence>
    <reasoning>r</reasoning>
    <verdict>rejected</verdict>
  </candidate>
</edge_analysis>"""
    with pytest.raises(ValueError, match="All candidates failed"):
        parse_edge_extraction_response(xml)
