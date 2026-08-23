"""MultiGraph support: wrapper parity with NetworkX and the dispatch gate."""

from __future__ import annotations

import inspect

import networkx as nx
import pytest

from nx_rustworkx.algorithms import ALGORITHMS
from nx_rustworkx.algorithms._utils import as_directed_rx
from nx_rustworkx.convert import convert_from_nx, convert_to_nx
from nx_rustworkx.graph import RustworkxMultiGraph
from nx_rustworkx.interface import BackendInterface


def _populate(G):
    G.add_edge(0, 1, weight=3)
    G.add_edge(0, 1, weight=1)
    G.add_edge(1, 1)
    G.add_edge(1, 1, key="loop", note="self")
    G.add_edge(2, 3, key="k", color="red")
    G.add_edge(1, 2)
    G.add_node(9, tag="iso")
    G.graph["name"] = "multi"
    return G


def _pair(cls):
    M = _populate(cls())
    return convert_from_nx(M, preserve_all_attrs=True), M


def _canon(edges, directed):
    """Order-free form of an edge iterable, for undirected or directed views."""
    out = []
    for edge in edges:
        u, v, *rest = edge
        ends = (u, v) if directed else tuple(sorted((u, v), key=str))
        out.append((*ends, *rest))
    return sorted(out, key=str)


VIEW_CASES = {
    "edges_keyed": lambda G: _canon(G.edges, G.is_directed()),
    "edges_plain": lambda G: _canon(G.edges(), G.is_directed()),
    "edges_keys_data": lambda G: _canon(G.edges(keys=True, data=True), G.is_directed()),
    "edges_attr": lambda G: _canon(G.edges(data="weight", keys=True, default=0), G.is_directed()),
    "edges_nbunch": lambda G: _canon(G.edges([1], keys=True), G.is_directed()),
    "len_edges": lambda G: len(G.edges),
    "contains_pair": lambda G: (0, 1) in G.edges,
    "contains_keyed": lambda G: (0, 1, 1) in G.edges,
    "contains_pair_without_key_0": lambda G: (2, 3) in G.edges,
    "adj_bundle": lambda G: dict(G[0][1]),
    "adj_self_loop": lambda G: dict(G.adj[1][1]),
    "adj_row": lambda G: {nbr: dict(keyed) for nbr, keyed in G.adj[1].items()},
    "degree": lambda G: sorted(G.degree),
    "degree_one": lambda G: G.degree(1),
    "number_of_edges_pair": lambda G: G.number_of_edges(0, 1),
    "number_of_edges": lambda G: G.number_of_edges(),
    "has_edge_keyed": lambda G: G.has_edge(0, 1, 1),
    "has_edge_missing_key": lambda G: G.has_edge(0, 1, 7),
    "has_edge_pair": lambda G: G.has_edge(2, 3),
    "get_edge_data_bundle": lambda G: dict(G.get_edge_data(0, 1)),
    "get_edge_data_default": lambda G: G.get_edge_data(0, 1, 9, default="d"),
    "get_edge_data_missing": lambda G: G.get_edge_data(5, 6),
    "new_edge_key": lambda G: G.new_edge_key(0, 1),
    "new_edge_key_fresh": lambda G: G.new_edge_key(0, 9),
    "neighbors": lambda G: sorted(G.neighbors(1), key=str),
    "nodes": lambda G: sorted(G.nodes, key=str),
    "is_multigraph": lambda G: G.is_multigraph(),
}


@pytest.mark.parametrize("case", sorted(VIEW_CASES))
@pytest.mark.parametrize("cls", [nx.MultiGraph, nx.MultiDiGraph])
def test_views_match_networkx(cls, case):
    rwg, M = _pair(cls)
    read = VIEW_CASES[case]
    assert read(rwg) == read(M)


def test_directed_views_are_successor_only():
    rwg, M = _pair(nx.MultiDiGraph)
    assert sorted(rwg.in_degree) == sorted(M.in_degree)
    assert sorted(rwg.out_degree) == sorted(M.out_degree)
    assert set(rwg.adj[1]) == set(M.adj[1])
    assert set(rwg.adj[3]) == set(M.adj[3]) == set()


def test_multi_edge_view_rejects_malformed_membership():
    rwg, _M = _pair(nx.MultiGraph)
    with pytest.raises(ValueError, match="MultiEdge"):
        assert (0, 1, 2, 3) in rwg.edges


def _mutation_script(G):
    keys = []
    keys.append(G.add_edge(0, 1))
    keys.append(G.add_edge(0, 1))
    keys.append(G.add_edge(0, 1, key="x", w=5))
    keys.append(G.add_edge(0, 1, key=0, color="red"))  # updates key 0 in place
    keys.extend(
        G.add_edges_from(
            [(1, 2), (1, 2, {"w": 1}), (1, 2, "named"), (1, 2, "named", {"w": 2}), (2, 2)],
            tag="bulk",
        )
    )
    G.remove_edge(0, 1)  # pops the most recently added key of the bundle
    keys.append(G.add_edge(0, 1))  # the freed slot gets the next free key
    G.remove_edge(1, 2, key="named")
    G.add_edge(4, 5)
    G.remove_node(2)
    keys.append(G.add_edge(3, 3, key="loop"))
    G.add_edges_from([(3, 4)], weight=7)
    return keys


