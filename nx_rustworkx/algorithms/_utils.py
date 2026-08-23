"""Shared helpers for rustworkx algorithm wrappers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import networkx as nx
import rustworkx as rx

from nx_rustworkx.convert import convert_from_nx
from nx_rustworkx.graph import RustworkxGraph

MIN_NODES = 200
MIN_EDGES = 400


def as_rw_graph(G) -> RustworkxGraph:
    """Return a ``RustworkxGraph``, converting a NetworkX graph if needed.

    The dispatcher normally hands us an already-converted graph. Direct calls
    do not, so keep edge attributes here or weighted kernels would silently
    read every edge as weight 1.
    """
    if isinstance(G, RustworkxGraph):
        return G
    return convert_from_nx(G, preserve_edge_attrs=True)


def is_graph_like(obj: Any) -> bool:
    if isinstance(obj, RustworkxGraph):
        return True
    return (
        hasattr(obj, "is_directed")
        and hasattr(obj, "is_multigraph")
        and hasattr(obj, "number_of_nodes")
    )


def graphs_from_call(args, kwargs) -> list:
    found = []
    for value in args:
        if is_graph_like(value):
            found.append(value)
    for value in kwargs.values():
        if is_graph_like(value):
            found.append(value)
    return found


def is_multigraph_input(obj) -> bool:
    """True for a MultiGraph/MultiDiGraph instance or class (``create_using``)."""
    if isinstance(obj, type):
        return issubclass(obj, nx.MultiGraph)
    return bool(obj.is_multigraph())


def multigraph_reason(name, args, kwargs) -> str | None:
    """The can_run refusal for a multigraph argument, or None if there is none.

    ``BackendInterface.can_run`` applies this to every function that does not
    declare ``multigraph = True``; it runs before the function's own checker so
    a refused multigraph never reaches per-function logic.
    """
    for graph in graphs_from_call(args, kwargs):
        if is_multigraph_input(graph):
            return f"nx-rustworkx {name} does not accept MultiGraph or MultiDiGraph inputs"
    return None


def reject_callable_weight(weight) -> str | None:
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    return None


def default_can_run(*args, weight=None, **kwargs):
    _ = args, kwargs
    return reject_callable_weight(weight) or True


def too_small(G, min_nodes=MIN_NODES, min_edges=MIN_EDGES) -> bool:
    return G.number_of_nodes() < min_nodes or G.number_of_edges() < min_edges


def size_thresholds():
    min_nodes = MIN_NODES
    min_edges = MIN_EDGES
    try:
        cfg = nx.config.backends.rustworkx
        min_nodes = int(cfg.min_nodes)
        min_edges = int(cfg.min_edges)
    except Exception:
        pass
    return min_nodes, min_edges


def default_should_run(args, kwargs):
    graphs = graphs_from_call(args, kwargs)
    if not graphs:
        return True
    if all(isinstance(graph, RustworkxGraph) for graph in graphs):
        return True
    min_nodes, min_edges = size_thresholds()
    for graph in graphs:
        if too_small(graph, min_nodes=min_nodes, min_edges=min_edges):
            n = graph.number_of_nodes()
            m = graph.number_of_edges()
            return (
                f"graph too small for rustworkx conversion "
                f"(n={n} < {min_nodes} or m={m} < {min_edges})"
            )
    return True


def require_node(rwg: RustworkxGraph, node, *, kind: str = "Node"):
    try:
        return rwg.node_to_index[node]
    except KeyError as exc:
        raise nx.NodeNotFound(f"{kind} {node} is not in G") from exc


def remap_scores(rwg: RustworkxGraph, mapping: Mapping[int, float]) -> dict:
    index_to_node = rwg.index_to_node
    return {index_to_node[i]: float(value) for i, value in mapping.items()}


def remap_path(rwg: RustworkxGraph, path) -> list:
    index_to_node = rwg.index_to_node
    return [index_to_node[i] for i in path]


def remap_path_dict(rwg: RustworkxGraph, paths: Mapping) -> dict:
    index_to_node = rwg.index_to_node
    return {index_to_node[target]: remap_path(rwg, path) for target, path in paths.items()}


def remap_length_dict(rwg: RustworkxGraph, lengths: Mapping) -> dict:
    index_to_node = rwg.index_to_node
    return {index_to_node[target]: float(length) for target, length in lengths.items()}


def remap_components(rwg: RustworkxGraph, components) -> list[set]:
    index_to_node = rwg.index_to_node
    return [{index_to_node[i] for i in component} for component in components]


def edge_weight_fn(weight):
    if weight is None:
        return lambda _data: 1.0
    if callable(weight):
        raise TypeError("nx-rustworkx does not support custom weight callables")

    def _fn(data):
        if data is None:
            return 1.0
        if isinstance(data, dict):
            value = data.get(weight, 1.0)
            return 1.0 if value is None else float(value)
        return float(data)

    return _fn


@dataclass(frozen=True)
class SimpleView:
    """``rwg.rx_graph`` with every bundle of parallel edges collapsed to one edge.

    ``graph`` is a ``multigraph=False`` container over the same node indices.
    The payload of collapsed edge ``c`` is the ORIGINAL edge index of the
    bundle's representative: the lowest index (NetworkX's first key) when
    unweighted, else the lowest-index member of minimum weight, which is
    NetworkX's min-over-parallel-edges rule with its stable first-key tie-break.
    Kernels that count paths (betweenness) or walk DFS trees (bridges,
    articulation points) run here, since NetworkX reads ``G[u][v]`` and never
    sees parallel edges; kernels that return edges run here so the payload
    leads back to a NetworkX key.
    """

    graph: Any
    bundles: dict[int, list[int]]  # collapsed index -> original indices, ascending
    orig_to_simple: dict[int, int]
    weights: dict[int, float] | None  # original index -> weight; None when unweighted

    def representative(self, collapsed: int) -> int:
        return self.graph.get_edge_data_by_index(collapsed)

    def multiplicity(self, collapsed: int) -> int:
        return len(self.bundles[collapsed])

    @property
    def weight_fn(self):
        """Weight callback for kernels run on ``graph`` (payload = original index)."""
        if self.weights is None:
            return lambda _index: 1.0
        return self.weights.__getitem__


def simple_view(rwg: RustworkxGraph, weight=None) -> SimpleView:
    """The cached :class:`SimpleView` of a multigraph wrapper for ``weight``.

    Cached on the wrapper's ``__networkx_cache__`` under a backend-private key,
    so every mutator's ``.clear()`` invalidates it and NetworkX's own
    ``"backends"`` entry is untouched.
    """
    if not rwg.is_multigraph():
        raise ValueError("simple_view is only defined for multigraph wrappers")
    cache = rwg.__networkx_cache__
    views = cache.setdefault("nx_rustworkx", {}) if cache is not None else {}
    key = ("simple_view", weight)
    view = views.get(key)
    if view is None:
        view = views[key] = _build_simple_view(rwg, weight)
    return view


def _build_simple_view(rwg: RustworkxGraph, weight) -> SimpleView:
    rx_graph = rwg.rx_graph
    edge_map = rx_graph.edge_index_map()
    indices = sorted(edge_map)  # ascending index == NetworkX key order for converted graphs
    weights = None
    if weight is not None:
        weight_fn = edge_weight_fn(weight)
        weights = {index: weight_fn(edge_map[index][2]) for index in indices}
    graph = rx.PyDiGraph(multigraph=False) if rwg.is_directed() else rx.PyGraph(multigraph=False)
    graph.add_nodes_from([rx_graph.get_node_data(i) for i in rx_graph.node_indices()])
    # On a multigraph=False container add_edges_from updates a duplicate pair in
    # place and hands back the existing index, so one Rust call both collapses
    # the bundles and yields the original -> collapsed map.
    collapsed = graph.add_edges_from(
        [(edge_map[index][0], edge_map[index][1], index) for index in indices]
    )
    bundles: dict[int, list[int]] = {}
    for index, c in zip(indices, collapsed):
        bundles.setdefault(c, []).append(index)
    for c, members in bundles.items():
        if len(members) > 1:
            # add_edges_from left the newest member as payload; NetworkX wants
            # the first key, or the first of the lightest when weighted.
            representative = (
                members[0] if weights is None else min(members, key=weights.__getitem__)
            )
            graph.update_edge_by_index(c, representative)
    orig_to_simple = {index: c for c, members in bundles.items() for index in members}
    return SimpleView(graph, bundles, orig_to_simple, weights)


def keyed_edge(rwg: RustworkxGraph, index: int, *, data=False, edge_map=None):
    """NetworkX's ``(u, v, key)`` or ``(u, v, key, attrs)`` for rustworkx edge ``index``."""
    if edge_map is None:
        u, v = rwg.rx_graph.get_edge_endpoints_by_index(index)
        payload = rwg.rx_graph.get_edge_data_by_index(index) if data else None
    else:
        u, v, payload = edge_map[index]
    index_to_node = rwg.index_to_node
    edge = (index_to_node[u], index_to_node[v], rwg.edge_keys[index])
    if not data:
        return edge
    return (*edge, payload if isinstance(payload, dict) else {})


