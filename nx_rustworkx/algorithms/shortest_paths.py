"""Shortest-path algorithms dispatched to rustworkx."""

from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx
import rustworkx as rx

from nx_rustworkx._compat import single_target_shortest_path_length_returns_dict
from nx_rustworkx.algorithms._utils import (
    as_directed_rx,
    as_rw_graph,
    default_can_run,
    default_should_run,
    edge_weight_fn,
    reject_callable_weight,
    remap_length_dict,
    remap_path,
    remap_path_dict,
    require_node,
    reversed_digraph,
    simple_view,
)

__all__ = [
    "all_pairs_bellman_ford_path",
    "all_pairs_bellman_ford_path_length",
    "all_pairs_dijkstra",
    "all_pairs_dijkstra_path",
    "all_pairs_dijkstra_path_length",
    "all_pairs_shortest_path",
    "all_pairs_shortest_path_length",
    "all_shortest_paths",
    "single_source_all_shortest_paths",
    "astar_path",
    "astar_path_length",
    "average_shortest_path_length",
    "bellman_ford_path",
    "bellman_ford_path_length",
    "bidirectional_shortest_path",
    "dijkstra_path",
    "dijkstra_path_length",
    "find_negative_cycle",
    "floyd_warshall",
    "floyd_warshall_numpy",
    "floyd_warshall_predecessor_and_distance",
    "has_path",
    "negative_edge_cycle",
    "shortest_path",
    "shortest_path_length",
    "single_source_bellman_ford",
    "single_source_bellman_ford_path",
    "single_source_bellman_ford_path_length",
    "single_source_dijkstra",
    "single_source_dijkstra_path",
    "single_source_dijkstra_path_length",
    "single_source_shortest_path",
    "single_source_shortest_path_length",
    "single_target_shortest_path",
    "single_target_shortest_path_length",
]


def _inf():
    """Factory for the ``defaultdict`` NetworkX returns from Floyd-Warshall."""
    return math.inf


def _can_run_shortest(G, source=None, target=None, weight=None, method="dijkstra", **kwargs):
    _ = source, target, method, kwargs
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


def _single_source_paths(rx_graph, source_idx, weight, method, target_idx=None):
    """Paths from one source; ``target_idx`` lets the kernel stop early."""
    weight_fn = edge_weight_fn(weight)
    try:
        if method == "bellman-ford":
            return rx.bellman_ford_shortest_paths(
                rx_graph,
                source_idx,
                target=target_idx,
                weight_fn=weight_fn,
            )
        return rx.dijkstra_shortest_paths(
            rx_graph,
            source_idx,
            target=target_idx,
            weight_fn=weight_fn,
        )
    except rx.NegativeCycle as exc:
        _raise_negative_cycle(exc)


def _single_source_lengths(rx_graph, source_idx, weight, method, goal_idx=None):
    """Lengths from one source; ``goal_idx`` lets the kernel stop early."""
    weight_fn = edge_weight_fn(weight)
    try:
        if method == "bellman-ford":
            return rx.bellman_ford_shortest_path_lengths(
                rx_graph,
                source_idx,
                weight_fn,
                goal=goal_idx,
            )
        return rx.dijkstra_shortest_path_lengths(
            rx_graph,
            source_idx,
            weight_fn,
            goal=goal_idx,
        )
    except rx.NegativeCycle as exc:
        _raise_negative_cycle(exc)


def _path_weight(rwg, path, weight):
    """Total weight along an already-computed path of NetworkX node IDs."""
    weight_fn = edge_weight_fn(weight)
    node_to_index = rwg.node_to_index
    rx_graph = rwg.rx_graph
    total = 0.0
    if rwg.is_multigraph():
        # NetworkX's weight function takes the cheapest of the parallel edges;
        # get_edge_data would hand back an arbitrary one.
        for u, v in zip(path, path[1:]):
            total += min(
                weight_fn(data)
                for data in rx_graph.get_all_edge_data(node_to_index[u], node_to_index[v])
            )
        return total
    for u, v in zip(path, path[1:]):
        total += weight_fn(rx_graph.get_edge_data(node_to_index[u], node_to_index[v]))
    return total


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
    method = "dijkstra" if weight is None else _validate_method(method)
    rwg = as_rw_graph(G)

    if source is not None and target is not None:
        if source == target:
            require_node(rwg, source, kind="Source")
            return [source]
        src = require_node(rwg, source, kind="Source")
        tgt = require_node(rwg, target, kind="Target")
        raw = _single_source_paths(rwg.rx_graph, src, weight, method, target_idx=tgt)
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