@pytest.mark.parametrize("cls", [nx.MultiGraph, nx.MultiDiGraph])
def test_mutation_matches_networkx(cls):
    M = cls()
    rwg = RustworkxMultiGraph.empty(directed=M.is_directed())
    assert _mutation_script(rwg) == _mutation_script(M)
    back = convert_to_nx(rwg)
    assert type(back) is cls
    assert back._adj == M._adj
    assert set(back.nodes) == set(M.nodes)
    # Indices stay dense after remove_node, and every edge still has a key.
    assert list(rwg.rx_graph.node_indices()) == list(range(rwg.number_of_nodes()))
    assert set(rwg.edge_keys) == set(rwg.rx_graph.edge_indices())


def test_remove_edge_errors_match_networkx():
    rwg, M = _pair(nx.MultiGraph)
    for G in (rwg, M):
        with pytest.raises(nx.NetworkXError, match="not in the graph"):
            G.remove_edge(0, 9)
        with pytest.raises(nx.NetworkXError, match="with key"):
            G.remove_edge(0, 1, key="missing")
    with pytest.raises(nx.NetworkXError, match="4-tuple"):
        rwg.add_edges_from([(0, 1, 2, 3, 4)])


def test_copy_is_independent():
    rwg, _M = _pair(nx.MultiGraph)
    clone = rwg.copy()
    clone.add_edge(0, 1)
    clone[0][1][0]["weight"] = 99
    assert rwg.number_of_edges(0, 1) == 2
    assert rwg[0][1][0]["weight"] == 3
    assert clone.edge_keys is not rwg.edge_keys


def test_to_directed_matches_networkx():
    rwg, M = _pair(nx.MultiGraph)
    directed = rwg.to_directed()
    assert isinstance(directed, RustworkxMultiGraph) and directed.is_directed()
    assert convert_to_nx(directed)._adj == M.to_directed()._adj
    directed[0][1][0]["weight"] = 42
    assert rwg[0][1][0]["weight"] == 3


def test_to_undirected_merges_antiparallel_keys():
    D = nx.MultiDiGraph()
    D.add_edge(0, 1, key=0, a=1)
    D.add_edge(1, 0, key=0, a=2, b=3)
    D.add_edge(1, 0, key=1)
    D.add_edge(2, 2, key="loop")
    rwg = convert_from_nx(D, preserve_all_attrs=True)
    undirected = rwg.to_undirected()
    assert not undirected.is_directed()
    assert convert_to_nx(undirected)._adj == D.to_undirected()._adj


def test_as_directed_rx_keeps_parallel_edges():
    rwg, M = _pair(nx.MultiGraph)
    directed = as_directed_rx(rwg)
    assert directed.multigraph
    loops = nx.number_of_selfloops(M)
    assert directed.num_edges() == 2 * (M.number_of_edges() - loops) + loops
    assert directed.has_parallel_edges()


def test_str_names_the_class():
    rwg, _M = _pair(nx.MultiDiGraph)
    assert str(rwg).startswith("RustworkxMultiDiGraph with")


# --- the dispatch gate ---------------------------------------------------------


def _dispatchable(name):
    """The decorated NetworkX entry point for ``name`` (has ``orig_func``)."""
    for module in (nx, nx.approximation, nx.bipartite, nx.algorithms.connectivity.stoerwagner):
        func = getattr(module, name, None)
        if func is not None and hasattr(func, "orig_func"):
            return func
    raise LookupError(name)


def _refused_names():
    return sorted(
        name
        for name in ALGORITHMS
        if not getattr(getattr(BackendInterface, name), "multigraph", False)
    )


@pytest.mark.parametrize("name", _refused_names())
def test_refused_functions_report_a_reason(name):
    from test_signatures import REQUIRED_STANDINS

    M = nx.MultiGraph([(0, 1), (0, 1), (1, 2)])
    params = list(inspect.signature(_dispatchable(name).orig_func).parameters.values())
    args = [M]
    for param in params[1:]:
        if param.default is not inspect.Parameter.empty or param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            break
        args.append(REQUIRED_STANDINS.get(param.name, 0))
    result = BackendInterface.can_run(name, tuple(args), {})
    assert isinstance(result, str)
    assert "MultiGraph" in result


def test_gate_handles_graph_classes_as_create_using():
    assert BackendInterface.can_run("path_graph", (3,), {"create_using": nx.MultiGraph}) is not True
    assert BackendInterface.can_run("cycle_graph", (3, nx.MultiDiGraph), {}) is not True
    assert BackendInterface.can_run("path_graph", (3,), {"create_using": nx.Graph}) is True
    # The constructors opted in, so the class passes the gate there.
    assert BackendInterface.can_run("empty_graph", (3, nx.MultiDiGraph), {}) is True


def test_gate_refuses_wrapped_multigraphs_too():
    rwg, _M = _pair(nx.MultiGraph)
    result = BackendInterface.can_run("core_number", (rwg,), {})
    assert isinstance(result, str) and "MultiGraph" in result


def test_explicit_backend_raises_for_refused_function():
    # complement: NetworkX accepts multigraphs, the backend declines them.
    M = nx.MultiGraph([(0, 1), (0, 1), (1, 2)])
    with pytest.raises(NotImplementedError):
        nx.complement(M, backend="rustworkx")