def as_directed_rx(rwg: RustworkxGraph):
    """Return a PyDiGraph, treating undirected edges as two directed edges."""
    src = rwg.rx_graph
    if isinstance(src, rx.PyDiGraph):
        return src
    # The wrapper, not ``src.multigraph``, decides: kernel-built simple graphs
    # report multigraph=True, while a converted multigraph must keep its
    # parallel edges so weight-summing kernels (pagerank, hits) see them all.
    directed = rx.PyDiGraph(multigraph=rwg.is_multigraph())
    directed.add_nodes_from(src.get_node_data(i) for i in src.node_indices())
    for u, v, data in src.weighted_edge_list():
        directed.add_edge(u, v, data)
        if u != v:
            directed.add_edge(v, u, data)
    return directed


def reversed_digraph(rx_graph):
    """Copy a PyDiGraph and reverse edge direction without mutating the cache."""
    copied = rx_graph.copy()
    copied.reverse()
    return copied


def require_nodes(rwg: RustworkxGraph, nodes, *, kind: str = "Node") -> list[int]:
    """Map an iterable of NetworkX nodes to rustworkx indices."""
    nodes = list(nodes)  # a one-shot iterator must survive both passes below
    node_to_index = rwg.node_to_index
    missing = [n for n in nodes if n not in node_to_index]
    if missing:
        raise nx.NodeNotFound(f"{kind}(s) {set(missing)} not in G")
    return [node_to_index[n] for n in nodes]