def _should_run_single_pair_length(G, source=None, target=None, weight=None, **kwargs):
    """NetworkX answers an unweighted single pair with a bidirectional search
    that stops as soon as the two frontiers meet, which converting cannot beat.
    A weighted pair runs the goal-stopped rustworkx lengths kernel and wins
    (measured in benches/bench_single_pair.py)."""
    if source is not None and target is not None and weight is None:
        return "NetworkX's bidirectional search is faster for an unweighted single pair"
    return default_should_run((G,), kwargs)


def _should_run_shortest_path(
    G, source=None, target=None, weight=None, method="dijkstra", **kwargs
):
    if source is not None and target is not None:
        if weight is None:
            return "NetworkX's bidirectional search is faster for an unweighted single pair"
        # Measured in benches/bench_single_pair.py: rustworkx's single-source
        # paths kernel materializes a path for every visited node, which
        # NetworkX's bidirectional Dijkstra never has to do.
        return "NetworkX's bidirectional Dijkstra is faster for a weighted single pair"
    if weight is None:
        # Unweighted paths come from a cheap BFS in NetworkX, so the win would
        # have to come from remapping every path back, which it cannot.
        return "NetworkX's BFS is faster than remapping unweighted paths"
    return default_should_run((G,), kwargs)


shortest_path.can_run = _can_run_shortest
shortest_path.should_run = _should_run_shortest_path
shortest_path.multigraph = True


def shortest_path_length(G, source=None, target=None, weight=None, method="dijkstra"):
    """Shortest path lengths via rustworkx Dijkstra or Bellman-Ford."""
    method = "dijkstra" if weight is None else _validate_method(method)
    rwg = as_rw_graph(G)

    if source is not None and target is not None:
        if source == target:
            require_node(rwg, source, kind="Source")
            return 0
        src = require_node(rwg, source, kind="Source")
        tgt = require_node(rwg, target, kind="Target")
        raw = _single_source_lengths(rwg.rx_graph, src, weight, method, goal_idx=tgt)
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
shortest_path_length.should_run = _should_run_single_pair_length
shortest_path_length.multigraph = True


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
        path = remap_path(rwg, paths[tgt])
        return _path_weight(rwg, path, weight), path

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
single_source_dijkstra.multigraph = True


def dijkstra_path(G, source, target, weight="weight"):
    """One Dijkstra path via rustworkx."""
    path = shortest_path(G, source=source, target=target, weight=weight, method="dijkstra")
    return path


dijkstra_path.can_run = _can_run_st_path
dijkstra_path.multigraph = True


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
bellman_ford_path.multigraph = True


def _reject_cutoff(cutoff, name):
    if cutoff is not None:
        return f"rustworkx {name} does not support cutoff"
    return None


def _can_run_unweighted(G, *args, cutoff=None, **kwargs):
    _ = G, args, kwargs
    return _reject_cutoff(cutoff, "shortest path") or True


def _can_run_weighted(G, *args, cutoff=None, weight="weight", **kwargs):
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    return _reject_cutoff(cutoff, "shortest path") or True


def _lengths_from_source(rwg, source, weight, method, cast=float):
    src = require_node(rwg, source, kind="Source")
    raw = _single_source_lengths(rwg.rx_graph, src, weight, method)
    index_to_node = rwg.index_to_node
    out = {index_to_node[target]: cast(length) for target, length in raw.items()}
    out[source] = cast(0)
    return out


def _paths_from_source(rwg, source, weight, method):
    src = require_node(rwg, source, kind="Source")
    raw = _single_source_paths(rwg.rx_graph, src, weight, method)
    out = remap_path_dict(rwg, raw)
    out[source] = [source]
    return out


def _all_pairs_length_items(rwg, weight, method, cast=float):
    raw = _all_pairs_lengths(rwg.rx_graph, weight, method)
    index_to_node = rwg.index_to_node
    for src_index, targets in raw.items():
        src = index_to_node[src_index]
        mapped = {index_to_node[t]: cast(length) for t, length in targets.items()}
        mapped[src] = cast(0)
        yield src, mapped


