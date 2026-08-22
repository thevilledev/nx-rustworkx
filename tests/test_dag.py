"""DAG and traversal parity against NetworkX."""

from __future__ import annotations

import random

import networkx as nx
import pytest


def random_dag(n=25, p=0.15, seed=1, weighted=False):
    rng = random.Random(seed)
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < p:
                G.add_edge(u, v, **({"weight": 1 + ((u * 3 + v) % 5)} if weighted else {}))
    return G


DAGS = [random_dag(seed=1), random_dag(seed=2), random_dag(seed=3, weighted=True)]


def _path_cost(G, path, weight="weight", default=1):
    return sum(G[u][v].get(weight, default) for u, v in zip(path, path[1:]))


@pytest.mark.parametrize("G", DAGS)
def test_is_directed_acyclic_graph(G):
    assert nx.is_directed_acyclic_graph(G, backend="rustworkx") is True


def test_is_dag_false_for_cycle_and_undirected():
    C = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    assert nx.is_directed_acyclic_graph(C, backend="rustworkx") is False
    assert nx.is_directed_acyclic_graph(nx.path_graph(4), backend="rustworkx") is False


@pytest.mark.parametrize("G", DAGS)
def test_topological_sort_is_valid(G):
    order = list(nx.topological_sort(G, backend="rustworkx"))
    assert sorted(order) == sorted(G)
    position = {node: i for i, node in enumerate(order)}
    assert all(position[u] < position[v] for u, v in G.edges())


def test_topological_sort_rejects_cycles():
    C = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    with pytest.raises(nx.NetworkXUnfeasible):
        list(nx.topological_sort(C, backend="rustworkx"))


@pytest.mark.parametrize("G", DAGS)
def test_topological_generations_match_as_sets(G):
    got = [set(layer) for layer in nx.topological_generations(G, backend="rustworkx")]
    expected = [set(layer) for layer in nx.topological_generations.orig_func(G)]
    assert got == expected


@pytest.mark.parametrize("G", DAGS)
def test_ancestors_and_descendants(G):
    for node in list(G)[:8]:
        assert nx.ancestors(G, node, backend="rustworkx") == nx.ancestors.orig_func(G, node)
        assert nx.descendants(G, node, backend="rustworkx") == nx.descendants.orig_func(G, node)


def test_ancestors_on_undirected():
    G = nx.Graph([(0, 1), (1, 2), (3, 4)])
    assert nx.ancestors(G, 0, backend="rustworkx") == nx.ancestors.orig_func(G, 0)
    assert nx.descendants(G, 3, backend="rustworkx") == nx.descendants.orig_func(G, 3)


def test_ancestors_unknown_node_raises():
    G = nx.DiGraph([(0, 1)])
    with pytest.raises(nx.NetworkXError):
        nx.ancestors(G, 99, backend="rustworkx")


@pytest.mark.parametrize("G", DAGS)
def test_descendants_at_distance(G):
    for distance in range(4):
        assert nx.descendants_at_distance(
            G, 0, distance, backend="rustworkx"
        ) == nx.descendants_at_distance.orig_func(G, 0, distance)


@pytest.mark.parametrize("G", DAGS)
def test_dag_longest_path_is_a_longest_path(G):
    got = nx.dag_longest_path(G, backend="rustworkx")
    expected = nx.dag_longest_path.orig_func(G)
    assert _path_cost(G, got) == _path_cost(G, expected)
    assert all(G.has_edge(u, v) for u, v in zip(got, got[1:]))
    assert nx.dag_longest_path_length(G, backend="rustworkx") == pytest.approx(
        nx.dag_longest_path_length.orig_func(G)
    )


def test_dag_longest_path_respects_weights():
    G = nx.DiGraph()
    G.add_weighted_edges_from([(0, 1, 1), (1, 3, 1), (0, 2, 10), (2, 3, 10)])
    assert nx.dag_longest_path(G, backend="rustworkx") == [0, 2, 3]
    assert nx.dag_longest_path_length(G, backend="rustworkx") == 20


@pytest.mark.parametrize("G", DAGS)
def test_transitive_reduction_matches(G):
    got = nx.transitive_reduction(G, backend="rustworkx")
    expected = nx.transitive_reduction.orig_func(G)
    assert set(got.nodes) == set(expected.nodes)
    assert set(got.edges) == set(expected.edges)


def test_transitive_reduction_rejects_cycles():
    C = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    with pytest.raises(nx.NetworkXError):
        nx.transitive_reduction(C, backend="rustworkx")


@pytest.mark.parametrize("G", DAGS)
def test_dominators_match(G):
    assert nx.immediate_dominators(G, 0, backend="rustworkx") == (
        nx.immediate_dominators.orig_func(G, 0)
    )


def test_dominators_with_unreachable_nodes():
    G = nx.DiGraph([("a", "b"), ("b", "c")])
    G.add_edge("x", "y")
    assert nx.immediate_dominators(G, "a", backend="rustworkx") == (
        nx.immediate_dominators.orig_func(G, "a")
    )


@pytest.mark.parametrize(
    "G",
    [
        nx.gnp_random_graph(30, 0.12, seed=4),
        nx.gnp_random_graph(30, 0.10, seed=8, directed=True),
    ],
)
def test_dfs_edges_matches_networkx_order(G):
    assert list(nx.dfs_edges(G, 0, backend="rustworkx")) == list(nx.dfs_edges.orig_func(G, 0))
    assert list(nx.dfs_edges(G, backend="rustworkx")) == list(nx.dfs_edges.orig_func(G))


def test_dfs_edges_rejects_depth_limit():
    from nx_rustworkx.interface import BackendInterface

    G = nx.path_graph(5)
    assert BackendInterface.can_run("dfs_edges", (G, 0), {"depth_limit": 2}) is not True
