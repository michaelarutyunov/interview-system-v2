"""Domain identity types for the interview pipeline.

Distinguishes surface graph UUIDs from canonical slot keys at the type level.
Both are str at runtime; NewType enables static-analysis enforcement of the
keyspace contract.
"""

from typing import NewType

SurfaceNodeId = NewType("SurfaceNodeId", str)
"""A graph node UUID stored in kg_nodes. Always usable for graph_repo.get_node()."""

SlotId = NewType("SlotId", str)
"""A canonical slot key, prefixed 'slot_'. NEVER usable for kg_nodes lookup directly."""
