"""Graph traversal dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, remap_nodes

__all__ = ["bfs_layers", "dfs_edges"]


def _can_run_dfs_edges(G, source=None, depth_limit=None, sort_neighbors=None, **kwargs):
    if depth_limit is not None:
        return "rustworkx dfs_edges does not support depth_limit"
    if sort_neighbors is not None:
        return "rustworkx dfs_edges does not support sort_neighbors"
    return True


def dfs_edges(G, source=None, depth_limit=None, *, sort_neighbors=None):
    """Yield edges in depth-first order via rustworkx."""
    _ = depth_limit, sort_neighbors
    rwg = as_rw_graph(G)
    index = None
    if source is not None:
        if source not in rwg.node_to_index:
            raise nx.NetworkXError(f"The node {source} is not in the graph.")
        index = rwg.node_to_index[source]
    index_to_node = rwg.index_to_node

    def _iter():
        for u, v in rx.dfs_edges(rwg.rx_graph, index):
            yield index_to_node[u], index_to_node[v]

    return _iter()


dfs_edges.can_run = _can_run_dfs_edges
dfs_edges.multigraph = True


def bfs_layers(G, sources):
    """Yield each BFS layer. The order inside one layer is unspecified."""
    rwg = as_rw_graph(G)
    if rwg.has_node(sources):
        sources = [sources]
    indices = []
    for source in sources:
        if source not in rwg.node_to_index:
            raise nx.NetworkXError(f"The node {source} is not in the graph.")
        indices.append(rwg.node_to_index[source])

    def _iter():
        for layer in rx.bfs_layers(rwg.rx_graph, indices):
            yield remap_nodes(rwg, layer)

    return _iter()


bfs_layers.multigraph = True