def _all_pairs_path_items(rwg, weight, method):
    raw = _all_pairs_paths(rwg.rx_graph, weight, method)
    index_to_node = rwg.index_to_node
    for src_index, targets in raw.items():
        src = index_to_node[src_index]
        mapped = remap_path_dict(rwg, targets)
        mapped[src] = [src]
        yield src, mapped


# --- single source, weighted ---------------------------------------------


def single_source_dijkstra_path(G, source, cutoff=None, weight="weight"):
    """Dijkstra paths from ``source`` via rustworkx."""
    _ = cutoff
    return _paths_from_source(as_rw_graph(G), source, weight, "dijkstra")


single_source_dijkstra_path.can_run = _can_run_weighted
single_source_dijkstra_path.multigraph = True


def single_source_dijkstra_path_length(G, source, cutoff=None, weight="weight"):
    """Dijkstra path lengths from ``source`` via rustworkx."""
    _ = cutoff
    return _lengths_from_source(as_rw_graph(G), source, weight, "dijkstra")


single_source_dijkstra_path_length.can_run = _can_run_weighted
single_source_dijkstra_path_length.multigraph = True


def single_source_bellman_ford_path(G, source, weight="weight"):
    """Bellman-Ford paths from ``source`` via rustworkx."""
    return _paths_from_source(as_rw_graph(G), source, weight, "bellman-ford")


single_source_bellman_ford_path.can_run = _can_run_weighted
single_source_bellman_ford_path.multigraph = True


def single_source_bellman_ford_path_length(G, source, weight="weight"):
    """Bellman-Ford path lengths from ``source`` via rustworkx."""
    return _lengths_from_source(as_rw_graph(G), source, weight, "bellman-ford")


single_source_bellman_ford_path_length.can_run = _can_run_weighted
single_source_bellman_ford_path_length.multigraph = True


def single_source_bellman_ford(G, source, target=None, weight="weight"):
    """Bellman-Ford lengths and paths from ``source`` via rustworkx."""
    rwg = as_rw_graph(G)
    if target is not None:
        if source == target:
            require_node(rwg, source, kind="Source")
            return 0, [source]
        src = require_node(rwg, source, kind="Source")
        tgt = require_node(rwg, target, kind="Target")
        raw = _single_source_paths(rwg.rx_graph, src, weight, "bellman-ford", target_idx=tgt)
        if tgt not in raw:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
        path = remap_path(rwg, raw[tgt])
        return _path_weight(rwg, path, weight), path
    return (
        _lengths_from_source(rwg, source, weight, "bellman-ford"),
        _paths_from_source(rwg, source, weight, "bellman-ford"),
    )


single_source_bellman_ford.can_run = _can_run_weighted
single_source_bellman_ford.multigraph = True


# --- single source, unweighted -------------------------------------------


def single_source_shortest_path(G, source, cutoff=None):
    """Unweighted shortest paths from ``source`` via rustworkx."""
    _ = cutoff
    return _paths_from_source(as_rw_graph(G), source, None, "dijkstra")


single_source_shortest_path.can_run = _can_run_unweighted
single_source_shortest_path.multigraph = True


def single_source_shortest_path_length(G, source, cutoff=None):
    """Unweighted shortest path lengths from ``source`` via rustworkx."""
    _ = cutoff
    return _lengths_from_source(as_rw_graph(G), source, None, "dijkstra", cast=int)


single_source_shortest_path_length.can_run = _can_run_unweighted
single_source_shortest_path_length.multigraph = True


def single_target_shortest_path(G, target, cutoff=None):
    """Unweighted shortest paths to ``target`` via rustworkx."""
    _ = cutoff
    return _paths_toward_target(as_rw_graph(G), target, None, "dijkstra")


single_target_shortest_path.can_run = _can_run_unweighted
single_target_shortest_path.multigraph = True


