"""Conversion round-trips: string nodes, isolates, attributes."""

from __future__ import annotations

import networkx as nx
import pytest

from nx_rustworkx.convert import convert_from_nx, convert_to_nx, rustworkx_graph_to_nx
from nx_rustworkx.graph import RustworkxGraph


def test_string_nodes_and_isolates():
    G = nx.Graph()
    G.add_edges_from([("alice", "bob"), ("bob", "carol")])
    G.add_node("isolated")
    rwg = convert_from_nx(G)
    assert isinstance(rwg, RustworkxGraph)
    assert not rwg.is_directed()
    assert set(rwg.node_to_index) == {"alice", "bob", "carol", "isolated"}
    assert rwg.number_of_nodes() == 4
    assert rwg.number_of_edges() == 2
    assert rwg.node_to_index["isolated"] in range(4)


def test_directed_preserves_orientation():
    G = nx.DiGraph([("a", "b"), ("b", "c")])
    rwg = convert_from_nx(G)
    assert rwg.is_directed()
    edges = {
        (rwg.index_to_node[u], rwg.index_to_node[v])
        for u, v, _data in rwg.rx_graph.weighted_edge_list()
    }
    assert edges == {("a", "b"), ("b", "c")}


def test_edge_attrs_payload():
    G = nx.Graph()
    G.add_edge("u", "v", weight=2.5, color="red")
    rwg = convert_from_nx(G, edge_attrs={"weight": 1})
    _u, _v, data = next(iter(rwg.rx_graph.weighted_edge_list()))
    assert data == {"weight": 2.5}


def test_preserve_edge_and_graph_attrs():
    G = nx.Graph(name="demo")
    G.add_edge(1, 2, weight=3, note="keep")
    rwg = convert_from_nx(G, preserve_edge_attrs=True, preserve_graph_attrs=True)
    _u, _v, data = next(iter(rwg.rx_graph.weighted_edge_list()))
    assert data["note"] == "keep"
    assert rwg.graph["name"] == "demo"


def test_convert_to_nx_round_trip():
    G = nx.DiGraph()
    G.add_edge("x", "y", weight=4)
    G.add_node("z")
    rwg = convert_from_nx(G, preserve_edge_attrs=True)
    back = convert_to_nx(rwg)
    assert set(back.nodes) == {"x", "y", "z"}
    assert back.has_edge("x", "y")
    assert back["x"]["y"]["weight"] == 4


def test_convert_to_nx_leaves_dicts():
    scores = {"a": 0.5, "b": 0.25}
    assert convert_to_nx(scores) is scores


def test_already_converted_is_identity():
    G = nx.path_graph(3)
    rwg = convert_from_nx(G)
    assert convert_from_nx(rwg) is rwg


def test_rustworkx_graph_to_nx_matches_original_nodes():
    G = nx.Graph([("p", "q"), ("q", "r")])
    back = rustworkx_graph_to_nx(convert_from_nx(G, preserve_edge_attrs=True))
    assert nx.utils.graphs_equal(nx.Graph(G), back)


@pytest.mark.parametrize("nodes", [["a", "b", "c"], [0, 1, 2], [("x", 1), ("y", 2)]])
def test_index_map_is_dense(nodes):
    G = nx.path_graph(nodes)
    rwg = convert_from_nx(G)
    assert list(rwg.rx_graph.node_indices()) == list(range(len(nodes)))
    assert [rwg.index_to_node[i] for i in range(len(nodes))] == list(G)
