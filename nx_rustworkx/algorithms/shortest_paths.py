"""Shortest-path algorithms dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    default_can_run,
    edge_weight_fn,
    reject_callable_weight,
    reject_multigraph,
    remap_length_dict,
    remap_path,
    remap_path_dict,
    require_node,
    reversed_digraph,
)

__all__ = [
    "shortest_path",
    "shortest_path_length",
    "single_source_dijkstra",
    "dijkstra_path",
    "bellman_ford_path",
]


def _can_run_shortest(G, source=None, target=None, weight=None, method="dijkstra", **kwargs):
    _ = source, target, method, kwargs
    reason = reject_multigraph(G)
    if reason:
        return reason
    return reject_callable_weight(weight) or True


def _can_run_single_source(
    G,
    source,
    target=None,
    cutoff=None,
    weight="weight",
    **kwargs,
):
    _ = source, target, kwargs
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if cutoff is not None:
        return "rustworkx single_source_dijkstra does not support cutoff"
    return True


def _can_run_st_path(G, source, target, weight="weight", **kwargs):
    _ = source, target, kwargs
    return default_can_run(G, weight=weight)


def _validate_method(method: str) -> str:
    if method not in {"dijkstra", "bellman-ford"}:
        raise ValueError(f"method not supported: {method}")
    return method


def _raise_negative_cycle(exc):
    raise nx.NetworkXUnbounded("Negative cycle detected.") from exc


def _single_source_paths(rx_graph, source_idx, weight, method):
    weight_fn = edge_weight_fn(weight)
    try:
        if method == "bellman-ford":
            return rx.bellman_ford_shortest_paths(
                rx_graph,
                source_idx,
                weight_fn=weight_fn,
            )
        return rx.dijkstra_shortest_paths(
            rx_graph,
            source_idx,
            weight_fn=weight_fn,
        )
    except rx.NegativeCycle as exc:
        _raise_negative_cycle(exc)


def _single_source_lengths(rx_graph, source_idx, weight, method):
    weight_fn = edge_weight_fn(weight)
    try:
        if method == "bellman-ford":
            return rx.bellman_ford_shortest_path_lengths(
                rx_graph,
                source_idx,
                weight_fn,
            )
        return rx.dijkstra_shortest_path_lengths(
            rx_graph,
            source_idx,
            weight_fn,
        )
    except rx.NegativeCycle as exc:
        _raise_negative_cycle(exc)


def _all_pairs_paths(rx_graph, weight, method):
    weight_fn = edge_weight_fn(weight)
    try:
        if method == "bellman-ford":
            return rx.all_pairs_bellman_ford_shortest_paths(rx_graph, weight_fn)
        return rx.all_pairs_dijkstra_shortest_paths(rx_graph, weight_fn)
    except rx.NegativeCycle as exc:
        _raise_negative_cycle(exc)


def _all_pairs_lengths(rx_graph, weight, method):
    weight_fn = edge_weight_fn(weight)
    try:
        if method == "bellman-ford":
            return rx.all_pairs_bellman_ford_path_lengths(rx_graph, weight_fn)
        return rx.all_pairs_dijkstra_path_lengths(rx_graph, weight_fn)
    except rx.NegativeCycle as exc:
        _raise_negative_cycle(exc)


def _paths_toward_target(rwg, target, weight, method):
    target_idx = require_node(rwg, target, kind="Target")
    rx_graph = rwg.rx_graph
    if rwg.is_directed():
        rx_graph = reversed_digraph(rx_graph)
    raw = _single_source_paths(rx_graph, target_idx, weight, method)
    out = {}
    for src_idx, path in raw.items():
        src = rwg.index_to_node[src_idx]
        out[src] = list(reversed(remap_path(rwg, path)))
    out[target] = [target]
    return out


def _lengths_toward_target(rwg, target, weight, method):
    target_idx = require_node(rwg, target, kind="Target")
    rx_graph = rwg.rx_graph
    if rwg.is_directed():
        rx_graph = reversed_digraph(rx_graph)
    raw = _single_source_lengths(rx_graph, target_idx, weight, method)
    out = remap_length_dict(rwg, raw)
    out[target] = 0.0
    return out


def shortest_path(G, source=None, target=None, weight=None, method="dijkstra"):
    """Shortest paths via rustworkx Dijkstra or Bellman-Ford."""
    if weight is None:
        method = "dijkstra"
    else:
        method = _validate_method(method)
    rwg = as_rw_graph(G)

    if source is not None and target is not None:
        if source == target:
            require_node(rwg, source, kind="Source")
            return [source]
        src = require_node(rwg, source, kind="Source")
        tgt = require_node(rwg, target, kind="Target")
        raw = _single_source_paths(rwg.rx_graph, src, weight, method)
        if tgt not in raw:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
        return remap_path(rwg, raw[tgt])

    if source is not None:
        src = require_node(rwg, source, kind="Source")
        raw = _single_source_paths(rwg.rx_graph, src, weight, method)
        out = remap_path_dict(rwg, raw)
        out[source] = [source]
        return out

    if target is not None:
        return _paths_toward_target(rwg, target, weight, method)

    raw = _all_pairs_paths(rwg.rx_graph, weight, method)
    def _iter():
        for src_idx, targets in raw.items():
            src = rwg.index_to_node[src_idx]
            mapped = remap_path_dict(rwg, targets)
            mapped[src] = [src]
            yield src, mapped

    return _iter()


shortest_path.can_run = _can_run_shortest


def shortest_path_length(G, source=None, target=None, weight=None, method="dijkstra"):
    """Shortest path lengths via rustworkx Dijkstra or Bellman-Ford."""
    if weight is None:
        method = "dijkstra"
    else:
        method = _validate_method(method)
    rwg = as_rw_graph(G)

    if source is not None and target is not None:
        if source == target:
            require_node(rwg, source, kind="Source")
            return 0
        src = require_node(rwg, source, kind="Source")
        tgt = require_node(rwg, target, kind="Target")
        raw = _single_source_lengths(rwg.rx_graph, src, weight, method)
        if tgt not in raw:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
        return float(raw[tgt])

    if source is not None:
        src = require_node(rwg, source, kind="Source")
        raw = _single_source_lengths(rwg.rx_graph, src, weight, method)
        out = remap_length_dict(rwg, raw)
        out[source] = 0.0
        return out

    if target is not None:
        return _lengths_toward_target(rwg, target, weight, method)

    raw = _all_pairs_lengths(rwg.rx_graph, weight, method)
    def _iter():
        for src_idx, targets in raw.items():
            src = rwg.index_to_node[src_idx]
            mapped = remap_length_dict(rwg, targets)
            mapped[src] = 0.0
            yield src, mapped

    return _iter()


shortest_path_length.can_run = _can_run_shortest


def single_source_dijkstra(G, source, target=None, cutoff=None, weight="weight"):
    """Single-source Dijkstra lengths and paths via rustworkx."""
    _ = cutoff
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    if target is not None:
        if source == target:
            return 0, [source]
        tgt = require_node(rwg, target, kind="Target")
        paths = rx.dijkstra_shortest_paths(
            rwg.rx_graph,
            src,
            target=tgt,
            weight_fn=edge_weight_fn(weight),
        )
        if tgt not in paths:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
        lengths = rx.dijkstra_shortest_path_lengths(
            rwg.rx_graph,
            src,
            edge_weight_fn(weight),
            goal=tgt,
        )
        return float(lengths[tgt]), remap_path(rwg, paths[tgt])

    paths = remap_path_dict(
        rwg,
        rx.dijkstra_shortest_paths(
            rwg.rx_graph,
            src,
            weight_fn=edge_weight_fn(weight),
        ),
    )
    lengths = remap_length_dict(
        rwg,
        rx.dijkstra_shortest_path_lengths(
            rwg.rx_graph,
            src,
            edge_weight_fn(weight),
        ),
    )
    paths[source] = [source]
    lengths[source] = 0.0
    return lengths, paths


single_source_dijkstra.can_run = _can_run_single_source


def dijkstra_path(G, source, target, weight="weight"):
    """One Dijkstra path via rustworkx."""
    path = shortest_path(G, source=source, target=target, weight=weight, method="dijkstra")
    return path


dijkstra_path.can_run = _can_run_st_path


def bellman_ford_path(G, source, target, weight="weight"):
    """One Bellman-Ford path via rustworkx."""
    return shortest_path(
        G,
        source=source,
        target=target,
        weight=weight,
        method="bellman-ford",
    )


bellman_ford_path.can_run = _can_run_st_path