def test_info_refused_set_mirrors_multigraph_flags():
    from nx_rustworkx._info import _MULTIGRAPH_REFUSED, _NO_MULTIGRAPH, get_info

    assert set(_MULTIGRAPH_REFUSED) == set(_refused_names())
    docs = get_info()["functions"]
    for name in ALGORITHMS:
        assert (_NO_MULTIGRAPH in docs[name]["additional_docs"]) == (name in _MULTIGRAPH_REFUSED)


# --- pass-through parity: kernels whose parallel-edge semantics already match --


APPROX = {"rel": 1e-9, "abs": 1e-12}


def _multi_undirected(isolate=True):
    G = nx.MultiGraph()
    G.add_weighted_edges_from(
        [
            (0, 1, 3.0),
            (0, 1, 1.0),
            (1, 2, 2.0),
            (2, 3, 2.5),
            (2, 3, 2.5),
            (3, 4, 1.5),
            (1, 5, 4.0),
            (5, 0, 1.0),
            (4, 4, 1.0),
            (4, 4, 5.0),
            (5, 6, 2.0),
            (6, 7, 1.0),
            (6, 7, 3.0),
            (7, 8, 2.0),
        ]
    )
    if isolate:
        G.add_node(9)
    return G


def _multi_directed(isolate=True):
    D = nx.MultiDiGraph()
    D.add_weighted_edges_from(
        [
            (0, 1, 3.0),
            (0, 1, 1.0),
            (1, 2, 2.0),
            (0, 3, 2.5),
            (3, 2, 2.5),
            (3, 2, 1.0),
            (2, 0, 4.0),
            (2, 4, 1.5),
            (4, 4, 1.0),
            (4, 5, 2.0),
            (5, 6, 1.0),
            (5, 6, 3.0),
            (6, 2, 2.0),
        ]
    )
    if isolate:
        D.add_node(9)
    return D


def _multi_dag():
    D = nx.MultiDiGraph()
    D.add_weighted_edges_from(
        [(0, 1, 1.0), (0, 1, 9.0), (1, 2, 1.0), (0, 2, 1.0), (2, 3, 2.0), (1, 3, 5.0), (1, 3, 2.0)]
    )
    return D


def _path_cost(G, path, weight):
    if weight is None:
        return len(path) - 1
    return sum(min(d[weight] for d in G[u][v].values()) for u, v in zip(path, path[1:]))


def _assert_same(got, expected, G, kind, weight=None):
    if kind == "exact":
        assert got == expected
    elif kind == "mapping":  # a dict on NetworkX >= 3.5, an iterator of pairs before
        assert dict(got) == dict(expected)
    elif kind == "approx":
        assert got == pytest.approx(expected, **APPROX)
    elif kind == "approx_dict":
        assert set(got) == set(expected)
        for key in expected:
            assert got[key] == pytest.approx(expected[key], **APPROX), key
    elif kind == "iterative_dict":  # power iterations converge to slightly different points
        assert set(got) == set(expected)
        for key in expected:
            assert got[key] == pytest.approx(expected[key], rel=1e-3, abs=1e-4), key
    elif kind == "nested_approx":
        got, expected = dict(got), dict(expected)
        assert set(got) == set(expected)
        for key in expected:
            _assert_same(dict(got[key]), dict(expected[key]), G, "approx_dict")
    elif kind == "nested_iterative":
        got, expected = dict(got), dict(expected)
        assert set(got) == set(expected)
        for key in expected:
            _assert_same(dict(got[key]), dict(expected[key]), G, "iterative_dict")
    elif kind == "hits":  # (hubs, authorities)
        for got_part, expected_part in zip(got, expected):
            _assert_same(got_part, expected_part, G, "iterative_dict")
    elif kind == "topological":
        got, expected = list(got), list(expected)
        assert sorted(got) == sorted(expected)
        position = {node: i for i, node in enumerate(got)}
        assert all(position[u] < position[v] for u, v in G.edges())
    elif kind == "node_sets":
        assert sorted(sorted(c) for c in got) == sorted(sorted(c) for c in expected)
    elif kind == "sorted":
        assert sorted(got) == sorted(expected)
    elif kind == "path":
        assert got[0] == expected[0] and got[-1] == expected[-1]
        assert all(G.has_edge(u, v) for u, v in zip(got, got[1:]))
        assert _path_cost(G, got, weight) == pytest.approx(_path_cost(G, expected, weight))
    elif kind == "paths":
        assert set(got) == set(expected)
        for target in expected:
            _assert_same(got[target], expected[target], G, "path", weight)
    elif kind == "all_pairs_paths":
        got = dict(got)
        expected = dict(expected)
        assert set(got) == set(expected)
        for source in expected:
            _assert_same(got[source], expected[source], G, "paths", weight)
    elif kind == "edge_set":
        assert {frozenset(e[:2]) for e in got} == {frozenset(e[:2]) for e in expected}
    elif kind == "layers":
        assert [set(layer) for layer in got] == [set(layer) for layer in expected]
    elif kind == "graph":
        assert set(got.nodes) == set(expected.nodes)
        assert set(got.edges) == set(expected.edges)
    else:  # pragma: no cover - programming error in the table
        raise AssertionError(kind)


U = _multi_undirected
UC = lambda: _multi_undirected(isolate=False)  # noqa: E731
D = _multi_directed
DC = lambda: _multi_directed(isolate=False)  # noqa: E731
W = {"weight": "weight"}

