"""Graph traversal dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, reject_multigraph

__all__ = ["dfs_edges"]


def _can_run_dfs_edges(G, source=None, depth_limit=None, sort_neighbors=None, **kwargs):
    reason = reject_multigraph(G)
    if reason:
        return reason
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
