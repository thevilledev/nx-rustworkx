"""Matching, coloring, tree, operator and simple-path parity."""

from __future__ import annotations

import networkx as nx
import pytest


def _weighted(seed=3, n=24, p=0.2):
    G = nx.gnp_random_graph(n, p, seed=seed)
    for u, v in G.edges():
        G[u][v]["weight"] = 1 + ((u * 5 + v * 3) % 9)
    return G


def _total_weight(G, edges):
    return sum(G[u][v].get("weight", 1) for u, v in edges)


@pytest.mark.parametrize("seed", [1, 3, 5])
def test_minimum_spanning_tree_matches(seed):
    G = _weighted(seed=seed)
    G.add_node("lonely", color="red")
    got = nx.minimum_spanning_tree(G, backend="rustworkx")
    expected = nx.minimum_spanning_tree.orig_func(G)
    assert set(got.nodes) == set(expected.nodes)
    assert got.number_of_edges() == expected.number_of_edges()
    assert _total_weight(G, got.edges()) == _total_weight(G, expected.edges())
    assert got.nodes["lonely"] == {"color": "red"}
    for u, v, data in got.edges(data=True):
        assert data == G[u][v]


def test_minimum_spanning_edges_matches():
    G = _weighted()
    got = list(nx.minimum_spanning_edges(G, backend="rustworkx"))
    expected = list(nx.minimum_spanning_edges.orig_func(G))
    # Minimum spanning forests are not unique when weights tie, so compare the
    # total weight and the spanning property rather than the exact edge set.
    assert len(got) == len(expected)
    assert _total_weight(G, [(u, v) for u, v, _ in got]) == _total_weight(
        G, [(u, v) for u, v, _ in expected]
    )
    forest = nx.Graph()
    forest.add_nodes_from(G)
    forest.add_edges_from((u, v) for u, v, _ in got)
    assert nx.number_connected_components.orig_func(forest) == (
        nx.number_connected_components.orig_func(G)
    )
    assert all(data == G[u][v] for u, v, data in got)
    no_data = list(nx.minimum_spanning_edges(G, data=False, backend="rustworkx"))
    assert all(len(edge) == 2 for edge in no_data)


def test_minimum_spanning_tree_on_forest():
    G = nx.Graph()
    G.add_weighted_edges_from([(0, 1, 1), (1, 2, 2), (5, 6, 3)])
    got = nx.minimum_spanning_tree(G, backend="rustworkx")
    expected = nx.minimum_spanning_tree.orig_func(G)
    assert set(got.edges) == set(expected.edges)


def test_steiner_tree_spans_terminals():
    G = _weighted(seed=7)
    terminals = [0, 5, 11]
    got = nx.approximation.steiner_tree(G, terminals, backend="rustworkx")
    expected = nx.approximation.steiner_tree.orig_func(G, terminals)
    assert set(terminals) <= set(got.nodes)
    assert nx.is_connected(nx.Graph(got))
    assert _total_weight(G, got.edges()) <= _total_weight(G, expected.edges()) * 2


@pytest.mark.parametrize("seed", [0, 2, 4])
def test_max_weight_matching_matches(seed):
    G = _weighted(seed=seed, n=16, p=0.3)
    got = nx.max_weight_matching(G, backend="rustworkx")
    expected = nx.max_weight_matching.orig_func(G)
    assert len(got) == len(expected)
    assert _total_weight(G, got) == _total_weight(G, expected)
    seen = set()
    for u, v in got:
        assert G.has_edge(u, v)
        assert u not in seen and v not in seen
        seen.update((u, v))


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_greedy_color_matches_largest_first(seed):
    G = nx.gnp_random_graph(25, 0.25, seed=seed)
    got = nx.greedy_color(G, backend="rustworkx")
    assert got == nx.greedy_color.orig_func(G)
    assert all(got[u] != got[v] for u, v in G.edges())


def test_greedy_color_rejects_other_strategies():
    from nx_rustworkx.interface import BackendInterface

    G = nx.path_graph(5)
    assert BackendInterface.can_run("greedy_color", (G, "random_sequential"), {}) is not True
    assert BackendInterface.can_run("greedy_color", (G, "largest_first", True), {}) is not True


@pytest.mark.parametrize(
    "G",
    [nx.gnp_random_graph(20, 0.2, seed=6), nx.gnp_random_graph(15, 0.2, seed=6, directed=True)],
)
def test_complement_matches(G):
    got = nx.complement(G, backend="rustworkx")
    expected = nx.complement.orig_func(G)
    assert set(got.nodes) == set(expected.nodes)
    assert {frozenset((u, v)) for u, v in got.edges()} == {
        frozenset((u, v)) for u, v in expected.edges()
    }
    assert got.is_directed() == expected.is_directed()


@pytest.mark.parametrize("kernel", ["cartesian_product", "tensor_product"])
def test_products_match(kernel):
    G = nx.path_graph(4)
    H = nx.cycle_graph(3)
    got = getattr(nx, kernel)(G, H, backend="rustworkx")
    expected = getattr(nx, kernel).orig_func(G, H)
    assert set(got.nodes) == set(expected.nodes)
    assert {frozenset((u, v)) for u, v in got.edges()} == {
        frozenset((u, v)) for u, v in expected.edges()
    }


@pytest.mark.parametrize(
    "G",
    [
        nx.gnp_random_graph(12, 0.25, seed=2),
        nx.gnp_random_graph(12, 0.2, seed=2, directed=True),
    ],
)
def test_all_simple_paths_matches(G):
    nodes = list(G)
    source, target = nodes[0], nodes[-1]
    got = sorted(nx.all_simple_paths(G, source, target, backend="rustworkx"))
    expected = sorted(nx.all_simple_paths.orig_func(G, source, target))
    assert got == expected


def test_all_simple_paths_cutoff_matches():
    G = nx.gnp_random_graph(12, 0.25, seed=2)
    for cutoff in (1, 2, 3, 4):
        got = sorted(nx.all_simple_paths(G, 0, 11, cutoff=cutoff, backend="rustworkx"))
        expected = sorted(nx.all_simple_paths.orig_func(G, 0, 11, cutoff=cutoff))
        assert got == expected, cutoff


def test_vf2pp_is_isomorphic_matches():
    G = nx.gnp_random_graph(30, 0.2, seed=9)
    H = nx.relabel_nodes(G, {n: n + 100 for n in G})
    assert nx.vf2pp_is_isomorphic(G, H, backend="rustworkx") is True
    assert nx.vf2pp_is_isomorphic(G, nx.path_graph(30), backend="rustworkx") is False
