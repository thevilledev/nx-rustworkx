"""Connectivity, cycle and core parity against NetworkX."""

from __future__ import annotations

import networkx as nx
import pytest

UNDIRECTED = nx.Graph([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 5), (5, 3)])
UNDIRECTED.add_node(9)

DIRECTED = nx.DiGraph([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 3)])
DIRECTED.add_node(7)


def _sorted_sets(components):
    return sorted(sorted(component) for component in components)


def test_strongly_connected_components():
    assert _sorted_sets(nx.strongly_connected_components(DIRECTED, backend="rustworkx")) == (
        _sorted_sets(nx.strongly_connected_components.orig_func(DIRECTED))
    )
    assert nx.number_strongly_connected_components(DIRECTED, backend="rustworkx") == (
        nx.number_strongly_connected_components.orig_func(DIRECTED)
    )
    assert nx.is_strongly_connected(DIRECTED, backend="rustworkx") is False
    cycle = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    assert nx.is_strongly_connected(cycle, backend="rustworkx") is True


def test_weakly_connected_counts():
    assert nx.number_weakly_connected_components(DIRECTED, backend="rustworkx") == (
        nx.number_weakly_connected_components.orig_func(DIRECTED)
    )


def test_is_semiconnected():
    chain = nx.DiGraph([(0, 1), (1, 2), (2, 3)])
    for G in (DIRECTED, chain):
        assert nx.is_semiconnected(G, backend="rustworkx") == (nx.is_semiconnected.orig_func(G))


def test_node_connected_component():
    assert nx.node_connected_component(UNDIRECTED, 0, backend="rustworkx") == (
        nx.node_connected_component.orig_func(UNDIRECTED, 0)
    )
    assert nx.node_connected_component(UNDIRECTED, 9, backend="rustworkx") == {9}


def test_articulation_points_and_bridges():
    assert sorted(nx.articulation_points(UNDIRECTED, backend="rustworkx")) == sorted(
        nx.articulation_points.orig_func(UNDIRECTED)
    )
    got = {frozenset(edge) for edge in nx.bridges(UNDIRECTED, backend="rustworkx")}
    expected = {frozenset(edge) for edge in nx.bridges.orig_func(UNDIRECTED)}
    assert got == expected


def test_biconnected_components():
    assert _sorted_sets(nx.biconnected_components(UNDIRECTED, backend="rustworkx")) == (
        _sorted_sets(nx.biconnected_components.orig_func(UNDIRECTED))
    )


def test_condensation_matches_structure():
    got = nx.condensation(DIRECTED, backend="rustworkx")
    expected = nx.condensation.orig_func(DIRECTED)
    got_members = _sorted_sets(data["members"] for _, data in got.nodes(data=True))
    expected_members = _sorted_sets(data["members"] for _, data in expected.nodes(data=True))
    assert got_members == expected_members
    assert got.number_of_edges() == expected.number_of_edges()

    # Edges between condensation nodes must connect the same member sets.
    def edge_member_pairs(C):
        return {
            (frozenset(C.nodes[u]["members"]), frozenset(C.nodes[v]["members"]))
            for u, v in C.edges()
        }

    assert edge_member_pairs(got) == edge_member_pairs(expected)
    assert got.graph["mapping"].keys() == expected.graph["mapping"].keys()


def test_stoer_wagner_matches():
    G = nx.Graph()
    G.add_weighted_edges_from([(0, 1, 3), (1, 2, 4), (2, 3, 5), (3, 0, 2), (0, 2, 1)])
    value, (left, right) = nx.stoer_wagner(G, backend="rustworkx")
    e_value, _ = nx.stoer_wagner.orig_func(G)
    assert value == pytest.approx(e_value)
    assert sorted(left + right) == sorted(G)
    assert set(left) & set(right) == set()
    cut = sum(G[u][v]["weight"] for u, v in G.edges() if (u in set(left)) != (v in set(left)))
    assert cut == pytest.approx(value)


def test_stoer_wagner_guards():
    with pytest.raises(nx.NetworkXError):
        nx.stoer_wagner(nx.Graph([(0, 1), (2, 3)]), backend="rustworkx")
    negative = nx.Graph()
    negative.add_weighted_edges_from([(0, 1, -1), (1, 2, 2)])
    with pytest.raises(nx.NetworkXError):
        nx.stoer_wagner(negative, backend="rustworkx")


def test_simple_cycles_matches():
    assert _sorted_sets(nx.simple_cycles(DIRECTED, backend="rustworkx")) == (
        _sorted_sets(nx.simple_cycles.orig_func(DIRECTED))
    )


def test_cycle_basis_is_a_basis():
    got = nx.cycle_basis(UNDIRECTED, backend="rustworkx")
    expected = nx.cycle_basis.orig_func(UNDIRECTED)
    assert len(got) == len(expected)
    assert _sorted_sets(got) == _sorted_sets(expected)
    for cycle in got:
        for u, v in zip(cycle, cycle[1:] + cycle[:1]):
            assert UNDIRECTED.has_edge(u, v)


