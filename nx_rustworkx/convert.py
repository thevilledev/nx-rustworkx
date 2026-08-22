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
    if keep_all_edges:
        def _payload(data):
            return dict(data)
    elif edge_attrs:
        def _payload(data):
            return {key: data.get(key, default) for key, default in edge_attrs.items()}
    else:
        def _payload(_data):
            return None

    # Read the graph through its adjacency view rather than ``G.edges()``.
    # NetworkX algorithms read ``G.adj``, and a subclass may override the
    # adjacency views without overriding the edge view. Indexing the view keeps
    # this working for adjacency views that are not dicts.
    adjacency = G.adj
    edges: list[tuple[int, int, Any]] = []
    if directed:
        for u in nodes:
            u_index = node_to_index[u]
            neighbors = adjacency[u]
            for v in neighbors:
                edges.append((u_index, node_to_index[v], _payload(neighbors[v])))
    else:
        seen: set = set()
        for u in nodes:
            u_index = node_to_index[u]
            neighbors = adjacency[u]
            for v in neighbors:
                if v in seen:
                    continue  # already added when walking v's neighbors
                edges.append((u_index, node_to_index[v], _payload(neighbors[v])))
            seen.add(u)
    if edges:
        rx_graph.add_edges_from(edges)

    graph_attrs = None
    if preserve_all_attrs or preserve_graph_attrs:
        graph_attrs = dict(getattr(G, "graph", {}))

    # Node payloads are the original node IDs, so node attributes are kept
    # alongside them for the algorithms that return a graph.
    stored_node_attrs = None
    if preserve_all_attrs or preserve_node_attrs:
        stored_node_attrs = {node: dict(data) for node, data in G.nodes(data=True)}
    elif node_attrs:
        stored_node_attrs = {
            node: {key: data.get(key, default) for key, default in node_attrs.items()}
            for node, data in G.nodes(data=True)
        }

    _ = name
    _ = graph_name
    _ = kwargs

    return RustworkxGraph(
        rx_graph,
        node_to_index,
        index_to_node,
        directed=directed,
        graph_attrs=graph_attrs,
        node_attrs=stored_node_attrs,
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
    # Iterate node_to_index, not index_to_node: after remove_node the index list
    # can carry None holes, while the map only ever holds real nodes.
    if rwg.node_attrs:
        out.add_nodes_from((node, rwg.node_attrs.get(node, {})) for node in rwg.node_to_index)
    else:
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
