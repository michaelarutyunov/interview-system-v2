"""Methodology schema models for YAML-based configuration."""

from pydantic import BaseModel, Field, PrivateAttr, ConfigDict
from typing import List, Dict, Set, Optional, Any, Union


class NodeTypeSpec(BaseModel):
    """A node type from methodology schema."""

    name: str
    description: str
    examples: List[str] = Field(default_factory=list)
    level: Optional[int] = Field(
        default=None,
        description="Hierarchy level (0=abstract, higher=more concrete). None for non-hierarchical ontologies.",
    )
    terminal: Optional[bool] = Field(
        default=None,
        description="Whether this is a terminal node type (no further expansion). None for non-hierarchical ontologies.",
    )


class EdgeConnectionSpec(BaseModel):
    """A permitted connection for an edge type."""

    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from", description="Source node type")
    to: str = Field(description="Target node type")


class EdgeTypeSpec(BaseModel):
    """An edge type from methodology schema."""

    name: str
    description: str
    permitted_connections: Optional[List[Union[EdgeConnectionSpec, List[str]]]] = Field(
        default=None,
        description="List of permitted connections. Can be EdgeConnectionSpec objects or [source, target] lists.",
    )


class OntologySpec(BaseModel):
    """Ontology specification containing nodes and edges."""

    nodes: List[NodeTypeSpec] = Field(description="Node type definitions")
    edges: List[EdgeTypeSpec] = Field(description="Edge type definitions")


class RelationshipExampleSpec(BaseModel):
    """A relationship extraction example from methodology schema."""

    description: str
    example: str
    extraction: str


class ExtractabilityCriteriaSpec(BaseModel):
    """Extractability criteria from methodology schema."""

    extractable_contains: List[str] = Field(default_factory=list)
    non_extractable_contains: List[str] = Field(default_factory=list)


class MethodologySchema(BaseModel):
    """Methodology schema loaded from YAML.

    Uses new structure with method + ontology fields.
    All methodology YAML files have been migrated to this format.
    """

    # New structure fields
    method: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Method metadata containing:\n"
        "- name: Methodology identifier (e.g., 'means_end_chain', 'jobs_to_be_done')\n"
        "- version: Schema version string\n"
        "- goal: High-level description of the methodology's purpose\n"
        "- opening_bias: Methodology-specific guidance for opening question generation\n"
        "  (e.g., 'Start with concrete attributes' for MEC, 'Start with job context' for JTBD)\n\n"
        "The opening_bias field is particularly important for exploratory interviews as it\n"
        "provides methodology-specific context to guide the LLM in generating appropriate\n"
        "opening questions that align with the methodology's approach.",
    )
    ontology: Optional[OntologySpec] = Field(
        default=None,
        description="Ontology specification with nodes and edges",
    )

    # Methodology-specific extraction sections (optional)
    extraction_guidelines: Optional[List[str]] = None
    relationship_examples: Optional[Dict[str, RelationshipExampleSpec]] = None
    extractability_criteria: Optional[ExtractabilityCriteriaSpec] = None

    # Built on load (not in YAML)
    _node_names: Set[str] = PrivateAttr(default_factory=set)
    _edge_names: Set[str] = PrivateAttr(default_factory=set)

    def model_post_init(self, __context) -> None:
        """Build internal lookup sets after model initialization."""
        # Build lookup sets from ontology
        if self.ontology is not None:
            self._node_names = {nt.name for nt in self.ontology.nodes}
            self._edge_names = {et.name for et in self.ontology.edges}

    def is_valid_node_type(self, name: str) -> bool:
        """Check if a node type is defined in the schema."""
        return name in self._node_names

    def is_valid_edge_type(self, name: str) -> bool:
        """Check if an edge type is defined in the schema."""
        return name in self._edge_names

    def get_valid_node_types(self) -> List[str]:
        """Get list of all valid node type names."""
        if self.ontology:
            return [nt.name for nt in self.ontology.nodes]
        return []

    def get_valid_edge_types(self) -> List[str]:
        """Get list of all valid edge type names."""
        if self.ontology:
            return [et.name for et in self.ontology.edges]
        return []

    def get_terminal_node_types(self) -> List[str]:
        """Get list of terminal node type names.

        Returns:
            List of node type names marked as terminal.
            Returns empty list if no nodes have terminal=True (non-hierarchical ontology).
        """
        if self.ontology:
            return [nt.name for nt in self.ontology.nodes if nt.terminal is True]
        return []

    def get_level_for_node_type(self, node_type: str) -> Optional[int]:
        """Get the hierarchy level for a node type.

        Args:
            node_type: The node type name to look up

        Returns:
            The hierarchy level (0=abstract, higher=more concrete),
            or None if the node type doesn't exist or has no level (non-hierarchical).
        """
        if self.ontology:
            for nt in self.ontology.nodes:
                if nt.name == node_type:
                    return nt.level
        return None

    def is_terminal_node_type(self, node_type: str) -> Optional[bool]:
        """Check if a node type is terminal (end of chain).

        Args:
            node_type: The node type name to check

        Returns:
            True if terminal, False if not terminal, None if not applicable (non-hierarchical).
        """
        if self.ontology:
            for nt in self.ontology.nodes:
                if nt.name == node_type:
                    return nt.terminal
        return None

    def is_valid_connection(
        self, edge_type: str, source_type: str, target_type: str
    ) -> bool:
        """Check if edge_type allows source_type → target_type.

        Args:
            edge_type: The edge/relationship type
            source_type: The source node type
            target_type: The target node type

        Returns:
            True if this connection is allowed by the schema
        """
        if not self.ontology:
            return False

        for et in self.ontology.edges:
            if et.name == edge_type and et.permitted_connections:
                for conn in et.permitted_connections:
                    if isinstance(conn, EdgeConnectionSpec):
                        src, tgt = conn.from_, conn.to
                    elif isinstance(conn, list):
                        src, tgt = conn[0], conn[1]
                    else:
                        continue

                    if (src == "*" or src == source_type) and (
                        tgt == "*" or tgt == target_type
                    ):
                        return True
        return False

    def get_node_descriptions(self) -> Dict[str, str]:
        """For LLM prompt generation: {name: "description (e.g., ex1, ex2)"}.

        Returns:
            Dictionary mapping node type names to formatted descriptions with examples
        """
        result = {}
        if self.ontology:
            for nt in self.ontology.nodes:
                examples = ", ".join(f"'{e}'" for e in nt.examples[:3])
                result[nt.name] = (
                    f"{nt.description} (e.g., {examples})"
                    if examples
                    else nt.description
                )
        return result

    def get_edge_descriptions(self) -> Dict[str, str]:
        """For LLM prompt generation: {name: description}.

        Returns:
            Dictionary mapping edge type names to their descriptions
        """
        result = {}
        if self.ontology:
            result = {et.name: et.description for et in self.ontology.edges}
        return result

    def get_extraction_guidelines(self) -> List[str]:
        """Get methodology-specific extraction guidelines.

        Returns:
            List of guideline strings, or empty list if not defined
        """
        return self.extraction_guidelines or []

    def get_relationship_examples(self) -> Dict[str, RelationshipExampleSpec]:
        """Get methodology-specific relationship extraction examples.

        Returns:
            Dictionary of example name to spec, or empty dict if not defined
        """
        return self.relationship_examples or {}

    def get_extractability_criteria(self) -> ExtractabilityCriteriaSpec:
        """Get extractability criteria for this methodology.

        Returns:
            ExtractabilityCriteriaSpec, or empty spec if not defined
        """
        return self.extractability_criteria or ExtractabilityCriteriaSpec()