def test_core_number_matches():
    assert nx.core_number(UNDIRECTED, backend="rustworkx") == (nx.core_number.orig_func(UNDIRECTED))


def test_core_number_rejects_self_loops():
    G = nx.Graph([(0, 1)])
    G.add_edge(2, 2)
    with pytest.raises(nx.NetworkXNotImplemented):
        nx.core_number(G, backend="rustworkx")


def test_isolates_and_transitivity():
    assert sorted(nx.isolates(UNDIRECTED, backend="rustworkx")) == sorted(
        nx.isolates.orig_func(UNDIRECTED)
    )
    assert nx.number_of_isolates(UNDIRECTED, backend="rustworkx") == (
        nx.number_of_isolates.orig_func(UNDIRECTED)
    )
    assert nx.transitivity(UNDIRECTED, backend="rustworkx") == pytest.approx(
        nx.transitivity.orig_func(UNDIRECTED)
    )


@pytest.mark.parametrize(
    "G", [nx.complete_bipartite_graph(3, 4), nx.cycle_graph(5), nx.path_graph(6)]
)
def test_is_bipartite_matches(G):
    assert nx.is_bipartite(G, backend="rustworkx") == nx.is_bipartite.orig_func(G)


def test_find_cycle_matches():
    G = nx.DiGraph([(-1, 0), (0, 1), (1, 0), (2, 1), (3, 1)])
    nodes = [0, 1, 2, 3]
    assert nx.find_cycle(G, nodes, backend="rustworkx") == nx.find_cycle.orig_func(G, nodes)
    assert nx.find_cycle(G, backend="rustworkx") == nx.find_cycle.orig_func(G)


def test_find_cycle_no_cycle_raises():
    G = nx.DiGraph([(0, 1), (1, 2)])
    with pytest.raises(nx.NetworkXNoCycle):
        nx.find_cycle(G, backend="rustworkx")
    # A cycle exists but is not reachable from the given source.
    H = nx.DiGraph([(0, 1), (3, 4), (4, 3)])
    with pytest.raises(nx.NetworkXNoCycle):
        nx.find_cycle(H, 0, backend="rustworkx")
    assert nx.find_cycle(H, backend="rustworkx") == [(3, 4), (4, 3)]


def test_find_cycle_self_loop():
    G = nx.DiGraph([(0, 1)])
    G.add_edge(2, 2)
    assert nx.find_cycle(G, backend="rustworkx") == [(2, 2)]


def test_chain_decomposition_is_valid():
    G = nx.Graph([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 2)])
    chains = list(nx.chain_decomposition(G, backend="rustworkx"))
    expected = list(nx.chain_decomposition.orig_func(G))
    assert len(chains) == len(expected)
    # The decomposition is not unique, but the chain edges partition the same
    # edge set NetworkX's chains cover.
    flat = lambda cs: {frozenset(e) for c in cs for e in c}  # noqa: E731
    assert flat(chains) == flat(expected)


def test_chain_decomposition_root():
    G = nx.Graph([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 2)])
    chains = list(nx.chain_decomposition(G, root=2, backend="rustworkx"))
    assert all(chain[0][0] == 2 for chain in chains)
    with pytest.raises(nx.NodeNotFound):
        list(nx.chain_decomposition(G, root=99, backend="rustworkx"))


def test_bridges_with_root():
    G = nx.Graph([(0, 1), (1, 2), (2, 0), (2, 3), (4, 5)])
    assert sorted(nx.bridges(G, root=4, backend="rustworkx")) == sorted(
        nx.bridges.orig_func(G, root=4)
    )
    assert sorted(nx.bridges(G, root=0, backend="rustworkx")) == sorted(
        nx.bridges.orig_func(G, root=0)
    )
    with pytest.raises(nx.NodeNotFound):
        list(nx.bridges(G, root=99, backend="rustworkx"))


@pytest.mark.parametrize(
    "G, expected",
    [
        (nx.petersen_graph(), False),
        (nx.complete_graph(4), True),
        (nx.complete_graph(5), False),
        (nx.grid_2d_graph(4, 4), True),
        (nx.DiGraph([(0, 1), (1, 2), (2, 0)]), True),
        (nx.complete_graph(5, create_using=nx.DiGraph), False),
    ],
)
def test_is_planar_matches(G, expected):
    assert nx.is_planar(G, backend="rustworkx") is expected
    assert nx.is_planar(G, backend="rustworkx") == nx.is_planar.orig_func(G)


def test_bridges_match_networkx_order():
    G = nx.Graph()
    nx.add_path(G, [0, 1, 2])
    nx.add_path(G, [4, 5, 6])
    assert list(nx.bridges(G, root=4, backend="rustworkx")) == [(4, 5), (5, 6)]
    H = nx.Graph([(3, 1), (1, 0), (0, 3), (1, 9)])
    assert list(nx.bridges(H, backend="rustworkx")) == list(nx.bridges.orig_func(H))
