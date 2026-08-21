"""Phase 3: rustworkx-backed graph objects and fallback."""

from __future__ import annotations

import networkx as nx
import pytest

from nx_rustworkx.graph import RustworkxGraph


@pytest.fixture
def restore_nx_config():
    prev_classes = list(nx.config.backend_priority.classes)
    prev_gens = list(nx.config.backend_priority.generators)
    prev_algos = list(nx.config.backend_priority.algos)
    prev_fallback = nx.config.fallback_to_nx
    yield
    nx.config.backend_priority.classes = prev_classes
    nx.config.backend_priority.generators = prev_gens
    nx.config.backend_priority.algos = prev_algos
    nx.config.fallback_to_nx = prev_fallback


def test_graph_backend_kwarg_builds_rustworkx_graph():
    G = nx.Graph(backend="rustworkx")
    assert isinstance(G, RustworkxGraph)
    assert not G.is_directed()
    G.add_edge("a", "b")
    G.add_node("isolated")
    assert set(G) == {"a", "b", "isolated"}
    assert G.has_edge("a", "b")
    got = nx.betweenness_centrality(G)
    assert set(got) == {"a", "b", "isolated"}


def test_graph_backend_from_edgelist():
    G = nx.Graph([("s", "t"), ("t", "u")], backend="rustworkx", name="demo")
    assert isinstance(G, RustworkxGraph)
    assert G.name == "demo"
    assert nx.shortest_path(G, "s", "u") == ["s", "t", "u"]


def test_digraph_backend_kwarg():
    G = nx.DiGraph([("a", "b"), ("b", "c")], backend="rustworkx")
    assert isinstance(G, RustworkxGraph)
    assert G.is_directed()
    assert nx.shortest_path(G, "a", "c") == ["a", "b", "c"]
    with pytest.raises(nx.NetworkXNoPath):
        nx.shortest_path(G, "c", "a")


def test_empty_graph_and_from_edgelist_backend():
    G = nx.empty_graph(["x", "y", "z"], backend="rustworkx")
    assert isinstance(G, RustworkxGraph)
    assert set(G) == {"x", "y", "z"}
    H = nx.from_edgelist([(0, 1), (1, 2)], backend="rustworkx")
    assert isinstance(H, RustworkxGraph)
    assert H.number_of_edges() == 2


def test_generator_priority_skips_conversion(restore_nx_config, monkeypatch):
    import nx_rustworkx.convert as convert_mod

    calls = {"n": 0}
    original = convert_mod.convert_from_nx

    def wrapped(G, *args, **kwargs):
        calls["n"] += 1
        return original(G, *args, **kwargs)

    monkeypatch.setattr(convert_mod, "convert_from_nx", wrapped)
    nx.config.backend_priority.generators = ["rustworkx"]
    G = nx.gnp_random_graph(40, 0.2, seed=0)
    assert isinstance(G, RustworkxGraph)
    nx.betweenness_centrality(G)
    assert calls["n"] == 0


def test_class_priority_builds_backend_graph(restore_nx_config):
    nx.config.backend_priority.classes = ["rustworkx"]
    G = nx.Graph([(1, 2), (2, 3)])
    assert isinstance(G, RustworkxGraph)
    assert nx.shortest_path_length(G, 1, 3) == 2


def test_fallback_to_nx_for_unimplemented(restore_nx_config):
    G = nx.Graph([(0, 1), (1, 2)], backend="rustworkx")
    nx.config.fallback_to_nx = False
    with pytest.raises(NotImplementedError):
        nx.degree_centrality(G)

    nx.config.fallback_to_nx = True
    result = nx.degree_centrality(G)
    assert result[1] == pytest.approx(1.0)
    assert result[0] == pytest.approx(0.5)


def test_multigraph_constructor_rejected():
    with pytest.raises(NotImplementedError):
        nx.MultiGraph(backend="rustworkx")


def test_constructed_graph_matches_networkx_betweenness():
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
    rw = nx.Graph(edges, backend="rustworkx")
    nx_g = nx.Graph(edges)
    got = nx.betweenness_centrality(rw)
    expected = nx.betweenness_centrality.orig_func(nx_g)
    for node in nx_g:
        assert got[node] == pytest.approx(expected[node], rel=1e-9, abs=1e-12)


def test_remove_node_keeps_dense_indices():
    G = nx.Graph(backend="rustworkx")
    G.add_edges_from([(0, 1), (1, 2), (2, 3)])
    G.remove_node(1)
    assert set(G) == {0, 2, 3}
    assert list(G.rx_graph.node_indices()) == list(range(G.number_of_nodes()))
    assert not G.has_edge(0, 2)
    assert G.has_edge(2, 3)
