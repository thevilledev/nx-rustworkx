"""Conversion round-trips: string nodes, isolates, attributes."""

from __future__ import annotations

import networkx as nx
import pytest

from nx_rustworkx.convert import convert_from_nx, convert_to_nx, rustworkx_graph_to_nx
from nx_rustworkx.graph import RustworkxGraph, RustworkxMultiGraph


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


def _multigraph_fixture(cls):
    M = cls(name="multi")
    M.add_edge(0, 1, weight=3)
    M.add_edge(0, 1, weight=1)
    M.add_edge(1, 1)
    M.add_edge(1, 1, key="loop")
    M.add_edge(2, 3, key="k", color="red", key_=5)
    M.add_node(9, tag="iso")
    M.nodes[0]["n"] = 1
    return M


def test_multigraph_conversion_keeps_parallel_edges_and_keys():
    M = _multigraph_fixture(nx.MultiGraph)
    rwg = convert_from_nx(M, preserve_all_attrs=True)
    assert isinstance(rwg, RustworkxMultiGraph)
    assert rwg.is_multigraph()
    assert rwg.rx_graph.multigraph
    assert rwg.number_of_edges() == 5
    assert set(rwg.edge_keys) == set(rwg.rx_graph.edge_indices())
    assert sorted(map(str, rwg.edge_keys.values())) == ["0", "0", "1", "k", "loop"]
    one = rwg.node_to_index[1]
    # The self-loop bundle is stored once per key, not once per adjacency side.
    assert len(rwg.rx_graph.edge_indices_from_endpoints(one, one)) == 2
    payloads = rwg.rx_graph.get_all_edge_data(rwg.node_to_index[0], one)
    assert sorted(p["weight"] for p in payloads) == [1, 3]


def test_multidigraph_conversion_keeps_orientation_and_keys():
    D = nx.MultiDiGraph([(0, 1, {}), (0, 1, {}), (1, 0, {})])
    rwg = convert_from_nx(D)
    assert rwg.is_directed() and rwg.is_multigraph()
    zero, one = rwg.node_to_index[0], rwg.node_to_index[1]
    assert len(rwg.rx_graph.edge_indices_from_endpoints(zero, one)) == 2
    assert len(rwg.rx_graph.edge_indices_from_endpoints(one, zero)) == 1
    assert sorted(rwg.edge_keys.values()) == [0, 0, 1]


@pytest.mark.parametrize("cls", [nx.MultiGraph, nx.MultiDiGraph])
def test_multigraph_round_trip_is_strictly_equal(cls):
    M = _multigraph_fixture(cls)
    back = convert_to_nx(convert_from_nx(M, preserve_all_attrs=True))
    assert type(back) is cls
    assert back._adj == M._adj
    assert back._node == M._node
    assert back.graph == M.graph


def test_multigraph_edge_attrs_filter_applies_per_key():
    M = _multigraph_fixture(nx.MultiGraph)
    rwg = convert_from_nx(M, edge_attrs={"weight": 1})
    payloads = [data for _u, _v, data in rwg.rx_graph.weighted_edge_list()]
    assert all(set(data) == {"weight"} for data in payloads)
    assert sorted(data["weight"] for data in payloads) == [1, 1, 1, 1, 3]


def test_multigraph_conversion_copies_payloads():
    M = nx.MultiGraph()
    M.add_edge(0, 1, weight=1)
    rwg = convert_from_nx(M, preserve_edge_attrs=True)
    rwg.rx_graph.get_edge_data_by_index(0)["weight"] = 99
    assert M[0][1][0]["weight"] == 1


def test_simple_wrapper_has_no_edge_keys():
    rwg = convert_from_nx(nx.path_graph(3))
    assert type(rwg) is RustworkxGraph
    assert rwg.edge_keys is None
    assert not rwg.rx_graph.multigraph


def test_convert_back_accepts_non_string_attr_keys():
    # NetworkX allows non-string attribute keys; keyword expansion does not.
    g = nx.Graph()
    g.add_edge(0, 1)
    g[0][1][1] = "x"
    g[0][1]["w"] = 2
    out = rustworkx_graph_to_nx(convert_from_nx(g, preserve_edge_attrs=True))
    assert out[0][1] == {1: "x", "w": 2}