PASS_THROUGH_CASES = [
    # centrality / link analysis
    ("closeness_centrality", U, {}, "approx_dict"),
    ("closeness_centrality", D, {"distance": "weight"}, "approx_dict"),
    ("degree_centrality", U, {}, "approx_dict"),
    ("in_degree_centrality", D, {}, "approx_dict"),
    ("out_degree_centrality", D, {}, "approx_dict"),
    ("group_closeness_centrality", U, {"S": [0, 1]}, "approx"),
    ("group_degree_centrality", U, {"S": [0, 4]}, "approx"),
    ("pagerank", D, {}, "iterative_dict"),
    ("pagerank", U, W, "iterative_dict"),
    ("hits", D, {"max_iter": 500}, "hits"),
    # connectivity
    ("is_connected", UC, {}, "exact"),
    ("connected_components", U, {}, "node_sets"),
    ("number_connected_components", U, {}, "exact"),
    ("node_connected_component", U, {"n": 3}, "exact"),
    ("is_strongly_connected", DC, {}, "exact"),
    ("strongly_connected_components", D, {}, "node_sets"),
    ("number_strongly_connected_components", D, {}, "exact"),
    ("is_weakly_connected", DC, {}, "exact"),
    ("weakly_connected_components", D, {}, "node_sets"),
    ("number_weakly_connected_components", D, {}, "exact"),
    ("is_semiconnected", DC, {}, "exact"),
    ("condensation", D, {}, "graph"),
    # dag
    ("is_directed_acyclic_graph", _multi_dag, {}, "exact"),
    ("is_directed_acyclic_graph", D, {}, "exact"),
    ("topological_sort", _multi_dag, {}, "topological"),
    ("topological_generations", _multi_dag, {}, "layers"),
    ("ancestors", D, {"source": 2}, "exact"),
    ("descendants", D, {"source": 3}, "exact"),
    ("descendants_at_distance", U, {"source": 0, "distance": 2}, "exact"),
    ("dag_longest_path", _multi_dag, {}, "exact"),
    ("dag_longest_path_length", _multi_dag, {}, "approx"),
    ("dag_longest_path_length", _multi_dag, {"weight": None}, "approx"),
    ("transitive_reduction", _multi_dag, {}, "graph"),
    ("immediate_dominators", D, {"start": 0}, "exact"),
    ("dominance_frontiers", D, {"start": 0}, "exact"),
    # distance measures (connected fixtures)
    ("eccentricity", UC, {}, "exact"),
    ("eccentricity", DC, W, "approx_dict"),
    ("diameter", UC, W, "approx"),
    ("radius", UC, {}, "exact"),
    ("center", UC, W, "sorted"),
    ("periphery", UC, W, "sorted"),
    ("average_shortest_path_length", UC, {}, "approx"),
    # shortest paths
    ("shortest_path", U, {"source": 0, "target": 8, "weight": "weight"}, "path"),
    ("shortest_path", D, {"source": 0}, "paths"),
    ("shortest_path", U, W, "all_pairs_paths"),
    ("shortest_path_length", U, {"source": 0, "target": 8, "weight": "weight"}, "approx"),
    ("shortest_path_length", D, W, "nested_approx"),
    ("dijkstra_path", U, {"source": 0, "target": 8}, "path"),
    ("dijkstra_path_length", D, {"source": 0, "target": 6}, "approx"),
    ("bellman_ford_path", D, {"source": 0, "target": 6}, "path"),
    ("bellman_ford_path_length", U, {"source": 0, "target": 8}, "approx"),
    ("single_source_dijkstra_path", D, {"source": 0}, "paths"),
    ("single_source_dijkstra_path_length", U, {"source": 0}, "approx_dict"),
    ("single_source_bellman_ford_path", U, {"source": 0}, "paths"),
    ("single_source_bellman_ford_path_length", D, {"source": 0}, "approx_dict"),
    ("single_source_shortest_path", D, {"source": 0}, "paths"),
    ("single_source_shortest_path_length", U, {"source": 0}, "exact"),
    ("single_target_shortest_path", D, {"target": 2}, "paths"),
    ("single_target_shortest_path_length", D, {"target": 2}, "mapping"),
    ("bidirectional_shortest_path", U, {"source": 0, "target": 8}, "path"),
    ("all_pairs_dijkstra_path", U, {}, "all_pairs_paths"),
    ("all_pairs_dijkstra_path_length", D, {}, "nested_approx"),
    ("all_pairs_bellman_ford_path", D, {}, "all_pairs_paths"),
    ("all_pairs_bellman_ford_path_length", U, {}, "nested_approx"),
    ("all_pairs_shortest_path", U, {}, "all_pairs_paths"),
    ("all_pairs_shortest_path_length", D, {}, "nested_approx"),
    ("astar_path", U, {"source": 0, "target": 8}, "path"),
    ("has_path", D, {"source": 4, "target": 1}, "exact"),
    ("floyd_warshall", D, {}, "nested_approx"),
    ("negative_edge_cycle", D, {}, "exact"),
    # traversal / paths / structure / other
    ("bfs_layers", U, {"sources": 0}, "layers"),
    ("dfs_edges", D, {"source": 0}, "edge_set"),
    ("all_simple_paths", D, {"source": 0, "target": 2}, "sorted"),
    ("simple_cycles", D, {}, "node_sets"),
    ("is_bipartite", U, {}, "exact"),
    ("isolates", U, {}, "sorted"),
    ("number_of_isolates", U, {}, "exact"),
    # Self-loops already colour differently on simple graphs (rustworkx orders
    # by a self-loop-once degree), so the fixture here drops them.
    (
        "greedy_color",
        lambda: nx.MultiGraph(nx.restricted_view(U(), [], [(4, 4, 0), (4, 4, 1)])),
        {},
        "exact",
    ),
    ("is_matching", U, {"matching": {(0, 1), (2, 3)}}, "exact"),
    ("is_isomorphic", U, {"G2": _multi_undirected()}, "exact"),
    ("vf2pp_is_isomorphic", D, {"G2": _multi_directed()}, "exact"),
    ("metric_closure", UC, {}, "graph"),
]


