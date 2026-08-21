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
