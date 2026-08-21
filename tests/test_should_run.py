"""should_run skips graphs where conversion would lose."""

from __future__ import annotations

import networkx as nx

from nx_rustworkx.algorithms._utils import MIN_EDGES, MIN_NODES
from nx_rustworkx.interface import BackendInterface


def test_should_run_skips_tiny_graphs():
    G = nx.complete_graph(10)
    result = BackendInterface.should_run("betweenness_centrality", (G,), {})
    assert result is not True
    assert "too small" in str(result)


def test_should_run_skips_sparse_large_n():
    G = nx.gnp_random_graph(250, 0.002, seed=0)
    assert G.number_of_nodes() >= MIN_NODES
    assert G.number_of_edges() < MIN_EDGES
    result = BackendInterface.should_run("betweenness_centrality", (G,), {})
    assert result is not True


def test_should_run_accepts_large_enough_graphs():
    G = nx.gnp_random_graph(250, 0.02, seed=0)
    assert G.number_of_nodes() >= MIN_NODES
    assert G.number_of_edges() >= MIN_EDGES
    assert BackendInterface.should_run("betweenness_centrality", (G,), {}) is True


def test_can_run_rejects_multigraph():
    G = nx.MultiGraph([(0, 1), (0, 1)])
    result = BackendInterface.can_run("betweenness_centrality", (G,), {})
    assert result is not True
    assert "MultiGraph" in str(result)


def test_can_run_rejects_weighted_betweenness():
    G = nx.path_graph(5)
    result = BackendInterface.can_run(
        "betweenness_centrality",
        (G,),
        {"weight": "weight"},
    )
    assert result is not True


def test_can_run_rejects_k_sample():
    G = nx.path_graph(5)
    result = BackendInterface.can_run("betweenness_centrality", (G,), {"k": 2})
    assert result is not True


def test_can_run_rejects_weight_callable():
    G = nx.path_graph(5)
    result = BackendInterface.can_run(
        "shortest_path",
        (G,),
        {"weight": lambda u, v, d: 1},
    )
    assert result is not True


def test_priority_falls_back_on_tiny_graphs():
    G = nx.complete_graph(8)
    # should_run is consulted only for automatic conversion, not backend=.
    nx.config.backend_priority = ["rustworkx"]
    try:
        result = nx.betweenness_centrality(G)
    finally:
        nx.config.backend_priority = []
    expected = nx.betweenness_centrality.orig_func(G)
    assert result == expected