def single_target_shortest_path_length(G, target, cutoff=None):
    """Unweighted shortest path lengths to ``target`` via rustworkx.

    NetworkX 3.5 changed this from an iterator of pairs to a dict, so match
    whichever shape the installed NetworkX returns.
    """
    _ = cutoff
    lengths = _lengths_toward_target(as_rw_graph(G), target, None, "dijkstra")
    lengths = {node: int(length) for node, length in lengths.items()}
    if single_target_shortest_path_length_returns_dict():
        return lengths
    return iter(lengths.items())


single_target_shortest_path_length.can_run = _can_run_unweighted
single_target_shortest_path_length.multigraph = True


def bidirectional_shortest_path(G, source, target):
    """Unweighted shortest path between two nodes via rustworkx."""
    return shortest_path(G, source=source, target=target)


bidirectional_shortest_path.can_run = _can_run_unweighted
bidirectional_shortest_path.multigraph = True


# --- all pairs ------------------------------------------------------------


def all_pairs_dijkstra(G, cutoff=None, weight="weight"):
    """Yield ``(source, (lengths, paths))`` for every node via rustworkx."""
    _ = cutoff
    rwg = as_rw_graph(G)
    raw_lengths = _all_pairs_lengths(rwg.rx_graph, weight, "dijkstra")
    raw_paths = _all_pairs_paths(rwg.rx_graph, weight, "dijkstra")
    index_to_node = rwg.index_to_node

    def _iter():
        # Remap one source at a time so only one row of Python dicts is alive.
        for src_index, targets in raw_lengths.items():
            src = index_to_node[src_index]
            lengths = {index_to_node[t]: float(length) for t, length in targets.items()}
            lengths[src] = 0.0
            paths = remap_path_dict(rwg, raw_paths[src_index])
            paths[src] = [src]
            yield src, (lengths, paths)

    return _iter()


all_pairs_dijkstra.can_run = _can_run_weighted
all_pairs_dijkstra.multigraph = True


def all_pairs_dijkstra_path(G, cutoff=None, weight="weight"):
    """Yield ``(source, paths)`` for every node via rustworkx Dijkstra."""
    _ = cutoff
    return _all_pairs_path_items(as_rw_graph(G), weight, "dijkstra")


all_pairs_dijkstra_path.can_run = _can_run_weighted
all_pairs_dijkstra_path.multigraph = True


def all_pairs_dijkstra_path_length(G, cutoff=None, weight="weight"):
    """Yield ``(source, lengths)`` for every node via rustworkx Dijkstra."""
    _ = cutoff
    return _all_pairs_length_items(as_rw_graph(G), weight, "dijkstra")


all_pairs_dijkstra_path_length.can_run = _can_run_weighted
all_pairs_dijkstra_path_length.multigraph = True


def all_pairs_bellman_ford_path(G, weight="weight"):
    """Yield ``(source, paths)`` for every node via rustworkx Bellman-Ford."""
    return _all_pairs_path_items(as_rw_graph(G), weight, "bellman-ford")


all_pairs_bellman_ford_path.can_run = _can_run_weighted
all_pairs_bellman_ford_path.multigraph = True


def all_pairs_bellman_ford_path_length(G, weight="weight"):
    """Yield ``(source, lengths)`` for every node via rustworkx Bellman-Ford."""
    return _all_pairs_length_items(as_rw_graph(G), weight, "bellman-ford")


all_pairs_bellman_ford_path_length.can_run = _can_run_weighted
all_pairs_bellman_ford_path_length.multigraph = True


def all_pairs_shortest_path(G, cutoff=None):
    """Yield ``(source, paths)`` for every node, unweighted."""
    _ = cutoff
    return _all_pairs_path_items(as_rw_graph(G), None, "dijkstra")


all_pairs_shortest_path.can_run = _can_run_unweighted
all_pairs_shortest_path.multigraph = True


def all_pairs_shortest_path_length(G, cutoff=None):
    """Yield ``(source, lengths)`` for every node, unweighted."""
    _ = cutoff
    return _all_pairs_length_items(as_rw_graph(G), None, "dijkstra", cast=int)


all_pairs_shortest_path_length.can_run = _can_run_unweighted
all_pairs_shortest_path_length.multigraph = True


# --- point to point -------------------------------------------------------


def dijkstra_path_length(G, source, target, weight="weight"):
    """Dijkstra path length between two nodes via rustworkx."""
    return shortest_path_length(G, source=source, target=target, weight=weight, method="dijkstra")


