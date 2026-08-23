"""Connectivity algorithms dispatched to rustworkx."""

from __future__ import annotations

import networkx as nx
import rustworkx as rx

from nx_rustworkx.algorithms._utils import (
    as_rw_graph,
    can_run_directed,
    can_run_undirected,
    edge_weight_fn,
    remap_components,
    remap_nodes,
    require_directed,
    require_node,
    require_undirected,
    simple_view,
)

__all__ = [
    "articulation_points",
    "biconnected_components",
    "bridges",
    "condensation",
    "connected_components",
    "is_connected",
    "is_semiconnected",
    "is_strongly_connected",
    "is_weakly_connected",
    "node_connected_component",
    "number_connected_components",
    "number_strongly_connected_components",
    "number_weakly_connected_components",
    "stoer_wagner",
    "strongly_connected_components",
    "weakly_connected_components",
]


def _null_graph_guard(rwg):
    if rwg.number_of_nodes() == 0:
        raise nx.NetworkXPointlessConcept("Connectivity is undefined for the null graph.")


def is_connected(G):
    """Return True if the undirected graph is connected."""
    rwg = as_rw_graph(G)
    _null_graph_guard(rwg)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    try:
        return bool(rx.is_connected(rwg.rx_graph))
    except rx.NullGraph as exc:
        raise nx.NetworkXPointlessConcept("Connectivity is undefined for the null graph.") from exc


is_connected.can_run = can_run_undirected
is_connected.multigraph = True


def is_weakly_connected(G):
    """Return True if the directed graph is weakly connected."""
    rwg = as_rw_graph(G)
    _null_graph_guard(rwg)
    if not rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for undirected type")
    try:
        return bool(rx.is_weakly_connected(rwg.rx_graph))
    except rx.NullGraph as exc:
        raise nx.NetworkXPointlessConcept("Connectivity is undefined for the null graph.") from exc


is_weakly_connected.can_run = can_run_directed
is_weakly_connected.multigraph = True


def connected_components(G):
    """Generate connected components of an undirected graph."""
    rwg = as_rw_graph(G)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    return iter(remap_components(rwg, rx.connected_components(rwg.rx_graph)))


connected_components.can_run = can_run_undirected
connected_components.multigraph = True


def weakly_connected_components(G):
    """Generate weakly connected components of a directed graph."""
    rwg = as_rw_graph(G)
    if not rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for undirected type")
    return iter(remap_components(rwg, rx.weakly_connected_components(rwg.rx_graph)))


weakly_connected_components.can_run = can_run_directed
weakly_connected_components.multigraph = True


def number_connected_components(G):
    """Return the number of connected components in an undirected graph."""
    rwg = as_rw_graph(G)
    if rwg.is_directed():
        raise nx.NetworkXNotImplemented("not implemented for directed type")
    return int(rx.number_connected_components(rwg.rx_graph))


number_connected_components.can_run = can_run_undirected
number_connected_components.multigraph = True


def number_weakly_connected_components(G):
    """Return the number of weakly connected components in a directed graph."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    return int(rx.number_weakly_connected_components(rwg.rx_graph))


number_weakly_connected_components.can_run = can_run_directed
number_weakly_connected_components.multigraph = True


def strongly_connected_components(G):
    """Generate strongly connected components of a directed graph."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    return iter(remap_components(rwg, rx.strongly_connected_components(rwg.rx_graph)))


strongly_connected_components.can_run = can_run_directed
strongly_connected_components.multigraph = True


def number_strongly_connected_components(G):
    """Return the number of strongly connected components."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    return int(rx.number_strongly_connected_components(rwg.rx_graph))


number_strongly_connected_components.can_run = can_run_directed
number_strongly_connected_components.multigraph = True


def is_strongly_connected(G):
    """Return True if the directed graph is strongly connected."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    _null_graph_guard(rwg)
    return bool(rx.is_strongly_connected(rwg.rx_graph))


is_strongly_connected.can_run = can_run_directed
is_strongly_connected.multigraph = True


def is_semiconnected(G):
    """Return True if the directed graph is semiconnected."""
    rwg = as_rw_graph(G)
    require_directed(rwg)
    if rwg.number_of_nodes() == 0:
        raise nx.NetworkXPointlessConcept("Connectivity is undefined for the null graph.")
    return bool(rx.is_semi_connected(rwg.rx_graph))


is_semiconnected.can_run = can_run_directed
is_semiconnected.multigraph = True


def node_connected_component(G, n):
    """Return the connected component containing ``n``."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    index = require_node(rwg, n)
    index_to_node = rwg.index_to_node
    return {index_to_node[i] for i in rx.node_connected_component(rwg.rx_graph, index)}


node_connected_component.can_run = can_run_undirected
node_connected_component.multigraph = True


def _dfs_graph(rwg):
    """The container for DFS-tree kernels: parallel edges collapsed.

    rustworkx's bridges/articulation/biconnected kernels assume a simple graph,
    and NetworkX walks ``G[v]`` so it never sees parallel edges either.
    """
    return simple_view(rwg).graph if rwg.is_multigraph() else rwg.rx_graph


def articulation_points(G):
    """Yield the articulation points of an undirected graph."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    return iter(remap_nodes(rwg, rx.articulation_points(_dfs_graph(rwg))))