@pytest.mark.parametrize(
    "name,make,kwargs,kind",
    PASS_THROUGH_CASES,
    ids=[
        f"{name}-{make.__name__ if hasattr(make, '__name__') else 'G'}"
        for name, make, *_ in PASS_THROUGH_CASES
    ],
)
def test_pass_through_matches_networkx(name, make, kwargs, kind):
    if name in {"pagerank", "hits"}:
        pytest.importorskip("scipy")
    G = make()
    func = _dispatchable(name)
    assert BackendInterface.can_run(name, (G,), dict(kwargs)) is True
    expected = func.orig_func(G, **kwargs)
    got = func(G, backend="rustworkx", **kwargs)
    weight = kwargs.get("weight")
    if name in {
        "dijkstra_path",
        "dijkstra_path_length",
        "bellman_ford_path",
        "bellman_ford_path_length",
        "single_source_dijkstra_path",
        "single_source_dijkstra_path_length",
        "single_source_bellman_ford_path",
        "single_source_bellman_ford_path_length",
        "all_pairs_dijkstra_path",
        "all_pairs_dijkstra_path_length",
        "all_pairs_bellman_ford_path",
        "all_pairs_bellman_ford_path_length",
        "astar_path",
        "floyd_warshall",
    }:
        weight = "weight"
    _assert_same(got, expected, G, kind, weight)


def _consume(value):
    if inspect.isgenerator(value) or isinstance(value, map):
        return list(value)
    return value


#: Kernels whose default iteration budget is not enough on the cyclic fixture.
SMOKE_KWARGS = {"hits": {"max_iter": 1000}}


def test_multigraph_functions_accept_multigraphs_end_to_end():
    """Every flipped function runs on a multigraph through backend= like NetworkX does."""
    from test_signatures import REQUIRED_STANDINS

    names = sorted(
        name for name in ALGORITHMS if getattr(getattr(BackendInterface, name), "multigraph", False)
    )
    assert names, "nothing flipped"
    problems = []
    for name in names:
        func = _dispatchable(name)
        kwargs = SMOKE_KWARGS.get(name, {})
        for G in (_multi_undirected(isolate=False), _multi_directed(isolate=False)):
            params = list(inspect.signature(func.orig_func).parameters.values())
            args = [G]
            for param in params[1:]:
                if param.default is not inspect.Parameter.empty or param.kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ):
                    break
                # A second graph argument must be the same kind as G.
                standin = G.copy() if param.name in {"G2", "H"} else REQUIRED_STANDINS[param.name]
                args.append(standin)
            if BackendInterface.can_run(name, tuple(args), dict(kwargs)) is not True:
                continue  # declined for a non-multigraph reason (directedness etc.)
            try:
                _consume(func.orig_func(*args, **kwargs))
            except Exception as exc:  # NetworkX refuses this shape; so must we
                try:
                    _consume(func(*args, backend="rustworkx", **kwargs))
                except type(exc):
                    continue
                except Exception as other:
                    problems.append((name, type(G).__name__, f"nx {type(exc).__name__}: {other!r}"))
                    continue
                problems.append((name, type(G).__name__, f"nx raised {type(exc).__name__}"))
                continue
            try:
                _consume(func(*args, backend="rustworkx", **kwargs))
            except Exception as exc:
                problems.append((name, type(G).__name__, repr(exc)))
    assert problems == []


# --- adapted kernels: regression fixtures for every known divergence -------------


def _diamond():
    """0->1 twice, 1->2, 0->3, 3->2: parallel edges must not double a path count."""
    return nx.MultiDiGraph([(0, 1), (0, 1), (1, 2), (0, 3), (3, 2)])


def test_simple_view_invariants():
    from nx_rustworkx.algorithms._utils import simple_view

    for weight in (None, "weight"):
        for G in (_multi_undirected(), _multi_directed()):
            rwg = convert_from_nx(G, preserve_all_attrs=True)
            view = simple_view(rwg, weight)
            assert not view.graph.multigraph
            assert not view.graph.has_parallel_edges()
            assert view.graph.num_nodes() == rwg.number_of_nodes()
            members = sorted(i for bundle in view.bundles.values() for i in bundle)
            assert members == sorted(rwg.rx_graph.edge_indices())
            for collapsed, bundle in view.bundles.items():
                assert bundle == sorted(bundle)
                representative = view.representative(collapsed)
                if weight is None:
                    assert representative == bundle[0]
                else:
                    lightest = min(view.weights[i] for i in bundle)
                    assert representative == next(i for i in bundle if view.weights[i] == lightest)
                u, v = view.graph.get_edge_endpoints_by_index(collapsed)
                ru, rv = rwg.rx_graph.get_edge_endpoints_by_index(representative)
                assert {u, v} == {ru, rv}
                assert view.multiplicity(collapsed) == len(bundle)
            assert simple_view(rwg, weight) is view
            rwg.add_edge(0, 1)
            assert simple_view(rwg, weight) is not view
    with pytest.raises(ValueError):
        simple_view(convert_from_nx(nx.path_graph(3)))


