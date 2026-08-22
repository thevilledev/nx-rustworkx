"""Spanning trees dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_undirected,
    edge_weight_fn,
    require_nodes,
    require_undirected,
)

__all__ = ["minimum_spanning_tree", "minimum_spanning_edges", "steiner_tree"]

_SUPPORTED_MST_ALGORITHMS = {"kruskal", "prim", "boruvka"}


def _rebuild(rwg, edges, *, keep_graph_attrs=True):
    """Build a NetworkX graph over every node of ``rwg`` with the given edges."""
    out = nx.Graph()
    node_attrs = rwg.node_attrs
    if node_attrs:
        out.add_nodes_from((node, node_attrs.get(node, {})) for node in rwg.index_to_node)
    else:
        out.add_nodes_from(rwg.index_to_node)
    index_to_node = rwg.index_to_node
    for u, v, data in edges:
        payload = data if isinstance(data, dict) else {}
        out.add_edge(index_to_node[u], index_to_node[v], **payload)
    if keep_graph_attrs and rwg.graph:
        out.graph.update(rwg.graph)
    return out


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
    tree = rx.minimum_spanning_tree(rwg.rx_graph, edge_weight_fn(weight))
    return _rebuild(rwg, tree.weighted_edge_list())


minimum_spanning_tree.can_run = _can_run_mst


def _can_run_mst_edges(
    G, algorithm="kruskal", weight="weight", keys=True, data=True, ignore_nan=False, **kwargs
):
    return _can_run_mst(G, weight=weight, algorithm=algorithm, ignore_nan=ignore_nan)


def minimum_spanning_edges(
    G, algorithm="kruskal", weight="weight", keys=True, data=True, ignore_nan=False
):
    """Yield the edges of a minimum spanning forest via rustworkx."""
    _ = algorithm, keys, ignore_nan
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    index_to_node = rwg.index_to_node
    edges = rx.minimum_spanning_edges(rwg.rx_graph, edge_weight_fn(weight))

    def _iter():
        for u, v, payload in edges:
            edge = (index_to_node[u], index_to_node[v])
            if data:
                yield (*edge, payload if isinstance(payload, dict) else {})
            else:
                yield edge

    return _iter()


minimum_spanning_edges.can_run = _can_run_mst_edges


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
    tree = rx.steiner_tree(rwg.rx_graph, terminals, edge_weight_fn(weight))
    out = _rebuild(rwg, tree.weighted_edge_list())
    # NetworkX returns only the nodes the tree actually spans.
    out.remove_nodes_from([node for node in list(out) if out.degree(node) == 0])
    out.add_nodes_from(node for node in terminal_nodes if node not in out)
    return out


steiner_tree.can_run = _can_run_steiner_tree
