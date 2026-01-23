"""Methodology schema models for YAML-based configuration."""

from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Dict, Set


class NodeTypeSpec(BaseModel):
    """A node type from methodology schema."""
    name: str
    description: str
    examples: List[str] = Field(default_factory=list)


class EdgeTypeSpec(BaseModel):
    """An edge type from methodology schema."""
    name: str
    description: str


class MethodologySchema(BaseModel):
    """Methodology schema loaded from YAML."""
    name: str
    version: str
    description: str
    node_types: List[NodeTypeSpec]
    edge_types: List[EdgeTypeSpec]
    valid_connections: Dict[str, List[List[str]]]  # edge_name → [[source, target], ...]

    # Built on load (not in YAML)
    _node_names: Set[str] = PrivateAttr(default_factory=set)
    _edge_names: Set[str] = PrivateAttr(default_factory=set)

    def model_post_init(self, __context) -> None:
        """Build internal lookup sets after model initialization."""
        self._node_names = {nt.name for nt in self.node_types}
        self._edge_names = {et.name for et in self.edge_types}

    def is_valid_node_type(self, name: str) -> bool:
        """Check if a node type is defined in the schema."""
        return name in self._node_names

    def is_valid_edge_type(self, name: str) -> bool:
        """Check if an edge type is defined in the schema."""
        return name in self._edge_names

    def get_valid_node_types(self) -> List[str]:
        """Get list of all valid node type names."""
        return [nt.name for nt in self.node_types]

    def get_valid_edge_types(self) -> List[str]:
        """Get list of all valid edge type names."""
        return [et.name for et in self.edge_types]

    def is_valid_connection(self, edge_type: str, source_type: str, target_type: str) -> bool:
        """Check if edge_type allows source_type → target_type.

        Args:
            edge_type: The edge/relationship type
            source_type: The source node type
            target_type: The target node type

        Returns:
            True if this connection is allowed by the schema
        """
        connections = self.valid_connections.get(edge_type, [])
        for pair in connections:
            src, tgt = pair[0], pair[1]
            if (src == "*" or src == source_type) and (tgt == "*" or tgt == target_type):
                return True
        return False

    def get_node_descriptions(self) -> Dict[str, str]:
        """For LLM prompt generation: {name: "description (e.g., ex1, ex2)"}.

        Returns:
            Dictionary mapping node type names to formatted descriptions with examples
        """
        result = {}
        for nt in self.node_types:
            examples = ", ".join(f"'{e}'" for e in nt.examples[:3])
            result[nt.name] = f"{nt.description} (e.g., {examples})" if examples else nt.description
        return result

    def get_edge_descriptions(self) -> Dict[str, str]:
        """For LLM prompt generation: {name: description}.

        Returns:
            Dictionary mapping edge type names to their descriptions
        """
        return {et.name: et.description for et in self.edge_types}
