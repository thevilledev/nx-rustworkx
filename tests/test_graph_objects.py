"""Rustworkx-backed graph objects: construction, views, and fallback."""

from __future__ import annotations

import networkx as nx
import pytest

from nx_rustworkx.graph import RustworkxGraph

# Graph(backend=) / backend_priority.classes arrived in NetworkX 3.6.
# Python 3.10 cannot install that (NetworkX 3.5 dropped 3.10).
HAS_CLASS_DISPATCH = hasattr(nx.config.backend_priority, "classes")
HAS_GENERATOR_PRIORITY = hasattr(nx.config.backend_priority, "generators")


def rustworkx_graph(data=(), *, directed=False, **attr):
    """Build a RustworkxGraph on every supported NetworkX version."""
    G = nx.empty_graph(
        0,
        create_using=nx.DiGraph if directed else nx.Graph,
        backend="rustworkx",
    )
    if data:
        G.add_edges_from(data)
    G.graph.update(attr)
    return G


needs_class_dispatch = pytest.mark.skipif(
    not HAS_CLASS_DISPATCH,
    reason="NetworkX < 3.6 has no Graph(backend=) / backend_priority.classes",
)
needs_generator_priority = pytest.mark.skipif(
    not HAS_GENERATOR_PRIORITY,
    reason="NetworkX < 3.5 has no backend_priority.generators",
)


@pytest.fixture
def restore_nx_config():
    prio = nx.config.backend_priority
    prev_classes = list(getattr(prio, "classes", []))
    prev_gens = list(getattr(prio, "generators", []))
    prev_algos = list(getattr(prio, "algos", prio if isinstance(prio, list) else []))
    prev_fallback = nx.config.fallback_to_nx
    yield
    if HAS_CLASS_DISPATCH:
        nx.config.backend_priority.classes = prev_classes
    if HAS_GENERATOR_PRIORITY:
        nx.config.backend_priority.generators = prev_gens
    if hasattr(prio, "algos"):
        nx.config.backend_priority.algos = prev_algos
    elif isinstance(prio, list):
        nx.config.backend_priority = prev_algos
    nx.config.fallback_to_nx = prev_fallback


@needs_class_dispatch
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


@needs_class_dispatch
def test_graph_backend_from_edgelist():
    G = nx.Graph([("s", "t"), ("t", "u")], backend="rustworkx", name="demo")
    assert isinstance(G, RustworkxGraph)
    assert G.name == "demo"
    assert nx.shortest_path(G, "s", "u") == ["s", "t", "u"]


@needs_class_dispatch
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


@needs_generator_priority
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


@needs_class_dispatch
def test_class_priority_builds_backend_graph(restore_nx_config):
    nx.config.backend_priority.classes = ["rustworkx"]
    G = nx.Graph([(1, 2), (2, 3)])
    assert isinstance(G, RustworkxGraph)
    assert nx.shortest_path_length(G, 1, 3) == 2


def test_fallback_to_nx_for_unimplemented(restore_nx_config):
    # Needs a function this backend does not implement. degree_centrality used
    # to qualify; it is dispatched now, so this uses triangles, which rustworkx
    # has no kernel for.
    G = rustworkx_graph([(0, 1), (1, 2), (2, 0), (2, 3)])
    nx.config.fallback_to_nx = False
    with pytest.raises(NotImplementedError):
        nx.triangles(G)

    nx.config.fallback_to_nx = True
    result = nx.triangles(G)
    assert result[0] == 1
    assert result[3] == 0


@needs_class_dispatch
def test_multigraph_constructor_returns_backend_multigraph():
    from nx_rustworkx.graph import RustworkxMultiGraph

    G = nx.MultiGraph(backend="rustworkx")
    assert isinstance(G, RustworkxMultiGraph)
    assert G.is_multigraph() and not G.is_directed()
    D = nx.MultiDiGraph([(0, 1), (0, 1), (1, 0)], name="d", backend="rustworkx")
    assert isinstance(D, RustworkxMultiGraph) and D.is_directed()
    assert D.number_of_edges() == 3 and D.number_of_edges(0, 1) == 2
    assert D.graph["name"] == "d"