articulation_points.can_run = can_run_undirected
articulation_points.multigraph = True


def _can_run_bridges(G, root=None, **kwargs):
    _ = root
    return can_run_undirected(G)


def bridges(G, root=None):
    """Yield the bridges of an undirected graph.

    With ``root``, only bridges in the connected component containing it.
    Bridges are reported in edge-insertion order, as NetworkX yields them.
    """
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    if rwg.is_multigraph():
        return _multigraph_bridges(rwg, root)
    component = None
    if root is not None:
        index = require_node(rwg, root)
        component = set(rx.node_connected_component(rwg.rx_graph, index))
    bridge_set = {frozenset(pair) for pair in rx.bridges(rwg.rx_graph)}
    index_to_node = rwg.index_to_node
    return iter(
        [
            (index_to_node[u], index_to_node[v])
            for u, v in rwg.rx_graph.edge_list()
            if frozenset((u, v)) in bridge_set and (component is None or u in component)
        ]
    )


def _multigraph_bridges(rwg, root):
    """NetworkX finds bridges on ``nx.Graph(G)`` and then drops any pair that
    has parallel edges, since removing one of them never disconnects anything.
    rustworkx reports such a pair as a bridge, so run on the collapsed view."""
    view = simple_view(rwg)
    graph = view.graph
    component = None
    if root is not None:
        component = set(rx.node_connected_component(graph, require_node(rwg, root)))
    bridge_set = {frozenset(pair) for pair in rx.bridges(graph)}
    index_to_node = rwg.index_to_node
    return iter(
        [
            (index_to_node[u], index_to_node[v])
            for collapsed, (u, v) in zip(graph.edge_indices(), graph.edge_list())
            if view.multiplicity(collapsed) == 1
            and frozenset((u, v)) in bridge_set
            and (component is None or u in component)
        ]
    )


bridges.can_run = _can_run_bridges
bridges.multigraph = True


def biconnected_components(G):
    """Yield the node set of each biconnected component."""
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    index_to_node = rwg.index_to_node
    grouped: dict[int, set] = {}
    for (u, v), component in rx.biconnected_components(_dfs_graph(rwg)).items():
        nodes = grouped.setdefault(component, set())
        nodes.add(index_to_node[u])
        nodes.add(index_to_node[v])
    return iter(list(grouped.values()))


biconnected_components.can_run = can_run_undirected
biconnected_components.multigraph = True


def _can_run_condensation(G, scc=None, **kwargs):
    reason = can_run_directed(G)
    if reason is not True:
        return reason
    if scc is not None:
        return "rustworkx condensation computes its own components"
    return True


def condensation(G, scc=None):
    """Return the condensation of a directed graph as a NetworkX DiGraph.

    Component numbering follows rustworkx's component order, which need not
    match NetworkX's.
    """
    _ = scc
    rwg = as_rw_graph(G)
    require_directed(rwg)
    condensed = rx.condensation(rwg.rx_graph)
    out = nx.DiGraph()
    mapping = {}
    for component in condensed.node_indices():
        members = set(condensed[component])
        out.add_node(component, members=members)
        for member in members:
            mapping[member] = component
    out.add_edges_from(condensed.edge_list())
    out.graph["mapping"] = mapping
    return out


condensation.can_run = _can_run_condensation
condensation.multigraph = True


def _can_run_stoer_wagner(G, weight="weight", heap=None, **kwargs):
    _ = heap
    reason = can_run_undirected(G)
    if reason is not True:
        return reason
    if callable(weight):
        return "nx-rustworkx does not support custom weight callables"
    return True


def stoer_wagner(G, weight="weight", heap=None):
    """Return the minimum cut value and partition of an undirected graph.

    ``heap`` selects NetworkX's internal priority queue and does not change the
    result, so rustworkx ignores it.
    """
    _ = heap
    rwg = as_rw_graph(G)
    require_undirected(rwg)
    if rwg.number_of_nodes() < 2:
        raise nx.NetworkXError("graph has less than two nodes.")
    if not rx.is_connected(rwg.rx_graph):
        raise nx.NetworkXError("graph is not connected.")
    weight_fn = edge_weight_fn(weight)
    for _u, _v, data in rwg.rx_graph.weighted_edge_list():
        if weight_fn(data) < 0:
            raise nx.NetworkXError("graph has a negative-weighted edge.")
    cut_value, partition = rx.stoer_wagner_min_cut(rwg.rx_graph, weight_fn)
    index_to_node = rwg.index_to_node
    first = {index_to_node[i] for i in partition}
    second = [node for node in index_to_node if node not in first]
    return cut_value, ([node for node in index_to_node if node in first], second)


stoer_wagner.can_run = _can_run_stoer_wagner
