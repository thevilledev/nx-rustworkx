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


def test_steiner_tree_accepts_iterator_terminals():
    G = _weighted(seed=7)
    got = nx.approximation.steiner_tree(G, iter([0, 5, 11]), backend="rustworkx")
    assert {0, 5, 11} <= set(got.nodes)
    assert nx.is_connected(nx.Graph(got))


def test_steiner_tree_lone_terminal_matches_networkx():
    # NetworkX's edge subgraph of a single terminal spans nothing at all.
    G = nx.path_graph(4)
    got = nx.approximation.steiner_tree(G, [2], method="kou", backend="rustworkx")
    expected = nx.approximation.steiner_tree.orig_func(G, [2], method="kou")
    assert list(got) == list(expected) == []
    assert got.number_of_edges() == 0


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


def test_complement_carries_no_attributes():
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_node(0, color="red")
    G.add_edge(0, 1, w=3)
    H = nx.Graph()
    H.add_node(0, color="red")
    H.add_edge(0, 1, w=3)
    got = nx.complement(G, backend="rustworkx")
    expected = nx.complement.orig_func(H)
    assert dict(got.nodes(data=True)) == dict(expected.nodes(data=True))


@pytest.mark.parametrize("kernel", ["cartesian_product", "tensor_product"])
def test_products_pair_node_attrs_like_networkx(kernel):
    A = nx.Graph()
    A.add_node(0, na="x")
    A.add_edge(0, 1)
    B = nx.Graph()
    B.add_node("a", nb="y")
    B.add_edge("a", "b")
    got = getattr(nx, kernel)(A, B, backend="rustworkx")
    expected = getattr(nx, kernel).orig_func(A, B)
    assert dict(got.nodes(data=True)) == dict(expected.nodes(data=True))
    assert {frozenset(e) for e in got.edges()} == {frozenset(e) for e in expected.edges()}


def test_products_decline_edge_attribute_graphs():
    from nx_rustworkx.interface import BackendInterface

    A = nx.Graph([(0, 1)])
    B = nx.Graph()
    B.add_edge("a", "b", w=4)
    assert BackendInterface.can_run("cartesian_product", (A, B), {}) is not True
    assert BackendInterface.can_run("tensor_product", (A, B), {}) is not True
    assert BackendInterface.can_run("cartesian_product", (A, nx.Graph([("a", "b")])), {}) is True


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


def test_greedy_color_extra_strategies_are_valid():
    for strategy in ("saturation_largest_first", "DSATUR", "independent_set"):
        for G in (nx.petersen_graph(), nx.gnp_random_graph(40, 0.15, seed=4)):
            colors = nx.greedy_color(G, strategy=strategy, backend="rustworkx")
            assert set(colors) == set(G)
            for u, v in G.edges():
                assert colors[u] != colors[v], (strategy, u, v)


def test_line_graph_matches():
    G = nx.Graph()
    G.add_edge(2, 1)
    G.add_edge(1, 0)
    G.add_edge(1, 1)  # self-loops become ordinary line-graph nodes
    got = nx.line_graph(G, backend="rustworkx")
    expected = nx.line_graph.orig_func(G)
    assert set(got.nodes) == set(expected.nodes)
    assert {frozenset(e) for e in got.edges} == {frozenset(e) for e in expected.edges}


def test_line_graph_directed_falls_back():
    from nx_rustworkx.interface import BackendInterface

    D = nx.DiGraph([(0, 1), (1, 2)])
    assert BackendInterface.can_run("line_graph", (D,), {}) is not True


def test_is_matching_variants():
    G = nx.Graph([(1, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5)])
    cases = [{(1, 3), (2, 4)}, {(1, 2), (3, 5)}, {(1, 2), (2, 3)}, {1: 3, 3: 1, 2: 4, 4: 2}]
    for matching in cases:
        assert nx.is_matching(G, matching, backend="rustworkx") == nx.is_matching.orig_func(
            G, matching
        )
        assert nx.is_maximal_matching(
            G, matching, backend="rustworkx"
        ) == nx.is_maximal_matching.orig_func(G, matching)
    with pytest.raises(nx.NetworkXError):
        nx.is_matching(G, {(1, 99)}, backend="rustworkx")
    with pytest.raises(nx.NetworkXError):
        nx.is_matching(G, {7: 7}, backend="rustworkx")
    # A self-loop edge in set form is invalid, not an error.
    H = nx.Graph([(0, 0), (0, 1)])
    assert nx.is_matching(H, {(0, 0)}, backend="rustworkx") is False


def test_metric_closure_matches_distances():
    G = _weighted(seed=6, n=18, p=0.3)
    if not nx.is_connected.orig_func(G):
        G = nx.compose(G, nx.path_graph(sorted(G)))
    got = nx.approximation.metric_closure(G, backend="rustworkx")
    expected = nx.approximation.metric_closure.orig_func(G)
    assert set(got.nodes) == set(expected.nodes)
    for u, v in expected.edges:
        assert got[u][v]["distance"] == pytest.approx(expected[u][v]["distance"])
        path = got[u][v]["path"]
        assert path[0] == u and path[-1] == v
        assert _total_weight(G, zip(path, path[1:])) == pytest.approx(expected[u][v]["distance"])


def test_metric_closure_disconnected_raises():
    with pytest.raises(nx.NetworkXError):
        nx.approximation.metric_closure(nx.Graph([(0, 1), (2, 3)]), backend="rustworkx")


def test_all_simple_paths_multiple_targets():
    G = nx.gnp_random_graph(12, 0.25, seed=2)
    for targets in ([3, 7], [0, 5], [5, 99], (7, 3, 3)):
        got = sorted(nx.all_simple_paths(G, 0, targets, backend="rustworkx"))
        expected = sorted(nx.all_simple_paths.orig_func(G, 0, targets))
        assert got == expected, targets


def test_vf2pp_isomorphism_returns_valid_mapping():
    G = nx.gnp_random_graph(25, 0.2, seed=9)
    H = nx.relabel_nodes(G, {n: n + 100 for n in G})
    mapping = nx.vf2pp_isomorphism(G, H, backend="rustworkx")
    assert set(mapping) == set(G) and set(mapping.values()) == set(H)
    for u, v in G.edges():
        assert H.has_edge(mapping[u], mapping[v])
    assert nx.vf2pp_isomorphism(G, nx.path_graph(25), backend="rustworkx") is None
    assert nx.vf2pp_isomorphism(nx.path_graph(3), nx.DiGraph([(0, 1)]), backend="rustworkx") is None


def test_vf2pp_all_isomorphisms_counts():
    got = list(nx.vf2pp_all_isomorphisms(nx.cycle_graph(4), nx.cycle_graph(4), backend="rustworkx"))
    expected = list(nx.vf2pp_all_isomorphisms.orig_func(nx.cycle_graph(4), nx.cycle_graph(4)))
    key = lambda m: tuple(sorted(m.items()))  # noqa: E731
    assert sorted(map(key, got)) == sorted(map(key, expected))


def test_vf2pp_isomorphism_empty_graphs():
    for cls in (nx.Graph, nx.DiGraph):
        assert nx.vf2pp_isomorphism(cls(), cls(), backend="rustworkx") is None
        assert list(nx.vf2pp_all_isomorphisms(cls(), cls(), backend="rustworkx")) == []


def test_metric_closure_isolated_node_raises():
    G = nx.complete_graph(4)
    G.add_node(100)
    with pytest.raises(nx.NetworkXError):
        nx.approximation.metric_closure(G, backend="rustworkx")