def test_constructed_graph_matches_networkx_betweenness():
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
    rw = rustworkx_graph(edges)
    nx_g = nx.Graph(edges)
    got = nx.betweenness_centrality(rw)
    expected = nx.betweenness_centrality.orig_func(nx_g)
    for node in nx_g:
        assert got[node] == pytest.approx(expected[node], rel=1e-9, abs=1e-12)


def test_remove_node_keeps_dense_indices():
    G = rustworkx_graph([(0, 1), (1, 2), (2, 3)])
    G.remove_node(1)
    assert set(G) == {0, 2, 3}
    assert list(G.rx_graph.node_indices()) == list(range(G.number_of_nodes()))
    assert not G.has_edge(0, 2)
    assert G.has_edge(2, 3)


def _populate(make):
    """Same graph built through the backend and through NetworkX."""
    G = make()
    G.add_node(1, color="red")
    G.add_edge(1, 2, weight=5)
    G.add_edge(2, 3, weight=7)
    G.add_nodes_from([(4, {"color": "blue"})])
    G.add_node(1, size=3)  # update an existing node
    return G


@pytest.fixture
def pair():
    return _populate(lambda: nx.empty_graph(0, backend="rustworkx")), _populate(nx.Graph)


VIEW_CASES = {
    "set(nodes)": lambda G: set(G.nodes),
    "len(nodes)": lambda G: len(G.nodes),
    "nodes[n]": lambda G: dict(G.nodes[1]),
    "nodes(data=True)": lambda G: sorted((n, dict(d)) for n, d in G.nodes(data=True)),
    "nodes(data=key)": lambda G: sorted(G.nodes(data="color")),
    "nodes(data,default)": lambda G: sorted(G.nodes(data="color", default="none")),
    "len(edges)": lambda G: len(G.edges),
    "set(edges)": lambda G: {frozenset(e) for e in G.edges},
    "edges(data=key)": lambda G: sorted(
        (frozenset((u, v)), w) for u, v, w in G.edges(data="weight")
    ),
    "edges(nbunch)": lambda G: {frozenset(e) for e in G.edges(1)},
    "edges(nbunch list)": lambda G: {frozenset(e) for e in G.edges([1, 3])},
    "edge membership": lambda G: ((1, 2) in G.edges, (1, 3) in G.edges),
    "degree(n)": lambda G: G.degree(2),
    "degree[n]": lambda G: G.degree[2],
    "iter(degree)": lambda G: sorted(G.degree),
    "degree(nbunch)": lambda G: sorted(G.degree([1, 2])),
    "len(degree)": lambda G: len(G.degree),
    "node membership": lambda G: (1 in G.nodes, 99 in G.nodes),
    "unhashable is not a node": lambda G: (G.has_node([1]), [1] in G),
}


@pytest.mark.parametrize("case", list(VIEW_CASES))
def test_views_match_networkx(pair, case):
    backend_graph, nx_graph = pair
    read = VIEW_CASES[case]
    assert read(backend_graph) == read(nx_graph)


def test_edges_nbunch_orientation_and_order_match_networkx():
    edges = [(1, 2), (2, 3), (3, 4), (1, 4)]
    G = rustworkx_graph(edges)
    H = nx.Graph(edges)
    assert list(G.edges(2)) == list(H.edges(2))
    assert list(G.edges([3, 1])) == list(H.edges([3, 1]))
    assert list(G.edges([3, 99])) == list(H.edges([3, 99]))  # missing quietly ignored
    assert list(G.edges(2, data=True)) == list(H.edges(2, data=True))
    assert list(G.edges(2, data="w", default=0)) == list(H.edges(2, data="w", default=0))
    D = rustworkx_graph(edges, directed=True)
    DH = nx.DiGraph(edges)
    assert list(D.edges(2)) == list(DH.edges(2))
    assert list(D.edges([4, 1])) == list(DH.edges([4, 1]))


