"""Spanning trees dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx._compat import metric_closure_is_deprecated
from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_undirected,
    edge_weight_fn,
    require_nodes,
    require_undirected,
    simple_view,
)

__all__ = ["metric_closure", "minimum_spanning_tree", "minimum_spanning_edges", "steiner_tree"]

_SUPPORTED_MST_ALGORITHMS = {"kruskal", "prim", "boruvka"}


def _rebuild(rwg, edges, *, keep_graph_attrs=True):
    """Build a NetworkX graph over every node of ``rwg`` with the given edges.

    For a multigraph wrapper the edges come from its collapsed view, so each
    payload is an original edge index that leads back to the NetworkX key.
    """
    multigraph = rwg.is_multigraph()
    out = nx.MultiGraph() if multigraph else nx.Graph()
    node_attrs = rwg.node_attrs
    if node_attrs:
        out.add_nodes_from((node, node_attrs.get(node, {})) for node in rwg.index_to_node)
    else:
        out.add_nodes_from(rwg.index_to_node)
    index_to_node = rwg.index_to_node
    if multigraph:
        rx_graph = rwg.rx_graph
        edge_keys = rwg.edge_keys
        for u, v, index in edges:
            payload = rx_graph.get_edge_data_by_index(index)
            attrs = payload if isinstance(payload, dict) else {}
            out.add_edges_from([(index_to_node[u], index_to_node[v], edge_keys[index], attrs)])
    else:
        # 3-tuples rather than add_edge(u, v, **data): NetworkX allows
        # non-string attribute keys, which keyword expansion rejects.
        out.add_edges_from(
            (index_to_node[u], index_to_node[v], data if isinstance(data, dict) else {})
            for u, v, data in edges
        )
    if keep_graph_attrs and rwg.graph:
        out.graph.update(rwg.graph)
    return out


def _tree_container(rwg, weight):
    """Graph and weight callback for the spanning-tree kernels."""
    if rwg.is_multigraph():
        view = simple_view(rwg, weight)
        return view.graph, view.weight_fn
    return rwg.rx_graph, edge_weight_fn(weight)


def _can_run_mst(G, weight="weight", algorithm="kruskal", ignore_nan=False, **kwargs):
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    if algorithm not in _SUPPORTED_MST_ALGORITHMS:
        return f"unknown spanning tree algorithm {algorithm!r}"
    if ignore_nan:
        return "rustworkx minimum_spanning_tree does not support ignore_nan"
    if algorithm == "boruvka" and G.is_multigraph():
        return "NetworkX's boruvka_mst_edges rejects multigraphs"
    return True


def minimum_spanning_tree(G, weight="weight", algorithm="kruskal", ignore_nan=False):
    """Return a minimum spanning forest via rustworkx.

    rustworkx always runs Kruskal's algorithm; ``algorithm`` only picks which
    minimum spanning forest NetworkX would have built, and every choice has the
    same total weight.
    """
    _ = algorithm, ignore_nan
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    graph, weight_fn = _tree_container(rwg, weight)
    tree = rx.minimum_spanning_tree(graph, weight_fn)
    return _rebuild(rwg, tree.weighted_edge_list())


minimum_spanning_tree.can_run = _can_run_mst
minimum_spanning_tree.multigraph = True


def _can_run_mst_edges(
    G, algorithm="kruskal", weight="weight", keys=True, data=True, ignore_nan=False, **kwargs
):
    return _can_run_mst(G, weight=weight, algorithm=algorithm, ignore_nan=ignore_nan)


def minimum_spanning_edges(
    G, algorithm="kruskal", weight="weight", keys=True, data=True, ignore_nan=False
):
    """Yield the edges of a minimum spanning forest via rustworkx.

    On a multigraph the edges carry NetworkX keys when ``keys`` is set, and
    the lightest edge of every parallel bundle is the one chosen.
    """
    _ = algorithm, ignore_nan
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    index_to_node = rwg.index_to_node
    multigraph = rwg.is_multigraph()
    graph, weight_fn = _tree_container(rwg, weight)

    def _iter():
        # Run the kernel lazily: NetworkX's generator raises for a NaN weight
        # only once iterated, and its tests rely on that timing.
        for u, v, payload in rx.minimum_spanning_edges(graph, weight_fn):
            edge = (index_to_node[u], index_to_node[v])
            if multigraph:
                if keys:
                    edge = (*edge, rwg.edge_keys[payload])
                payload = rwg.rx_graph.get_edge_data_by_index(payload)
            if data:
                yield (*edge, payload if isinstance(payload, dict) else {})
            else:
                yield edge

    return _iter()


minimum_spanning_edges.can_run = _can_run_mst_edges
minimum_spanning_edges.multigraph = True


def _can_run_steiner_tree(G, terminal_nodes, weight="weight", method=None, **kwargs):
    _ = terminal_nodes
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    if method not in (None, "kou"):
        return f"rustworkx steiner_tree does not implement method={method!r}"
    return True


def steiner_tree(G, terminal_nodes, weight="weight", method=None):
    """Return an approximate Steiner tree via rustworkx's Kou algorithm."""
    _ = method
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    terminals = require_nodes(rwg, terminal_nodes, kind="Terminal")
    graph, weight_fn = _tree_container(rwg, weight)
    tree = rx.steiner_tree(graph, terminals, weight_fn)
    out = _rebuild(rwg, tree.weighted_edge_list())
    # NetworkX returns only the nodes the tree actually spans: a lone terminal
    # spans nothing, so it is absent from NetworkX's result too.
    out.remove_nodes_from([node for node in list(out) if out.degree(node) == 0])
    return out


steiner_tree.can_run = _can_run_steiner_tree
steiner_tree.multigraph = True


def _can_run_metric_closure(G, weight="weight", **kwargs):
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    if G.number_of_nodes() < 2:
        return "rustworkx metric_closure needs at least two nodes"
    return True


def metric_closure(G, weight="weight"):
    """Return the metric closure: a complete graph of shortest-path distances."""
    if metric_closure_is_deprecated():
        # NetworkX emits this inside the function body the backend replaces, so
        # repeat it here to keep the deprecation visible.
        import warnings

        warnings.warn(
            "metric_closure is deprecated and will be removed in NetworkX 3.8.\n"
            "Use nx.all_pairs_shortest_path_length instead.",
            category=DeprecationWarning,
            stacklevel=3,
        )
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    if rwg.number_of_nodes() < 2:
        raise nx.NetworkXError("metric_closure needs at least two nodes")
    # Check connectivity before the kernel: rustworkx's metric_closure panics
    # (rather than erroring) on a disconnected graph with an isolated node.
    if not rx.is_connected(rwg.rx_graph):
        raise nx.NetworkXError("G is not a connected graph. metric_closure is not defined.")
    closure = rx.metric_closure(rwg.rx_graph, edge_weight_fn(weight))
    index_to_node = rwg.index_to_node
    out = nx.Graph()
    out.add_nodes_from(rwg.node_to_index)
    for u, v, (distance, path) in closure.weighted_edge_list():
        out.add_edge(
            index_to_node[u],
            index_to_node[v],
            distance=distance,
            path=[index_to_node[i] for i in path],
        )
    return out


metric_closure.can_run = _can_run_metric_closure
metric_closure.multigraph = True
