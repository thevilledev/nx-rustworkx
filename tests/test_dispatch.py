"""Prove NetworkX dispatch actually hits rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.interface import BackendInterface


def test_backend_is_registered():
    assert "rustworkx" in nx.betweenness_centrality.backends


def test_info_does_not_import_rustworkx():
    from nx_rustworkx._info import get_info

    info = get_info()
    assert info["backend_name"] == "rustworkx"
    assert info["package"] == "nx_rustworkx"
    assert "betweenness_centrality" in info["functions"]
    assert info["default_config"]["min_nodes"] == 200


def test_explicit_backend_calls_rustworkx(monkeypatch):
    called = {}
    original = rx.betweenness_centrality

    def wrapper(*args, **kwargs):
        called["yes"] = True
        return original(*args, **kwargs)

    monkeypatch.setattr(rx, "betweenness_centrality", wrapper)
    G = nx.erdos_renyi_graph(40, 0.2, seed=0)
    result = nx.betweenness_centrality(G, backend="rustworkx")
    assert called.get("yes") is True
    assert set(result) == set(G)


def test_betweenness_matches_networkx_on_unweighted():
    G = nx.karate_club_graph()
    got = nx.betweenness_centrality(G, backend="rustworkx")
    expected = nx.betweenness_centrality.orig_func(G)
    assert got.keys() == expected.keys()
    for node in G:
        assert got[node] == pytest_approx(expected[node])


def pytest_approx(value):
    import pytest

    return pytest.approx(value, rel=1e-9, abs=1e-12)


def test_string_nodes_dispatch():
    G = nx.Graph([("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")])
    got = nx.betweenness_centrality(G, backend="rustworkx")
    expected = nx.betweenness_centrality.orig_func(G)
    assert set(got) == set(expected)
    for node in G:
        assert got[node] == pytest_approx(expected[node])


def test_interface_exposes_phase1_algorithms():
    for name in (
        "betweenness_centrality",
        "pagerank",
        "shortest_path",
        "is_connected",
        "is_isomorphic",
    ):
        assert hasattr(BackendInterface, name)


def test_info_documents_every_implemented_function():
    from nx_rustworkx._info import get_info
    from nx_rustworkx.algorithms import ALGORITHMS
    from nx_rustworkx.generators import GENERATORS

    documented = set(get_info()["functions"])
    assert documented == set(ALGORITHMS) | set(GENERATORS)


def test_info_functions_are_dispatchable_in_networkx():
    from nx_rustworkx.algorithms import ALGORITHMS

    missing = [
        name
        for name in ALGORITHMS
        if name not in nx.utils.backends._registered_algorithms
    ]
    assert missing == []


def test_compat_probes_match_installed_networkx():
    """The version probes must agree with what NetworkX actually does."""
    import warnings

    from nx_rustworkx import _compat

    G = nx.DiGraph([(0, 1)])
    assert _compat.immediate_dominators_includes_start() == (
        0 in nx.immediate_dominators.orig_func(G, 0)
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        reference = nx.single_target_shortest_path_length.orig_func(G, 1)
    assert _compat.single_target_shortest_path_length_returns_dict() == isinstance(
        reference, dict
    )
