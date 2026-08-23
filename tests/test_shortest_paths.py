"""Shortest-path parity against NetworkX."""

from __future__ import annotations

import math

import networkx as nx
import pytest


def _weighted_undirected(n=40, p=0.15, seed=7):
    G = nx.gnp_random_graph(n, p, seed=seed)
    for u, v in G.edges():
        G[u][v]["weight"] = 1 + ((u * 7 + v * 13) % 9)
    return G


def _weighted_directed(n=40, p=0.12, seed=11):
    G = nx.gnp_random_graph(n, p, seed=seed, directed=True)
    for u, v in G.edges():
        G[u][v]["weight"] = 1 + ((u * 5 + v * 3) % 7)
    return G


GRAPHS = [_weighted_undirected(), _weighted_directed()]


def _assert_length_maps(got, expected):
    assert set(got) == set(expected)
    for node, value in expected.items():
        assert got[node] == pytest.approx(value)


def _assert_paths_valid(G, source, got, expected, weight):
    """Paths may differ among ties; their costs must not."""
    assert set(got) == set(expected)
    for target, path in got.items():
        assert path[0] == source and path[-1] == target
        assert _cost(G, path, weight) == pytest.approx(_cost(G, expected[target], weight))


def _cost(G, path, weight):
    if weight is None:
        return len(path) - 1
    return sum(G[u][v].get(weight, 1) for u, v in zip(path, path[1:]))


@pytest.mark.parametrize("G", GRAPHS)
def test_single_source_dijkstra_variants(G):
    source = 0
    _assert_length_maps(
        nx.single_source_dijkstra_path_length(G, source, backend="rustworkx"),
        nx.single_source_dijkstra_path_length.orig_func(G, source),
    )
    _assert_paths_valid(
        G,
        source,
        nx.single_source_dijkstra_path(G, source, backend="rustworkx"),
        nx.single_source_dijkstra_path.orig_func(G, source),
        "weight",
    )


@pytest.mark.parametrize("G", GRAPHS)
def test_single_source_bellman_ford_variants(G):
    source = 0
    _assert_length_maps(
        nx.single_source_bellman_ford_path_length(G, source, backend="rustworkx"),
        nx.single_source_bellman_ford_path_length.orig_func(G, source),
    )
    lengths, paths = nx.single_source_bellman_ford(G, source, backend="rustworkx")
    e_lengths, e_paths = nx.single_source_bellman_ford.orig_func(G, source)
    _assert_length_maps(lengths, e_lengths)
    _assert_paths_valid(G, source, paths, e_paths, "weight")
    length, path = nx.single_source_bellman_ford(G, source, target=1, backend="rustworkx")
    assert path[0] == source and path[-1] == 1
    assert length == pytest.approx(nx.bellman_ford_path_length.orig_func(G, source, 1))


@pytest.mark.parametrize("G", GRAPHS)
def test_unweighted_single_source(G):
    source = 0
    got = nx.single_source_shortest_path_length(G, source, backend="rustworkx")
    expected = nx.single_source_shortest_path_length.orig_func(G, source)
    _assert_length_maps(got, expected)
    assert all(isinstance(v, int) for v in got.values())
    _assert_paths_valid(
        G,
        source,
        nx.single_source_shortest_path(G, source, backend="rustworkx"),
        nx.single_source_shortest_path.orig_func(G, source),
        None,
    )


@pytest.mark.parametrize("G", GRAPHS)
def test_single_target_variants(G):
    target = 0
    got = nx.single_target_shortest_path_length(G, target, backend="rustworkx")
    reference = nx.single_target_shortest_path_length.orig_func(G, target)
    # NetworkX 3.5 changed this from an iterator of pairs to a dict; the backend
    # has to return whichever shape the installed NetworkX returns.
    assert isinstance(got, dict) == isinstance(reference, dict)
    _assert_length_maps(dict(got), dict(reference))
    paths = nx.single_target_shortest_path(G, target, backend="rustworkx")
    e_paths = nx.single_target_shortest_path.orig_func(G, target)
    assert set(paths) == set(e_paths)
    for source, path in paths.items():
        assert path[0] == source and path[-1] == target
        assert len(path) == len(e_paths[source])


