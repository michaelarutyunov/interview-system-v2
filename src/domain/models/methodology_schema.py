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
        description="List of permitted connections. Can be EdgeConnectionSpec objects or [source, target] lists for backward compatibility.",
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

    Supports both new structure (with method + ontology) and legacy structure
    (with name, version, description, node_types, edge_types, valid_connections).
    """

    # New structure fields
    method: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Method metadata (name, version, goal, etc.)",
    )
    ontology: Optional[OntologySpec] = Field(
        default=None,
        description="Ontology specification with nodes and edges",
    )

    # Legacy structure fields (for backward compatibility)
    name: Optional[str] = Field(default=None, deprecated=True)
    version: Optional[str] = Field(default=None, deprecated=True)
    description: Optional[str] = Field(default=None, deprecated=True)
    node_types: Optional[List[NodeTypeSpec]] = Field(default=None, deprecated=True)
    edge_types: Optional[List[EdgeTypeSpec]] = Field(default=None, deprecated=True)
    valid_connections: Optional[Dict[str, List[List[str]]]] = Field(
        default=None, deprecated=True
    )

    # Methodology-specific extraction sections (optional)
    extraction_guidelines: Optional[List[str]] = None
    relationship_examples: Optional[Dict[str, RelationshipExampleSpec]] = None
    extractability_criteria: Optional[ExtractabilityCriteriaSpec] = None

    # Built on load (not in YAML)
    _node_names: Set[str] = PrivateAttr(default_factory=set)
    _edge_names: Set[str] = PrivateAttr(default_factory=set)

    def model_post_init(self, __context) -> None:
        """Build internal lookup sets after model initialization.

        Handles both new structure (method + ontology) and legacy structure.
        """
        # Normalize to new structure if legacy fields are present
        if self.ontology is None and self.node_types is not None:
            # Migrate from legacy structure
            self._migrate_from_legacy()

        # Build lookup sets from ontology
        if self.ontology is not None:
            self._node_names = {nt.name for nt in self.ontology.nodes}
            self._edge_names = {et.name for et in self.ontology.edges}

    def _migrate_from_legacy(self) -> None:
        """Migrate legacy structure to new structure."""
        if self.node_types is None or self.edge_types is None:
            return

        # Build method dict from legacy fields
        self.method = self.method or {}
        if self.name:
            self.method.setdefault("name", self.name)
        if self.version:
            self.method.setdefault("version", self.version)
        if self.description:
            self.method.setdefault("goal", self.description)

        # Migrate edge_types to include permitted_connections from valid_connections
        migrated_edges = []
        for edge_type in self.edge_types:
            edge_dict = edge_type.model_dump()
            # Add permitted_connections from valid_connections if available
            if self.valid_connections and edge_type.name in self.valid_connections:
                connections = self.valid_connections[edge_type.name]
                # Convert to EdgeConnectionSpec objects
                edge_dict["permitted_connections"] = [
                    EdgeConnectionSpec(from_=conn[0], to=conn[1])
                    for conn in connections
                ]
            migrated_edges.append(EdgeTypeSpec(**edge_dict))

        # Create ontology spec
        self.ontology = OntologySpec(nodes=self.node_types, edges=migrated_edges)

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
        return [nt.name for nt in self.node_types] if self.node_types else []

    def get_valid_edge_types(self) -> List[str]:
        """Get list of all valid edge type names."""
        if self.ontology:
            return [et.name for et in self.ontology.edges]
        return [et.name for et in self.edge_types] if self.edge_types else []

    def get_terminal_node_types(self) -> List[str]:
        """Get list of terminal node type names.

        Returns:
            List of node type names marked as terminal.
            Returns empty list if no nodes have terminal=True (non-hierarchical ontology).
        """
        node_types = self.ontology.nodes if self.ontology else self.node_types
        return (
            [nt.name for nt in node_types if nt.terminal is True] if node_types else []
        )

    def get_level_for_node_type(self, node_type: str) -> Optional[int]:
        """Get the hierarchy level for a node type.

        Args:
            node_type: The node type name to look up

        Returns:
            The hierarchy level (0=abstract, higher=more concrete),
            or None if the node type doesn't exist or has no level (non-hierarchical).
        """
        node_types = self.ontology.nodes if self.ontology else self.node_types
        if node_types:
            for nt in node_types:
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
        node_types = self.ontology.nodes if self.ontology else self.node_types
        if node_types:
            for nt in node_types:
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
        # Get valid connections from ontology or legacy field
        connections = None
        if self.ontology:
            for et in self.ontology.edges:
                if et.name == edge_type and et.permitted_connections:
                    connections = []
                    for conn in et.permitted_connections:
                        if isinstance(conn, EdgeConnectionSpec):
                            connections.append([conn.from_, conn.to])
                        elif isinstance(conn, list):
                            connections.append(conn)
                    break
        elif self.valid_connections:
            connections = self.valid_connections.get(edge_type)

        if not connections:
            return False

        for pair in connections:
            src, tgt = pair[0], pair[1]
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
        node_types = self.ontology.nodes if self.ontology else self.node_types
        if node_types:
            for nt in node_types:
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
        edge_types = self.ontology.edges if self.ontology else self.edge_types
        if edge_types:
            result = {et.name: et.description for et in edge_types}
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
