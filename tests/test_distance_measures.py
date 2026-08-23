"""The eccentricity family must answer exactly as NetworkX does."""

from __future__ import annotations

import networkx as nx
import pytest

from nx_rustworkx.algorithms import distance_measures as dm
from nx_rustworkx.convert import convert_from_nx

FAMILY = ["eccentricity", "diameter", "radius", "center", "periphery"]


def graphs():
    W = nx.Graph()
    W.add_edge(0, 1, weight=5)
    W.add_edge(1, 2, weight=1)
    W.add_edge(0, 2, weight=9)
    return {
        "path": nx.path_graph.orig_func(6),
        "karate": nx.karate_club_graph.orig_func(),
        "directed_cycle": nx.cycle_graph.orig_func(5, nx.DiGraph),
        "single": nx.trivial_graph.orig_func(),
        "selfloop": nx.Graph([(0, 0), (0, 1)]),
        "labels": nx.Graph([("a", "b"), ("b", "c"), ("c", "d"), ("b", "d")]),
        "weighted": W,
    }


@pytest.mark.parametrize("name", FAMILY)
@pytest.mark.parametrize("gname", sorted(graphs()))
def test_family_matches_networkx(name, gname):
    G = graphs()[gname]
    assert getattr(dm, name)(G) == getattr(nx, name).orig_func(G)


@pytest.mark.parametrize("name", FAMILY)
def test_family_weighted_matches(name):
    G = graphs()["weighted"]
    assert getattr(dm, name)(G, weight="weight") == getattr(nx, name).orig_func(G, weight="weight")


@pytest.mark.parametrize("name", ["diameter", "radius", "center", "periphery"])
def test_usebounds_is_an_algorithm_choice(name):
    G = graphs()["karate"]
    assert getattr(dm, name)(G, usebounds=True) == getattr(nx, name).orig_func(G)


@pytest.mark.parametrize("gname", ["disconnected", "weakly_connected_digraph"])
@pytest.mark.parametrize("name", FAMILY)
def test_family_raises_for_infinite_paths(name, gname):
    G = nx.Graph([(0, 1), (2, 3)]) if gname == "disconnected" else nx.DiGraph([(0, 1), (1, 2)])
    with pytest.raises(nx.NetworkXError) as expected:
        getattr(nx, name).orig_func(G)
    with pytest.raises(nx.NetworkXError, match=str(expected.value)):
        getattr(dm, name)(G)


def test_eccentricity_v_variants():
    G = graphs()["path"]
    orig = nx.eccentricity.orig_func
    assert dm.eccentricity(G, v=2) == orig(G, v=2)
    assert isinstance(dm.eccentricity(G, v=2), int)
    assert dm.eccentricity(G, v=[1, 3]) == orig(G, v=[1, 3])
    # nbunch semantics: missing members are skipped, a missing single node raises
    assert dm.eccentricity(G, v=[1, 99]) == orig(G, v=[1, 99])
    with pytest.raises(nx.NetworkXError):
        dm.eccentricity(G, v=99)


def test_unweighted_values_are_ints():
    ecc = dm.eccentricity(graphs()["karate"])
    assert all(isinstance(value, int) for value in ecc.values())


def test_empty_graph_behavior():
    assert dm.eccentricity(nx.Graph()) == {}
    with pytest.raises(ValueError):
        dm.diameter(nx.Graph())


def test_native_graph_input():
    G = graphs()["karate"]
    R = convert_from_nx(G)
    assert dm.diameter(R) == nx.diameter.orig_func(G)
    assert dm.center(R) == nx.center.orig_func(G)


def test_precomputed_arguments_fall_back():
    assert dm.eccentricity.can_run(nx.path_graph.orig_func(3), sp={}) is not True
    assert dm.diameter.can_run(nx.path_graph.orig_func(3), e={}) is not True
    assert dm.diameter.can_run(nx.path_graph.orig_func(3)) is True


def test_memory_guard_declines_large_graphs():
    class Big:
        def number_of_nodes(self):
            return dm.MAX_MATRIX_NODES + 1

    reason = dm.diameter.should_run(Big())
    assert reason is not True
    assert "MB" in reason

    # A single-node eccentricity request needs no matrix, so size does not gate it.
    class BigEnough(Big):
        def number_of_edges(self):
            return 10_000

    assert dm.eccentricity.should_run(BigEnough(), v=0) is True


def test_dispatch_via_networkx():
    G = nx.karate_club_graph.orig_func()
    assert nx.diameter(G, backend="rustworkx") == nx.diameter.orig_func(G)
    assert nx.eccentricity(G, backend="rustworkx") == nx.eccentricity.orig_func(G)