def test_betweenness_does_not_double_count_parallel_paths():
    G = _diamond()
    got = nx.betweenness_centrality(G, normalized=False, backend="rustworkx")
    assert got == pytest.approx({0: 0.0, 1: 0.5, 2: 0.0, 3: 0.5})
    assert got == pytest.approx(nx.betweenness_centrality.orig_func(G, normalized=False))
    for kwargs in ({}, {"endpoints": True}):
        for H in (_multi_undirected(), _multi_directed()):
            _assert_same(
                nx.betweenness_centrality(H, backend="rustworkx", **kwargs),
                nx.betweenness_centrality.orig_func(H, **kwargs),
                H,
                "approx_dict",
            )


def test_edge_betweenness_splits_pairs_over_keys():
    G = _diamond()
    got = nx.edge_betweenness_centrality(G, normalized=False, backend="rustworkx")
    expected = nx.edge_betweenness_centrality.orig_func(G, normalized=False)
    assert set(got) == set(G.edges(keys=True))
    assert got[(0, 1, 0)] == pytest.approx(0.75)
    assert got[(0, 1, 1)] == pytest.approx(0.75)
    assert got[(0, 3, 0)] == pytest.approx(1.5)
    _assert_same(got, expected, G, "approx_dict")
    for H in (_multi_undirected(), _multi_directed()):
        _assert_same(
            nx.edge_betweenness_centrality(H, backend="rustworkx"),
            nx.edge_betweenness_centrality.orig_func(H),
            H,
            "approx_dict",
        )


def test_group_betweenness_matches_on_multigraphs():
    for H in (_multi_undirected(), _multi_directed()):
        got = nx.group_betweenness_centrality(H, [0, 2], backend="rustworkx")
        assert got == pytest.approx(nx.group_betweenness_centrality.orig_func(H, [0, 2]))


def test_bridges_skip_parallel_bundles():
    G = nx.MultiGraph([(0, 1), (0, 1), (1, 2), (2, 3), (2, 3), (3, 4)])
    assert list(nx.bridges(G, backend="rustworkx")) == [(1, 2), (3, 4)]
    assert list(nx.bridges(G, backend="rustworkx")) == list(nx.bridges.orig_func(G))
    # NetworkX's own multigraph fixture from test_bridges.py.
    H = nx.cycle_graph(4, create_using=nx.MultiGraph)
    H.add_edge(1, 2)
    H.add_edge(2, 3, key="x")
    H.add_edges_from([(3, 4), (4, 5), (4, 5)])
    H.remove_edge(2, 3, key="x")
    assert list(nx.bridges(H, backend="rustworkx")) == list(nx.bridges.orig_func(H)) == [(3, 4)]
    assert list(nx.bridges(H, root=5, backend="rustworkx")) == list(nx.bridges.orig_func(H, root=5))
    U = _multi_undirected()
    assert list(nx.bridges(U, backend="rustworkx")) == list(nx.bridges.orig_func(U))


def test_articulation_and_biconnected_match_on_multigraphs():
    for G in (_multi_undirected(), nx.MultiGraph([(0, 1), (0, 1), (1, 2), (2, 3), (2, 3)])):
        assert set(nx.articulation_points(G, backend="rustworkx")) == set(
            nx.articulation_points.orig_func(G)
        )
        _assert_same(
            nx.biconnected_components(G, backend="rustworkx"),
            nx.biconnected_components.orig_func(G),
            G,
            "node_sets",
        )


def test_is_planar_ignores_parallel_edges():
    K5 = nx.MultiGraph(nx.complete_graph(5))
    K5.add_edge(0, 1)
    assert nx.is_planar(K5, backend="rustworkx") is False
    G = nx.MultiGraph([(1, 2)] * 4 + [(2, 3), (3, 1)])
    assert nx.is_planar(G, backend="rustworkx") is True
    D = nx.MultiDiGraph([(0, 1), (1, 0), (1, 2), (2, 1), (2, 0)])
    assert nx.is_planar(D, backend="rustworkx") is nx.is_planar.orig_func(D) is True


def test_path_weight_uses_the_cheapest_parallel_edge():
    G = nx.MultiDiGraph()
    G.add_weighted_edges_from([(0, 1, 1.0), (0, 1, 10.0), (1, 2, 1.0)])
    assert nx.single_source_dijkstra(G, 0, target=2, backend="rustworkx")[0] == 2
    assert nx.single_source_bellman_ford(G, 0, target=2, backend="rustworkx")[0] == 2
    assert nx.astar_path_length(G, 0, 2, heuristic=lambda u, v: 0, backend="rustworkx") == 2
    U = _multi_undirected()
    got_len, got_paths = nx.single_source_dijkstra(U, 0, backend="rustworkx")
    exp_len, exp_paths = nx.single_source_dijkstra.orig_func(U, 0)
    _assert_same(got_len, exp_len, U, "approx_dict")
    _assert_same(got_paths, exp_paths, U, "paths", "weight")