dijkstra_path_length.can_run = _can_run_st_path
dijkstra_path_length.multigraph = True


def bellman_ford_path_length(G, source, target, weight="weight"):
    """Bellman-Ford path length between two nodes via rustworkx."""
    return shortest_path_length(
        G, source=source, target=target, weight=weight, method="bellman-ford"
    )


bellman_ford_path_length.can_run = _can_run_st_path
bellman_ford_path_length.multigraph = True


def _can_run_all_shortest_paths(G, source, target, weight=None, method="dijkstra", **kwargs):
    _ = source, target
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if method not in {"dijkstra", "unweighted"}:
        return "rustworkx all_shortest_paths only implements the dijkstra method"
    return True


def all_shortest_paths(G, source, target, weight=None, method="dijkstra"):
    """Every shortest path between two nodes via rustworkx."""
    _ = method
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    tgt = require_node(rwg, target, kind="Target")
    if src == tgt:
        return iter([[source]])
    graph, weight_fn = _shortest_path_container(rwg, weight)
    paths = rx.all_shortest_paths(graph, src, tgt, weight_fn=weight_fn)
    if not paths:
        raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
    return iter([remap_path(rwg, path) for path in paths])


def _shortest_path_container(rwg, weight):
    """Graph and weight callback for kernels that enumerate shortest paths.

    rustworkx would emit the same node path once per equal-weight parallel
    edge; NetworkX, working from predecessors, emits it once. The collapsed
    view keeps the lightest edge of every bundle, so the enumeration matches.
    """
    if rwg.is_multigraph():
        view = simple_view(rwg, weight)
        return view.graph, view.weight_fn
    return rwg.rx_graph, edge_weight_fn(weight)


all_shortest_paths.can_run = _can_run_all_shortest_paths
all_shortest_paths.multigraph = True


def _can_run_ssasp(G, source, weight=None, method="dijkstra", **kwargs):
    _ = source
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if method not in {"dijkstra", "unweighted"}:
        return "rustworkx single_source_all_shortest_paths only implements the dijkstra method"
    return True


def single_source_all_shortest_paths(G, source, weight=None, method="dijkstra"):
    """Yield ``(target, all shortest paths)`` for every reachable node."""
    _ = method
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    graph, weight_fn = _shortest_path_container(rwg, weight)
    raw = rx.single_source_all_shortest_paths(graph, src, weight_fn=weight_fn)
    index_to_node = rwg.index_to_node

    def _iter():
        for target, paths in raw.items():
            yield index_to_node[target], [remap_path(rwg, path) for path in paths]

    return _iter()


single_source_all_shortest_paths.can_run = _can_run_ssasp
single_source_all_shortest_paths.multigraph = True


def _heuristic_is_consistent(G, target, heuristic, weight) -> bool:
    """Check ``h(u) <= w(u, v) + h(v)`` on every edge, and ``h(target) == 0``.

    rustworkx's A* never reopens a settled node, so it needs a consistent
    heuristic. NetworkX only asks for an admissible one and still returns an
    optimal path for heuristics that are admissible but not consistent, so an
    inconsistent heuristic has to fall back to NetworkX.
    """
    cache = {}

    def h(node):
        if node not in cache:
            cache[node] = float(heuristic(node, target))
        return cache[node]

    if h(target) != 0:
        return False
    slack = 1e-12
    directed = G.is_directed()
    for u, v, data in G.edges(data=True):
        cost = data.get(weight, 1) if weight is not None else 1
        cost = 1.0 if cost is None else float(cost)
        if h(u) > cost + h(v) + slack:
            return False
        if not directed and h(v) > cost + h(u) + slack:
            return False
    return True


def _astar_check_enabled() -> bool:
    try:
        return bool(nx.config.backends.rustworkx.astar_heuristic_check)
    except Exception:
        return True


def _can_run_astar(G, source, target, heuristic=None, weight="weight", cutoff=None, **kwargs):
    _ = source
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    reason = _reject_cutoff(cutoff, "astar_shortest_path")
    if reason:
        return reason
    if heuristic is not None and _astar_check_enabled():
        if target not in G:
            return True
        if not _heuristic_is_consistent(G, target, heuristic, weight):
            return "rustworkx astar_shortest_path needs a consistent heuristic"
    return True