def test_multigraph_edges_nbunch_matches_networkx():
    from nx_rustworkx.convert import convert_from_nx

    edges = [(1, 2), (1, 2), (2, 3), (3, 3)]
    M = nx.MultiGraph(edges)
    W = convert_from_nx(M, preserve_edge_attrs=True)
    assert list(W.edges(2, keys=True)) == list(M.edges(2, keys=True))
    assert list(W.edges(2, keys=True, data=True)) == list(M.edges(2, keys=True, data=True))
    assert list(W.edges([3, 1])) == list(M.edges([3, 1]))


@pytest.mark.parametrize("directed", [False, True])
def test_add_edge_merges_attributes_like_networkx(directed):
    G = rustworkx_graph(directed=directed)
    H = (nx.DiGraph if directed else nx.Graph)()
    for graph in (G, H):
        graph.add_edge(1, 2, weight=3)
        graph.add_edge(1, 2, color="red")
    assert G.get_edge_data(1, 2) == H.get_edge_data(1, 2) == {"weight": 3, "color": "red"}
    for graph in (G, H):
        graph.add_edge(1, 2)  # a bare re-add keeps the attributes
    assert G.get_edge_data(1, 2) == H.get_edge_data(1, 2) == {"weight": 3, "color": "red"}
    for graph in (G, H):
        graph.add_edge(1, 2, weight=9)
    assert G.get_edge_data(1, 2) == H.get_edge_data(1, 2) == {"weight": 9, "color": "red"}
    assert G.number_of_edges() == H.number_of_edges() == 1


def test_add_edges_from_merges_duplicates_like_networkx():
    edges = [(1, 2, {"a": 1}), (1, 2, {"b": 2}), (1, 2)]
    G = rustworkx_graph()
    G.add_edges_from(edges)
    H = nx.Graph()
    H.add_edges_from(edges)
    assert G.get_edge_data(1, 2) == H[1][2] == {"a": 1, "b": 2}
    assert G.number_of_edges() == 1


def test_add_edge_updates_kernel_built_containers_in_place():
    # An unseeded random generator hands back a multigraph=True rustworkx
    # container inside the simple wrapper; add_edge must merge there too,
    # never grow a parallel edge.
    G = nx.gnp_random_graph(30, 0.2, backend="rustworkx")
    assert G.rx_graph.multigraph
    G.add_edge(0, 1, weight=1)
    edges = G.rx_graph.num_edges()
    G.add_edge(0, 1, color="red")
    assert G.rx_graph.num_edges() == edges
    assert G.get_edge_data(0, 1) == {"weight": 1, "color": "red"}


def test_node_attributes_survive_add_and_update():
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_node("a", color="red")
    assert G.nodes["a"] == {"color": "red"}
    G.add_node("a", size=2)
    assert G.nodes["a"] == {"color": "red", "size": 2}
    # The view hands back the live dict, so assignment sticks.
    G.nodes["a"]["shape"] = "box"
    assert G.nodes["a"]["shape"] == "box"


def test_add_nodes_from_applies_shared_and_per_node_attrs():
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_nodes_from(["a", ("b", {"color": "blue"})], kind="node")
    assert G.nodes["a"] == {"kind": "node"}
    assert G.nodes["b"] == {"kind": "node", "color": "blue"}


def test_copy_gives_independent_attribute_dicts():
    # NetworkX's copy is independent at the dict level: writing through the
    # copy never shows up in the original.
    G = rustworkx_graph()
    G.add_node(1, color="red")
    G.add_edge(1, 2, weight=3)
    H = G.copy()
    H.nodes[1]["color"] = "blue"
    H.get_edge_data(1, 2)["weight"] = 99
    assert G.nodes[1] == {"color": "red"}
    assert G.get_edge_data(1, 2) == {"weight": 3}


