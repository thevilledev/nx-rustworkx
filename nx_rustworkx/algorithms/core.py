"""k-core decomposition dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import as_rw_graph, reject_multigraph

__all__ = ["core_number"]


def core_number(G):
    """Return the core number of every node."""
    rwg = as_rw_graph(G)
    rx_graph = rwg.rx_graph
    if any(u == v for u, v in rx_graph.edge_list()):
        raise nx.NetworkXNotImplemented(
            "Input graph has self loops which is not permitted; "
            "Consider using G.remove_edges_from(nx.selfloop_edges(G))."
        )
    index_to_node = rwg.index_to_node
    return {index_to_node[i]: int(value) for i, value in rx.core_number(rx_graph).items()}


core_number.can_run = lambda G, *a, **k: reject_multigraph(G) or True