def remap_nodes(rwg: RustworkxGraph, indices) -> list:
    index_to_node = rwg.index_to_node
    return [index_to_node[i] for i in indices]


def can_run_undirected(G, *args, **kwargs):
    """can_run guard for kernels NetworkX only defines on undirected graphs."""
    if G.is_directed():
        return "not implemented for directed type"
    return True


def can_run_directed(G, *args, **kwargs):
    """can_run guard for kernels NetworkX only defines on directed graphs."""
    if not G.is_directed():
        return "not implemented for undirected type"
    return True


def require_undirected(rwg) -> None:
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")


def require_directed(rwg) -> None:
    if not rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for undirected type")


#: Functions the backend implements but should not be chosen for automatically.
#:
#: For each of these, ``benches/bench_parity.py`` measures rustworkx slower than
#: NetworkX at both n=400 and n=2000, and the reason is structural rather than a
#: constant factor: NetworkX stops early (``has_path``,
#: ``bidirectional_shortest_path``, ``descendants_at_distance``,
#: ``is_bipartite``, ``find_cycle``, ``is_maximal_matching``), the result is
#: quadratic in the graph so building it in Python dominates (``complement``,
#: ``all_pairs_shortest_path``, the ``single_source_``/``single_target_`` path
#: variants), or the kernel is so cheap that only the remap is left (the degree
#: centralities, ``group_degree_centrality``).
#:
#: ``backend="rustworkx"`` still runs them, so nothing becomes unreachable. Only
#: ``nx.config.backend_priority`` skips them.
NO_AUTO_DISPATCH = frozenset(
    {
        "all_pairs_shortest_path",
        "all_shortest_paths",
        "bellman_ford_path",
        "bidirectional_shortest_path",
        "complement",
        "cycle_basis",
        "degree_centrality",
        "descendants_at_distance",
        "dijkstra_path",
        "find_cycle",
        "find_negative_cycle",
        "group_degree_centrality",
        "is_maximal_matching",
        "has_path",
        "in_degree_centrality",
        "is_bipartite",
        "negative_edge_cycle",
        "out_degree_centrality",
        "single_source_dijkstra",
        "single_source_shortest_path",
        "single_source_shortest_path_length",
        "single_target_shortest_path",
        "single_target_shortest_path_length",
        "is_weakly_connected",
        "weakly_connected_components",
    }
)

NO_AUTO_DISPATCH_REASON = (
    "NetworkX is measured faster than converting for this function; "
    'pass backend="rustworkx" to run it anyway'
)
