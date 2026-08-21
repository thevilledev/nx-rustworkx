"""Convert NetworkX graphs to rustworkx and remap results back."""

from __future__ import annotations

from typing import Any

import rustworkx as rx

from nx_rustworkx.graph import RustworkxGraph


def convert_from_nx(
    G,
    *,
    edge_attrs=None,
    node_attrs=None,
    preserve_edge_attrs=False,
    preserve_node_attrs=False,
    preserve_graph_attrs=False,
    preserve_all_attrs=False,
    name=None,
    graph_name=None,
    **kwargs,
):
    """Build a ``PyGraph`` / ``PyDiGraph`` and keep a node-to-index map.

    Parameters match the NetworkX backend dispatcher. Node payloads are the
    original NetworkX node IDs so results can be remapped.
    """
    if isinstance(G, RustworkxGraph):
        return G

    directed = G.is_directed()
    rx_graph = rx.PyDiGraph(multigraph=False) if directed else rx.PyGraph(multigraph=False)

    nodes = list(G)
    rx_graph.add_nodes_from(nodes)
    node_to_index = {node: i for i, node in enumerate(nodes)}
    index_to_node = list(nodes)

    keep_all_edges = bool(preserve_all_attrs or preserve_edge_attrs)
    edges: list[tuple[int, int, Any]] = []
    if keep_all_edges:
        for u, v, data in G.edges(data=True):
            edges.append((node_to_index[u], node_to_index[v], dict(data)))
    elif edge_attrs:
        for u, v, data in G.edges(data=True):
            payload = {key: data.get(key, default) for key, default in edge_attrs.items()}
            edges.append((node_to_index[u], node_to_index[v], payload))
    else:
        for u, v in G.edges():
            edges.append((node_to_index[u], node_to_index[v], None))
    if edges:
        rx_graph.add_edges_from(edges)

    graph_attrs = None
    if preserve_all_attrs or preserve_graph_attrs:
        graph_attrs = dict(getattr(G, "graph", {}))

    # node_attrs are unused in v0.1: algorithms remap via original node IDs.
    _ = node_attrs
    _ = preserve_node_attrs
    _ = name
    _ = graph_name
    _ = kwargs

    return RustworkxGraph(
        rx_graph,
        node_to_index,
        index_to_node,
        directed=directed,
        graph_attrs=graph_attrs,
    )


def convert_to_nx(result, *, name=None):
    """Wrap graph-valued returns as NetworkX graphs; leave remapped dicts as-is."""
    _ = name
    if isinstance(result, RustworkxGraph):
        return rustworkx_graph_to_nx(result)
    return result


def rustworkx_graph_to_nx(rwg: RustworkxGraph):
    """Rebuild a NetworkX graph using the original node IDs."""
    import networkx as nx

    out = nx.DiGraph() if rwg.is_directed() else nx.Graph()
    out.add_nodes_from(rwg.node_to_index)
    for u_idx, v_idx, data in rwg.rx_graph.weighted_edge_list():
        u = rwg.index_to_node[u_idx]
        v = rwg.index_to_node[v_idx]
        if isinstance(data, dict):
            out.add_edge(u, v, **data)
        elif data is None:
            out.add_edge(u, v)
        else:
            out.add_edge(u, v, weight=data)
    if rwg.graph:
        out.graph.update(rwg.graph)
    return out
