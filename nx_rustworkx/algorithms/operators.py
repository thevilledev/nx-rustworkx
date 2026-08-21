"""Graph operators dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, reject_multigraph

__all__ = ["complement", "cartesian_product", "tensor_product"]


def _can_run(G, *args, **kwargs):
    for graph in (G, *args):
        if hasattr(graph, "is_multigraph"):
            reason = reject_multigraph(graph)
            if reason:
                return reason
    return True


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


complement.can_run = _can_run


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


cartesian_product.can_run = _can_run


def tensor_product(G, H):
    """Return the tensor product of two graphs via rustworkx."""
    return _product(G, H, rx.tensor_product)


tensor_product.can_run = _can_run