def test_all_shortest_paths_reports_each_node_path_once():
    G = nx.MultiDiGraph([(0, 1), (0, 1), (1, 2)])
    assert list(nx.all_shortest_paths(G, 0, 2, backend="rustworkx")) == [[0, 1, 2]]
    W = nx.MultiDiGraph()
    W.add_weighted_edges_from([(0, 1, 1.0), (0, 1, 5.0), (1, 2, 1.0), (0, 3, 1.0), (3, 2, 1.0)])
    got = sorted(nx.all_shortest_paths(W, 0, 2, weight="weight", backend="rustworkx"))
    assert got == sorted(nx.all_shortest_paths.orig_func(W, 0, 2, weight="weight"))
    got = {t: sorted(p) for t, p in nx.single_source_all_shortest_paths(W, 0, backend="rustworkx")}
    expected = {t: sorted(p) for t, p in nx.single_source_all_shortest_paths.orig_func(W, 0)}
    assert got == expected


def test_minimum_spanning_edges_keys_and_shapes():
    G = nx.MultiGraph()
    G.add_edge(0, 1, key="a", weight=2)
    G.add_edge(0, 1, key="b", weight=1)
    G.add_edge(1, 2, key="c", weight=3)
    mst = nx.minimum_spanning_edges
    assert sorted(mst(G, data=False, backend="rustworkx")) == [(0, 1, "b"), (1, 2, "c")]
    assert sorted(mst(G, backend="rustworkx")) == sorted(mst.orig_func(G))
    assert sorted(mst(G, keys=False, data=False, backend="rustworkx")) == [(0, 1), (1, 2)]
    assert sorted(mst(G, keys=False, backend="rustworkx")) == sorted(mst.orig_func(G, keys=False))
    # An equal-weight bundle resolves to its first key, like NetworkX's stable sort.
    T = nx.MultiGraph()
    T.add_edge(0, 1, key="first", weight=1)
    T.add_edge(0, 1, key="second", weight=1)
    assert list(mst(T, data=False, backend="rustworkx")) == [(0, 1, "first")]
    # The kernel runs lazily so a NaN weight raises on iteration, as NetworkX's does.
    N = nx.MultiGraph()
    N.add_edge(0, 12, weight=float("nan"))
    edges = mst(N, data=False, backend="rustworkx")
    with pytest.raises(ValueError):
        list(edges)
    assert (
        BackendInterface.can_run("minimum_spanning_edges", (G,), {"algorithm": "boruvka"})
        is not True
    )


def test_minimum_spanning_tree_keeps_keys():
    G = nx.MultiGraph()
    G.add_edge(0, 1, key="a", weight=2)
    G.add_edge(0, 1, key="b", weight=1)
    G.add_edge(1, 2, weight=1)
    G.add_edge(2, 3, weight=2)
    G.add_edge(2, 3, weight=1)
    G.graph["name"] = "mst"
    G.nodes[0]["tag"] = "t"
    T = nx.minimum_spanning_tree(G, backend="rustworkx")
    assert isinstance(T, nx.MultiGraph)
    expected = nx.minimum_spanning_tree.orig_func(G)
    assert sorted(T.edges(keys=True, data=True), key=str) == sorted(
        expected.edges(keys=True, data=True), key=str
    )
    assert T.graph == expected.graph and T.nodes[0] == expected.nodes[0]
    U = _multi_undirected()
    total = lambda H: sum(d["weight"] for _u, _v, d in H.edges(data=True))  # noqa: E731
    got = nx.minimum_spanning_tree(U, backend="rustworkx")
    assert total(got) == pytest.approx(total(nx.minimum_spanning_tree.orig_func(U)))
    for u, v, k in got.edges(keys=True):
        bundle = U[u][v]
        assert bundle[k]["weight"] == min(d["weight"] for d in bundle.values())


def test_steiner_tree_keeps_keys():
    # NetworkX's test_multigraph_steiner_tree fixture.
    G = nx.MultiGraph()
    G.add_edges_from(
        [
            (1, 2, 0, {"distance": 1}),
            (2, 3, 0, {"distance": 999}),
            (2, 3, 1, {"distance": 1}),
            (3, 4, 0, {"distance": 1}),
            (3, 5, 0, {"distance": 1}),
        ]
    )
    T = nx.approximation.steiner_tree(
        G, [2, 4, 5], weight="distance", method="kou", backend="rustworkx"
    )
    assert isinstance(T, nx.MultiGraph)
    assert sorted(T.edges(keys=True, data=True)) == [
        (2, 3, 1, {"distance": 1}),
        (3, 4, 0, {"distance": 1}),
        (3, 5, 0, {"distance": 1}),
    ]


def test_find_cycle_reports_keys():
    G = nx.MultiDiGraph([(-1, 0), (0, 1), (1, 0), (1, 0), (2, 1), (3, 1)])
    got = nx.find_cycle(G, backend="rustworkx")
    assert got == nx.find_cycle.orig_func(G) == [(0, 1, 0), (1, 0, 0)]
    L = nx.MultiDiGraph([(2, 2), (2, 2)])
    assert nx.find_cycle(L, backend="rustworkx") == [(2, 2, 0)]