@pytest.mark.parametrize("G", GRAPHS)
def test_all_pairs_variants(G):
    got = dict(nx.all_pairs_dijkstra_path_length(G, backend="rustworkx"))
    expected = dict(nx.all_pairs_dijkstra_path_length.orig_func(G))
    assert set(got) == set(expected)
    for source in expected:
        _assert_length_maps(got[source], expected[source])

    got = dict(nx.all_pairs_bellman_ford_path_length(G, backend="rustworkx"))
    expected = dict(nx.all_pairs_bellman_ford_path_length.orig_func(G))
    for source in expected:
        _assert_length_maps(got[source], expected[source])

    got = dict(nx.all_pairs_shortest_path_length(G, backend="rustworkx"))
    expected = dict(nx.all_pairs_shortest_path_length.orig_func(G))
    for source in expected:
        _assert_length_maps(got[source], expected[source])

    got = dict(nx.all_pairs_dijkstra_path(G, backend="rustworkx"))
    expected = dict(nx.all_pairs_dijkstra_path.orig_func(G))
    for source in expected:
        _assert_paths_valid(G, source, got[source], expected[source], "weight")


@pytest.mark.parametrize("G", GRAPHS)
def test_all_pairs_dijkstra_pairs(G):
    got = dict(nx.all_pairs_dijkstra(G, backend="rustworkx"))
    expected = dict(nx.all_pairs_dijkstra.orig_func(G))
    assert set(got) == set(expected)
    for source in expected:
        _assert_length_maps(got[source][0], expected[source][0])
        _assert_paths_valid(G, source, got[source][1], expected[source][1], "weight")


@pytest.mark.parametrize("G", GRAPHS)
def test_point_to_point_lengths(G):
    reachable = nx.single_source_dijkstra_path_length.orig_func(G, 0)
    target = max(reachable, key=reachable.get)
    assert nx.dijkstra_path_length(G, 0, target, backend="rustworkx") == pytest.approx(
        nx.dijkstra_path_length.orig_func(G, 0, target)
    )
    assert nx.bellman_ford_path_length(G, 0, target, backend="rustworkx") == pytest.approx(
        nx.bellman_ford_path_length.orig_func(G, 0, target)
    )
    path = nx.bidirectional_shortest_path(G, 0, target, backend="rustworkx")
    assert len(path) == len(nx.bidirectional_shortest_path.orig_func(G, 0, target))


@pytest.mark.parametrize("G", GRAPHS)
def test_point_to_point_paths(G):
    """The single-pair branch hands the target to the kernel; results must not change."""
    reachable = nx.single_source_dijkstra_path_length.orig_func(G, 0)
    target = max(reachable, key=reachable.get)
    for func in (nx.dijkstra_path, nx.bellman_ford_path):
        got = func(G, 0, target, backend="rustworkx")
        assert got[0] == 0 and got[-1] == target
        assert _cost(G, got, "weight") == pytest.approx(
            _cost(G, func.orig_func(G, 0, target), "weight")
        )
    length, path = nx.single_source_dijkstra(G, 0, target=target, backend="rustworkx")
    assert path[0] == 0 and path[-1] == target
    assert length == pytest.approx(nx.dijkstra_path_length.orig_func(G, 0, target))
    length, path = nx.single_source_bellman_ford(G, 0, target=target, backend="rustworkx")
    assert path[0] == 0 and path[-1] == target
    assert length == pytest.approx(nx.bellman_ford_path_length.orig_func(G, 0, target))


