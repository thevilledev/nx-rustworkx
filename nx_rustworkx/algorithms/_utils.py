"""Shared helpers for rustworkx algorithm wrappers."""

from __future__ import annotations

from collections.abc import Mapping
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


def reject_multigraph(G) -> str | None:
    if G.is_multigraph():
        return "nx-rustworkx does not support MultiGraph or MultiDiGraph"
    return None


def reject_callable_weight(weight) -> str | None:
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    return None


def default_can_run(*args, weight=None, **kwargs):
    graphs = [a for a in args if is_graph_like(a)]
    graphs.extend(v for v in kwargs.values() if is_graph_like(v))
    for graph in graphs:
        reason = reject_multigraph(graph)
        if reason:
            return reason
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


def as_directed_rx(rwg: RustworkxGraph):
    """Return a PyDiGraph, treating undirected edges as two directed edges."""
    src = rwg.rx_graph
    if isinstance(src, rx.PyDiGraph):
        return src
    directed = rx.PyDiGraph()
    directed.add_nodes_from(rwg.index_to_node)
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
    reason = reject_multigraph(G)
    if reason:
        return reason
    if G.is_directed():
        return "not implemented for directed type"
    return True


def can_run_directed(G, *args, **kwargs):
    """can_run guard for kernels NetworkX only defines on directed graphs."""
    reason = reject_multigraph(G)
    if reason:
        return reason
    if not G.is_directed():
        return "not implemented for undirected type"
    return True


def require_undirected(rwg) -> None:
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")


def require_directed(rwg) -> None:
    if not rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for undirected type")
