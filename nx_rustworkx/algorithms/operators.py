"""Graph operators dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph

__all__ = ["complement", "cartesian_product", "line_graph", "tensor_product"]


def complement(G):
    """Return the graph complement via rustworkx."""
    rwg = as_rw_graph(G)
    complemented = rx.complement(rwg.rx_graph)
    out = nx.DiGraph() if rwg.is_directed() else nx.Graph()
    node_attrs = rwg.node_attrs
    if node_attrs:
        out.add_nodes_from((node, node_attrs.get(node, {})) for node in rwg.index_to_node)
    else:
        out.add_nodes_from(rwg.index_to_node)
    index_to_node = rwg.index_to_node
    out.add_edges_from((index_to_node[u], index_to_node[v]) for u, v in complemented.edge_list())
    return out


def _product(G, H, kernel):
    left = as_rw_graph(G)
    right = as_rw_graph(H)
    if left.is_directed() != right.is_directed():
        raise nx.NetworkXError("G and H must be both directed or both undirected")
    product, node_map = kernel(left.rx_graph, right.rx_graph)
    out = nx.DiGraph() if left.is_directed() else nx.Graph()
    index_to_pair = {}
    for (i, j), index in node_map.items():
        index_to_pair[index] = (left.index_to_node[i], right.index_to_node[j])
    out.add_nodes_from(index_to_pair[i] for i in sorted(index_to_pair))
    out.add_edges_from((index_to_pair[u], index_to_pair[v]) for u, v in product.edge_list())
    return out


def cartesian_product(G, H):
    """Return the Cartesian product of two graphs via rustworkx."""
    return _product(G, H, rx.cartesian_product)


def tensor_product(G, H):
    """Return the tensor product of two graphs via rustworkx."""
    return _product(G, H, rx.tensor_product)


def _can_run_line_graph(G, create_using=None, **kwargs):
    if G.is_directed():
        return "not implemented for directed type"
    if create_using is not None:
        return "rustworkx line_graph does not support create_using"
    return True


def line_graph(G, create_using=None):
    """Return the line graph of an undirected graph.

    Line-graph nodes are the edges of ``G``, named with the same tuple
    orientation NetworkX uses: the order the edge was first seen in.
    """
    _ = create_using
    rwg = as_rw_graph(G)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    line, node_map = rx.graph_line_graph(rwg.rx_graph)
    edge_index_map = rwg.rx_graph.edge_index_map()
    index_to_node = rwg.index_to_node

    if rwg.is_multigraph():
        # NetworkX names the line nodes (u, v, key) and returns a MultiGraph;
        # rustworkx lists a pair of parallel edges once per shared endpoint,
        # so collapse those duplicates.
        edge_keys = rwg.edge_keys
        line_nodes = {}
        for line_index, edge_index in node_map.items():
            u, v, _data = edge_index_map[edge_index]
            line_nodes[line_index] = (index_to_node[u], index_to_node[v], edge_keys[edge_index])
        out = nx.MultiGraph()
        out.add_nodes_from(line_nodes.values())
        pairs = {(a, b) if a < b else (b, a) for a, b in line.edge_list()}
        out.add_edges_from((line_nodes[a], line_nodes[b]) for a, b in sorted(pairs))
        return out

    line_nodes = {}
    for line_index, edge_index in node_map.items():
        u, v, _data = edge_index_map[edge_index]
        line_nodes[line_index] = (index_to_node[u], index_to_node[v])

    out = nx.Graph()
    out.add_nodes_from(line_nodes.values())
    out.add_edges_from((line_nodes[a], line_nodes[b]) for a, b in line.edge_list())
    return out


line_graph.can_run = _can_run_line_graph
line_graph.multigraph = True
