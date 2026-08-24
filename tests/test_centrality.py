"""Centrality parity against NetworkX."""

from __future__ import annotations

import networkx as nx
import pytest

APPROX = {"rel": 1e-9, "abs": 1e-12}


def _undirected():
    return nx.karate_club_graph()


def _directed():
    return nx.gnp_random_graph(40, 0.15, seed=3, directed=True)


def _undirected_with_self_loops():
    G = _undirected()
    G.add_edges_from([(0, 0), (5, 5)])
    return G


def _directed_with_self_loops():
    G = _directed()
    G.add_edges_from([(0, 0), (7, 7)])
    return G


def _assert_scores_match(got, expected, **tol):
    tol = tol or APPROX
    assert set(got) == set(expected)
    for node, value in expected.items():
        assert got[node] == pytest.approx(value, **tol)


@pytest.mark.parametrize("graph", [_undirected(), _directed()])
def test_degree_centrality_matches(graph):
    _assert_scores_match(
        nx.degree_centrality(graph, backend="rustworkx"),
        nx.degree_centrality.orig_func(graph),
    )


def test_in_out_degree_centrality_matches():
    G = _directed()
    _assert_scores_match(
        nx.in_degree_centrality(G, backend="rustworkx"),
        nx.in_degree_centrality.orig_func(G),
    )
    _assert_scores_match(
        nx.out_degree_centrality(G, backend="rustworkx"),
        nx.out_degree_centrality.orig_func(G),
    )


@pytest.mark.parametrize("graph", [_undirected_with_self_loops(), _directed_with_self_loops()])
def test_degree_centrality_counts_self_loops_twice(graph):
    expected = nx.degree_centrality.orig_func(graph)
    got = nx.degree_centrality(graph, backend="rustworkx")
    _assert_scores_match(got, expected)
    assert got == expected  # bit-identical, not merely close


def test_degree_centrality_self_loop_reported_case():
    G = nx.Graph([(0, 1), (1, 1), (1, 2)])
    assert nx.degree_centrality(G, backend="rustworkx") == {0: 0.5, 1: 2.0, 2: 0.5}
    D = nx.DiGraph([(0, 1), (1, 1), (1, 2)])
    assert nx.degree_centrality(D, backend="rustworkx") == {0: 0.5, 1: 2.0, 2: 0.5}


def test_in_out_degree_centrality_with_self_loops():
    G = _directed_with_self_loops()
    for fn in (nx.in_degree_centrality, nx.out_degree_centrality):
        expected = fn.orig_func(G)
        got = fn(G, backend="rustworkx")
        _assert_scores_match(got, expected)
        assert got == expected


def test_in_degree_centrality_rejects_undirected():
    G = _undirected()
    with pytest.raises(nx.NetworkXNotImplemented):
        nx.in_degree_centrality(G, backend="rustworkx")


@pytest.mark.parametrize("graph", [_undirected(), _directed()])
def test_katz_centrality_matches(graph):
    _assert_scores_match(
        nx.katz_centrality(graph, alpha=0.05, tol=1e-12, max_iter=5000, backend="rustworkx"),
        nx.katz_centrality.orig_func(graph, alpha=0.05, tol=1e-12, max_iter=5000),
        rel=1e-7,
        abs=1e-9,
    )


def test_katz_centrality_beta_dict():
    G = _undirected()
    beta = {n: 1.0 + (n % 3) for n in G}
    _assert_scores_match(
        nx.katz_centrality(G, alpha=0.05, beta=beta, tol=1e-12, max_iter=5000, backend="rustworkx"),
        nx.katz_centrality.orig_func(G, alpha=0.05, beta=beta, tol=1e-12, max_iter=5000),
        rel=1e-7,
        abs=1e-9,
    )


def test_katz_centrality_numpy_matches():
    G = _undirected()
    _assert_scores_match(
        nx.katz_centrality_numpy(G, alpha=0.05, backend="rustworkx"),
        nx.katz_centrality_numpy.orig_func(G, alpha=0.05),
        rel=1e-7,
        abs=1e-9,
    )


def test_katz_rejects_unsupported_arguments():
    G = nx.path_graph(5)
    from nx_rustworkx.interface import BackendInterface

    assert BackendInterface.can_run("katz_centrality", (G,), {"nstart": {0: 1}}) is not True
    assert BackendInterface.can_run("katz_centrality", (G,), {"normalized": False}) is not True


@pytest.mark.parametrize("graph", [_undirected(), _directed()])
def test_hits_matches(graph):
    hubs, auth = nx.hits(graph, tol=1e-12, max_iter=2000, backend="rustworkx")
    e_hubs, e_auth = nx.hits.orig_func(graph, tol=1e-12, max_iter=2000)
    _assert_scores_match(hubs, e_hubs, rel=1e-6, abs=1e-9)
    _assert_scores_match(auth, e_auth, rel=1e-6, abs=1e-9)


def test_group_centrality_single_group():
    G = _undirected()
    group = [0, 1, 2]
    assert nx.group_betweenness_centrality(G, group, backend="rustworkx") == pytest.approx(
        nx.group_betweenness_centrality.orig_func(G, group)
    )
    assert nx.group_closeness_centrality(G, group, backend="rustworkx") == pytest.approx(
        nx.group_closeness_centrality.orig_func(G, group)
    )
    assert nx.group_degree_centrality(G, group, backend="rustworkx") == pytest.approx(
        nx.group_degree_centrality.orig_func(G, group)
    )


def test_group_betweenness_many_groups():
    G = _undirected()
    groups = [[0, 1], [2, 3, 4]]
    got = nx.group_betweenness_centrality(G, groups, backend="rustworkx")
    expected = nx.group_betweenness_centrality.orig_func(G, groups)
    assert len(got) == len(expected)
    for a, b in zip(got, expected):
        assert a == pytest.approx(b)


def test_group_centralities_accept_one_shot_iterators():
    # A generator group must survive both the membership check and the mapping.
    G = _undirected()
    group = [0, 1, 2]
    assert nx.group_closeness_centrality(G, iter(group), backend="rustworkx") == pytest.approx(
        nx.group_closeness_centrality.orig_func(G, group)
    )
    assert nx.group_degree_centrality(G, iter(group), backend="rustworkx") == pytest.approx(
        nx.group_degree_centrality.orig_func(G, group)
    )


def test_group_centrality_unknown_node_raises():
    G = _undirected()
    with pytest.raises(nx.NodeNotFound):
        nx.group_degree_centrality(G, [0, "missing"], backend="rustworkx")