def _astar_path(rwg, source, target, heuristic, weight):
    src = require_node(rwg, source, kind="Source")
    tgt = require_node(rwg, target, kind="Target")
    if source == target:
        return [source]
    if heuristic is None:
        # A* without a heuristic is Dijkstra, and the dedicated kernel avoids
        # the per-node Python estimate callback while stopping at the target.
        raw = _single_source_paths(rwg.rx_graph, src, weight, "dijkstra", target_idx=tgt)
        if tgt not in raw:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
        return remap_path(rwg, raw[tgt])
    weight_fn = edge_weight_fn(weight)
    try:
        path = rx.astar_shortest_path(
            rwg.rx_graph,
            src,
            lambda payload: payload == target,
            lambda data: weight_fn(data),
            lambda payload: float(heuristic(payload, target)),
        )
    except rx.NoPathFound as exc:
        raise nx.NetworkXNoPath(f"No path between {source} and {target}.") from exc
    return remap_path(rwg, path)


def astar_path(G, source, target, heuristic=None, weight="weight", *, cutoff=None):
    """A* shortest path via rustworkx."""
    _ = cutoff
    return _astar_path(as_rw_graph(G), source, target, heuristic, weight)


astar_path.can_run = _can_run_astar
astar_path.multigraph = True


def astar_path_length(G, source, target, heuristic=None, weight="weight", *, cutoff=None):
    """A* shortest path length via rustworkx."""
    _ = cutoff
    rwg = as_rw_graph(G)
    if heuristic is None:
        # A* without a heuristic is Dijkstra; the lengths kernel stops at the
        # goal without materializing the path.
        src = require_node(rwg, source, kind="Source")
        tgt = require_node(rwg, target, kind="Target")
        if source == target:
            return 0
        raw = _single_source_lengths(rwg.rx_graph, src, weight, "dijkstra", goal_idx=tgt)
        if tgt not in raw:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
        return float(raw[tgt])
    path = _astar_path(rwg, source, target, heuristic, weight)
    return _path_weight(rwg, path, weight)


astar_path_length.can_run = _can_run_astar
astar_path_length.multigraph = True


def has_path(G, source, target):
    """Return True if a path exists between two nodes."""
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    tgt = require_node(rwg, target, kind="Target")
    if src == tgt:
        return True
    return bool(rx.has_path(rwg.rx_graph, src, tgt))


has_path.can_run = _can_run_unweighted
has_path.multigraph = True


# --- dense all pairs ------------------------------------------------------


def _floyd_warshall_reverse(rwg, weight):
    """Distances and successors computed on the reversed graph.

    ``dist[u][v] == dist_r[v][u]`` and ``pred[u][v] == successor_r[v][u]``,
    which is how NetworkX reports predecessors.
    """
    directed = as_directed_rx(rwg)
    if rwg.is_directed():
        directed = reversed_digraph(directed)
    return rx.floyd_warshall_successor_and_distance(directed, weight_fn=edge_weight_fn(weight))


def floyd_warshall_predecessor_and_distance(G, weight="weight"):
    """All-pairs predecessors and distances via rustworkx Floyd-Warshall."""
    rwg = as_rw_graph(G)
    distance_r, successor_r = _floyd_warshall_reverse(rwg, weight)
    nodes = rwg.index_to_node
    n = len(nodes)
    predecessors = {}
    distances = {}
    for u_index in range(n):
        u = nodes[u_index]
        row = defaultdict(_inf)
        pred_row = {}
        for v_index in range(n):
            value = float(distance_r[v_index][u_index])
            row[nodes[v_index]] = value
            if u_index != v_index and value != math.inf:
                pred_row[nodes[v_index]] = nodes[int(successor_r[v_index][u_index])]
        distances[u] = row
        if pred_row:
            predecessors[u] = pred_row
    return predecessors, distances


floyd_warshall_predecessor_and_distance.can_run = _can_run_weighted
floyd_warshall_predecessor_and_distance.multigraph = True