def test_point_to_point_no_path_raises():
    G = nx.Graph([(0, 1), (2, 3)])
    for u, v in G.edges():
        G[u][v]["weight"] = 1
    with pytest.raises(nx.NetworkXNoPath):
        nx.dijkstra_path(G, 0, 3, backend="rustworkx")
    with pytest.raises(nx.NetworkXNoPath):
        nx.shortest_path_length(G, source=0, target=3, weight="weight", backend="rustworkx")
    with pytest.raises(nx.NetworkXNoPath):
        nx.single_source_bellman_ford(G, 0, target=3, backend="rustworkx")


def test_single_pair_negative_cycle_raises():
    D = nx.DiGraph()
    D.add_weighted_edges_from([(0, 1, 1), (1, 2, -3), (2, 0, 1), (0, 3, 1)])
    with pytest.raises(nx.NetworkXUnbounded):
        nx.bellman_ford_path(D, 0, 3, backend="rustworkx")
    with pytest.raises(nx.NetworkXUnbounded):
        nx.single_source_bellman_ford(D, 0, target=3, backend="rustworkx")


@pytest.mark.parametrize("G", GRAPHS)
def test_all_shortest_paths_matches(G):
    reachable = nx.single_source_shortest_path_length.orig_func(G, 0)
    target = max(reachable, key=reachable.get)
    got = sorted(nx.all_shortest_paths(G, 0, target, backend="rustworkx"))
    expected = sorted(nx.all_shortest_paths.orig_func(G, 0, target))
    assert got == expected


@pytest.mark.parametrize("G", GRAPHS)
def test_astar_matches(G):
    reachable = nx.single_source_dijkstra_path_length.orig_func(G, 0)
    target = max(reachable, key=reachable.get)
    got = nx.astar_path(G, 0, target, backend="rustworkx")
    assert _cost(G, got, "weight") == pytest.approx(
        _cost(G, nx.astar_path.orig_func(G, 0, target), "weight")
    )
    assert nx.astar_path_length(G, 0, target, backend="rustworkx") == pytest.approx(
        nx.astar_path_length.orig_func(G, 0, target)
    )


def test_astar_with_heuristic():
    G = nx.grid_2d_graph(8, 8)
    for u, v in G.edges():
        G[u][v]["weight"] = 1

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    got = nx.astar_path(G, (0, 0), (7, 7), heuristic=heuristic, backend="rustworkx")
    assert got[0] == (0, 0) and got[-1] == (7, 7)
    assert len(got) == len(nx.astar_path.orig_func(G, (0, 0), (7, 7), heuristic=heuristic))


def test_astar_no_path_raises():
    G = nx.Graph([(0, 1), (2, 3)])
    with pytest.raises(nx.NetworkXNoPath):
        nx.astar_path(G, 0, 3, backend="rustworkx")


@pytest.mark.parametrize("G", GRAPHS)
def test_has_path_matches(G):
    for target in list(G)[:10]:
        assert nx.has_path(G, 0, target, backend="rustworkx") == nx.has_path.orig_func(G, 0, target)


def test_has_path_disconnected():
    G = nx.Graph([(0, 1), (2, 3)])
    assert nx.has_path(G, 0, 3, backend="rustworkx") is False
    assert nx.has_path(G, 0, 1, backend="rustworkx") is True


@pytest.mark.parametrize("G", GRAPHS)
def test_floyd_warshall_matches(G):
    got = nx.floyd_warshall(G, backend="rustworkx")
    expected = nx.floyd_warshall.orig_func(G)
    assert set(got) == set(expected)
    for u in expected:
        for v in expected:
            assert got[u][v] == pytest.approx(expected[u][v])


def test_floyd_warshall_reports_infinity_for_unreachable():
    G = nx.Graph([(0, 1)])
    G.add_node(9)
    dist = nx.floyd_warshall(G, backend="rustworkx")
    assert dist[0][9] == math.inf
    assert dist[0][0] == 0


@pytest.mark.parametrize("G", GRAPHS)
def test_floyd_warshall_numpy_matches(G):
    import numpy as np

    got = nx.floyd_warshall_numpy(G, backend="rustworkx")
    expected = nx.floyd_warshall_numpy.orig_func(G)
    assert np.allclose(got, expected)


