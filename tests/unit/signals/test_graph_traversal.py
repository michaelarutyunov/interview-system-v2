"""Tests for shared graph traversal utilities."""

from typing import NamedTuple

import pytest

from src.signals.graph.graph_traversal import (
    bfs_reachable,
    bfs_to_target,
    build_adjacency_list,
    build_reverse_adjacency_list,
    get_node_type_map,
)


# -- Lightweight mock objects --


class MockNode(NamedTuple):
    id: str
    node_type: str


class MockEdge(NamedTuple):
    source_node_id: str
    target_node_id: str


# -- Fixtures --


@pytest.fixture
def linear_chain():
    """A→B→C→D (attribute → functional → psychosocial → terminal)."""
    nodes = [
        MockNode("a", "attribute"),
        MockNode("b", "functional_consequence"),
        MockNode("c", "psychosocial_consequence"),
        MockNode("d", "terminal_value"),
    ]
    edges = [
        MockEdge("a", "b"),
        MockEdge("b", "c"),
        MockEdge("c", "d"),
    ]
    return nodes, edges


@pytest.fixture
def branching_graph():
    """Two chains sharing a middle node:
    A1 → B → C1 → D
    A2 → B → C2 → D
    """
    nodes = [
        MockNode("a1", "attribute"),
        MockNode("a2", "attribute"),
        MockNode("b", "functional_consequence"),
        MockNode("c1", "psychosocial_consequence"),
        MockNode("c2", "psychosocial_consequence"),
        MockNode("d", "terminal_value"),
    ]
    edges = [
        MockEdge("a1", "b"),
        MockEdge("a2", "b"),
        MockEdge("b", "c1"),
        MockEdge("b", "c2"),
        MockEdge("c1", "d"),
        MockEdge("c2", "d"),
    ]
    return nodes, edges


@pytest.fixture
def disconnected_graph():
    """Two disconnected chains: A→B and C→D."""
    nodes = [
        MockNode("a", "attribute"),
        MockNode("b", "functional_consequence"),
        MockNode("c", "attribute"),
        MockNode("d", "terminal_value"),
    ]
    edges = [
        MockEdge("a", "b"),
        MockEdge("c", "d"),
    ]
    return nodes, edges


# -- Tests --


class TestBuildAdjacencyList:
    def test_linear_chain(self, linear_chain):
        nodes, edges = linear_chain
        adj = build_adjacency_list(nodes, edges)
        assert adj == {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}

    def test_branching(self, branching_graph):
        nodes, edges = branching_graph
        adj = build_adjacency_list(nodes, edges)
        assert adj["b"] == ["c1", "c2"]
        assert adj["a1"] == ["b"]
        assert adj["a2"] == ["b"]

    def test_empty_edges(self):
        nodes = [MockNode("a", "attribute")]
        adj = build_adjacency_list(nodes, [])
        assert adj == {"a": []}

    def test_unknown_source_ignored(self):
        """Edges with source not in nodes list are dropped."""
        nodes = [MockNode("a", "attribute")]
        edges = [MockEdge("unknown", "a")]
        adj = build_adjacency_list(nodes, edges)
        assert adj == {"a": []}


class TestBuildReverseAdjacencyList:
    def test_linear_chain(self, linear_chain):
        nodes, edges = linear_chain
        rev = build_reverse_adjacency_list(nodes, edges)
        assert rev == {"a": [], "b": ["a"], "c": ["b"], "d": ["c"]}

    def test_branching(self, branching_graph):
        nodes, edges = branching_graph
        rev = build_reverse_adjacency_list(nodes, edges)
        assert set(rev["b"]) == {"a1", "a2"}
        assert rev["a1"] == []


class TestGetNodeTypeMap:
    def test_basic(self, linear_chain):
        nodes, _ = linear_chain
        type_map = get_node_type_map(nodes)
        assert type_map == {
            "a": "attribute",
            "b": "functional_consequence",
            "c": "psychosocial_consequence",
            "d": "terminal_value",
        }

    def test_empty(self):
        assert get_node_type_map([]) == {}


class TestBFSToTarget:
    def test_reaches_terminal(self, linear_chain):
        nodes, edges = linear_chain
        adj = build_adjacency_list(nodes, edges)
        type_map = get_node_type_map(nodes)
        assert bfs_to_target("a", adj, {"terminal_value"}, type_map) is True

    def test_start_is_terminal(self, linear_chain):
        nodes, edges = linear_chain
        adj = build_adjacency_list(nodes, edges)
        type_map = get_node_type_map(nodes)
        assert bfs_to_target("d", adj, {"terminal_value"}, type_map) is True

    def test_no_path_to_terminal(self, disconnected_graph):
        nodes, edges = disconnected_graph
        adj = build_adjacency_list(nodes, edges)
        type_map = get_node_type_map(nodes)
        # "a" reaches "b" but not "d" (disconnected)
        assert bfs_to_target("a", adj, {"terminal_value"}, type_map) is False

    def test_disconnected_reaches_own_terminal(self, disconnected_graph):
        nodes, edges = disconnected_graph
        adj = build_adjacency_list(nodes, edges)
        type_map = get_node_type_map(nodes)
        assert bfs_to_target("c", adj, {"terminal_value"}, type_map) is True

    def test_empty_target_types(self, linear_chain):
        nodes, edges = linear_chain
        adj = build_adjacency_list(nodes, edges)
        type_map = get_node_type_map(nodes)
        assert bfs_to_target("a", adj, set(), type_map) is False

    def test_orphan_node(self):
        nodes = [MockNode("a", "attribute")]
        adj = build_adjacency_list(nodes, [])
        type_map = get_node_type_map(nodes)
        assert bfs_to_target("a", adj, {"terminal_value"}, type_map) is False


class TestBFSReachable:
    def test_linear_chain(self, linear_chain):
        nodes, edges = linear_chain
        adj = build_adjacency_list(nodes, edges)
        reachable = bfs_reachable("a", adj)
        assert reachable == {"a": 0, "b": 1, "c": 2, "d": 3}

    def test_partial_chain(self, linear_chain):
        nodes, edges = linear_chain
        adj = build_adjacency_list(nodes, edges)
        reachable = bfs_reachable("b", adj)
        assert reachable == {"b": 0, "c": 1, "d": 2}
        assert "a" not in reachable  # reverse direction not traversed

    def test_orphan_node(self):
        nodes = [MockNode("a", "attribute")]
        adj = build_adjacency_list(nodes, [])
        reachable = bfs_reachable("a", adj)
        assert reachable == {"a": 0}

    def test_reverse_adjacency(self, linear_chain):
        """Using reverse adjacency traces paths backward."""
        nodes, edges = linear_chain
        rev = build_reverse_adjacency_list(nodes, edges)
        reachable = bfs_reachable("d", rev)
        assert reachable == {"d": 0, "c": 1, "b": 2, "a": 3}