def test_line_graph_names_nodes_with_keys():
    # NetworkX's test_line.py multigraph fixtures.
    for G in (
        nx.MultiGraph([(0, 1), (0, 1), (1, 2), (2, 3)]),
        nx.MultiGraph([(0, 1), (1, 2), (1, 2)]),
    ):
        L = nx.line_graph(G, backend="rustworkx")
        expected = nx.line_graph.orig_func(G)
        assert isinstance(L, nx.MultiGraph)
        assert set(L.nodes) == set(expected.nodes)
        assert {frozenset(e) for e in L.edges()} == {frozenset(e) for e in expected.edges()}
        assert L.number_of_edges() == expected.number_of_edges()


# --- constructors ----------------------------------------------------------------


def test_empty_graph_and_from_edgelist_with_multigraph_create_using():
    from nx_rustworkx.graph import RustworkxMultiGraph

    G = nx.empty_graph(3, create_using=nx.MultiGraph, backend="rustworkx")
    assert isinstance(G, RustworkxMultiGraph) and not G.is_directed()
    assert sorted(G.nodes) == [0, 1, 2] and G.number_of_edges() == 0
    D = nx.empty_graph(["a", "b"], create_using=nx.MultiDiGraph(), backend="rustworkx")
    assert isinstance(D, RustworkxMultiGraph) and D.is_directed()
    assert convert_to_nx(D)._adj == nx.empty_graph(["a", "b"], create_using=nx.MultiDiGraph())._adj
    # default= picks the class when create_using is None, as in NetworkX.
    E = nx.empty_graph(2, default=nx.MultiGraph, backend="rustworkx")
    assert E.is_multigraph()
    # A simple create_using still yields a simple wrapper.
    assert not nx.empty_graph(2, create_using=nx.Graph, backend="rustworkx").is_multigraph()

    edgelist = [(0, 1), (0, 1, {"w": 1}), (0, 1, "k"), (1, 2, "k", {"w": 2}), (2, 2)]
    F = nx.from_edgelist(edgelist, create_using=nx.MultiGraph, backend="rustworkx")
    assert isinstance(F, RustworkxMultiGraph)
    assert (
        convert_to_nx(F)._adj
        == nx.from_edgelist.orig_func(edgelist, create_using=nx.MultiGraph)._adj
    )


def test_multigraph_constructor_inputs_match_networkx():
    from nx_rustworkx.graph import RustworkxMultiGraph

    simple = nx.path_graph(3)
    simple[0][1]["w"] = 2
    wrapped_simple = convert_from_nx(simple, preserve_all_attrs=True)
    multi = _populate(nx.MultiGraph())
    wrapped_multi = convert_from_nx(multi, preserve_all_attrs=True)
    edgelist = [(0, 1), (0, 1), (1, 2, {"w": 1})]
    for data, expected in [
        (None, nx.MultiGraph()),
        (simple, nx.MultiGraph(simple)),
        (wrapped_simple, nx.MultiGraph(simple)),
        (multi, nx.MultiGraph(multi)),
        (wrapped_multi, nx.MultiGraph(multi)),
        (edgelist, nx.MultiGraph(edgelist)),
    ]:
        got = RustworkxMultiGraph.from_incoming(data, directed=False, graph_attrs={"tag": 1})
        assert isinstance(got, RustworkxMultiGraph)
        back = convert_to_nx(got)
        assert back._adj == expected._adj, data
        assert got.graph["tag"] == 1
    # Widening copies attribute dicts rather than sharing them.
    widened = RustworkxMultiGraph.from_incoming(wrapped_simple, directed=False)
    widened[0][1][0]["w"] = 99
    assert wrapped_simple[0][1]["w"] == 2
    # Directed from undirected data duplicates keys both ways, as NetworkX does.
    D = RustworkxMultiGraph.from_incoming(multi, directed=True)
    assert convert_to_nx(D)._adj == nx.MultiDiGraph(multi)._adj
    # A simple class never collapses a multigraph silently.
    from nx_rustworkx.graph import RustworkxGraph

    with pytest.raises(nx.NetworkXError):
        RustworkxGraph.from_incoming(multi, directed=False)
    with pytest.raises(nx.NetworkXError):
        RustworkxGraph.from_incoming(wrapped_multi, directed=False)


def test_constructed_multigraph_dispatches_without_conversion():
    G = nx.empty_graph(0, create_using=nx.MultiGraph, backend="rustworkx")
    G.add_weighted_edges_from([(0, 1, 3.0), (0, 1, 1.0), (1, 2, 1.0), (0, 2, 5.0)])
    ref = nx.MultiGraph()
    ref.add_weighted_edges_from([(0, 1, 3.0), (0, 1, 1.0), (1, 2, 1.0), (0, 2, 5.0)])
    assert nx.shortest_path_length(G, 0, 2, weight="weight") == 2.0
    assert nx.betweenness_centrality(G) == pytest.approx(nx.betweenness_centrality(ref))
    assert list(nx.bridges(G)) == list(nx.bridges(ref))
    T = nx.minimum_spanning_tree(G)
    assert sorted(T.edges(keys=True)) == sorted(nx.minimum_spanning_tree(ref).edges(keys=True))