@pytest.mark.parametrize("G", GRAPHS)
def test_floyd_warshall_predecessor_and_distance(G):
    pred, dist = nx.floyd_warshall_predecessor_and_distance(G, backend="rustworkx")
    e_pred, e_dist = nx.floyd_warshall_predecessor_and_distance.orig_func(G)
    for u in G:
        for v in G:
            assert dist[u][v] == pytest.approx(e_dist[u][v])
    # Predecessors may differ among ties, but must rebuild a shortest path.
    assert set(pred) == set(e_pred)
    for u, row in pred.items():
        for v, p in row.items():
            assert dist[u][p] + _edge_weight(G, p, v) == pytest.approx(dist[u][v])


def _edge_weight(G, u, v):
    return G[u][v].get("weight", 1)


def test_negative_edge_cycle_matches():
    D = nx.DiGraph()
    D.add_weighted_edges_from([(0, 1, 1), (1, 2, -3), (2, 0, 1), (3, 4, 2)])
    assert nx.negative_edge_cycle(D, backend="rustworkx") is True
    P = nx.DiGraph()
    P.add_weighted_edges_from([(0, 1, 1), (1, 2, 2), (2, 0, 3)])
    assert nx.negative_edge_cycle(P, backend="rustworkx") is False


def test_find_negative_cycle_returns_negative_cycle():
    D = nx.DiGraph()
    D.add_weighted_edges_from([(0, 1, 1), (1, 2, -3), (2, 0, 1), (3, 4, 2)])
    cycle = nx.find_negative_cycle(D, 0, backend="rustworkx")
    assert cycle[0] == cycle[-1]
    total = sum(D[u][v]["weight"] for u, v in zip(cycle, cycle[1:]))
    assert total < 0


def test_average_shortest_path_length_matches():
    G = nx.karate_club_graph()
    assert nx.average_shortest_path_length(G, backend="rustworkx") == pytest.approx(
        nx.average_shortest_path_length.orig_func(G)
    )


def test_average_shortest_path_length_disconnected_raises():
    G = nx.Graph([(0, 1), (2, 3)])
    with pytest.raises(nx.NetworkXError):
        nx.average_shortest_path_length(G, backend="rustworkx")


def test_cutoff_falls_back_to_networkx():
    from nx_rustworkx.interface import BackendInterface

    G = nx.path_graph(5)
    assert (
        BackendInterface.can_run("single_source_shortest_path_length", (G, 0), {"cutoff": 2})
        is not True
    )


@pytest.mark.parametrize("G", GRAPHS)
def test_single_source_all_shortest_paths_matches(G):
    got = {
        t: sorted(ps) for t, ps in nx.single_source_all_shortest_paths(G, 0, backend="rustworkx")
    }
    expected = {t: sorted(ps) for t, ps in nx.single_source_all_shortest_paths.orig_func(G, 0)}
    assert got == expected


def test_single_source_all_shortest_paths_weighted_ties():
    G = nx.Graph([(0, 1), (0, 2), (1, 3), (2, 3)])
    for u, v in G.edges():
        G[u][v]["weight"] = 1
    got = {
        t: sorted(ps)
        for t, ps in nx.single_source_all_shortest_paths(G, 0, weight="weight", backend="rustworkx")
    }
    expected = {
        t: sorted(ps)
        for t, ps in nx.single_source_all_shortest_paths.orig_func(G, 0, weight="weight")
    }
    assert got == expected


def test_floyd_warshall_rows_default_to_inf():
    G = nx.path_graph(5)
    got = nx.floyd_warshall(G, backend="rustworkx")
    expected = nx.floyd_warshall.orig_func(G)
    assert {u: dict(row) for u, row in got.items()} == {u: dict(row) for u, row in expected.items()}
    # NetworkX hands back defaultdict rows; unknown keys read as inf.
    assert got[0]["not-a-node"] == math.inf