def floyd_warshall(G, weight="weight"):
    """All-pairs distances via rustworkx Floyd-Warshall."""
    # Distances only: skip the reversed-graph copy and the successor matrix
    # floyd_warshall_predecessor_and_distance pays for, and let numpy hand
    # each row over as Python floats in one call.
    rwg = as_rw_graph(G)
    matrix = rx.floyd_warshall_numpy(rwg.rx_graph, weight_fn=edge_weight_fn(weight))
    nodes = rwg.index_to_node
    distances = {}
    for node, row in zip(nodes, matrix.tolist()):
        entry = defaultdict(_inf)
        entry.update(zip(nodes, row))
        distances[node] = entry
    return distances


floyd_warshall.can_run = _can_run_weighted
floyd_warshall.multigraph = True


def _can_run_floyd_numpy(G, nodelist=None, weight="weight", **kwargs):
    reason = default_can_run(G, weight=weight)
    if reason is not True:
        return reason
    if nodelist is not None and set(nodelist) != set(G):
        return "rustworkx floyd_warshall_numpy needs a nodelist covering every node"
    return True


def floyd_warshall_numpy(G, nodelist=None, weight="weight"):
    """All-pairs distance matrix via rustworkx Floyd-Warshall."""
    rwg = as_rw_graph(G)
    matrix = rx.floyd_warshall_numpy(rwg.rx_graph, weight_fn=edge_weight_fn(weight))
    if nodelist is None:
        return matrix
    node_to_index = rwg.node_to_index
    order = [node_to_index[node] for node in nodelist]
    return matrix[order, :][:, order]


floyd_warshall_numpy.can_run = _can_run_floyd_numpy
floyd_warshall_numpy.multigraph = True


# --- negative cycles ------------------------------------------------------


def negative_edge_cycle(G, weight="weight", heuristic=True):
    """Return True if the graph has a negative-weight cycle."""
    _ = heuristic
    rwg = as_rw_graph(G)
    if rwg.number_of_nodes() == 0:
        return False
    return bool(
        rx.negative_edge_cycle(as_directed_rx(rwg), lambda data: edge_weight_fn(weight)(data))
    )


negative_edge_cycle.can_run = _can_run_weighted
negative_edge_cycle.multigraph = True


def find_negative_cycle(G, source, weight="weight"):
    """Return a negative-weight cycle reachable from ``source``."""
    rwg = as_rw_graph(G)
    src = require_node(rwg, source, kind="Source")
    directed = as_directed_rx(rwg)
    reachable = {src} | {int(i) for i in rx.descendants(directed, src)}
    if len(reachable) < directed.num_nodes():
        directed = directed.subgraph(sorted(reachable))
    weight_fn = edge_weight_fn(weight)
    try:
        cycle = rx.find_negative_cycle(directed, lambda data: weight_fn(data))
    except rx.NullGraph as exc:
        raise nx.NetworkXError("No negative cycles detected.") from exc
    except ValueError as exc:
        raise nx.NetworkXError("No negative cycles detected.") from exc
    return [directed[int(index)] for index in cycle]


find_negative_cycle.can_run = _can_run_weighted
find_negative_cycle.multigraph = True


def _can_run_average_shortest_path_length(G, weight=None, method=None, **kwargs):
    if weight is not None:
        return "rustworkx average_shortest_path_length is unweighted only"
    if method not in (None, "unweighted"):
        return f"rustworkx average_shortest_path_length does not implement method={method!r}"
    return True


def average_shortest_path_length(G, weight=None, method=None):
    """Unweighted average shortest path length via rustworkx."""
    _ = weight, method
    rwg = as_rw_graph(G)
    n = rwg.number_of_nodes()
    if n == 0:
        raise nx.NetworkXPointlessConcept(
            "The null graph has no paths, thus there is no average shortest path length"
        )
    if n == 1:
        return 0.0
    _require_connected_for_average(rwg)
    return float(rx.unweighted_average_shortest_path_length(rwg.rx_graph))


def _require_connected_for_average(rwg):
    if rwg.is_directed():
        if not rx.is_strongly_connected(rwg.rx_graph):
            raise nx.NetworkXError("Graph is not strongly connected.")
    elif not rx.is_connected(rwg.rx_graph):
        raise nx.NetworkXError("Graph is not connected.")


average_shortest_path_length.can_run = _can_run_average_shortest_path_length
average_shortest_path_length.multigraph = True
