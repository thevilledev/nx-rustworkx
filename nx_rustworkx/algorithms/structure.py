"""Whole-graph structural properties dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_directed_rx,
    as_rw_graph,
    remap_nodes,
)

__all__ = ["color", "is_bipartite", "is_planar", "isolates", "number_of_isolates", "transitivity"]


def is_bipartite(G):
    """Return True if the graph is bipartite."""
    rwg = as_rw_graph(G)
    graph = as_directed_rx(rwg) if rwg.is_directed() else rwg.rx_graph
    return bool(rx.is_bipartite(graph))


is_bipartite.multigraph = True


def is_planar(G):
    """Return True if the graph can be drawn without edge crossings."""
    rwg = as_rw_graph(G)
    # rustworkx's planarity check takes an undirected graph; edge direction
    # does not change planarity, and neither do parallel edges or payloads,
    # so anything else runs on a bare undirected container over the same
    # indices rather than a full to_undirected copy.
    if rwg.is_directed() or rwg.is_multigraph():
        graph = _undirected_simple(rwg.rx_graph)
    else:
        graph = rwg.rx_graph
    return bool(rx.is_planar(graph))


is_planar.multigraph = True


def _undirected_simple(rx_graph):
    """A simple undirected container over the same node indices."""
    graph = rx.PyGraph(multigraph=False)
    graph.add_nodes_from([rx_graph.get_node_data(i) for i in rx_graph.node_indices()])
    graph.add_edges_from([(u, v, None) for u, v in rx_graph.edge_list()])
    return graph


def isolates(G):
    """Yield the nodes with no neighbors."""
    rwg = as_rw_graph(G)
    return iter(remap_nodes(rwg, rx.isolates(rwg.rx_graph)))


isolates.multigraph = True


def number_of_isolates(G):
    """Return the number of nodes with no neighbors."""
    rwg = as_rw_graph(G)
    return len(rx.isolates(rwg.rx_graph))


number_of_isolates.multigraph = True


def transitivity(G):
    """Return the fraction of all possible triangles present in the graph."""
    rwg = as_rw_graph(G)
    return float(rx.transitivity(rwg.rx_graph))


def color(G):
    """Two-coloring of a bipartite graph; isolates get 0 as NetworkX assigns."""
    rwg = as_rw_graph(G)
    two = rx.two_color(rwg.rx_graph)
    if two is None:
        raise nx.NetworkXError("Graph is not bipartite.")
    index_to_node = rwg.index_to_node
    out = {index_to_node[i]: c for i, c in two.items()}
    for i in rx.isolates(rwg.rx_graph):
        out[index_to_node[i]] = 0
    return out


color.multigraph = True
