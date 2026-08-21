"""Correctness against NetworkX on unweighted graphs."""

from __future__ import annotations

import networkx as nx
import pytest


def _er_graph(n=80, p=0.08, seed=0, directed=False):
    if directed:
        return nx.gnp_random_graph(n, p, seed=seed, directed=True)
    return nx.gnp_random_graph(n, p, seed=seed)


def test_edge_betweenness_matches():
    G = nx.karate_club_graph()
    got = nx.edge_betweenness_centrality(G, backend="rustworkx")
    expected = nx.edge_betweenness_centrality.orig_func(G)
    assert set(got) == set(expected)
    for edge in expected:
        assert got[edge] == pytest.approx(expected[edge], rel=1e-9, abs=1e-12)


def test_closeness_matches():
    G = nx.karate_club_graph()
    got = nx.closeness_centrality(G, backend="rustworkx")
    expected = nx.closeness_centrality.orig_func(G)
    for node in G:
        assert got[node] == pytest.approx(expected[node], rel=1e-9, abs=1e-12)


def test_eigenvector_matches():
    G = nx.karate_club_graph()
    got = nx.eigenvector_centrality(G, backend="rustworkx", max_iter=500)
    expected = nx.eigenvector_centrality.orig_func(G, max_iter=500)
    for node in G:
        assert got[node] == pytest.approx(expected[node], rel=1e-5, abs=1e-6)


def test_shortest_path_variants():
    G = nx.path_graph(["s", "a", "b", "t"])
    assert nx.shortest_path(G, "s", "t", backend="rustworkx") == ["s", "a", "b", "t"]
    assert nx.shortest_path_length(G, "s", "t", backend="rustworkx") == 3
    paths = nx.shortest_path(G, source="s", backend="rustworkx")
    assert paths["t"] == ["s", "a", "b", "t"]
    assert paths["s"] == ["s"]


def test_dijkstra_and_bellman_ford_paths():
    G = nx.DiGraph()
    G.add_edge("s", "a", weight=1)
    G.add_edge("a", "t", weight=2)
    G.add_edge("s", "t", weight=10)
    assert nx.dijkstra_path(G, "s", "t", backend="rustworkx") == ["s", "a", "t"]
    assert nx.bellman_ford_path(G, "s", "t", backend="rustworkx") == ["s", "a", "t"]
    length, path = nx.single_source_dijkstra(G, "s", target="t", backend="rustworkx")
    assert path == ["s", "a", "t"]
    assert length == pytest.approx(3)


def test_single_source_dijkstra_dicts():
    G = nx.path_graph(4)
    lengths, paths = nx.single_source_dijkstra(G, 0, backend="rustworkx")
    assert lengths[0] == 0
    assert lengths[3] == 3
    assert paths[3] == [0, 1, 2, 3]


def test_no_path_raises():
    G = nx.Graph([(0, 1), (2, 3)])
    with pytest.raises(nx.NetworkXNoPath):
        nx.shortest_path(G, 0, 3, backend="rustworkx")


def test_connectivity_undirected():
    G = nx.Graph([(0, 1), (1, 2), (3, 4)])
    assert nx.is_connected(G, backend="rustworkx") is False
    assert nx.number_connected_components(G, backend="rustworkx") == 2
    comps = [frozenset(c) for c in nx.connected_components(G, backend="rustworkx")]
    assert frozenset({0, 1, 2}) in comps
    assert frozenset({3, 4}) in comps


def test_weak_connectivity_directed():
    G = nx.DiGraph([(0, 1), (1, 2)])
    assert nx.is_weakly_connected(G, backend="rustworkx") is True
    comps = list(nx.weakly_connected_components(G, backend="rustworkx"))
    assert comps == [{0, 1, 2}]


def test_null_graph_connectivity():
    with pytest.raises(nx.NetworkXPointlessConcept):
        nx.is_connected(nx.Graph(), backend="rustworkx")


def test_pagerank_close_to_networkx():
    G = _er_graph(directed=True)
    got = nx.pagerank(G, backend="rustworkx")
    expected = nx.pagerank.orig_func(G)
    for node in G:
        assert got[node] == pytest.approx(expected[node], rel=1e-5, abs=1e-6)


def test_is_isomorphic_structural():
    G1 = nx.cycle_graph(6)
    G2 = nx.cycle_graph(6)
    G2 = nx.relabel_nodes(G2, {i: f"n{i}" for i in G2})
    assert nx.is_isomorphic(G1, G2, backend="rustworkx") is True
    assert nx.is_isomorphic(G1, nx.path_graph(6), backend="rustworkx") is False


def test_priority_hits_rustworkx_on_large_graph(monkeypatch):
    import rustworkx as rx

    called = {}
    original = rx.betweenness_centrality

    def wrapper(*args, **kwargs):
        called["yes"] = True
        return original(*args, **kwargs)

    monkeypatch.setattr(rx, "betweenness_centrality", wrapper)
    G = nx.erdos_renyi_graph(220, 0.05, seed=0)
    nx.config.backend_priority = ["rustworkx"]
    try:
        nx.betweenness_centrality(G)
    finally:
        nx.config.backend_priority = []
    assert called.get("yes") is True
