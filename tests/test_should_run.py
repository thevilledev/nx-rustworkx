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
    # core_number never accepts multigraphs: NetworkX itself raises for them.
    G = nx.MultiGraph([(0, 1), (0, 1)])
    result = BackendInterface.can_run("core_number", (G,), {})
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


def test_no_auto_dispatch_functions_decline_automatic_selection():
    """Functions measured slower than NetworkX must not be chosen automatically."""
    import inspect

    from nx_rustworkx.algorithms._utils import NO_AUTO_DISPATCH

    G = nx.gnp_random_graph(400, 0.05, seed=0, directed=True)
    stand_ins = {"source": 0, "target": 3, "n": 0, "distance": 1, "S": [0, 1]}
    for name in NO_AUTO_DISPATCH:
        reference = getattr(nx, name).orig_func
        args = [
            stand_ins[p.name]
            for p in list(inspect.signature(reference).parameters.values())[1:]
            if p.default is inspect.Parameter.empty and p.name in stand_ins
        ]
        assert BackendInterface.should_run(name, (G, *args), {}) is not True, name
        # can_run must still accept them, so backend="rustworkx" keeps working.
        assert BackendInterface.can_run(name, (G, *args), {}) is not False, name


def test_explicit_backend_still_runs_declined_functions():
    G = nx.gnp_random_graph(300, 0.05, seed=0)
    got = nx.degree_centrality(G, backend="rustworkx")
    expected = nx.degree_centrality.orig_func(G)
    # The backend applies NetworkX's own formula, so the values are bit-identical.
    assert got == expected
    assert nx.has_path(G, 0, 5, backend="rustworkx") == nx.has_path.orig_func(G, 0, 5)


def test_backend_priority_skips_declined_functions():
    G = nx.gnp_random_graph(300, 0.05, seed=0)
    nx.config.backend_priority = ["rustworkx"]
    try:
        assert nx.degree_centrality(G) == nx.degree_centrality.orig_func(G)
        assert nx.complement(G).number_of_edges() == nx.complement.orig_func(G).number_of_edges()
    finally:
        nx.config.backend_priority = []


def test_shortest_path_declines_where_networkx_wins():
    G = nx.gnp_random_graph(400, 0.05, seed=0)
    # An unweighted single pair goes to NetworkX's bidirectional search.
    assert (
        BackendInterface.should_run("shortest_path", (G,), {"source": 0, "target": 9}) is not True
    )
    assert (
        BackendInterface.should_run("shortest_path_length", (G,), {"source": 0, "target": 9})
        is not True
    )
    # Unweighted paths are cheaper to build in NetworkX than to remap.
    assert BackendInterface.should_run("shortest_path", (G,), {"source": 0}) is not True
    # A weighted pair loses too: the single-source paths kernel materializes a
    # path per visited node, which NetworkX's bidirectional Dijkstra never has
    # to do (measured in benches/bench_single_pair.py).
    weighted_pair = {"source": 0, "target": 9, "weight": "weight"}
    result = BackendInterface.should_run("shortest_path", (G,), weighted_pair)
    assert result is not True
    assert "bidirectional Dijkstra" in str(result)
    # Forced dispatch must remain possible.
    assert BackendInterface.can_run("shortest_path", (G,), weighted_pair) is True
    # The goal-stopped lengths kernel has no path to materialize and measures
    # faster than NetworkX on every benchmarked shape, so it keeps dispatching,
    # as do the source-only and all-pairs weighted forms of shortest_path.
    assert BackendInterface.should_run("shortest_path_length", (G,), weighted_pair) is True
    assert BackendInterface.should_run("shortest_path", (G,), {"weight": "weight"}) is True
    # Weighted paths and any lengths are worth converting for.
    assert (
        BackendInterface.should_run("shortest_path", (G,), {"source": 0, "weight": "weight"})
        is True
    )
    assert BackendInterface.should_run("shortest_path_length", (G,), {}) is True


def test_closeness_centrality_declines_single_node_requests():
    import pytest

    G = nx.gnp_random_graph(400, 0.05, seed=0)
    assert BackendInterface.should_run("closeness_centrality", (G,), {"u": 0}) is not True
    assert BackendInterface.should_run("closeness_centrality", (G,), {}) is True
    # backend="rustworkx" still answers, and with NetworkX's value.
    got = nx.closeness_centrality(G, u=0, backend="rustworkx")
    assert got == pytest.approx(nx.closeness_centrality.orig_func(G, u=0))