def test_multigraph_copy_gives_independent_node_dicts():
    from nx_rustworkx.graph import RustworkxMultiGraph

    G = RustworkxMultiGraph.empty()
    G.add_node(1, color="red")
    G.add_edge(1, 2, weight=3)
    H = G.copy()
    H.nodes[1]["color"] = "blue"
    H.get_edge_data(1, 2, 0)["weight"] = 99
    assert G.nodes[1] == {"color": "red"}
    assert G.get_edge_data(1, 2, 0) == {"weight": 3}


def test_to_directed_gives_each_direction_its_own_dict():
    G = rustworkx_graph()
    G.add_node(1, color="red")
    G.add_edge(1, 2, weight=3)
    D = G.to_directed()
    D.get_edge_data(1, 2)["weight"] = 99
    D.nodes[1]["color"] = "blue"
    assert G.get_edge_data(1, 2) == {"weight": 3}
    assert D.get_edge_data(2, 1) == {"weight": 3}
    assert G.nodes[1] == {"color": "red"}


def test_to_undirected_merges_reciprocal_edges_like_networkx():
    build = [((1, 2), {"w": 1, "only_fwd": True}), ((2, 1), {"w": 9})]
    G = rustworkx_graph(directed=True)
    H = nx.DiGraph()
    for (u, v), data in build:
        G.add_edge(u, v, **data)
        H.add_edge(u, v, **data)
    U = G.to_undirected()
    expected = H.to_undirected()
    assert U.get_edge_data(1, 2) == expected[1][2] == {"w": 9, "only_fwd": True}
    assert U.number_of_edges() == expected.number_of_edges() == 1
    # The merged dict is the undirected graph's own.
    U.get_edge_data(1, 2)["w"] = 5
    assert G.get_edge_data(2, 1) == {"w": 9}


def test_constructing_from_a_wrapper_still_copies_it():
    source = rustworkx_graph()
    source.add_node(1, color="red")
    source.add_edge(1, 2, weight=3)
    built = RustworkxGraph.from_incoming(source)
    built.add_edge(2, 3)
    built.nodes[1]["color"] = "blue"
    built.get_edge_data(1, 2)["weight"] = 99
    assert not source.has_edge(2, 3)
    assert source.nodes[1] == {"color": "red"}
    assert source.get_edge_data(1, 2) == {"weight": 3}


def test_node_attributes_follow_copies_and_orientation():
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_node(1, color="red")
    G.add_edge(1, 2)
    assert G.copy().nodes[1] == {"color": "red"}
    assert G.to_directed().nodes[1] == {"color": "red"}
    assert G.to_directed().to_undirected().nodes[1] == {"color": "red"}


def test_remove_node_and_clear_drop_attributes():
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_node(1, color="red")
    G.add_edge(1, 2)
    G.remove_node(1)
    assert 1 not in G.nodes
    G.add_node(1)
    assert G.nodes[1] == {}
    G.clear()
    assert len(G.nodes) == 0


def test_node_attributes_reach_networkx_on_fallback(restore_nx_config):
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_node(1, color="red")
    G.add_edge(1, 2)
    G.add_edge(2, 3)
    nx.config.fallback_to_nx = True
    # triangles converts back through convert_to_nx; attributes must survive.
    assert nx.triangles(G) == {1: 0, 2: 0, 3: 0}
    from nx_rustworkx.convert import convert_to_nx

    assert convert_to_nx(G).nodes[1] == {"color": "red"}


def test_missing_node_attribute_lookup_raises_keyerror():
    G = nx.empty_graph(0, backend="rustworkx")
    G.add_node(1)
    with pytest.raises(KeyError):
        G.nodes[99]


def test_in_and_out_degree_are_directed_only():
    D = nx.empty_graph(0, create_using=nx.DiGraph, backend="rustworkx")
    D.add_edge("x", "y")
    assert D.degree("y") == 1
    assert D.in_degree("y") == 1
    assert D.out_degree("y") == 0
    U = nx.empty_graph(0, backend="rustworkx")
    with pytest.raises(AttributeError):
        U.in_degree
